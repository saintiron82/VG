"""Exercise exact fallback/cull semantics without mutating any source module."""
import sys,pathlib,json,hashlib,types,collections
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r13_precinct_interfaces import materials as terrain
from world_city.concept_city_v3.registered_integration.r4 import fast_interfaces as fast

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def rect(x0,x1,owner,render=True):return dict(owner_id=owner,kind='synthetic_native_hole' if not render else 'ground',render_land=render,polygon_xz_m=[[x0,0],[x1,0],[x1,1],[x0,1]])
def compare(name,width,render=True):
 def owner(x,z):
  if abs(x)<width:return rect(-width,width,'STRIP',render)
  return rect(-1,1,'LEFT' if x<0 else 'RIGHT')
 def height(r,x,z):return {'LEFT':0.,'STRIP':.5,'RIGHT':1.}[r['owner_id']]
 oldglobals=dict(terrain.retaining_interfaces.__globals__,owner_at=owner,surface_height_at=height)
 newglobals=dict(fast.retaining_interfaces.__globals__,base=types.SimpleNamespace(owner_at=owner,surface_height_at=height),STATS=collections.Counter())
 old=types.FunctionType(terrain.retaining_interfaces.__code__,oldglobals,argdefs=terrain.retaining_interfaces.__defaults__)
 new=types.FunctionType(fast.retaining_interfaces.__code__,newglobals,argdefs=fast.retaining_interfaces.__defaults__)
 records=[rect(-1,-width,'LEFT'),rect(-width,0,'STRIP',render),rect(0,width,'STRIP',render),rect(width,1,'RIGHT')]
 a=old([-1,0,1,1],records);b=new([-1,0,1,1],records);ids={r['id'] for r in b}
 return dict(id=name,width_each_side_m=width,strip_render_land=render,exact_equal=a==b,reference_interface_count=len(a),fast_interface_count=len(b),missing_interfaces=[r for r in a if r['id'] not in ids],records=records,stats=dict(newglobals['STATS']))
results=[compare('wide_same_owner_control',.1),compare('thin_same_owner_sliver',1e-6),compare('wide_native_hole_control',.1,False),compare('thin_native_hole_sliver',1e-6,False)]
assert results[0]['exact_equal'] and results[2]['exact_equal']
report=dict(schema='riverstone.fast_interface_adversarial_controls.v1',candidate_sha256=sha(fast.__file__),reference_sha256=sha(terrain.prior.__file__),checker_sha256=sha(__file__),status='general_equivalence_counterexamples' if any(not r['exact_equal'] for r in results) else 'controls_pass',results=results,interpretation='Finite valid synthetic owner partitions expose the exact reference sampler behavior. These do not assert a corresponding real-city defect. A normal offset1e-5 can jump across a thin shared owner/hole, so topological adjacency alone does not prove output equivalence.',recommendation='Retain the original fallback when either normal sample leaves the adjoining polygon(s); test source-owner parity for any proposed guard.' )
(H/'adversarial_controls.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status']);print([(r['id'],r['exact_equal'],r['reference_interface_count'],r['fast_interface_count']) for r in results])
