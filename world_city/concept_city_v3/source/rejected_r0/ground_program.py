"""Explicit finite ground polygons and honest union-area ledger for clean v3."""
import math
from collections import Counter,defaultdict
from world_city.runtime_city.checks import placement as g

def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def clean(p):
 out=[]
 for v in p:
  if not out or math.dist(v,out[-1])>1e-7:out.append(v)
 if len(out)>1 and math.dist(out[0],out[-1])<1e-7:out.pop()
 return out if len(out)>=3 and g.polygon_area(out)>1e-7 else []
def subtract(p,obs):
 pieces=[p]
 for ob in obs:
  pieces=[q for old in pieces for part in (g.convex_difference(old,ob) if g.positive_area_overlap(old,ob) else [old]) if (q:=clean(part))]
  if not pieces:break
 return pieces

def add_ground_program(plan):
 records=[];index=g._SpatialIndex(48)
 def add(kind,identity,p):
  if p:index.add(len(records),p);records.append({'kind':kind,'id':identity,'polygon':p})
 for p in plan['plots']:add('parcel',p['id'],p['polygon_xz_m'])
 for p in plan['spaces']:add('named_site',p['id'],p['polygon_xz_m'])
 for r in plan['roads']:
  for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):add('public_road',r['id']+f':{i}',g.road_ribbon(a,b,r['width_m']))
 for path in plan['paths']:
  for i,(a,b) in enumerate(zip(path['polyline_xz_m'],path['polyline_xz_m'][1:])):
   if math.dist(a,b)>1e-6:add('access_path',path['id']+f':{i}',g.road_ribbon(a,b,path['width_m']))
 for b in plan['buildings']:add('building',b['id'],b['footprint_xz_m'])
 water=plan['water_reservations']
 for i,(a,b) in enumerate(zip(water['service_canal_polyline_xz_m'],water['service_canal_polyline_xz_m'][1:])):add('service_water',str(i),g.road_ribbon(a,b,water['service_corridor_width_m']))
 add('river','river',water['river_polygon_xz_m']);add('reservoir','reservoir',water['reservoir_outer_polygon_xz_m'])
 program={
 'castle':('castle_approach_ramp_repair_and_supply_grounds','earth',['retaining_edge','repair_stock','military_service_path']),
 'water_gardens':('productive_orchard_and_gardener_holding','grass',['fruit_rows','vegetable_beds','field_edge_lanes']),
 'cathedral':('clergy_service_cemetery_and_kitchen_garden','grass',['bounded_burial_rows','herb_beds','clergy_service_lanes']),
 'noble':('estate_private_garden_orchard_and_service_extension','grass',['enclosing_estate_boundary','private_orchard','household_service_court']),
 'merchants':('warehouse_loading_and_stable_service_court','earth',['loading_pads','covered_stock','cart_bays']),
 'civic':('market_edge_trade_and_civic_service_court','stone',['organized_stall_rows','civic_walkway','cart_hold']),
 'monastery':('monastic_food_garden_orchard_and_charitable_service','grass',['kitchen_beds','orchard','hospital_service_court']),
 'old_town':('shared_residential_work_and_washing_court','earth',['washing_trough','repair_bench','small_household_fuel_store']),
 'poor':('communal_labor_workcourt_and_drying_ground','earth',['shared_well','washing_and_drying_frames','fuel_bays']),
 'craft':('workshop_stock_drying_and_fire_separation_yard','earth',['timber_stock','tanning_drying_frames','fire_clearance']),
 'port':('goods_unloading_cart_turning_and_quay_service','stone',['bulk_goods_bays','crane_service','porter_stand','mooring_access'])}
 grounds=[];district_areas={};total=0.
 for district in plan['districts']:
  dp=district['polygon_xz_m'];xs,zs=zip(*dp);groups={};residual=0.
  # 48 m planning blocks provide individually bounded working grounds. These
  # source tiles do not turn into buildings/trees or a fine terrain voxel fill.
  for ix in range(math.floor(min(xs)/48),math.ceil(max(xs)/48)):
   for iz in range(math.floor(min(zs)/48),math.ceil(max(zs)/48)):
    tile=clean(g.convex_intersection(dp,rect(ix*48,iz*48,(ix+1)*48,(iz+1)*48)))
    if not tile:continue
    pieces=subtract(tile,[records[i]['polygon'] for i in index.candidates(tile)])
    if not pieces:continue
    identity=f'GROUND_{district["id"]}_{ix:+03d}_{iz:+03d}'
    role,mat,parts=program[district['role']]
    point=[sum(p[0] for p in pieces[0])/len(pieces[0]),sum(p[1] for p in pieces[0])/len(pieces[0])]
    nearby=sorted(plan['plots'],key=lambda p:math.dist(point,p['origin_xz_m']))[:2]
    amount=sum(g.polygon_area(p) for p in pieces);residual+=amount
    grounds.append({'id':identity,'district_id':district['id'],'role':role,'polygons_xz_m':pieces,'area_m2':amount,
     'material':mat,'facility_intent':parts,'associated_plot_ids':[p['id'] for p in nearby],
     'status':'explicit_source_ground_program; facility_geometry_not_yet_built',
     'surface_ownership':'exact finite polygons only; public roads, source sites, water and all door paths excluded',
     'social_class':district['role'],'observed_vs_inferred':'Function cluster follows concept; exact polygons and facilities are authored, not image measurements.'})
  district_areas[district['id']]={'district_m2':g.polygon_area(dp),'already_assigned_union_m2':g.polygon_area(dp)-residual,'additional_explicit_ground_m2':residual}
  total+=residual
 wall=g.polygon_area(plan['boundary_xz_m']);plan['grounds']=grounds
 plan['residual_ledger']={'wall_interior_area_m2':wall,'plots_named_sites_roads_water_buildings_and_access_union_m2':wall-total,
  'residual_before_ground_program_m2':total,'residual_fraction_before_ground_program':total/wall,
  'additional_exact_ground_polygon_area_m2':sum(p['area_m2'] for p in grounds),'unassigned_area_after_ground_program_m2':0.,
  'districts':district_areas,'meaningful_ground_groups':len(grounds),'convex_source_piece_count':sum(len(p['polygons_xz_m']) for p in grounds),
  'numeric_polygon_drop_tolerance_m2':1e-7,
  'honesty':'The last zero means source-use assignment is complete. It does not claim that gardens, stocks, boundaries, terrain or facilities are compiled or visually complete.'}
 plan['coverage']['policy']='District envelopes are not coverage. See residual_ledger for exact source-assignment union and explicit finite additional grounds.'
 return plan
