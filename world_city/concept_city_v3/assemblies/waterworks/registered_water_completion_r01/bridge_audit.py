"""Audit actual ROAD_OPEN moving leaves separately from absent north approach."""
from .audit import *
def tx(v,t):return[t['translation'][i]+sum(t['basis'][i][j]*v[j]for j in range(3))for i in range(3)]
def run():
 s=a.load_scene();m=s['bridge_mechanism'];state=m['states']['ROAD_OPEN'];ix=Index();refs=[]
 for p in s['common_instances']:
  if not p['id'].startswith('BRIDGE_MAIN_RIVER:'):continue
  ass=s['common_assets'][p['asset_key']];r=json.loads((ROOT/ass['render_path']).read_text());refs.append(ref(ROOT/ass['render_path']))
  for gr in r['groups']:
   for q in gr['quads']:
    q=[pose(v,p)for v in q]
    for t in[q[:3],[q[0],q[2],q[3]]]:ix.add(t,id=p['id'])
 for p in state['movable_placements']:
  if not p['id'].startswith(('LEAF_','HINGE_PLATE_')):continue
  ass=s['common_assets'][p['asset_key']];r=json.loads((ROOT/ass['render_path']).read_text());refs.append(ref(ROOT/ass['render_path']))
  for gr in r['groups']:
   for q in gr['quads']:
    q=[tx(tx(v,p['transform_bridge_local']),m['bridge_to_world'])for v in q]
    for t in[q[:3],[q[0],q[2],q[3]]]:ix.add(t,id=p['id'])
 source=json.loads((HERE/'actual_geometry_audit.json').read_text());out=[]
 for r in source['road_water_intersections']:
  if r['road_id']not in['MAIN_BRIDGE','PORT_BRIDGE_TIE']:continue
  covers=[];owners=[]
  for row,q in ix.covering(r['polygon_xz_m']):covers.append(q);owners.append(row['id'])
  gap=sum(g.polygon_area(q)for q in a.common.subtract([r['polygon_xz_m']],covers));out.append(dict(road_id=r['road_id'],road_segment=r['road_segment'],water_triangle_index=r['water_triangle_index'],area_m2=r['area_m2'],static_only_missing_deck_area_m2=r['missing_deck_area_m2'],ROAD_OPEN_missing_deck_area_m2=gap,actual_top_owners=sorted(set(owners))))
 main=[r for r in out if r['road_id']=='MAIN_BRIDGE'];assert sum(r['ROAD_OPEN_missing_deck_area_m2']for r in main)<1e-7
 write('main_bridge_interfaces.json',dict(base_scene=ref(a.SCENE_PATH),native_cache_dependencies=refs,actual_state='ROAD_OPEN',state_road_enabled=state['road_enabled'],state_navigation_enabled=state['navigation_enabled'],main_road_water_projection_m2=sum(r['area_m2']for r in main),static_only_gap_m2=sum(r['static_only_missing_deck_area_m2']for r in main),with_actual_moving_leaves_gap_m2=sum(r['ROAD_OPEN_missing_deck_area_m2']for r in main),crossings=out,explicit_open_dependency=dict(id='north_approach_r03',owner='parent city lead',role='Missing bridge-to-city/PORT_BRIDGE_TIE connector; deliberately not duplicated here'),limits=['Actual ROAD_OPEN cache top projection only. Live movement, state interlocks and whole-controller clearance were not replayed in this audit.','Southern finite lane already exists with separate collision contracts; this audit does not replace them.']))
 print('PASS ROAD_OPEN main wet crossing; north approach remains parent-owned',flush=True)
if __name__=='__main__':run()
