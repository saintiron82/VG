"""Bind exact finite collision inputs and summarize unchanged-controller results."""
import pathlib,json,hashlib,collections,sys
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 prepared=H/'prepared_runtime.json';d=json.loads(prepared.read_bytes());result=json.loads((H/'evidence/public_network_replay.json').read_bytes());scene_path=pathlib.Path(d['sources']['scene']['path']);scene=json.loads(scene_path.read_bytes());checks={};checks['prepared_result_hash']=result['prepared_sha256']==sha(prepared);checks['all_source_files_current']=all(sha(pathlib.Path(r['path']))==r['sha256']for r in d['sources'].values());checks['all_implementation_hashes_current']=all(sha(ROOT/p)==h for p,h in d['implementation_hashes'].items());checks['unchanged_controller']=(H/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes();checks['unchanged_common_loader']=(H/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes()
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
 from prepare import n
 for state,data in scene['bridge_mechanism']['states'].items():
  for p in data['movable_placements']:
   tr=n.compose(scene['bridge_mechanism']['bridge_to_world'],p['transform_bridge_local']);pid='BRIDGE_STATE:'+state+':'+p['id'];actual[pid]=dict(id=pid,asset_key=p['asset_key'],position_m=tr['translation'],transform=tr)
 for pid,p in d['placements'].items():
  if pid.startswith(('SCENE:','CONTRACT:')):continue
  old=actual.get(pid)
  if old is None or p['asset_key']!=old['asset_key']or p['position_m']!=old['position_m']or p.get('yaw_rad',0)!=old.get('yaw_rad',0)or p.get('transform')!=old.get('transform'):placement_errors.append(pid)
 checks['native_poses_match_integrated_scene']=not placement_errors;checks['all_declared_cases_reported']=len(result['routes'])==len(d['routes']) and{r['id']for r in result['routes']}=={r['id']for r in d['routes']};checks['no_controller_errors']=not result['errors'];checks['no_within_case_teleports']=all(r['within_route_teleports']==0 for r in result['routes']);lookup={r['id']:r for r in d['routes']};summary={}
 for cls in sorted({r['case_class']for r in d['routes']}):
  rows=[r for r in result['routes']if lookup[r['id']]['case_class']==cls];summary[cls]=dict(cases=len(rows),passed=sum(bool(r['pass'])for r in rows),failed=sum(not r['pass']for r in rows),status_counts=dict(collections.Counter(r['status']for r in rows)),ground_ray_miss_frames=sum(r['ground_ray_miss_frames']for r in rows),not_on_floor_frames=sum(r['not_on_floor_frames']for r in rows))
 checks['all_cases_pass_strict_original_acceptance']=all(r['pass']for r in result['routes']);failures=[]
 for r in result['routes']:
  if not r['pass']:failures.append(dict(case=r['id'],case_class=lookup[r['id']]['case_class'],source_entry_id=lookup[r['id']].get('entry_id'),door_id=lookup[r['id']].get('door_id'),status=r['status'],failed_target=r.get('failed_target'),failed_target_index=r.get('failed_target_index'),end_position=r.get('end_position'),ground_ray_miss_frames=r['ground_ray_miss_frames'],not_on_floor_frames=r['not_on_floor_frames'],obstacle_contact_ids=r['obstacle_contact_ids'],obstacle_contact_samples=r['obstacle_contact_samples']))
 out=dict(schema='riverstone.actual_resolved_public_network_validation.r18.v1',status='PASS_DECLARED_ACTUAL_PUBLIC_ROUTES'if all(checks.values())else'FAILED_CASES_RETAINED',scene=ref(scene_path),prepared=ref(prepared),result=ref(H/'evidence/public_network_replay.json'),checks=checks,coverage=summary,ownership_coverage=d['coverage']['ownership_coverage'],exact_input_parity=dict(native_cache_assets=meshes,extracted_scene_triangle_references=faces,declared_contract_triangles=contract_faces,asset_errors=asset_errors,placement_errors=placement_errors),failures=failures,metrics=json.loads((H/'evidence/public_network_replay_metrics.json').read_bytes()),limits=['Finite resolved public-route controls test only the activated coverage ledger. Held or retired owners are not counted as passing.','Bidirectional main routes and accepted ordinary entries are distinct from untested road-to-road turns, door interiors, carts and moving actors.','Actual static bridge poses and their barriers use exact native scene state transforms; this is not live mechanism-operation certification.','Water has no opaque collider. Actual causeway-edge negatives test finite support loss, while old isolated fixtures remain separately retained.','No scene geometry, native cache, controller, loader or collision acceptance was altered.'])
 write(H/'evidence/summary.json',out);print(json.dumps(dict(status=out['status'],checks=checks,coverage=summary,failures=len(failures)),indent=2))
if __name__=='__main__':main()
