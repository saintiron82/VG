"""Three explicitly enumerated collision frames for the one diagnosed native asset."""
import json,pathlib,hashlib,copy,math,numpy as np
D=pathlib.Path(__file__).resolve().parent;B=D.parent;ROOT=next(p for p in D.parents if(p/'voxel_character').is_dir());PRIOR=B/'east_radial_shared_frame_r01';SOURCE=B/'public_network_final_runtime_r01/prepared_runtime.json';ID='REGISTERED_WATER_CROSSING:EAST_RADIAL'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def aref(p):return dict(path=str(p),sha256=sha(p))
def can(j):return hashlib.sha256(json.dumps(j,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def put(p,j):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,separators=(',',':'),allow_nan=False)+'\n');return ref(p)
def main():
 src=json.loads(SOURCE.read_bytes());prior=json.loads((PRIOR/'representation_proof.json').read_bytes());assert ref(SOURCE)==prior['source_prepared'];g=json.loads((ROOT/prior['candidate_collision_asset']['path']).read_bytes());assert sha(ROOT/prior['candidate_collision_asset']['path'])==prior['candidate_collision_asset']['sha256']
 world=[[[v[k]+g['world_origin_xyz_m'][k]for k in range(3)]for v in t]for t in g['triangles']];assert can(world)==prior['original_world_sha256'];out=copy.deepcopy(src);key=src['placements'][ID]['asset_key'];original_pose=src['placements'][ID];routes=[r for r in out['routes']if ID in r.get('placement_ids',[])];assert len(routes)==24
 frames={};frame_cases=[]
 for route in routes:
  scene=[src['placements'][pid]for pid in route['placement_ids']if pid.startswith('SCENE:')];assert len(scene)==1;origin=tuple(scene[0]['position_m']);assert origin in [(320.,0.,304.),(320.,0.,320.),(0.,0.,0.)]
  if origin not in frames:
   tag='_'.join(str(int(n))for n in origin);asset_key=key+':shared_frame:'+tag;instance=ID if origin==(320.,0.,304.)else ID+':SHARED_FRAME:'+tag;local=[[[v[k]-origin[k]for k in range(3)]for v in t]for t in world];back=[[[v[k]+origin[k]for k in range(3)]for v in t]for t in local];assert back==world
   f=np.array(local,dtype=np.float32);ww=np.array(world);localerr=float(np.max(np.abs(f.astype(float)+origin-ww)));worlderr=float(np.max(np.abs((f+np.array(origin,dtype=np.float32)).astype(float)-ww)));bad=[]
   for i,t in enumerate(f):
    n=np.cross(t[1]-t[0],t[2]-t[0]);p=ww[i];old=np.cross(p[1]-p[0],p[2]-p[0]);
    if not np.dot(old,n)>0:bad.append(i)
   assert not bad and localerr<3.1e-5 and worlderr<3.1e-5
   ar=put(D/f'geometry/{tag}.json',dict(g,triangles=local,world_origin_xyz_m=list(origin),exact_source_world_sha256=can(world),world_roundtrip_error_m=0.))
   out['assets'][asset_key]=dict(render_path=ar['path'],render_sha256=ar['sha256'],collision_format='actual_scene_triangles');out['placements'][instance]=dict(original_pose,id=instance,asset_key=asset_key,position_m=list(origin),yaw_rad=0.,yaw_deg=0.,logical_source_instance_id=ID)
   frames[origin]=dict(origin_xyz_m=list(origin),asset=ar,asset_key=asset_key,instance_id=instance,original_logical_owner=ID,triangles=len(world),exact_world_sha256=can(back),maximum_local_float32_coordinate_error_m=localerr,maximum_forward_world_float32_coordinate_error_m=worlderr,zero_or_reversed_faces=bad)
  variant=frames[origin];route['placement_ids']=[variant['instance_id']if p==ID else p for p in route['placement_ids']];assert route['placement_ids'].count(variant['instance_id'])==1 and (variant['instance_id']==ID or ID not in route['placement_ids'])
  frame_cases.append(dict(case_id=route['id'],terrain_instance_id=scene[0]['id'],terrain_origin_xyz_m=list(origin),native_origin_xyz_m=list(origin),native_variant=variant['instance_id'],exact_source_route_points_sha256=can(route['points']),original_native_owner=ID))
 proof=put(D/'representation_proof.json',dict(status='EXACT_SOURCE_EQUIVALENT_PER_CASE_FRAMES_RUNTIME_PENDING',source_prepared=ref(SOURCE),source_scene=src['sources']['scene'],prior_world_proof=ref(PRIOR/'representation_proof.json'),source_world_sha256=can(world),frames=list(frames.values()),case_frames=frame_cases,all_terrain_assets_and_placements_unchanged=True,all_source_route_points_unchanged=True,all_native_faces_preserved_per_case=504,removed_or_added_faces=0,policy='Only one of three explicit native collider aliases is selected per affected case; each uses precisely that case terrain origin. Original visible native instance and all source collision arrays remain untouched. Aliases map to the same logical native owner.',limits=['Equivalent collision extraction only; no scene field, route point, controller or acceptance change.','The long EAST_WALL_SERVICE reverse failure at another crossing is preserved and independently diagnosed.']))
 out['sources']['east_radial_per_case_shared_frame']=aref(D/'representation_proof.json');out['sources']['east_radial_per_case_shared_frame_author']=aref(D/'prepare.py');out['sources']['east_radial_original_prepared']=aref(SOURCE);out['assumptions'].append('Explicit per-case EAST_RADIAL collider aliases share the exact existing terrain frame; all source-world faces, native rails/sides and route XYZ are preserved.')
 put(D/'prepared_all_candidate.json',out);out=copy.deepcopy(out);out['routes']=[r for r in out['routes']if r['id']in prior['affected_route_ids']];out['coverage']=dict(cases=24,scope='Every affected case in unchanged 481-source catalog.');put(D/'prepared_runtime.json',out)
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:(D/n).write_bytes((B/'public_network_final_runtime_r01'/n).read_bytes())
 (D/'evidence').mkdir();print(json.dumps(dict(proof=proof,frames=list(frames.values())),indent=2))
if __name__=='__main__':main()
