"""Exact finite road-owned residual; frozen recovered landing masks stay intact."""
import hashlib,json
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[2]
PATH=CITY/'validation/supplemental_side_repair_r1/finite_road_corner_restoration.json'
SHA256='5efb51b1ec563fb99fcf8415290864d3301294ce97698ed32dae5682bac57496'
assert hashlib.sha256(PATH.read_bytes()).hexdigest()==SHA256,'Changed finite restoration'
SIDE_HELPER_PATH=CITY/'validation/supplemental_side_repair_r1/side_repair.py'
SIDE_HELPER_SHA256='12c4810a586b1ee91d3419eb4637947540611577744696a91e0e3d91c87b711c'
assert hashlib.sha256(SIDE_HELPER_PATH.read_bytes()).hexdigest()==SIDE_HELPER_SHA256,'Changed finite side helper'
DATA=json.loads(PATH.read_bytes());RECORDS=DATA['restorations']
def point_owner(x,z):
 for r in RECORDS:
  if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-12):return r
 return None
def y(r,x,z):
 p,q,s=r['triangle_xyz_m'];ux,uz=q[0]-p[0],q[2]-p[2];vx,vz=s[0]-p[0],s[2]-p[2];det=ux*vz-uz*vx
 u=((x-p[0])*vz-(z-p[2])*vx)/det;v=(ux*(z-p[2])-uz*(x-p[0]))/det
 return p[1]+u*(q[1]-p[1])+v*(s[1]-p[1])
def restore_domains(records,bounds,clean):
 out=[]
 for r in records:
  parts=[r['polygon_xz_m']]
  for patch in RECORDS:
   if r['owner_id'] not in (patch['replaces_owner_id'],patch['underlying_record']['owner_id']):continue
   pending=[]
   for p in parts:
    q=clean(geo.convex_intersection(p,patch['polygon_xz_m']))
    if q:
     out.append(dict(patch,polygon_xz_m=q,review_tile_bounds_xz_m=bounds));pending.extend(q for raw in geo.convex_difference(p,patch['polygon_xz_m']) if(q:=clean(raw)))
    else:pending.append(p)
   parts=pending
  out.extend(dict(r,polygon_xz_m=p) for p in parts)
 return out
