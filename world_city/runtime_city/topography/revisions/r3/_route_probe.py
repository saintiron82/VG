"""Source-only layout probe; never edits city data."""
import json, math, heapq
from pathlib import Path
from world_city.runtime_city.topography import author as a
ROOT=Path(__file__).resolve().parents[5]
s=json.load(open(ROOT/'world_city/runtime_city/generated/r2/scene.graded_property.json'))
b=json.load(open(ROOT/'world_city/data/city_brief.v2.json'))
polys=[]
for x in s['instances']:
 p=x['source_footprint_xz_m']
 if max(t[0] for t in p)<480 or min(t[0] for t in p)>640: continue
 if max(t[1] for t in p)<-300 or min(t[1] for t in p)>320:continue
 polys.append((x['id'],[[u,v,w+3] for u,v,w in a._inside_planes(a._convex(p))]))
wall=a._inside_planes(a._convex(b['wall_outline_xz_m']))
def valid(p):
 if not all(a._eval(c,*p)>=3 for c in wall):return False
 return not any(all(a._eval(c,*p)>=0 for c in planes) for _,planes in polys)
def clear(p,q):
 n=max(1,math.ceil(math.dist(p,q)/.5))
 return all(valid([p[0]+(q[0]-p[0])*i/n,p[1]+(q[1]-p[1])*i/n]) for i in range(n+1))
start=(578,-270);end=(540,280)
print('valid',valid(start),valid(end))
queue=[(0,start)];cost={start:0};prev={}
while queue:
 _,p=heapq.heappop(queue)
 if p==end:break
 for dx,dz in [(2,0),(-2,0),(0,2),(0,-2),(2,2),(2,-2),(-2,2),(-2,-2)]:
  q=(p[0]+dx,p[1]+dz)
  if not (480<=q[0]<=640 and -290<=q[1]<=300) or not valid(q): continue
  c=cost[p]+math.hypot(dx,dz)
  if c>=cost.get(q,float('inf')):continue
  cost[q]=c;prev[q]=p;heapq.heappush(queue,(c+math.dist(q,end),q))
if end not in prev:print('NO ROUTE');raise SystemExit()
p=end;route=[p]
while p!=start:p=prev[p];route.append(p)
route.reverse();out=[route[0]];i=0
while i<len(route)-1:
 j=len(route)-1
 while j>i+1 and not clear(route[i],route[j]):j-=1
 out.append(route[j]);i=j
print(out,'length',sum(math.dist(p,q) for p,q in zip(out,out[1:])))
