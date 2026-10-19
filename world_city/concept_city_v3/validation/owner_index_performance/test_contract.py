"""Read-only candidate API/binding checks; fake sources never mutate upstream."""
import sys,pathlib,json,hashlib,types,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream as s
from world_city.concept_city_v3.validation.owner_index_performance.prefilter import OwnerLookup
lookup=OwnerLookup(s);checks=[]
def check(condition,name):
 assert condition,name
 checks.append(name)
points=json.loads((H/'fixtures.json').read_text())['benchmark_points'][:100]+[[100000.,100000.],[-100000.,-100000.],[0.,0.],[-0.,0.]]
for p in points:
 old=s.owner_at(*p);new=lookup.owner_at(*p)
 check(old==new,'cached-result:'+str(p))
 check(lookup.owner_at(*p) is new,'cached-object:'+str(p))
check(lookup.owner_at.cache_info().hits>=len(points),'LRU hits on repeated calls')
check(lookup.owner_at.cache_info().maxsize==262144,'LRU size unchanged')
check(lookup.owners is s._owners() and lookup.index is s.INDEX,'same owner and index objects')
base=dict(__file__=s.__file__,_owners=s._owners,INDEX=s.INDEX,geo=s.geo)
changed=list(s._owners());changed[0]=dict(changed[0],material_hint='DELIBERATE_TEST_ONLY_CHANGED_SNAPSHOT')
fake_cases=[('source bytes',dict(__file__=__file__)),('ordered owner snapshot',dict(_owners=lambda:changed)),('index cell size',dict(INDEX=types.SimpleNamespace(cell_m=16)))]
for label,overrides in fake_cases:
 try:OwnerLookup(types.SimpleNamespace(**dict(base,**overrides)))
 except ValueError:check(True,'reject changed '+label)
 else:raise AssertionError('accepted changed '+label)
report=dict(status='pass',checks=len(checks),check_names=checks,candidate_sha256=hashlib.sha256((H/'prefilter.py').read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),source_modified=False)
(H/'contract_test_report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(checks))
