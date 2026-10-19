"""Fresh-process effective-layer parity fixture. Run only on sealed target bytes.

Modes original / owner / both. This script writes only its own report files.
"""
import sys,pathlib,json,hashlib,importlib,math,random,time,contextlib
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
# Explicit inputs avoid accidentally binding a moving revision.
mode,module_name,contract_arg,contract_sha,label=sys.argv[1:]
assert mode in ('original','owner','both')
contract_path=ROOT/contract_arg
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(contract_path)==contract_sha,'Unsealed or changed target contract'
read_paths=set()
def audit(event,args):
 if event!='open' or not args or not isinstance(args[0],(str,bytes,pathlib.Path)):return
 try:p=pathlib.Path(args[0]).resolve()
 except (TypeError,ValueError):return
 if ROOT in p.parents and p.suffix in ('.py','.json') and not (len(args)>1 and isinstance(args[1],str) and any(c in args[1] for c in 'wax+')):read_paths.add(p)
sys.addaudithook(audit)
mod=importlib.import_module(module_name)
contract_data=json.loads(contract_path.read_text());target_path=pathlib.Path(mod.__file__).resolve();city=ROOT/'world_city/concept_city_v3';target_key=str(target_path.relative_to(city))
assert contract_data.get('module_sources',{}).get(target_key)==sha(target_path),'Target author bytes do not match sealed contract'
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream
from world_city.concept_city_v3.registered_topography.revisions.r02_assembly_overlay import author as excluded_source
from world_city.concept_city_v3.validation.owner_index_performance.activate_r5 import activate
from world_city.concept_city_v3.validation.owner_index_performance.excluded_memo import ExcludedMemo
for m in tuple(sys.modules.values()):
 p=getattr(m,'__file__',None)
 if p and ROOT in pathlib.Path(p).resolve().parents and pathlib.Path(p).suffix=='.py':read_paths.add(pathlib.Path(p).resolve())
read_paths.add(contract_path.resolve());before={str(p.relative_to(ROOT)):sha(p) for p in sorted(read_paths)}
# Deterministic independent strata: global tiles, each upstream owner kind,
# new target owners, collar quadrants and known prior counterexamples.
T=set()
def tile(p):return (math.floor(p[0]/8)*8,math.floor(p[1]/8)*8)
def center(r):return [sum(p[k] for p in r['polygon_xz_m'])/len(r['polygon_xz_m']) for k in (0,1)]
rng=random.Random(202610180503)
for _ in range(40):T.add((rng.randrange(-66,66)*8,rng.randrange(-66,82)*8))
by_kind={}
for r in upstream._owners():by_kind.setdefault(r['kind'],[]).append(r)
for kind,rs in sorted(by_kind.items()):T.add(tile(center(rs[len(rs)//2])))
new=list(getattr(mod,'OWNERS',[]))
for r in rng.sample(new,min(24,len(new))):T.add(tile(center(r)))
if hasattr(mod,'COLLAR_BOUNDS'):
 b=mod.COLLAR_BOUNDS
 for x in [b[0],(b[0]+b[2])/2,b[2]]:
  for z in [b[1],(b[1]+b[3])/2,b[3]]:T.add(tile([x,z]))
T.update([(-256,-112),(320,304),(328,304),(320,312),(328,312),(-248,-8)])
# Material-only aliases and shared source-plane metadata are compared too.
original_excluded=excluded_source.is_excluded;installed_excluded=None;memo=None;activation=None;reports=[];failures=[];started=time.perf_counter()
try:
 if mode in ('owner','both'):activation=activate(upstream,opt_in=True,export_revision='r5')
 if mode=='both':memo=ExcludedMemo(excluded_source);installed_excluded=memo.is_excluded;excluded_source.is_excluded=installed_excluded
 for n,(x,z) in enumerate(sorted(T)):
  b=[x,z,x+8,z+8]
  try:
   records=mod.surface_domains(b);up=[];points=[]
   for r in records:
    p=r['polygon_xz_m'];points.append(center(r));points.extend(p)
    for a,c in zip(p,p[1:]+p[:1]):
     L=math.dist(a,c)
     if L>1e-7:
      m=[(a[k]+c[k])/2 for k in (0,1)];v=[-(c[1]-a[1])/L*1e-5,(c[0]-a[0])/L*1e-5]
      points.extend([[m[k]+s*v[k] for k in (0,1)] for s in (-1,0,1)])
    if r.get('render_land',True):up.append([[q[0],mod.surface_height_at(r,*q),q[1]] for q in p])
   owners=[mod.owner_at(*p) for p in points];sides=mod.retaining_interfaces(b,records)
   value=dict(records=records,upward=up,owners=owners,sides=sides)
   digest=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
   reports.append(dict(bounds=b,digest=digest,records=len(records),owner_queries=len(points),interfaces=len(sides),kinds=sorted({r['kind'] for r in records})))
  except Exception as e:
   failures.append(dict(bounds=b,error=repr(e)));raise
  if n%20==0:print(mode,n+1,'/',len(T),round(time.perf_counter()-started,2),flush=True)
 # The actual repaired-corner supplemental path is covered without replaying
 # every city approach in each performance run.
 sb=[-244.37,-2.38,-244.23,-2.22];supp=mod.supplemental_side_records(sb);supp_digest=hashlib.sha256(json.dumps(supp,sort_keys=True,separators=(',',':')).encode()).hexdigest()
finally:
 if memo is not None:
  assert excluded_source.is_excluded is installed_excluded,'Unexpected exclusion callable replacement'
  excluded_source.is_excluded=original_excluded
 if activation is not None:activation.restore()
for p,h in before.items():assert sha(ROOT/p)==h,'Changed input '+p
for p in read_paths:
 if p.is_file() and str(p.relative_to(ROOT)) not in before:before[str(p.relative_to(ROOT))]=sha(p)
result=dict(schema='riverstone.effective_layer_owner_acceleration_parity.v1',status='pass_run_complete',mode=mode,target_module=module_name,target_contract_sha256=contract_sha,case_count=len(reports),cases=reports,total_owner_queries=sum(r['owner_queries'] for r in reports),supplemental_corner_side_count=len(supp),supplemental_corner_digest=supp_digest,activation=None if activation is None else activation.report,exclusion_memo_cache=None if memo is None else memo.cached.cache_info()._asdict(),exclusion_restored_exact_original=excluded_source.is_excluded is original_excluded,verified_inputs=before,checker_sha256=sha(__file__),wall_seconds=time.perf_counter()-started,failures=failures,limits=['Representative effective-layer parity only; independent geometric/native/traversal acceptance remains separate.','Timing includes imports, guards, preparation and cached API work; no export speedup inference.'])
(H/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(mode,'DONE',len(reports),result['total_owner_queries'],flush=True)
