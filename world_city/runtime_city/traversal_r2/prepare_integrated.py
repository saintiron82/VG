#!/usr/bin/env python3
"""Stable integrated baseline/proxy pair with matching fixed route fixtures."""
import argparse,copy,json
from pathlib import Path
import prepare as base
from prepare_candidate import control_asset
ROOT=base.ROOT;HERE=base.HERE
REMOVE_PROXY_CATEGORIES={'terrain_macro','terrain_medium','fine_walk_surface','fine_buried_buffer','fine_buried_support'}

def prepare(scene,layers,out,proxy=False,proxy_path=HERE/'proxy_city/layer_manifest.json'):
 p=base.prepare(scene,layers,out,False);layer=base.read(layers);integrated=base.read(scene)
 merged_assets={**layer['assets'],**integrated['infrastructure']['assets']}
 support_placements={v['id']:v for v in layer['placements']+integrated['infrastructure']['placements']}
 for route in list(p['routes']):
  if route['kind'] in ('medium_grade_transition','medium_entry_approach'):
   reverse=copy.deepcopy(route);reverse['id']+='_REVERSE';reverse['points'].reverse();p['routes'].append(reverse)
 # Preserve new dedicated wall footing/support colliders if present in final layer.
 for placement in support_placements.values():
  if placement['category'] in base.GROUND|base.OBSTACLES:continue
  if not any(word in placement['category'] for word in ['foundation','retaining','support']):continue
  asset=merged_assets[placement['asset_key']];bounds=base.transformed_bounds(asset['bounds'],placement)
  for route in p['routes']:
   if not base.corridor_intersects(bounds,route['points']):continue
   item=copy.deepcopy(placement);item.update(world_bounds_xz_m=bounds,collision_layer=2)
   p['placements'][item['id']]=item;p['assets'][item['asset_key']]=asset
   if item['id'] not in route['placement_ids']:route['placement_ids'].append(item['id'])
 key='INTEGRATED_ACTUAL_STEP_025';p['assets'][key]=control_asset(key,[([-2,-.2,-2],[2,0,2]),([0,0,-2],[2,.25,2])]);ident='CONTROL:'+key
 p['placements'][ident]={'id':ident,'asset_key':key,'position_m':[0,0,0],'yaw_deg':0,'category':'isolated_actual_voxel_control','collision_layer':1}
 route=base.route_record('NEGATIVE_AUTHORED_STEP_0P25',[[-1,0],[1,0]],'negative_control',[],expected_failure='blocked',expected_contact_id=ident,test_scope='actual isolated common-voxel control; never terrain proxy')
 route.update(placement_ids=[ident],building_ids=[]);p['routes'].append(route)
 p['schema']='riverstone.city.r2_integrated_actual_suite.v1'
 if proxy:
  candidate=base.read(proxy_path)
  plan_path=ROOT/layer['source_plan_path']
  if candidate['sources']['source_plan']['sha256']!=base.digest(plan_path):raise ValueError('Full proxy source differs from final terrain source')
  for name,s in candidate['sources'].items():
   if base.digest(s['path'])!=s['sha256']:raise ValueError('Proxy source changed '+name)
  p['visual_ground_assets_replaced_for_collision']={item['asset_key']:p['assets'][item['asset_key']] for item in p['placements'].values() if item['category'] in REMOVE_PROXY_CATEGORIES}
  removed={id for id,item in p['placements'].items() if item['category'] in REMOVE_PROXY_CATEGORIES}
  p['placements']={id:item for id,item in p['placements'].items() if id not in removed}
  for route in p['routes']:
   route['placement_ids']=[id for id in route['placement_ids'] if id not in removed]
   if route['id']=='NEGATIVE_AUTHORED_STEP_0P25':continue
   for item in candidate['placements']:
    if base.corridor_intersects(item['world_bounds_xz_m'],route['points']):
     p['placements'][item['id']]=item;p['assets'][item['asset_key']]=candidate['assets'][item['asset_key']];route['placement_ids'].append(item['id'])
  p['sources']['city_proxy']={'path':str(proxy_path.resolve()),'sha256':base.digest(proxy_path)}
  p['sources']['city_proxy_source_plan']=candidate['sources']['source_plan'];p['sources']['city_proxy_r1_infrastructure']=candidate['sources']['r1_infrastructure']
  p['proxy_validation']=candidate['summary'];p['schema']='riverstone.city.r2_integrated_source_grade_proxy_suite.v1'
  p['assumptions']['actual_ground']='exact finite source H collision over owned graded tiles;326body voids subtracted; other actual ground/structures untouched'
  p['assumptions']['controller']='original generic capsule; no step-up'
  p['assumptions']['test_collision_policy']='optional source-grade proxy only; actual authored stairs/foundations/retaining walls/bridges/structures remain colliders'
  for f in ['CitySourceGradeProxy.gd','CitySourceGradeProxy.tscn','build_city_proxy.py']:
   file=HERE/f;p['implementation_hashes'][str(file.relative_to(ROOT))]=base.digest(file)
 keys={v['asset_key'] for v in p['placements'].values()};p['assets']={k:v for k,v in p['assets'].items() if k in keys}
 for key,asset in p['assets'].items():
  if base.digest(ROOT/asset['render_path'])!=asset['render_sha256']:raise ValueError('Selected collision asset changed '+key)
 p['implementation_hashes'][str((HERE/'prepare_integrated.py').relative_to(ROOT))]=base.digest(HERE/'prepare_integrated.py')
 p['coverage']['route_count']=len(p['routes']);p['coverage']['selected_collision_assets']=len(p['assets']);p['coverage']['selected_placements']=len(p['placements'])
 p['coverage']['bidirectional_grade_and_entry']=True
 p['secondary_entrance_exceptions']=[{'id':b['id'],'exceptions':b.get('integration_exceptions',[]),'all_entrance_contracts':b.get('all_entrance_contracts',[])} for b in layer['building_footing_contracts'] if any('secondary' in str(x).lower() or 'second' in str(x).lower() for x in b.get('integration_exceptions',[]))]
 base.write(out,p);return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--scene',type=Path,default=ROOT/'world_city/runtime_city/generated/r2/scene.json')
 ap.add_argument('--layers',type=Path,default=ROOT/'world_city/runtime_city/generated/r2_topography/layer_manifest.json')
 ap.add_argument('--output',type=Path,default=HERE/'prepared.integrated_actual.json');ap.add_argument('--proxy',action='store_true');args=ap.parse_args()
 p=prepare(args.scene,args.layers,args.output,args.proxy);print(json.dumps({'sources':p['sources'],'coverage':p['coverage'],'secondary_entrance_exception_buildings':len(p['secondary_entrance_exceptions']),'anchor_overrides':len(p['scene_anchor_overrides_from_tested_layer'])},indent=2))
