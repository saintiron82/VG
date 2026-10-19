"""Finite R8 candidate, original mesh/controller baseline. No source edits."""
import pathlib,json,hashlib,math,sys,copy,importlib.util
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';SRC=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02'
spec=importlib.util.spec_from_file_location('base_prepare',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
sha,read,ref,write=b.sha,b.read,b.ref,b.write
SCENE=CITY/'evidence/r8_precinct_preflight/scene.json';EXPECTED='8854181bee8ee44d162e537a188157a42474d0e976dcd7b0f999d33294748beb'
def main():
 assert sha(SCENE)==EXPECTED
 seal=SRC/'freeze_manifest.json';assert sha(seal)=='3c54b69f6852c1adbb1cc0ebabf449e66048e8386bef5e2a88ec0c888939bdb1'
 refs={}
 def check(v):
  if isinstance(v,dict):
   if 'path'in v and 'sha256'in v:
    p=pathlib.Path(v['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==v['sha256'],str(p);refs[str(p.relative_to(ROOT))]=v['sha256']
   for a in v.values():check(a)
  elif isinstance(v,list):
   for a in v:check(a)
 check(read(seal));pack=read(SRC/'resolved_placements.json');handoff=read(SRC/'ownership_handoff.json');scene=read(SCENE)
 stair=next(p for p in pack['placements']if p['role']=='real_neighborhood_stair');stair_id=stair['id']
 def world(x,z,y):return b.transform([x,y-8.1,z],stair)
 # Landing centres and actual footprint ends, derived from the native source boxes.
 collar=read(SRC/'collar_design.json');a,c=collar['triangles'][0]['triangle_xyz_m'][:2];public=[(u+v)/2 for u,v in zip(a,c)]
 stair_line=[public,world(0,0,8.1),world(0,.6,8.1),world(0,5.7,10.05),world(0,10.8,12),world(0,11.4,12)]
 routes=[]
 def pair(ident,points,group,scope,**extra):
  r=b.route(ident,points,['NORTH_BACK_LANE'if group=='estate'else 'A_EAST_GUEST_GARDEN:1'],scope);r.update(group=group,**extra);routes.append(r);q=copy.deepcopy(r);q.update(id=ident+'_REVERSE',points=list(reversed(points)));routes.append(q)
 pair('R8_STAIR_CENTER',stair_line,'estate','Exact private collar, native two-flight stair and upper native landing.')
 for x,label in [(-.8,'LEFT'),(.8,'RIGHT')]:
  pair('R8_STAIR_EDGE_'+label,[world(x,.6,8.1),world(x,5.7,10.05),world(x,10.8,12)],'estate','Native stair edge line: capsule edge 0.1 m inside the 2.4 m clear width.')
 estate=next(r for r in handoff['internal_routes']if r['holding_id'].startswith('B03'));xyz=[[x,12,z]for x,z in reversed(estate['polylines_xz_m'][0])];assert math.dist(xyz[0],stair_line[-1])<1e-10
 pair('R8_ESTATE_PUBLIC_TO_PRODUCTIVE_ROUTE',stair_line+xyz[1:],'estate','Complete source public collar/stair then exact reversed internal productive holding route.')
 guest=next(r for r in handoff['internal_routes']if r['holding_id'].startswith('A_EAST'));pair('R8_GUEST_PRODUCTIVE_ROUTE',[[x,8,z]for x,z in guest['polylines_xz_m'][0]],'guest','Exact handed-off guest-garden gate route in the actual staged scene.')
 for x,label in [(-2,'LEFT'),(2,'RIGHT')]:
  r=b.route('NEGATIVE_NATIVE_STAIR_GUARD_'+label,[world(0,5.7,10.05),world(x,5.7,10.05)],['NATIVE_STAIR'],'Attempt to cross actual 0.3 m native side guard at the middle landing.');r.update(group='estate',expected_failure='blocked',expected_contact_id=stair_id);routes.append(r)
 controls=read(BASE/'revisions/r04_r6_winding/prepared.json')
 for ident in ['NEGATIVE_UNBRIDGED_RIVER','NEGATIVE_ACTUAL_SOLID_WALL']:
  r=copy.deepcopy(next(r for r in controls['routes']if r['id']==ident));r['group']='isolated_control';routes.append(r)
 pair('R8_STAIR_STOP_RESTART',stair_line,'estate','Same centreline and original walking method, with separate one-second zero-input holds at the lower and middle landings.',pause_points_xyz_m=[world(0,.6,8.1),world(0,5.7,10.05)],pause_frames=60)
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:assert sha(H/n)==sha(BASE/n)
 assets={};placements={};buildings={};cache={};audit=[];instances={p['id']:p for p in scene['common_instances']};pose_checks=[]
 for p in pack['placements']:
  actual=instances[p['id']];asset=scene['common_assets'][actual['asset_key']];assert asset['render_sha256']==p['cache']['sha256'];assert actual['position_m']==p['position_m'];assert actual.get('yaw_rad',0)==p.get('yaw_rad',0);assert actual.get('scale',[1,1,1])==[1,1,1];pose_checks.append(p['id'])
 disabled={pid for c in scene.get('collision_contracts',[])for pid in c.get('disable_native_mesh_collider_ids',[])}
 def render(key,asset):
  if key not in cache:
   p=ROOT/asset['render_path'];assert sha(p)==asset['render_sha256'];cache[key]=read(p)
  return cache[key]
 for group in ['estate','guest']:
  rs=[r for r in routes if r['group']==group];bb=b.bounds([v for r in rs for v in r['points']]);bb=[bb[0]-6,bb[1]-6,bb[2]+6,bb[3]+6];tris=[];faces=[];water=0
  for material,vertices in scene['surfaces'].items():
   for i in range(0,len(vertices),3):
    t=vertices[i:i+3]
    if not b.overlaps(b.bounds(t),bb):continue
    if material=='water':water+=1;continue
    tris.append([t[0],t[2],t[1]]);faces.append([material,i//3])
  path=H/'geometry'/(group+'.json');write(path,{'scene_sha256':EXPECTED,'source_face_indices':faces,'triangles':tris,'selection_bounds_xz_m':bb,'whole_triangles_only':True,'height_resampling':False});key='SCENE:R8:'+group
  assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_r8_scene_surface','collision_layer':1};ids=[key];natives=[];boxids=[]
  for item in scene['common_instances']:
   key=item['asset_key'];asset=scene['common_assets'][key];bounds=asset.get('bounds')or render(key,asset)['bounds']
   if not b.overlaps(b.instance_bounds(item,bounds),bb):continue
   assert item['id']not in disabled,'Nearby declared collision policy requires explicit extraction'
   data=render(key,asset);assert not data.get('rigid_parts');assets[key]={'render_path':asset['render_path'],'render_sha256':asset['render_sha256']};placements[item['id']]=dict(item,category='actual_native_common_mesh',collision_layer=3,yaw_deg=math.degrees(item.get('yaw_rad',0)));ids.append(item['id']);natives.append(item['id'])
  for item in scene['boxes']:
   bounds={'min':[-v/2 for v in item['size_m']],'max':[v/2 for v in item['size_m']]}
   if not b.overlaps(b.instance_bounds(item,bounds),bb):continue
   buildings[item['id']]={'id':item['id'],'position_m':item['position_m'],'yaw_rad':item.get('yaw_rad',0),'boxes':[bounds],'collision_layer':3};boxids.append(item['id'])
  for c in scene.get('collision_contracts',[]):assert not any(b.overlaps(b.bounds(t),bb)for t in c.get('add_triangles_world_xyz_m',[]))
  for r in rs:r.update(placement_ids=ids,building_ids=boxids,collision_bounds_xz_m=bb)
  audit.append({'group':group,'triangles':len(tris),'native_ids':natives,'box_ids':boxids,'bounds':bb,'water_display_triangles_excluded':water})
 for r in routes:
  if r['group']!='isolated_control':continue
  for pid in r['placement_ids']:
   p=controls['placements'][pid];assets[p['asset_key']]=controls['assets'][p['asset_key']];placements[pid]=p
 sources={'actual_r8_candidate':ref(SCENE),'phase02_freeze':ref(seal),'phase02_pack':ref(SRC/'resolved_placements.json'),'ownership_handoff':ref(SRC/'ownership_handoff.json'),'stair_source':ref(ROOT/stair['source']['path']),'collar':ref(SRC/'collar_design.json'),'original_controller':ref(BASE/'Traversal.gd'),'common_loader':ref(ROOT/'voxel_character/common/preview/RenderData.gd'),'prior_r7_pass':ref(BASE/'revisions/r05_r7_working_ranges/freeze_initial_result.json')}
 coverage={'cases':len(routes),'baseline_cases':14,'stop_restart_cases':2,'collision_audit':audit,'actual_native_poses_verified':pose_checks,'stair_risers':26,'riser_height_m':.15,'tread_depth_m':.3,'clear_width_m':2.4,'stair_local_to_world':stair,'source_references_verified':len(refs)}
 implementations={str(p.relative_to(ROOT)):sha(p)for p in [H/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','PauseTraversal.gd','PauseTraversal.tscn','project.godot','run.sh','prepare_scene.py','run_capture.py']]+[BASE/'prepare.py']}
 result={'schema':'riverstone.r8.precinct_physics.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':implementations,'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,'coverage':coverage,'assumptions':['Exact staged R7 plus phase02 geometry; final whole-city integration requires scene rebinding.','Unchanged no-step CharacterBody3D movement and native RenderData triangle loading.','Pause wrapper changes input only; strict support remains required.','Source stairs remain actual mesh collision; no ramps or invented support.','Centre and near-edge samples do not certify all continuous routes, carts, NPCs or closed interiors.']}
 write(H/'prepared.json',result);write(H/'evidence/preparation.json',{'status':'prepared_not_executed','prepared':ref(H/'prepared.json'),'scene':ref(SCENE),'coverage':coverage,'verified_phase02_inputs':refs});print(json.dumps({'cases':len(routes),'assets':len(assets),'placements':len(placements),'boxes':len(buildings),'collision_groups':[{k:v for k,v in a.items()if k not in ['native_ids','box_ids']}for a in audit]}))
if __name__=='__main__':main()
