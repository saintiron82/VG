"""Exact finite face-domain replacement over a frozen composed render.

This layer only clips already-authored meshes. Outside the declared AABBs every
prior quad is byte-equivalent JSON geometry, with a reproducible fingerprint.
"""
import argparse,collections,gzip,hashlib,io,json,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent.parent),str(HERE.parent.parent/'composed_runtime')]
import author as a
import stream_render as sr
import stream_compose as base
import seam_adapter as seam
import compile_set as helpers

def bind(inputs,path,role,expected=None,load=True):
    path=Path(path);path=path if path.is_absolute() else a.ROOT/path;digest=a.sha(path)
    if expected:assert digest==expected,(role,path)
    inputs.append({'path':str(path.relative_to(a.ROOT)),'sha256':digest,'role':role});return a.load(path) if load else None

def touching(q,r):return all(max(v[j] for v in q)>=r['min'][j]-1e-8 and min(v[j] for v in q)<=r['max'][j]+1e-8 for j in range(3))
def update_edges(counters,regions,m,q):
    for r in regions:
        if touching(q,r):counters[r['id']].update(seam.interface_segments([q],{k:[round(v*20) for v in r[k]] for k in ('min','max')},.05,[0,0,0]))
def edge_report(counters):
    return {rid:{'unit_edges':len(c),'unpaired_unit_edges':sum(n%2 for n in c.values()),'unpaired_examples':[{'edge':[list(v) for v in k],'count':n} for k,n in c.items() if n%2][:8]} for rid,c in counters.items()}

def write_render(path,factory,meta,summary,provenance):
    with path.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as z,io.TextIOWrapper(z,encoding='utf-8') as f:
        f.write('{"groups":[');last=None;first=True;n=0
        for material,q in factory():
            if material!=last:
                if not first:f.write(']},')
                f.write('{"material":'+json.dumps(material)+',"quads":[');last=material;first=False;ingroup=0
            if ingroup:f.write(',')
            f.write(json.dumps(q,separators=(',',':')));ingroup+=1;n+=1
        if not first:f.write(']}')
        f.write(']');assert n==summary['quad_count']
        meta={k:v for k,v in meta.items() if k not in ('groups','quad_count','bounds','provenance','cell_count','payload_hash','pitch')}
        meta.update(quad_count=n,bounds=summary['bounds'],pitch=.05,cell_count=None,geometry='Finite source-revision replacement over preserved mixed-resolution composed geometry.',provenance=provenance)
        for k,v in meta.items():f.write(','+json.dumps(k)+':'+json.dumps(v,separators=(',',':')))
        f.write('}\n')

def run(catalog_path,out):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));start=time.monotonic();inputs=[];cat=bind(inputs,catalog_path,'complete finite revision compile catalog');assert cat['complete'];out.mkdir(parents=True,exist_ok=True)
    old=bind(inputs,cat['retained_manifest_path'],'immutable prior accepted composition',cat['retained_manifest_sha256']);bind(inputs,cat['retained_render_path'],'immutable prior composed render',cat['retained_render_sha256'],False);source=a.ROOT/cat['retained_render_path'];contract=bind(inputs,cat['replacement_contract_path'],'revised window replacement contract',cat['replacement_contract_sha256']);bind(inputs,cat['canonical_master_path'],'complete canonical revised source',cat['canonical_master_sha256'],False);plan=bind(inputs,cat['plan_path'],'finite revision domains and budgets',cat['plan_sha256']);regions=cat['ordered_regions'];clip=base.Clipper(regions);extra=[]
    for i,row in enumerate(cat['outputs']):
        assert row['region']==regions[i];d=bind(inputs,row['path'],'bounded revision render and exact retained-cache adapter',row['sha256']);assert not d['source_shapes_cropped'] and not d['protected_entry_violations'];later=base.Clipper(regions[i+1:])
        for g in d['groups']:
            for q in g['quads']:extra.extend((g['material'],p) for p in later.pieces(q))
        for c in d['chunks']:bind(inputs,c['path'],'native common chunk occupancy fingerprint',c['sha256'],False)
    for p,h in cat['tools'].items():bind(inputs,p,'frozen bounded compile implementation',h,False)
    for p in [__file__,base.__file__,sr.__file__,seam.__file__,helpers.__file__]:bind(inputs,p,'mesh composition implementation',load=False)
    source_edits=[];untouched=hashlib.sha256();unchanged=edited=original_count=0;old_edges=collections.defaultdict(collections.Counter)
    for gi,qi,m,q in sr.iter_indexed_quads(source):
        original_count+=1;update_edges(old_edges,regions,m,q);parts=clip.pieces(q)
        if parts==[q]:unchanged+=1;untouched.update(json.dumps([gi,qi,m,q],separators=(',',':')).encode())
        else:edited+=1;source_edits.append({'group_index':gi,'quad_index':qi,'original_quad_sha256':a.core.digest(q),'material':m,'retained_quads':parts})
    assert original_count==old['output_quad_count'];edit_path=out/'prior_composed_finite_quad_edits.json.gz';a.write(edit_path,{'source_render_path':cat['retained_render_path'],'source_render_sha256':cat['retained_render_sha256'],'regions':regions,'finite_quad_edits':source_edits,'untouched_quads':unchanged,'untouched_sha256':untouched.hexdigest()});bind(inputs,edit_path,'exact prior composed finite edits and unchanged fingerprint',load=False)
    def factory():
        for m,q in sr.iter_quads(source):
            for p in clip.pieces(q):yield m,p
        yield from extra
    n=0;lo=[float('inf')]*3;hi=[float('-inf')]*3;materials=collections.Counter();new_edges=collections.defaultdict(collections.Counter);analytic=old['bounds_contract']['analytic_source_bounds'];outside=0;geom=hashlib.sha256()
    for m,q in factory():
        n+=1;materials[m]+=1;geom.update(json.dumps([m,q],separators=(',',':')).encode());update_edges(new_edges,regions,m,q)
        for v in q:
            outside+=any(v[j]<analytic['min'][j]-1e-8 or v[j]>analytic['max'][j]+1e-8 for j in range(3))
            for j in range(3):lo[j]=min(lo[j],v[j]);hi[j]=max(hi[j],v[j])
    summary={'quad_count':n,'vertex_normal_material_bytes':n*144,'runtime_mib':n*144/1048576,'runtime_cap_96mib_pass':n*144<=96*1048576,'bounds':{'min':lo,'max':hi},'material_quads':dict(materials),'outside_analytic_aabb_vertices':outside,'composition_geometry_sha256':geom.hexdigest()}
    report={'schema':'riverstone.facility.finite_revision.preflight.v1','asset_key':cat['asset_key'],'summary':summary,'source_inputs':inputs,'prior_composed_untouched_quads':unchanged,'prior_composed_untouched_sha256':untouched.hexdigest(),'prior_composed_finite_edited_quads':edited,'prior_boundary_edges':edge_report(old_edges),'composed_boundary_edges':edge_report(new_edges),'regions':regions,'collision_reference_changed':False};print(json.dumps({'stage':'count_and_boundary','summary':summary,'boundary':report['composed_boundary_edges']}),flush=True);a.write(out/'composition_preflight.json',report)
    report['face_audit']=sr.plane_audit(factory);a.write(out/'composition_preflight.json',report);print(json.dumps({'stage':'face_audit',**report['face_audit']}),flush=True)
    assert report['face_audit']['same_normal_duplicate_unit_faces']==report['face_audit']['opposed_coplanar_unit_faces']==report['face_audit']['off_grid_quads']==0
    assert all(x['unpaired_unit_edges']==0 for x in report['composed_boundary_edges'].values()),'Finite source revision boundary is not closed'
    assert summary['runtime_cap_96mib_pass'] and not outside and summary['bounds']==old['bounds']
    target=out/(cat['asset_key']+'.b2.candidate.render.json.gz');meta=sr.read_metadata(source);provenance={'source_master_sha256':cat['source_master_sha256'],'revised_master_sha256':cat['source_revision']['revised_master_sha256'],'prior_composed_render_sha256':cat['retained_render_sha256'],'composition_implementation_sha256':a.sha(__file__),'collision_reference_changed':False};write_render(target,factory,meta,summary,provenance)
    # Overlay support is a separate geometry-only surface source: inherited
    # retained body outside revision domains plus newly emitted masonry faces.
    op=old['outside_retained_sourcequads'];retained=bind(inputs,op['path'],'prior outside retained body faces',op['sha256']);groups=[]
    for g in retained['groups']:
        for q in g['quads']:groups.extend({'material':g['material'],'quads':[p]} for p in clip.pieces(q))
    # Limit this addition to exact source masonry materials, not glass/timber.
    original_source=cat['source_revision']['original_master_path'];original=bind(inputs,original_source,'unchanged original indexed source',cat['source_master_sha256']);masonry={o['material'] for c in original['components'] if c['id']=='masonry' for o in c['operations'] if o['action']=='paint'}
    groups.extend({'material':m,'quads':[q]} for m,q in extra if m in masonry);overlay=out/'outside_retained_and_revised_masonry.json.gz';a.write(overlay,{'schema':'riverstone.facility.revision_overlay_support.v1','asset_key':cat['asset_key'],'source_render_path':old['collision_reference_path'],'source_render_sha256':old['source_render_sha256'],'revised_master_sha256':cat['source_revision']['revised_master_sha256'],'groups':helpers.merge_groups(groups),'pitch':.05,'grid_origin':[0,0,0],'bounds':summary['bounds'],'quad_count':sum(len(g['quads']) for g in groups),'description':'Exact previous retained body outside revision regions plus actual revised fine masonry. Window-feature masks use the revised source; these are overlay supports, not a second visible body mesh.','collision_reference_changed':False});bind(inputs,overlay,'actual retained/revised masonry relief support',load=False)
    report.update(render_path=str(target.relative_to(a.ROOT)),render_sha256=a.sha(target),output_bytes=target.stat().st_size,outside_retained_sourcequads={'path':str(overlay.relative_to(a.ROOT)),'sha256':a.sha(overlay)},source_inputs=inputs,elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);a.write(out/'composition_preflight.json',report);print(json.dumps({'complete':True,'render_path':report['render_path'],'render_sha256':report['render_sha256'],'seconds':report['elapsed_seconds'],'rss_kib':report['max_rss_kib']}),flush=True)
    assert report['max_rss_kib']<256*1024
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('output',type=Path);q=p.parse_args();run(q.catalog.resolve(),q.output.resolve())
