"""Deterministic planar-face extraction and simple polygon triangulation."""
import math
from collections import defaultdict
from world_city.runtime_city.checks import placement as g

def inside(p,poly):
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if g.point_segment_distance(p,a,b)<1e-6:return True
 x,z=p;yes=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:yes=not yes
 return yes

def triangulate(poly):
 p=[list(x) for x in poly]
 if g.signed_polygon_area(p)<0:p.reverse()
 changed=True
 while changed and len(p)>3:
  changed=False
  for i in range(len(p)):
   a,b,c=p[i-1],p[i],p[(i+1)%len(p)]
   if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))<1e-7:p.pop(i);changed=True;break
 out=[]
 for _ in range(len(p)*len(p)+1):
  if len(p)<=3:break
  for i in range(len(p)):
   a,b,c=p[i-1],p[i],p[(i+1)%len(p)]
   if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<=1e-8:continue
   t=[a,b,c]
   if any(g.point_in_convex_polygon(q,t,-1e-7) for j,q in enumerate(p) if j not in [(i-1)%len(p),i,(i+1)%len(p)]):continue
   out.append(t);p.pop(i);break
  else:break
 if len(p)==3 and g.polygon_area(p)>1e-7:out.append(p)
 return out

def faces(roads,boundary):
 segments=[]
 for r in roads:
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):
   if math.dist(a,b)>1e-7:segments.append((a,b,r['id']))
 segments.extend((a,b,'WALL') for a,b in zip(boundary,boundary[1:]+boundary[:1]))
 splits=[{0.,1.} for _ in segments]
 for i,(a,b,_) in enumerate(segments):
  u=[b[k]-a[k] for k in(0,1)];ll=sum(x*x for x in u)
  for j,(c,d,_) in enumerate(segments[:i]):
   v=[d[k]-c[k] for k in(0,1)];den=u[0]*v[1]-u[1]*v[0]
   if abs(den)>1e-9:
    t=((c[0]-a[0])*v[1]-(c[1]-a[1])*v[0])/den;s=((c[0]-a[0])*u[1]-(c[1]-a[1])*u[0])/den
    if -1e-8<=t<=1+1e-8 and -1e-8<=s<=1+1e-8:splits[i].add(max(0,min(1,t)));splits[j].add(max(0,min(1,s)))
   else:
    for p in(c,d):
     if g.point_segment_distance(p,a,b)<1e-6:splits[i].add(max(0,min(1,sum((p[k]-a[k])*u[k] for k in(0,1))/ll)))
    vv=sum(x*x for x in v)
    for p in(a,b):
     if g.point_segment_distance(p,c,d)<1e-6:splits[j].add(max(0,min(1,sum((p[k]-c[k])*v[k] for k in(0,1))/vv)))
 adj=defaultdict(set);edge_road={}
 for (a,b,rid),ss in zip(segments,splits):
  pts=[tuple(round(a[k]+t*(b[k]-a[k]),6) for k in(0,1)) for t in sorted(ss)]
  for u,v in zip(pts,pts[1:]):
   if u==v:continue
   adj[u].add(v);adj[v].add(u);edge_road[(u,v)]=rid;edge_road[(v,u)]=rid
 order={v:sorted(ns,key=lambda n:math.atan2(n[1]-v[1],n[0]-v[0])) for v,ns in adj.items()};visited=set();result=[]
 for u in sorted(adj):
  for v in order[u]:
   if(u,v) in visited:continue
   start=(u,v);edges=[];poly=[];cur=start
   for _ in range(len(edge_road)+1):
    if cur in visited:break
    visited.add(cur);a,b=cur;poly.append(list(a));edges.append(edge_road[cur]);opts=order[b];c=opts[(opts.index(a)-1)%len(opts)];cur=(b,c)
    if cur==start:break
   if cur==start and len(poly)>2 and g.signed_polygon_area(poly)>50 and all(inside(q,boundary) for q in poly):result.append((poly,edges))
 return sorted(result,key=lambda e:(sum(p[1] for p in e[0])/len(e[0]),sum(p[0] for p in e[0])/len(e[0])))
