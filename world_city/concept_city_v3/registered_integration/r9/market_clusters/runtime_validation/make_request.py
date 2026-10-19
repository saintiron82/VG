"""Bind the exact14 selected source paths and a native stall negative control."""
from pathlib import Path
import json,hashlib,math
H=Path(__file__).resolve().parent;root=next(p for p in H.parents if (p/'voxel_character').is_dir());city=root/'world_city/concept_city_v3'
def ref(p):
 p=p.resolve();return dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def read(p):return json.loads(p.read_text())
market=H.parent;rt=read(market/'runtime_routes.json');selected=set(rt['recommended_first_pass_route_ids']);routes=[]
for r in rt['routes']:
 if r['id'] not in selected:continue
 rr=dict(r,both_directions=True,cart_test=False);rr['placement_ids']=[];routes.append(rr)
assert len(routes)==14
p=next(p for p in read(market/'pack.json')['add_instances'] if p['id']=='R9_CLUSTER_GRAIN_WEST:02L')
def transform(z):
 x,y,w=p['position_m'];a=p['yaw_rad'];return[x+math.sin(a)*z,4,w+math.cos(a)*z]
routes.append(dict(id='NEGATIVE_ACTUAL_CLUSTER_STALL_COUNTER',kind='actual_market_stall_negative_control',points=[transform(3.8),transform(-3.8)],source_road_ids=[],test_scope='Deliberate straight crossing through an actual composed grain stall counter; expected blocked contact with that exact new native instance. No substitute wall or synthetic floor.',minimum_allowed_feet_y_m=3.7,group='GRAIN_WEST',expected_failure='blocked',expected_contact_id=p['id'],both_directions=False,cart_test=False))
index=city/'registered_integration/r9/integration_r02/index.json';headless=index.parent/'headless.json';hr=read(headless)
assert hr['visual_index_sha256']==ref(index)['sha256']
pattern=city/'registered_integration/r9/gate_runtime_validation/prepare.py';snapshot=H/'gate_prepare_pattern.py.txt'
if not snapshot.exists():snapshot.write_bytes(pattern.read_bytes())
request=dict(schema='riverstone.r9.market_runtime_request.v1',base_scene=ref(city/'evidence/r8_final110_runtime_r01/scene.json'),finite_patch=dict(path=hr['surface_addendum']['path'],sha256=hr['surface_addendum']['sha256']),visual_index=ref(index),producer_sources={'runtime_routes':ref(market/'runtime_routes.json'),'market_pack':ref(market/'pack.json'),'root_headless':ref(headless),'gate_prepare_pattern_snapshot':ref(snapshot)},collision_margin_m=6,routes=routes,market_coverage=dict(selected_unique_routes=14,customer_unique_routes=7,service_unique_routes=7,positive_directional_cases=28,old493_rerun=False,crop_policy='AABB of every source waypoint in the court, expanded6m in XZ. Every whole triangle whose bounds overlap is retained, with all overlapping exact native meshes. This encloses the full3m service corridor and all0.6m capsule diameters, not just route midpoints.'))
with (H/'request.json').open('x') as f:json.dump(request,f,indent=2);f.write('\n')
print('request ready:',len(routes),'unique with blocked counter;31 cases including two retained controls')
