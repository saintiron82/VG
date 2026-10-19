"""Read-only source/frame and actual-run checks; failures remain intact."""
import pathlib,json,hashlib,sys,math,importlib.util,argparse
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());BASE=H.parents[1];spec=importlib.util.spec_from_file_location('base_prepare',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
sha=b.sha;read=b.read;write=b.write;ref=b.ref

def main():
 arg=argparse.ArgumentParser();arg.add_argument('--results');arg.add_argument('--output',required=True);opt=arg.parse_args();p=read(H/'prepared.json');plan=read(H/'route_plan.json');issues=[]
 for key,s in p['sources'].items():
  if sha(s['path'])!=s['sha256']:issues.append(['changed_source',key])
 for path,expected in p['implementation_hashes'].items():
  if sha(ROOT/path)!=expected:issues.append(['changed_implementation',path])
 for key,a in p['assets'].items():
  if sha(ROOT/a['render_path'])!=a['render_sha256']:issues.append(['changed_asset',key])
 scene=read(p['sources']['actual_r6_scene']['path']);instances={r['id']:r for r in scene['common_instances']};merchant=read(p['sources']['merchant_pack']['path']);srcassets=merchant['assets'];srcassets={r['id']:r for r in srcassets} if isinstance(srcassets,list) else srcassets;max_pose_error=0.;checked=[]
 for original in merchant['placements']:
  actual=instances[original['id']];src=srcassets[original['asset_key']];dst=scene['common_assets'][actual['asset_key']];assert src['render_sha256']==dst['render_sha256'];box=dst['bounds']
  for x in [box['min'][0],box['max'][0]]:
   for y in [box['min'][1],box['max'][1]]:
    for z in [box['min'][2],box['max'][2]]:max_pose_error=max(max_pose_error,math.dist(b.transform([x,y,z],original),b.transform([x,y,z],actual)))
  checked.append(original['id'])
 if max_pose_error>1e-8:issues.append(['native_pose_changed',max_pose_error])
 assert len(checked)==14 and len(plan['selected_private_chains'])==7
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:assert sha(H/name)==sha(BASE/name)
 result={'schema':'riverstone.r6.bounded_traversal_integrity.v1','integrity_status':'pass' if not issues else 'fail','issues':issues,'prepared':ref(H/'prepared.json'),'source_scene':p['sources']['actual_r6_scene'],'native_merchant_placements_checked':checked,'maximum_native_pose_error_m':max_pose_error,'controller':ref(H/'Traversal.gd'),'loader':ref(H/'RenderData.gd'),'scope':plan['coverage'],'selected_door_chains':plan['selected_private_chains'],'limits':p['assumptions']}
 if opt.results:
  path=pathlib.Path(opt.results).resolve();r=read(path);assert r['prepared_sha256']==sha(H/'prepared.json');assert len(r['routes'])==18;assert {q['id'] for q in r['routes']}=={q['id'] for q in p['routes']};assert r['settings']['physics_hz']==60
  positives=[q for q in r['routes'] if 'expected_failure' not in q];assert len(positives)==16
  result.update(raw_report=ref(path),physics_status=r['status'],physics_summary=r['summary'],all_spawns_grounded=all(q['spawn_ground_ray_hit'] and q['spawn_on_floor'] for q in r['routes']),positive_obstacle_routes=[q['id'] for q in positives if q['obstacle_contact_ids']],cases=[{k:q.get(k) for k in ['id','status','pass','not_on_floor_frames','ground_ray_miss_frames','physics_frames','obstacle_contact_ids','spawn_ground_ray_hit','spawn_surface_y_m','failed_target_index']} for q in r['routes']])
  assert all(q['within_route_teleports']==0 for q in r['routes'])
 write(pathlib.Path(opt.output),result);print(json.dumps({k:result[k] for k in ['integrity_status','issues','maximum_native_pose_error_m','scope']},indent=2))
 if issues:raise SystemExit(2)
if __name__=='__main__':main()
