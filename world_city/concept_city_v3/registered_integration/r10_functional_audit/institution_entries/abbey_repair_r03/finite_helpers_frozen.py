"""Verbatim common helper definitions from preserved r07 (c52962...). Original r02 full producer f9c43... was not preserved. No new clipping/height algorithm."""
import math
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import fan
def xz(p):return [p[0],p[2]]

def area3(t):
 a,b,c=t;u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)];return math.sqrt(sum(n*n for n in [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]))/2

def plane(t):
 a,b,c=t;d=(b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2]);ax=((b[1]-a[1])*(c[2]-a[2])-(c[1]-a[1])*(b[2]-a[2]))/d;az=((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))/d;return ax,az,a[1]-ax*a[0]-az*a[2]

def ph(pl,p):return pl[0]*p[0]+pl[1]*p[1]+pl[2]

def up(t):return t if geo.signed_polygon_area([xz(v)for v in t])<0 else [t[0],t[2],t[1]]

def split3(poly,a,b,sgn):
 def side(p):return sgn*((b[0]-a[0])*(p[2]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
 inside=[];outside=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  d,e=side(p),side(q);pi=d>=0.;qi=e>=0.
  (inside if pi else outside).append(p)
  if pi!=qi:
   t=d/(d-e);v=[p[k]+t*(q[k]-p[k])for k in range(3)];inside.append(v);outside.append(v)
 return inside,outside

def cut3(poly,mask):
 cur=poly;out=[];sgn=1 if geo.signed_polygon_area(mask)>0 else -1
 for a,b in zip(mask,mask[1:]+mask[:1]):
  if not cur:break
  cur,outer=split3(cur,a,b,sgn)
  if len(outer)>=3 and sum(area3(t)for t in fan(outer))>1e-10:out.append(outer)
 return out

class Ground:
 def __init__(self,rows):
  self.rows=[];self.idx=geo._SpatialIndex(8)
  for r in rows:
   t=r['triangle'];p=[xz(v)for v in t]
   if r['material']=='water' or geo.polygon_area(p)<1e-9:continue
   self.idx.add(len(self.rows),p);self.rows.append(dict(r,polygon=p,plane=plane(t)))
 def at(self,p):
  found=[r for i in self.idx.candidates([p])if geo.point_in_convex_polygon(p,(r:=self.rows[i])['polygon'],1e-7)]
  if not found:raise ValueError('No source ground '+str(p))
  road=[r for r in found if r['material']=='road'];return max(ph(r['plane'],p)for r in (road or found))
