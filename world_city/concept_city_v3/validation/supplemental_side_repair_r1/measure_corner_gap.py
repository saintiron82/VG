import sys,pathlib,json,math,hashlib
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import author as s, approaches as a,landings as l
f=json.loads((H/'targeted_original_endpoint_failures.json').read_text())['failures'][0];origin=[f['edge_xyz_m'][0][0],f['edge_xyz_m'][0][2]]
def local(p):return [[q[k]-origin[k] for k in (0,1)] for q in p]
def world(p):return [[q[k]+origin[k] for k in (0,1)] for q in p]
def area(p):return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))/2
# Subtract locally to retain the known sub-millimetre finite corner.
def signed(p):return sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))
def cross(a,b,p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
def clip(p,a,b,sign):
 if not p:return []
 out=[]
 for u,v in zip(p,p[1:]+p[:1]):
  cu=sign*cross(a,b,u);cv=sign*cross(a,b,v);iu=cu>=0;iv=cv>=0
  if iu:out.append(u)
  if iu!=iv:
   t=cu/(cu-cv);out.append([u[k]+t*(v[k]-u[k]) for k in (0,1)])
 clean=[]
 for q in out:
  if not clean or math.dist(q,clean[-1])>1e-14:clean.append(q)
 if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-14:clean.pop()
 return clean if len(clean)>2 and area(clean)>1e-18 else []
def difference(subject,cutter):
 sign=1 if signed(cutter)>0 else -1;rest=subject;out=[]
 for a,b in zip(cutter,cutter[1:]+cutter[:1]):
  p=clip(rest,a,b,-sign)
  if p:out.append(p)
  rest=clip(rest,a,b,sign)
  if not rest:break
 return out
b=[origin[0]-.002,origin[1]-.002,origin[0]+.002,origin[1]+.002];box=[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]
mask=local(f['outside_owner']['polygon_xz_m']);parts=[mask]
for u,v in zip(local(box),local(box)[1:]+local(box)[:1]):parts=[clip(p,u,v,1) for p in parts];parts=[p for p in parts if p]
clipped_mask_area=sum(map(area,parts));ids=sorted(l.INDEX.candidates(box))
for i in ids:
 t=local(l.TRIANGLES[i]['polygon_xz_m']);parts=[piece for p in parts for piece in difference(p,t)]
parts=[p for p in parts if area(p)>1e-16]
road=s.owner_at(*(origin[k]+f['normal_xz_m'][k] for k in (0,1)))
report=dict(status='measured_geometry_only',local_bounds_xz_m=b,original_mask_owner_id=f['outside_owner']['owner_id'],underlying_endpoint_road=road,corner_gap_polygons_xz_m=[world(p) for p in parts],corner_gap_area_m2=sum(map(area,parts)),touches_local_crop=any(abs(abs(v[k])-.002)<1e-10 for p in parts for v in p for k in (0,1)),all_gap_vertices_within_endpoint_road=all(a.geo.point_in_convex_polygon(q,road['polygon_xz_m'],1e-9) for p in parts for q in world(p)),clipped_mask_area_m2=clipped_mask_area,nearby_triangle_count=len(ids),source_profile_sha256=a.SHA)
(H/'corner_gap_geometry.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
