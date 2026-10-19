"""Two frozen actual ROI chunks: old/v2 equality before separate warm timings.

Only this audit directory receives small summary reports. No engine/catalog,
checkpoint, original sampler, or source master is changed. 512 MiB hard AS cap.
"""
from __future__ import annotations
import cProfile,gc,gzip,hashlib,io,json,math,pathlib,pstats,resource,signal,statistics,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));signal.alarm(180)
from voxel_character.common import core,exact_sampling_v2 as v2,prepared_sampling_v3 as v3
B=HERE.parent/'facility_openings'/'batch_r01';sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime')]
import author as a
import compile_set as helpers
import seam_adapter as seam
from compile_source_contacts import ExactOutside

def load(path):
 path=pathlib.Path(path)
 with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as f:return json.load(f)
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def clean(r):return {k:v for k,v in r.items() if k not in ('compiler_source_hash','compiler_provenance')}
def timed(fn):
 t=time.perf_counter();r=fn();return r,time.perf_counter()-t
def rss():
 return next(int(l.split()[1]) for l in pathlib.Path('/proc/self/status').read_text().splitlines() if l.startswith('VmRSS:'))
def write_report(name,r):
 data=(json.dumps(r,indent=2)+'\n').encode();assert len(data)<5_000_000
 assert sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())+len(data)<10_000_000
 (HERE/name).write_bytes(data)

start=time.perf_counter();catalog_path=B/'compiled_v2/registered_castle_front_gate_wing/catalog.json';cat=load(catalog_path);assert cat['complete'];assert cat['sampler_provenance']==v2.get_sampler_provenance()
protected={str(catalog_path):sha(catalog_path)}
for field,hashfield in [('canonical_master_path','canonical_master_sha256'),('roof_master_path','roof_master_sha256'),('source_master_path','source_sha256'),('plan_path','plan_sha256'),('window_contract_path','window_contract_sha256'),('source_render_path','source_render_sha256')]:
 p=ROOT/cat[field];assert sha(p)==cat[hashfield];protected[str(p)]=sha(p)
for path in [pathlib.Path(core.__file__),pathlib.Path(v2.__file__)]:protected[str(path)]=sha(path)
source,roof,canonical=[load(ROOT/cat[k]) for k in ['source_master_path','roof_master_path','canonical_master_path']]
geometry_plan=load(ROOT/cat['plan_path']);wc=load(ROOT/cat['window_contract_path']);render=load(ROOT/cat['source_render_path'])
masters={'coarse':source,'roof':roof,'fine':canonical};requests={'coarse':{'pitch':.5},'roof':{'pitch':.05},'fine':{'pitch':.05}}
plans={};preparation={}
for name in masters:
 before_rss=rss();plan,seconds=timed(lambda:v3.prepare_master(masters[name],requests[name],max_plan_bytes=128*1024**2));plans[name]=plan
 assert v3.assert_plan_matches(plan,masters[name],requests[name]);assert plan.retained_bytes>=v3._deep_size(plan)
 preparation[name]={'seconds':seconds,'retained_plan_bytes':plan.retained_bytes,'rss_before_kib':before_rss,'rss_after_kib':rss(),'source_canonical_bytes':len(plan.source_snapshot_json),'source_hash':plan.source_hash,'request_hash':plan.request_hash,'plan_key':plan.plan_key,'operations':plan.operation_count}
 print('prepared',name,json.dumps(preparation[name]),flush=True)

refs={}
for out in cat['outputs']:
 p=ROOT/out['path'];assert sha(p)==out['sha256'];protected[str(p)]=out['sha256']
 for ref in load(p)['chunks']:
  chunk=load(ROOT/ref['path']);refs[(chunk['region'],chunk['chunk'])]=(ref,chunk)
selected=[('opening_000',0),('contact_000',0)];samples=[];chunk_proofs=[];saved_inputs=[]
for key in selected:
 ref,stored=refs[key];path=ROOT/ref['path'];assert sha(path)==ref['sha256'];protected[str(path)]=ref['sha256']
 p=next(p for p in geometry_plan['plans'] if p['region']['id']==key[0]);cp=p['chunks'][key[1]];bounds=cp['sample_cell_bounds_with_one_cell_halo'];coarsebounds={'min':[math.floor(x/10)-1 for x in bounds['min']],'max':[math.ceil(x/10)+1 for x in bounds['max']]}
 results={}
 for name in masters:
  kw={'cell_bounds':coarsebounds if name=='coarse' else bounds,'max_candidate_cells':140000,'max_output_cells':140000}
  old,oldseconds=timed(lambda:core.compile_master(masters[name],requests[name],**kw));fast,fastseconds=timed(lambda:v2.compile_master_v2(masters[name],requests[name],**kw));new,newseconds=timed(lambda:v3.compile_prepared(plans[name],**kw))
  assert clean(old)==clean(fast)==clean(new),[k for k in old if k!='compiler_source_hash' and old[k]!=new.get(k)]
  storedkey={'coarse':'coarse_payload_sha256','roof':'roof_only_payload_sha256','fine':'common_payload_sha256'}[name];assert new['payload_hash']==stored[storedkey]
  entry={'region':key[0],'chunk':key[1],'sample':name,'cell_bounds':kw['cell_bounds'],'candidates':new['candidate_cells'],'cells':len(new['cells']),'payload_hash':new['payload_hash'],'original_full_result_equal_v2_v3':True,'stored_v2_payload_equal':True,'independent_equality_pass_seconds':{'original':oldseconds,'v2':fastseconds,'prepared':newseconds}}
  samples.append(entry);saved_inputs.append((entry,name,kw));results[name]=new;del old,fast;gc.collect()
  print('equal',key,name,entry['cells'],entry['candidates'],flush=True)
 roofcells={tuple(r[:3]):r[5] for r in results['roof']['cells']};patch={'id':p['region']['id'],'fine_cell_bounds':p['fine_cell_bounds'],'replacement_volume_master_m':p['region']};entries=wc.get('protected_component_entry_cuts',[])+source.get('assembly_cuts',[])
 def downstream():
  outside=ExactOutside(results['fine'],results['coarse'],roofcells,geometry_plan['ordered_regions'],cat['roof_materials']);preview=helpers.owned_surface(results['fine'],cp['owned_cell_bounds']);adapter=seam.build(render,results['fine'],preview,patch,entries,owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=outside);groups=helpers.merge_groups(adapter['fine_exterior_groups']+adapter['transition_groups']);return adapter,groups
 (adapter,groups),seconds=timed(downstream)
 assert groups==stored['groups'];assert adapter['interface_pixel_counts']==stored['interface_pixel_counts'];assert adapter['protected_entry_interface_violations']==0
 chunk_proofs.append({'region':key[0],'chunk':key[1],'stored_chunk_path':ref['path'],'stored_chunk_sha256':ref['sha256'],'material_exterior_and_transition_groups_exact':True,'interface_pixel_counts_exact':True,'protected_entry_violations':0,'downstream_seconds':seconds})
 del results,roofcells,adapter,groups;gc.collect()

# Independent equality has now completed. Timings below are unprofiled, with
# garbage collection outside timed intervals; preparation remains separately
# reported. Three baseline/warm repeats, alternating order across samples.
assert all(x['original_full_result_equal_v2_v3'] for x in samples)
write_report('actual_equality.json',{'passed':True,'samples':samples,'chunk_proofs':chunk_proofs,'preparation':preparation,'provenance':v3.get_sampler_provenance(),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
for index,(entry,name,kw) in enumerate(saved_inputs):
 timings={'v2':[],'prepared':[]}
 for rep in range(3):
  order=('v2','prepared') if (rep+index)%2==0 else ('prepared','v2')
  for engine in order:
   gc.collect();result,seconds=timed(lambda:v2.compile_master_v2(masters[name],requests[name],**kw) if engine=='v2' else v3.compile_prepared(plans[name],**kw))
   assert result['payload_hash']==entry['payload_hash'] and result['candidate_cells']==entry['candidates'];timings[engine].append(seconds);del result
 medians={k:statistics.median(v) for k,v in timings.items()};entry['benchmark']={'unprofiled_seconds':timings,'median_seconds':medians,'warm_speedup_vs_v2':medians['v2']/medians['prepared']}
 print('bench',entry['region'],name,json.dumps(entry['benchmark']),flush=True)

# Confirm amortized execution never invokes validation, transform construction,
# shape preparation or shape-bound calculation, even for the zero-candidate roof.
profile=cProfile.Profile();profile.enable()
for entry,name,kw in saved_inputs:
 result=v3.compile_prepared(plans[name],**kw);assert result['payload_hash']==entry['payload_hash'];del result
profile.disable();stats=pstats.Stats(profile);forbidden={'validate_master','prepare_shape','shape_bounds','transform','compose'}
called=[{'file':k[0],'line':k[1],'function':k[2]} for k in stats.stats if k[2] in forbidden];assert not called,called
stream=io.StringIO();pstats.Stats(profile,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(30)
assert all(sha(path)==before for path,before in protected.items())
summary=[]
for region,_ in selected:
 entries=[s for s in samples if s['region']==region];baseline=sum(e['benchmark']['median_seconds']['v2'] for e in entries);warm=sum(e['benchmark']['median_seconds']['prepared'] for e in entries);downstream=next(p['downstream_seconds'] for p in chunk_proofs if p['region']==region)
 summary.append({'region':region,'sum_median_sampling_v2_seconds':baseline,'sum_median_sampling_prepared_seconds':warm,'sampling_speedup':baseline/warm,'same_downstream_seconds':downstream,'estimated_compute_plus_same_downstream_speedup':(baseline+downstream)/(warm+downstream),'scope':'sum of measured stage medians; no checkpoint IO and no whole-city throughput claim'})
report={'schema':'riverstone.prepared_sampling.actual_benchmark.v1','passed':True,'asset_key':cat['asset_key'],'selected_chunk_count':len(selected),'preparation':preparation,'total_retained_plan_bytes':sum(p.retained_bytes for p in plans.values()),'total_preparation_seconds':sum(p['seconds'] for p in preparation.values()),'samples':samples,'chunk_proofs':chunk_proofs,'summary':summary,'warm_profile_forbidden_prepare_calls':called,'warm_profile':stream.getvalue(),'provenance':v3.get_sampler_provenance(),'protected_input_files_unchanged':protected,'process_as_limit_bytes':512*1024**2,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'current_rss_kib':rss(),'wall_seconds':time.perf_counter()-start,'production_runtime_changed':False,'checkpoint_migration':False,'scope':'Two identical frozen gate ROI chunks only. Equality precedes separate unprofiled medians. All full master geometry remains; prepared-plan memory and startup cost included separately.'}
write_report('actual_benchmark.json',report);print(json.dumps({k:report[k] for k in ['passed','summary','total_retained_plan_bytes','total_preparation_seconds','peak_rss_kib','wall_seconds']},indent=2),flush=True);signal.alarm(0)
