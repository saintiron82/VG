"""Source-defined empty-volume rays and exact protected functional face domains.

Open constraints are measured as finite rays, not whole-volume certificates.
Water and machine cut states are compared, never assumed to be open passages.
"""
import argparse,collections,hashlib,json,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime'),str(B/'sampler_v2'),str(B/'sampler_v3')]
import author as a
import stream_render as sr
import reserved_io_r04 as rio
from verify_open_structures import hits

def overlap(x,y):
    return all(x['max'][j]>y['min'][j]+1e-8 and x['min'][j]<y['max'][j]-1e-8 for j in range(3))

def domain_faces(rows,bounds):
    result=collections.defaultdict(list)
    for material,q in rows:
        axis,t,p,sign,r=a.quad_info(q)
        if not bounds['min'][axis]-1e-8<=p<=bounds['max'][axis]+1e-8:continue
        clipped=[max(r[0],bounds['min'][t[0]]),max(r[1],bounds['min'][t[1]]),min(r[2],bounds['max'][t[0]]),min(r[3],bounds['max'][t[1]])]
        if clipped[2]>clipped[0]+1e-8 and clipped[3]>clipped[1]+1e-8:result[material,axis,round(p,8),sign].append(clipped)
    return result

def difference_area(left,right):
    total=0.
    for key,rects in left.items():
        for rect in rects:
            remaining=[rect]
            for other in right.get(key,[]):remaining=[piece for r in remaining for piece in a.subtract_rect(r,other)[0]]
            total+=sum(a.rect_area(r) for r in remaining)
    return total

def empty_constraint_probes(source,original):
    probes=[]
    for constraint in source.get('constraints',[]):
        if constraint.get('kind')!='empty_region' or constraint.get('selector',{}):continue
        shape=constraint.get('shape',{})
        if shape.get('kind')!='box' or constraint.get('transform'):continue
        lo,hi=shape['min'],shape['max']
        for axis in [0,2]:
            tangents=[j for j in range(3) if j!=axis]
            for fu in [.25,.5,.75]:
                for fv in [.25,.5,.75]:
                    point=[(lo[j]+hi[j])/2 for j in range(3)]
                    for j,f in zip(tangents,[fu,fv]):point[j]=lo[j]+(hi[j]-lo[j])*f
                    probe={'id':constraint['id']+':'+str(axis)+':'+str(fu)+':'+str(fv),'source_constraint_id':constraint['id'],'source_constraint_sha256':a.core.digest(constraint),'axis':axis,'point_m':point,'interval_m':[lo[axis],hi[axis]],'source_constraint_contains_probe':True}
                    probe['original_render_crossing_faces']=sum(hits(q,probe) for _,q in original)
                    assert not probe['original_render_crossing_faces'],probe
                    probes.append(probe)
    return probes

def ref(path):return {'path':str(Path(path).resolve().relative_to(a.ROOT)),'sha256':a.sha(path)}

def main(catalog,render):
    start=time.monotonic();cat=a.load(catalog);w=rio.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules')
    for path,sha in [(cat['source_master_path'],cat['source_sha256']),(cat['source_render_path'],cat['source_render_sha256']),(cat['canonical_master_path'],cat['canonical_master_sha256'])]:assert a.sha(a.ROOT/path)==sha
    source=a.load(a.ROOT/cat['source_master_path']);canonical=a.load(a.ROOT/cat['canonical_master_path']);contract=a.load(a.ROOT/cat['window_contract_path']);assert not contract['patches'];assert source.get('constraints')==canonical.get('constraints')
    original=a.load(a.ROOT/cat['source_render_path']);oldrows=[(g['material'],q) for g in original['groups'] for q in g['quads']];newrows=list(sr.iter_quads(render));probes=empty_constraint_probes(source,oldrows)
    functional_path=HERE/'functional_cut_validation.json';functional=a.load(functional_path);assert functional['all_pass'];cuts=next(x for x in functional['assets'] if x['asset_key']==cat['asset_key']);assert cuts['source_sha256']==cat['source_sha256'] and cuts['canonical_master_sha256']==cat['canonical_master_sha256']
    semantic_path=HERE/'semantic_protection_candidates.json';semantic=next(x for x in a.load(semantic_path)['assets'] if x['asset_key']==cat['asset_key']);assert len(cuts['witnesses'])==len(semantic['features']);features=[]
    for feature in semantic['features']:
        witness=next(x for x in cuts['witnesses'] if (x['source_component'],x['source_instance'],x['source_operation'])==(feature['component'],feature['instance'],feature['operation']));assert witness['source_operation_sha256']==feature['operation_sha256'] and witness['exact_cells_and_labels_equal'] and witness['original_core_replay_equal']
        bounds=feature['world_aabb'];regions=[r['id'] for r in cat['ordered_regions'] if overlap(bounds,r)];assert not regions,(feature,regions)
        old=domain_faces(oldrows,bounds);new=domain_faces(newrows,bounds);removed=difference_area(old,new);added=difference_area(new,old);assert removed<1e-8 and added<1e-8,(feature,removed,added)
        features.append({**feature,'overlapping_modified_regions':regions,'original_cut_bytes_and_tiny_reference_payload_equal':True,'removed_material_face_area_m2':removed,'added_material_face_area_m2':added,'original_face_fragments':sum(map(len,old.values())),'composed_face_fragments':sum(map(len,new.values())),'empty_pedestrian_space_claimed':False})
    assert probes or features,'No source-defined functional evidence'
    references={'source_master':ref(a.ROOT/cat['source_master_path']),'source_render':ref(a.ROOT/cat['source_render_path']),'canonical_master':ref(a.ROOT/cat['canonical_master_path']),'replacement_contract':ref(a.ROOT/cat['window_contract_path']),'functional_cut_validation':ref(functional_path),'functional_cut_driver':ref(HERE/'verify_functional_cuts.py'),'semantic_candidates':ref(semantic_path),'driver':ref(__file__),'ray_helper':ref(B/'sampler_v3/verify_open_structures.py')}
    for name in ['operation_roof_adapter_v1.py','operation_roof_adapter_v2.py','plan_regions_native_r02.py','prepare_native_sources_r03.py','test_operation_adapter.py','validate_samples.py','test_native_grid.py']:references[name]=ref(HERE/name)
    witness={'schema':'riverstone.facility.native_functional_witnesses.v1','asset_key':cat['asset_key'],'source_references':references,'window_count':0,'probes':probes,'functional_features':features,'scope':'Finite rays inside original all-part empty box constraints; exact oriented/material face-domain equality within each functional cut AABB, preserved cut bytes and 27-cell original/canonical/reference witnesses. No claim every cut is open or every volume is clear.'};wp=B/'polygon_sources/emitted_qa'/(cat['asset_key']+'.native_source_witnesses.json');w.write(wp,witness)
    failures=[{'id':p['id'],'crossing_faces':sum(hits(q,p) for _,q in newrows)} for p in probes];failures=[p for p in failures if p['crossing_faces']];digest=hashlib.sha256()
    for m,q in newrows:digest.update(json.dumps([m,q],separators=(',',':')).encode())
    report={'schema':'riverstone.facility.native_emitted_geometry_qa.v1','asset_key':cat['asset_key'],'render_path':str(render.relative_to(a.ROOT)),'render_sha256':a.sha(render),'quad_count':len(newrows),'ordered_material_quad_digest':digest.hexdigest(),'source_witness_reference':ref(wp),'reserved_driver_reference':references['driver'],'window_count':0,'entry_passage_ray_count':len(probes),'functional_feature_count':len(features),'semantic_protection_all_pass':not failures,'failure_count':len(failures),'failures':failures,'all_pass':not failures,'elapsed_seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};w.write(B/'polygon_sources/emitted_qa'/(cat['asset_key']+'.emitted_geometry_qa.json'),report);w.close();print(json.dumps(report),flush=True);assert report['all_pass']

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('render',type=Path);q=p.parse_args();main(q.catalog.resolve(),q.render.resolve())
