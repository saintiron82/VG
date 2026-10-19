from pathlib import Path
import json,numpy as np,hashlib
OUT=Path(__file__).resolve().parent;ROOT=next(p for p in OUT.parents if(p/'world_city/concept_city_v3').is_dir());CITY=ROOT/'world_city/concept_city_v3';H=CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01/evidence/noble_failure_handoff_r01.json'
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
h=json.loads(H.read_text());cache={};cases=[]
for row in h['failures']:
 r=row['result'];cid=next(k for k in row['assets']if k.startswith('SCENE:'));path=ROOT/row['assets'][cid]['render_path'];g=cache.setdefault(str(path),json.loads(path.read_text()));ts=np.array(g['triangles']);samples=r['obstacle_contact_samples'];selected=samples[:2]+samples[-2:];hits=[]
 for si,s in enumerate(selected):
  p=np.array(s['position']);ix=np.where(((ts.min(1)-.002<=p)&(ts.max(1)+.002>=p)).all(1))[0];close=[]
  for i in ix:
   a,b,c=ts[i];u=b-a;v=c-a;w=p-a;n=np.cross(u,v);norm=np.linalg.norm(n)
   if norm==0:continue
   distance=abs(float(n@w))/norm
   if distance>.002:continue
   # Projected barycentric test in dominant plane, independent of near-vertical XZ area.
   drop=int(np.argmax(np.abs(n)));use=[j for j in range(3)if j!=drop];A=np.column_stack([u[use],v[use]])
   try:uv=np.linalg.solve(A,w[use])
   except np.linalg.LinAlgError:continue
   if min(uv)<-.002 or sum(uv)>1.002:continue
   close.append(dict(collider_face_index=int(i),source_face=g['source_face_indices'][i],vertices_xyz_m=ts[i].tolist(),distance_from_sample_m=distance,barycentric_uv=uv.tolist(),normal_xyz=(n/norm).tolist()))
  hits.append(dict(sample=s,matching_faces=close));print(r['id'],'contact',s['position'],[(x['source_face'],x['distance_from_sample_m'])for x in close],flush=True)
 cases.append(dict(id=r['id'],source_collision_asset=ref(path),end_position=r['end_position'],contacts=hits))
p=OUT/'contact_face_diagnosis.json';p.write_text(json.dumps(dict(handoff=ref(H),cases=cases,method='Read-only nearest exact triangle plane and barycentric test of recorded runtime contact positions, with 2 mm observation tolerance; no scene or source changes.'),indent=2)+'\n');print(ref(p))
