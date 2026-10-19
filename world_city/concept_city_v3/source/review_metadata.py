"""Measured block densities, semantic landmark components, landscape reservations."""
import json,math
from pathlib import Path
from collections import defaultdict
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.source.block_geometry import inside,triangulate
from world_city.concept_city_v3.source.ground_program import subtract
HERE=Path(__file__).parent

def enrich(plan):
 targets={'poor':[.40,.55],'craft':[.40,.55],'merchants':[.35,.50],'civic':[.35,.50],'old_town':[.30,.45],'water_gardens':[.30,.45]}
 sums=defaultdict(lambda:[0.,0.,0])
 for bl in plan['blocks']:
  houses=[b for b in plan['buildings'] if inside(b['position_xz_m'],bl['polygon_xz_m']) and not b.get('replace_by_assembly_key') and not b.get('plot_id','').startswith('P_NOBLE')]
  roof=sum(g.polygon_area(b['footprint_xz_m']) for b in houses);den=bl['buildable_area_m2'];role=bl['role'];target=targets.get(role)
  bl['density_metrics']={'actual_roof_envelope_area_m2':roof,'net_block_ground_before_internal_lanes_m2':den,'actual_building_count':len(houses),'roof_coverage_fraction':roof/den,'design_target_range':target,'target_status':'below_target_review_required' if target and roof/den<target[0] else 'above_target_review_required' if target and roof/den>target[1] else 'within_target' if target else 'institutional_or_productive_ground_no_housing_target','denominator_note':'Exact street-enclosed buildable ground excludes named precincts, estate parcels, public streets and water; internal bent alley area remains included. A block crossing district boundaries is reported with its planning role, not falsely claimed to be uniformly residential.'}
  sums[role][0]+=den;sums[role][1]+=roof;sums[role][2]+=len(houses)
 plan['block_density_summary']={r:{'net_ground_m2':a,'actual_roof_m2':b,'coverage_fraction':b/a,'building_count':n,'design_target_range':targets.get(r)} for r,(a,b,n) in sums.items()}
 p=HERE.parent/'assemblies/landmarks/proxy_masses.json'
 if p.exists():
  data=json.loads(p.read_text());plan['landmark_components']=data['groups']
  for group in plan['landmark_components']:
   gid=group['id'];families={'castle':['castle'],'cathedral':['cathedral'],'monastery':['monastery'],'civic_grain':['town_hall','grain_hall']}.get(gid,[])
   ids=[b['id'] for b in plan['buildings'] if b.get('replace_by_assembly_key') in families]
   if gid.startswith('port_cluster_'):
    anchor=group['world_anchor_xyz_m'][0]
    ids=[b['id'] for b in plan['buildings'] if b.get('replace_by_assembly_key')=='warehouse' and min([-180,0,180],key=lambda x:abs(x-b['position_xz_m'][0]))==anchor]
   group['replaces_source_building_ids']=sorted(set(group['replaces_source_building_ids']+ids))
   group['internal_component_overlap_policy']='intentional_union_inside_one_assembly; components are not independent buildings'
   for b in plan['buildings']:
    if b['id'] in group['replaces_source_building_ids']:b['visible_proxy']=False;b['superseded_by_component_group_id']=gid
  plan['landmark_component_suppressed_building_ids']=sorted({bid for group in plan['landmark_components'] for bid in group['replaces_source_building_ids']})
  plan['landmark_component_contract']={'source':str(p.relative_to(HERE.parents[3])),'coordinate_contract':data['coordinate_contract'],'render_policy':'Suppress each replaces_source_building_ids envelope from visible massing and draw its semantic component boxes. Keep source envelope records for reservations and door connectivity only. Internal component overlap is an intentional single assembly union, not separate building overlap. No whole-group box is rendered.','not_independent_buildings':True,'entrance_owner':'retained source envelope or resolved assembly connector'}
 # Named, bounded landscape design reservations, deliberately separate from
 # unassigned block ground; these are the source parcels the landscape provider
 # may populate after visual approval, with every hard blocker subtracted.
 def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
 exclusions=[b['footprint_xz_m'] for b in plan['buildings']]
 exclusions.extend(g.road_ribbon(a,b,r['width_m']+2) for r in plan['roads'] for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]) if math.dist(a,b)>1e-6)
 exclusions.extend(g.road_ribbon(a,b,p['width_m']+.5) for p in plan['paths'] for a,b in zip(p['polyline_xz_m'],p['polyline_xz_m'][1:]) if math.dist(a,b)>1e-6)
 water=plan['water_reservations'];exclusions.extend(g.road_ribbon(a,b,16) for a,b in zip(water['service_canal_polyline_xz_m'],water['service_canal_polyline_xz_m'][1:]));exclusions.append(water['reservoir_outer_polygon_xz_m'])
 specs=[('LAND_PUBLIC_COMMON','small_terraced_public_park',rect(-185,10,-140,55),'neighborhood sitting shade and pedestrian steps'),('LAND_MONASTERY_WEST','monastery_food_garden',rect(-445,88,-395,230),'enclosed food beds and charitable kitchen supply'),('LAND_MONASTERY_SOUTH','monastery_productive_orchard',rect(-385,230,-205,265),'orchard and herb garden above service canal'),('LAND_CLERGY_CEMETERY','cathedral_cemetery',rect(160,-350,350,-330),'burial garden immediately north of cathedral close'),('LAND_CLERGY_KITCHEN','clergy_kitchen_garden',rect(360,-300,410,-190),'clergy food beds east of cathedral'),('LAND_NORTH_ORCHARD','productive_orchard',rect(-205,-362,-75,-335),'small gardener holding beside upper water neighborhood'),('LAND_FOREST_NW','outside_natural_woodland',[[-630,-570],[-180,-570],[-205,-390],[-450,-345],[-560,-165],[-630,-220]],'irregular outside woodland with varied species and clear city approaches'),('LAND_FOREST_NE','outside_natural_woodland',[[140,-550],[610,-520],[620,-190],[480,-110],[390,-335],[150,-390]],'irregular outside woodland on northern and eastern slopes')]
 plan['landscape_patches']=[]
 for identity,role,poly,purpose in specs:
  # All authored masks are convex; outside forest is split at the city wall.
  obs=exclusions+([plan['boundary_xz_m']] if role=='outside_natural_woodland' else [])
  if role!='outside_natural_woodland':poly=g.convex_intersection(poly,plan['boundary_xz_m'])
  ix=g._SpatialIndex(48)
  for j,ob in enumerate(obs):ix.add(j,ob)
  pieces=[q for t in triangulate(poly) for q in subtract(t,[obs[j] for j in ix.candidates(t)])]
  plan['landscape_patches'].append({'id':identity,'role':role,'polygons_xz_m':pieces,'area_m2':sum(g.polygon_area(p) for p in pieces),'purpose':purpose,'status':'bounded_source_reservation_for_landscape_recipe; not yet populated','excluded_features':'actual building envelopes, public roads, every entrance path, reservoir and service canal; forest also excludes the walled city','observed_vs_inferred':'Function and broad placement follow concept; exact polygons, planting density and steps are authored.'})
 return plan
