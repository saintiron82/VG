"""Verbatim finite redundant-knot normalizer from causeway side-join author.
Source SHA e0efa2344df77cd241eb97d12513c65c22ccbca25aba0a890944384be2e60995
"""
import math
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as g
NORMALIZATION=[]
def normalized(poly,tag):
 original=[list(v)for v in poly];p=[list(v)for v in poly];removed=[]
 again=True
 while again and len(p)>=3:
  again=False
  for i,v in enumerate(p):
   u,w=p[i-1],p[(i+1)%len(p)];dx,dz=w[0]-u[0],w[1]-u[1];L=math.hypot(dx,dz)
   if L==0:distance=math.dist(v,u);between=True
   else:
    distance=abs(dx*(v[1]-u[1])-dz*(v[0]-u[0]))/L;t=((v[0]-u[0])*dx+(v[1]-u[1])*dz)/L**2;between=-1e-9<=t<=1+1e-9
   if between and distance<=1e-9:
    removed.append(dict(vertex_xz_m=v,distance_to_retained_edge_m=distance));p.pop(i);again=True;break
 if len(p)<3:p=[]
 if removed:NORMALIZATION.append(dict(tag=tag,source_polygon_xz_m=original,output_polygon_xz_m=p,removed=removed,source_area_m2=g.area(original),output_area_m2=g.area(p),area_delta_m2=g.area(p)-g.area(original)))
 return p

