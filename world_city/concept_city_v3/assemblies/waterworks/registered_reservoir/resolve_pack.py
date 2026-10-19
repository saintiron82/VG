"""Source-bound finite reservoir integration pack; no scene export."""
import json,math,itertools
from author_reservoir import *
from author_interfaces import CISTERN_ORIGIN
from world_city.concept_city_v3.review_geometry import clean,DomainCut

def top_faces(cache,y):
 for group in cache['groups']:
  for q in group['quads']:
   u=[q[1][j]-q[0][j] for j in range(3)];v=[q[2][j]-q[0][j] for j in range(3)];ny=u[2]*v[0]-u[0]*v[2]
   if ny>0 and all(abs(p[1]-y)<1e-7 for p in q):yield [[p[0],p[2]] for p in q]

def transform_poly(poly,pos,yaw):
 return [[q[0],q[2]] for x,z in poly if (q:=pose([x,0,z],pos,yaw))]

def mouth(surface):
 s=next(x for x in DATA['water_surfaces'] if x['id']==surface);a,b=s['polyline_xz_m'][:2];lo,hi=0,1;start=geo.point_in_convex_polygon(a,BASIN['polygon_xz_m'],0)
 for _ in range(60):
  t=(lo+hi)/2;q=[a[j]+t*(b[j]-a[j]) for j in (0,1)]
  if geo.point_in_convex_polygon(q,BASIN['polygon_xz_m'],0)==start:lo=t
  else:hi=t
 q=[a[j]+(lo+hi)/2*(b[j]-a[j]) for j in (0,1)];u=[(b[j]-a[j])/math.dist(a,b) for j in (0,1)];return q,u

def main():
 rows=json.loads((HERE/'compile_report.json').read_text())['requests']+json.loads((HERE/'interface_compile_report.json').read_text())['requests'];rows=[r for r in rows if r['id']!='registered_reservoir_basin_perimeter'];placements=[];assets=[];floors=[];bedfaces=[];requests=[]
 outlet,axis=mouth('NORTHERN_CHANNEL_VISIBLE');spring=next(w for w in DATA['water_surfaces'] if w['id']=='SPRING_VISIBLE');a,b=spring['polyline_xz_m'][:2];u=[(b[j]-a[j])/math.dist(a,b) for j in (0,1)];slope=-1/math.dist(a,b);cosa=1/math.sqrt(1+slope*slope);intakepos=[a[0]+2*cosa*u[0],24+2*cosa*slope,a[1]+2*cosa*u[1]]
 specs={'registered_reservoir_basin_bed':('RESERVOIR_BED',ORIGIN,0),'registered_reservoir_basin_perimeter_supply_opening_r02':('RESERVOIR_BANKS',ORIGIN,0),'registered_reservoir_covered_cistern_drawpoint':('RESERVOIR_DRAWPOINT',CISTERN_ORIGIN,0),'registered_reservoir_protected_bank_conduit':('RESERVOIR_PROTECTED_CONDUIT',[-36,15,-341.0167708839214],0),'registered_reservoir_overflow_sluice':('RESERVOIR_OVERFLOW_SLUICE',[outlet[0],16,outlet[1]],math.degrees(math.atan2(axis[0],axis[1]))),'registered_reservoir_graded_spring_intake':('RESERVOIR_SPRING_INTAKE',intakepos,math.degrees(math.atan2(u[0],u[1])))}
 for row in rows:
  id,pos,yaw=specs[row['id']];s=json.loads((ROOT/row['source']['path']).read_text());r=json.loads((ROOT/row['cache']['path']).read_text());assert ref(ROOT/row['source']['path'])==row['source'];assert ref(ROOT/row['cache']['path'])==row['cache'];asset={k:row[k] for k in ['id','source','cache','master_hash','pitch_m','candidate_cells','output_cells','quad_count']};assets.append(asset);b=r['bounds'];poly=transform_poly([[b['min'][0],b['min'][2]],[b['max'][0],b['min'][2]],[b['max'][0],b['max'][2]],[b['min'][0],b['max'][2]]],pos,yaw)
  p={'id':id,'asset_key':row['id'],'source_id':row['id'],'source':row['source'],'cache':row['cache'],'master_hash':row['master_hash'],'position_m':pos,'position_xyz_m':pos,'yaw_degrees':yaw,'yaw_rad':math.radians(yaw),'scale':[1,1,1],'scale_xyz':[1,1,1],'actual_cached_bounds_local_m':b,'outer_footprint_xz_m':poly,'world_y_range_m':[pos[1]+b['min'][1],pos[1]+b['max'][1]],'network_role':s['extensions']['network_role']};placements.append(p)
  if id=='RESERVOIR_DRAWPOINT':
   for i,q in enumerate(top_faces(r,0)):
    poly=transform_poly(q,pos,yaw);floors.append({'id':id+':floor:'+str(i),'placement_id':id,'polygon_xz_m':poly,'floor_y_m':18,'support_bottom_y_m':13.2,'footprint_basis':'Actual upward native quad at finished platform datum; holes and road cuts omitted.','priority':'Existing travel lane first; finite supported dry floor may replace unoccupied shoulder.'})
  if id=='RESERVOIR_BED':
   for i,q in enumerate(top_faces(r,-2.4)):
    poly=clean(geo.convex_intersection(transform_poly(q,pos,yaw),BASIN['polygon_xz_m']))
    if poly:bedfaces.append({'id':id+':bed:'+str(i),'polygon_xz_m':poly,'top_y_m':13.6,'bottom_y_m':13.2})
  if id in ('RESERVOIR_PROTECTED_CONDUIT','RESERVOIR_DRAWPOINT'):
   requests.append({'id':id+':finite_excavation','placement_id':id,'polygon_xz_m':poly if id=='RESERVOIR_PROTECTED_CONDUIT' else transform_poly([[-4,-4],[10.4,-4],[10.4,6],[-4,6]],pos,0),'bottom_y_m':p['world_y_range_m'][0],'top_y_m':18,'policy':'Reserve native hollow tank/conduit void and retain its opaque shell. Remove soil only within this finite footprint, except source road keepouts; do not alter water heads.','exclude_road_keepouts_xz_m':s['extensions'].get('native_road_keepouts_xz_m',[])})
 wet=water.finite_water_polygons();road=next(r for r in DATA['roads'] if r['id']=='RESERVOIR_SERVICE');ribbons=[geo.road_ribbon(a,b,road['width_m']) for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])];wetarea=roadarea=0
 for f in floors:
  wetarea+=sum(geo.intersection_area(f['polygon_xz_m'],w['polygon_xz_m']) for w in wet);roadarea+=sum(geo.intersection_area(f['polygon_xz_m'],q) for q in ribbons)
 assert wetarea<1e-7 and roadarea<1e-7,(wetarea,roadarea)
 banks=[{'contract_index':i,'record':v} for i,v in enumerate(DATA['water_support']['exterior_banks']) if v['surface_id']=='NORTHERN_RESERVOIR'];links=[{'id':'RESERVOIR_DRAWPOINT_SERVICE','network':'pedestrian_service','width_m':1.4,'points_xyz_m':[[road['polyline_xz_m'][-1][0],18,road['polyline_xz_m'][-1][1]],[-31,18,-331.7],[-33.2,18,-333.7],[-34.2,18,-335.7167708839214]],'public_target_id':'RESERVOIR_SERVICE','status':'proposed; native apron checked separately, short terrain handoff and capsule route need validation'}]
 pack={'schema':'riverstone.city.registered_common_reservoir_placements.v1','status':'compiled_resolved_candidate_pending_terrain_access_integration','source_plan':ref(ROOT/'world_city/concept_city_v3/registered_source/plan.json'),'water_contract':ref(CONTRACT),'author':ref(Path(__file__)),'assets':assets,'placements':placements,'owned_floors':floors,'native_bed_masks':bedfaces,'superseded_reservoir_bank_faces':banks,'terrain_excavation_requests':requests,'access_links':links,'water_graph_unchanged':True,'physical_node_bindings':[{'logical_id':'COVERED_CISTERN','logical_xz_m':[-30.050779741957584,-365.97947492968893],'physical_center_xyz_m':CISTERN_ORIGIN,'physical_water_head_y_m':15.5,'role':'Separate dry-bank covered storage and bucket drawpoint connected to reservoir through an actual open bore.'}],'checks':{'hashes_verified':True,'native_dry_floor_water_overlap_m2':wetarea,'native_dry_floor_traffic_overlap_m2':roadarea,'bank_records_replaced':len(banks)},'completion_claims':{'source_present':True,'compiled_cache':True,'resolved_placement':True,'actual_scene_loaded':False,'actual_visual_review':False,'flow_or_potable_certified':False},'missing':['Short terrain-owned entrance handoff across native road keepout needs height and capsule validation.','Service access along the full feeder and to the sluice, plus finite inlet/outlet service crossings, remain unresolved.','Inlet settling baffles and cleaning/drain-down access are missing.','Covered cistern fluid surface is reserved but not integrated into the water renderer.','Protected distribution routes to cathedral, market and monastery drawpoints remain source graph only.','Gate and windlass hooks have no runtime mechanism.','Hydraulic capacity, source yield, flood/backwater and water quality are unverified.']};write(HERE/'resolved_placements.json',pack);print(json.dumps({'pack':ref(HERE/'resolved_placements.json'),'placements':len(placements),'assets':len(assets),'dry_floor_pieces':len(floors),'native_bed_pieces':len(bedfaces),'dry_floor_area_m2':sum(geo.polygon_area(f['polygon_xz_m']) for f in floors),'checks':pack['checks']},indent=2))
if __name__=='__main__':main()
