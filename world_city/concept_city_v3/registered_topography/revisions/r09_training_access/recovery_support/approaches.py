"""Exact persisted r3 planar surfaces; reconstructed provenance, never old hashes."""
import json,math,hashlib
from pathlib import Path
from functools import lru_cache
from world_city.concept_city_v3.registered_topography.revisions.r05_preview_lod import review
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
HERE=Path(__file__).resolve().parent;CITY=review.prior.CITY
BIND_PATH=HERE/'binding.json';BIND=json.loads(BIND_PATH.read_bytes());PATH=CITY/BIND['data_path'];SHA=BIND['data_sha256']
if review.prior.sha(PATH)!=SHA:raise ValueError('Reconstructed finite profile source changed')
DATA=json.loads(PATH.read_bytes());TRIANGLES=DATA['approaches']['triangles'];MASKS=DATA['approaches']['masks'];INDEX=geo._SpatialIndex(4);MASK_INDEX=geo._SpatialIndex(16)
for i,r in enumerate(TRIANGLES):INDEX.add(i,r['polygon_xz_m'])
for i,r in enumerate(MASKS):MASK_INDEX.add(i,r['polygon_xz_m'])
def point_y(t,x,z):return review.prior.point_y(t,x,z)
def inside(x,z):return any(geo.point_in_convex_polygon([x,z],MASKS[i]['polygon_xz_m'],1e-8) for i in MASK_INDEX.candidates([[x,z]]))
@lru_cache(maxsize=131072)
def height_at(x,z):
 for i in sorted(INDEX.candidates([[x,z]])):
  r=TRIANGLES[i]
  if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-7):return point_y(r['triangle_xyz_m'],x,z)
 raise ValueError('Point outside reconstructed finite approach source')
def supplemental_surface_domains(bounds_xz_m=None):
 box=None if bounds_xz_m is None else review.prior.old.rect(bounds_xz_m);out=[]
 for i in (range(len(TRIANGLES)) if box is None else sorted(INDEX.candidates(box))):
  r=TRIANGLES[i];p=r['polygon_xz_m'] if box is None else clean(geo.convex_intersection(r['polygon_xz_m'],box))
  if not p:continue
  xyz=[[q[0],point_y(r['triangle_xyz_m'],*q),q[1]] for q in p]
  out.append(dict(r,vertices_xyz_m=xyz,polygon_xz_m=p,render_surface=True,material='stone',material_hint='stone',support=dict(polygon_xz_m=p,top_vertices_xyz_m=xyz,bottom_y_m=min(v[1] for v in xyz)-r.get('support_fill_bound_m',1)-.25,verification='recovered planar source and conservative support proposal; no new native or capsule approval')))
 return out
def side_records(bounds_xz_m,outside_owner=None,outside_height=None):
 outside_owner=outside_owner or review.owner_at;outside_height=outside_height or review.source_surface_height_at;out=[];seen=set()
 for r in supplemental_surface_domains(bounds_xz_m):
  ps=r['vertices_xyz_m']
  for a,b in zip(ps,ps[1:]+ps[:1]):
   p=[a[0],a[2]];q=[b[0],b[2]];L=math.dist(p,q)
   if L<1e-7:continue
   key=tuple(sorted(tuple(round(v,7) for v in t) for t in (p,q)))
   if key in seen:continue
   seen.add(key);m=[(p[k]+q[k])/2 for k in (0,1)];n=[-(q[1]-p[1])/L*1e-5,(q[0]-p[0])/L*1e-5];states=[inside(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)]
   if states[0]==states[1]:continue
   sign=-1 if states[0] else 1;o=outside_owner(*(m[k]+sign*n[k] for k in (0,1)));ys=[outside_height(o,*t) for t in (p,q)]
   if max(abs(a[1]-ys[0]),abs(b[1]-ys[1]))<1e-6:continue
   out.append(dict(id='RECOVERED_APPROACH_SIDE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],material_hint='stone',vertices_xyz_m=[a,b,[q[0],ys[1],q[1]],[p[0],ys[0],p[1]]],outside_owner_id=o['owner_id'],status='reconstructed finite support side; collision not approved'))
 return out
def recovery_record():return dict(BIND,provenance=DATA.get('provenance',{}),old_hash_equivalence_claim=False)
def contract():return dict(source_path=str(PATH.relative_to(CITY)),source_sha256=SHA,triangle_count=len(TRIANGLES),ownership_cut_count=len(MASKS),reconstruction=recovery_record(),status='exact frozen r3 rendered triangle reconstruction; original source metadata may be unavailable')
