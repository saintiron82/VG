"""Read-only exact upper supporting field. No globals or geometry are modified."""
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as terrain
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.final_profile_audit_r01 import exact_clip
def exact_subtract(polygons,masks):
 out=list(polygons)
 for mask in masks:
  nxt=[]
  for poly in out:
   overlap=exact_clip.clip(poly,mask)
   if len(overlap)>=3 and geo.polygon_area(overlap)>1e-13:nxt.extend(q for q in exact_clip.difference(poly,mask)if len(q)>=3 and geo.polygon_area(q)>1e-13)
   else:nxt.append(poly)
  out=nxt
  if not out:break
 return out

class ExactTriangleIndex(terrain.TriangleIndex):
 def covering(self,poly):
  for i in self.index.candidates(poly):
   self.candidate_tests+=1;r=self.rows[i];p=exact_clip.clip(poly,r['polygon_xz_m'])
   if p and geo.polygon_area(p)>1e-12:yield dict(r,intersection_polygon_xz_m=p)

class Support:
 def __init__(self,scene,windows,native):self.terrain=ExactTriangleIndex(scene,windows);self.native=ExactTriangleIndex({'surfaces':native},windows)
 def covering(self,p):
  # Exact upper envelope of retained rendered tops. Plane crossings are clipped,
  # so an ordering heuristic can never select a buried surface.
  rows=list(self.native.covering(p))+list(self.terrain.covering(p));claimed=[]
  rows.sort(key=lambda r:-sum(terrain.common.height(r['plane_y_xz_m'],q)for q in r['intersection_polygon_xz_m'])/len(r['intersection_polygon_xz_m']))
  for ri,r in enumerate(rows):
   poly=r['intersection_polygon_xz_m'];plane=r['plane_y_xz_m'];minimum=min(terrain.common.height(plane,q)for q in poly);masks=list(claimed)
   for oi,other in enumerate(rows):
    if oi==ri:continue
    op=other['intersection_polygon_xz_m'];otherplane=other['plane_y_xz_m']
    if max(terrain.common.height(otherplane,q)for q in op)<=minimum+1e-9:continue
    delta=[otherplane[k]-plane[k]for k in range(3)]
    vals=[delta[0]*q[0]+delta[1]*q[1]+delta[2]for q in op]
    if max(vals)<=1e-9:continue
    dom=[];prev=op[-1];pv=delta[0]*prev[0]+delta[1]*prev[1]+delta[2]
    for cur in op:
     cv=delta[0]*cur[0]+delta[1]*cur[1]+delta[2]
     if (pv>=0)!=(cv>=0):
      t=pv/(pv-cv);dom.append([prev[k]+t*(cur[k]-prev[k])for k in range(2)])
     if cv>=0:dom.append(cur)
     prev,pv=cur,cv
    if len(dom)>=3 and geo.polygon_area(dom)>1e-12:masks.append(dom)
   for q in exact_subtract([poly],masks):
    if geo.polygon_area(q)>1e-12:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
