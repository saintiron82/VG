"""Source polygon ownership boolean operations; no voxel or mesh operations."""
from __future__ import annotations
import math
from collections import defaultdict
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.registered_source.geometry import triangulate,inside

def bounds(p):return [min(q[0] for q in p),min(q[1] for q in p),max(q[0] for q in p),max(q[1] for q in p)]
def boxes_touch(a,b):return min(a[2],b[2])>=max(a[0],b[0])-1e-8 and min(a[3],b[3])>=max(a[1],b[1])-1e-8

def boundary_loops(pieces):
 """Extract directed union perimeter by splitting and classifying source edges."""
 edges=[(a,b) for p in pieces for a,b in zip(p,p[1:]+p[:1]) if math.dist(a,b)>1e-6]
 vertices=[p for e in edges for p in e];kept={}
 def covered(p):return any(inside(p,q) for q in pieces)
 for a,b in edges:
  u=[b[k]-a[k] for k in (0,1)];l2=sum(x*x for x in u);length=math.sqrt(l2);ts={0.,1.}
  for p in vertices:
   t=sum((p[k]-a[k])*u[k] for k in (0,1))/l2
   if 1e-7<t<1-1e-7 and g.point_segment_distance(p,a,b)<1e-5:ts.add(t)
  ts=sorted(ts)
  for t0,t1 in zip(ts,ts[1:]):
   if (t1-t0)*length<1e-5:continue
   p=[a[k]+t0*u[k] for k in (0,1)];q=[a[k]+t1*u[k] for k in (0,1)];mid=[(p[k]+q[k])/2 for k in (0,1)];n=[-u[1]/length,u[0]/length];eps=1e-4
   left=covered([mid[k]+eps*n[k] for k in (0,1)]);right=covered([mid[k]-eps*n[k] for k in (0,1)])
   if left==right:continue
   if right:p,q=q,p
   p,q=tuple(round(v,5) for v in p),tuple(round(v,5) for v in q)
   if p!=q:kept[(p,q)]=True
 adj=defaultdict(list)
 for a,b in kept:adj[a].append(b)
 if any(len(v)!=1 for v in adj.values()):raise ValueError('Ambiguous ownership perimeter branches')
 loops=[];remaining=set(kept)
 while remaining:
  a,b=min(remaining);start=a;loop=[]
  for _ in range(len(remaining)+1):
   loop.append(list(a));remaining.remove((a,b));a=b
   if a==start:break
   if a not in adj:raise ValueError('Unclosed ownership perimeter')
   b=adj[a][0]
  else:raise ValueError('Ownership loop did not close')
  # Collapse numerically collinear subdivision vertices, preserving bends.
  changed=True
  while changed and len(loop)>3:
   changed=False
   for i,v in enumerate(loop):
    if g.point_segment_distance(v,loop[i-1],loop[(i+1)%len(loop)])<2e-5:loop.pop(i);changed=True;break
  if g.polygon_area(loop)>1e-5:loops.append(loop)
 return loops

def road_owned_parcel(plot,roads):
 original=plot['polygon_xz_m'];bb=bounds(original);pieces=triangulate(original);cuts=[]
 for road in roads:
  for i,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   if math.dist(a,b)<1e-7:continue
   ribbon=g.road_ribbon(a,b,road['width_m'])
   if not boxes_touch(bb,bounds(ribbon)):continue
   area=sum(g.intersection_area(p,ribbon) for p in pieces)
   if area<1e-6:continue
   # Sequential difference computes union ownership: a bend is never counted twice.
   pieces=[q for p in pieces for q in g.convex_difference(p,ribbon) if g.polygon_area(q)>1e-6]
   cuts.append(dict(road_id=road['id'],segment_index=i,public_road_ribbon_xz_m=ribbon,newly_removed_union_area_m2=area))
 loops=boundary_loops(pieces) if cuts else [original]
 if len(loops)!=1 or g.signed_polygon_area(loops[0])<0:raise ValueError(plot['id']+' road cuts split the property or create a hole; explicit redesign required')
 area=g.polygon_area(original)-sum(g.polygon_area(p) for p in pieces)
 if abs(g.polygon_area(loops[0])-sum(g.polygon_area(p) for p in pieces))>.02:raise ValueError('Ownership perimeter area does not match finite source union')
 return dict(original_trace_polygon_xz_m=original,owned_polygon_xz_m=loops[0],owned_regions_xz_m=pieces,public_road_cuts=cuts,removed_union_area_m2=area,topology='one_continuous_closed_property_perimeter_with_explicit_gate_to_be_cut')
