"""Bounded actual R6 collision crops. Requires explicit parent scene hash."""
import json,pathlib,hashlib,sys,math,copy,shutil,argparse,importlib.util
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5'
spec=importlib.util.spec_from_file_location('baseline_prepare',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
sha=b.sha;read=b.read;write=b.write;ref=b.ref

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scene',required=True);parser.add_argument('--scene-sha256',required=True);args=parser.parse_args();scene_path=pathlib.Path(args.scene).resolve();assert sha(scene_path)==args.scene_sha256
 plan=read(H/'route_plan.json');sources=copy.deepcopy(plan['sources'])
 for source in sources.values():assert sha(source['path'])==source['sha256'],source['path']
 scene=read(scene_path);assert scene.get('bridge_mechanism');contracts=scene.get('collision_contracts',[]);assert len(contracts)==1 and contracts[0]['id']=='SOUTHERN_FINITE_GRADED_LANE';contract=contracts[0]
 profile_ref=contract['source_profile'];profile_path=ROOT/profile_ref['path'];assert sha(profile_path)==profile_ref['sha256'];profile=read(profile_path);assert contract['add_triangles_world_xyz_m']==[t['triangle_xyz_m'] for t in profile['triangles']]
 disabled=set(contract['disable_native_mesh_collider_ids']);kept=set(contract['keep_native_mesh_collider_ids']);assert disabled=={'BRIDGE_MAIN_RIVER:SOUTH_VISIBLE_GRADED_COVER'};assert kept=={'BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED'};scene_instances={p['id']:p for p in scene['common_instances']};assert disabled|kept<=scene_instances.keys()
 normalized=read(sources['southern_normalized_pack']['path'])
 for p in normalized['placements']:
  actual=scene_instances[p['id']];asset=scene['common_assets'][actual['asset_key']];expected=normalized['assets'][p['asset_key']];assert asset['render_sha256']==expected['render_sha256'];assert actual['position_m']==p['position_m'];assert abs(actual['yaw_rad']-p['yaw_rad'])<1e-12;assert actual['collision_policy']==p['collision_policy'];assert sha(ROOT/asset['render_path'])==asset['render_sha256']
 merchant=read(sources['merchant_pack']['path']);accept=read(sources['subset_acceptance']['path']);assert all(p['id'] in scene_instances for p in merchant['placements']);assert not set(accept['retired_source_ids'])&scene_instances.keys();assert set(accept['inactive_original_ids'])<=scene_instances.keys()
 sources.update(actual_r6_scene=ref(scene_path),route_plan=ref(H/'route_plan.json'),southern_contract_profile=ref(profile_path),baseline_controller=ref(BASE/'Traversal.gd'),common_loader=ref(ROOT/'voxel_character/common/preview/RenderData.gd'))
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:shutil.copy2(BASE/name,H/name);assert sha(H/name)==sha(BASE/name)
 assets={};placements={};buildings={};render_cache={};audit=[];routes=copy.deepcopy(plan['routes']);positive=[r for r in routes if 'expected_failure' not in r]
 def render(key,asset):
  if key not in render_cache:
   p=ROOT/asset['render_path'];assert sha(p)==asset['render_sha256'];render_cache[key]=read(p)
  return render_cache[key]
 for number,r in enumerate(positive):
  if number%2:
   r['placement_ids']=positive[number-1]['placement_ids'];r['building_ids']=positive[number-1]['building_ids'];continue
  box=b.bounds(r['points']);box=[box[0]-6,box[1]-6,box[2]+6,box[3]+6];r['collision_bounds_xz_m']=box;triangles=[];faces=[];water=0
  for material,vertices in scene['surfaces'].items():
   assert len(vertices)%3==0
   for i in range(0,len(vertices),3):
    tri=vertices[i:i+3]
    if not b.overlaps(b.bounds(tri),box):continue
    if material=='water':water+=1;continue
    triangles.append([tri[0],tri[2],tri[1]]);faces.append([material,i//3])
  path=H/'geometry'/(r['id']+'.json');write(path,{'schema':'riverstone.actual_r6_collision_crop.v1','scene_sha256':args.scene_sha256,'source_face_indices':faces,'triangles':triangles,'selection_bounds_xz_m':box,'height_resampling':False,'whole_triangles_only':True})
  key='SCENE:'+r['id'];assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_r6_scene_surface','collision_layer':1};r['placement_ids'].append(key)
  # Honor explicit finite collision contracts, without applying display winding conversion again.
  colltris=[t for t in contract['add_triangles_world_xyz_m'] if b.overlaps(b.bounds(t),box)]
  if colltris:
   assert len(colltris)==8
   key='CONTRACT:SOUTHERN_FINITE_GRADED_LANE';path=H/'geometry/contract_southern_lane.json';write(path,{'source_profile':ref(profile_path),'triangles':colltris,'direct_godot_collision_winding':True});assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'source_grade_proxy_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'declared_supported_continuous_road_cover','collision_layer':1};r['placement_ids'].append(key)
  natives=[];skipped=[]
  for instance in scene['common_instances']:
   assert instance.get('scale',[1,1,1])==[1,1,1]
   key=instance['asset_key'];asset=scene['common_assets'][key];bb=asset.get('bounds')
   if bb is None:bb=render(key,asset)['bounds']
   if not b.overlaps(b.instance_bounds(instance,bb),box):continue
   if instance['id'] in disabled:skipped.append(instance['id']);continue
   data=render(key,asset);assert not data.get('rigid_parts'),'Explicit rigid-part pose binding is required'
   assets[key]={'render_path':asset['render_path'],'render_sha256':asset['render_sha256']};placements[instance['id']]=dict(instance,category='actual_native_common_mesh',collision_layer=3,yaw_deg=math.degrees(instance.get('yaw_rad',0)));r['placement_ids'].append(instance['id']);natives.append(instance['id'])
  for item in scene['boxes']:
   bb={'min':[-v/2 for v in item['size_m']],'max':[v/2 for v in item['size_m']]}
   if not b.overlaps(b.instance_bounds(item,bb),box):continue
   buildings[item['id']]={'id':item['id'],'position_m':item['position_m'],'yaw_rad':item.get('yaw_rad',0),'boxes':[bb],'collision_layer':3};r['building_ids'].append(item['id'])
  pivot=read(CITY/'assemblies/waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json')['bridge_to_world']['translation'];assert not b.overlaps([pivot[0]-25,pivot[2]-25,pivot[0]+25,pivot[2]+25],box),'Central mechanism belongs to a separate future fixture'
  if colltris:assert kept<=set(natives) and disabled==set(skipped)
  audit.append({'route':r['id'],'bounds':box,'exact_scene_triangles':len(triangles),'native_instance_ids':natives,'remaining_actual_box_ids':r['building_ids'],'water_display_triangles_excluded':water,'explicitly_disabled_visual_collider_ids':skipped,'added_contract_triangles':len(colltris),'whole_original_triangles_preserved':True})
 # Reuse exact already-checked negative geometry. No fresh common compile.
 control=read(BASE/'revisions/r02/prepared.json')
 for r in routes:
  if 'expected_failure' not in r:continue
  for pid in r['placement_ids']:
   p=control['placements'][pid];key=p['asset_key'];assets[key]=control['assets'][key];placements[pid]=p
 assert sha(scene_path)==args.scene_sha256
 implementations=[H/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare_scene.py','plan_routes.py']]+[BASE/'prepare.py']
 result={'schema':'riverstone.r6.prepared_seven_merchant_chains.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':{str(p.relative_to(ROOT)):sha(p) for p in implementations},'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,'coverage':dict(plan['coverage'],collision_audit=audit),'assumptions':['Exact parent-sealed composed R6 triangles and actual local native meshes, plus the explicit southern finite collision contract.','The native sampled cover collider is disabled exactly as declared in the scene; derived fixed native collider remains active.','Same original generic no-step CharacterBody3D controller, common RenderData loader, gravity, snap and contact checks; no within-route correction.','All seven accepted gate chains tested both ways to actual closed-door standing lips; 39 branches and 12 inactive properties not tested.','No full-width/cart, native closed-leaf interior, central moving-span or live-city NPC guarantee.']}
 write(H/'prepared.json',result);write(H/'evidence/preparation.json',{'status':'prepared_not_executed','scene':ref(scene_path),'prepared':ref(H/'prepared.json'),'collision_audit':audit,'total_cases':len(routes),'controller_sha256':sha(H/'Traversal.gd'),'native_loader_sha256':sha(H/'RenderData.gd')});print(json.dumps({'cases':len(routes),'assets':len(assets),'native_placements':len(placements),'actual_boxes':len(buildings),'prepared':ref(H/'prepared.json')}))
if __name__=='__main__':main()
