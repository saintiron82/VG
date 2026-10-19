"""Explicit prepared-v3 resumable bounded region compiler. All active domains use one source.

This is orchestration of common.compile_master and frozen seam helpers, not a
new voxel engine. Only render meshes and fingerprints are persisted.
"""
import argparse,gc,json,math,resource,signal,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE/'sampler_v2'))
import reserved_io_r03 as reserved_io
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'composed_runtime')]
import author as a
from voxel_character.common import prepared_sampling_v3 as sampler_v3
EXPECTED_SAMPLER_SHA256='fc1d25b73b3158394c6559246288ded2f5b882c80389b12695a254100239dfd7'
import compile_set as helpers
import seam_adapter as seam
from compile_source_contacts import ExactOutside
CAP=50_000_000
H=a.HERE.parent/'house_rules'
sys.path.insert(0,str(H))
from output_reservations_v3 import ReservationBook
BUDGET=None

def disk_bytes():
    roots=[HERE,a.HERE.parent/'facility_roofs/compiled_expansion_r01']
    return sum(p.stat().st_size for r in roots for p in r.rglob('*') if p.is_file())
def guard(start):
    if BUDGET is not None:BUDGET.check()
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<256*1024,'256MiB RSS cap'
    assert time.monotonic()-start<590,'bounded execution window; checkpoint retained'
    assert disk_bytes()<CAP,'joint additional50MiB cap'
def checkpoint(p,x):
    assert BUDGET is not None
    BUDGET.write(p,x)

def run(path,region_filter=None,chunk_limit=None,reservation_cap_bytes=None):
    global BUDGET
    assert type(reservation_cap_bytes)is int and reservation_cap_bytes>0
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    cpu0=resource.getrusage(resource.RUSAGE_SELF)
    def usage():
        r=resource.getrusage(resource.RUSAGE_SELF);return {'user_cpu_seconds':r.ru_utime-cpu0.ru_utime,'system_cpu_seconds':r.ru_stime-cpu0.ru_stime}
    start=time.monotonic();sampler=sampler_v3.get_sampler_provenance();assert sampler['implementation_sha256']==EXPECTED_SAMPLER_SHA256;plan=a.load(path);key=plan['asset_key'];out=HERE/'compiled_v3'/key
    mp=a.ROOT/plan['canonical_master_path'];sp=a.ROOT/plan['source_master_path'];rp=a.ROOT/plan['roof_master_path'];wp=a.ROOT/plan['window_contract_path']
    for p,k in [(mp,'canonical_master_sha256'),(sp,'source_sha256'),(rp,'roof_master_sha256'),(wp,'window_contract_sha256')]:assert a.sha(p)==plan[k]
    master=a.load(mp);original=a.load(sp);roof=a.load(rp);wc=a.load(wp);render=a.load(a.ROOT/wc['source_render_path']);assert a.sha(a.ROOT/wc['source_render_path'])==wc['source_render_sha256']
    assert master.get('grid_origin')==original.get('grid_origin')==[0,0,0] and wc['source_pitch_m']==.5
    prepare_start=time.monotonic();prepared={};prepared_keys={};prepared_sizes={}
    for role,source,request in [('original',original,{'pitch':.5}),('roof',roof,{'pitch':.05}),('canonical',master,{'pitch':.05})]:
        obj=sampler_v3.prepare_master(source,request,max_plan_bytes=128*1024**2);sampler_v3.assert_plan_matches(obj,source,request);prepared[role]=obj;prepared_keys[role]={'plan_key':obj.plan_key,'source_hash':obj.source_hash,'request_hash':obj.request_hash,'pitch_m':obj.pitch};prepared_sizes[role]=obj.retained_bytes
    preparation_seconds=time.monotonic()-prepare_start
    def sample(role,bounds):
        result=sampler_v3.compile_prepared(prepared[role],max_candidate_cells=140000,max_output_cells=140000,cell_bounds=bounds);expected={**sampler,**{k:v for k,v in prepared_keys[role].items() if k!='pitch_m'}};assert result['compiler_provenance']==expected;return result
    roof_materials=sorted({op['material'] for c in roof['components'] for op in c['operations'] if op['action']=='paint'})
    tools={str(Path(p).resolve().relative_to(a.ROOT)):a.sha(p) for p in [__file__,a.core.__file__,sampler_v3.__file__,reserved_io.__file__,reserved_io.previous.__file__,a.ROOT/'voxel_character/common/exact_sampling_v2.py',sys.modules[ReservationBook.__module__].__file__,H/'shared_output_budget.v2.json',seam.__file__,helpers.__file__,sys.modules[ExactOutside.__module__].__file__]}
    signature=a.core.digest({'plan':plan,'tools':tools,'sampler_provenance':sampler,'prepared_plan_keys':prepared_keys});progress={'asset_key':key,'signature':signature,'sampler_provenance':sampler,'prepared_plan_keys':prepared_keys,'plan_path':str(path.relative_to(a.ROOT)),'plan_sha256':a.sha(path),'tools':tools,'status':'running','finished_regions':[]}
    config=a.load(H/'shared_output_budget.v2.json');book=ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/p for p in config['retained_roots']],config['limit_bytes'],min_free_disk_bytes=config['min_free_disk_bytes'])
    scopes=[{'directory':str((HERE/'compiled_v3'/key).relative_to(a.ROOT)),'prefix':''},{'directory':str((HERE/'composed'/key).relative_to(a.ROOT)),'prefix':''},{'directory':str((HERE/'polygon_sources/emitted_qa').relative_to(a.ROOT)),'prefix':key}]
    identity={'asset_key':key,'plan_sha256':a.sha(path),'source_sha256':plan['source_sha256'],'canonical_master_sha256':plan['canonical_master_sha256'],'roof_master_sha256':plan['roof_master_sha256'],'tools':tools,'sampler_provenance':sampler,'prepared_plan_keys':prepared_keys,'signature':signature}
    reservation_key='facility_roi_v3:'+key
    book.reserve(reservation_key,scopes,reservation_cap_bytes,identity)
    book.acquire_writer(reservation_key)
    BUDGET=reserved_io.ReservedWriter(book,reservation_key,HERE,scopes,a.ROOT)
    BUDGET.check();out.mkdir(parents=True,exist_ok=True)
    reservation={'key':reservation_key,'identity':identity,'cap_bytes':reservation_cap_bytes,'scopes':scopes,'shared_config_path':str((H/'shared_output_budget.v2.json').relative_to(a.ROOT)),'shared_config_sha256':a.sha(H/'shared_output_budget.v2.json'),'release_policy':'Retain through final geometry QA and manifest closure; release only after all output is committed.'}
    checkpoint(out/'reservation.json',reservation)
    session_path=out/('session_%03d.json'%(len(list(out.glob('session_*.json')))+1))
    entries=wc.get('protected_component_entry_cuts',[])
    # Closed doors are original authored occupancy, so their aperture cuts are
    # not empty passage guards. Only explicitly empty original assembly cuts
    # and contract-protected through-paths may reject transition surfaces.
    entries+=original.get('assembly_cuts',[])
    outputs=[];calls=0;new_chunks=0
    try:
      for p in plan['plans']:
        region=p['region'];rid=region['id']
        if region_filter and rid not in region_filter:continue
        patch={'id':rid,'fine_cell_bounds':p['fine_cell_bounds'],'replacement_volume_master_m':region};groups=[];records=[];pixels=0
        for ci,cp in enumerate(p['chunks']):
            guard(start);target=out/f'{rid}.{ci:03d}.chunk.json.gz'
            if target.exists():
                result=a.load(target);assert result['signature']==signature
            else:
                cb=cp['sample_cell_bounds_with_one_cell_halo'];coarsecb={'min':[math.floor(v/10)-1 for v in cb['min']],'max':[math.ceil(v/10)+1 for v in cb['max']]};t=time.monotonic()
                coarse=sample('original',coarsecb)
                roofcell=sample('roof',cb);assert roofcell['candidate_cells']==cp['roof_only_candidate_visits'];roofhash=roofcell['payload_hash'];roofcells={tuple(r[:3]):r[5] for r in roofcell['cells']};del roofcell;gc.collect()
                fine=sample('canonical',cb);assert fine['candidate_cells']==cp['candidate_visits']
                outside=ExactOutside(fine,coarse,roofcells,plan['ordered_regions'],roof_materials)
                preview=helpers.owned_surface(fine,cp['owned_cell_bounds']);adapter=seam.build(render,fine,preview,patch,entries,owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=outside)
                result={'signature':signature,'sampler_provenance':sampler,'prepared_plan_keys':prepared_keys,'asset_key':key,'region':rid,'chunk':ci,'groups':helpers.merge_groups(adapter['fine_exterior_groups']+adapter['transition_groups']),'interface_pixel_counts':adapter['interface_pixel_counts'],'transition_quads':adapter['transition_quads'],'transition_unit_faces':adapter['transition_unit_faces'],'common_payload_sha256':fine['payload_hash'],'coarse_payload_sha256':coarse['payload_hash'],'roof_only_payload_sha256':roofhash,'fine_candidates':fine['candidate_cells'],'fine_cells':len(fine['cells']),'sample_cell_bounds':cb,'owned_cell_bounds':cp['owned_cell_bounds'],'source_shapes_cropped':False,'new_contact_occupancy_authored':False,'protected_entry_violations':adapter['protected_entry_interface_violations'],'seconds':round(time.monotonic()-t,4),'global_constraints_evaluated':False}
                del fine,coarse,roofcells,outside,preview,adapter;gc.collect();guard(start);checkpoint(target,result);calls+=3;new_chunks+=1
            groups+=result['groups'];pixels+=sum(result['interface_pixel_counts'].values());records.append({'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target)})
            progress.update(**usage(),status='running',region=rid,region_chunk=ci+1,region_chunks=len(p['chunks']),elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,additional_output_bytes=disk_bytes());checkpoint(out/'progress.json',progress)
            print(json.dumps({k:progress[k] for k in ['asset_key','region','region_chunk','region_chunks','elapsed_seconds','max_rss_kib']}),flush=True)
            if chunk_limit and new_chunks>=chunk_limit:raise TimeoutError('Requested subset chunk checkpoint reached')
        spans=[p['fine_cell_bounds']['max'][j]-p['fine_cell_bounds']['min'][j] for j in range(3)];assert pixels==2*sum(spans[i]*spans[j] for i,j in [(0,1),(1,2),(0,2)])
        target=out/(rid+'.render.json.gz');data={'schema':'riverstone.facility.finite_region.render.v1','asset_key':key,'region':region,'groups':helpers.merge_groups(groups),'chunks':records,'canonical_master_sha256':a.sha(mp),'collision_reference_changed':False,'source_shapes_cropped':False,'protected_entry_violations':0,'signature':signature};checkpoint(target,data)
        outputs.append({'region':region,'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target),'quad_count':sum(len(g['quads']) for g in data['groups']),'chunks':len(records)});progress['finished_regions'].append(rid)
      catalog={'schema':'riverstone.facility.finite_region.catalog.v1','asset_key':key,'source_master_path':plan['source_master_path'],'source_sha256':plan['source_sha256'],'source_render_path':wc['source_render_path'],'source_render_sha256':wc['source_render_sha256'],'canonical_master_path':plan['canonical_master_path'],'canonical_master_sha256':plan['canonical_master_sha256'],'window_contract_path':plan['window_contract_path'],'window_contract_sha256':plan['window_contract_sha256'],'roof_master_path':plan['roof_master_path'],'roof_master_sha256':plan['roof_master_sha256'],'ordered_regions':plan['ordered_regions'],'outputs':outputs,'roof_materials':roof_materials,'plan_path':str(path.relative_to(a.ROOT)),'plan_sha256':a.sha(path),'tools':tools,'signature':signature,'sampler_provenance':sampler,'prepared_plan_keys':prepared_keys,'output_reservation':reservation,'complete':len(outputs)==len(plan['ordered_regions']),'source_shapes_cropped':False,'collision_reference_changed':False,'source_contact_occupancy_authored':False,'global_constraints_evaluated':False,'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'new_common_calls':calls,'preparation_seconds':preparation_seconds,'prepared_retained_bytes_by_role':prepared_sizes,**usage()}
      checkpoint(out/('subset.catalog.json' if region_filter else 'catalog.json'),catalog);progress['status']='complete' if catalog['complete'] else 'subset_complete';checkpoint(out/'progress.json',progress);print(json.dumps({k:catalog[k] for k in ['asset_key','complete','elapsed_seconds','max_rss_kib','new_common_calls']}),flush=True)
    except Exception as e:
      progress.update(**usage(),status='paused',error=str(e),elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);checkpoint(out/'progress.json',progress);print(json.dumps(progress),flush=True);raise
    finally:
      checkpoint(session_path,{'asset_key':key,'signature':signature,'sampler_provenance':sampler,'prepared_plan_keys':prepared_keys,'status':progress.get('status'),'wall_seconds':time.monotonic()-start,**usage(),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'new_common_calls':calls,'new_committed_chunks':new_chunks,'committed_chunk_count':len(list(out.glob('*.chunk.json.gz'))),'preparation_seconds':preparation_seconds,'prepared_retained_bytes_by_role':prepared_sizes})
      prepared.clear();gc.collect();BUDGET.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('--region',action='append');p.add_argument('--chunk-limit',type=int);p.add_argument('--reservation-cap-bytes',type=int,required=True);args=p.parse_args();run(args.plan.resolve(),args.region,args.chunk_limit,args.reservation_cap_bytes)
