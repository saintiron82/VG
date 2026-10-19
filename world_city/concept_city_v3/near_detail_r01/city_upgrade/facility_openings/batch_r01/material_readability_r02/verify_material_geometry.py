"""Exact material-independent oriented unit-face comparison, no voxel sampling."""
import collections,hashlib,json,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime'),str(B/'sampler_v2'),str(B/'sampler_v3')]
import author as a
import stream_render as sr
import reserved_io_r04 as rio
from verify_source_passages_v2 import hits

def faces(rows):
    planes=collections.defaultdict(list)
    for material,q in rows:
        axis,t,p,s,r=a.quad_info(q);coords=[p,*r];integers=[round(v*20) for v in coords];assert all(abs(v*20-i)<1e-6 for v,i in zip(coords,integers));planes[axis,integers[0],s].append(integers[1:])
    return planes
def unit_mask(rects):
    return {(u,v) for x0,y0,x1,y1 in rects for u in range(x0,x1) for v in range(y0,y1)}
def compare_rows(old,new):
    left=faces(old);right=faces(new);missing=extra=total=0;examples=[];digest=hashlib.sha256();peak=0
    for key in sorted(set(left)|set(right)):
        a0=unit_mask(left.get(key,[]));b=unit_mask(right.get(key,[]));removed=a0-b;added=b-a0;missing+=len(removed);extra+=len(added);total+=len(a0);peak=max(peak,len(a0)+len(b));digest.update(json.dumps([key,sorted(a0)],separators=(',',':')).encode())
        if removed or added:examples.append({'plane':key,'removed':sorted(removed)[:10],'added':sorted(added)[:10]})
    return {'removed_oriented_unit_faces':missing,'added_oriented_unit_faces':extra,'reference_oriented_unit_faces':total,'reference_coordinate_digest':digest.hexdigest(),'peak_two_plane_face_cells':peak,'examples':examples[:10],'all_pass':missing==extra==0}
def reference(path):return {'path':str(Path(path).resolve().relative_to(a.ROOT)),'sha256':a.sha(path)}
def main():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));start=time.monotonic();key='registered_main_gate_header';cp=HERE/'compiled_native_v1'/key/'catalog.json';cat=a.load(cp);w=rio.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules');oldmp=B/'composed'/key/(key+'.manifest.json');oldm=a.load(oldmp);pre=a.load(HERE/'composed'/key/'preflight.json');h=a.load(HERE/'composed'/key/'roof_handoff_snapshot.json');oldh=a.load(B/'composed'/key/'roof_handoff_snapshot.json');oldroof=a.ROOT/oldh['files']['.render.json']['path'];newroof=a.ROOT/h['files']['.render.json']['path'];roof_result=compare_rows(sr.iter_quads(oldroof),sr.iter_quads(newroof));assert roof_result['all_pass'],roof_result;final_result=compare_rows(sr.iter_quads(a.ROOT/oldm['render_path']),sr.iter_quads(a.ROOT/pre['render_path']));assert final_result['all_pass'],final_result
    oldcat=a.load(B/'compiled_v3'/key/'catalog.json');assert cat['ordered_regions']==oldcat['ordered_regions'];regions=[]
    for old,new in zip(oldcat['outputs'],cat['outputs']):
        op=a.ROOT/old['path'];np=a.ROOT/new['path'];assert a.sha(op)==old['sha256'] and a.sha(np)==new['sha256'];od=a.load(op);nd=a.load(np);result=compare_rows(((g['material'],q) for g in od['groups'] for q in g['quads']),((g['material'],q) for g in nd['groups'] for q in g['quads']));assert result['all_pass'];chunks=[]
        for o,n in zip(od['chunks'],nd['chunks']):
            oo=a.load(a.ROOT/o['path']);nn=a.load(a.ROOT/n['path']);assert oo['coarse_payload_sha256']==nn['coarse_payload_sha256'] and oo['owned_cell_bounds']==nn['owned_cell_bounds'] and oo['fine_cells']==nn['fine_cells'] and oo['interface_pixel_counts']==nn['interface_pixel_counts'];chunks.append({'original':o,'revised':n,'native_original_payload_equal':True,'fine_cell_count_equal':True,'interface_occupancy_xor_equal':True})
        regions.append({'id':new['region']['id'],'exterior_face_comparison':result,'chunks':chunks})
    oldstats=a.load(a.ROOT/oldh['stats_path']);newstats=a.load(a.ROOT/h['stats_path']);assert {tuple(r['chunk']):r['reference_owned_fine_cells'] for r in oldstats['chunks']}=={tuple(r['chunk']):r['reference_owned_fine_cells'] for r in newstats['chunks']};oldw=B/'polygon_sources/emitted_qa'/(key+'.open_source_witnesses.json');witness=a.load(oldw);probes=witness['probes'];crossings=[0]*len(probes);digest=hashlib.sha256();count=0;materials=collections.Counter()
    for mat,q in sr.iter_quads(a.ROOT/pre['render_path']):
        count+=1;materials[mat]+=1;digest.update(json.dumps([mat,q],separators=(',',':')).encode())
        for i,p in enumerate(probes):crossings[i]+=hits(q,p)
    assert not any(crossings);revision=a.load(HERE/'generated/material_revision.json');from author_material_revision import normalized
    oldsource=a.load(a.ROOT/revision['base_roof']['path']);newsource=a.load(a.ROOT/revision['revised_roof']['path']);assert normalized(newsource,oldsource,revision['roof_operation_changes'])==oldsource;oldcan=a.load(a.ROOT/revision['base_canonical']['path']);newcan=a.load(a.ROOT/revision['revised_canonical']['path']);assert normalized(newcan,oldcan,revision['canonical_operation_changes'])==oldcan
    report={'schema':'riverstone.roof.material_only_geometry_qa.v1','asset_key':key,'all_pass':True,'render_path':pre['render_path'],'render_sha256':pre['render_sha256'],'quad_count':count,'ordered_material_quad_digest':digest.hexdigest(),'material_quads':dict(materials),'full_roof_exterior_comparison':roof_result,'complete_composed_exterior_comparison':final_result,'contact_regions':regions,'all_full_roof_chunk_occupied_counts_equal':True,'all_ordered_geometry_exact_after_material_restore':True,'source_material_selectors_absent':True,'occupancy_equality_proof':'Every ordered shape, transform, part, instance, cut, selector and grid is identical after restoring only listed material fields; no material selectors exist. Thus common inclusion/deletion decisions and occupied-cell coordinates are unchanged. Full emitted oriented exterior face coordinates independently match; all roof chunk occupied counts and all21 ROI coarse payloads/interface XOR masks agree. No missing full cell payload comparison is claimed.','entry_passage_ray_count':len(probes),'entry_crossings':crossings,'source_witness_reference':reference(oldw),'source_references':[reference(p) for p in [__file__,HERE/'author_material_revision.py',HERE/'generated/material_revision.json',oldmp,a.ROOT/oldm['render_path'],oldroof,newroof,a.ROOT/oldh['stats_path'],a.ROOT/h['stats_path'],B/'sampler_v3/verify_source_passages_v2.py']],'geometry_shape_change':False,'collision_reference_changed':False,'visual_acceptance':'PENDING parent same-camera review','wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};w.write(HERE/'composed'/key/'material_geometry_qa.json',report);w.close();print(json.dumps({k:report[k] for k in ['all_pass','quad_count','material_quads','entry_passage_ray_count','wall_seconds','peak_rss_kib']}),flush=True)
if __name__=='__main__':main()
