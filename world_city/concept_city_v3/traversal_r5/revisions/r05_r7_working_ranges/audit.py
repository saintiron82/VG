"""Read-only hashes, native poses, route identity and strict runtime outcomes."""
import pathlib,json,hashlib,sys,math,argparse,importlib.util
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());BASE=H.parents[1];spec=importlib.util.spec_from_file_location('r5_base_prepare',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);sha=b.sha;read=b.read;ref=b.ref

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--results');parser.add_argument('--output',required=True);args=parser.parse_args();p=read(H/'prepared.json');plan=read(H/'route_plan.json');issues=[]
 for key,s in p['sources'].items():
  if sha(s['path'])!=s['sha256']:issues.append(['changed_source',key])
 for path,h in p['implementation_hashes'].items():
  if sha(ROOT/path)!=h:issues.append(['changed_implementation',path])
 for key,a in p['assets'].items():
  if sha(ROOT/a['render_path'])!=a['render_sha256']:issues.append(['changed_asset',key])
 scene=read(p['sources']['actual_r7_scene']['path']);instances={r['id']:r for r in scene['common_instances']};pack=read(p['sources']['working_range_pack']['path']);max_pose=0.;max_door_error=0.;checked=[]
 for original in pack['placements']:
  actual=instances[original['id']];src=pack['assets'][original['asset_key']];dst=scene['common_assets'][actual['asset_key']];assert src['render_sha256']==dst['render_sha256'];bounds=dst['bounds']
  for x in [bounds['min'][0],bounds['max'][0]]:
   for y in [bounds['min'][1],bounds['max'][1]]:
    for z in [bounds['min'][2],bounds['max'][2]]:max_pose=max(max_pose,math.dist(b.transform([x,y,z],original),b.transform([x,y,z],actual)))
  for door in pack['actual_doors']:
   if door['parcel_id']==original['id']:max_door_error=max(max_door_error,math.dist(b.transform(door['actual_local_xyz_m'],actual),door['actual_door_xyz_m']))
  checked.append(original['id'])
 if max_pose>1e-8 or max_door_error>1e-8:issues.append(['native_pose_or_door_changed',max_pose,max_door_error])
 assert len(checked)==4 and len(pack['actual_doors'])==15
 court_checks=[]
 for original in read(p['sources']['court_prop_pack']['path'])['placements']:
  actual=instances[original['id']];assert actual['position_m']==original['position_m'];assert abs(actual.get('yaw_rad',0)-original.get('yaw_rad',0))<1e-12;court_checks.append(original['id'])
 assert len(court_checks)==6
 assert {r['actual_door_id'] for r in plan['routes'] if r.get('actual_door_id')}=={r['id'] for r in pack['actual_doors']}
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:assert sha(H/name)==sha(BASE/name)
 for q,r in zip(plan['routes'],p['routes']):
  assert q['id']==r['id'] and q['points']==r['points'],'Scene preparation altered route geometry'
 result={'schema':'riverstone.r7.bounded_traversal_integrity.v1','integrity_status':'pass' if not issues else 'fail','issues':issues,'prepared':ref(H/'prepared.json'),'source_scene':p['sources']['actual_r7_scene'],'native_range_placements_checked':checked,'native_court_prop_poses_checked':court_checks,'maximum_native_pose_error_m':max_pose,'maximum_actual_door_anchor_error_m':max_door_error,'controller':ref(H/'Traversal.gd'),'loader':ref(H/'RenderData.gd'),'scope':plan['coverage'],'limits':p['assumptions']}
 if args.results:
  path=pathlib.Path(args.results).resolve();r=read(path);assert r['prepared_sha256']==sha(H/'prepared.json');assert len(r['routes'])==len(p['routes']);assert {q['id'] for q in r['routes']}=={q['id'] for q in p['routes']};assert r['settings']['physics_hz']==60
  positive=[q for q in r['routes'] if 'expected_failure' not in q];assert len(positive)==34;assert all(q['within_route_teleports']==0 for q in r['routes'])
  result.update(raw_report=ref(path),physics_status=r['status'],physics_summary=r['summary'],positive_ground_ray_miss_frames=sum(q['ground_ray_miss_frames'] for q in positive),positive_obstacle_routes=[q['id'] for q in positive if q['obstacle_contact_ids']],cases=[{k:q.get(k) for k in ['id','status','pass','not_on_floor_frames','ground_ray_miss_frames','physics_frames','obstacle_contact_ids','spawn_ground_ray_hit','spawn_surface_y_m','failed_target_index']} for q in r['routes']])
 with pathlib.Path(args.output).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['integrity_status','issues','maximum_native_pose_error_m','maximum_actual_door_anchor_error_m','scope']},indent=2))
 if issues:raise SystemExit(2)
if __name__=='__main__':main()
