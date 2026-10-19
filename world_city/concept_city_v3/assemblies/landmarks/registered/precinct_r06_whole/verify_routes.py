"""Exact native-body and cross-pack polygon tests for every external ground spur."""
from resolve_pack import *
def main():
 pack=load(HERE/'resolved_placements.json');routes=load(HERE/'external_routes.json');source=load(HERE/'actual_native_projection.json');walk=load(HERE/'native_walk_support.json');special={r['id']:r for r in walk['instances']};bodies=[]
 for p in source['instances']:
  polygons=special[p['id']]['walking_body_parts_xz_m']if p['id']in special else p['native_parts_xz_m']
  bodies.extend((p['id'],q,'existing_native')for q in polygons)
 for p in pack['placements']:
  mesh=load(ROOT/p['cache']['path']);bodies.extend((p['id'],b.xform(q,p),'new_native')for q in slab_rectangles(mesh,.01,2.2))
 for p in load(HERE/'preserved_reservations.json')['reservations']:
  if p['kind']in('phase01','phase02','existing_designed_garden','existing_productive_frame'):bodies.extend((p['id'],q,'preserved_reservation')for q in p['polygon_parts_xz_m'])
 waterpath=CITY/'assemblies/waterworks/registered_services_r01/locations.json';water=load(waterpath)
 for p in water['drawhouses']:bodies.append((p['id'],p['footprint_xz_m'],'new_water_fixture'))
 ix=geo._SpatialIndex(16)
 for i,(_,q,_)in enumerate(bodies):ix.add(i,q)
 rows=[]
 for r in routes['routes']:
  hit=[]
  for j,q in enumerate(r['ribbon_polygons_xz_m']):
   for i in ix.candidates(q):
    id,p,kind=bodies[i];area=geo.intersection_area(q,p)
    if area>1e-7:hit.append(dict(ribbon_index=j,body_id=id,kind=kind,overlap_m2=area))
  rows.append({'holding_id':r['holding_id'],'route_id':r['id'],'pass':not hit,'contacts':hit})
 report=dict(sources={'external_routes':ref(HERE/'external_routes.json'),'native_pack':ref(HERE/'resolved_placements.json'),'native_walks':ref(HERE/'native_walk_support.json'),'water_services':ref(waterpath)},routes=rows,summary={'passing':sum(r['pass']for r in rows),'failed':sum(not r['pass']for r in rows),'exact_obstacle_polygons':len(bodies)},method='Full two metre route ribbons including square joins intersect exact native walking-height bodies for retained courtyards, conservative full native projections for other existing assets, all new native bodies, existing finite functional reservations, and new water fixture footprints. Raster screening is never counted as the exact clearance proof.')
 write('route_geometry_tests.json',report);print(report['summary'])
 for r in rows:
  if not r['pass']:print(r['holding_id'],len(r['contacts']),r['contacts'][:3])
if __name__=='__main__':main()
