"""Finite source/native interface audit; no capsule or exported mesh claim."""
import json,math,collections
from . import author as a

def run():
 gates=[];maxgrad=0.;outer=[]
 for p in a.HANDOFF['properties']:
  g=p['finite_gate_approach'];poly=g['polygon_xz_m'];hs=[]
  for i in range(17):
   t=i/16
   for j in range(17):
    s=j/16;pt=[(1-t)*((1-s)*poly[0][k]+s*poly[1][k])+t*((1-s)*poly[3][k]+s*poly[2][k]) for k in (0,1)];hs.append(a.land_height_at(*pt))
  gates.append(dict(property_id=p['property_id'],floor_y_m=p['finished_floor_y_m'],sample_count=len(hs),maximum_floor_error_m=max(abs(y-p['finished_floor_y_m']) for y in hs)))
 b=a.COLLAR_BOUNDS
 for i in range(101):
  u=i/100
  for x,z in [(b[0]+u*(b[2]-b[0]),b[1]),(b[0]+u*(b[2]-b[0]),b[3]),(b[0],b[1]+u*(b[3]-b[1])),(b[2],b[1]+u*(b[3]-b[1]))]:
   r=a.expanded_record(a.prior.owner_at(x,z),x,z)
   if a.collar_eligible(r):outer.append(max(0,a.COLLAR_FLOOR-a.COLLAR_GRADE*a.gate_distance(x,z)-a.prior.source_surface_height_at(r,x,z)))
 roads=[r for r in a.prior.prior.r07._owners() if r['kind']=='road' and r.get('road_id')==a.COLLAR_ROAD]
 road_samples=0;maxdelta=0
 for r in roads:
  q=a.clean(a.geo.convex_intersection(r['polygon_xz_m'],a.COLLAR_BOX))
  if not q:continue
  x0=min(v[0] for v in q);x1=max(v[0] for v in q);z0=min(v[1] for v in q);z1=max(v[1] for v in q)
  for ix in range(math.floor(x0*2),math.ceil(x1*2)+1):
   for iz in range(math.floor(z0*2),math.ceil(z1*2)+1):
    x,z=ix/2,iz/2
    if not a.geo.point_in_convex_polygon([x,z],q,1e-8):continue
    f=lambda x,z:a.road_height_at(a.COLLAR_ROAD,x,z)
    e=.001;gx=(f(x+e,z)-f(x-e,z))/(2*e);gz=(f(x,z+e)-f(x,z-e))/(2*e);maxgrad=max(maxgrad,math.hypot(gx,gz));road_samples+=1;maxdelta=max(maxdelta,f(x,z)-a.prior.road_height_at(a.COLLAR_ROAD,x,z))
 native_conflicts=[];protected=[]
 for r in a.prior.surface_domains(a.COLLAR_BOUNDS,False):
  if a.R04.prior.is_excluded(r,a.EXCLUDED):continue
  if a.collar_eligible(r):continue
  if r['kind'].startswith('r14_'):continue
  for p in r['polygon_xz_m']:
   h=a.prior.source_surface_height_at(r,*p);needed=a.COLLAR_FLOOR-a.COLLAR_GRADE*a.gate_distance(*p)-h
   if needed>1e-6:protected.append(dict(owner_id=r['owner_id'],kind=r['kind'],point_xz_m=p,envelope_above_preserved_owner_m=needed))
 route_report=[]
 for r in a.ACCESS['routes']:
  vals=[]
  for poly in r['ribbon_polygons_xz_m']+r['join_polygons_xz_m']:
   for p,q in zip(poly,poly[1:]+poly[:1]):
    n=max(1,math.ceil(math.dist(p,q)))
    vals.extend(a.land_height_at(p[0]+i/n*(q[0]-p[0]),p[1]+i/n*(q[1]-p[1])) for i in range(n+1))
  route_report.append(dict(route_id=r['id'],sample_count=len(vals),maximum_floor_error_m=max(abs(v-r['gate_y_m']) for v in vals)))
 result=dict(schema='riverstone.r14_bounded_interface_audit.v1',author_sha256=a.R04.sha(a.HERE/'author.py'),gates=gates,precinct_routes=route_report,merchant_collar_outer_delta_m=max(outer,default=0),merchant_public_gradient_sample_count=road_samples,maximum_sampled_public_gradient=maxgrad,maximum_public_uplift_m=maxdelta,protected_owner_envelope_conflicts=protected,limitations=['Source profiles only; actual triangulated preview grades and capsule remain separate.','Abbey shoulder has finite retaining preview and a separately bound native timber guard; no capsule approval.'])
 (a.HERE/'interface_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('gates','precinct_routes','protected_owner_envelope_conflicts')},indent=2));print('gate_errors',gates);print('route_errors',route_report);print('protected_envelope_conflicts',len(protected),str(protected[:5]))
 return result
if __name__=='__main__':run()
