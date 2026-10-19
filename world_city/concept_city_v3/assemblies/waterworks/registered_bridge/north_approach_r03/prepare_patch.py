"""Exact cached footprint ownership and continuous road-top collision binding."""
import json,math
from .author import HERE,ROOT,CITY,read,old,ref
from .audit_native import cols
from .profile import a
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import frozen
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges.frozen_r6 import fan_upward,normal_y

def write(name,d):(HERE/name).write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')
def rectangles(keys,pitch):
 # Maximal runs, merged only when the occupied rows have identical extents.
 rows={}
 for x,z in keys:rows.setdefault(z,[]).append(x)
 active={};out=[]
 for z in range(min(rows),max(rows)+2):
  xs=sorted(rows.get(z,[]));runs=[]
  for x in xs:
   if runs and x==runs[-1][1]:runs[-1][1]=x+1
   else:runs.append([x,x+1])
  now=set(map(tuple,runs))
  for run,(z0,z1)in list(active.items()):
   if run not in now:
    x0,x1=run;out.append([[x0*pitch,z0*pitch],[x1*pitch,z0*pitch],[x1*pitch,z1*pitch],[x0*pitch,z1*pitch]]);del active[run]
  for run in now:active[run]=[active.get(run,[z,z])[0],z+1]
 return out

def run():
 scene=a.load_scene();p=read(HERE/'profile.json');pack=read(HERE/'resolved_placements.json');b,t=p['bridge_frame']['basis'],p['bridge_frame']['translation'];world=lambda q:[t[i]+sum(b[i][j]*q[j]for j in range(3))for i in range(3)]
 local_masks=[]
 for asset in pack['assets'][1:]:
  c=read(ROOT/asset['compiled']['path']);local_masks+=rectangles(cols(c),c['pitch'])
 local_masks=a.common.disjoint_union(local_masks);masks=[[[q[0],q[2]]for v in poly for q in[world([v[0],0,v[1]])]]for poly in local_masks];ix=a.TriangleIndex(scene,masks);edits=[];proof=[]
 for r in ix.rows:
  candidates=[m for m in masks if a.intersects(a.bounds(m),a.bounds(r['polygon_xz_m']))]
  pieces=a.common.subtract([r['polygon_xz_m']],candidates);before=old.area(r['polygon_xz_m']);after=sum(old.area(q)for q in pieces)
  if before-after<1e-8:continue
  ts=[]
  for q in pieces:ts+=fan_upward([[x,a.common.height(r['plane_y_xz_m'],[x,z]),z]for x,z in q])
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=ts));proof.append(dict(material=r['material'],triangle_index=r['triangle_index'],removed_area_m2=before-after))
 bank=scene['surfaces']['bank'];bankproof=[]
 for j in range(0,len(bank),3):
  tri=bank[j:j+3];xz=[[v[0],v[2]]for v in tri]
  candidates=[m for m in masks if a.intersects(a.bounds(m),a.bounds(xz))]
  if not candidates:continue
  if abs(normal_y(tri))>1e-10:
   # A canal/river bed is deliberately retained below this supported approach.
   continue
  cut=frozen.clip_vertical_triangle(tri,candidates)
  if cut['unchanged']:continue
  oldarea=area3(tri);newarea=sum(area3(v)for v in cut['triangles_xyz_m'])
  if oldarea-newarea<1e-8:continue
  if max(v[1]for v in tri)>2.55:raise ValueError(('High vertical boundary requires dedicated ownership',j//3,tri))
  edits.append(dict(material='bank',triangle_index=j//3,source_triangle_sha256=a.canonical_sha(tri),replacement_triangles_xyz_m=cut['triangles_xyz_m']));bankproof.append(dict(triangle_index=j//3,removed_area_3d_m2=oldarea-newarea))
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='NORTH_SUPPORTED_APPROACH_R03',status='SOURCE_NATIVE_OWNERSHIP_PENDING_REPLAY',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in {r['material']for r in edits}},surface_edits=edits,appended_surfaces={},removed_foundation_proxy_ids=[])
 triangles=[]
 for r in p['triangles']:
  tri=r['triangle_xyz_m'];triangles.append(tri if normal_y(tri)>0 else[tri[0],tri[2],tri[1]])
 native=pack['assets'][2];placement=pack['placements'][2]
 contract=dict(id='NORTH_APPROACH_R03_CONTINUOUS_ROAD',native_placement_id=placement['id'],native_source=native['cache'],replacement_transform={k:placement[k]for k in('position_m','yaw_rad')},disable_native_mesh_collider_ids=[placement['id']],add_triangles_world_xyz_m=triangles,profile_source=ref(HERE/'profile.json'),visible_geometry_unchanged=True,maximum_visible_surface_sampling_error_m=.1,logical_surface='Supported6m public road through main gate, source width and seam-bound. New continuous road is not an intentional staircase.',limits=['Final scene capsule replay and full-width native volume checks pending.','Exact closed/open bridge mechanism is unchanged.'])
 write('surface_patch.json',patch);write('collision_contract.json',contract);write('ownership_review.json',dict(base_scene_sha256=a.SCENE_SHA256,exact_native_footprint_masks_xz_m=masks,actual_native_footprint_area_m2=sum(old.area(q)for q in masks),terrain_edits=proof,bank_edits=bankproof,existing_water_and_bed_unchanged=True,collision_triangles=len(triangles),native_seam_profile=ref(HERE/'profile.json')));print(json.dumps(dict(edits=len(edits),masks=len(masks),bank_edits=len(bankproof),collision_triangles=len(triangles))))

def area3(t):
 u=[t[1][i]-t[0][i]for i in range(3)];v=[t[2][i]-t[0][i]for i in range(3)];return math.sqrt(sum(q*q for q in[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]))/2
if __name__=='__main__':run()
