#!/usr/bin/env python3
"""Read-only nearest exact source-face attribution for retained capsule contacts."""
import argparse,json,pathlib,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def main():
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=pathlib.Path,required=True);p.add_argument('--result',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();d=json.loads(a.prepared.read_bytes());r=json.loads(a.result.read_bytes());cache={};rows=[]
 for case in r['routes']:
  if case['pass']or not case['obstacle_contact_samples']:continue
  sample=case['obstacle_contact_samples'][0];pid=sample['collider_id']
  if not pid.startswith('SCENE:R9:GATE:'):continue
  if pid not in cache:
   place=d['placements'][pid];asset=d['assets'][place['asset_key']];geo=json.loads((ROOT/asset['render_path']).read_bytes());tri=np.asarray(geo['triangles'])+np.asarray(place['position_m']);cache[pid]=(geo,tri)
  geo,tri=cache[pid];point=np.asarray(sample['position']);lo=tri.min(1);hi=tri.max(1);mask=np.all((lo<=point+.06)&(hi>=point-.06),axis=1);matches=[]
  for idx in np.nonzero(mask)[0]:
   t=tri[idx];n=np.cross(t[1]-t[0],t[2]-t[0]);norm=np.linalg.norm(n)
   if norm==0:continue
   dist=abs(np.dot(point-t[0],n))/norm
   if dist>.06:continue
   matches.append({'source_face':geo['source_face_indices'][int(idx)],'world_triangle':t.tolist(),'collision_order_normal':(n/norm).tolist(),'plane_distance_m':float(dist)})
  matches.sort(key=lambda m:m['plane_distance_m']);rows.append({'route_id':case['id'],'status':case['status'],'contact':sample,'candidate_exact_faces':matches[:20]})
 with a.output.open('x')as f:json.dump({'method':'Exact source triangles within 0.06 m contact AABB and plane distance; candidates, not uninstrumented triangle-index certainty','routes':rows},f,indent=2);f.write('\n')
 print(json.dumps([{'id':x['route_id'],'matches':[f['source_face']for f in x['candidate_exact_faces'][:5]]}for x in rows],indent=2))
if __name__=='__main__':main()
