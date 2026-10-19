"""Explicit exact-world local-origin stage for actual-scene collision extraction."""
import argparse,copy,hashlib,json,pathlib,resource,shutil,sys,time
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_integration.r8 import collision_local_origin as origin
IMPLEMENTATION_SHA='1ce3880ec9cfa88aa03bcd39510f8afc62486be519e83dc470c746cd2a5eb064'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def resolve(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==r['sha256'],p;return p
def transform(data,asset_key,asset_data):
 placements=[p for p in data['placements'].values()if p['asset_key']==asset_key];assert placements
 assert all(p.get('position_m',[0,0,0])==[0,0,0]and p.get('yaw_rad',0)==0 and p.get('yaw_deg',0)==0 and p.get('scale',[1,1,1])==[1,1,1]for p in placements),'Only original identity actual-scene assets may be rebased'
 pids={p['id']for p in placements};routes=[r for r in data['routes']if pids.intersection(r['placement_ids'])];points=[p for r in routes for p in r['points']];local,translation,proof=origin.rebase(asset_data['triangles'],points);assert [[[v[i]+translation[i]for i in range(3)]for v in t]for t in local]==asset_data['triangles'];assert len(local)==len(asset_data['source_face_indices'])
 result=copy.deepcopy(asset_data);result.update(triangles=local,collision_local_origin_xyz_m=translation,exact_world_coordinate_reconstruction=True);return result,translation,dict(proof,route_ids=[r['id']for r in routes],placement_ids=sorted(pids))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args();resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));start=time.monotonic();src=args.prepared.resolve();out=args.output.resolve();assert out.is_relative_to(ROOT)and not out.exists();implementation=pathlib.Path(origin.__file__);assert sha(implementation)==IMPLEMENTATION_SHA
 d=json.loads(src.read_bytes());original=copy.deepcopy(d)
 for r in d['sources'].values():
  if isinstance(r,dict)and'path'in r and'sha256'in r:resolve(r)
 for p,h in d['implementation_hashes'].items():assert sha(ROOT/p)==h,p
 out.mkdir();(out/'geometry').mkdir();(out/'evidence').mkdir();rows=[]
 for key,ass in d['assets'].items():
  p=ROOT/ass['render_path'];assert sha(p)==ass['render_sha256']
  if ass.get('collision_format')!='actual_scene_triangles':continue
  raw=json.loads(p.read_bytes());local,t,proof=transform(original,key,raw);target=out/'geometry'/(hashlib.sha256(key.encode()).hexdigest()[:16]+'.json');write(target,local);ass.update(render_path=str(target.relative_to(ROOT)),render_sha256=sha(target));
  for pid in proof['placement_ids']:d['placements'][pid]['position_m']=t
  rows.append(dict(asset_key=key,source=ref(p),local=ref(target),proof=proof))
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:shutil.copyfile(src.parent/name,out/name)
 assert (out/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes();assert (out/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes()
 assert original['routes']==d['routes'];assert all(v==original['assets'][k]for k,v in d['assets'].items()if v.get('collision_format')!='actual_scene_triangles');assert all(v==original['placements'][k]for k,v in d['placements'].items()if d['assets'][v['asset_key']].get('collision_format')!='actual_scene_triangles')
 d['sources'].update(world_prepared=ref(src),local_origin_implementation=ref(implementation),local_origin_handoff=ref(ROOT/'world_city/concept_city_v3/registered_integration/r8/north_support_miss_r01/integration_handoff.json'))
 for p in [H/'bind_origins.py',implementation]+[out/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']]:d['implementation_hashes'][str(p.relative_to(ROOT))]=sha(p)
 d['coverage']['local_origin_stage']=dict(source=ref(src),actual_scene_assets=len(rows),applied_assets=sum(any(r['proof']['applied_origin_xyz_m'])for r in rows),fallback_assets=sum(r['proof']['fallback_reason']is not None for r in rows),removed_faces=0,added_faces=0,world_double_vertices_exact=True);d['assumptions'].append('Explicit local-origin stage uses existing common-loader placement translations only. Every source world double, triangle order, native pose and controller setting is preserved; per-asset proof and safe fallbacks are recorded. Actual replay remains required.')
 write(out/'prepared_runtime.json',d);write(out/'evidence/local_origin_binding.json',dict(schema='riverstone.explicit_local_origin_extraction.v1',source=ref(src),prepared=ref(out/'prepared_runtime.json'),implementation=ref(implementation),assets=rows,route_vectors_unchanged=True,native_assets_and_poses_unchanged=True,controller_loader_unchanged=True,elapsed_s=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss));print(json.dumps(dict(prepared=ref(out/'prepared_runtime.json'),cases=len(d['routes']),assets=len(rows),applied=d['coverage']['local_origin_stage']['applied_assets'])))
if __name__=='__main__':main()
