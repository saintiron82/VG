"""Static camera eye/standing-foot checks; not a capsule result."""
import pathlib,json,hashlib,sys,math,importlib.util
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
spec=importlib.util.spec_from_file_location('b',CITY/'traversal_r5/prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
read=b.read;sha=b.sha;ref=b.ref
camera_path=CITY/'registered_integration/r7/candidate_cameras.json';packpath=CITY/'assemblies/ordinary/registered/working_ranges_r01/resolved_placements.json';courtpath=packpath.parent/'court_phase01/resolved_placements.json';cameras=read(camera_path);packs=[read(packpath),read(courtpath)];scene_path=CITY/'evidence/visual_registered_common_r6_apron_r01/scene.json';assert sha(scene_path)=='6e441b9ca417db63dccbb0bbccd48aa59e6a2a62079cdeeb3e5440d78f654844';scene=read(scene_path);rows=[]
for key,camera in cameras.items():
 if 'eye_height_m' not in camera:continue
 v=camera['position_m'];q=[v[0],v[2]];floor=v[1]-camera['eye_height_m'];slabs=[];assets=dict(scene['common_assets']);instances=list(scene['common_instances'])
 for n,pack in enumerate(packs):
  for ak,asset in pack['assets'].items():assets[f'NEW{n}:{ak}']=asset
  for p in pack['placements']:instances.append(dict(p,asset_key=f'NEW{n}:'+p['asset_key']))
 tested=[]
 for p in instances:
  asset=assets[p['asset_key']];box=asset.get('bounds');renderpath=ROOT/asset['render_path']
  if box is None:box=read(renderpath)['bounds']
  bb=b.instance_bounds(p,box)
  if not(bb[0]-.3<=q[0]<=bb[2]+.3 and bb[1]-.3<=q[1]<=bb[3]+.3):continue
  assert sha(renderpath)==asset['render_sha256'];render=read(renderpath)
  for poly in slab_rectangles(render,floor+.05-p['position_m'][1],floor+1.85-p['position_m'][1]):slabs.append((p['id'],transform(poly,p)))
  tested.append(p['id'])
 solids=[];clearance=math.inf
 for id,poly in slabs:
  inside=g.point_in_convex_polygon(q,poly,0);d=0 if inside else min(g.point_segment_distance(q,a,z) for a,z in zip(poly,poly[1:]+poly[:1]));clearance=min(clearance,d)
  if d<.3:solids.append({'id':id,'distance_m':d,'polygon_xz_m':poly})
 floors=[]
 for material,vertices in scene['surfaces'].items():
  if material=='water':continue
  for i in range(0,len(vertices),3):
   t=vertices[i:i+3];poly=[[w[0],w[2]]for w in t]
   if g.polygon_area(poly)<1e-9 or not (min(x[0]for x in poly)<=q[0]<=max(x[0]for x in poly) and min(x[1]for x in poly)<=q[1]<=max(x[1]for x in poly)):continue
   if g.point_in_convex_polygon(q,poly,0):
    a,z,c=t;den=(z[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(z[2]-a[2]);u=((q[0]-a[0])*(c[2]-a[2])-(q[1]-a[2])*(c[0]-a[0]))/den;w=((z[0]-a[0])*(q[1]-a[2])-(z[2]-a[2])*(q[0]-a[0]))/den;y=a[1]+u*(z[1]-a[1])+w*(c[1]-a[1]);floors.append({'material':material,'triangle_index':i//3,'height_m':y})
 rows.append({'camera_id':key,'position_m':v,'target_m':camera['target_m'],'floor_y_m':floor,'actual_r6_floor_hits':floors,'tested_native_instances':tested,'walking_slab_radius_0p3_conflicts':solids,'minimum_native_slab_clearance_m':clearance if math.isfinite(clearance) else None,'static_eye_candidate_clear':not solids and any(abs(f['height_m']-floor)<1e-8 for f in floors)})
report={'status':'static_camera_geometry_only','inputs':{'cameras':ref(camera_path),'native_ranges':ref(packpath),'native_courts':ref(courtpath),'actual_base_scene':ref(scene_path),'checker':ref(pathlib.Path(__file__))},'cameras':rows,'limits':['Final R7 scene/capsule still pending. Native slabs are projected occupied geometry from floor+0.05 to +1.85 m, plus actual R6 floor-point triangles.','Camera visibility is a visual review; clear standing points do not establish full route traversal.']}
with (H/'evidence/camera_static_check.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(rows,indent=2))
