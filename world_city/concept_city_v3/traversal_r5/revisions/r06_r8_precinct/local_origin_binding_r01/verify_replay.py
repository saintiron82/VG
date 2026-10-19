"""Verify and freeze unchanged-controller results on an exact runtime scene."""
import argparse,collections,hashlib,importlib.util,json,pathlib,copy
from bind_origins import transform, IMPLEMENTATION_SHA, origin
TOOL=pathlib.Path(__file__).resolve();ROOT=next(p for p in TOOL.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def read(p):return json.loads(p.read_bytes())
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def validate_origin_asset(world,key,world_asset,local_asset,placements,proof):
 expected,translation,expected_proof=transform(world,key,world_asset)
 assert expected==local_asset,'Local triangles/metadata differ from declared exact transform'
 assert proof==expected_proof,'Local transform proof mismatch'
 assert placements,'Missing actual-scene placement'
 assert all(p['position_m']==translation and dict(p,position_m=[0,0,0])==world['placements'][p['id']]for p in placements),'Unexpected placement transform'
 reconstructed=[[[v[i]+translation[i]for i in range(3)]for v in t]for t in local_asset['triangles']]
 assert reconstructed==world_asset['triangles'],'Source world coordinates changed'
 return translation

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--runtime-output',type=pathlib.Path,required=True);args=ap.parse_args();h=args.runtime_output.resolve();prepared=h/'prepared_runtime.json';d=read(prepared);r=read(h/'evidence/public_network_replay.json');scene_path=pathlib.Path(d['sources']['scene']['path']);scene=read(scene_path);world_path=pathlib.Path(d['sources']['world_prepared']['path']);world=read(world_path);authored_path=pathlib.Path(world['sources']['authored_prepared']['path']);authored=read(authored_path);binding_path=world_path.parent/'evidence/runtime_binding.json';binding=read(binding_path);origin_binding=read(h/'evidence/local_origin_binding.json');origin_rows={row['asset_key']:row for row in origin_binding['assets']};checks={}
 checks['prepared_result_hash']=r['prepared_sha256']==sha(prepared);checks['all_source_hashes_current']=all(sha(pathlib.Path(v['path']))==v['sha256']for v in d['sources'].values());checks['all_implementation_hashes_current']=all(sha(ROOT/p)==s for p,s in d['implementation_hashes'].items());checks['original_controller_unchanged']=(h/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes();checks['common_loader_unchanged']=(h/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes();checks['original_scene_hierarchy_and_physics_settings']=(h/'Traversal.tscn').read_bytes()==(authored_path.parent/'Traversal.tscn').read_bytes()and(h/'project.godot').read_bytes()==(authored_path.parent/'project.godot').read_bytes();checks['authored_routes_and_native_poses_unchanged']=d['routes']==world['routes']==authored['routes']and world['placements']==authored['placements']and d['buildings']==world['buildings']==authored['buildings'];checks['all_declared_cases_reported']=len(r['routes'])==len(d['routes'])and{x['id']for x in r['routes']}=={x['id']for x in d['routes']};checks['no_controller_errors']=not r['errors'];checks['no_within_case_teleports']=all(x['within_route_teleports']==0 for x in r['routes']);checks['exact_runtime_binding_output']=binding['prepared']['sha256']==sha(world_path)and origin_binding['prepared']['sha256']==sha(prepared)and origin_binding['source']['sha256']==sha(world_path)and binding['runtime_scene']['sha256']==sha(scene_path)
 spec=importlib.util.spec_from_file_location('immutable_authored_replay_prepare',authored_path.parent/'prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);n=module.n
 actual={p['id']:p for p in scene['common_instances']}
 for state,data in scene['bridge_mechanism']['states'].items():
  for p in data['movable_placements']:
   tr=n.compose(scene['bridge_mechanism']['bridge_to_world'],p['transform_bridge_local']);pid='BRIDGE_STATE:'+state+':'+p['id'];actual[pid]=dict(id=pid,asset_key=p['asset_key'],position_m=tr['translation'],transform=tr)
 pose_errors=[]
 for pid,p in d['placements'].items():
  if pid.startswith(('SCENE:','CONTRACT:')):continue
  old=actual.get(pid)
  if old is None or p['asset_key']!=old['asset_key']or p['position_m']!=old['position_m']or p.get('yaw_rad',0)!=old.get('yaw_rad',0)or p.get('transform')!=old.get('transform'):pose_errors.append(pid)
 checks['actual_runtime_native_poses_exact']=not pose_errors
 scene_contracts={c['id']:c for c in scene.get('collision_contracts',[])};contract_sets={};asset_errors=[];scene_faces=0;contract_faces=0;native_assets=0
 origin_errors=[]
 checks['declared_local_origin_implementation']=sha(pathlib.Path(origin.__file__))==IMPLEMENTATION_SHA==d['sources']['local_origin_implementation']['sha256']
 for key,a in d['assets'].items():
  p=ROOT/a['render_path']
  if sha(p)!=a['render_sha256']:asset_errors.append([key,'hash']);continue
  form=a.get('collision_format')
  if form=='actual_scene_triangles':
   data=read(p)
   if data['scene_sha256']!=d['sources']['scene']['sha256']or len(data['triangles'])!=len(data['source_face_indices']):asset_errors.append([key,'source binding']);continue
   row=origin_rows.get(key);original_asset=world['assets'][key];world_asset=read(ROOT/original_asset['render_path'])
   actual_placements=[po for po in d['placements'].values()if po['asset_key']==key]
   if row is None or row['source']['sha256']!=sha(ROOT/original_asset['render_path'])or row['local']['sha256']!=sha(p):origin_errors.append([key,'local file binding']);continue
   try:translation=validate_origin_asset(world,key,world_asset,data,actual_placements,row['proof'])
   except AssertionError as e:origin_errors.append([key,str(e)]);continue
   for (material,i),local_triangle in zip(data['source_face_indices'],data['triangles']):
    triangle=[[v[k]+translation[k]for k in range(3)]for v in local_triangle]
    old=scene['surfaces'][material][i*3:i*3+3]
    if triangle!=[old[0],old[2],old[1]]:asset_errors.append([key,material,i])
   scene_faces+=len(data['triangles'])
  elif form=='source_grade_proxy_triangles':
   data=read(p);cid=data['contract_id']
   if cid not in contract_sets:contract_sets[cid]={json.dumps(t,separators=(',',':'))for t in scene_contracts[cid]['add_triangles_world_xyz_m']}
   if not all(json.dumps(t,separators=(',',':'))in contract_sets[cid]for t in data['triangles']):asset_errors.append([key,'contract faces'])
   contract_faces+=len(data['triangles'])
  else:
   native_assets+=1
   if a!=authored['assets'].get(key):asset_errors.append([key,'changed native cache'])
 checks['exact_runtime_surface_native_and_contract_inputs']=not asset_errors;checks['exact_world_local_origin_stage']=not origin_errors and len(origin_rows)==sum(a.get('collision_format')=='actual_scene_triangles'for a in d['assets'].values());checks['all_cases_pass_strict_original_acceptance']=all(x['pass']for x in r['routes']);assert all(v for k,v in checks.items()if k!='all_cases_pass_strict_original_acceptance'),checks
 routes={q['id']:q for q in d['routes']};coverage={}
 for cls in sorted({q['case_class']for q in d['routes']}):
  cases=[q for q in r['routes']if routes[q['id']]['case_class']==cls];coverage[cls]=dict(cases=len(cases),passed=sum(bool(q['pass'])for q in cases),failed=sum(not q['pass']for q in cases),status_counts=dict(collections.Counter(q['status']for q in cases)),ground_ray_miss_frames=sum(q['ground_ray_miss_frames']for q in cases),not_on_floor_frames=sum(q['not_on_floor_frames']for q in cases))
 failures=[dict(result=q,prepared_route=routes[q['id']])for q in r['routes']if not q['pass']];limits=['Only the declared accepted route vectors, junction turns, entries, interfaces and original negative controls are tested. Held owners and untested streets/interiors remain held.','Authored source geometry and producer proofs are preserved. Runtime terrain first applies the exact hash-bound float32-zero-area retirement ledger, then exactly ten bound winding rows using the same float32 geometric vertex sets. These ten rows affect the shared runtime rendering and collision winding; every other terrain row remains exact.','An explicit exact-world local-origin stage changes only existing scene-triangle placement origins; every world double, source index, face order and winding is preserved. Controller, loader, capsule, timing, thresholds and acceptance are unchanged. No whole-city or cart suitability claim follows from this bounded run.','Static bridge poses and barriers are tested; live mechanism operation and fluid simulation are outside scope.']
 summary=dict(schema='riverstone.actual_r18_runtime_scene_replay_validation.v1',status='PASS_ALL_DECLARED_CASES'if not failures else'FAILED_CASES_RETAINED',authored_prepared=ref(authored_path),runtime_scene=ref(scene_path),runtime_binding=ref(binding_path),local_origin_binding=ref(h/'evidence/local_origin_binding.json'),report=ref(h/'evidence/public_network_replay.json'),checks=checks,coverage=coverage,owner_status_coverage=d['coverage'].get('ownership_coverage'),exact_input_parity=dict(native_assets=native_assets,scene_triangle_references=scene_faces,contract_triangle_references=contract_faces,asset_errors=asset_errors,pose_errors=pose_errors,local_origin_errors=origin_errors),failures=failures,limits=limits);write(h/'evidence/summary.json',summary)
 external={v['path']:v['sha256']for v in d['sources'].values()};external.update({str(ROOT/p):s for p,s in d['implementation_hashes'].items()if not(ROOT/p).is_relative_to(h)});external[str(TOOL)]=sha(TOOL)
 for a in d['assets'].values():
  p=ROOT/a['render_path']
  if not p.is_relative_to(h):external[str(p)]=sha(p)
 write(h/'source_closure.json',dict(schema='riverstone.actual_runtime_replay_source_closure.v1',external_dependencies=[dict(path=p,sha256=s)for p,s in sorted(external.items())],authored_prepared=ref(authored_path),runtime_binding=ref(binding_path),local_origin_binding=ref(h/'evidence/local_origin_binding.json'),verifier=ref(TOOL)))
 files={str(p.relative_to(h)):sha(p)for p in sorted(h.rglob('*'))if p.is_file()and not any(part in ['.runtime','.godot','__pycache__']for part in p.parts)and p.name!='freeze_manifest.json'};passed=sum(bool(q['pass'])for q in r['routes']);write(h/'freeze_manifest.json',dict(schema='riverstone.actual_traversal_frozen_evidence.r01',id=h.name,status=f'QUIESCENT_{passed}_PASS_{len(failures)}_FAIL_DECLARED_CASES',owned_files=files,summary=ref(h/'evidence/summary.json'),source_closure=ref(h/'source_closure.json'),limits=limits));print(json.dumps(dict(status=summary['status'],cases=len(r['routes']),passed=passed,failed=len(failures),coverage=coverage,freeze=ref(h/'freeze_manifest.json')),indent=2))
if __name__=='__main__':main()
