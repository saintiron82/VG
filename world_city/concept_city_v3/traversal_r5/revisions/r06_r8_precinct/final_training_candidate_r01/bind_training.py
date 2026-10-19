"""Bind one declared complete training collision contract; preserve all other inputs."""
import copy,hashlib,json,pathlib,shutil
H=pathlib.Path(__file__).resolve().parent;B=H.parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
base=B/'final_road_contact_diagnosis_r01/composed_candidate_r01/prepared_all481.json';goals=B/'primary_goals_runtime_r01/prepared_runtime.json';hp=ROOT/'world_city/concept_city_v3/assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01/training_collision_r01/candidate_r02/integration_handoff.json'
assert sha(base)=='54c0813d08741561016cc00ecbe5248ef4e60df88459b1bb193a3cd53194cf26';assert sha(hp)=='2529df9d9c63e9f6ca61cf12e6547191535e7d14b2b74b6542879149ce7ca6c1'
h=read(hp)
for r in h.values():
 if isinstance(r,dict)and'path'in r and'sha256'in r:assert sha(ROOT/r['path'])==r['sha256']
c=read(ROOT/h['collision_contract']['path']);native='TRAIN:r09:fine';assert c['native_placement_id']==native and c['disable_native_mesh_collider_ids']==[native];assert c['replacement_transform']==dict(position_m=[-330,18,-180],yaw_rad=0,scale=[1,1,1]);w=read(ROOT/c['replacement_world_mesh']['path']);assert w['triangles']==c['add_triangles_world_xyz_m'];asset=H/'training_complete_collision.json';write(asset,dict(contract_id=c['id'],triangles=w['triangles'],direct_godot_collision_winding=True))
a=read(base);g=read(goals);result=copy.deepcopy(a)
for collection in ['assets','placements','buildings']:
 for key,value in g[collection].items():
  if key in result[collection]:assert result[collection][key]==value,(collection,key)
  else:result[collection][key]=copy.deepcopy(value)
result['routes']+=copy.deepcopy(g['routes']);assert len(result['routes'])==487
pose=result['placements'][native];assert pose['position_m']==[-330,18,-180]and pose['yaw_rad']==0 and pose['scale']==[1,1,1];assert result['assets'][pose['asset_key']]['render_sha256']==c['native_source']['sha256']
key='DECLARED_TRAINING_COMPLETE_R01';result['assets'][key]=dict(render_path=str(asset.relative_to(ROOT)),render_sha256=sha(asset),collision_format='source_grade_proxy_triangles');result['placements'][native]=dict(id=native,asset_key=key,position_m=[0,0,0],yaw_rad=0,scale=[1,1,1],collision_layer=3,category='declared_exact_collision_contract')
result['sources']['training_contract']=dict(path=str(ROOT/h['collision_contract']['path']),sha256=h['collision_contract']['sha256']);result['sources']['training_handoff']=dict(path=str(hp),sha256=sha(hp));result['sources']['training_binder']=dict(path=str(pathlib.Path(__file__)),sha256=sha(pathlib.Path(__file__)))
result['assumptions'].append('Explicit additional training complete collision contract replaces only TRAIN:r09:fine in the derived collision recipe. The source visual scene remains exact; all retained native side, bottom and guard faces are in this complete replacement. No controller or route coordinate changes.')
for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:shutil.copyfile(B/'public_network_final_runtime_r01'/name,H/name)
(H/'evidence').mkdir();write(H/'prepared_all487.json',result)
changed=[r['id']for r in result['routes']if native in r['placement_ids']];assert len(changed)==6
controls=[r['id']for r in a['routes']if r['id'].startswith('NEGATIVE_')];assert len(controls)==15
subset=copy.deepcopy(result);subset['routes']=[r for r in result['routes']if r['id']in changed+controls];write(H/'prepared_runtime.json',subset)
write(H/'binding_review.json',dict(source_prepared=ref(base),source_goals=ref(goals),training_handoff=ref(hp),contract=ref(ROOT/h['collision_contract']['path']),selected=ref(H/'prepared_all487.json'),replay=ref(H/'prepared_runtime.json'),changed_training_case_ids=changed,preserved_control_ids=controls,triangles=len(w['triangles']),native_visual_source_unchanged=True,source_scene=result['sources']['scene'],controller_and_route_coordinates_unchanged=True))
print(json.dumps(dict(cases=len(subset['routes']),changed=changed,selected=ref(H/'prepared_all487.json'))))
