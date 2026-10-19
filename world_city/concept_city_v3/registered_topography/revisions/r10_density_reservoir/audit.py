"""Bounded exact-polygon and sampled-height checks; no physics or city compile."""
import json,math
from . import author as a

def samples(poly):
 out=list(poly);out.append([sum(p[k] for p in poly)/len(poly) for k in (0,1)])
 for x,y in zip(poly,poly[1:]+poly[:1]):
  n=max(1,math.ceil(math.dist(x,y)/.5));out += [[(1-i/n)*x[k]+i/n*y[k] for k in (0,1)] for i in range(1,n)]
 return out

def run():
 wet=a.finite_water_polygons();wi=a.geo._SpatialIndex(16)
 for i,r in enumerate(wet):wi.add(i,r['polygon_xz_m'])
 def wetarea(p):return sum(a.geo.intersection_area(p,wet[i]['polygon_xz_m']) for i in wi.candidates(p))
 density=[r for r in a.OWNERS if r['kind'].startswith('b015_')];native=[r for r in density if r['kind']=='b015_native_hole'];entries=[r for r in density if r['kind']!='b015_native_hole'];water_hits=[dict(owner_id=r['owner_id'],area_m2=s) for r in density if(s:=wetarea(r['polygon_xz_m']))>1e-8]
 road_polys=[r for r in a.r07._owners() if r['kind']=='road'];ri=a.geo._SpatialIndex(16)
 for i,r in enumerate(road_polys):ri.add(i,r['polygon_xz_m'])
 native_road=[dict(owner_id=r['owner_id'],road_id=road_polys[i]['road_id'],area_m2=s) for r in native for i in ri.candidates(r['polygon_xz_m']) if(s:=a.geo.intersection_area(r['polygon_xz_m'],road_polys[i]['polygon_xz_m']))>1e-8]
 deltas=[abs(a.height_at(*d['actual_door_xyz_m'][::2])-d['actual_door_xyz_m'][1]) for d in a.DENSITY['access_proposals']]
 entry_deltas=[dict(owner_id=r['owner_id'],point_xz_m=q,delta_m=a.height_at(*q)-2.5) for r in entries for q in samples(r['polygon_xz_m']) if abs(a.height_at(*q)-2.5)>1e-7]
 route=a.HANDOFF['replacement_route'];ps=route['points_xyz_m'];service_samples=[]
 for u,v in zip(ps,ps[1:]):
  L=math.hypot(v[0]-u[0],v[2]-u[2]);n=max(1,math.ceil(L/.1));normal=[-(v[2]-u[2])/L,(v[0]-u[0])/L]
  for i in range(n+1):
   for side in (-.7,-.35,0,.35,.7):
    x=u[0]+(v[0]-u[0])*i/n+normal[0]*side;z=u[2]+(v[2]-u[2])*i/n+normal[1]*side;service_samples.append(abs(a.height_at(x,z)-18))
 grades=[];outer=[];h=.001;x0,z0,x1,z1=a.BOUNDS
 for i in range(math.ceil((x1-x0)*2)+1):
  x=x0+i/2
  for j in range(math.ceil((z1-z0)*2)+1):
   z=z0+j/2;r=a.prior.owner_at(x,z)
   if r['kind']=='road' and r.get('road_id')==a.ROAD:
    gx=(a.road_height_at(a.ROAD,x+h,z)-a.road_height_at(a.ROAD,x-h,z))/(2*h);gz=(a.road_height_at(a.ROAD,x,z+h)-a.road_height_at(a.ROAD,x,z-h))/(2*h);grades.append(math.hypot(gx,gz))
 for u,v in zip(a.BOX,a.BOX[1:]+a.BOX[:1]):
  for q in samples([u,v]):
   r=a.prior.owner_at(*q)
   if a.eligible_transition(r):outer.append(abs(a.source_surface_height_at(a.transition(r),*q)-a.prior.source_surface_height_at(r,*q)))
 # Source road triangles are the exact finite replacement profile.
 tri_grades=[];cutfill=[]
 for t in a.SOUTH['triangles']:
  p=t['vertices_xyz_m'];u=[p[1][k]-p[0][k] for k in range(3)];v=[p[2][k]-p[0][k] for k in range(3)];det=u[0]*v[2]-u[2]*v[0];gx=(u[1]*v[2]-u[2]*v[1])/det;gz=(u[0]*v[1]-u[1]*v[0])/det;tri_grades.append(math.hypot(gx,gz))
  for q in samples(t['polygon_xz_m']):cutfill.append(a.R04.point_y(p,*q)-a.prior.land_height_at(*q))
 tail=[]
 for r in a.R04._owners():
  if not a.stale_tail(r):continue
  p=a.clean(a.geo.convex_intersection(r['polygon_xz_m'],a.TAIL_CLIP))
  if not p:continue
  parts=[p]
  for old in tail:parts=[q for pp in parts for cut in a.geo.convex_difference(pp,old['polygon_xz_m']) if(q:=a.clean(cut))]
  tail.extend(dict(old_owner_id=r['owner_id'],old_kind=r['kind'],polygon_xz_m=q) for q in parts)
 total=sum(a.geo.polygon_area(r['polygon_xz_m']) for r in tail);road=sum(a.geo.intersection_area(r['polygon_xz_m'],t['polygon_xz_m']) for r in tail for t in a.SOUTH['triangles'])
 restoration=dict(scope_polygon_xz_m=a.TAIL_CLIP,records=tail,restored_total_m2=total,replaced_by_new_road_m2=road,restored_dry_shoulder_m2=total-road,native_stone_protection='Every restored point lies beyond actual stone localX72; exact common cache ends at72.',water_protection='Water owner never restored or overlaid')
 (a.HERE/'south_tail_restoration.json').write_text(json.dumps(restoration,indent=2)+'\n')
 report=dict(status='bounded_source_geometry_checks',input_hashes={str(p.relative_to(a.CITY)):h for p,h in [(a.DENSITY_PATH,a.DENSITY_SHA),(a.SERVICE_PATH,a.SERVICE_SHA),(a.HANDOFF_PATH,a.HANDOFF_SHA),(a.SOUTH_PATH,a.SOUTH_SHA)]},native_foundation_regions=len(native),actual_thresholds=len(deltas),maximum_threshold_delta_m=max(deltas),density_water_conflicts=water_hits,native_road_conflicts=native_road,entry_profile_exceptions=entry_deltas,maximum_entry_profile_delta_m=max([abs(r['delta_m']) for r in entry_deltas] or [0]),service_route_samples=len(service_samples),maximum_service_route_delta_m=max(service_samples),actual_service_public_flat_regions=len(a.PUBLIC_FLAT),maximum_sampled_service_road_gradient=max(grades),maximum_service_outer_boundary_change_m=max(outer),south_triangle_count=len(tri_grades),south_maximum_full_triangle_grade=max(tri_grades),south_water_overlap_m2=sum(wetarea(t['polygon_xz_m']) for t in a.SOUTH['triangles']),south_source_cut_fill_range_m=[min(cutfill),max(cutfill)],tail_restoration={k:v for k,v in restoration.items() if k!='records'},water_domain_count=len(wet),ordinary_foundation_count=len(a.ordinary_foundation_contracts()),excluded_source_count=len(a.EXCLUDED),limits=['New public profile is analytically sampled only; surrounding exported triangle gradients/capsule unverified.','Reservoir ring native bearing and cross-pack guard/sluice interfaces remain independently reviewable.','Inherited recovered public landing mask has1.46416e-6m² known preview-filter residual.'])
 (a.HERE/'bounded_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('input_hashes','entry_profile_exceptions','tail_restoration')}),flush=True)
 assert not water_hits and not native_road and max(deltas)<1e-7 and not entry_deltas
 assert max(service_samples)<1e-7 and max(grades)<=.12001 and max(outer)<1e-7
 assert report['south_water_overlap_m2']<1e-8 and max(tri_grades)<.01
 return report
if __name__=='__main__':run()
