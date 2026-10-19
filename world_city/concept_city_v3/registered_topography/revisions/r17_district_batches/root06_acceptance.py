"""Exact private/public ramp ownership proof; boundary curbs are not route crossings."""
import json,math
from . import author as a,side_clearance,public_tails,preflight_layout

def run():
 folder=a.HERE/'root06_regrade_r04';out=folder/'acceptance.json'
 if out.exists():raise SystemExit('Preserve acceptance evidence')
 profile=json.loads((folder/'profile.json').read_bytes());interfaces=json.loads((folder/'interfaces.json').read_bytes());p=profile['polygon_xz_m'];scene=a.load_scene();layout=json.loads((public_tails.FABRIC/'selected_layout.json').read_bytes());hand=json.loads((public_tails.FABRIC/'terrain_handoff.json').read_bytes());protected=[]
 projection=json.loads((a.CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_bytes())
 for inst in projection['instances']:
  if inst['id']not in layout['retired_source_ids']:
   protected.extend((inst['id'],q)for q in inst['native_owner_parts_xz_m'])
 protected.extend((r['surface_id'],r['polygon_xz_m'])for r in scene['terrain_contract']['water_domain_polygons'])
 protected.extend((r['id'],r.get('polygon_xz_m',r.get('polygon')))for r in hand['protected_regions'])
 for parcel in hand['parcels']:
  protected.extend((f['id'],q)for f in parcel.get('native_footing_owners',[])for q in f['polygons_xz_m'])
 for r in layout['placements']:protected.extend((r['id'],q)for q in r['native_walking_obstacles_xz_m'])
 pi=a.geo._SpatialIndex(16)
 for j,(_,q)in enumerate(protected):pi.add(j,q)
 conflicts=[]
 for j in pi.candidates(p):
  rid,q=protected[j];cut=a.clip(p,q)
  if cut and a.geo.polygon_area(cut)>1e-7:conflicts.append(dict(id=rid,area_m2=a.geo.polygon_area(cut),polygon_xz_m=cut))
 # Closed clear-volume intersections along a nonwalking lateral curb must have
 # every point on the exterior boundary. Recheck the open route interior at 1um.
 sign=1 if a.geo.signed_polygon_area(p)>0 else-1
 def dist(v,u,w):return sign*a.geo._cross(u,w,[v[0],v[2]])/math.dist(u,w)
 classified=[];interior=[]
 for c in interfaces['after_side_clearance']['contacts']:
  q=c['intersection_vertices_xyz_m'];boundary_distance=max(min(abs(dist(v,u,w))for u,w in zip(p,p[1:]+p[:1]))for v in q)
  clipped=q
  for u,w in zip(p,p[1:]+p[:1]):clipped=side_clearance.halfspace(clipped,lambda v:dist(v,u,w)-1e-6)
  area=side_clearance.area3d(clipped)
  row=dict(c,boundary_distance_m=boundary_distance,open_interior_contact_area_m2=area,classification='LATERAL_BOUNDARY_CURB'if area<1e-10 and boundary_distance<1e-7 else'INTERIOR_BLOCKER');classified.append(row)
  if row['classification']=='INTERIOR_BLOCKER':interior.append(row)
 plan=json.loads(a.PLAN_PATH.read_bytes());road=next(r for r in plan['roads']if r['id']==profile['road_id']);j=profile['road_segment_index'];public=a.geo.road_ribbon(road['polyline_xz_m'][j],road['polyline_xz_m'][j+1],road['width_m']);q=a.clip(p,public);public_area=a.geo.polygon_area(q)if q else 0.
 index=a.TriangleIndex(scene,[p]);preflight_layout.virtual_restorations(index,layout);coverage=a.audit_polygon(index,p)
 d=dict(schema='riverstone.r17.finite_ramp_acceptance.v1',profile_sha256=a.sha(folder/'profile.json'),interfaces_sha256=a.sha(folder/'interfaces.json'),protected_conflicts=conflicts,public_traffic_overlap_area_m2=public_area,source_coverage=coverage,closed_boundary_contacts=classified,interior_contacts=interior,maximum_gradient=profile['maximum_gradient'],exact_fixed_seam_error_m=profile['maximum_fixed_error_m'],nonwalking_side_policy='Finite lateral curbs/retaining faces occupy only the outer boundary; no crossing is claimed. The full open 3.5 m route interior and both terminal seams remain clear.',passes=not(conflicts or interior or interfaces['uncovered_boundary_segments'])and public_area<1e-7 and coverage['missing_area_m2']<1e-7 and profile['maximum_gradient']<=.12,activation=False)
 out.write_text(json.dumps(d,separators=(',',':'))+'\n');print({k:d[k]for k in('passes','public_traffic_overlap_area_m2','maximum_gradient')});print('protected',len(conflicts),'interior',len(interior),'boundary',len(classified));print(a.sha(out))
if __name__=='__main__':run()
