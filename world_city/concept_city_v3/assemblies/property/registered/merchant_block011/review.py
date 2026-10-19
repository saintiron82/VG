"""Exact native static-clearance regression, including all full-width corner joins."""
import json,math
from pathlib import Path
from .grammar import HERE,ROOT,PLAN,ORDINARY,ref,write,g,estate
from world_city.concept_city_v3.registered_source.author import Domain
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import closest

def run():
 p=json.loads((HERE/'resolved_placements.json').read_text());source=json.loads((HERE/'proposal.json').read_text());plan=json.loads(PLAN.read_text());old=json.loads(ORDINARY.read_text());issues=[]
 assert p['proposal']==ref(HERE/'proposal.json');assert source['sources']['plan']==ref(PLAN);assert source['sources']['ordinary']==ref(ORDINARY)
 water=Domain([r['polygon_xz_m'] for r in plan['water_reservations']['finite_water_polygons']]);native=Domain();fixed=Domain();roads={r['id']:r for r in plan['roads']};road_domain=Domain()
 for r in plan['roads']:
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):road_domain.add(g.road_ribbon(a,b,r['width_m']),r['id'])
 for q in p['native_walking_slabs']:native.add(q['polygon_xz_m'],q['id'])
 for q in old['placements']:
  if q['id'] not in p['replaced_placement_ids']:fixed.add(q['actual_outer_footprint_xz_m'],q['id'])
 def check(poly,identity,kind,check_native=True):
  for target,domain in [('water',water),('native_walking_slab',native),('retained_native_envelope',fixed)]:
   if target=='native_walking_slab' and not check_native:continue
   for q in estate.triangulate(poly):
    for i in domain.index.candidates(q):
     area=g.polygon_area(g.convex_intersection(q,domain.polys[i]))
     if area>1e-6:issues.append(dict(kind=kind+'_'+target,id=identity,other_id=domain.ids[i],area_m2=area))
 joins=0;ribbons=0
 for route in p['access_proposals']:
  for q in route['ribbon_polygons_xz_m']:check(q,route['id'],'ribbon');ribbons+=1
  for q in route['round_join_polygons_xz_m']:check(q,route['id'],'round_join');joins+=1
  prop=next(x for x in source['properties'] if x['id']==route['property_id'])
  assert math.dist(route['polyline_xz_m'][-1],prop['gate_position_xz_m'])<1e-7
  assert route['finished_floor_y_m']==prop['floor_y_m']
 for route in p['external_gate_links']:
  check(route['ribbon_polygon_xz_m'],route['id'],'public_link');assert closest(route['polyline_xz_m'][-1],roads[route['road_id']]['polyline_xz_m'])[0]<1e-7
 for court in p['courts']:check(court['polygon_xz_m'],court['id'],'service_court')
 for mask in p['ownership_masks']:
  for q in mask['terrain_exclusion_regions_xz_m']:
   check(q,mask['owner_id'],'foundation',False)
   if road_domain.hits(q):issues.append(dict(kind='foundation_public_road_overlap',id=mask['owner_id']))
 for prop in source['properties']:
  if road_domain.hits(prop['polygon_xz_m']):issues.append(dict(kind='platform_public_road_overlap',id=prop['id']))
  if water.hits(prop['polygon_xz_m']):issues.append(dict(kind='platform_water_overlap',id=prop['id']))
 for d in p['actual_doors']:
  assert d['actual_union_threshold_evidence'];owner=next(q for q in p['placements'] if q['id']==d['actual_runtime_group_id']);assert abs(d['actual_door_xyz_m'][1]-owner['pad_floor_y_m'])<1e-8
  # Stub starts at a closed native leaf. Its physical leaf width is recorded;
  # only the external lip onward receives the full-width walking-ribbon claim.
  assert d['threshold_lip_xz_m']==next(r for r in p['access_proposals'] if r['actual_door_id']==d['id'])['polyline_xz_m'][0]
 result=dict(schema='riverstone.merchant_native_static_review.v1',pack=ref(HERE/'resolved_placements.json'),reviewer=ref(Path(__file__)),status='pass_native_full_width_static_clearance' if not issues else 'failed',counts=dict(actual_thresholds=len(p['actual_doors']),routes=len(p['access_proposals']),ribbons=ribbons,rounded_joins=joins,external_gate_links=len(p['external_gate_links']),native_walking_slabs=len(p['native_walking_slabs']),foundation_regions=p['summary']['foundation_regions'],service_courts=len(p['courts'])),issues=issues,limits=['Horizontal native slabs and declared full-width routes only; no finished floor support or capsule/controller validation.','Exact native closed-leaf thresholds are interaction anchors, not certified interior portals.','Raised platform and retaining ownership require the separately bound terrain handoff.'])
 write(HERE/'native_review.json',result);print(json.dumps(dict(status=result['status'],counts=result['counts'],issue_count=len(issues),issues=issues[:20]),indent=2));return result
if __name__=='__main__':raise SystemExit(bool(run()['issues']))
