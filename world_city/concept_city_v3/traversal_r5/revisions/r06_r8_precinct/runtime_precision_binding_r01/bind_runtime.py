"""Derive a separate replay input after strict authored-scene preparation passes."""
import argparse,copy,gc,hashlib,json,pathlib,resource,shutil,time
from runtime_pair import canonical,source_proof,verify_runtime,need
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def resolve(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p
 need(sha(p)==r['sha256'],'Changed source: '+str(p));return p
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--authored-prepared',type=pathlib.Path,required=True);ap.add_argument('--runtime-ledger',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args();start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
 original=args.authored_prepared.resolve();ledger_path=args.runtime_ledger.resolve();out=args.output.resolve();need(out.is_relative_to(ROOT),'Output must be in the authorized repository');need(not out.exists(),'Preserve prior runtime binding output')
 d=json.loads(original.read_bytes());ledger=json.loads(ledger_path.read_bytes());source=resolve(ledger['source']);runtime=resolve(ledger['runtime_scene']);mp=resolve(ledger['retained_source_index_map']);implementation=resolve(ledger['implementation']);index_map=json.loads(mp.read_bytes())
 need(pathlib.Path(d['sources']['scene']['path'])==source and d['sources']['scene']['sha256']==sha(source),'Authored preparation does not bind this source scene')
 for r in d['sources'].values():resolve(r)
 for p,s in d['implementation_hashes'].items():need(sha(ROOT/p)==s,'Changed authored preparation implementation')
 authored=json.loads(source.read_bytes());proof=source_proof(authored,ledger,index_map);del authored;gc.collect();scene=json.loads(runtime.read_bytes());verify_runtime(scene,proof)
 out.mkdir();(out/'geometry').mkdir();(out/'evidence').mkdir();(out/'source_snapshots').mkdir();old_sources=copy.deepcopy(d['sources']);old_assets=copy.deepcopy(d['assets']);removed={(r['material'],r['source_triangle_index']):r for r in ledger['removals']};inverse={m:{i:j for j,i in enumerate(rows)}for m,rows in index_map.items()};rows=[]
 for key,asset in d['assets'].items():
  source_asset=ROOT/asset['render_path'];need(sha(source_asset)==asset['render_sha256'],'Changed original collision asset')
  if asset.get('collision_format')!='actual_scene_triangles':continue
  data=json.loads(source_asset.read_bytes());need(data['scene_sha256']==ledger['source']['sha256'],'Original extracted asset scene mismatch');need(len(data['triangles'])==len(data['source_face_indices']),'Malformed source collision input');triangles=[];indices=[];retired=[]
  for (mat,i),triangle in zip(data['source_face_indices'],data['triangles']):
   original_triangle=[triangle[0],triangle[2],triangle[1]]
   if i not in inverse[mat]:
    record=removed.get((mat,i));need(record is not None and original_triangle==record['source_triangle_xyz_m']and canonical(original_triangle)==record['source_triangle_sha256'],'Unproved original collision retirement');retired.append([mat,i,record['source_triangle_sha256']]);continue
   j=inverse[mat][i];need(scene['surfaces'][mat][j*3:j*3+3]==original_triangle,'Retained exact collision face changed');triangles.append(triangle);indices.append([mat,j])
  target=out/'geometry'/(hashlib.sha256(key.encode()).hexdigest()[:16]+'.json');write(target,dict(data,scene_sha256=ledger['runtime_scene']['sha256'],triangles=triangles,source_face_indices=indices));asset.update(render_path=str(target.relative_to(ROOT)),render_sha256=sha(target));rows.append(dict(asset_key=key,source=ref(source_asset),runtime=ref(target),retained_triangles=len(triangles),retired_original_source_faces=retired))
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:
  p=original.parent/name;need(p.is_file(),'Missing authored runner file '+name);shutil.copyfile(p,out/name)
 need((out/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes(),'Controller changed');need((out/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes(),'Loader changed')
 d['sources'].update(authored_prepared=ref(original),authored_scene=old_sources['scene'],scene=ref(runtime),runtime_precision_ledger=ref(ledger_path),runtime_precision_index_map=ref(mp),runtime_precision_implementation=ref(implementation))
 for p in [H/'bind_runtime.py',H/'runtime_pair.py']+[out/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']]:
  rel=str(p.relative_to(ROOT));digest=sha(p);snapshot=out/'source_snapshots'/(digest[:12]+'_'+p.name);shutil.copyfile(p,snapshot);d['implementation_hashes'][rel]=digest;d['implementation_snapshots'][rel]=ref(snapshot)
 sizes={row['asset_key']:row['retained_triangles']for row in rows};groups={}
 for route in d['routes']:
  group=route.get('group',route['id']);groups[group]=sum(sizes.get(d['placements'][pid]['asset_key'],0)for pid in route['placement_ids'])
 for row in d['coverage'].get('collision_audit',[]):
  if row['group']in groups:row['authored_scene_triangles']=row['scene_triangles'];row['scene_triangles']=groups[row['group']]
 d['coverage']['runtime_precision']=dict(authored_producer_proof=ref(original),runtime_scene=ref(runtime),ledger=ref(ledger_path),changed_route_vectors=0,changed_native_assets=0,removed_route_local_source_faces=sum(len(r['retired_original_source_faces'])for r in rows))
 d['assumptions'].append('Authored producer and native activation proofs remain strict. Runtime terrain is separately bound by exact zero-float32 retirement and retained source indices; no other source face may be absent.')
 write(out/'prepared_runtime.json',d);write(out/'evidence/runtime_binding.json',dict(schema='riverstone.strict_authored_to_runtime_replay_binding.v1',authored_prepared=ref(original),prepared=ref(out/'prepared_runtime.json'),source=ref(source),runtime_scene=ref(runtime),ledger=ref(ledger_path),index_map=ref(mp),whole_scene_proof=proof,local_assets=rows,routes_unchanged=True,native_assets_unchanged=all(asset==old_assets[k]for k,asset in d['assets'].items()if asset.get('collision_format')!='actual_scene_triangles'),elapsed_s=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,limits=['No runtime replay is launched by this preparation.','Authored source, original proof inputs and all prior results are preserved.']))
 print(json.dumps(dict(prepared=ref(out/'prepared_runtime.json'),cases=len(d['routes']),removed_local_faces=sum(len(r['retired_original_source_faces'])for r in rows),elapsed_s=time.monotonic()-start),indent=2))
if __name__=='__main__':main()
