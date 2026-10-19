from pathlib import Path
import sys,json,hashlib,math
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));from resolve_pack import *
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
OUT=Path(__file__).resolve().parent;N=OUT.parent/'noble_entry_batch_r02'
p=CITY/'registered_topography/revisions/public_corridors_r18/public_top_r03_native_bound/physical_owners.json';caps=[r for r in load(p)['owners']if r['kind']=='nonwalking_private_cap_remainder'];prof={r['owner_id']:r for r in load(N/'physical_profile_audit.json')['owners']};routes=load(N/'runtime_routes.json')['routes'];rows=[]
for route in routes:
 eid=route['owner_id'];polys=b.ribbon(route['polyline_xz_m'],2)+[[[p[0]+math.cos(k*math.pi/4),p[1]+math.sin(k*math.pi/4)]for k in range(8)]for p in route['polyline_xz_m'][1:-1]];hits=[]
 for cap in caps:
  clipped=[]
  for q in polys:
   pp=fg.clip(q,cap['polygon_xz_m'])
   if fg.area(pp)>1e-10:clipped+=fg.subtract([pp],clipped)
  if not clipped:continue
  candidates=[]
  for fi,f in enumerate(prof[eid]['private_field_pieces']):
   for q in clipped:
    pp=fg.clip(q,f['polygon_xz_m'])
    if fg.area(pp)>1e-10:candidates.append(dict(private_field_index=fi,source_plane_y_xz_m=f['plane_y_xz_m'],polygon_xz_m=pp,maximum_height_delta_m=max(abs(terrain.common.height(f['plane_y_xz_m'],v)-terrain.common.height(cap['plane_y_xz_m'],v))for v in pp)))
  missing=fg.subtract(clipped,[c['polygon_xz_m']for c in candidates]);hits.append(dict(cap=cap,route_intersection_polygons_xz_m=clipped,route_intersection_area_m2=sum(fg.area(q)for q in clipped),candidate_profile_covering_pieces=candidates,candidate_missing_area_m2=sum(fg.area(q)for q in missing)))
 if hits: print(eid,'cap count',len(hits),'area',sum(h['route_intersection_area_m2']for h in hits),'candidate_missing',sum(h['candidate_missing_area_m2']for h in hits),[(h['cap']['id'],h['route_intersection_area_m2'])for h in hits],flush=True)
 rows.append(dict(owner_id=eid,route=route,route_ribbon_polygons_xz_m=polys,cap_contacts=hits))
(OUT/'cap_route_overlap.json').write_text(json.dumps(dict(cap_source=ref(p),profile_source=ref(N/'physical_profile_audit.json'),runtime_route_source=ref(N/'runtime_routes.json'),owners=rows,policy='Read-only full two-metre route versus existing nonwalking caps. private_field_pieces are un-emitted candidate planes, recorded only for repair feasibility, never counted as existing support.'),indent=2)+'\n')
