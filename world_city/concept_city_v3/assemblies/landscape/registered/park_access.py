"""Bounded public-park gate search using the proven finite estate access contract."""
import json,math,time
from . import context as c
from world_city.concept_city_v3.assemblies.property.registered import author as a
from world_city.concept_city_v3.assemblies.property.registered.r1 import access_search as search
from world_city.concept_city_v3.assemblies.property.registered.r1 import author as surface
HERE=c.HERE

def run():
 data=c.load();pack=json.loads((HERE/'generated/source_pack.json').read_text());site=next(s for s in pack['sites'] if s['id']=='PUBLIC_TERRACE_PARK');r=dict(id=site['id'],plot={'polygon_xz_m':site['polygon_xz_m'],'pad_floor_y_m':site['floor']},placements=site['placements'],shared_edge_ownership={});world=search.World(data['plan'],[]);gates=search.gate_candidates(r);cs=[];tested=0;started=time.monotonic()
 for g in gates:
  for segment in world.segments:
   if search.bbox_distance(segment['bounds'],g['center_xz_m'])>130:continue
   tested+=1;candidate,error=search.evaluate(r,g,segment,world)
   if candidate:cs.append(candidate)
 cs.sort(key=lambda q:q['ramp_run_m']+10*q['maximum_cut_fill_m']);chosen=None;attempts=[]
 for q in cs:
  core=a.rect(site['position'],site['width']-3,site['depth']-3,math.radians(site['yaw']));route=a.route_in_parcel(site['position'],q['gate']['inside_point_xz_m'],core,[p['footprint_xz_m'] for p in site['placements']],3)
  if not route:continue
  q['projection_target']=dict(road_id=q['road_id'],road_segment_id=q['road_segment_id'],road_center_connection_xz_m=q['road_center_connection_xz_m'])
  ownership=[]
  for domain in ('owned_ramp_polygon_xz_m','road_landing_polygon_xz_m'):
   for key in world.road_index.candidates(q[domain]):
    road=world.roads[key];pieces=[a.geom.convex_intersection(t,road['polygon']) for t in a.triangulate(q[domain])];pieces=[p for p in pieces if a.geom.polygon_area(p)>1e-7]
    if pieces:ownership.append(dict(source_domain=domain,road_id=road['road_id'],road_segment_id=key,polygons_xz_m=pieces,area_m2=sum(a.geom.polygon_area(p) for p in pieces)))
  terminal_owners=[o for o in ownership if o['source_domain']=='road_landing_polygon_xz_m'];assert terminal_owners
  main_owner=max(terminal_owners,key=lambda o:o['area_m2']);q['road_id']=main_owner['road_id'];q['road_segment_id']=main_owner['road_segment_id'];q['source_road_landing_override']['road_id']=q['road_id'];q['public_surface_override_regions']=ownership
  top=surface.make_surface_record(r,q);top['public_surface_override_regions']=ownership;top['public_lane_endpoint']['projection_target_provenance']=q['projection_target'];top['public_interface_review']='Terminal landing plus every finite ramp/public-ribbon overlap is explicitly owned. Adjacent public-side height transitions remain pending terrain interface review.'
  if top['maximum_service_ramp_grade']>.1 or top['maximum_inherited_public_landing_grade']>.12:continue
  chosen=dict(candidate=q,external_surface=top,internal_gate_branch_xz_m=route+[q['gate']['center_xz_m']]);break
 report=dict(schema='riverstone.registered_public_park_access_candidate.v1',source_bindings=data['sources'],source_park_polygon_sha256=a.sha(site['polygon_xz_m']),gate_positions_tested=len(gates),gate_road_pairs_tested=tested,clear_external_candidates=len(cs),selected=chosen,status='bounded_complete_candidate_pending_terrain_and_traversal' if chosen else 'no_complete_contained_candidate',elapsed_s=round(time.monotonic()-started,3))
 (HERE/'park_access_candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],pairs=tested,candidates=len(cs),elapsed_s=report['elapsed_s'],run_m=chosen['candidate']['ramp_run_m'] if chosen else None)),flush=True);return report
if __name__=='__main__':run()
