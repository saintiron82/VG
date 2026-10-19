"""Equivalent complete native collision extraction in the existing public local frame.
Every source quad/side/rail is retained; the scene and movement sources are untouched.
"""
import json,pathlib,hashlib,math,copy,numpy as np
D=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in D.parents if(p/'voxel_character').is_dir());B=D.parent;SOURCE=B/'public_network_final_runtime_r01/prepared_runtime.json'
ID='REGISTERED_WATER_CROSSING:EAST_RADIAL';ORIGIN=[320.,0.,304.]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def aref(p):return dict(path=str(p),sha256=sha(p))
def can(j):return hashlib.sha256(json.dumps(j,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def put(p,j):
 assert not p.exists();p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(j,separators=(',',':'),allow_nan=False)+'\n');return ref(p)
def main():
 source=json.loads(SOURCE.read_bytes());pose=source['placements'][ID];asset=source['assets'][pose['asset_key']];cp=ROOT/asset['render_path'];assert sha(cp)==asset['render_sha256'];cache=json.loads(cp.read_bytes());assert pose.get('scale')==[1,1,1]and' transform'not in pose
 angle=math.radians(pose['yaw_deg']);assert angle==pose['yaw_rad'];co=math.cos(angle);si=math.sin(angle);world=[];local=[];keys=[];maxround=0.;normals=[]
 for gi,g in enumerate(cache['groups']):
  for qi,q in enumerate(g['quads']):
   for half,order in enumerate([[0,2,1],[0,3,2]]):
    w=[];l=[]
    for vi in order:
     x,y,z=q[vi];p=[co*x+si*z+pose['position_m'][0],y+pose['position_m'][1],-si*x+co*z+pose['position_m'][2]];v=[p[k]-ORIGIN[k]for k in range(3)];back=[v[k]+ORIGIN[k]for k in range(3)];assert back==p,(gi,qi,p,back);w.append(p);l.append(v)
    world.append(w);local.append(l);keys.append(dict(group_index=gi,quad_index=qi,triangle_half=half,vertex_order=order,material=g['material']))
 local32=np.array(local,dtype=np.float32);ws=np.array(world);localerr=np.max(np.abs(local32.astype(float)+ORIGIN-ws));world32=(local32+np.array(ORIGIN,dtype=np.float32)).astype(float);worlderr=float(np.max(np.abs(world32-ws)));original_zero=0;new_zero=0;orientation_failures=[]
 for i,(w,l)in enumerate(zip(world,local)):
  a=np.array(w);n=np.cross(a[1]-a[0],a[2]-a[0]);f=local32[i];nf=np.cross(f[1]-f[0],f[2]-f[0]);original_zero+=int(np.all(n==0));new_zero+=int(np.all(nf==0))
  if np.dot(n,nf)<=0:orientation_failures.append(i)
 assert not orientation_failures and original_zero==new_zero==0
 assert localerr<2e-6 and worlderr<4e-5
 ar=put(D/'geometry/east_radial_complete_shared_frame.json',dict(schema='riverstone.exact_native_shared_collision_frame.v1',triangles=local,source_cache=ref(cp),source_placement=pose,world_origin_xyz_m=ORIGIN,source_face_keys=keys,source_world_triangles_sha256=can(world),original_native_triangle_count=len(world),world_roundtrip_error_m=0.))
 allcandidate=copy.deepcopy(source);allcandidate['assets'][pose['asset_key']]=dict(render_path=ar['path'],render_sha256=ar['sha256'],collision_format='actual_scene_triangles');allcandidate['placements'][ID]=dict(pose,position_m=ORIGIN,yaw_deg=0.,yaw_rad=0.)
 if 'transform'in allcandidate['placements'][ID]:del allcandidate['placements'][ID]['transform']
 affected=[r['id']for r in source['routes']if ID in r.get('placement_ids',[])];selected=[r for r in source['routes']if r['id'].startswith('CROSSING_EAST_RADIAL_')or r['id'].startswith('NEGATIVE_RAIL_EAST_RADIAL_')];assert len(selected)==8
 for r in selected:
  for pid in r['placement_ids']:
   if pid.startswith('SCENE:'):assert source['placements'][pid]['position_m']==ORIGIN
 proof=put(D/'representation_proof.json',dict(schema='riverstone.exact_native_shared_frame_proof.v1',source_prepared=ref(SOURCE),source_scene=source['sources']['scene'],source_native_cache=ref(cp),source_pose=pose,candidate_collision_asset=ar,candidate_pose=allcandidate['placements'][ID],native_triangles=len(world),native_quad_count=len(world)//2,all_native_sides_rails_and_floors_carried=True,deleted_triangles=0,added_triangles=0,original_world_sha256=can(world),reconstructed_world_sha256=can([[[v[k]+ORIGIN[k]for k in range(3)]for v in t]for t in local]),exact_world_roundtrip_error_m=0.,max_float32_local_surface_coordinate_error_m=float(localerr),max_float32_forward_world_coordinate_error_m=worlderr,source_zero_faces=original_zero,new_zero_faces=new_zero,orientation_reversals=orientation_failures,affected_route_ids=affected,first_selected_route_ids=[r['id']for r in selected],scene_binding_changes=False,representation='Existing actual_scene_triangles format with every native source quad triangulated in original common-loader order after exact source rigid transform; shared power-of-two translation, no runtime rotated native frame.',limits=['Only collision extraction recipe changes. The actual scene hash, visual native assets, source-world vertex set and controller remain unchanged.','All 24 source routes whose local crop contains this asset are affected and require regression; first subset contains the six direct lane routes and two rail negatives.']))
 allcandidate['sources']['east_radial_shared_frame_recipe']=aref(D/'representation_proof.json');allcandidate['sources']['east_radial_shared_frame_author']=aref(D/'prepare.py');allcandidate['sources']['east_radial_shared_frame_input']=aref(SOURCE)
 allcandidate['assumptions'].append('Only EAST_RADIAL native collider is equivalently extracted in the public collision frame, preserving every source-world native face and all side/rail collisions. Exact parity proof is bound.')
 put(D/'prepared_all_candidate.json',allcandidate)
 direct=copy.deepcopy(allcandidate);direct['routes']=selected;direct['coverage']=dict(cases=8,subset_of_source=481,affected_total=len(affected),positive=6,negative=2);put(D/'prepared_runtime.json',direct)
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:(D/name).write_bytes((B/'public_network_final_runtime_r01'/name).read_bytes())
 (D/'evidence').mkdir();print(json.dumps(proof));print(json.dumps(dict(native_triangles=len(world),local_error=float(localerr),world32error=worlderr,affected=len(affected))))
if __name__=='__main__':main()
