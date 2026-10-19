import json,math
from pathlib import Path
from world_city.runtime_city.checks import placement as g
H=Path(__file__).parent;R=H.parents[4]
s=json.load(open(R/'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json'))
points=[[-400.108204,-232.024295],[-389,-228],[-361,-237],[-330,-225],[-300,-215],[-273.02884,-197.71714],[-450,-270],[-490,-300],[-500,-310],[-490,-320],[-470,-310],[-480,-280],[-475,-300],[-490,-280],[505,-18],[500,20]]
found=[[]for _ in points];local=[]
for m,v in s['surfaces'].items():
 for j in range(0,len(v),3):
  t=v[j:j+3];p=[[q[0],q[2]]for q in t];lo=[min(q[k]for q in p)for k in [0,1]];hi=[max(q[k]for q in p)for k in [0,1]]
  if not ((hi[0]>-600 and lo[0]<-230 and hi[1]>-350 and lo[1]<-110)or(hi[0]>355 and lo[0]<610 and hi[1]>-80 and lo[1]<100)):continue
  local.append({'material':m,'triangle_index':j//3,'triangle':t})
  det=(t[1][0]-t[0][0])*(t[2][2]-t[0][2])-(t[2][0]-t[0][0])*(t[1][2]-t[0][2])
  if abs(det)<1e-8:continue
  ax=((t[1][1]-t[0][1])*(t[2][2]-t[0][2])-(t[2][1]-t[0][1])*(t[1][2]-t[0][2]))/det;az=((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[2][0]-t[0][0])*(t[1][1]-t[0][1]))/det;c=t[0][1]-ax*t[0][0]-az*t[0][2]
  for k,pt in enumerate(points):
   if lo[0]-1e-8<=pt[0]<=hi[0]+1e-8 and lo[1]-1e-8<=pt[1]<=hi[1]+1e-8 and g.point_in_convex_polygon(pt,p,1e-7):found[k].append((m,ax*pt[0]+az*pt[1]+c))
json.dump(local,open(H/'local_source_faces.json','w'))
for p,v in zip(points,found):print(p,v)
print('local',len(local))
