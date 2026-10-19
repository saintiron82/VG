"""One continuous public datum, constrained by accepted finite access profiles.

This is authoring geometry over the existing registered framework. It is not a
runtime terrain engine. A fixed convex region uses its exact affine plane; its
outside influence is the analytic Lipschitz extension of the region boundary.
Conflicting fixed constraints are rejected, never averaged away.
"""
from functools import lru_cache
import json,math
from .survey import HERE
from ..r17_district_batches import author as a
from ... import author as topo
from ..r17_district_batches.audit_retired_boundaries import interval
from ..r17_district_batches import public_tails
from .survey import ROAD_IDS
from . import public_domain
LIMIT=.12
BASELINE_LIMIT=.102  # Includes spring longitudinal 0.082211 + lateral 0.06.

def edge_extrema(p,u,v,yu,yv,limit=LIMIT):
 length=math.dist(u,v)
 if length<1e-10:
  d=math.dist(p,u);return yu-limit*d,yu+limit*d
 tangent=[(v[k]-u[k])/length for k in(0,1)]
 s=sum((p[k]-u[k])*tangent[k]for k in(0,1))
 d=abs((p[0]-u[0])*tangent[1]-(p[1]-u[1])*tangent[0])
 grade=(yv-yu)/length
 if abs(grade)>limit+1e-8:raise ValueError('Fixed edge exceeds extension slope')
 denom=math.sqrt(max(1e-18,limit*limit-grade*grade))
 hi=min(length,max(0.,s+grade*d/denom))
 lo=min(length,max(0.,s-grade*d/denom))
 lower=yu+grade*hi-limit*math.hypot(hi-s,d)
 upper=yu+grade*lo+limit*math.hypot(lo-s,d)
 return lower,upper

class HeightField:
 def __init__(self,regions,segments=()):
  self.regions=[];self.segments=[];self.index=a.geo._SpatialIndex(32)
  for row in regions:
   p=row['polygon_xz_m'];plane=row['plane_y_xz_m']
   if math.hypot(*plane[:2])>LIMIT+1e-8:raise ValueError('Fixed region too steep: '+row['id'])
   ys=[a.common.height(plane,q)for q in p]
   self.add(row['id'],p,ys,plane)
  for row in segments:self.add(row['id'],[[v[0],v[2]]for v in row['xyz_m']],[v[1]for v in row['xyz_m']],None)
 def add(self,id,p,ys,plane):
  # A conservative influence bound follows from baseline 0.102 and extension
  # 0.12 Lipschitz constants. The spring-bank component is slightly steeper
  # than the 0.10 road seed cones; it must not be omitted from this bound.
  dia=max(math.dist(u,v)for u in p for v in p)
  delta=max(abs(y-topo.dry_height_at(*q))for q,y in zip(p,ys))+(LIMIT+BASELINE_LIMIT)*dia
  radius=delta/(LIMIT-BASELINE_LIMIT)+1
  box=a.bounds(p);window=[[box[0]-radius,box[1]-radius],[box[2]+radius,box[1]-radius],[box[2]+radius,box[3]+radius],[box[0]-radius,box[3]+radius]]
  self.index.add(len(self.regions),window)
  self.regions.append(dict(id=id,polygon_xz_m=p,ys=ys,plane=plane,influence_radius_m=radius))
 @lru_cache(maxsize=200000)
 def value(self,x,z):
  p=[x,z];base=topo.dry_height_at(x,z);low=-math.inf;high=math.inf;li=hi=None
  for i in self.index.candidates([p]):
   r=self.regions[i];poly=r['polygon_xz_m'];ys=r['ys']
   if r['plane'] is not None and a.geo.point_in_convex_polygon(p,poly,1e-9):
    bottom=top=a.common.height(r['plane'],p)
   else:
    edges=list(zip(poly,poly[1:]+poly[:1],ys,ys[1:]+ys[:1]))if r['plane']is not None else[(poly[0],poly[1],ys[0],ys[1])]
    e=[edge_extrema(p,u,v,yu,yv)for u,v,yu,yv in edges]
    bottom=max(v[0]for v in e);top=min(v[1]for v in e)
   if bottom>low:low=bottom;li=r['id']
   if top<high:high=top;hi=r['id']
  if low>high+1e-6:raise ValueError(json.dumps(dict(reason='Incompatible fixed public profiles',xz_m=p,lower=low,upper=high,lower_owner=li,upper_owner=hi)))
  return min(high,max(low,base))

def fixed_sources():
 regions=[];segments=[];refs=[]
 def read(path):
  p=a.CITY/path;refs.append(dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)));return json.loads(p.read_bytes())
 b15_path='registered_topography/revisions/r17_district_batches/coherent_b15_r02/fixed_public_seams.json'
 if a.sha(a.CITY/b15_path)!='6024333b9f3278879c9e5033171244ec924a2a410e980642ae4ed790588d245e':raise ValueError('Changed sealed B15 r02 seams')
 b15=read(b15_path)
 for r in b15['roots']:
  rid=r.get('root_id',r.get('id'))
  source_pieces=r.get('fixed_source_regions',r.get('retained_public_source_pieces',[]))
  # Hash-only references preserve provenance but do not define geometry.
  for j,p in enumerate(source_pieces):
   if 'polygon_xz_m' not in p:continue
   regions.append(dict(id=rid+':SOURCE:'+str(j),polygon_xz_m=p['polygon_xz_m'],plane_y_xz_m=p['plane_y_xz_m']))
  for j,p in enumerate(r.get('shared_profile_triangles',[])):
   regions.append(dict(id=rid+':SHARED:'+str(j),polygon_xz_m=p['polygon_xz_m'],plane_y_xz_m=p['plane_y_xz_m']))
  knots=r.get('public_seam_knots_xyz_m')or[]
  for j,(p,q)in enumerate(zip(knots,knots[1:])):segments.append(dict(id=rid+':EDGE:'+str(j),xyz_m=[p,q]))
 nobles=read('traversal_r5/revisions/r06_r8_precinct/public_corridor_priorities_r01/boundary_constraints.json')
 seen=set()
 for r in nobles['retained_property_terminal_triangles']:
  if r['owner_id']in seen:continue
  seen.add(r['owner_id']);t=r['triangle_xyz_m'];regions.append(dict(id=r['owner_id'],polygon_xz_m=[[v[0],v[2]]for v in t],plane_y_xz_m=a.common.plane(t)))
 extra=public_domain.outer_handoff();refs+=public_domain.source_refs();regions+=extra['regions'];segments+=extra['segments']
 water_path=a.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/public_handoff.json'
 if water_path.exists():
  water=read(str(water_path.relative_to(a.CITY)))
  for r in water['exact_public_terminals']:
   for j,(u,v)in enumerate(zip(r['xyz_m'],r['xyz_m'][1:])):segments.append(dict(id=r['id']+':'+str(j),xyz_m=[u,v]))
 common_path='assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/common_entry_repair_r02/fixed_public_interface_r18.json'
 if a.sha(a.CITY/common_path)!='5bde0018f4b2acead65900ea801c790c9b8811924233666d4a9c5d7390284151':raise ValueError('Changed common R02 level terminal')
 common=read(common_path)
 for j,r in enumerate(common['actual_native_piecewise_constant_edge']):
  assert all(v[1]==8 for v in r['edge_xyz_m'])
  segments.append(dict(id=common['id']+':NATIVE_EDGE:'+str(j),xyz_m=r['edge_xyz_m']))
 # Only actual regenerated traffic may constrain this public field. Private
 # plateau interiors are excluded owners, not global road-height controls.
 traffic=public_domain.polygons();ti=a.geo._SpatialIndex(8)
 for i,p in enumerate(traffic):ti.add(i,p)
 clipped=[]
 for r in regions:
  p=r['polygon_xz_m'];parts=a.common.disjoint_union([q for j in ti.candidates(p)if(q:=a.clip(p,traffic[j]))])
  clipped.extend(dict(r,id=r['id']+':PUBLIC:'+str(j),polygon_xz_m=q)for j,q in enumerate(parts))
 kept=[]
 for r in segments:
  if r['id'].startswith('RETAINED_JUNCTION:'):
   # These exact terminal segments are the already-verified outer boundary
   # of the added masks. Keep them verbatim, rather than dropping a boundary
   # whose recomputed polygon differs by sub-picometre roundoff.
   kept.append(r);continue
  u,v=r['xyz_m'];p=[u[0],u[2]];q=[v[0],v[2]];spans=sorted([s for j in ti.candidates([p,q])if(s:=interval(p,q,traffic[j]))]);merged=[]
  for lo,hi in spans:
   if merged and lo<=merged[-1][1]+1e-9:merged[-1][1]=max(merged[-1][1],hi)
   else:merged.append([lo,hi])
  for j,(lo,hi)in enumerate(merged):
   if (hi-lo)*math.dist(p,q)>1e-8:kept.append(dict(r,id=r['id']+':PUBLIC:'+str(j),xyz_m=[[u[k]+t*(v[k]-u[k])for k in range(3)]for t in(lo,hi)]))
 regions,segments=clipped,kept
 return regions,segments,refs

def main():
 regions,segments,refs=fixed_sources();field=HeightField(regions,segments);errors=[];tested=0
 for r in field.regions:
  p=r['polygon_xz_m'];ys=r['ys'];edges=list(zip(p,p[1:]+p[:1],ys,ys[1:]+ys[:1]))if r['plane']is not None else[(p[0],p[1],ys[0],ys[1])]
  for u,v,yu,yv in edges:
   for t in (0,.25,.5,.75,1):
    q=[u[k]+t*(v[k]-u[k])for k in(0,1)];y=yu+t*(yv-yu);tested+=1
    try:actual=field.value(*q)
    except ValueError as exc:errors.append(dict(owner=r['id'],error=str(exc)));continue
    if abs(actual-y)>1e-6:errors.append(dict(owner=r['id'],xz_m=q,expected=y,actual=actual))
 report=dict(schema='riverstone.r18.shared_public_field.v1',status='FIXED_PROFILES_COMPATIBLE'if not errors else'HELD_CONSTRAINT_CONFLICT',source_refs=refs,fixed_regions=len(regions),fixed_segments=len(segments),tested_points=tested,errors=errors,extension_grade=LIMIT,activation=False)
 (HERE/'fixed_profile_review.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print({k:v for k,v in report.items()if k not in('source_refs','errors')});print('errors',len(errors),errors[:3])
if __name__=='__main__':main()
