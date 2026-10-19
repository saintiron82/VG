"""Bind precisely ten approved derived collision-winding rows after zero sanitation."""
import argparse,copy,gc,hashlib,json,pathlib,resource,shutil,sys,time
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.final23_precision_continuation_r01 import runtime_winding as winding
IMPLEMENTATION_SHA='7c6f778986c848dbec9e05442e924ae6f6979781fa01feb71229b0a2ca8f2d8d';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p),sha256=sha(p));read=lambda p:json.loads(p.read_bytes())
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def resolve(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==r['sha256'],'Changed source '+str(p);return p

def validate_rows(scene,ledger):
 assert sha(pathlib.Path(winding.__file__))==IMPLEMENTATION_SHA
 expected=winding.bind_scene(scene,ledger['source_scene']);extras=set(ledger)-set(expected);assert extras<= {'derived_scene','changed_surface_rows','unchanged_non_surface_fields'},'Unknown winding ledger fields'
 assert all(ledger.get(k)==v for k,v in expected.items()),'Winding rows differ from the exact recognized ten-row binding'
 if 'changed_surface_rows'in ledger:assert ledger['changed_surface_rows']==10
 if 'unchanged_non_surface_fields'in ledger:assert ledger['unchanged_non_surface_fields']is True
 assert len(ledger['rows'])==10 and len({(r['material'],r['scene_triangle_index'])for r in ledger['rows']})==10
 return {(r['material'],r['scene_triangle_index']):r for r in ledger['rows']}

def surface_proof(scene,rows):
 # Mutate this in-memory read only. No authored or intermediate file is changed.
 for(mat,i),r in rows.items():
  vs=scene['surfaces'][mat];assert vs[3*i:3*i+3]==r['precise_source_vertices_xyz_m'];vs[3*i:3*i+3]=copy.deepcopy(r['runtime_after_vertices_xyz_m'])
 return dict(non_surface_sha256=winding.canonical_sha({k:v for k,v in scene.items()if k!='surfaces'}),surface_sha256={m:winding.canonical_sha(v)for m,v in scene['surfaces'].items()},surface_triangle_counts={m:len(v)//3 for m,v in scene['surfaces'].items()})

def verify_output(scene,proof):
 assert winding.canonical_sha({k:v for k,v in scene.items()if k!='surfaces'})==proof['non_surface_sha256'],'Changed non-surface fields';assert set(scene['surfaces'])==set(proof['surface_sha256'])
 for m,v in scene['surfaces'].items():assert len(v)//3==proof['surface_triangle_counts'][m]and winding.canonical_sha(v)==proof['surface_sha256'][m],'Moved, missing or extra runtime triangle '+m

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--zero-prepared',type=pathlib.Path,required=True);ap.add_argument('--winding-ledger',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args();resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));start=time.monotonic();inp=args.zero_prepared.resolve();lp=args.winding_ledger.resolve();out=args.output.resolve();assert out.is_relative_to(ROOT)and not out.exists();d=read(inp);before=copy.deepcopy(d);ledger=read(lp);zero=resolve(ledger['source_scene']);runtime=resolve(ledger['derived_scene']);zero_sha=ledger['source_scene']['sha256'];runtime_sha=ledger['derived_scene']['sha256'];assert d['sources']['scene']['sha256']==sha(zero)and pathlib.Path(d['sources']['scene']['path'])==zero
 for r in d['sources'].values():resolve(r)
 for p,h in d['implementation_hashes'].items():assert sha(ROOT/p)==h
 scene=read(zero);rows=validate_rows(scene,ledger);proof=surface_proof(scene,rows);del scene;gc.collect();scene=read(runtime);verify_output(scene,proof)
 out.mkdir();(out/'geometry').mkdir();(out/'evidence').mkdir();asset_rows=[]
 for key,ass in d['assets'].items():
  source_asset=ROOT/ass['render_path'];assert sha(source_asset)==ass['render_sha256']
  if ass.get('collision_format')!='actual_scene_triangles':continue
  data=read(source_asset);assert data['scene_sha256']==zero_sha;assert len(data['triangles'])==len(data['source_face_indices']);updated=[];changes=[]
  for (mat,i),t in zip(data['source_face_indices'],data['triangles']):
   row=rows.get((mat,i));old=[t[0],t[2],t[1]];actual=scene['surfaces'][mat][3*i:3*i+3]
   if row:
    assert old==row['precise_source_vertices_xyz_m']and actual==row['runtime_after_vertices_xyz_m'];updated.append([actual[0],actual[2],actual[1]]);changes.append(dict(case_id=row['case_id'],source_index=[mat,i]))
   else:assert actual==old,'Unrecognized changed collision face';updated.append(t)
  target=out/'geometry'/(hashlib.sha256(key.encode()).hexdigest()[:16]+'.json');write(target,dict(data,scene_sha256=runtime_sha,triangles=updated));ass.update(render_path=str(target.relative_to(ROOT)),render_sha256=sha(target));asset_rows.append(dict(asset_key=key,source=ref(source_asset),runtime=ref(target),recognized_changed_rows=changes,face_indices_and_count_unchanged=True))
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:shutil.copyfile(inp.parent/name,out/name)
 assert (out/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes();assert (out/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes();assert d['routes']==before['routes']and d['placements']==before['placements']and all(a==before['assets'][k]for k,a in d['assets'].items()if a.get('collision_format')!='actual_scene_triangles')
 d['sources'].update(zero_sanitized_prepared=ref(inp),zero_sanitized_scene=ref(zero),scene=ref(runtime),runtime_winding_ledger=ref(lp),runtime_winding_implementation=ref(pathlib.Path(winding.__file__)),runtime_winding_contract=ref(pathlib.Path(winding.__file__).with_name('runtime_winding_contract.json')))
 for p in [H/'bind_winding.py',pathlib.Path(winding.__file__)]+[out/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']]:d['implementation_hashes'][str(p.relative_to(ROOT))]=sha(p)
 d['coverage']['runtime_winding']=dict(ledger=ref(lp),whole_scene_changed_rows=10,local_collision_row_references=sum(len(r['recognized_changed_rows'])for r in asset_rows),face_count_changed=0,native_geometry_changed=0,policy='Derived shared scene rendering and collision both use the ten exact authorized float32 vertex sets and their corrected winding. Precise authored ownership remains separate.');d['assumptions'].append('After exact-zero sanitation, exactly ten hash-bound source rows use the authorized float32 vertex set and collision winding. Every other runtime row, index, native asset, controller setting and route is unchanged.')
 write(out/'prepared_runtime.json',d);zero_binding=ref(inp.parent/'evidence/runtime_binding.json');write(out/'evidence/runtime_binding.json',dict(schema='riverstone.strict_zero_then_ten_row_runtime_binding.v1',authored_prepared=d['sources']['authored_prepared'],prepared=ref(out/'prepared_runtime.json'),source=d['sources']['authored_scene'],runtime_scene=ref(runtime),exact_zero_binding=zero_binding,winding_ledger=ref(lp),whole_scene_proof=proof,local_assets=asset_rows,routes_unchanged=True,native_assets_and_poses_unchanged=True,elapsed_s=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss));print(json.dumps(dict(prepared=ref(out/'prepared_runtime.json'),cases=len(d['routes']),changed_local_references=sum(len(r['recognized_changed_rows'])for r in asset_rows),seconds=time.monotonic()-start)))
if __name__=='__main__':main()
