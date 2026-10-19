"""Hash-bound finite road preview. Ownership clips inherit one checked plane."""
import json,hashlib
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent
SHA256='f9ed6913281352263cec173bd95b6fe9ee424a364f2be60b1a8eb6c135c19cb9'
raw=(HERE/'collar_profile.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==SHA256,'Changed finite public profile'
DATA=json.loads(raw);TRIANGLES=DATA['triangles'];INDEX=geo._SpatialIndex(4)
for i,r in enumerate(TRIANGLES):INDEX.add(i,r['polygon_xz_m'])
def triangle_at(x,z):
 for i in sorted(INDEX.candidates([[x,z]])):
  r=TRIANGLES[i]
  if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-9):return r
 return None
def record(r,t,p):
 return dict(r,kind='r14_public_profile',underlying_record=r,polygon_xz_m=p,preview_plane_y_xz_m=t['plane_y_xz_m'],profile_triangle_id=t['id'])
def point_record(r,x,z):
 t=triangle_at(x,z)
 return record(r,t,t['polygon_xz_m']) if t else r
def pieces(r,clean):
 out=[]
 for i in sorted(INDEX.candidates(r['polygon_xz_m'])):
  t=TRIANGLES[i];p=clean(geo.convex_intersection(r['polygon_xz_m'],t['polygon_xz_m']))
  if p:out.append(record(r,t,p))
 return out
def y(r,x,z):
 a,b,c=r['preview_plane_y_xz_m'];return a*x+b*z+c
