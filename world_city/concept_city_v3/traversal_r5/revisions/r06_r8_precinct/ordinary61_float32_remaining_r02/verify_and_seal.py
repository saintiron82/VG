"""Freeze the thirteen-case remaining-failure isolated scene-face retirement experiment."""
import hashlib,json,pathlib,collections
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 d=json.loads((H/'prepared_runtime.json').read_bytes());a=json.loads((H/'evidence/preparation.json').read_bytes());r=json.loads((H/'evidence/public_network_replay.json').read_bytes());old=json.loads((H.parent/'ordinary61_diagnostic_r01/prepared_runtime.json').read_bytes());original_result=json.loads((H.parent/'ordinary61_diagnostic_r01/evidence/public_network_replay.json').read_bytes());scene=json.loads(pathlib.Path(d['sources']['scene']['path']).read_bytes())
 checks={};checks['all_sources_hash_bound']=all(sha(pathlib.Path(v['path']))==v['sha256']for v in d['sources'].values());checks['all_implementation_hashes_bound']=all(sha(ROOT/p)==s for p,s in d['implementation_hashes'].items());checks['unchanged_controller_loader_scene_and_project']=all((H/name).read_bytes()==(H.parent/'ordinary61_diagnostic_r01'/name).read_bytes()for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot']);checks['result_prepared_hash']=r['prepared_sha256']==sha(H/'prepared_runtime.json');checks['exact_selected_routes_unchanged']=all(x==next(y for y in old['routes']if y['id']==x['id'])for x in d['routes']);checks['exact_requested_case_set']=len(r['routes'])==len(d['routes'])==13 and{q['id']for q in r['routes']}==set(a['cases']);checks['native_poses_unchanged']=all(v==old['placements'][k]for k,v in d['placements'].items());checks['native_assets_unchanged']=all(v==old['assets'][k]for k,v in d['assets'].items()if v.get('collision_format')!='actual_scene_triangles');checks['no_errors_or_teleports']=not r['errors']and all(q['within_route_teleports']==0 for q in r['routes']);checks['strict_original_thirteen_case_acceptance']=all(q['pass']for q in r['routes']);errors=[]
 for key,asset in d['assets'].items():
  path=ROOT/asset['render_path'];assert sha(path)==asset['render_sha256']
  if asset.get('collision_format')!='actual_scene_triangles':continue
  data=json.loads(path.read_bytes());assert data['scene_sha256']==d['sources']['scene']['sha256']
  for (mat,i),t in zip(data['source_face_indices'],data['triangles']):
   tri=scene['surfaces'][mat][i*3:i*3+3]
   if t!=[tri[0],tri[2],tri[1]]:errors.append([key,mat,i])
 checks['exact_sanitized_scene_triangle_parity']=not errors
 assert all(checks.values()),checks
 prior={q['id']:q for q in original_result['routes']};comparisons=[dict(case=q['id'],original_status=prior[q['id']]['status'],original_pass=prior[q['id']]['pass'],current_status=q['status'],current_pass=q['pass'],ground_ray_miss_frames=q['ground_ray_miss_frames'],not_on_floor_frames=q['not_on_floor_frames'],max_centerline_error_m=q['max_centerline_error_m'])for q in r['routes']]
 summary=dict(schema='riverstone.float32_zero_area_isolated_replay.v1',status='PASS_THIRTEEN_REMAINING_ORIGINALLY_FAILED_DIRECTIONS',scene=d['sources']['scene'],original_scene=d['sources']['original_diagnostic_scene'],checks=checks,comparisons=comparisons,removed_route_local_source_faces=sum(len(row['removed'])for row in a['rows']),report=ref(H/'evidence/public_network_replay.json'),preparation=ref(H/'evidence/preparation.json'),limits=['Thirteen local direction passes support the exact removal-only candidate for the remaining original failures. This does not establish a complete 244-case or whole-network candidate regression.','Every nonzero float32 triangle was retained by the source candidate. No route, terrain profile, native geometry, controller, physics timing, threshold or acceptance change was used.','Original complete 244-case report remains immutable.'])
 write(H/'evidence/summary.json',summary)
 external={v['path']:v['sha256']for v in d['sources'].values()};external.update({str(ROOT/p):s for p,s in d['implementation_hashes'].items()if not(ROOT/p).is_relative_to(H)})
 for asset in d['assets'].values():
  p=ROOT/asset['render_path']
  if not p.is_relative_to(H):external[str(p)]=sha(p)
 write(H/'source_closure.json',dict(schema='riverstone.isolated_replay_source_closure.v1',external_dependencies=[dict(path=p,sha256=s)for p,s in sorted(external.items())],original_evidence_freeze=ref(H.parent/'ordinary61_diagnostic_r01/freeze_manifest.json')))
 files={str(p.relative_to(H)):sha(p)for p in sorted(H.rglob('*'))if p.is_file()and not any(part in ['.runtime','.godot','__pycache__']for part in p.parts)and p.name!='freeze_manifest.json'}
 write(H/'freeze_manifest.json',dict(schema='riverstone.actual_traversal_frozen_evidence.r01',id=H.name,status='QUIESCENT_13_PASS_0_FAIL_ISOLATED_REGRESSION',owned_files=files,summary=ref(H/'evidence/summary.json'),source_closure=ref(H/'source_closure.json')));print(json.dumps(dict(checks=checks,freeze=ref(H/'freeze_manifest.json'),comparisons=comparisons),indent=2))
if __name__=='__main__':main()
