"""Source-boundary roundoff diagnosis, preserving strict R01 evidence.
A 1 nm signed-distance classification band is reported, not used to alter any
ownership polygon, endpoint, plane, collision input, or controller threshold.
"""
import json,math
from . import public_domain as d
from .survey import HERE,ROAD_IDS
from ..r17_district_batches import author as a
from ..r17_district_batches.audit_retired_boundaries import interval as strict_interval
BOUNDARY_ROUNDOFF_M=1e-9
SOURCES=[('contour_bulk_r01','75838459adef3a81f7078dd8bad5b068ad6533e6ce72a71b445fb145b118a33f'),('remaining_level_r01','f85ef5062d4b16fc42ae50ae3c6ef7a545aefff7a9035a30b43ad88eab46a2f8')]
def boundary_interval(p,q,poly):
 sign=1 if a.geo.signed_polygon_area(poly)>0 else -1;lo,hi=0.,1.
 for u,v in zip(poly,poly[1:]+poly[:1]):
  length=math.dist(u,v)
  if length<1e-12:continue
  f=sign*a.geo._cross(u,v,p)/length;g=sign*a.geo._cross(u,v,q)/length
  if abs(f)<=BOUNDARY_ROUNDOFF_M:f=0.
  if abs(g)<=BOUNDARY_ROUNDOFF_M:g=0.
  delta=g-f
  if abs(delta)<1e-13:
   if f<0:return None
  elif delta>0:lo=max(lo,-f/delta)
  else:hi=min(hi,-f/delta)
  if lo>hi:return None
 return[lo,hi]if hi-lo>1e-10 else None

def merged_spans(fn,p,q,polys,candidates):
 merged=[]
 for lo,hi in sorted(s for i in candidates if(s:=fn(p,q,polys[i]))):
  if merged and lo<=merged[-1][1]+1e-9:merged[-1][1]=max(hi,merged[-1][1])
  else:merged.append([lo,hi])
 return merged

def main():
 polygons=d.polygons();ix=a.geo._SpatialIndex(8)
 for i,p in enumerate(polygons):ix.add(i,p)
 rows=[];sources=[]
 for folder,expected in SOURCES:
  p=a.CITY/'registered_topography/revisions/r17_district_batches'/folder/'public_interface_requests.json';assert a.sha(p)==expected;sources.append(dict(path=str(p.relative_to(a.ROOT)),sha256=expected))
  for r in json.loads(p.read_bytes())['entries']:
   p,q=r['requested_public_edge_xz_m'];length=math.dist(p,q);cs=ix.candidates([p,q]);strict=merged_spans(strict_interval,p,q,polygons,cs);boundary=merged_spans(boundary_interval,p,q,polygons,cs);missing=length*(1-sum(hi-lo for lo,hi in boundary));rows.append(dict(holding_id=r['holding_id'],public_road_id=r['public_road_id'],source_group=folder,edge_xz_m=[p,q],length_m=length,strict_uncovered_length_m=length*(1-sum(hi-lo for lo,hi in strict)),boundary_matched_uncovered_length_m=missing,boundary_matched_t_intervals=boundary,primary16=r['public_road_id']in ROAD_IDS,status='DOMAIN_CLASSIFICATION_ONLY_PROFILE_PENDING'if missing<=1e-7 else'FINITE_FRONTAGE_NOT_FULLY_IN_CURRENT_DOMAIN'))
 out=dict(source_refs=sources+ d.source_refs(),boundary_roundoff_classification_m=BOUNDARY_ROUNDOFF_M,rows=rows,scope=__doc__)
 (HERE/'contour_domain_screen_r02.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('total',len(rows),'in domain',sum(r['boundary_matched_uncovered_length_m']<=1e-7 for r in rows),'needs finite review',sum(r['boundary_matched_uncovered_length_m']>1e-7 for r in rows))
if __name__=='__main__':main()
