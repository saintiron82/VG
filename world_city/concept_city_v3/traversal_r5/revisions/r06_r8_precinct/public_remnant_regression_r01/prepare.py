"""Exact index/byte-bound removal-only collision candidate; original scene stays immutable."""
import pathlib,json,hashlib,copy,shutil
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());OLD=H.parent/'public_network_r18_runtime_r01';MAP=ROOT/'world_city/concept_city_v3/registered_topography/revisions/public_corridors_r18/runtime_local_remnants_r02/runtime_retirement_map.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def canon(v):return hashlib.sha256(json.dumps(v,separators=(',',':')).encode()).hexdigest()
def write(p,d):
 with p.open('x')as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 original=json.loads((OLD/'prepared_runtime.json').read_bytes());d=copy.deepcopy(original);ledger=json.loads(MAP.read_bytes());assert sha(ROOT/ledger['runtime_scene']['path'])==ledger['runtime_scene']['sha256']==d['sources']['scene']['sha256'];assert len(ledger['rows'])==45;retired={tuple(r['source_face_key']):r for r in ledger['rows']};assert len(retired)==45
 for row in retired.values():
  assert canon(row['collision_triangle_xyz_m'])==row['collision_triangle_sha256'];assert row['triangle_xyz_m']==[row['collision_triangle_xyz_m'][0],row['collision_triangle_xyz_m'][2],row['collision_triangle_xyz_m'][1]]
 names=['ROAD:'+n for n in ['UPPER_CONTOUR','LOWER_CONTOUR','MARKET_NORTH','CENTRAL_WEST_RADIAL']];names=set(names+[n+'_REVERSE'for n in names]);d['routes']=[r for r in d['routes']if r['id']in names];assert len(d['routes'])==8
 pids={p for r in d['routes']for p in r['placement_ids']};bids={p for r in d['routes']for p in r['building_ids']};d['placements']={k:v for k,v in d['placements'].items()if k in pids};d['buildings']={k:v for k,v in d['buildings'].items()if k in bids};keys={v['asset_key']for v in d['placements'].values()};d['assets']={k:v for k,v in d['assets'].items()if k in keys};(H/'geometry').mkdir();(H/'evidence').mkdir();changes=[];seen=set()
 for key,a in d['assets'].items():
  if a.get('collision_format')!='actual_scene_triangles':continue
  p=ROOT/a['render_path'];assert sha(p)==a['render_sha256'];g=json.loads(p.read_bytes());indices=[];ts=[];removed=[]
  for ids,t in zip(g['source_face_indices'],g['triangles']):
   record=retired.get(tuple(ids))
   if record:
    assert t==record['collision_triangle_xyz_m']and canon(t)==record['collision_triangle_sha256'];removed.append(ids);seen.add(tuple(ids))
   else:indices.append(ids);ts.append(t)
  out=H/'geometry'/p.name;write(out,dict(g,source_face_indices=indices,triangles=ts));a.update(render_path=str(out.relative_to(ROOT)),render_sha256=sha(out));changes.append(dict(key=key,original=ref(p),candidate=ref(out),removed_source_face_indices=removed,retained_count=len(ts)))
 assert seen==set(retired),set(retired)-seen
 d['sources'].update(original_prepared=ref(OLD/'prepared_runtime.json'),exact_retirement_map=ref(MAP));d['coverage']=dict(cases=8,case_classes={'public_corridor':8},diagnostic_scope='Exact45 source-face retirement only; no north transition or other repairs applied.');d['assumptions'].append('Bounded collision-input removal candidate, not an updated composed scene. Exactly45 declared runtime source faces are removed; retained triangle bytes/order, native inputs, routes, controller and acceptance remain unchanged.')
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:shutil.copyfile(OLD/n,H/n)
 for p in [H/'prepare.py']+[H/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']]:d['implementation_hashes'][str(p.relative_to(ROOT))]=sha(p)
 write(H/'prepared_runtime.json',d);write(H/'evidence/removal_parity.json',dict(schema='riverstone.bounded_runtime_retirement_input_parity.v1',original=ref(OLD/'prepared_runtime.json'),candidate=ref(H/'prepared_runtime.json'),ledger=ref(MAP),exact_retired_unique_faces=45,all_other_triangle_bytes_and_order_unchanged=True,native_assets_unchanged=all(v==original['assets'][k]for k,v in d['assets'].items()if v.get('collision_format')!='actual_scene_triangles'),route_vectors_unchanged=all(r in original['routes']for r in d['routes']),native_poses_unchanged=all(v==original['placements'][k]for k,v in d['placements'].items()),assets=changes));print(json.dumps(dict(prepared=ref(H/'prepared_runtime.json'),cases=8,removed_unique=45)))
if __name__=='__main__':main()
