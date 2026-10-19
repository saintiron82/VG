"""Bind exact finite collision inputs and summarize unchanged-controller results."""
import pathlib,json,hashlib,collections,sys
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 prepared=H/'prepared_runtime.json';d=json.loads(prepared.read_bytes());result=json.loads((H/'evidence/services_replay.json').read_bytes());scene_path=pathlib.Path(d['sources']['scene']['path']);scene=json.loads(scene_path.read_bytes());checks={};checks['prepared_result_hash']=result['prepared_sha256']==sha(prepared);checks['all_source_files_current']=all(sha(pathlib.Path(r['path']))==r['sha256']for r in d['sources'].values());checks['all_implementation_hashes_current']=all(sha(ROOT/p)==h for p,h in d['implementation_hashes'].items());checks['unchanged_controller']=(H/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes();checks['unchanged_common_loader']=(H/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes()
 meshes=0;faces=0;contract_faces=0;asset_errors=[]
 for key,a in d['assets'].items():
  path=ROOT/a['render_path']
  if sha(path)!=a['render_sha256']:asset_errors.append(key);continue
  if a.get('collision_format')=='actual_scene_triangles':
   data=json.loads(path.read_bytes());assert data['scene_sha256']==d['sources']['scene']['sha256'];assert len(data['source_face_indices'])==len(data['triangles'])
   for (mat,i),t in zip(data['source_face_indices'],data['triangles']):
    old=scene['surfaces'][mat][i*3:i*3+3]
    if t!=[old[0],old[2],old[1]]:asset_errors.append(key+':'+str(i))
   faces+=len(data['triangles'])
  elif a.get('collision_format')=='source_grade_proxy_triangles':
   data=json.loads(path.read_bytes());contract=next(c for c in scene['collision_contracts']if c['id']==data['contract_id']);old={json.dumps(t,separators=(',',':'))for t in contract['add_triangles_world_xyz_m']};assert all(json.dumps(t,separators=(',',':'))in old for t in data['triangles']);contract_faces+=len(data['triangles'])
  else:meshes+=1
 checks['exact_scene_native_contract_inputs']=not asset_errors;actual={p['id']:p for p in scene['common_instances']};placement_errors=[]
 for pid,p in d['placements'].items():
  if pid.startswith(('SCENE:','CONTRACT:')):continue
  old=actual.get(pid)
  if old is None or p['asset_key']!=old['asset_key']or p['position_m']!=old['position_m']or p.get('yaw_rad',0)!=old.get('yaw_rad',0)or p.get('transform')!=old.get('transform'):placement_errors.append(pid)
 checks['native_poses_match_integrated_scene']=not placement_errors;checks['all_46_cases_reported']=len(result['routes'])==len(d['routes'])==46 and{r['id']for r in result['routes']}=={r['id']for r in d['routes']};checks['no_controller_errors']=not result['errors'];checks['no_within_case_teleports']=all(r['within_route_teleports']==0 for r in result['routes']);lookup={r['id']:r for r in d['routes']};summary={}
 for cls in['canal_crossing','local_crossing_network','common_entry','bridge_rail_negative','common_wall_negative']:
  rows=[r for r in result['routes']if lookup[r['id']]['case_class']==cls];summary[cls]=dict(cases=len(rows),passed=sum(bool(r['pass'])for r in rows),failed=sum(not r['pass']for r in rows),status_counts=dict(collections.Counter(r['status']for r in rows)),ground_ray_miss_frames=sum(r['ground_ray_miss_frames']for r in rows),not_on_floor_frames=sum(r['not_on_floor_frames']for r in rows))
 checks['all_cases_pass_strict_original_acceptance']=all(r['pass']for r in result['routes']);failures=[]
 for r in result['routes']:
  if not r['pass']:failures.append(dict(case=r['id'],case_class=lookup[r['id']]['case_class'],source_entry_id=lookup[r['id']].get('entry_id'),door_id=lookup[r['id']].get('door_id'),status=r['status'],failed_target=r.get('failed_target'),failed_target_index=r.get('failed_target_index'),end_position=r.get('end_position'),ground_ray_miss_frames=r['ground_ray_miss_frames'],not_on_floor_frames=r['not_on_floor_frames'],obstacle_contact_ids=r['obstacle_contact_ids'],obstacle_contact_samples=r['obstacle_contact_samples']))
 out=dict(schema='riverstone.actual_district_services_capsule_validation.r02',status='PASS_BOUNDED_ACTUAL_SERVICES_BATCH'if all(checks.values())else'FAILED_CASES_RETAINED',scene=ref(scene_path),prepared=ref(prepared),result=ref(H/'evidence/services_replay.json'),checks=checks,coverage=summary,exact_input_parity=dict(native_cache_assets=meshes,extracted_scene_triangle_references=faces,declared_contract_triangles=contract_faces,asset_errors=asset_errors,placement_errors=placement_errors),failures=failures,metrics=json.loads((H/'evidence/services_replay_metrics.json').read_bytes()),limits=['46 finite capsule controls do not certify carts, continuous full-width traffic, interiors, hydraulic operation or the whole city road network.','Four native decks and the common R02 entrance have three sampled lanes tested bidirectionally; both connected crossing networks have local centerline tests.','Eight native bridge rails and two common perimeter walls are blocked controls.','The exact immutable r8_district_r02 scene is tested, independently of the sealed passing B15 r01 evidence.','No geometry, native cache, controller, loader, scene contract or collision acceptance was altered.'])
 write(H/'evidence/summary.json',out);print(json.dumps(dict(status=out['status'],checks=checks,coverage=summary,failures=len(failures)),indent=2))
if __name__=='__main__':main()
