import sys,pathlib,json,hashlib,time,random,itertools
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r02_assembly_overlay import author as source
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream
from world_city.concept_city_v3.registered_topography.revisions.r10_density_reservoir import author as r10
from world_city.concept_city_v3.validation.owner_index_performance.excluded_memo import ExcludedMemo
mode=sys.argv[1] if len(sys.argv)>1 else 'parity';label=sys.argv[2] if len(sys.argv)>2 else mode
memo=ExcludedMemo(source);records=upstream._owners();exclusions=[source.DEFAULT_EXCLUDED_SOURCE_IDS,upstream.EXCLUDED,r10.EXCLUDED];counts=0;digest=hashlib.sha256();st=time.perf_counter();cpu=time.process_time()
if mode=='parity':
 for r in records:
  for ex in exclusions:
   old=source.is_excluded(r,ex);new=memo.is_excluded(r,ex);assert type(old) is bool and old is new
   digest.update(bytes([old]));counts+=1
 controls=[]
 for id in set(itertools.chain.from_iterable(exclusions)):
  for key in ('source_mass_id','owner_id','door_id'):
   for value in (id,id+':door',id+'x',id[:-1],':'+id):controls.append({key:value})
 controls += [{},{'owner_id':None},{'owner_id':[]},{'door_id':None},{'source_mass_id':42},{'source_mass_id':'B_REG_0191','owner_id':None}]
 for r in controls:
  for ex in exclusions+[[],(),iter(())]:
   def outcome(f,ex):
    try:return ('value',f(r,ex))
    except Exception as e:return ('error',type(e).__name__,str(e))
   a=outcome(source.is_excluded,list(ex));b=outcome(memo.is_excluded,list(ex));assert a==b,(r,a,b);counts+=1
 # A generator is deliberately not materialized or cached: short-circuit use is preserved.
 for f in [source.is_excluded,memo.is_excluded]:
  it=iter(['B_REG_0191','unused']);assert f({'source_mass_id':'B_REG_0191'},it) is True;assert list(it)==['unused'];counts+=1
 # Mutating a plain record/list between calls changes the key rather than retaining stale identity-based results.
 r={'owner_id':'NOT_EXCLUDED'};ex=['B_REG_0191'];assert memo.is_excluded(r,ex) is False;r['owner_id']='B_REG_0191';assert memo.is_excluded(r,ex) is True;ex[0]='OTHER';assert memo.is_excluded(r,ex) is False;counts+=3
else:
 sample=random.Random(202610180449).sample(records,5000);f=source.is_excluded if mode=='original' else memo.is_excluded
 for _ in range(4):
  for r in sample:
   for ex in exclusions:
    digest.update(bytes([f(r,ex)]));counts+=1
wall=time.perf_counter()-st;cpu=time.process_time()-cpu
report=dict(status='pass',mode=mode,label=label,calls=counts,query_wall_seconds=wall,query_cpu_seconds=cpu,result_digest=digest.hexdigest(),source_sha256=hashlib.sha256(pathlib.Path(source.__file__).read_bytes()).hexdigest(),memo_sha256=hashlib.sha256((H/'excluded_memo.py').read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),ordered_record_sha256=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest(),exclusion_lengths=list(map(len,exclusions)),exclusion_tuples=exclusions,cache_info=memo.cached.cache_info()._asdict(),activation='None; explicitly called test object only.',proof='For plain strings/None and a plain tuple/list of strings, the original reads only the three fields present in the cache key and the complete ordered exclusion tuple. A cache miss evaluates that exact original function. Nonstandard inputs use the original directly; values are captured on each call, not keyed by mutable object identity.',limits=['Repeated-call bounded microbenchmark; no full-export speedup or integration claim.','This optional cache is separate from the owner lookup activation hook.'])
(H/('excluded_'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(mode,counts,wall,report['result_digest'])
