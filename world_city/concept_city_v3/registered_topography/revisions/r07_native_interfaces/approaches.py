"""Exact validated finite landmark approach profiles, still spatial previews."""
import json,math,hashlib
from pathlib import Path
from functools import lru_cache
from ..r05_preview_lod import review
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
HERE=Path(__file__).resolve().parent;CITY=review.prior.CITY
PATH=CITY/'validation/landmark_access_candidate/finite_ramps_optimized_a3c19f62609a_c49a90d166d1.json'
SHA='bf960c12defbcedcf96b2b105fbe686180d5380c18d6b8cafeb8759519d72748'
DATA=json.loads(PATH.read_bytes())
if review.prior.sha(PATH)!=SHA:raise ValueError('Landmark approach source changed')
TRIANGLES=[];MASKS=[];INDEX=geo._SpatialIndex(4);MASK_INDEX=geo._SpatialIndex(16)
for g in DATA['groups']:
 for i,p in enumerate(g['proposed_ramp_regions_xz_m']):
  MASK_INDEX.add(len(MASKS),p);MASKS.append(dict(owner_id='LANDMARK_APPROACH:'+g['group_id']+':'+str(i),group_id=g['group_id'],polygon_xz_m=p,kind='landmark_ramp_hole',render_land=False,material_hint='stone',priority=18))
 for t in g['triangulated_top_surface']:
  p=[[v[0],v[2]] for v in t['vertices_xyz_m']];INDEX.add(len(TRIANGLES),p)
  TRIANGLES.append(dict(owner_id=t['id'],group_id=g['group_id'],route_id=t['route_id'],kind='landmark_approach_preview',material_hint='stone',material='stone',polygon_xz_m=p,triangle_xyz_m=t['vertices_xyz_m'],source_grade=t['source_grade'],support_fill_bound_m=g['measurements']['maximum_sampled_fill_m']))

def point_y(t,x,z):return review.prior.point_y(t,x,z)
def inside(x,z):return any(geo.point_in_convex_polygon([x,z],MASKS[i]['polygon_xz_m'],1e-8) for i in MASK_INDEX.candidates([[x,z]]))
@lru_cache(maxsize=131072)
def height_at(x,z):
 for i in sorted(INDEX.candidates([[x,z]])):
  r=TRIANGLES[i]
  if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-7):return point_y(r['triangle_xyz_m'],x,z)
 raise ValueError('Point outside finite landmark approach source')

def supplemental_surface_domains(bounds_xz_m=None):
 out=[];ids=range(len(TRIANGLES)) if bounds_xz_m is None else sorted(INDEX.candidates(review.prior.old.rect(bounds_xz_m)))
 for i in ids:
  r=TRIANGLES[i];p=r['polygon_xz_m'] if bounds_xz_m is None else clean(geo.convex_intersection(r['polygon_xz_m'],review.prior.old.rect(bounds_xz_m)))
  if not p:continue
  xyz=[[q[0],point_y(r['triangle_xyz_m'],*q),q[1]] for q in p]
  out.append(dict(r,polygon_xz_m=p,vertices_xyz_m=xyz,render_surface=True,
   support=dict(polygon_xz_m=p,top_vertices_xyz_m=xyz,bottom_y_m=min(v[1] for v in xyz)-r['support_fill_bound_m']-.25,verification='conservative source proposal from group sampled cut/fill bound; native support/collision pending'),
   status='labeled continuous terrain-approach preview; not native-common or capsule approval'))
 return out

def side_records(bounds_xz_m,outside_owner=None,outside_height=None):
 outside_owner=outside_owner or review.owner_at;outside_height=outside_height or review.source_surface_height_at
 out=[];seen=set()
 for r in supplemental_surface_domains(bounds_xz_m):
  points=r['vertices_xyz_m']
  for a,b in zip(points,points[1:]+points[:1]):
   p=[a[0],a[2]];q=[b[0],b[2]];L=math.dist(p,q)
   if L<1e-7:continue
   key=tuple(sorted(tuple(round(v,7) for v in u) for u in (p,q)))
   if key in seen:continue
   seen.add(key);m=[(p[k]+q[k])/2 for k in (0,1)];n=[-(q[1]-p[1])/L*1e-5,(q[0]-p[0])/L*1e-5]
   states=[inside(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)]
   if states[0]==states[1]:continue
   sign=-1 if states[0] else 1;outside=outside_owner(*(m[k]+sign*n[k] for k in (0,1)))
   if outside['kind']=='water_hole':raise ValueError('Approach side unexpectedly meets water')
   ys=[outside_height(outside,*u) for u in (p,q)]
   if max(abs(a[1]-ys[0]),abs(b[1]-ys[1]))<1e-6:continue
   out.append(dict(id='APPROACH_SIDE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],material_hint='stone',outside_owner_id=outside['owner_id'],public_interface=outside['kind']=='road',
    vertices_xyz_m=[a,b,[q[0],ys[1],q[1]],[p[0],ys[0],p[1]]],status='finite cut/fill side source; public-side triangulation remains a separate gate'))
 return out

def contract():
 return dict(source_path=str(PATH.relative_to(CITY)),source_sha256=SHA,triangle_count=len(TRIANGLES),ownership_cut_count=len(MASKS),route_count=sum(len(g['route_ids']) for g in DATA['groups']),
  shared_boundaries=[dict(group_id=g['group_id'],public=g['shared_public_boundary_segments'],native=g['shared_native_floor_boundaries']) for g in DATA['groups']],
  missing_routes=DATA['missing_routes'],api=dict(surfaces='supplemental_surface_domains(bounds=None)',height='height_at(x,z)',sides='side_records(bounds)'),
  rule='Keep each source triangle planar when clipping; do not re-evaluate optimized vertex heights from the analytic ground field. Common compilation and capsule approval are not claimed.')
