"""Hash-bound finite public-landings, preserving optimized planar triangles."""
import json, math
from functools import lru_cache
from . import approaches as a
geo=a.geo;review=a.review;CITY=a.CITY
PATH=CITY/'traversal/registered_candidate/public_landing_handoff.json'
SHA='9afbd08d17715ad95aeb7a5c2057037e2d8dc09746a7b455bcfd430a32552e4e'
if review.prior.sha(PATH)!=SHA:raise ValueError('Public landing handoff changed')
DATA=json.loads(PATH.read_bytes());TRIANGLES=[];MASKS=[];INDEX=geo._SpatialIndex(4);MASK_INDEX=geo._SpatialIndex(4)
REPO=CITY.parents[1]
for g in DATA['records']:
 path=REPO/g['path']
 if review.prior.sha(path)!=g['sha256']:raise ValueError('Public landing triangles changed')
 d=json.loads(path.read_bytes())
 for i,p in enumerate(g['finite_owned_polygons']):
  MASK_INDEX.add(len(MASKS),p['poly']);MASKS.append(dict(owner_id='LANDMARK_PUBLIC:'+g['id']+':'+str(i),group_id=g['id'],road_id=p['road_id'],polygon_xz_m=p['poly'],kind='landmark_public_hole',priority=9,render_land=False,material_hint='stone'))
 for i,t in enumerate(d['triangles']):
  p=[[v[0],v[2]] for v in t];INDEX.add(len(TRIANGLES),p)
  TRIANGLES.append(dict(owner_id=g['id']+':'+str(i),group_id=g['id'],kind='landmark_public_landing_preview',material_hint='stone',material='stone',polygon_xz_m=p,triangle_xyz_m=t,source_grade_bound=d['maximum_triangle_grade']))

def inside(x,z):return any(geo.point_in_convex_polygon([x,z],MASKS[i]['polygon_xz_m'],1e-8) for i in MASK_INDEX.candidates([[x,z]]))
@lru_cache(maxsize=131072)
def height_at(x,z):
 for i in sorted(INDEX.candidates([[x,z]])):
  r=TRIANGLES[i]
  if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-7):return a.point_y(r['triangle_xyz_m'],x,z)
 raise ValueError('Point outside finite public landing')

def supplemental_surface_domains(bounds_xz_m=None):
 out=[];box=None if bounds_xz_m is None else review.prior.old.rect(bounds_xz_m)
 ids=range(len(TRIANGLES)) if box is None else sorted(INDEX.candidates(box))
 for i in ids:
  r=TRIANGLES[i];p=r['polygon_xz_m'] if box is None else a.clean(geo.convex_intersection(r['polygon_xz_m'],box))
  if not p:continue
  xyz=[[q[0],a.point_y(r['triangle_xyz_m'],*q),q[1]] for q in p]
  out.append(dict(r,polygon_xz_m=p,vertices_xyz_m=xyz,render_surface=True,support=dict(polygon_xz_m=p,top_vertices_xyz_m=xyz,bottom_y_m=min(v[1] for v in xyz)-.25,verification='bounded thin road support proposal; no native/capsule claim'),status='validated finite triangle preview; surrounding road triangles not grade-certified'))
 return out

@lru_cache(maxsize=1)
def boundary_segments():
 # Test every finite edge against the coarse owned union. This handles source
 # triangle T-junctions without assuming matching subdivision on both sides.
 out=[];seen=set()
 for r in TRIANGLES:
  t=r['triangle_xyz_m']
  for p,q in zip(t,t[1:]+t[:1]):
   aa=[p[0],p[2]];bb=[q[0],q[2]];L=math.dist(aa,bb)
   if L<1e-8:continue
   key=tuple(sorted(tuple(round(v,8) for v in u) for u in (aa,bb)))
   if key in seen:continue
   seen.add(key);m=[(aa[k]+bb[k])/2 for k in (0,1)];n=[-(bb[1]-aa[1])/L*1e-5,(bb[0]-aa[0])/L*1e-5]
   if inside(m[0]+n[0],m[1]+n[1])==inside(m[0]-n[0],m[1]-n[1]):continue
   out.append(dict(a_xyz_m=p,b_xyz_m=q,group_id=r['group_id']))
 return out
@lru_cache(maxsize=1)
def boundary_index():
 idx=geo._SpatialIndex(4)
 for i,s in enumerate(boundary_segments()):idx.add(i,[[s[k][0],s[k][2]] for k in ('a_xyz_m','b_xyz_m')])
 return idx

def boundary_y(x,z):
 for i in boundary_index().candidates([[x-1e-6,z-1e-6],[x+1e-6,z+1e-6]]):
  s=boundary_segments()[i];p=s['a_xyz_m'];q=s['b_xyz_m'];dx=q[0]-p[0];dz=q[2]-p[2];L2=dx*dx+dz*dz
  t=((x-p[0])*dx+(z-p[2])*dz)/L2
  if -1e-7<=t<=1+1e-7 and math.hypot(x-p[0]-t*dx,z-p[2]-t*dz)<=1e-7:return p[1]+t*(q[1]-p[1])
 return None

def boundary_knots(bounds):
 p=review.prior.old.rect(bounds);out=[]
 for i in boundary_index().candidates(p):
  s=boundary_segments()[i]
  for k in ('a_xyz_m','b_xyz_m'):
   v=s[k]
   if bounds[0]-1e-7<=v[0]<=bounds[2]+1e-7 and bounds[1]-1e-7<=v[2]<=bounds[3]+1e-7:out.append([v[0],v[2]])
 return out

def contract():
 return dict(source_path=str(PATH.relative_to(CITY)),source_sha256=SHA,triangle_count=len(TRIANGLES),ownership_cut_count=len(MASKS),source_records=DATA['records'],outer_boundary_rule='Adjacent preview-road vertices inherit these exact piecewise-linear edge heights. Remaining preview road triangle gradients and collision are not approved.',max_source_deviation_m=max(r['maximum_sampled_source_error_m'] for r in DATA['records']))
