"""Actual compiled port infill and exact top-retirement candidate, unchanged controller."""
import pathlib,json,hashlib,copy,shutil
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());OLD=H.parent/'port_bridge_candidate_r02';SRC=ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/port_approach_r01';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'));f.write('\n')
def main():
 d=json.loads((OLD/'prepared_runtime.json').read_bytes());pack=json.loads((SRC/'resolved_placements_r02.json').read_bytes());con=json.loads((SRC/'collision_contract_r02.json').read_bytes());own=json.loads((SRC/'ownership_requests_r03.json').read_bytes());(H/'geometry').mkdir();(H/'evidence').mkdir();ret={tuple(r['runtime_source_key']):r for r in own['current_top_retirement_requests']};records=[]
 for key,ass in d['assets'].items():
  if ass.get('collision_format')!='actual_scene_triangles':continue
  src=ROOT/ass['render_path'];data=json.loads(src.read_bytes());tt=[];keys=[];edited=[]
  for k,t in zip(data['source_face_indices'],data['triangles']):
   r=ret.get(tuple(k))
   if r:
    assert [t[0],t[2],t[1]]==r['source_triangle_xyz_m'];edited.append(k)
    for tri in r['replacement_triangles_xyz_m']:tt.append([tri[0],tri[2],tri[1]]);keys.append(k)
   else:tt.append(t);keys.append(k)
  target=H/'geometry'/(hashlib.sha256(key.encode()).hexdigest()[:16]+'.json');write(target,dict(data,triangles=tt,source_face_indices=keys,source_top_retirement_candidate=ref(SRC/'ownership_requests_r03.json')));ass.update(render_path=str(target.relative_to(ROOT)),render_sha256=sha(target));records.append(dict(asset=key,source=ref(src),candidate=ref(target),edited_source_faces=edited))
 support=pack['assets'][0];po=pack['placements'][0];key=support['id'];d['assets'][key]=dict(render_path=support['cache']['path'],render_sha256=support['cache']['sha256']);d['placements'][po['id']]=dict(po,category='actual_native_common_mesh',collision_layer=3,yaw_deg=po['yaw_rad']*180/3.141592653589793)
 for r in d['routes']:r['placement_ids'].append(po['id'])
 assert pack['placements'][1]['id']in con['disable_native_mesh_collider_ids'];d['sources'].update(port_native_pack=ref(SRC/'resolved_placements_r02.json'),port_contract=ref(SRC/'collision_contract_r02.json'),port_ownership=ref(SRC/'ownership_requests_r03.json'),previous_port_trial=ref(OLD/'prepared_runtime.json'));d['assumptions'].append('Native support is active; exact visible fine native cap is excluded by its declared continuous collision contract. Local source top retirements apply only exact recorded triangles. This is a candidate, not a composed-scene release.')
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:shutil.copyfile(OLD/name,H/name)
 for p in [H/'prepare.py']+[H/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']]:d['implementation_hashes'][str(p.relative_to(ROOT))]=sha(p)
 write(H/'prepared_runtime.json',d);write(H/'evidence/native_and_retirement_parity.json',dict(sources=d['sources'],compiled_support=support,visible_native_cap=pack['assets'][1],excluded_fine_instance=pack['placements'][1],exclusion_contract=ref(SRC/'collision_contract_r02.json'),local_retirements=records,route_vectors_unchanged=True,controller_unchanged=True));print(sha(H/'prepared_runtime.json'))
if __name__=='__main__':main()
