"""Read actual tested triangles at retained final blocked ray coordinates."""
import pathlib,json,math,hashlib,sys,importlib.util
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as g
spec=importlib.util.spec_from_file_location('base_prepare',H.parents[1]/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=b.read(H/'prepared.json');results=b.read(H/'evidence/capsule_r6_initial.json');routes={r['id']:r for r in p['routes']};cache={}
def load(key):
 if key not in cache:cache[key]=b.read(ROOT/p['assets'][key]['render_path'])
 return cache[key]
def hits_at(tri,point):
 poly=[[v[0],v[2]] for v in tri];ar=g.signed_polygon_area(poly)
 if abs(ar)<1e-10 or not g.point_in_convex_polygon([point[0],point[2]],poly,1e-8):return None
 a,c,d=tri;den=(c[0]-a[0])*(d[2]-a[2])-(d[0]-a[0])*(c[2]-a[2]);u=((point[0]-a[0])*(d[2]-a[2])-(point[2]-a[2])*(d[0]-a[0]))/den;v=((c[0]-a[0])*(point[2]-a[2])-(c[2]-a[2])*(point[0]-a[0]))/den;y=a[1]+u*(c[1]-a[1])+v*(d[1]-a[1])
 if y>point[1]+.01 or y<point[1]-1.2-.01:return None
 return {'y_m':y,'signed_xz_area_m2':ar,'front_up_in_tested_godot_order':ar>0,'triangle_world_xyz_m':tri}
findings=[]
for result in results['routes']:
 if result['status']!='blocked' or result['id'].startswith('NEGATIVE'):continue
 route=routes[result['id']];pos=result['end_position'];found=[]
 for pid in route['placement_ids']:
  placement=p['placements'][pid];key=placement['asset_key'];data=load(key);asset=p['assets'][key]
  if asset.get('collision_format') in ['actual_scene_triangles','source_grade_proxy_triangles']:
   for i,tri in enumerate(data['triangles']):
    hit=hits_at(tri,pos)
    if hit:found.append(dict(hit,placement_id=pid,asset_key=key,collision_triangle_index=i,scene_material_and_triangle=data.get('source_face_indices',[None]*len(data['triangles']))[i],render_sha256=asset['render_sha256']))
  else:
   for gi,group in enumerate(data['groups']):
    for qi,quad in enumerate(group['quads']):
     q=[b.transform(v,placement) for v in quad]
     for tri in [[q[0],q[2],q[1]],[q[0],q[3],q[2]]]:
      hit=hits_at(tri,pos)
      if hit:found.append(dict(hit,placement_id=pid,asset_key=key,group_index=gi,quad_index=qi,render_sha256=asset['render_sha256']))
 findings.append({'route_id':result['id'],'final_repeated_miss_center_xyz_m':pos,'floor_ray_end_xyz_m':[pos[0],pos[1]-1.2,pos[2]],'failed_target':result['failed_target'],'ground_ray_miss_frames':result['ground_ray_miss_frames'],'candidate_triangles_in_ray_interval':found,'interpretation':'Positive geometric coverage alone does not prove ray-facing floor; use front_up_in_tested_godot_order. End position is exact retained repeated-block location, not an invented per-frame miss trace.'})
out={'schema':'riverstone.r6.retained_failure_ray_geometry.v1','source_scene':p['sources']['actual_r6_scene'],'raw_results':b.ref(H/'evidence/capsule_r6_initial.json'),'prepared':b.ref(H/'prepared.json'),'cases':findings,'southern_single_miss':'Original controller does not persist miss-frame coordinates. Exact localization requires a separate telemetry-only rerun; do not infer its frame from sparse hit samples.'};b.write(H/'evidence/failure_ray_geometry.json',out)
for r in findings:print(r['route_id'],[(h.get('scene_material_and_triangle'),h.get('placement_id'),h['front_up_in_tested_godot_order'],h['y_m']) for h in r['candidate_triangles_in_ray_interval']])
