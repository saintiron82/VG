"""Bind unchanged route-local collision input to exact float32-zero-area removal."""
import copy, hashlib, json, pathlib, resource, time
import numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
OLD=H.parent/'ordinary61_diagnostic_r01';SAN=H.parent/'ordinary61_contact_diagnosis_r01/float32_zero_area_r01'
CASES=['BLOCK_002:R8_C009:PUBLIC_ENTRY','BLOCK_002:R8_C009:PUBLIC_ENTRY_REVERSE','BLOCK_005:R8_C002:PUBLIC_ENTRY','BLOCK_005:R8_C002:PUBLIC_ENTRY_REVERSE']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));start=time.monotonic()
 old=json.loads((OLD/'prepared_runtime.json').read_bytes());d=copy.deepcopy(old);ledger=json.loads((SAN/'removal_ledger.json').read_bytes());index_map=json.loads((SAN/'retained_source_index_map.json').read_bytes())
 assert sha(SAN/'scene.json')==ledger['derived_scene']['sha256']=='0b980d256f43cfba9f316ec67a615dcd4c674f89254ea0c0d26a48595b32cf39'
 assert old['sources']['scene']['sha256']==ledger['source']['sha256'];assert ledger['non_surface_fields_identical'];assert ledger['retained_triangle_order_and_original_double_vertices_identical']
 assert sha(SAN/'retained_source_index_map.json')==ledger['retained_source_index_map']['sha256']
 scene=json.loads((SAN/'scene.json').read_bytes());inverse={m:{old_i:new_i for new_i,old_i in enumerate(rows)}for m,rows in index_map.items()};removed={(r['material'],r['original_triangle_index']):r for r in ledger['removals']}
 d['routes']=[r for r in d['routes']if r['id']in CASES];assert len(d['routes'])==len(CASES)
 ids={i for r in d['routes']for i in r['placement_ids']};keys={d['placements'][i]['asset_key']for i in ids};d['placements']={i:p for i,p in d['placements'].items()if i in ids};d['assets']={k:a for k,a in d['assets'].items()if k in keys};buildings={i for r in d['routes']for i in r['building_ids']};d['buildings']={k:v for k,v in d['buildings'].items()if k in buildings}
 (H/'geometry').mkdir();rows=[]
 for key,a in d['assets'].items():
  source=ROOT/a['render_path'];assert sha(source)==a['render_sha256']
  if a.get('collision_format')!='actual_scene_triangles':continue
  data=json.loads(source.read_bytes());kept=[];faces=[];dropped=[]
  for (mat,i),tri in zip(data['source_face_indices'],data['triangles']):
   original=[tri[0],tri[2],tri[1]]
   if i not in inverse[mat]:
    r=removed[(mat,i)];assert original==r['source_triangle_xyz_m'];assert canonical(original)==r['source_triangle_sha256'];q=np.asarray(original,dtype=np.float32);assert np.all(np.cross(q[1]-q[0],q[2]-q[0])==np.float32(0));dropped.append(dict(material=mat,original_triangle_index=i,source_triangle_sha256=r['source_triangle_sha256']));continue
   new_i=inverse[mat][i];assert scene['surfaces'][mat][new_i*3:new_i*3+3]==original;kept.append(tri);faces.append([mat,new_i])
  out=dict(data,scene_sha256=ledger['derived_scene']['sha256'],source_face_indices=faces,triangles=kept);target=H/'geometry'/source.name;write(target,out);a['render_path']=str(target.relative_to(ROOT));a['render_sha256']=sha(target);rows.append(dict(asset=key,previous=ref(source),current=ref(target),retained_triangles=len(kept),removed=dropped,unmodified_whole_triangle_vertices=True))
 d['sources']['original_diagnostic_prepared']=ref(OLD/'prepared_runtime.json');d['sources']['original_diagnostic_scene']=d['sources']['scene'];d['sources']['scene']=ref(SAN/'scene.json');d['sources']['exact_float32_removal_ledger']=ref(SAN/'removal_ledger.json');d['sources']['exact_float32_index_map']=ref(SAN/'retained_source_index_map.json')
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot']:
  assert (H/name).read_bytes()==(OLD/name).read_bytes()
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','prepare_filtered.py']:
  d['implementation_hashes'][str((H/name).relative_to(ROOT))]=sha(H/name)
 d['coverage']=dict(cases=len(d['routes']),case_classes={'ordinary_entry':len(d['routes'])},source_coverage_ref=ref(OLD/'prepared_runtime.json'),scope='Four originally blocked directions only, with exact float32-zero-area scene-face removals; all original route vectors, native meshes, contracts and controller settings retained.')
 d['assumptions'].append('This isolated regression admits only hash-bound exact float32-zero-area source face retirements; no general producer verification is weakened.')
 write(H/'prepared_runtime.json',d)
 write(H/'evidence/preparation.json',dict(schema='riverstone.exact_float32_retirement_route_binding.v1',original=ref(OLD/'prepared_runtime.json'),prepared=ref(H/'prepared_runtime.json'),scene=ref(SAN/'scene.json'),ledger=ref(SAN/'removal_ledger.json'),map=ref(SAN/'retained_source_index_map.json'),cases=CASES,rows=rows,routes_byte_value_identical=all(r==next(x for x in old['routes']if x['id']==r['id'])for r in d['routes']),native_assets_placements_unchanged=True,elapsed_s=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
 print(json.dumps(dict(cases=len(CASES),removed=sum(len(r['removed'])for r in rows),elapsed_s=time.monotonic()-start)))
if __name__=='__main__':main()
