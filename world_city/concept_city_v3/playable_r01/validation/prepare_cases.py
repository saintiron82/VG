#!/usr/bin/env python3
"""Select unchanged authored coordinates; never author traversal geometry."""
import hashlib,json,pathlib,math
ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent
CITY=ROOT/'world_city/concept_city_v3'
def read(p):return json.loads(p.read_text())
def source(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def route(p,id):return next(r for r in read(p)['routes'] if r['id']==id)
def length(points):return sum(math.dist(a,b) for a,b in zip(points,points[1:]))
network=CITY/'traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04/selected_all493_bound_r02.json'
stairs=CITY/'traversal_r5/revisions/r06_r8_precinct/stair_proxy_r01/prepared.json'
gates=CITY/'registered_integration/r9/landward_gates/runtime_r10_tools/replay_r01/prepared.json'
pack=CITY/'registered_integration/r9/landward_gates/candidate_r09/gate_pack.json'
procession=route(network,'ROAD:MARKET_PROCESSION')['points']
south=route(network,'ROAD:SOUTH_MARKET_AXIS')['points']
market=[procession[1],procession[0]]+list(reversed(south[-4:-1]))
assert market[0][2]<64<market[-1][2]
cases=[{'id':'MARKET_TO_ADJACENT_SOUTH_STREET','expect':'reach','points':market,'source_segments':[{'source':'network','route_id':'ROAD:MARKET_PROCESSION','indices':[1,0]},{'source':'network','route_id':'ROAD:SOUTH_MARKET_AXIS','indices':[42,41,40]}], 'scope':'Continuous market procession to adjacent south street, crossing real 64 m streaming cell boundary at Z64.'}]
for id in ['R8_STAIR_CENTER','R8_STAIR_CENTER_REVERSE']:
 r=route(stairs,id);cases.append({'id':id,'expect':'reach','points':r['points'],'source_segments':[{'source':'stairs','route_id':id,'all_points':True}],'scope':'Real native two-flight neighborhood stair with the approved existing finite walking collision contract; no added step assist.'})
for id in ['EAST_GATE_THROAT_TURNS','WEST_GATE_THROAT_TURNS']:
 r=route(gates,id);cases.append({'id':id,'expect':'reach','points':r['points'],'source_segments':[{'source':'gates','route_id':id,'all_points':True}],'scope':'Separate native landward gate throat, exact original route.'})
fountain_tile=CITY/'playable_r01/generated/tile_r01/tiles/1_0.json'
fountain=next(i for i in read(fountain_tile)['common_instances'] if i['id']=='MARKET_FOUNTAIN')
assert abs(fountain.get('yaw_rad',0))<1e-8
fountain_asset=read(CITY/'playable_r01/generated/tile_r01/index.json')['common_assets'][fountain['asset_key']]
fountain_render=ROOT/fountain_asset['render_path']
assert abs(procession[3][2]-fountain['position_m'][2])<1e-8
cases.append({'id':'NEGATIVE_MARKET_FOUNTAIN','expect':'blocked','points':[procession[3],fountain['position_m']],'duration_ticks':480,'fixed_direction':True,'expected_obstacle_source_ids':['MARKET_FOUNTAIN'],'source_segments':[{'source':'network','route_id':'ROAD:MARKET_PROCESSION','indices':[3]},{'source':'fountain_tile','instance_id':'MARKET_FOUNTAIN','basis':'exact native fountain origin, axis-aligned solid obstacle ahead of an actual market street point'}],'scope':'Hold +X walking input from the actual market procession into the unchanged native fountain. Require opposing near-vertical native fountain contact and at least 120 consecutive stationary blocked ticks; no test geometry or floor.'})
for case in cases:case.update(length_m=length(case['points']),speed_mps=1.65,waypoint_tolerance_m=.10)
data={'schema':'riverstone.lily_city.actual_route_inputs.v1','physics_hz':60,'repo_root':str(ROOT),'tile_size_m':64,'sources':{'network':source(network),'stairs':source(stairs),'gates':source(gates),'gate_pack':source(pack),'fountain_tile':source(fountain_tile),'fountain_render':source(fountain_render),'lily_controller':source(ROOT/'voxel_character/lily_city/runtime/LilyController.gd')},'cases':cases,'limitations':['Direction/speed route-following is automated test input, not manual WASD or camera review.','Waypoint Y is diagnostic only; it never positions the actor during traversal.','Case starts are separate spawn-only resets, not a claim that the distant scenarios are one continuous walk.','No NPC behavior, economy, time schedule, jump, floor injection or collision changes.']}
(OUT/'cases.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'cases':len(cases),'output':str(OUT/'cases.json'),'lengths':{x['id']:x['length_m'] for x in cases}},indent=2))
