import sys,pathlib,json,hashlib,math,time,collections,itertools,os
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT));mode=sys.argv[1];label=sys.argv[2] if len(sys.argv)>2 else mode
import_start=time.perf_counter();from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream as s
from world_city.concept_city_v3.validation.owner_index_performance.prefilter import OwnerLookup
import_seconds=time.perf_counter()-import_start

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
inputs={str(p.relative_to(ROOT)):sha(p) for p in [H/'prefilter.py',H/'candidate_binding.json',H/'fixtures.json',pathlib.Path(s.__file__),pathlib.Path(s.geo.__file__)]};fixtures=json.loads((H/'fixtures.json').read_text());st=time.perf_counter();owners=s._owners();lookup=OwnerLookup(s) if mode!='original' else None;setup_seconds=time.perf_counter()-st;owner_index={id(r):i for i,r in enumerate(owners)};base=s.owner_at.__wrapped__;failures=[];result=hashlib.sha256();count=0
if mode=='parity':
 def samples():
  for p in fixtures['vertices']:yield p
  for a,b in fixtures['edges']:
   L=math.dist(a,b);m=[(a[k]+b[k])/2 for k in (0,1)];n=[-(b[1]-a[1])/L,(b[0]-a[0])/L]
   for offset in fixtures['boundary_offsets_m']:yield [m[k]+offset*n[k] for k in (0,1)]
  yield from fixtures['benchmark_points']
 points=samples()
else:points=iter(fixtures['benchmark_points'])
wall_start=time.perf_counter();cpu_start=time.process_time()
for point in points:
 if mode=='parity':
  old=base(*point);new=lookup.lookup(*point)
  if old is not new and old!=new:
   failure=dict(point_xz_m=point,original=old,candidate=new);failures.append(failure);(H/'first_failure.json').write_text(json.dumps(failure,indent=2)+'\n');print('FAILURE',point,flush=True);break
  value=owner_index.get(id(old),-1)
 else:
  r=(base if mode=='original' else lookup.lookup)(*point);value=owner_index.get(id(r),-1)
 result.update(str(value).encode()+b'\n');count+=1
 if mode=='parity' and count%50000==0:print('PARITY',count,'/',fixtures['expected_full_parity_points'],'elapsed',round(time.perf_counter()-wall_start,2),flush=True)
wall=time.perf_counter()-wall_start;cpu=time.process_time()-cpu_start
for p,h in inputs.items():assert sha(ROOT/p)==h,'Changed input '+p
report=dict(schema='riverstone.owner_lookup_bounded_performance.v1',mode=mode,label=label,pid=os.getpid(),status='failed' if failures else 'pass',inputs=inputs,runner_sha256=sha(__file__),queries=count,expected_queries=fixtures['expected_full_parity_points'] if mode=='parity' else len(fixtures['benchmark_points']),output_digest_sha256=result.hexdigest(),import_seconds=import_seconds,index_prepare_seconds=setup_seconds,query_wall_seconds=wall,query_cpu_seconds=cpu,failures=failures,cache_policy='Call original.__wrapped__ / candidate.lookup directly; no prior query cache and no warmed baseline-first timing in this process.',limits=['Microbenchmark and bounded direct owner API parity only.','No production installation, current-export change, or whole-export speedup claim.','Original32m bucket candidate set/order and original edge predicates are preserved.'])
(H/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','limits']},indent=2),flush=True)
