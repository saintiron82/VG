"""Adopt checked property recipe envelopes/routes for cheap source blockouts."""
import math
from world_city.concept_city_v3.assemblies.property.recipes import build_property_recipe
from world_city.runtime_city.checks import placement as g

def adopt(plan,nearest):
 selected=[p for p in plan['plots'] if p['property_type'] in ('noble_estate','merchant_court','poor_block')]
 ids={p['id'] for p in selected};plan['buildings']=[b for b in plan['buildings'] if b.get('plot_id') not in ids]
 plan['paths']=[p for p in plan['paths'] if p.get('owner_plot_id') not in ids or p['kind']=='property_gate_link']
 recipes=[]
 for plot in selected:
  r=build_property_recipe(plot)
  assert r['checks']['valid'],(plot['id'],r['checks'])
  plot['recipe_metrics']=r['metrics'];plot['surface_ownership']=r['surface_ownership']
  for a in r['placements']:
   if a['source_provider']!='ordinary_r2':continue
   spec=r['cache_specs'][a['asset_key']]['params'];bounds=a['local_bounds'];doors=a['entrances'];ep=doors[0]['door_world_xz_m']
   b={'id':a['id'],'district_id':plot['district_id'],'function':plot['property_type']+'_'+a['role'],'position_xz_m':[a['position_m'][0],a['position_m'][2]],'width_m':bounds['max'][0]-bounds['min'][0],'depth_m':bounds['max'][2]-bounds['min'][2],'height_m':bounds['max'][1]-bounds['min'][1],'yaw_rad':a['yaw_rad'],'entrance_xz_m':ep,'road_id':plot['road_id'],'assembly_intent':'property_recipe_ordinary_r2','plot_id':plot['id'],'source_plot_id':plot['id'],'source_recipe_placement_id':a['id'],'asset_key':a['asset_key'],'floors':spec['floors'],'footprint_xz_m':a['footprint_xz_m'],'social_class':plot['property_type'],'roof_material':a['roof_material_family'],'all_entrances_xz_m':[d['door_world_xz_m'] for d in doors]}
   plan['buildings'].append(b)
  houses={a['id']:a for a in r['placements'] if a['source_provider']=='ordinary_r2'}
  for path in r['entrance_routes']:
   owner=path['owner_id'];line=path['polyline_xz_m']
   if owner in houses:
    door=next(e for e in houses[owner]['entrances'] if e['id']==path['door_id']);line=[door['door_world_xz_m']]+line
   plan['paths'].append({'id':path['id'],'owner_building_id':owner if owner in houses else None,'owner_plot_id':plot['id'],'polyline_xz_m':line,'width_m':path['width_m'],'road_id':plot['road_id'],'kind':'recipe_actual_door_link' if owner in houses else 'recipe_garden_path'})
  for f in r['external_frontage_requirements']:
   ep=f['frontage_point_xz_m'];_,rid,q=nearest(ep,[road for road in plan['roads'] if road['id']==plot['road_id']])[0]
   plan['paths'].append({'id':f['gate_id']+':EXTERNAL','owner_plot_id':plot['id'],'polyline_xz_m':[ep,q],'width_m':f['minimum_link_width_m'],'road_id':rid,'kind':'recipe_external_frontage_link'})
  recipes.append({'plot_id':plot['id'],'checks_valid':True,'metrics':r['metrics'],'cache_asset_keys':sorted(r['cache_specs'])})
 plan['property_recipe_proxy_report']=recipes
 return plan
