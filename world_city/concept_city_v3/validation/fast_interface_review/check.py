"""Independent exact-output parity, including thin-domain adversarial controls."""
import sys,pathlib,json,hashlib,math,random,collections,types,importlib
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r13_precinct_interfaces import materials as terrain
from world_city.concept_city_v3.registered_integration.r4 import fast_interfaces as fast

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(pathlib.Path(p).relative_to(ROOT)),sha256=sha(p))
inputs=[ref(fast.__file__),ref(terrain.__file__),ref(terrain.prior.__file__)];seal=json.loads((terrain.HERE/'material_freeze.json').read_text());inputs.append(ref(terrain.HERE/'material_freeze.json'))
for p,h in seal['files'].items():assert sha(terrain.HERE/p)==h;inputs.append(ref(terrain.HERE/p))
rng=random.Random(202610180425);tiles=collections.defaultdict(set)
def add(p,reason):
 x,z=[math.floor(v/8)*8 for v in p];tiles[(x,z,x+8,z+8)].add(reason)
def center(p):return [sum(q[k] for q in p)/len(p) for k in (0,1)]
# Stratify real finite owners and finite water, then add deterministic random tiles.
pools=collections.defaultdict(list)
for r in terrain.prior.R04._owners()+terrain.prior.OWNERS:pools[r['kind']].append(r)
for kind,rs in sorted(pools.items()):
 for r in rng.sample(rs,min(6,len(rs))):
  p=r['polygon_xz_m'];add(center(p),'owner:'+kind);i=rng.randrange(len(p));a,b=p[i],p[(i+1)%len(p)];add([(a[k]+b[k])/2 for k in (0,1)],'boundary:'+kind)
for r in rng.sample(terrain.finite_water_polygons(),32):
 p=r['polygon_xz_m'];add(center(p),'finite_water');a,b=p[0],p[1];add([(a[k]+b[k])/2 for k in (0,1)],'finite_water_edge')
for r in rng.sample(terrain.REGIONS,32):add(center(r['polygon_xz_m']),'material_boundary')
for _ in range(128):add([rng.uniform(-530,530),rng.uniform(-530,656)],'uniform_random')
for p in [[324.8,312.9],[-260,-153],[-31,-330],[138.8,562.1],[139,570],[145,601],[154,654],[350,210],[300,230]]:add(p,'named_regression')
results=[];failures=[];kinds=collections.Counter();fast.STATS.clear()
for n,(bounds,reasons) in enumerate(sorted(tiles.items())):
 records=terrain.surface_domains(bounds);kinds.update(r['kind'] for r in records);expected=terrain.retaining_interfaces(bounds,records);actual=fast.retaining_interfaces(bounds,records);same=actual==expected
 row=dict(bounds=bounds,reasons=sorted(reasons),record_count=len(records),reference_interfaces=len(expected),fast_interfaces=len(actual),exact_list_equal=same);results.append(row)
 if not same:
  old={r['id']:r for r in expected};new={r['id']:r for r in actual};failure=dict(**row,missing=[old[k] for k in old.keys()-new.keys()],extra=[new[k] for k in new.keys()-old.keys()],changed=[dict(reference=old[k],fast=new[k]) for k in old.keys()&new.keys() if old[k]!=new[k]],records=records);failures.append(failure)
  (HERE/'first_real_failure.json').write_text(json.dumps(failure,indent=2)+'\n');print('REAL FAILURE',bounds,len(failure['missing']),len(failure['extra']),flush=True)
 if n%40==0:print('REAL TILE',n+1,'/',len(tiles),'failures',len(failures),flush=True)
report=dict(schema='riverstone.independent_fast_retaining_interface_parity.v1',status='fail_actual_output_parity' if failures else 'pass_bounded_actual_output_parity',inputs=inputs,checker=ref(__file__),random_seed=202610180425,tiles=len(results),observed_record_kinds=dict(kinds),fast_stats=dict(fast.STATS),failures=failures,tile_results=results,limits=['Exact observed dictionary/list parity only on the persisted finite tile fixtures.','Cache-warmed evaluations are not a measured speedup claim.','No navigation, capsule, wall support, complete geometry or whole-city theorem claimed.'])
for f in inputs:assert sha(ROOT/f['path'])==f['sha256'],'source changed during audit'
p=HERE/('parity_'+sha(fast.__file__)[:12]+'_'+sha(__file__)[:12]+'.json');p.write_text(json.dumps(report,indent=2)+'\n');print('REPORT',p,report['status'],flush=True)
