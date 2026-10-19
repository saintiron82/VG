"""Concept-only head and environmental proximity screen for six network stations."""
from pathlib import Path
import json,math,hashlib
ROOT=Path(__file__).resolve().parents[5];B=ROOT/'world_city/concept_city_v3';OUT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inside(p,poly):
 x,z=p;hit=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:hit=not hit
 return hit
def seg(p,a,b):
 dx=b[0]-a[0];dz=b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/(dx*dx+dz*dz))) if dx*dx+dz*dz else 0
 q=[a[0]+dx*t,a[1]+dz*t];return math.dist(p,q),q,t
def dist(p,d):
 poly=d['polygon_xz_m']
 if inside(p,poly):return {'distance_m':0,'point_xz_m':p,'surface_id':d['surface_id'],'water_y_range_m':[min(d['vertex_y_m']),max(d['vertex_y_m'])]}
 dd,q,t=min(seg(p,a,b)for a,b in zip(poly,poly[1:]+poly[:1]))
 return {'distance_m':dd,'point_xz_m':q,'surface_id':d['surface_id'],'water_y_range_m':[min(d['vertex_y_m']),max(d['vertex_y_m'])]}
S=B/'evidence/r8_final110_runtime_r01/scene.json';scene=read(S)
P=B/'registered_integration/r10_functional_audit/network/observed_facility_location_candidates.json';sites=read(P)['selected']
master=ROOT/scene['common_assets']['registered_services_closed_cistern']['master_path'];m=read(master)
assert m['extensions']['authored_parameters']['nominal_head_below_platform_m']==2
water=scene['terrain_contract']['water_domain_polygons'];rows=[]
for s in sites:
 x,y,z=s['point_m'];p=[x,z]
 process=min((dist(p,w)for w in water if w['surface_id'] in ['CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE']),key=lambda r:r['distance_m'])
 river=min((dist(p,w)for w in water if w['surface_id']=='MAIN_RIVER'),key=lambda r:r['distance_m'])
 nearest=min((dist(p,w)for w in water),key=lambda r:r['distance_m'])
 rows.append({'rank':s['addition_count'],'station_node':s['node'],'route_id':s['road'],'station_xyz_m':s['point_m'],'status':'NETWORK_STATION_ONLY_NOT_APPROVED_PLACEMENT','cistern_reuse_assumption':{'dry_platform_floor_y_m':y,'nominal_stored_water_y_m':y-2,'solid_bottom_y_m':y-2.6,'dry_platform_width_depth_m':[4,4],'required_excavation':True,'water_surface_required_separately':True},'protected_source_head_y_m':15.5,'static_head_difference_to_nominal_stored_water_m':15.5-(y-2),'static_head_order_screen':'PASS_RELATIVE_HEAD_ONLY' if y-2<15.5 else 'FAIL_NO_UNASSISTED_GRAVITY','nearest_authored_process_water_domain':process,'nearest_authored_river_domain':river,'nearest_authored_water_domain':nearest,'conservative_4m_square_edge_to_nearest_domain_lower_bound_m':max(0,nearest['distance_m']-math.sqrt(8)),'low_site_review':y<3,'conditions':['Final floor must be sampled at off-carriageway placement, not copied from station centre.','Maintain dry platform, a clear approach and reserved shaft excavation; rerun world-native/terrain tests.','Assign source from protected storage branch only; do not connect process/rain-drain/latrine or open canal into draw shaft.','Grade a shallow apron/runoff channel away from shaft and preserve open bank/service access; do not invent a ground-drain route through houses.','Static head ordering does not prove conveyance, water quality, flow, pressure, supply capacity or flood safety.','At low sites, a watertight stored-water vessel and maintenance/overflow arrangements require design; do not portray the shaft as a new groundwater well.']})
d={'schema':'riverstone.city.cistern_station_service_screen.v1','status':'CONCEPT_ONLY_SOURCE_HEAD_AND_PROXIMITY_SCREEN','network_candidates':{'path':str(P.relative_to(ROOT)),'sha256':sha(P)},'actual_scene_sha256':sha(S),'shared_master':{'path':str(master.relative_to(ROOT)),'sha256':sha(master),'datum':m['extensions']['datum'],'bounds':m['extensions']['local_bounds_m']},'source':{'id':'COVERED_CISTERN','head_y_m':15.5,'origin':'RAW_SPRING via reservoir; hypothetical separate covered distribution','status':'NEW_BRANCHES_NOT_AUTHORED_OR_BUILT'},'station_rows':rows,'limits':['Distance uses named finite authored water-domain polygons retained in actual scene terrain contract; not flood extents or pollution plume.','4m-square edge lower bound subtracts half diagonal from point distance; real side-pocket shift needs rescreening.','No numeric sanitary safe setback is certified; distance is a geometric screen only.','Station ranking1 and2 partly responds to disconnected evidence components; repair/replay junctions before fixing service priorities.','Master holds no water mesh or active supply connection. Reuse requires separate local water polygon and source association.','A lower static receiving head is necessary but not sufficient for a functioning gravity conduit; route/crests, losses, venting and capacity remain unbuilt.'],'market_fountain_minimal_fix':{'existing_instance':'MARKET_FOUNTAIN','existing_xyz_m':[99.41505784216918,4,22.75638652919374],'graph_inlet_head_y_m':4.6,'static_upper_water_y_m':6.1,'head_deficit_m':1.5,'preferred_reversible_change':'Place a separate low draw basin/ledge with nominal stored surface at or belowY4.4, or reuse the manually drawn closed-cistern concept at floorY4 with nominal waterY2; upper bowl remains inactive or explicitly manually filled.','do_not':['Do not arbitrarily raise the source/branch head toY6.1.','Do not label static opaque upper-bowl cells a working gravity-fed fluid.','Do not count manual filling/pressurization as implemented until source, apparatus and operation are shown.']}}
(OUT/'cistern_candidate_screen.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for r in rows:print(r['rank'],r['route_id'],'floor',round(r['station_xyz_m'][1],3),'stored',round(r['cistern_reuse_assumption']['nominal_stored_water_y_m'],3),'headmargin',round(r['static_head_difference_to_nominal_stored_water_m'],3),'process_distance',round(r['nearest_authored_process_water_domain']['distance_m'],2),'river',round(r['nearest_authored_river_domain']['distance_m'],2))
