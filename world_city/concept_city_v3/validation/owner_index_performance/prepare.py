import sys,pathlib,json,hashlib,math,random,collections
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream as s

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(pathlib.Path(p).relative_to(ROOT)),sha256=sha(p))
owners=s._owners();binding=dict(schema='riverstone.explicit_owner_prefilter_binding.v1',source=ref(s.__file__),geometry_helper=ref(s.geo.__file__),ordered_owners_sha256=hashlib.sha256(json.dumps(owners,sort_keys=True,separators=(',',':')).encode()).hexdigest(),owner_count=len(owners),original_index_cell_m=32,point_tolerance_m=1e-8,numeric_epsilon=s.geo.NUMERIC_EPSILON,activation='Explicit lookup object only; no module/file changes or auto installation.')
(H/'candidate_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
edges=set();vertices=set()
for r in owners:
 p=r['polygon_xz_m'];vertices.update(map(tuple,p))
 for a,b in zip(p,p[1:]+p[:1]):
  if math.dist(a,b)>s.geo.NUMERIC_EPSILON:edges.add(tuple(sorted([tuple(a),tuple(b)])))
edges=sorted(edges);vertices=sorted(vertices);rng=random.Random(202610180435)
bench=[]
for r in rng.sample(owners,12000):
 p=r['polygon_xz_m'];bench.append([sum(v[k] for v in p)/len(p) for k in (0,1)])
for a,b in rng.sample(edges,4000):
 x,z=(a[0]+b[0])/2,(a[1]+b[1])/2;L=math.dist(a,b);bench.append([x-(b[1]-a[1])/L*1e-5,z+(b[0]-a[0])/L*1e-5])
bench.extend([[rng.uniform(-600,600),rng.uniform(-560,680)] for _ in range(4000)])
fixture=dict(seed=202610180435,vertices=vertices,edges=edges,boundary_offsets_m=[-1e-5,-1.1e-8,0,1.1e-8,1e-5],benchmark_points=bench,expected_full_parity_points=len(vertices)+len(edges)*5+len(bench))
(H/'fixtures.json').write_text(json.dumps(fixture,separators=(',',':'))+'\n');print(dict(owners=len(owners),edges=len(edges),vertices=len(vertices),full_parity_points=fixture['expected_full_parity_points'],bench_points=len(bench)))
