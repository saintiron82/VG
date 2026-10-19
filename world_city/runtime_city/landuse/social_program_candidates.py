#!/usr/bin/env python3
"""Bounded social-program proposals; exact XZ quantities, no final style/terrain."""
import json
from collections import defaultdict
from pathlib import Path
from author import ROOT,HERE,FILES,Constraints,rect,g,area,center,clean,digest

def main():
 overlay=json.loads((HERE/'candidate_overlay.json').read_text())
 plan=json.loads((ROOT/FILES['brief']).read_text());scene=json.loads((ROOT/FILES['scene']).read_text())
 context=Constraints(json.loads((HERE/'source_constraints.json').read_text()))
 candidates=[
  {'id':'LU_R3_SOCIAL_NOBLE_QUARTER_CANDIDATE','social_class':'landed_nobility_and_household_service',
   'polygon_xz_m':[[-310,-510],[80,-525],[170,-450],[140,-332],[-80,-332],[-270,-390]],
   'program':['contiguous_quarter_of_multiple_enclosed_estates','main_halls_and_private_gardens','stables_kitchens_servant_lodges','shared_public_approach_streets','separate_household_gates'],
   'parts_target_not_geometry':{'major_holdings':[6,10],'main_hall_per_holding':1,'service_buildings_per_holding':[2,5]},
   'revision_need':'Reclassify connected northern productive-backland and selected source service plots; existing roads stay public; source orchards become productive estate grounds rather than a uniform park.'},
  {'id':'LU_R3_MILITARY_TRAINING_GROUND_CANDIDATE','social_class':'military_and_city_watch',
   'polygon_xz_m':[[540,-90],[615,-70],[620,70],[585,110],[530,80]],
   'program':['large_clear_drill_ground','archery_targets_with_safe_backstop','repair_and_equipment_sheds','cart_and_watch_access','wall_patrol_connection'],
   'revision_need':'Select and terrace one contiguous clear training court inside this envelope; do not paint disconnected residual scraps as an already built field.'},
  {'id':'LU_R3_FREIGHT_MARKET_CANDIDATE','social_class':'merchant_carriers_and_wage_laborers',
   'polygon_xz_m':[[290,215],[390,215],[405,285],[315,305],[280,270]],
   'program':['grain_and_timber_bulk_exchange','cart_turning_and_unloading','weighing_shed','porter_hiring_edge','service_link_to_port_and_craft_roads'],
   'revision_need':'Source-constrained macro envelope; exact operative court must exclude reserved frontages and retain all public road entries.'},
  {'id':'LU_R3_D07_TERRACED_PARK_CANDIDATE','social_class':'shared_neighborhood_space',
   'polygon_xz_m':rect(-184,-285,-158,-266),
   'program':['small_planted_terraced_court','retaining_edge','steps_plus_accessible_route','three_rear_house_connections'],
   'associated_source_buildings':['D07-B118','D07-B119','D07-B120'],
   'proposed_level_y_m':7.8,
   'revision_need':'Terrain owner is reviewing cut/fill and stairs; sourceplotP0288 overlaps2.244m². Current exact H ranges4.949675–8.512925m.'},
 ]
 for rec in candidates:
  poly=clean(g.convex_intersection(rec['polygon_xz_m'],plan['wall_outline_xz_m']))
  rec['polygon_xz_m']=poly;rec['gross_area_m2']=area(poly)
  clipped=[q for p in overlay['patches'] for fragment in p['polygons_xz_m'] if (q:=clean(g.convex_intersection(fragment,poly)))]
  rec['residual_polygons_xz_m']=clipped;rec['newly_assignable_residual_area_m2']=sum(area(q) for q in clipped)
  rec['already_assigned_source_area_m2']=rec['gross_area_m2']-rec['newly_assignable_residual_area_m2']
  rec['overlapping_source_building_ids']=[b['id'] for b in scene['instances'] if g.positive_area_overlap(poly,b['source_footprint_xz_m'])]
  rec['source_assignment_intersections']=[{'source_id':r['id'],'category':r['category'],'area_m2':g.intersection_area(poly,r['polygon'])} for r in context.hits(poly)]
  rec['status']='inferred_macro_candidate_pending_concept_v3_not_integrated'
  rec['observed_vs_inferred']={'observed':'v2 concept shows visible social clusters, enclosed gardens, working yards and small layered parks',
   'latest_user_program':'large noble quarter, separate livelihood classes, large functional training/logistics grounds and connected water system',
   'inferred':'these exact boundaries, areas, counts and levels are authored proposals constrained by source geometry; not image measurements'}
 areas=defaultdict(float)
 for p in overlay['patches']:areas[p['role']]+=p['area_m2']
 out={'schema':'riverstone.city.social_program_candidates.v1','status':'pending_v3_concept_and_parent_integration',
      'pre_v3_exact_residual_function_areas_m2':dict(sorted(areas.items())),
      'candidates':candidates,
      'water_coordination':'No canals/reservoir placed here. Terrain/water worker must supply exact polygons and cut/fill constraints for explicit priority reconciliation.',
      'source_overlay_sha256':digest(HERE/'candidate_overlay.json')}
 (HERE/'social_program_candidates.json').write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 print(json.dumps([{k:c[k] for k in ('id','gross_area_m2','newly_assignable_residual_area_m2','already_assigned_source_area_m2')} for c in candidates]))
if __name__=='__main__':main()
