"""Small original-source samples for native pitch/ownership certification.

No full asset compile, source crop, geometry export, or existing cache overwrite.
"""
import gc,hashlib,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime'),str(B/'sampler_v2')]
import author as a
import seam_adapter as seam
import compile_set as helpers
from compile_source_contacts import ExactOutside as LegacyOutside
import native_grid as n
import test_native_grid as unit
import reserved_io_r03 as rio
from voxel_character.common import prepared_sampling_v3 as prepared
H=a.HERE.parent/'house_rules';sys.path.insert(0,str(H))
from output_reservations_v3 import ReservationBook

def sample(plan,master,pitch,cb):
    fast=prepared.compile_prepared(plan,cell_bounds=cb,max_candidate_cells=140000,max_output_cells=140000)
    reference=a.core.compile_master(master,{'pitch':pitch},cell_bounds=cb,max_candidate_cells=140000,max_output_cells=140000)
    assert fast['payload_hash']==reference['payload_hash'] and fast['cells']==reference['cells']
    return fast

def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));start=time.monotonic();cpu0=resource.getrusage(resource.RUSAGE_SELF);tests=unit.run();invp=B/'pitch_generalization_plan/inventory.json';inventory=a.load(invp)
 refs=[Path(__file__),HERE/'native_grid.py',HERE/'test_native_grid.py',invp,Path(a.core.__file__),Path(prepared.__file__),Path(seam.__file__),Path(helpers.__file__),Path(rio.__file__),Path(sys.modules[ReservationBook.__module__].__file__),H/'shared_output_budget.v2.json'];identity={'scope':'native_pitch_small_samples','references':[{'path':str(p.relative_to(a.ROOT)),'sha256':a.sha(p)} for p in refs]};config=a.load(H/'shared_output_budget.v2.json');book=ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/p for p in config['retained_roots']],config['limit_bytes'],min_free_disk_bytes=config['min_free_disk_bytes']);key='facility_native_pitch_validation:r01';scopes=[{'directory':str(HERE.relative_to(a.ROOT)),'prefix':''}];book.reserve(key,scopes,500000,identity);book.acquire_writer(key);writer=rio.ReservedWriter(book,key,B,scopes,a.ROOT);rows=[]
 try:
  for row in [r for r in inventory['assets'] if r['native_pitch_m']!=.5]:
   assert time.monotonic()-start<550;writer.check();mp=a.ROOT/row['source_master_path'];rp=a.ROOT/row['source_render_path'];assert a.sha(mp)==row['source_master_sha256'] and a.sha(rp)==row['source_render_sha256'];master=a.load(mp);render=a.load(rp);pitch=render['pitch'];grids=n.Grids(pitch,.05,tuple(render['grid_origin']),tuple(master['grid_origin']));native_plan=prepared.prepare_master(master,{'pitch':pitch},max_plan_bytes=64*1024**2);fine_plan=prepared.prepare_master(master,{'pitch':.05},max_plan_bytes=64*1024**2);prepared.assert_plan_matches(native_plan,master,{'pitch':pitch});prepared.assert_plan_matches(fine_plan,master,{'pitch':.05});cache=seam.CacheOccupancy(render);ops=a.source_inventory(master);paints=[x for x in ops if x[2]['action']=='paint'];roof=[x for x in paints if x[2].get('material','').startswith('slate')];selected=[paints[0],(roof or paints)[0]];results=[]
   for op_index,(cid,iid,op,t,bb) in enumerate(selected):
    # Small cube at the exact selected operation AABB midpoint. The full original
    # source is still evaluated; an empty sample is reported, never called coverage.
    mid=[(bb[0][j]+bb[1][j])/2 for j in range(3)];center=grids.world_cell(mid,True);owned={'min':[v-4 for v in center],'max':[v+4 for v in center]};cb={'min':[v-1 for v in owned['min']],'max':[v+1 for v in owned['max']]};native_cb=grids.native_bounds(cb);coarse=sample(native_plan,master,pitch,native_cb);fine=sample(fine_plan,master,.05,cb);region={k:[grids.detail_origin[j]+owned[k][j]*.05 for j in range(3)] for k in ['min','max']};patch={'id':str(op_index),'fine_cell_bounds':owned,'replacement_volume_master_m':region};outside=n.ExactOutside(fine,coarse,{},[region],[],grids);preview=helpers.owned_surface(fine,owned);result=seam.build(render,fine,preview,patch,owned_bounds=owned,validate_edges=False,occupancy=outside)
    mismatch=[];occupied={tuple(c[:3]) for c in coarse['cells']}
    for x in range(native_cb['min'][0],native_cb['max'][0]):
     for y in range(native_cb['min'][1],native_cb['max'][1]):
      for z in range(native_cb['min'][2],native_cb['max'][2]):
       cell=(x,y,z);world=[grids.native_origin[j]+(cell[j]+.5)*pitch for j in range(3)]
       if cache.sample(world)[0]!=(cell in occupied):mismatch.append(cell)
    # Independent XOR mask counts from actual cached original exterior parity.
    independent={};native_differences=0
    for axis in range(3):
     u,v=(axis+1)%3,(axis+2)%3
     for sign in [-1,1]:
      for aa in range(owned['min'][u],owned['max'][u]):
       for zz in range(owned['min'][v],owned['max'][v]):
        c=[0,0,0];c[axis]=owned['min'][axis] if sign<0 else owned['max'][axis]-1;c[u]=aa;c[v]=zz;other=c.copy();other[axis]+=sign;p=[grids.detail_origin[j]+(other[j]+.5)*.05 for j in range(3)];inside=tuple(c) in outside.fine;old=cache.sample(p)[0];name=f'coarse_{int(old)}_fine_{int(inside)}';independent[name]=independent.get(name,0)+1;native_differences+=old!=outside.sample(p)[0]
    assert not mismatch and native_differences==0 and independent==result['interface_pixel_counts']
    results.append({'source_component':cid,'source_instance':iid,'source_operation':op['id'],'owned_fine_cell_bounds':owned,'source_native_cell_bounds':native_cb,'native_cells':len(coarse['cells']),'fine_cells':len(fine['cells']),'original_cache_occupancy_mismatches':mismatch,'cache_vs_native_outside_differences':native_differences,'native_reference_payload':coarse['payload_hash'],'fine_reference_payload':fine['payload_hash'],'reference_fast_payloads_equal':True,'actual_cache_xor_pixel_counts_equal':True,'interface_pixel_counts':result['interface_pixel_counts'],'transition_unit_faces':result['transition_unit_faces'],'source_shape_change':False})
    del coarse,fine,outside,preview,result;gc.collect()
   rows.append({'asset_key':row['asset_key'],'native_pitch_m':pitch,'grid_origin_m':render['grid_origin'],'source_master_sha256':row['source_master_sha256'],'source_render_sha256':row['source_render_sha256'],'plan_keys':{'native':native_plan.plan_key,'fine':fine_plan.plan_key},'samples':results,'semantic_scope':'Source volume and finite roof/body boundary only; no pedestrian clearance claim for basins, shafts, water bores or mechanical voids.','all_pass':True});del native_plan,fine_plan,cache,master,render;gc.collect();writer.write(HERE/'progress.json',{'complete':False,'completed_assets':[r['asset_key'] for r in rows],'wall_seconds':time.monotonic()-start});print(json.dumps({'asset_key':row['asset_key'],'all_pass':True,'seconds':round(time.monotonic()-start,3),'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
  # Actual default .5 stored source chunk: identical fine/seam bytes through old/new adapter.
  cp=B/'compiled_v3/registered_main_gate_header/catalog.json';cat=a.load(cp);plan=a.load(a.ROOT/cat['plan_path']);chunk=plan['plans'][0]['chunks'][0];bounds=chunk['sample_cell_bounds_with_one_cell_halo'];g=n.Grids();samples={}
  for role,field,pitch,cb in [('coarse','source_master_path',.5,g.native_bounds(bounds)),('fine','canonical_master_path',.05,bounds),('roof','roof_master_path',.05,bounds)]:
   master=a.load(a.ROOT/cat[field]);p=prepared.prepare_master(master,{'pitch':pitch},max_plan_bytes=64*1024**2);samples[role]=prepared.compile_prepared(p,cell_bounds=cb,max_candidate_cells=140000,max_output_cells=140000);del p,master
  fine,coarse=samples['fine'],samples['coarse'];roof={tuple(c[:3]):c[5] for c in samples['roof']['cells']};region=plan['plans'][0]['region'];patch={'id':region['id'],'fine_cell_bounds':plan['plans'][0]['fine_cell_bounds'],'replacement_volume_master_m':region};preview=helpers.owned_surface(fine,chunk['owned_cell_bounds']);render=a.load(a.ROOT/cat['source_render_path']);old=LegacyOutside(fine,coarse,roof,plan['ordered_regions'],cat['roof_materials']);new=n.ExactOutside(fine,coarse,roof,plan['ordered_regions'],cat['roof_materials']);adapters=[seam.build(render,fine,preview,patch,owned_bounds=chunk['owned_cell_bounds'],validate_edges=False,occupancy=o) for o in [old,new]];assert json.dumps(adapters[0],sort_keys=True,separators=(',',':'))==json.dumps(adapters[1],sort_keys=True,separators=(',',':'));stored=a.load(cp.parent/(region['id']+'.000.chunk.json.gz'));groups=helpers.merge_groups(adapters[1]['fine_exterior_groups']+adapters[1]['transition_groups']);assert groups==stored['groups'];tests['actual_default_half_pitch_fine_and_adapter_bytes_identical']=True;tests['actual_default_half_pitch_stored_groups_unchanged']=True
  cpu=resource.getrusage(resource.RUSAGE_SELF);report={'schema':'riverstone.facility.native_pitch_small_sample_validation.v1','all_pass':True,'tests':tests,'source_references':identity['references'],'sampler_provenance':prepared.get_sampler_provenance(),'actual_samples':rows,'default_actual_regression':{'catalog_path':str(cp.relative_to(a.ROOT)),'catalog_sha256':a.sha(cp),'stored_chunk_sha256':a.sha(cp.parent/(region['id']+'.000.chunk.json.gz')),'fine_seam_json_bytes_identical':True,'stored_group_payload_identical':True},'full_asset_compiles':0,'source_or_existing_cache_modified':False,'new_runtime_candidates_emitted':False,'default_runtime_changed':False,'global_constraints_evaluated':False,'scope':'Two tiny original full-source bounded samples per exceptional pitch asset plus one existing .5 adapter comparison. Not full source cache replay or full contact coverage.','wall_seconds':time.monotonic()-start,'user_cpu_seconds':cpu.ru_utime-cpu0.ru_utime,'system_cpu_seconds':cpu.ru_stime-cpu0.ru_stime,'peak_rss_kib':cpu.ru_maxrss};writer.write(HERE/'small_sample_validation.json',report);writer.write(HERE/'progress.json',{'complete':True,'all_pass':True,'wall_seconds':report['wall_seconds']});book.release(key,identity,'Small native-pitch validation complete; no runtime asset activated.');print(json.dumps({'complete':True,'all_pass':True,'tests':len(tests),'wall_seconds':report['wall_seconds'],'rss_kib':cpu.ru_maxrss}),flush=True)
 finally:writer.close()
if __name__=='__main__':main()
