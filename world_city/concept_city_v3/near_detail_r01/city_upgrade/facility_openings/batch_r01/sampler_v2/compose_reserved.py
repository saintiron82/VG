"""Source-bound shared offline mesh composition for finite facility batches.

Reuse frozen exact rectangle subtraction/streaming primitives. Every native
operation and old cache group is independently hash-bound by a canonical
source contract; original component-scoped cuts are never inferred by colour.
"""
import argparse,collections,gzip,hashlib,io,json,resource,sys,time
import reserved_io_r03 as reserved_io
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'composed_runtime')]
import stream_compose as base
import stream_render as sr
import compile_set as helper
a=base.a

class Composition(base.Composition):
    def __init__(self,catalog_path,roof_handoff):
        self.budget=reserved_io.writer_for_catalog(a.load(catalog_path),a.ROOT,HERE,a.HERE.parent/'house_rules')
        self.inputs=[];self.stats={};cat=self.bind(catalog_path,'complete bounded region catalog');assert cat['complete'];self.key=cat['asset_key'];self.item={'asset_key':self.key,'source_sha256':cat['source_sha256'],'source_render_sha256':cat['source_render_sha256']}
        self.cat=cat;self.source=self.bind(cat['source_render_path'],'original render and unchanged collider',cat['source_render_sha256']);self.bind(cat['source_master_path'],'original master',cat['source_sha256'],load=False)
        self.contract=contract=self.bind(cat['window_contract_path'],'canonical opening and source roof replacement scope',cat['window_contract_sha256']);self.bind(cat['canonical_master_path'],'canonical detailed roof plus opening source',cat['canonical_master_sha256'],load=False)
        proof=contract['roof_composition'];self.bind(proof['composition_proof_path'],'all transformed operation equivalence and preserved source scopes',proof['composition_proof_sha256'],load=False)
        h=a.load(roof_handoff);roof=next(x for x in h['assets'] if x['asset_key']==self.key);assert roof['native_asset_key']==self.key and roof['source_sha256']==cat['source_sha256'] and roof['source_render_sha256']==cat['source_render_sha256'] and roof['emitted_master_sha256']==cat['roof_master_sha256'];assert roof['complete_authored_source_domain_coverage'] and roof['independent_qa']['pass'] and roof['independent_replay']['pass']
        self.roof=roof;self.out=HERE/'composed'/self.key;self.out.mkdir(parents=True,exist_ok=True);snap=self.out/'roof_handoff_snapshot.json'
        if snap.exists():assert a.load(snap)==roof
        else:self.budget.write(snap,roof)
        self.bind(snap,'frozen asset roof handoff');self.bind(roof['emitted_master_path'],'selected complete fine roof source',roof['emitted_master_sha256'],load=False)
        for k in ['independent_qa','independent_replay']:self.bind(roof[k]['path'],k,roof[k]['sha256'],load=False)
        rf=roof['files']['.render.json'];self.roof_path=a.ROOT/rf['path'];self.bind(self.roof_path,'complete fine roof render',rf['sha256'],load=False)
        self.regions=cat['ordered_regions'];self.roof_clip=base.Clipper(self.regions)
        roofgroups=set()
        for m in contract['roof_replacement_scope']['exact_source_roof_groups']:
            gi=m['group_index'];assert self.source['groups'][gi]==m['original_group'];assert a.core.digest(self.source['groups'][gi])==m['original_group_sha256'];roofgroups.add(gi)
        self.roofgroups=roofgroups;self.retained=[];self.retained_origins=[]
        for gi,g in enumerate(self.source['groups']):
            if gi in roofgroups:continue
            for qi,q in enumerate(g['quads']):
                kept=self.roof_clip.pieces(q);self.retained.extend((g['material'],f) for f in kept);self.retained_origins.extend((gi,qi) for f in kept)
        self.cutters=collections.defaultdict(list);indexed=collections.defaultdict(list)
        for i,(m,q) in enumerate(self.retained):
            axis,t,p,s,r=a.quad_info(q);self.cutters[axis,round(p*20),s].append(r);indexed[axis,round(p*20),s].append((i,r))
        contact=collections.defaultdict(list)
        for material,q in sr.iter_quads(self.roof_path):
            for f in self.roof_clip.pieces(q):
                axis,t,p,s,r=a.quad_info(f)
                for i,other in indexed.get((axis,round(p*20),-s),[]):
                    _,intersection=a.subtract_rect(r,other)
                    if intersection:contact[i].append(intersection)
        repaired=[];origins=[];self.contact_exceptions=[];self.contact_area=0.
        for i,(m,q) in enumerate(self.retained):
            axis,t,p,s,r=a.quad_info(q);rs=[r]
            for cut in contact.get(i,[]):rs=[f for rr in rs for f in a.subtract_rect(rr,cut)[0]]
            area=a.rect_area(r)-sum(map(a.rect_area,rs));qs=[q] if rs==[r] else [a.rect_quad(rr,axis,t,p,s) for rr in rs];repaired.extend((m,f) for f in qs);origins.extend(self.retained_origins[i] for f in qs)
            if area>1e-8:
                self.contact_area+=area;gi,qi=self.retained_origins[i];self.contact_exceptions.append({'group_index':gi,'quad_index':qi,'original_fragment_sha256':a.core.digest(q),'opposite_contact_rectangles':contact[i],'removed_area_m2':round(area,8),'axis':axis,'plane':p,'source_normal':s,'reason':'Exact opposing outward compiled surfaces bound occupied half-spaces; remove both finite interior face domains.'})
        self.retained=repaired;self.retained_origins=origins;byorigin=collections.defaultdict(list)
        for (_,q),origin in zip(repaired,origins):byorigin[origin].append(q)
        self.untouched_count=self.edited_count=0;self.source_edits=[];digest=hashlib.sha256()
        for gi,g in enumerate(self.source['groups']):
            if gi in roofgroups:continue
            for qi,q in enumerate(g['quads']):
                kept=byorigin.get((gi,qi),[])
                if kept==[q]:self.untouched_count+=1;digest.update(json.dumps([gi,qi,g['material'],q],separators=(',',':')).encode())
                else:self.edited_count+=1;self.source_edits.append({'group_index':gi,'quad_index':qi,'original_quad_sha256':a.core.digest(q),'retained_quads':kept})
        self.untouched_sha=digest.hexdigest();self.extra=[];self.priority_edits=[]
        assert len(cat['outputs'])==len(self.regions)
        for i,r in enumerate(cat['outputs']):
            assert r['region']==self.regions[i];later=base.Clipper(self.regions[i+1:]);payload=self.bind(r['path'],'canonical finite region render and boundary adapter',r['sha256']);assert not payload['source_shapes_cropped'] and payload['protected_entry_violations']==0;changed=0
            for g in payload['groups']:
                for q in g['quads']:
                    parts=later.pieces(q);changed+=parts!=[q];self.extra.extend((g['material'],f) for f in parts)
            self.priority_edits.append({'region':r['region']['id'],'changed_quads':changed,'later_region_count':len(self.regions)-i-1})
            for chunk in payload['chunks']:self.bind(chunk['path'],'bounded source occupancy fingerprint and exact interface pixels',chunk['sha256'],load=False)
        self.indexpath=a.ROOT/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json';self.bind(self.indexpath,'unchanged original city index',load=False)
        self.bind(cat['plan_path'],'finite native integer cell_bounds plan',cat['plan_sha256'],load=False)
        for path,digest in cat['tools'].items():self.bind(path,'frozen bounded compile implementation',digest,load=False)
        for p in [__file__,base.__file__,sr.__file__,reserved_io.__file__]:self.bind(p,'offline composition implementation',load=False)
        for r in self.budget.provenance['dependencies']:self.bind(r['path'],r['role'],r['sha256'],load=False)

    def write_render(self,path,summary):
        # New groups on material changes are valid and avoid buffering geometry.
        with self.budget.stream(path) as raw:
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

def run(catalog,roof_handoff,audit_edges=False,emit=False):
    start=time.monotonic();comp=Composition(catalog,roof_handoff);summary=comp.count();report={'schema':'riverstone.facility.batch_composition.preflight.v1','asset_key':comp.key,'summary':summary,'face_audit':sr.plane_audit(comp.factory),'source_inputs':comp.inputs,'source_untouched_quads':comp.untouched_count,'source_untouched_sha256':comp.untouched_sha,'source_finite_edited_quads':comp.edited_count,'priority_edits':comp.priority_edits,'original_collider_reference_changed':False,'new_contact_occupancy_authored':False,'output_write_policy':comp.budget.provenance};print(json.dumps({'stage':'face_audit',**summary,**report['face_audit']}),flush=True)
    if audit_edges:
        report['edge_audit']=sr.edge_audit(comp.factory,max_axis_lines=262144)
        report['original_edge_audit']=sr.edge_audit(lambda:((g['material'],q) for g in comp.source['groups'] for q in g['quads']),max_axis_lines=262144)
        print(json.dumps({'stage':'edge_audit','composed':report['edge_audit'],'original':report['original_edge_audit']}),flush=True)
    comp.budget.write(comp.out/'preflight.json',report)
    assert report['face_audit']['same_normal_duplicate_unit_faces']==report['face_audit']['opposed_coplanar_unit_faces']==report['face_audit']['off_grid_quads']==0,'Exact face-domain audit failed; evidence preserved'
    if emit:
        assert summary['runtime_cap_96mib_pass'];target=comp.out/(comp.key+'.candidate.render.json.gz');comp.write_render(target,summary);report['render_path']=str(target.relative_to(a.ROOT));report['render_sha256']=a.sha(target)
        outret=comp.out/'outside_retained_sourcequads.json.gz';comp.budget.write(outret,{'schema':'riverstone.facility_openings.outside_source_quads.v1','asset_key':comp.key,'source_render_path':comp.cat['source_render_path'],'source_render_sha256':comp.cat['source_render_sha256'],'groups':helper.merge_groups([{'material':m,'quads':[q]} for m,q in comp.retained]),'world_local_aabbs':comp.regions,'collision_reference_changed':False})
        comp.budget.write(comp.out/'finite_source_quad_edits.json.gz',{'source_edits':comp.source_edits,'opposed_internal_contacts':comp.contact_exceptions,'untouched_sha256':comp.untouched_sha,'untouched_count':comp.untouched_count,'roof_group_indices':sorted(comp.roofgroups)})
    report.update(elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);comp.budget.write(comp.out/'preflight.json',report);print(json.dumps({'complete':True,'seconds':report['elapsed_seconds'],'rss_kib':report['max_rss_kib'],'render':report.get('render_path')}),flush=True)
    assert report['max_rss_kib']<256*1024

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('--roof-handoff',type=Path,required=True);p.add_argument('--edges',action='store_true');p.add_argument('--emit',action='store_true');args=p.parse_args();run(args.catalog,args.roof_handoff,args.edges,args.emit)
