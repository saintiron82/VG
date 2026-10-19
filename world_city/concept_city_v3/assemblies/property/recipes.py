"""Reusable social-property recipes for the clean concept city; no old-city placement.

All geometry is ordinary common-source data. Buildings remain separately cached.
"""
from __future__ import annotations
import copy,json,math
from collections import Counter
from pathlib import Path
from world_city.runtime_city.archetypes import ordinary_r2
from world_city.runtime_city.urban_fabric.revisions.r3.author_overlay import make_master as make_fabric_master,master_bounds as fabric_bounds,route_inside
from world_city.runtime_city.urban_fabric.author import rect,unit,add,digest,yaw_basis
from world_city.runtime_city.checks.placement import positive_area_overlap,convex_polygon_contains,polygon_area,road_ribbon,convex_intersection
from world_city.runtime_city.infrastructure.author import PALETTE
from voxel_character.common import core
HERE=Path(__file__).parent
SCHEMA='riverstone.voxel.master.v1'
FAMILIES={'noble_estate':(66,60),'merchant_court':(36,42),'poor_block':(30,36)}
DEFAULT_SIZES={'noble_estate':(70,62),'merchant_court':(36,42),'poor_block':(30,36)}


def key_for(spec):return 'c3_property_'+spec['provider']+'_'+digest(spec)[:16]
def resource_for(spec):
 """Sampling contract: thin floors/walls need 0.5 m; orchard crowns use 1 m."""
 return {'pitch':1 if spec['provider']=='fabric_r3' and spec['params']['kind']=='forest_tree' else .5}
def world_point(p,origin,yaw):return [origin[0]+math.cos(yaw)*p[0]+math.sin(yaw)*p[1],origin[1]-math.sin(yaw)*p[0]+math.cos(yaw)*p[1]]
def world_polygon(poly,origin,yaw):return [world_point(p,origin,yaw) for p in poly]


def _source(spec):
 p=spec['params'];ops=[];materials=dict(PALETTE)
 def box(lo,hi,mat,label,action='paint'):
  op={'id':label+'_'+str(len(ops)),'part':'solid','action':action,'shape':{'kind':'box','min':lo,'max':hi}}
  if action=='paint':op['material']=mat
  ops.append(op)
 def footprint(poly,ymin,ymax,mat,label,action='paint'):
  op={'id':label+'_'+str(len(ops)),'part':'solid','action':action,'shape':{'kind':'extrusion','polygon':[[v[0],-v[1]] for v in poly],'z_min':ymin,'z_max':ymax},'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}}
  if action=='paint':op['material']=mat
  ops.append(op)
 kind=p['kind'];supports=[]
 if kind=='boundary':
  # Short support spans share one source solid, so coincident internal faces vanish.
  for j,s in enumerate(p['segments']):
   a,b=s['a'],s['b'];w=math.dist(a,b);mid=[(a[0]+b[0])/2,(a[1]+b[1])/2];u=unit(a,b);theta=math.atan2(-u[1],u[0]);h=s['height_m'];t=s['thickness_m'];y=s.get('y_m',0)
   op={'id':'wall_'+str(j),'part':'solid','action':'paint','material':'stone','shape':{'kind':'box','min':[-w/2,-.5,-t/2],'max':[w/2,h,t/2]},'transform':{'translation':[mid[0],y,mid[1]],'basis':yaw_basis(theta)}};ops.append(op)
   supports.append({'id':s['id'],'support_points_local_xz_m':rect(mid,w,t,theta),'maximum_support_height_delta_m':.75,'footing_embed_m':.5,'operation_id':op['id']})
  for j,(x,z) in enumerate(p['corners']):box([x-.5,-.5,z-.5],[x+.5,p['height_m']+.25,z+.5],'stone_light','joined_corner')
  for j,g in enumerate(p['gates']):
   if not g.get('wall_opening',True):continue
   cx,cz=g['center_local_xz_m'];w=g['width_m'];wall_h=p['height_m'];t=p['thickness_m']
   # All gate fronts are local +Z; source cut owns the exact open interval.
   box([cx-w/2,-2,cz-2],[cx+w/2,wall_h+2,cz+2],'stone','gate_clearance','cut')
   for sign in (-1,1):
    px=cx+sign*(w/2+.5);box([px-.5,-.5,cz-.5],[px+.5,wall_h+.75,cz+.5],'stone_light','gate_pier')
  metadata={'source_support_segments':supports,'one_solid_boundary':True,'gate_count':len(p['gates']),'no_cell_or_mesh_repair':True}
 elif kind=='owned_surface':
  w,d=p['width_m'],p['depth_m'];parcel=rect([0,0],w,d)
  box([-w/2,-.5,-d/2],[w/2,0,d/2],p['base_material'],'single_owned_property_floor')
  for i,r in enumerate(p['ground_regions']):footprint(r['polygon_local_xz_m'],-.5,0,r['material'],'land_use_'+str(i))
  for i,r in enumerate(p['routes']):
   for q in r['ribbon_polygons_local_xz_m']:
    clip=convex_intersection(parcel,q)
    if len(clip)>=3 and polygon_area(clip)>.001:footprint(clip,-.5,0,'stone_dark','walk_service_route_'+str(i))
  for i,poly in enumerate(p['foundation_cutouts']):footprint(poly,-1,1,'earth','foundation_owned_cut_'+str(i),'cut')
  metadata={'surface_ownership':'exclusive_property_floor_replace_city_ground_inside_parcel','one_solid_floor':True,'foundation_cutouts':p['foundation_cutouts']}
 elif kind=='communal_well':
  ops.append({'id':'well_ring','part':'solid','action':'paint','material':'stone','shape':{'kind':'annulus','inner_radius':.5,'outer_radius':1,'y_min':0,'y_max':1.25}})
  box([-.5,.25,-.5],[.5,.5,.5],'water','well_water')
  for x in (-1.25,1.25):box([x-.25,0,-.25],[x+.25,3,.25],'timber','well_post')
  box([-1.5,2.5,-.25],[1.5,3,.25],'timber','well_crossbar');metadata={'shared_court_amenity':True}
 else:raise ValueError(kind)
 return {'schema':SCHEMA,'id':key_for(spec),'revision':3,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':materials,'components':[{'id':'module','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'module','component':'module'}],'metadata':metadata}


def make_asset_master(spec):
 """Finite cache dispatch to existing common-source building/fabric generators."""
 if spec['provider']=='ordinary_r2':return ordinary_r2.make_master({**spec['params'],'asset_id':key_for(spec)})
 if spec['provider']=='fabric_r3':
  m=make_fabric_master(spec['params']);m['id']=key_for(spec);return m
 if spec['provider']=='property':return _source(spec)
 raise ValueError('Unknown property source provider')


def describe_asset(spec):
 p=spec['params']
 if spec['provider']=='ordinary_r2':
  m=make_asset_master(spec);return m['metadata']['envelope'],m['metadata']
 if spec['provider']=='fabric_r3':w,d,h=fabric_bounds(p)
 elif p['kind']=='communal_well':w,d,h=3,2,3
 else:w,d,h=p['width_m'],p['depth_m'],p.get('height_m',0)+(.75 if p['kind']=='boundary' else 0)
 return {'min':[-w/2,-1,-d/2],'max':[w/2,h,d/2]},{}


def _boundary_params(w,d,family,gates):
 inset=1 if family=='noble_estate' else .5;x,z=w/2-inset,d/2-inset;thickness=1 if family=='noble_estate' else .5;height=3 if family=='noble_estate' else 1.25 if family=='poor_block' else 2
 ring=[[-x,-z],[x,-z],[x,z],[-x,z]];segments=[]
 for ei,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  if family=='merchant_court' and ei==2:continue # Shop fronts and the central drive form the street edge.
  length=math.dist(a,b);u=unit(a,b);at=0
  while at<length-1e-7:
   stop=min(at+6,length);segments.append({'id':'edge_'+str(ei)+'_span_'+str(len(segments)),'a':add(a,u,at),'b':add(a,u,stop),'height_m':height,'thickness_m':thickness});at=stop
 return {'kind':'boundary','width_m':w,'depth_m':d,'height_m':height,'thickness_m':thickness,'segments':segments,'corners':ring,'gates':[{k:g[k] for k in ('role','center_local_xz_m','width_m','wall_opening')} for g in gates],'closure':'closed_gated_ring' if family!='merchant_court' else 'three_wall_sides_plus_shop_frontages'}


def build_property_recipe(plot):
 """Plot schema agreed with the clean-city land-use author; no old scene input.

 Required: id, property_type, width_m, depth_m. Frame: origin_xz_m/yaw_rad,
 gate_front='+Z', polygon_xz_m and optional gate_position_xz_m/road_id.
 """
 plot=copy.deepcopy(plot);family=plot['property_type']
 if family not in FAMILIES:raise ValueError('Unknown property_type '+str(family))
 w,d=float(plot['width_m']),float(plot['depth_m']);minimum=FAMILIES[family]
 if w<minimum[0] or d<minimum[1]:raise ValueError(f'{family} requires at least {minimum[0]} by {minimum[1]} m')
 if plot.get('gate_front','+Z')!='+Z':raise ValueError('Normalize plot yaw so its reserved street is local +Z')
 origin=plot.get('origin_xz_m',[0,0]);yaw=float(plot.get('yaw_rad',0));pad_y=float(plot.get('pad_y_m',0));suffix=plot['id'].rsplit('_',1)[-1];variant=int(plot.get('variant',int(suffix)-1 if suffix.isdigit() else 0));pid=plot['id'];parcel=rect([0,0],w,d)
 supplied_gate=plot.get('gate_position_xz_m')
 if supplied_gate and math.dist(supplied_gate,world_point([0,d/2],origin,yaw))>.05:raise ValueError('gate_position_xz_m must be the transformed local +Z frontage center; gate-offset support requires an explicit recipe option')
 supplied=plot.get('polygon_xz_m')
 if supplied and not convex_polygon_contains(supplied,world_polygon(parcel,origin,yaw),.01):raise ValueError('Rectangular buildable frame does not fit supplied plot polygon')
 placements=[];cache={};houses=[];props=[];regions=[];routes=[];errors=[];foundation_cutouts=[]
 def place(role,spec,pos=(0,0),theta=0,roof_family=None,collidable=True):
  key=key_for(spec);cache.setdefault(key,spec);bounds,meta=describe_asset(spec);bw,bd=bounds['max'][0]-bounds['min'][0],bounds['max'][2]-bounds['min'][2];poly=rect(pos,bw,bd,theta);wp=world_point(pos,origin,yaw);id=pid+':'+role
  item={'id':id,'role':role,'asset_key':key,'source_provider':spec['provider'],'local_position_m':[pos[0],0,pos[1]],'local_yaw_rad':theta,'position_m':[wp[0],pad_y,wp[1]],'yaw_rad':yaw+theta,'footprint_local_xz_m':poly,'footprint_xz_m':world_polygon(poly,origin,yaw),'local_bounds':bounds,'collision_enabled':collidable,'collision_policy':'walkable_floor' if role=='owned_surface' else 'solid','roof_material_family':roof_family,'ground_anchor':{'policy':'owned_flat_property_pad_or_explicit_short_support_projection','datum_y_m':pad_y,'preserve_xz':True,'support_points_xz_m':world_polygon(rect(pos,2,2,theta) if spec['provider']=='fabric_r3' and spec['params']['kind']=='forest_tree' else poly,origin,yaw),'footing_embed_m':.5,'maximum_support_height_delta_m':.75}}
  placements.append(item)
  if spec['provider']=='ordinary_r2':
   item['assembly_class']=spec['params']['assembly_class'];item['dwelling_units']=meta['row_units'] if meta['assembly_class']=='poor_row' else 1 if role!='stable' and 'warehouse' not in role and 'workshop' not in role else 0;item['entrances']=[]
   front=[math.sin(theta),math.cos(theta)];right=[math.cos(theta),-math.sin(theta)]
   for n,door in enumerate(meta['entrance']['all_positions']):
    actual=add(add(pos,right,door[0]),front,door[2]);threshold=add(add(pos,right,door[0]),front,bounds['max'][2]);item['entrances'].append({'id':id+':door:'+str(n),'door_local_xz_m':actual,'threshold_local_xz_m':threshold,'outward_local_xz':front,'door_world_xz_m':world_point(actual,origin,yaw)})
   body=meta['body_bounds'];foundation_cutouts.append(rect(add(add(pos,right,(body['min'][0]+body['max'][0])/2),front,(body['min'][2]+body['max'][2])/2),body['max'][0]-body['min'][0],body['max'][2]-body['min'][2],theta));houses.append(item)
  elif collidable and role not in ('boundary','owned_surface'):props.append(item)
  return item
 def house(role,kind,bw,bd,pos,theta=0,floors=1,style='old_timber',roof='gable',pitch=38,units=None,roof_family='wood_brown',era='early'):
  p={'assembly_class':kind,'width_m':bw,'depth_m':bd,'floors':floors,'floor_height_m':3.4 if family=='noble_estate' and role=='main_residence' else 2.5 if kind=='poor_row' else 3 if kind in ('merchant_palazzo','timber_courtyard_house') else 2.65 if kind=='stable' else 2.7,'style':style,'roof_form':roof,'roof_pitch_degrees':pitch,'construction_era':era}
  if units:p['attached_units']=units
  return place(role,{'provider':'ordinary_r2','params':p},pos,theta,roof_family)
 def region(name,poly,material,use):regions.append({'id':pid+':'+name,'land_use':use,'polygon_local_xz_m':poly,'polygon_xz_m':world_polygon(poly,origin,yaw),'material':material,'area_m2':polygon_area(poly)})
 inset=1 if family=='noble_estate' else .5;front_z=d/2-inset
 gates=[{'id':pid+':main_gate','role':'main','center_local_xz_m':[0,front_z],'width_m':5 if family=='noble_estate' else 6 if family=='merchant_court' else 4,'wall_opening':family!='merchant_court'}]
 if family=='noble_estate':
  kind=('older_stone_manor','merchant_palazzo','timber_courtyard_house')[variant%3];house('main_residence',kind,26,22,[0,-2],floors=3 if kind=='merchant_palazzo' else 2,style='institutional' if kind=='older_stone_manor' else 'merchant',roof='twin_gable_z' if kind=='timber_courtyard_house' else 'hip',pitch=40 if kind=='older_stone_manor' else 35,roof_family='slate_gray' if kind=='older_stone_manor' else 'clay_red' if kind=='merchant_palazzo' else 'wood_brown',era='early' if kind=='older_stone_manor' else 'rebuilt')
  house('stable','stable',18,8,[-w/2+7,13],math.pi/2,roof='hip',pitch=30,roof_family='wood_brown')
  house('servants','servant_lodge',12,8,[w/2-7,13],-math.pi/2,roof='gable',pitch=35,roof_family='clay_red')
  gx=round((-w*.3)*2)/2;gates.append({'id':pid+':service_gate','role':'service','center_local_xz_m':[gx,front_z],'width_m':3.5,'wall_opening':True})
  rear=-d/2
  region('formal_garden',rect([0,rear+9],32,12),'grass','private_formal_kitchen_garden')
  for sign in (-1,1):region('orchard_'+str(sign),rect([sign*(w/2-10),rear+15],10,24),'grass','private_productive_orchard')
  for x in (-12,-4,4,12):
   for z in (rear+6,rear+12):place('garden_bed_'+str(x)+'_'+str(z),{'provider':'fabric_r3','params':{'kind':'garden_bed','width_m':6,'depth_m':3,'height_m':1.5}},[x,z])
  for sign in (-1,1):
   for j,z in enumerate((rear+6,rear+14,rear+22)):place('orchard_tree_'+str(sign)+'_'+str(j),{'provider':'fabric_r3','params':{'kind':'forest_tree','form':'low_hazel'}},[sign*(w/2-10),z],theta=0)
  region('service_court',rect([0,19],40,18),'stone_dark','private_service_and_arrival_court')
 elif family=='merchant_court':
  for sign in (-1,1):
   x=sign*(w/2-8);house('shop_residence_'+str(sign),'merchant_palazzo',12,8,[x,d/2-5],floors=2,style='merchant',roof='hip',pitch=38,roof_family='clay_red',era='rebuilt');gates.append({'id':pid+':shop_entry_'+str(sign),'role':'street_shop','center_local_xz_m':[x,d/2],'width_m':2,'wall_opening':False})
  house('rear_warehouse','regular_house',24,10,[0,-d/2+7],style='port',roof='hip',pitch=30,roof_family='slate_gray',era='rebuilt')
  for sign in (-1,1):house('side_workshop_'+str(sign),'regular_house',14,6,[sign*(w/2-4),0],-sign*math.pi/2,style='artisan',roof='hip',pitch=30,roof_family='wood_brown',era='rebuilt')
  region('loading_court',rect([0,1],22,20),'stone_dark','merchant_loading_and_trading_court')
 else:
  house('rear_poor_row','poor_row',24,8,[0,-d/2+5.5],floors=2,units=6,roof='gable',pitch=35)
  house('west_poor_row','poor_row',15,7,[-w/2+4.5,2],math.pi/2,floors=2,units=4,roof='gable',pitch=40)
  house('east_poor_row','poor_row',15,6,[w/2-4,2],-math.pi/2,floors=1,units=4,roof='gable',pitch=35)
  for sign in (-1,1):house('front_poor_row_'+str(sign),'poor_row',10,5,[sign*8,d/2-3.5],math.pi,floors=1 if (sign<0) != bool(variant%2) else 2,units=2,roof='gable',pitch=35 if sign<0 else 42)
  place('communal_well',{'provider':'property','params':{'kind':'communal_well'}},[3,2])
  region('shared_court',rect([0,2],12,14),'earth','shared_poor_court_and_well')
 # Every actual modular door gets its own swept approach, connected to an explicit gate.
 obstacles=[p['footprint_local_xz_m'] for p in houses+props];inside=rect([0,0],w-2*inset-2,d-2*inset-2)
 for h in houses:
  for e in h['entrances']:
   width=1.8;threshold=e['threshold_local_xz_m'];front=e['outward_local_xz'];start=add(threshold,front,1.0)
   if family=='merchant_court' and h['role'].startswith('shop_residence'):
    gate=min((g for g in gates if g['role']=='street_shop'),key=lambda g:abs(g['center_local_xz_m'][0]-threshold[0]));path=[threshold,[threshold[0],d/2]]
   else:
    gate=gates[1] if family=='noble_estate' and h['role']=='stable' else gates[0];goal=[gate['center_local_xz_m'][0],front_z-2]
    middle=route_inside(start,goal,inside,obstacles,width)
    if not middle:errors.append({'check':'unroutable_door','door_id':e['id']});continue
    path=[threshold]+middle+[gate['center_local_xz_m'],[gate['center_local_xz_m'][0],d/2]]
   ribbons=[road_ribbon(a,b,width) for a,b in zip(path,path[1:]) if math.dist(a,b)>.001]
   routes.append({'id':e['id']+':route','owner_id':h['id'],'door_id':e['id'],'gate_id':gate['id'],'width_m':width,'polyline_local_xz_m':path,'polyline_xz_m':[world_point(p,origin,yaw) for p in path],'ribbon_polygons_local_xz_m':ribbons,'ribbon_polygons_xz_m':[world_polygon(q,origin,yaw) for q in ribbons],'road_id':plot.get('road_id'),'threshold_bridge_to_actual_door_local_xz_m':[e['door_local_xz_m'],threshold]})
 if family=='noble_estate':
  for sign in (-1,1):
   path=[[0,26],[sign*18,26],[sign*18,-d/2+4]];ribbons=[road_ribbon(a,b,1.8) for a,b in zip(path,path[1:])];routes.append({'id':pid+':garden_walk:'+str(sign),'owner_id':pid,'kind':'garden_service_walk','gate_id':gates[0]['id'],'width_m':1.8,'polyline_local_xz_m':path,'polyline_xz_m':[world_point(p,origin,yaw) for p in path],'ribbon_polygons_local_xz_m':ribbons,'ribbon_polygons_xz_m':[world_polygon(q,origin,yaw) for q in ribbons]})
 boundary=place('boundary',{'provider':'property','params':_boundary_params(w,d,family,gates)})
 surface=place('owned_surface',{'provider':'property','params':{'kind':'owned_surface','width_m':w,'depth_m':d,'height_m':0,'base_material':'grass' if family=='noble_estate' else 'earth','ground_regions':[{k:r[k] for k in ('polygon_local_xz_m','material')} for r in regions],'routes':[{k:r[k] for k in ('ribbon_polygons_local_xz_m',)} for r in routes],'foundation_cutouts':foundation_cutouts}},collidable=True)
 for g in gates:g['position_xz_m']=world_point(g['center_local_xz_m'],origin,yaw);g['public_frontage_point_xz_m']=world_point([g['center_local_xz_m'][0],d/2],origin,yaw)
 result={'schema':'riverstone.concept_city.property_recipe.v3','plot':plot,'property_type':family,'placements':placements,'cache_specs':cache,'gates':gates,'entrance_routes':routes,'ground_regions':regions,'surface_ownership':{'owner_placement_id':surface['id'],'floor_collision_required':True,'polygon_xz_m':world_polygon(parcel,origin,yaw),'exclusive':True,'city_terrain_must_exclude_this_footprint':True,'foundation_cutouts_local_xz_m':foundation_cutouts,'pad_y_m':pad_y,'terrace_policy':'Provide a traversable flat property pad or explicitly project short boundary supports before compiling; no silent slope flattening.'},'boundary_placement_id':boundary['id'],'source_errors':errors,'metrics':{'plot_area_m2':w*d,'building_footprint_m2':sum(polygon_area(h['footprint_local_xz_m']) for h in houses),'building_count':len(houses),'dwelling_units':sum(h['dwelling_units'] for h in houses),'garden_orchard_area_m2':sum(r['area_m2'] for r in regions if 'garden' in r['land_use'] or 'orchard' in r['land_use']),'court_area_m2':sum(r['area_m2'] for r in regions if 'court' in r['land_use']),'cache_roles':dict(Counter(p['source_provider'] for p in placements))},'resolved_variant':variant,'external_frontage_requirements':[{'gate_id':g['id'],'frontage_point_xz_m':g['public_frontage_point_xz_m'],'minimum_link_width_m':3 if g['role']=='main' and family=='noble_estate' else 2.5 if g['role']=='service' else 1.8,'existing_main_gate_connection_xz_m':plot.get('gate_connection_xz_m') if g['role']=='main' else None,'external_connection_owner':'concept_city_v3 land-use street/path plan'} for g in gates],'no_old_city_inputs':True,'reference':'world_city/reference/revision_03/city_social_water_concept.png'}
 result['metrics']['building_coverage_fraction']=result['metrics']['building_footprint_m2']/(w*d);result['checks']=validate_recipe(result);return result


def validate_recipe(recipe):
 errors=list(recipe['source_errors']);w,d=recipe['plot']['width_m'],recipe['plot']['depth_m'];parcel=rect([0,0],w,d);houses=[p for p in recipe['placements'] if p['source_provider']=='ordinary_r2'];solids=[p for p in recipe['placements'] if p['collision_enabled'] and p['role'] not in ('boundary','owned_surface')]
 for p in recipe['placements']:
  bounds,_=describe_asset(recipe['cache_specs'][p['asset_key']]);pos=[p['local_position_m'][0],p['local_position_m'][2]];expected=rect(pos,bounds['max'][0]-bounds['min'][0],bounds['max'][2]-bounds['min'][2],p['local_yaw_rad']);origin=recipe['plot'].get('origin_xz_m',[0,0]);theta=recipe['plot'].get('yaw_rad',0);world_expected=world_point(pos,origin,theta)
  if any(math.dist(a,b)>.00001 for a,b in zip(expected,p['footprint_local_xz_m'])):errors.append({'check':'stale_local_footprint','id':p['id']})
  if math.dist(world_expected,[p['position_m'][0],p['position_m'][2]])>.00001 or abs(p['yaw_rad']-theta-p['local_yaw_rad'])>.00001:errors.append({'check':'stale_plot_frame_pose','id':p['id']})
 ownership=recipe['surface_ownership'];floor=next((p for p in recipe['placements'] if p['id']==ownership.get('owner_placement_id')),None)
 if not ownership.get('exclusive') or not ownership.get('city_terrain_must_exclude_this_footprint') or not ownership.get('floor_collision_required') or not floor or not floor['collision_enabled'] or floor.get('collision_policy')!='walkable_floor':errors.append({'check':'invalid_exclusive_floor_ownership'})
 for p in solids:
  if not convex_polygon_contains(parcel,p['footprint_local_xz_m'],.001):errors.append({'check':'outside_plot','id':p['id']})
 for i,p in enumerate(solids):
  for q in solids[:i]:
   if positive_area_overlap(p['footprint_local_xz_m'],q['footprint_local_xz_m'],.005):errors.append({'check':'solid_overlap','ids':[p['id'],q['id']]})
 for a in recipe['entrance_routes']:
  for poly in a['ribbon_polygons_local_xz_m']:
   for p in solids:
    if positive_area_overlap(poly,p['footprint_local_xz_m'],.005):errors.append({'check':'access_solid_overlap','access':a['id'],'target':p['id']})
 doors={e['id'] for h in houses for e in h['entrances']};routed={a.get('door_id') for a in recipe['entrance_routes']}
 if doors-routed:errors.append({'check':'missing_door_routes','ids':sorted(doors-routed)})
 return {'valid':not errors,'errors':errors,'building_doors':len(doors),'routed_doors':len(doors&routed),'boundary_is_one_common_solid':True,'surface_has_exclusive_owner':True,'scope':'within_plot source checks; external frontage-to-road links remain with land-use integration'}


def example_plot(kind,variant=0):
 w,d=DEFAULT_SIZES[kind];return {'id':'EXAMPLE_'+kind.upper(),'district_id':'NOBLE_NW' if kind=='noble_estate' else 'POOR_SE' if kind=='poor_block' else 'MERCHANT_CORE','property_type':kind,'width_m':w,'depth_m':d,'origin_xz_m':[0,0],'yaw_rad':0,'gate_front':'+Z','gate_position_xz_m':[0,d/2],'road_id':'EXAMPLE_STREET','land_use':kind,'variant':variant}


def main():
 out=HERE/'generated';out.mkdir(exist_ok=True);summary={}
 for kind in FAMILIES:
  r=build_property_recipe(example_plot(kind));(out/(kind+'.recipe.json')).write_text(json.dumps(r,separators=(',',':'))+'\n');summary[kind]={'metrics':r['metrics'],'checks':r['checks'],'placements':len(r['placements']),'unique_cache_assets':len(r['cache_specs'])}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
