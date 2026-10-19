"""Finite source-reservation profile release; unrelated held triangles remain held."""
import json,math,time
from .height_field import HERE
from . import public_domain as d
from .grid_candidate import grade
from ..r17_district_batches import author as a

def main():
 start=time.monotonic();request_path=a.CITY/'registered_topography/revisions/r17_district_batches/contour_bulk_r01/exact_public_reservations.json';assert a.sha(request_path)=='fcca52f49b1377478e604e2108cde1b0689d6d7f1e65a6df0a087b61941be15e';requests=json.loads(request_path.read_bytes());mesh_path=HERE/'field_refinement_r01.json';mesh=json.loads(mesh_path.read_bytes());triangles=mesh['triangles_xyz_m'];ix=a.geo._SpatialIndex(8);traffic=d.polygons();ti=a.geo._SpatialIndex(8)
 for n,t in enumerate(triangles):ix.add(n,[[v[0],v[2]]for v in t])
 for n,p in enumerate(traffic):ti.add(n,p)
 mask_path=HERE/'boundary_ownership_inputs_r01.json';ownership=json.loads(mask_path.read_bytes());assert all(a.sha(a.ROOT/r['path'])==r['sha256']for r in ownership['source_refs']);masks=ownership['masks'];mi=a.geo._SpatialIndex(8)
 for n,m in enumerate(masks):mi.add(n,m['polygon_xz_m'])
 rows=[]
 for entry in requests['entries']:
  requested=entry['public_union_parts_xz_m'];active=[]
  for p in requested:active.extend(a.clip(p,traffic[n])for n in ti.candidates(p)if a.clip(p,traffic[n]))
  active=a.common.disjoint_union(active);outside=a.common.subtract(requested,active);owned=[];excluded=[]
  for p in active:
   local=[masks[n]['polygon_xz_m']for n in mi.candidates(p)];remaining=a.common.subtract([p],local);owned.extend(remaining);excluded.extend(a.common.subtract([p],remaining))
  profiles=[];held=[]
  for p in owned:
   for n in sorted(ix.candidates(p)):
    t=triangles[n];q=a.clip(p,[[v[0],v[2]]for v in t])
    if not q:continue
    plane=a.common.plane(t);xyz=[[v[0],a.common.height(plane,v),v[1]]for v in q];r=dict(id=entry['holding_id']+':R18:'+str(n)+':'+str(len(profiles)),source_triangle_index=n,polygon_xz_m=q,plane_y_xz_m=plane,triangles_xyz_m=list(a.fan_upward(xyz)),gradient=grade(t));profiles.append(r)
    if grade(t)>.12+1e-7:held.append(r)
  uncovered=a.common.subtract(owned,[r['polygon_xz_m']for r in profiles]);area=lambda ps:sum(a.geo.polygon_area(p)for p in ps)
  status='READY_EXACT_R18_PROFILE_PORTIONS'if not held and area(uncovered)<1e-7 else'HELD_LOCAL_GRADIENT_OR_COVERAGE'
  if not profiles:status='RETAINED_OR_SEALED_OWNER_HANDOFF_REQUIRED'
  rows.append(dict(holding_id=entry['holding_id'],public_road_id=entry['named_public_road_id'],status=status,source_reserved_route_polygons_xz_m=entry['source_reserved_route_polygons_xz_m'],profile_regions=profiles,held_source_triangle_ids=sorted(set(r['source_triangle_index']for r in held)),profile_area_m2=area([r['polygon_xz_m']for r in profiles]),uncovered_r18_polygons_xz_m=uncovered,uncovered_r18_area_m2=area(uncovered),outside_r18_polygons_xz_m=outside,outside_r18_area_m2=area(outside),accepted_other_owner_polygons_xz_m=excluded,accepted_other_owner_area_m2=area(excluded),max_grade=max((r['gradient']for r in profiles),default=0)))
 report=dict(schema='riverstone.r18.exact_frontage_profiles.v1',source_mesh=dict(path=str(mesh_path.relative_to(a.ROOT)),sha256=a.sha(mesh_path)),request_source=dict(path=str(request_path.relative_to(a.ROOT)),sha256=a.sha(request_path)),ownership_input=dict(path=str(mask_path.relative_to(a.ROOT)),sha256=a.sha(mask_path)),source_refs=mesh['source_refs'],entries=rows,summary=dict(total=len(rows),ready=sum(r['status']=='READY_EXACT_R18_PROFILE_PORTIONS'for r in rows),held=sum(r['status']=='HELD_LOCAL_GRADIENT_OR_COVERAGE'for r in rows),retained_or_other=sum(r['status']=='RETAINED_OR_SEALED_OWNER_HANDOFF_REQUIRED'for r in rows),seconds=time.monotonic()-start),scope='Exact candidate profile portions only. Outside R18 and accepted other-owner parts remain explicit. No ownership activation or controller claim.')
 (HERE/'frontage_profiles_r01.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print(report['summary'],flush=True)
if __name__=='__main__':main()
