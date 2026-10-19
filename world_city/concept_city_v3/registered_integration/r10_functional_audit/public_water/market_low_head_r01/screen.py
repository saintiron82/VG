"""Conservative market low-head location screen; this is not an activated pack."""
import json,math
from pathlib import Path
from world_city.concept_city_v3.registered_integration.r9.market_clusters.author import Context,load,ring,overlap,corridor
from world_city.runtime_city.checks import placement as g
from ..select_sites import trans,rect
from ..author import ref,B,R
H=Path(__file__).resolve().parent
ctx=Context();market=B/'registered_integration/r9/market_clusters';pack=load(market/'pack.json');layout=load(market/'layout.json')
for p in pack['add_instances']:ctx.solids.append(dict(id=p['id'],polygon=ring(ctx.assets[p['asset_key']]['bounds'],p),y_min=3.5,y_max=4+ctx.assets[p['asset_key']]['bounds']['max'][1],source='current_r9_cluster'))
ctx.reindex();extra=[];eidx=g._SpatialIndex(8)
for r in layout['routes']:
 points=[[p[0],p[2]]for p in r['points_xyz_m']]
 for p in corridor(points,r['width_m']):eidx.add(len(extra),p);extra.append(dict(id=r['id'],polygon=p))
map={r['id']:r for r in load(B/'registered_integration/r10_functional_audit/network/observed_route_observation_mapping.json')};fountain=[99.4150578422,22.7563865292]
rows=[]
for roadid in ['ROAD:MARKET_PROCESSION','ROAD:MARKET_WEST_EDGE','ROAD:MARKET_EAST_EDGE','ROAD:MARKET_CROSS']:
 if roadid not in map:continue
 path=map[roadid]['observed_graph_points_xyz_m']
 for a,b in zip(path,path[1:]):
  L=math.dist(a,b)
  if L<1e-6:continue
  t=[(b[0]-a[0])/L,(b[2]-a[2])/L]
  for f in [.25,.75]:
   station=[a[k]+f*(b[k]-a[k])for k in range(3)]
   if math.dist([station[0],station[2]],fountain)>30:continue
   for side in [-1,1]:
    normal=[-t[1]*side,t[0]*side]
    for distance in [4,5,6,7,8]:
     pos=[station[0]+normal[0]*distance,4,station[2]+normal[1]*distance];yaw=math.atan2(-normal[0],-normal[1]);poly=trans(rect(-1.5,-1.5,1.5,1.5),pos,yaw)
     if not g.convex_polygon_contains(ctx.site,poly,0):continue
     if ctx.blocked(poly,4.001,6):continue
     if ctx.reserved(poly):continue
     if any(overlap(poly,extra[i]['polygon'])for i in eidx.candidates(poly)):continue
     if not ctx.support(poly):continue
     # New queue lives inside the reserved3x3 pocket; connector is separately
     # checked for actual retained native obstacles, never treated as a new shortcut.
     end=trans([[0,1.5]],pos,yaw)[0];branch=g.road_ribbon([station[0],station[2]],end,2)
     if ctx.blocked(branch,4.001,6.2):continue
     if not ctx.support(branch):continue
     rows.append(dict(position_m=pos,yaw_rad=yaw,public_road_id=roadid,public_station_xyz_m=station,footprint_xz_m=poly,branch_polygon_xz_m=branch,branch_points_xyz_m=[station,[end[0],4,end[1]]],branch_width_m=2,branch_length_m=distance-1.5,distance_to_existing_fountain_m=math.dist([pos[0],pos[2]],fountain),status='CURRENT_R9_BOUNDS_RESERVATIONS_AND_NINE_POINT_LEVEL_SUPPORT_SCREEN_PASS_NOT_FULL_SOURCE_AUDIT'))
rows.sort(key=lambda r:(r['distance_to_existing_fountain_m'],r['branch_length_m']))
out=dict(schema='riverstone.market_low_head_candidate_screen.v1',status='CANDIDATE_FOUND'if rows else'NO_CLEAR_POCKET_IN_SCREEN',tested_context_sources=ctx.c['source_refs'],current_cluster_pack=ref(market/'pack.json'),current_cluster_layout=ref(market/'layout.json'),first_candidates=rows[:10],candidate_count=len(rows),hydraulic_design=dict(market_floor_y_m=4,existing_inlet_head_y_m=4.6,proposed_direct_low_outlet_y_m=4.45,proposed_receiving_surface_y_m=4.3,maximum_receiving_surface_y_m=4.4,static_margin_above_outlet_m=.15,feed_relationship='Separate protected branch to low outlet; shallow basin receives, it does not pressurize an outlet above its water.',no_deep_excavation=True,no_head_invention=True,no_citywide_capacity_claim=True),missing=['Exact source-face floor ownership and bank-side audit','Final current composed whole-native/legacy clearance','Actual small basin common master and static valve/socket geometry','Full branch sourceY and public-owner integration','Runtime and visual review','Flow loss, source yield, water quality and cleaning operations'],original_fountain_policy='Position and complete external appearance remain unchanged. Its upper static bowls are not claimed gravity-fed fromY4.6; low-head public draw function is the new independent proposal.')
(H/'candidate_screen.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(rows));print(json.dumps(rows[:2],indent=2))
