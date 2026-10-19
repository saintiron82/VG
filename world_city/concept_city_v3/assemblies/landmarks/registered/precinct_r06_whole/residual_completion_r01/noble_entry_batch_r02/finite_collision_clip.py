"""Disjoint finite 3-D prism partition, including boundary-coincident side faces."""
import math
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg

def cross(a,b):return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def area3(p):
 return sum(math.sqrt(sum(v*v for v in cross([p[i][k]-p[0][k]for k in range(3)],[p[i+1][k]-p[0][k]for k in range(3)])))/2 for i in range(1,len(p)-1))if len(p)>2 else 0.
def clean(p):
 out=[]
 for v in p:
  if not out or math.dist(out[-1],v)>1e-12:out.append(v)
 if len(out)>1 and math.dist(out[0],out[-1])<=1e-12:out.pop()
 return out if area3(out)>1e-12 else[]
def clip3(p,fn,inside=True):
 if not p:return[]
 ds=[fn(v)for v in p];sgn=1 if inside else-1
 if all(d==0 for d in ds):return p if inside else[]
 out=[]
 for a,b,da,db in zip(p,p[1:]+p[:1],ds,ds[1:]+ds[:1]):
  ia=sgn*da>=0;ib=sgn*db>=0
  if ia:out.append(a)
  if ia!=ib:
   t=da/(da-db);out.append([a[k]+t*(b[k]-a[k])for k in range(3)])
 return clean(out)
def cutprism(p,poly):
 poly=fg.normalize_mask(poly)
 if len(poly)<3 or fg.area(poly)<=1e-14:return[p],[]
 sign=1 if fg.signed_area(poly)>0 else-1;inside=p;outside=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  L=math.dist(a,b)
  if L<=1e-12:continue
  def fn(v):
   d=sign*fg.cross(a,b,[v[0],v[2]])/L
   return 0. if abs(d)<1e-11 else d
  part=clip3(inside,fn,False)
  if part:outside.append(part)
  inside=clip3(inside,fn)
  if not inside:break
 return outside,inside
