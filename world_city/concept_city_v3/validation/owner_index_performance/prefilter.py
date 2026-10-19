"""Explicit opt-in owner lookup. No source file/module mutation or auto-activation.

Keep the original32m candidate set, sorted owner priority, boundary tolerance,
LRU size and base fallback. Bounding boxes only choose cheap existing edge
predicates; they never directly reject a record. A skipped record therefore
fails exactly the same predicate the original polygon test would execute.
"""
import math,json,hashlib
from pathlib import Path
from functools import lru_cache

class OwnerLookup:
 def __init__(self,source):
  self.source=source;self.owners=source._owners();self.index=source.INDEX;self.geo=source.geo;self.prepared=[]
  binding=json.loads((Path(__file__).parent/'candidate_binding.json').read_text())
  digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
  if digest(source.__file__)!=binding['source']['sha256'] or digest(self.geo.__file__)!=binding['geometry_helper']['sha256']:raise ValueError('Owner prefilter source binding changed')
  if hashlib.sha256(json.dumps(self.owners,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=binding['ordered_owners_sha256']:raise ValueError('Ordered owner snapshot changed')
  if self.index.cell_m!=32 or len(self.owners)!=binding['owner_count']:raise ValueError('Owner index contract changed')
  for r in self.owners:
   p=r['polygon_xz_m'];xs=[q[0] for q in p];zs=[q[1] for q in p];limits=[min(xs),min(zs),max(xs),max(zs)];orientation=1.0 if self.geo.signed_polygon_area(p)>0 else -1.0
   selected=[]
   for values,value in [(xs,limits[0]),(zs,limits[1]),(xs,limits[2]),(zs,limits[3])]:
    j=values.index(value);edges=[]
    for k in [(j-1)%len(p),j]:
     a,b=p[k],p[(k+1)%len(p)];length=math.dist(a,b)
     if length>self.geo.NUMERIC_EPSILON:edges.append((a,b,length,orientation))
    selected.append(edges)
   self.prepared.append((limits,selected))
  self.owner_at=lru_cache(maxsize=262144)(self.lookup)
 def rejects(self,point,i):
  x,z=point;box,edges=self.prepared[i]
  sides=[]
  if x<box[0]:sides.append(0)
  elif x>box[2]:sides.append(2)
  if z<box[1]:sides.append(1)
  elif z>box[3]:sides.append(3)
  for side in sides:
   for a,b,length,orientation in edges[side]:
    if orientation*self.geo._cross(a,b,point)/length < -1e-8-self.geo.NUMERIC_EPSILON:return True
  return False
 def lookup(self,x,z):
  point=[x,z]
  for i in sorted(self.index.candidates([[x,z]])):
   if self.rejects(point,i):continue
   r=self.owners[i]
   if self.geo.point_in_convex_polygon(point,r['polygon_xz_m'],1e-8):return r
  return dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot')
