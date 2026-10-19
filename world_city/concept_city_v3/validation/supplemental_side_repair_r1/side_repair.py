"""One finite boundary subdivision; unchanged original side algorithm thereafter.

Requires the terrain's explicit restored-road ownership/profile callbacks.
No module mutation, landing extrapolation, broad mask change or error swallowing.
"""
import hashlib,json,math,types
from pathlib import Path
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import approaches as original
HERE=Path(__file__).resolve().parent
DATA_PATH=HERE/'finite_road_corner_restoration.json'
DATA_SHA256='5efb51b1ec563fb99fcf8415290864d3301294ce97698ed32dae5682bac57496'
APPROACHES_SHA256='2063e0ab0448ff294559a60ca8ce36c532fbdfe84a188bca6b789cb0180ccff0'

def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _data():
 if _sha(DATA_PATH)!=DATA_SHA256 or _sha(original.__file__)!=APPROACHES_SHA256:raise ValueError('Finite side repair source binding changed')
 data=json.loads(DATA_PATH.read_text())
 if data['source_profile_sha256']!=original.SHA:raise ValueError('Recovered profile binding changed')
 return data

def _on_segment(point,a,b,tolerance=1e-9):
 dx=b[0]-a[0];dz=b[2]-a[2];L2=dx*dx+dz*dz
 if L2==0:return None
 t=((point[0]-a[0])*dx+(point[2]-a[2])*dz)/L2
 if -1e-10<=t<=1+1e-10 and math.hypot(point[0]-a[0]-t*dx,point[2]-a[2]-t*dz)<=tolerance:return t
 return None

def side_records(bounds_xz_m,outside_owner,outside_height,audit=None):
 data=_data();patch=data['restorations'][0];seam=data['source_landing_vertices'][0];edge=data['original_failed_edge_xyz_m'];subdivisions=[]
 # The ownership restoration must already be active in the caller. Do not
 # quietly query an unrelated underlying plane when the finite profile is absent.
 mid=[sum(q[k] for q in patch['polygon_xz_m'])/3 for k in (0,1)]
 effective=outside_owner(*mid)
 if effective['owner_id']!=patch['owner_id']:raise ValueError('Explicit finite restored road owner is not active')
 for v in patch['triangle_xyz_m']:
  if abs(outside_height(effective,v[0],v[2])-v[1])>1e-9:raise ValueError('Restored corner profile differs from shared finite triangle')
 def domains(bounds):
  records=original.supplemental_surface_domains(bounds);out=[]
  for record in records:
   if record['owner_id']!=data['source_approach_id']:out.append(record);continue
   vertices=record['vertices_xyz_m'];new=[]
   for a,b in zip(vertices,vertices[1:]+vertices[:1]):
    new.append(a);t=_on_segment(seam,a,b)
    if t is None or t<=1e-10 or t>=1-1e-10:continue
    if _on_segment(a,*edge) is None or _on_segment(b,*edge) is None:continue
    v=[seam[0],original.point_y(record['triangle_xyz_m'],seam[0],seam[2]),seam[2]]
    new.append(v);subdivisions.append(dict(source_approach_id=record['owner_id'],original_edge_xyz_m=[a,b],inserted_point_xyz_m=v,existing_landing_point_xyz_m=seam,top_vs_landing_height_error_m=abs(v[1]-seam[1])))
   out.append(dict(record,vertices_xyz_m=new))
  return out
 # A private globals dictionary changes only the boundary-iteration data.
 # The function code, original mask tests, height calls, thresholds and IDs
 # remain exactly the original implementation. No function/module is patched.
 namespace=dict(original.side_records.__globals__);namespace['supplemental_surface_domains']=domains
 evaluator=types.FunctionType(original.side_records.__code__,namespace,original.side_records.__name__,original.side_records.__defaults__,original.side_records.__closure__)
 result=evaluator(bounds_xz_m,outside_owner,outside_height)
 if audit is not None:audit.update(dict(schema='riverstone.finite_side_subdivision.v1',restoration_sha256=DATA_SHA256,original_side_module_sha256=APPROACHES_SHA256,original_function_code_unchanged=evaluator.__code__ is original.side_records.__code__,side_count=len(result),subdivisions=subdivisions,callbacks=dict(owner_module=getattr(outside_owner,'__module__',None),height_module=getattr(outside_height,'__module__',None)),support_status='finite source side geometry only; native and capsule support unverified'))
 return result
