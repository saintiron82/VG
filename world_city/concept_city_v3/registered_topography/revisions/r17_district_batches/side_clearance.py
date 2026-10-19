"""Exact retained terrain-face / walking-clear-volume intersections.

Vertical faces have zero XZ area but real collision area. This checker clips
source 3D polygons by convex plan boundaries and a finite floor/head envelope;
it does not triangulate, replace or hide any source face.
"""
import math
from . import author as a

# A near-vertical physical side remains a side regardless of triangle size.
# General sloped tops belong to the top/grade checker, not both ownership paths.
MAX_SIDE_NORMAL_Y=1e-3

def physical_side(triangle,material):
 area=area3d(triangle)
 if area<=1e-10:return False
 return material=='bank' or abs(a.normal_y(triangle))/(2*area)<=MAX_SIDE_NORMAL_Y

def halfspace(poly,value):
 if not poly:return[]
 out=[];prev=poly[-1];pv=value(prev)
 for cur in poly:
  cv=value(cur);pin=pv>=0;cin=cv>=0
  if pin!=cin:
   t=pv/(pv-cv);out.append([prev[k]+t*(cur[k]-prev[k])for k in range(3)])
  if cin:out.append(cur)
  prev,pv=cur,cv
 return out

def area3d(poly):
 if len(poly)<3:return 0.
 result=0.;p=poly[0]
 for b,c in zip(poly[1:],poly[2:]):
  u=[b[i]-p[i]for i in range(3)];v=[c[i]-p[i]for i in range(3)];w=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];result+=math.sqrt(sum(x*x for x in w))*.5
 return result

def clip_clear_volume(triangle,polygon,plane,headroom_m=2.2,contact_allowance_m=1e-5):
 sign=1 if a.geo.signed_polygon_area(polygon)>0 else-1;out=list(triangle)
 for p,q in zip(polygon,polygon[1:]+polygon[:1]):
  out=halfspace(out,lambda v:sign*a.geo._cross(p,q,[v[0],v[2]]))
  if not out:return[]
 height=lambda v:v[1]-a.common.height(plane,[v[0],v[2]])
 out=halfspace(out,lambda v:height(v)-contact_allowance_m)
 return halfspace(out,lambda v:headroom_m-height(v))

class SideIndex:
 def __init__(self,scene,windows=None):
  self.rows=[];self.index=a.geo._SpatialIndex(16);wi=None
  if windows:
   wi=a.geo._SpatialIndex(32)
   for i,p in enumerate(windows):wi.add(i,p)
  for material,vs in scene['surfaces'].items():
   if material=='water':continue
   for j in range(0,len(vs),3):
    t=vs[j:j+3]
    p=[[v[0],v[2]]for v in t]
    if wi is not None and not wi.candidates(p):continue
    if not physical_side(t,material):continue
    r=dict(material=material,triangle_index=j//3,source_triangle_sha256=a.canonical_sha(t),vertices_xyz_m=t,projection_xz_m=p)
    self.index.add(len(self.rows),p);self.rows.append(r)
 def audit(self,owners):
  hits=[];tested=0
  for owner in owners:
   p=owner['polygon_xz_m']
   if 'plane_y_xz_m' in owner:plane=owner['plane_y_xz_m']
   elif 'floor_y_m' in owner:plane=[0.,0.,owner['floor_y_m']]
   else:raise ValueError('Explicit walking floor/profile required')
   if len(plane)!=3 or not all(math.isfinite(v) for v in plane):raise ValueError('Invalid walking plane')
   for i in self.index.candidates(p):
    tested+=1;r=self.rows[i];q=clip_clear_volume(r['vertices_xyz_m'],p,plane,owner.get('headroom_m',2.2));area=area3d(q)
    if area>1e-8:hits.append(dict(owner_id=owner['id'],material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],intersection_vertices_xyz_m=q,clear_volume_contact_area_m2=area,source_vertices_xyz_m=r['vertices_xyz_m']))
  return dict(status='PASS'if not hits else'RETAINED_FACE_CONTACT_REQUIRES_FINITE_OWNERSHIP_REPAIR',tested_face_owner_pairs=tested,indexed_side_faces=len(self.rows),contacts=hits,policy='Reject or explicitly cut only these finite source-face intersections after ownership review. Never suppress an entire bank array.')
