"""Finite float32 boundary diagnosis; original controller and geometry preserved."""
from pathlib import Path
import json,hashlib,numpy as np,math
O=Path(__file__).resolve().parent;ROOT=next(p for p in O.parents if(p/'voxel_character').is_dir());C=ROOT/'world_city/concept_city_v3';T=C/'traversal_r5/revisions/r06_r8_precinct';load=lambda p:json.loads(p.read_text());ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def canonical(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def bary(t,q):
 a,b,c=np.asarray(t)[:,[0,2]];mat=np.column_stack((b-a,c-a))
 if abs(np.linalg.det(mat))<1e-16:return None
 w=np.linalg.solve(mat,np.asarray(q)-a);return[w[0],w[1],1-w.sum()]
def main():
 prepared=T/'final_training_candidate_r01/prepared_runtime.json';p=load(prepared);key='SCENE:PUBLIC_NETWORK:GOAL:MARKET_TO_TRAINING';asset=ROOT/p['assets'][key]['render_path'];d=load(asset);a=np.asarray(d['triangles']);a32=a.astype(np.float32).astype(float);xy=a[:,:,[0,2]];ep=T/'final_training_ray_diagnosis_r01/evidence/original_training_candidate/observer_events.jsonl';events=[]
 for line in ep.read_text().splitlines():
  try:r=json.loads(line)
  except json.JSONDecodeError:continue
  if r.get('original_ground_ray_miss_delta',0)>0:events.append(r)
 rows=[]
 for r in events:
  q=np.asarray(r['capsule_center'])[[0,2]];bb=(xy.min(axis=1)<=q+.001).all(axis=1)&(xy.max(axis=1)>=q-.001).all(axis=1);near=[]
  for i in np.flatnonzero(bb):
   bd=bary(a[i],q);bf=bary(a32[i],q)
   if bd is not None and min(bd)>-.001:near.append(dict(prepared_triangle_index=int(i),scene_source_face=d['source_face_indices'][i],source_triangle_xyz_m=a[i].tolist(),source_triangle_sha256=canonical(a[i].tolist()),float32_triangle_xyz_m=a32[i].tolist(),double_barycentric=bd,float32_barycentric=bf,double_covers_ray=min(bd)>=-1e-12,float32_covers_ray=min(bf)>=0.))
  rows.append(dict(walk_physics_frame=r['walk_physics_frame'],event=r,nearby_actual_source_triangles=near))
 out=dict(schema='riverstone.finite_ray_boundary_diagnosis.v1',prepared=ref(prepared),asset=ref(asset),source_asset_pose=p['placements'][key],observer_input_path=str(ep.relative_to(ROOT)),observer_complete=False,miss_events=rows,limits=['Live observer events are copied verbatim. Final observer freeze will be bound before release.','No threshold or geometry change is made by this diagnosis.'])
 (O/'initial_diagnosis.json').write_text(json.dumps(out,indent=2)+'\n');print('events',[(r['walk_physics_frame'],r['event']['capsule_center'])for r in rows])
if __name__=='__main__':main()
