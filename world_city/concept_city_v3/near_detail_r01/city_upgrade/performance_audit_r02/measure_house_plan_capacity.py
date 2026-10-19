"""Sampling-free capacity measurement for the next explicitly selected house."""
import gzip,hashlib,json,pathlib,resource,signal,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));signal.alarm(60)
from voxel_character.common import prepared_sampling_v3 as v3
SOURCE=ROOT/'world_city/concept_city_v3/near_detail_r01/city_upgrade/house_extensions/generated/masters/ordinary_r2_2b48237662aa54.master.json.gz'
EXPECTED='e3e71e2a12817192ffeaee67402023283be9d26bc9297d2cd64d3f8457c257f4';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE)==EXPECTED
with gzip.open(SOURCE,'rt') as f:master=json.load(f)
plans=[];results=[]
for pitch in (.05,.1):
 request={'pitch':pitch};start=time.perf_counter();plan=v3.prepare_master(master,request,max_plan_bytes=128*1024**2);seconds=time.perf_counter()-start;assert v3.assert_plan_matches(plan,master,request);plans.append(plan)
 results.append({'pitch':pitch,'plan_key':plan.plan_key,'source_hash':plan.source_hash,'request_hash':plan.request_hash,'retained_plan_bytes':plan.retained_bytes,'operations':plan.operation_count,'constraints':len(plan._constraints),'source_canonical_bytes':len(plan.source_snapshot_json),'preparation_seconds':seconds})
assert sha(SOURCE)==EXPECTED
report={'schema':'riverstone.prepared_sampling.house_capacity.v1','passed':True,'asset_key':'ordinary_r2_2b48237662aa54','source_path':str(SOURCE.relative_to(ROOT)),'source_file_sha256':EXPECTED,'source_modified':False,'sampling_calls':0,'geometry_cropped':False,'plans':results,'combined_retained_plan_bytes':sum(p.retained_bytes for p in plans),'combined_preparation_seconds':sum(r['preparation_seconds'] for r in results),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'process_as_limit_bytes':512*1024**2,'provenance':v3.get_sampler_provenance()}
(HERE/'house_plan_capacity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));signal.alarm(0)
