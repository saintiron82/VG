"""Bound exact certified bridge contracts + current r9 natives + whole-source bay faces.
No generic guard is disabled. Unexpected intersecting collision policies reject.
"""
import pathlib,json,hashlib,copy,importlib.util,math,sys,time
import numpy as np

sys.dont_write_bytecode=True
O=pathlib.Path(__file__).resolve().parent;N=O.parent;ROOT=N.parents[4];BASE=ROOT/'world_city/concept_city_v3/traversal_r5';sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_integration.r6 import merge_patches
read=lambda p:json.loads(pathlib.Path(p).read_bytes())
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(pathlib.Path(p).resolve()),'sha256':sha(p)}
def bound(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute() else ROOT/p;assert sha(p)==r['sha256'],p;return p
spec=importlib.util.spec_from_file_location('frozen_preparer',N/'frozen_finite_preparer_r01.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);b=m.b
T=time.monotonic();req=read(O/'request.json');source=read(bound(req['sources']['selected493']));original=next(r for r in source['routes'] if r['id']=='GOAL:PORT_TO_MARKET');shortp=N/'port_replay_r01';short=read(shortp/'prepared.json');scene_path=bound(source['sources']['scene']);scene=read(scene_path);patch_path=bound(req['finite_patch']);patch=read(patch_path);merge_patches.merge([patch],m.BASE_SHA);merge_patches.validate_against_scene(scene,patch);edits={(x['material'],x['triangle_index']):x for x in patch['surface_edits']};sources={'request':ref(O/'request.json'),'final_finite_patch':ref(patch_path),'original493':req['sources']['selected493'],'base_scene':ref(scene_path),'short_prepared':ref(shortp/'prepared.json'),'short_audit':req['sources']['short_port_qa'],'original_controller':ref(BASE/'Traversal.gd'),'common_render_loader':ref(ROOT/'voxel_character/common/preview/RenderData.gd')};index_path=bound(req['sources']['visual_index']);sources['visual_index']=ref(index_path);assets_in,instances,composition=m.compose_natives(scene,read(index_path),sources);out=O/'replay_r01';assert not out.exists();out.mkdir();(out/'geometry').mkdir();(out/'evidence').mkdir();(out/'source_snapshots').mkdir();assets={};placements={};buildings={};routes=[];audits=[]
goalasset=req['source_goal_collision']['asset'];gp=bound({'path':goalasset['render_path'],'sha256':goalasset['render_sha256']});g=read(gp);sources['original_goal_collision']=ref(gp);goal_origin=np.array(req['source_goal_collision']['placement']['position_m']);goal_faces={tuple(k):np.array(t)+goal_origin for k,t in zip(g['source_face_indices'],g['triangles'])};goalboxes=g['corridor_boxes_xz_m'];expected_contracts={c['placement']['id'].split(':')[1] for c in req['required_exact_collision_contracts']};contracts={c['id']:c for c in scene.get('collision_contracts',[])};disabled={pid for c in contracts.values() for pid in c.get('disable_native_mesh_collider_ids',[])};native_cache={}
def native(key):
 if key not in native_cache:
  a=assets_in[key];p=bound({'path':a['render_path'],'sha256':a['render_sha256']});native_cache[key]=read(p)
 return native_cache[key]
def intersects(bounds,boxes):return any(b.overlaps(bounds,bb) for bb in boxes)
for route in req['routes']:
 group=route['group'];localp=shortp/'geometry'/f'{group}.json';local=read(localp);sources['short_floor_'+group]=ref(localp);faces=dict(goal_faces);local_origin=np.array(local['local_origin_proof']['applied_origin_xyz_m']);dups=0
 for f,t in zip(local['source_face_indices'],local['triangles']):
  assert f.get('replacement_index') is None and 'base_triangle_index'in f;key=(f['material'],f['base_triangle_index']);tt=np.array(t)+local_origin
  if key in faces:assert np.array_equal(faces[key],tt),'Shared source face coordinate mismatch';dups+=1
  faces[key]=tt
 for (mat,i),t in faces.items():
  raw=scene['surfaces'][mat][i*3:i*3+3];assert np.array_equal(t,np.array([raw[0],raw[2],raw[1]])),('Source face drift',mat,i)
 boxes=goalboxes+[local['selection_bounds_xz_m']]
 # Resolve the final finite patch over the same exact whole-source corridor.
 # Every affected source face is verified against the base before replacement.
 original_face_count=len(faces);resolved={};source_face_records=[];applied=[]
 for (mat,i),t in faces.items():
  row=edits.get((mat,i))
  if row is None:resolved[(mat,i,None)]=t;source_face_records.append({'material':mat,'base_triangle_index':i,'replacement_index':None})
  else:
   assert row['source_triangle_xyz_m']==scene['surfaces'][mat][i*3:i*3+3]
   applied.append({'material':mat,'base_triangle_index':i,'replacement_count':len(row['replacement_triangles_xyz_m'])})
   for j,raw in enumerate(row['replacement_triangles_xyz_m']):
    if not intersects(b.bounds(raw),boxes):continue
    resolved[(mat,i,j)]=np.array([raw[0],raw[2],raw[1]]);source_face_records.append({'material':mat,'base_triangle_index':i,'replacement_index':j})
 for (mat,i),row in edits.items():
  if mat=='water' or (mat,i)in faces:continue
  if intersects(b.bounds(row['source_triangle_xyz_m']),boxes) and any(intersects(b.bounds(t),boxes)for t in row['replacement_triangles_xyz_m']):
   raise AssertionError(('Final source edit intersects a previously unselected original corridor face',mat,i))
 for mat,verts in patch['appended_surfaces'].items():
  if mat=='water':continue
  for i in range(0,len(verts),3):
   raw=verts[i:i+3]
   if not intersects(b.bounds(raw),boxes):continue
   resolved[(mat,'append',i//3)]=np.array([raw[0],raw[2],raw[1]]);source_face_records.append({'material':mat,'appended_triangle_index':i//3})
 faces=resolved
 active_contracts={cid for cid,c in contracts.items() if any(intersects(b.bounds(t),boxes) for t in c.get('add_triangles_world_xyz_m',[]))};assert active_contracts==expected_contracts,('Unexpected/omitted collision contract',active_contracts,expected_contracts)
 # Keep original world origin, matching existing certified GOAL; do not rebase.
 triangles=[t.tolist() for t in faces.values()];arr=np.array(triangles,dtype=np.float32);assert np.all(np.any(np.cross(arr[:,1]-arr[:,0],arr[:,2]-arr[:,0])!=0,axis=1)),'Float32 zero face';geo={'schema':'riverstone.actual_scene_collision_triangles.v1','base_scene_sha256':m.BASE_SHA,'source_face_indices':source_face_records,'finite_patch_sha256':sha(patch_path),'visual_index_sha256':sha(index_path),'triangles':triangles,'whole_triangles_only':True,'height_resampling':False,'collision_local_origin_xyz_m':[0,0,0],'corridor_boxes_xz_m':boxes};geom=out/'geometry'/f'{group}.json';m.write(geom,geo);key='SCENE:R10:PORT_FULL:'+group;assets[key]={'render_path':str(geom.relative_to(ROOT)),'render_sha256':sha(geom),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_r9_resolved_scene_surface','collision_layer':1};ids=[key];nativeids=[];disabled_here=[]
 for ins in instances:
  key=ins['asset_key'];bounds=assets_in[key].get('bounds')or native(key)['bounds']
  if not intersects(b.instance_bounds(ins,bounds),boxes):continue
  if ins['id'] in disabled:
   owners={cid for cid,c in contracts.items() if ins['id'] in c.get('disable_native_mesh_collider_ids',[])};assert owners&expected_contracts,('Disabled native without retained contract',ins['id']);disabled_here.append(ins['id']);continue
  data=native(key);assert not data.get('rigid_parts'),('Unexpected dynamic rigid-part state',ins['id']);assets[key]={'render_path':assets_in[key]['render_path'],'render_sha256':assets_in[key]['render_sha256']};placements[ins['id']]=dict(ins,category='actual_native_common_mesh',collision_layer=3,yaw_deg=math.degrees(ins.get('yaw_rad',0)));ids.append(ins['id']);nativeids.append(ins['id'])
 # Exact original fixed bridge state and exact contract meshes, never synthesized.
 for c in req['required_exact_collision_contracts']+[req['required_fixed_drawbridge']]:
  pl=c['placement'];a=c['asset'];p=bound({'path':a['render_path'],'sha256':a['render_sha256']});sources['retained_'+pl['id']]=ref(p)
  if pl['id'] in placements:assert placements[pl['id']]['asset_key']==pl['asset_key'] and placements[pl['id']]['position_m']==pl['position_m']
  assets[pl['asset_key']]=a;placements[pl['id']]=pl
  if pl['id'] not in ids:ids.append(pl['id'])
 boxids=[]
 for box in scene['boxes']:
  if box['id'] in patch.get('removed_foundation_proxy_ids',[]):continue
  bounds={'min':[-v/2 for v in box['size_m']],'max':[v/2 for v in box['size_m']]}
  if intersects(b.instance_bounds(box,bounds),boxes):buildings[box['id']]={'id':box['id'],'position_m':box['position_m'],'yaw_rad':box.get('yaw_rad',0),'boxes':[bounds],'collision_layer':3};boxids.append(box['id'])
 r=b.route(route['id'],route['points'],route['source_road_ids'],route['test_scope']);r.update({k:v for k,v in route.items() if k!='both_directions'});r.update(placement_ids=ids,building_ids=boxids,minimum_allowed_feet_y_m=-1.,length_m=route['length_inside_bay_to_market_m']);routes.append(r);rev=copy.deepcopy(r);rev.update(id=r['id']+'_REVERSE',points=r['points'][::-1]);routes.append(rev);audits.append({'group':group,'source_scene_face_count':len(faces),'original_source_face_count':original_face_count,'applied_final_surface_edits':applied,'final_patch_sha256':sha(patch_path),'duplicate_source_faces_removed':dups,'original_goal_faces_reused':len(goal_faces),'exact_source_coordinate_checks':original_face_count,'contract_ids':sorted(active_contracts),'disabled_native_ids_with_exact_contract':disabled_here,'native_ids':nativeids,'box_ids':boxids,'world_origin_unchanged':[0,0,0]})
# Reuse the exact two previously tested controls and every referenced asset/placement.
for ident in ['NEGATIVE_UNBRIDGED_RIVER','NEGATIVE_ACTUAL_SOLID_WALL']:
 r=copy.deepcopy(next(x for x in short['routes'] if x['id']==ident));routes.append(r)
 for pid in r['placement_ids']:
  pl=short['placements'][pid];a=short['assets'][pl['asset_key']];bound({'path':a['render_path'],'sha256':a['render_sha256']});placements[pid]=pl;assets[pl['asset_key']]=a
 for bid in r.get('building_ids',[]):buildings[bid]=short['buildings'][bid]
implementations=[ROOT/'world_city/concept_city_v3/registered_integration/r6/merge_patches.py',pathlib.Path(__file__),N/'frozen_finite_preparer_r01.py',BASE/'prepare.py']
for name,src in [('Traversal.gd',BASE/'Traversal.gd'),('RenderData.gd',ROOT/'voxel_character/common/preview/RenderData.gd'),('Traversal.tscn',BASE/'Traversal.tscn'),('project.godot',BASE/'project.godot'),('run.sh',BASE/'run.sh'),('CartClearance.gd',N/'CartClearance.gd'),('CartClearance.tscn',N/'CartClearance.tscn')]:
 target=out/name;target.write_bytes(src.read_bytes());implementations.append(target)
snaps={}
for p in implementations:
 snap=out/'source_snapshots'/(sha(p)[:12]+'_'+p.name);snap.write_bytes(p.read_bytes());snaps[str(p.relative_to(ROOT))]=ref(snap)
for k,v in sources.items():
 source_path=pathlib.Path(v['path']);source_path=source_path if source_path.is_absolute()else ROOT/source_path;assert sha(source_path)==v['sha256'];v['path']=str(source_path)
prepared={'schema':'riverstone.r10.port_full_chain_physics.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':{str(p.relative_to(ROOT)):sha(p) for p in implementations},'implementation_snapshots':snaps,'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,'cart_fixture':req['cart_fixture'],'coverage':{'cases':len(routes),'collision_audit':audits,'native_composition':composition},'assumptions':req['limits']+['Exact original whole-triangle corridor plus bay crop, resolved final composite finite edits and actual added/removed native instances. Original three bridge contracts and fixed drawbridge state unchanged.','No suspension/load/traction/steering dynamics; rigid-envelope support and clearance only.']};m.write(out/'prepared.json',prepared);m.write(out/'evidence/preparation.json',{'prepared':ref(out/'prepared.json'),'status':'PREPARED_NOT_EXECUTED','elapsed_s':time.monotonic()-T,'coverage':prepared['coverage']});print(json.dumps({'status':'PREPARED_NOT_EXECUTED','cases':len(routes),'groups':audits,'elapsed_s':time.monotonic()-T},indent=2))
