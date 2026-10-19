"""Checkpointed native common evaluation of an explicit finite source revision.

Outside the declared region union the immutable prior render is authoritative.
No prior render voxelization or full-world cell volume is constructed.
"""
import argparse,gc,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent.parent),str(HERE.parent.parent/'composed_runtime')]
import author as a
import compile_set as helpers
import seam_adapter as seam
from sparse_ray_cache import SparseRayCache,RevisedOutside

def checkpoint(path,data):helpers.checkpoint(path,data)
def disk_bytes():return sum(p.stat().st_size for p in HERE.parent.rglob('*') if p.is_file())
def guard(start):
    assert time.monotonic()-start<590,'600-second checkpoint window reached'
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<256*1024,'256MiB RSS cap'
    assert disk_bytes()<30*1024*1024,'window/composition30MiB budget'

def run(plan_path,out,chunk_limit=None):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));start=time.monotonic();plan=a.load(plan_path);out.mkdir(parents=True,exist_ok=True)
    for pk,hk in [('canonical_master_path','canonical_master_sha256'),('retained_render_path','retained_render_sha256'),('retained_manifest_path','retained_manifest_sha256'),('replacement_contract_path','replacement_contract_sha256'),('source_catalog_path','source_catalog_sha256')]:assert a.sha(a.ROOT/plan[pk])==plan[hk]
    master=a.load(a.ROOT/plan['canonical_master_path']);contract=a.load(a.ROOT/plan['replacement_contract_path']);assert master['grid_origin']==plan['grid_origin_m']==[0,0,0]
    tools={str(Path(p).resolve().relative_to(a.ROOT)):a.sha(p) for p in [__file__,a.core.__file__,helpers.__file__,seam.__file__,sys.modules[SparseRayCache.__module__].__file__]};signature=a.core.digest({'plan':plan,'tools':tools})
    progress={'signature':signature,'status':'indexing_retained_render','finished_regions':[],'plan_path':str(plan_path.relative_to(a.ROOT)),'plan_sha256':a.sha(plan_path)};checkpoint(out/'progress.json',progress)
    retained=SparseRayCache(a.ROOT/plan['retained_render_path'],plan['ordered_regions']);guard(start);print(json.dumps({'stage':'retained_index','stats':retained.stats,'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
    entries=contract.get('protected_component_entry_cuts',[]);outputs=[];new_chunks=0
    try:
      for p in plan['plans']:
        region=p['region'];rid=region['id'];patch={'id':rid,'fine_cell_bounds':p['fine_cell_bounds'],'replacement_volume_master_m':region};groups=[];records=[];pixels=0
        for ci,cp in enumerate(p['chunks']):
            guard(start);target=out/f'{rid}.{ci:03d}.chunk.json.gz'
            if target.exists():result=a.load(target);assert result['signature']==signature
            else:
                t=time.monotonic();fine=a.core.compile_master(master,{'pitch':.05},max_candidate_cells=140000,max_output_cells=140000,cell_bounds=cp['sample_cell_bounds_with_one_cell_halo']);assert fine['candidate_cells']==cp['candidate_visits']
                outside=RevisedOutside(fine,plan['ordered_regions'],retained);preview=helpers.owned_surface(fine,cp['owned_cell_bounds']);adapter=seam.build(None,fine,preview,patch,entries,owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=outside)
                result={'signature':signature,'asset_key':plan['asset_key'],'region':rid,'chunk':ci,'groups':helpers.merge_groups(adapter['fine_exterior_groups']+adapter['transition_groups']),'interface_pixel_counts':adapter['interface_pixel_counts'],'transition_quads':adapter['transition_quads'],'transition_unit_faces':adapter['transition_unit_faces'],'common_payload_sha256':fine['payload_hash'],'fine_candidates':fine['candidate_cells'],'fine_cells':len(fine['cells']),'sample_cell_bounds':cp['sample_cell_bounds_with_one_cell_halo'],'owned_cell_bounds':cp['owned_cell_bounds'],'source_shapes_cropped':False,'protected_entry_violations':adapter['protected_entry_interface_violations'],'seconds':round(time.monotonic()-t,4),'global_constraints_evaluated':False}
                del fine,outside,preview,adapter;gc.collect();checkpoint(target,result);new_chunks+=1;guard(start)
            groups+=result['groups'];pixels+=sum(result['interface_pixel_counts'].values());records.append({'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target)})
            progress.update(status='running',region=rid,region_chunk=ci+1,region_chunks=len(p['chunks']),new_chunks=new_chunks,elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,additional_output_bytes=disk_bytes(),ray_stats=retained.stats);checkpoint(out/'progress.json',progress);print(json.dumps({k:progress[k] for k in ['region','region_chunk','region_chunks','new_chunks','elapsed_seconds','max_rss_kib']}),flush=True)
            if chunk_limit and new_chunks>=chunk_limit:raise TimeoutError('Requested subset checkpoint reached')
        spans=[p['fine_cell_bounds']['max'][j]-p['fine_cell_bounds']['min'][j] for j in range(3)];assert pixels==2*sum(spans[i]*spans[j] for i,j in [(0,1),(1,2),(0,2)])
        target=out/(rid+'.render.json.gz');data={'schema':'riverstone.facility.finite_revision.render.v1','asset_key':plan['asset_key'],'region':region,'groups':helpers.merge_groups(groups),'chunks':records,'canonical_master_sha256':plan['canonical_master_sha256'],'retained_render_sha256':plan['retained_render_sha256'],'collision_reference_changed':False,'source_shapes_cropped':False,'protected_entry_violations':0,'signature':signature};checkpoint(target,data);outputs.append({'region':region,'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target),'quad_count':sum(len(g['quads']) for g in data['groups']),'chunks':len(records)});progress['finished_regions'].append(rid)
      catalog={'schema':'riverstone.facility.finite_revision.catalog.v1','asset_key':plan['asset_key'],'plan_path':str(plan_path.relative_to(a.ROOT)),'plan_sha256':a.sha(plan_path),'source_master_sha256':plan['source_master_sha256'],'source_revision':plan['source_revision'],'canonical_master_path':plan['canonical_master_path'],'canonical_master_sha256':plan['canonical_master_sha256'],'retained_manifest_path':plan['retained_manifest_path'],'retained_manifest_sha256':plan['retained_manifest_sha256'],'retained_render_path':plan['retained_render_path'],'retained_render_sha256':plan['retained_render_sha256'],'replacement_contract_path':plan['replacement_contract_path'],'replacement_contract_sha256':plan['replacement_contract_sha256'],'ordered_regions':plan['ordered_regions'],'outputs':outputs,'tools':tools,'signature':signature,'complete':len(outputs)==len(plan['ordered_regions']),'source_shapes_cropped':False,'collision_reference_changed':False,'global_constraints_evaluated':False,'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'new_common_calls':new_chunks,'retained_ray_stats':retained.stats};checkpoint(out/'catalog.json',catalog);progress['status']='complete';checkpoint(out/'progress.json',progress);print(json.dumps({'complete':True,'elapsed_seconds':catalog['elapsed_seconds'],'max_rss_kib':catalog['max_rss_kib'],'new_common_calls':new_chunks}),flush=True)
    except Exception as e:
      progress.update(status='paused',error=str(e),elapsed_seconds=round(time.monotonic()-start,3));checkpoint(out/'progress.json',progress);print(json.dumps(progress),flush=True);raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('output',type=Path);p.add_argument('--chunk-limit',type=int);q=p.parse_args();run(q.plan.resolve(),q.output.resolve(),q.chunk_limit)
