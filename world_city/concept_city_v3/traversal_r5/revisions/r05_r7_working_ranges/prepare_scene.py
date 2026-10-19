"""Prepare exact, bounded R7 scene crops only after the lead supplies its hash."""
import pathlib,json,hashlib,math,sys,copy,importlib.util,argparse,collections
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';R04=BASE/'revisions/r04_r6_winding'
spec=importlib.util.spec_from_file_location('r5_base_prepare',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
sha=b.sha;read=b.read;ref=b.ref
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scene',required=True);parser.add_argument('--scene-sha256',required=True);args=parser.parse_args();scene_path=pathlib.Path(args.scene).resolve();assert sha(scene_path)==args.scene_sha256
 plan=read(H/'route_plan.json');sources=copy.deepcopy(plan['sources'])
 for source in sources.values():assert sha(source['path'])==source['sha256'],source['path']
 scene=read(scene_path);assert scene.get('bridge_mechanism');base=read(CITY/'evidence/visual_registered_common_r6_apron_r01/scene.json');assert sha(CITY/'evidence/visual_registered_common_r6_apron_r01/scene.json')=='6e441b9ca417db63dccbb0bbccd48aa59e6a2a62079cdeeb3e5440d78f654844';assert scene['collision_contracts']==base['collision_contracts'];del base
 contracts=scene['collision_contracts'];disabled={pid for c in contracts for pid in c.get('disable_native_mesh_collider_ids',[])}
 sourcepack=read(sources['working_range_pack']['path']);instances={p['id']:p for p in scene['common_instances']};pose_checks=[]
 for p in sourcepack['placements']:
  actual=instances[p['id']];expected_asset=sourcepack['assets'][p['asset_key']];asset=scene['common_assets'][actual['asset_key']];assert asset['render_sha256']==expected_asset['render_sha256'];assert actual['position_m']==p['position_m'];assert abs(actual.get('yaw_rad',0)-p.get('yaw_rad',0))<1e-12;assert actual.get('scale',[1,1,1])==[1,1,1];assert sha(ROOT/asset['render_path'])==asset['render_sha256'];pose_checks.append(p['id'])
 assert len(pose_checks)==4 and len(sourcepack['actual_doors'])==15
 courtpack=read(sources['court_prop_pack']['path']);court_pose_checks=[]
 for p in courtpack['placements']:
  actual=instances[p['id']];expected=courtpack['assets'][p['asset_key']];asset=scene['common_assets'][actual['asset_key']];assert asset['render_sha256']==expected['render_sha256'];assert actual['position_m']==p['position_m'];assert abs(actual.get('yaw_rad',0)-p.get('yaw_rad',0))<1e-12;assert sha(ROOT/asset['render_path'])==asset['render_sha256'];court_pose_checks.append(p['id'])
 assert len(court_pose_checks)==6
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:assert sha(H/name)==sha(BASE/name)
 sources.update(actual_r7_scene=ref(scene_path),route_plan=ref(H/'route_plan.json'),baseline_controller=ref(BASE/'Traversal.gd'),common_loader=ref(ROOT/'voxel_character/common/preview/RenderData.gd'),prior_r6_pass=ref(R04/'freeze_manifest.json'))
 assets={};placements={};buildings={};render_cache={};routes=copy.deepcopy(plan['routes']);groups=collections.defaultdict(list);audit=[]
 for r in routes:
  if 'expected_failure' not in r:groups[r['holding_id']].append(r)
 assert len(groups)==2
 def render(key,asset):
  if key not in render_cache:
   path=ROOT/asset['render_path'];assert sha(path)==asset['render_sha256'];render_cache[key]=read(path)
  return render_cache[key]
 for number,(holding,group) in enumerate(sorted(groups.items())):
  box=b.bounds([v for r in group for v in r['points']]);box=[box[0]-6,box[1]-6,box[2]+6,box[3]+6];triangles=[];faces=[];water=0;selected_ids=[];box_ids=[]
  for material,vertices in scene['surfaces'].items():
   assert len(vertices)%3==0
   for i in range(0,len(vertices),3):
    tri=vertices[i:i+3]
    if not b.overlaps(b.bounds(tri),box):continue
    if material=='water':water+=1;continue
    triangles.append([tri[0],tri[2],tri[1]]);faces.append([material,i//3])
  path=H/'geometry'/f'holding_{number:02d}.json';write(path,{'schema':'riverstone.actual_r7_collision_crop.v1','scene_sha256':args.scene_sha256,'source_face_indices':faces,'triangles':triangles,'selection_bounds_xz_m':box,'height_resampling':False,'whole_triangles_only':True})
  key='SCENE:'+holding;assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_r7_scene_surface','collision_layer':1};selected_ids.append(key)
  # Respect every finite collision contract. None should intersect these two inland crops.
  relevant_contracts=[]
  for c in contracts:
   tris=[t for t in c.get('add_triangles_world_xyz_m',[]) if b.overlaps(b.bounds(t),box)]
   if tris:
    key='CONTRACT:'+c['id'];path=H/'geometry'/f'contract_{number:02d}_{len(relevant_contracts):02d}.json';write(path,{'scene_contract_id':c['id'],'triangles':tris,'direct_godot_collision_winding':True});assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'source_grade_proxy_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'declared_scene_collision_contract','collision_layer':1};selected_ids.append(key);relevant_contracts.append(c['id'])
  skipped=[];native_ids=[]
  for item in scene['common_instances']:
   assert item.get('scale',[1,1,1])==[1,1,1];key=item['asset_key'];asset=scene['common_assets'][key];bb=asset.get('bounds')
   if bb is None:bb=render(key,asset)['bounds']
   if not b.overlaps(b.instance_bounds(item,bb),box):continue
   if item['id'] in disabled:skipped.append(item['id']);continue
   data=render(key,asset);assert not data.get('rigid_parts'),'Explicit rigid pose extraction is needed'
   assets[key]={'render_path':asset['render_path'],'render_sha256':asset['render_sha256']};placements[item['id']]=dict(item,category='actual_native_common_mesh',collision_layer=3,yaw_deg=math.degrees(item.get('yaw_rad',0)));selected_ids.append(item['id']);native_ids.append(item['id'])
  for item in scene['boxes']:
   bb={'min':[-v/2 for v in item['size_m']],'max':[v/2 for v in item['size_m']]}
   if not b.overlaps(b.instance_bounds(item,bb),box):continue
   buildings[item['id']]={'id':item['id'],'position_m':item['position_m'],'yaw_rad':item.get('yaw_rad',0),'boxes':[bb],'collision_layer':3};box_ids.append(item['id'])
  assert all(p['id'] in native_ids for p in sourcepack['placements'] if p['holding_id']==holding)
  assert not relevant_contracts,'New working ranges unexpectedly intersect distant bridge contract'
  for r in group:r['placement_ids']=list(selected_ids);r['building_ids']=list(box_ids);r['collision_bounds_xz_m']=box
  audit.append({'holding_id':holding,'routes':len(group),'bounds':box,'exact_scene_triangles':len(triangles),'native_instance_ids':native_ids,'actual_box_ids':box_ids,'water_display_triangles_excluded':water,'disabled_visual_colliders':skipped,'added_contract_ids':relevant_contracts})
 control=read(R04/'prepared.json')
 for r in routes:
  if 'expected_failure' not in r:continue
  for pid in r['placement_ids']:
   p=control['placements'][pid];key=p['asset_key'];assets[key]=control['assets'][key];placements[pid]=p
 implementations=[H/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare_scene.py','plan_routes.py']]+[BASE/'prepare.py']
 result={'schema':'riverstone.r7.prepared_working_range_chains.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':{str(p.relative_to(ROOT)):sha(p) for p in implementations},'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,'coverage':dict(plan['coverage'],collision_audit=audit),'assumptions':['Exact parent-sealed composed R7 scene triangles and actual nearby native meshes, including native closed door leaves and finite body holes.','Original generic no-step CharacterBody3D controller, common RenderData loader, gravity, snap and strict support checks. No within-route correction.','All 15 source external standing lips and both court entries tested in both directions, plus actual wall/water controls.','No native closed-door/interior, full-width/cart, moving central span or live-city actor guarantee.']}
 assert sha(scene_path)==args.scene_sha256;write(H/'prepared.json',result);write(H/'evidence/preparation.json',{'status':'prepared_not_executed','scene':ref(scene_path),'prepared':ref(H/'prepared.json'),'collision_audit':audit,'exact_native_poses_checked':pose_checks,'exact_court_prop_poses_checked':court_pose_checks,'total_cases':len(routes),'controller_sha256':sha(H/'Traversal.gd'),'native_loader_sha256':sha(H/'RenderData.gd')});print(json.dumps({'cases':len(routes),'assets':len(assets),'placements':len(placements),'boxes':len(buildings),'prepared':ref(H/'prepared.json')}))
if __name__=='__main__':main()
