"""Local finite polygon clipping with metre-normalized halfplanes.

R7 contains very short source edges. Normalize each edge before testing instead
of interpreting a fixed cross-product epsilon as a distance. This is a bounded
source-field helper, not a voxel compiler or an alteration of shared geometry.
"""
import math
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.runtime_city.checks import placement as g

def clean(p):
 out=[]
 for x in p:
  if not out or math.dist(x,out[-1])>1e-10:out.append(list(x))
 if len(out)>1 and math.dist(out[0],out[-1])<1e-10:out.pop()
 return out if len(out)>=3 and g.polygon_area(out)>1e-10 else[]
def half(poly,fn):
 if not poly:return[]
 out=[];p=poly[-1];fp=fn(p)
 for q in poly:
  fq=fn(q)
  if (fp>=0)!=(fq>=0):
   t=fp/(fp-fq);out.append([p[i]+t*(q[i]-p[i])for i in(0,1)])
  if fq>=0:out.append(q)
  p,fp=q,fq
 return clean(out)
def intersect(p,q):
 out=clean(p);q=clean(q)
 if not out or not q:return[]
 sign=1 if g.signed_polygon_area(q)>0 else-1
 for u,v in zip(q,q[1:]+q[:1]):
  L=math.dist(u,v)
  if L<1e-10:continue
  out=half(out,lambda x:sign*g._cross(u,v,x)/L)
  if not out:break
 return out

def difference(p,q):
 inside=clean(p);q=clean(q);out=[]
 if not q:return[inside]if inside else[]
 sign=1 if g.signed_polygon_area(q)>0 else-1
 for u,v in zip(q,q[1:]+q[:1]):
  L=math.dist(u,v)
  if L<1e-10:continue
  fn=lambda x:sign*g._cross(u,v,x)/L;part=half(inside,lambda x:-fn(x))
  if part:out.append(part)
  inside=half(inside,fn)
  if not inside:break
 return out

def subtract(polys,masks):
 out=polys
 for m in masks:
  nxt=[]
  for p in out:
   if intersect(p,m):nxt.extend(difference(p,m))
   else:nxt.append(p)
  out=nxt
  if not out:break
 return out

def audit(index,poly):
 pieces=[]
 for i in index.index.candidates(poly):
  r=index.rows[i];q=intersect(poly,r['polygon_xz_m'])
  if not q:continue
  ys=[a.common.height(r['plane_y_xz_m'],x)for x in q];pieces.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],area_m2=g.polygon_area(q),min_y_m=min(ys),max_y_m=max(ys),actual_triangle_grade=math.hypot(*r['plane_y_xz_m'][:2])))
 gap=subtract([poly],[r['polygon_xz_m']for r in pieces]);missing=sum(g.polygon_area(q)for q in gap);area=g.polygon_area(poly);covered=sum(r['area_m2']for r in pieces)
 return dict(area_m2=area,covered_area_m2=covered,missing_area_m2=missing,excess_area_m2=max(0,covered-area+missing),source_pieces=pieces,uncovered_polygons_xz_m=gap,method='Exact source planes; local metre-normalized finite clipping for short R7 edges.')

def interval(p,q,poly,tolerance_m=1e-9):
 """Closed line/convex-polygon span with metre-scaled collinearity tolerance."""
 sign=1 if g.signed_polygon_area(poly)>0 else-1;lo,hi=0.,1.
 for u,v in zip(poly,poly[1:]+poly[:1]):
  L=math.dist(u,v)
  if L<1e-10:continue
  f=sign*g._cross(u,v,p)/L;h=sign*g._cross(u,v,q)/L
  if abs(f)<tolerance_m:f=0.
  if abs(h)<tolerance_m:h=0.
  d=h-f
  if abs(d)<1e-13:
   if f<0:return None
  else:
   t=-f/d
   if d>0:lo=max(lo,t)
   else:hi=min(hi,t)
  if lo>hi+1e-12:return None
 return[max(0.,lo),min(1.,hi)]if hi-lo>1e-10 else None
