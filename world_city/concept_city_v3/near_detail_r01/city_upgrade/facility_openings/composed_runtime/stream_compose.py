"""Bounded offline render composition; no voxel generation and no runtime edits.

Inputs are immutable source/roof/window catalogs. Large roof geometry is streamed.
Optional interface outputs own all surfaces inside their finite AABBs.
"""
import argparse, collections, gzip, hashlib, io, json, resource, time
from pathlib import Path
import compose as c
import stream_render as sr
a=c.a
HERE=Path(__file__).resolve().parent

class Clipper:
    def __init__(self,regions):
        self.planes=collections.defaultdict(list)
        for r in regions:
            for axis in range(3):
                t=[j for j in range(3) if j!=axis]
                rect=[r['min'][t[0]],r['min'][t[1]],r['max'][t[0]],r['max'][t[1]]]
                for p in range(round(r['min'][axis]*20),round(r['max'][axis]*20)+1):self.planes[axis,p].append(rect)
    def pieces(self,q):
        axis,t,p,s,r=a.quad_info(q);cuts=self.planes.get((axis,round(p*20)))
        if not cuts:return [q]
        rects=[r]
        for cut in cuts:rects=[f for rect in rects for f in a.subtract_rect(rect,cut)[0]]
        return [q] if rects==[r] else [a.rect_quad(f,axis,t,p,s) for f in rects]

class Composition:
    def __init__(self,catalog_path,interface_path=None):
        self.inputs=[];self.stats={};cat=self.bind(catalog_path,'complete window catalog');assert len(cat['assets'])==1
        self.item=item=cat['assets'][0];self.key=item['asset_key']
        self.source=source=self.bind(item['source_render_path'],'original render and unchanged collider',item['source_render_sha256'])
        self.bind(item['source_master_path'],'original master',item['source_sha256'],load=False)
        contract=self.bind(item['replacement_contract_path'],'finite window replacement contract',item['replacement_contract_sha256'])
        self.contract=contract;self.bind(contract['authored_master_path'],'canonical roof and window source',contract['authored_master_sha256'],load=False)
        handoff=a.load(a.HERE.parent/'facility_roofs/compiled_priority_r01/handoff_manifest.json')
        self.roof=roof=next(x for x in handoff['assets'] if x['asset_key']==self.key)
        assert roof['source_master_sha256']==item['source_sha256'] and roof['source_render_sha256']==item['source_render_sha256']
        assert roof['complete_selected_source_coverage'] and roof['independent_qa']['pass']
        snap=HERE/(self.key+'.roof_handoff_snapshot.json')
        if snap.exists():assert a.load(snap)==roof,'Frozen roof handoff differs'
        else:a.write(snap,roof)
        self.bind(snap,'immutable complete roof handoff')
        self.bind(roof['emitted_master_path'],'finished roof source',roof['authored_master_sha256'],load=False)
        self.bind(roof['replacement_contract']['path'],'roof replacement contract',roof['replacement_contract']['sha256'])
        self.bind(roof['independent_qa']['path'],'independent roof QA',roof['independent_qa']['sha256'])
        rf=roof['files']['.render.json'];self.roof_path=a.ROOT/rf['path'];self.bind(self.roof_path,'complete fine roof render',rf['sha256'],load=False)
        self.windows=[{'id':p['id'],**p['replacement_volume_master_m']} for p in contract['patches']]
        self.interface=[];self.interface_outputs=[];self.interface_manifest=None
        if interface_path:
            self.interface_manifest=self.bind(interface_path,'bounded authored interface catalog')
            self.interface=self.interface_manifest['regions'];self.interface_outputs=self.interface_manifest['outputs']
        self.regions=self.windows+self.interface
        self.roof_clip=Clipper(self.regions);self.interface_clip=Clipper(self.interface)
        roofgroups=set()
        for m in roof['original_roof_material_mapping']:
            gi=m['source_render_group_index']
            if gi is None:continue
            assert a.core.digest(source['groups'][gi])==m['source_group_sha256_canonical'];roofgroups.add(gi)
        self.retained=[];self.retained_origins=[];self.untouched_count=0;self.edited_count=0;digest=hashlib.sha256();edits={(e['group_index'],e['quad_index']):e for e in contract['cache_quad_edits']}
        self.source_edits=[]
        for gi,g in enumerate(source['groups']):
            if gi in roofgroups:continue
            for qi,q in enumerate(g['quads']):
                e=edits.get((gi,qi));qs=e['retained_quads'] if e else [q]
                if e:assert e['original_quad']==q and a.core.digest(q)==e['original_quad_sha256']
                kept=[f for p in qs for f in self.interface_clip.pieces(p)]
                if kept==[q]:
                    self.untouched_count+=1;digest.update(json.dumps([gi,qi,g['material'],q],separators=(',',':')).encode())
                else:self.edited_count+=1
                self.retained.extend((g['material'],p) for p in kept)
                self.retained_origins.extend((gi,qi) for p in kept)
                if kept!=[q]:self.source_edits.append({'group_index':gi,'quad_index':qi,'original_quad_sha256':a.core.digest(q),'retained_quads':kept})
        self.untouched_sha=digest.hexdigest();self.roofgroups=roofgroups
        self.cutters=collections.defaultdict(list)
        for m,q in self.retained:
            axis,t,p,s,r=a.quad_info(q);self.cutters[axis,round(p*20),s].append(r)
        # Opposite exterior normals at the exact same face domain bound solids
        # on both sides. Their visual union removes BOTH internal contact faces.
        # Preserve the finite exception to untouched-source-quad invariance.
        indexed=collections.defaultdict(list)
        for i,(m,q) in enumerate(self.retained):
            axis,t,p,s,r=a.quad_info(q);indexed[axis,round(p*20),s].append((i,r))
        contact=collections.defaultdict(list)
        for material,q in sr.iter_quads(self.roof_path):
            for f in self.roof_clip.pieces(q):
                axis,t,p,s,r=a.quad_info(f)
                for i,other in indexed.get((axis,round(p*20),-s),[]):
                    _,intersection=a.subtract_rect(r,other)
                    if intersection:contact[i].append(intersection)
        repaired=[];repaired_origins=[];self.contact_exceptions=[];self.contact_area=0.
        for i,(m,q) in enumerate(self.retained):
            axis,t,p,s,r=a.quad_info(q);rects=[r]
            for cut in contact.get(i,[]):rects=[f for rr in rects for f in a.subtract_rect(rr,cut)[0]]
            area=a.rect_area(r)-sum(map(a.rect_area,rects))
            pieces=[q] if rects==[r] else [a.rect_quad(rr,axis,t,p,s) for rr in rects]
            repaired.extend((m,f) for f in pieces);repaired_origins.extend(self.retained_origins[i] for f in pieces)
            if area>1e-8:
                self.contact_area+=area;gi,qi=self.retained_origins[i];self.contact_exceptions.append({'source_group_index':gi,'source_quad_index':qi,'source_fragment_sha256':a.core.digest(q),'opposite_contact_rectangles':contact[i],'removed_area_m2':round(area,8),'axis':axis,'plane':p,'source_normal':s,'reason':'Exact coplanar opposite exterior faces; both backward half-spaces occupied by their compiled source solids.'})
        self.retained=repaired;self.retained_origins=repaired_origins
        by_original=collections.defaultdict(list)
        for (m,q),origin in zip(repaired,repaired_origins):by_original[origin].append(q)
        self.untouched_count=0;self.edited_count=0;self.source_edits=[];digest=hashlib.sha256()
        for gi,g in enumerate(source['groups']):
            if gi in roofgroups:continue
            for qi,q in enumerate(g['quads']):
                kept=by_original.get((gi,qi),[])
                if kept==[q]:
                    self.untouched_count+=1;digest.update(json.dumps([gi,qi,g['material'],q],separators=(',',':')).encode())
                else:
                    self.edited_count+=1;self.source_edits.append({'group_index':gi,'quad_index':qi,'original_quad_sha256':a.core.digest(q),'retained_quads':kept})
        self.untouched_sha=digest.hexdigest()
        self.extra=[]
        for record in item['windows']:
            w=self.bind(record['path'],'fine window and active boundary seam',record['sha256'])
            assert w['protected_entry_interface_violations']==0 and not w['source_geometry_deformed'] and not w['collider_changed']
            for g in w['groups']:
                for q in g['quads']:self.extra.extend((g['material'],p) for p in self.interface_clip.pieces(q))
        assert len(item['windows'])==len(self.windows)
        for record in self.interface_outputs:
            r=self.bind(record['path'],'authored interface fine geometry and seam',record['sha256'])
            for g in r['groups']:self.extra.extend((g['material'],q) for q in g['quads'])
        self.indexpath=a.ROOT/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json'
        self.bind(self.indexpath,'original source index',load=False)
        self.bind(__file__,'streaming compositor',load=False);self.bind(sr.__file__,'bounded streaming reader and QA',load=False)
    def bind(self,path,role,expected=None,load=True):
        path=Path(path);path=path if path.is_absolute() else a.ROOT/path;digest=a.sha(path)
        if expected:assert digest==expected,(role,'SHA mismatch')
        self.inputs.append({'path':str(path.relative_to(a.ROOT)),'sha256':digest,'role':role})
        return a.load(path) if load else None
    def factory(self):
        yield from self.retained
        count=touched=dedup=0;area=0.
        for m,q in sr.iter_quads(self.roof_path):
            fragments=self.roof_clip.pieces(q);touched+=fragments!=[q]
            for f in fragments:
                axis,t,p,s,r=a.quad_info(f);cuts=self.cutters.get((axis,round(p*20),s),[])+self.cutters.get((axis,round(p*20),-s),[]);rs=[r]
                if cuts:
                    for cut in cuts:rs=[piece for rect in rs for piece in a.subtract_rect(rect,cut)[0]]
                delta=a.rect_area(r)-sum(map(a.rect_area,rs));area+=delta;dedup+=delta>1e-8
                pieces=[f] if rs==[r] else [a.rect_quad(rr,axis,t,p,s) for rr in rs]
                count+=len(pieces)
                for piece in pieces:yield m,piece
        self.stats={'fine_roof_output_quads':count,'fine_roof_ROI_touched_quads':touched,'roof_coplanar_removed_quads':dedup,'roof_coplanar_removed_area_m2':round(area,8),'opposed_internal_contact_area_m2_each_side':round(self.contact_area,8),'source_contact_fragment_exceptions':len(self.contact_exceptions)}
        yield from self.extra
    def count(self):
        count=0;lo=[float('inf')]*3;hi=[float('-inf')]*3;materials=collections.Counter()
        for m,q in self.factory():
            count+=1;materials[m]+=1
            for v in q:
                for j in range(3):lo[j]=min(lo[j],v[j]);hi[j]=max(hi[j],v[j])
        return {'quad_count':count,'vertex_normal_material_bytes':count*144,'runtime_mib':count*144/1048576,'runtime_cap_96mib_pass':count*144<=96*1048576,'bounds':{'min':lo,'max':hi},'material_quads':dict(materials),**self.stats}
    def write_render(self,path,summary):
        # New groups on material changes are valid and avoid buffering geometry.
        with Path(path).open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as z:
                with io.TextIOWrapper(z,encoding='utf-8') as f:
                    f.write('{"groups":[');last=None;first=True;n=0
                    for material,q in self.factory():
                        if material!=last:
                            if not first:f.write(']},')
                            f.write('{"material":'+json.dumps(material)+',"quads":[');last=material;first=False;ingroup=0
                        if ingroup:f.write(',')
                        f.write(json.dumps(q,separators=(',',':')));ingroup+=1;n+=1
                    if not first:f.write(']}')
                    f.write(']');assert n==summary['quad_count']
                    meta={k:v for k,v in self.source.items() if k not in ['groups','quad_count','bounds','provenance','cell_count','payload_hash','pitch']}
                    meta.update(quad_count=n,bounds=summary['bounds'],pitch=.05,cell_count=None,geometry='Mixed-resolution offline render union: retained coarse body, detailed roof and bounded source-authored window/interface geometry.',provenance={'source_master_sha256':self.item['source_sha256'],'source_render_sha256':self.item['source_render_sha256'],'compositor_sha256':a.sha(__file__),'collision_reference_changed':False})
                    for k,v in meta.items():f.write(','+json.dumps(k)+':'+json.dumps(v,separators=(',',':')))
                    f.write('}\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('--interfaces',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--audit',action='store_true');p.add_argument('--faces-only',action='store_true');p.add_argument('--render',type=Path);args=p.parse_args();start=time.monotonic()
    comp=Composition(args.catalog,args.interfaces);result={'schema':'riverstone.streaming_composition.preflight.v1','asset_key':comp.key,'summary':comp.count(),'source_inputs':comp.inputs,'untouched_original_quads':comp.untouched_count,'untouched_original_quad_sha256':comp.untouched_sha,'finite_edited_original_quads':comp.edited_count,'no_whole_roof_json_load':True,'collision_reference_changed':False}
    print(json.dumps({'stage':'count',**result['summary']}),flush=True)
    a.write(args.report,result)
    if args.audit or args.faces_only:
        result['face_audit']=sr.plane_audit(comp.factory);print(json.dumps({'stage':'face_audit',**result['face_audit']}),flush=True)
        a.write(args.report,result)
    if args.audit:
        result['edge_audit']=sr.edge_audit(comp.factory,max_axis_lines=262144);print(json.dumps({'stage':'edge_audit',**result['edge_audit']}),flush=True)
    if args.render:
        assert result['summary']['runtime_cap_96mib_pass'];comp.write_render(args.render,result['summary']);result['output']={'path':str(args.render.resolve().relative_to(a.ROOT)),'sha256':a.sha(args.render),'bytes':args.render.stat().st_size}
    result['elapsed_seconds']=round(time.monotonic()-start,3);result['max_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;a.write(args.report,result);assert result['max_rss_kib']<256*1024
    print(json.dumps({'complete':True,'seconds':result['elapsed_seconds'],'rss_kib':result['max_rss_kib']}),flush=True)

if __name__=='__main__':main()
