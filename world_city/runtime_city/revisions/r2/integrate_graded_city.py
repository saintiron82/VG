"""Bind independently compiled common terrain layers to existing city placements.
This is placement/data orchestration, never a geometry sampler or collision engine.
"""
from pathlib import Path
import argparse,copy,json,math,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.assemble_city import write,sha
from world_city.runtime_city.topography.author import GradeField
from world_city.runtime_city.checks.placement import transform_point_m
RUNTIME=ROOT/'world_city/runtime_city'

def integrate(flat,layer,wall=None,fabric=None):
 if layer.get('status')!='compiled_structural_only':raise ValueError('Incomplete terrain layer must never replace ground')
 scene=copy.deepcopy(flat);field=GradeField(layer['changed_ground_ownership'].get('regions',[])) if layer['changed_ground_ownership'].get('regions') else None
 if field is None:
  source=json.loads((ROOT/layer['source_plan_path']).read_text())
  if sha(ROOT/layer['source_plan_path'])!=layer['source_plan_sha256']:raise ValueError('Terrain source snapshot changed after compile')
  field=GradeField(source['regions'])
 byid={x['id']:x for x in scene['instances']};contracts=layer['building_footing_contracts'];entry_exceptions=[]
 for c in contracts:
  i=byid[c['id']];old=copy.deepcopy(i['position_m']);p=c['position_m']
  if [old[0],old[2]]!=[p[0],p[2]]:raise ValueError(('Terrain moved building XZ',i['id']))
  i['position_m']=p;i['terrain_projection']={'source_position_m':old,'foundation_resources':c.get('compiled_resources'),'exceptions':c.get('integration_exceptions',[])}
  i['entrance']['position_m']=c['entrance_position_m'];i['entrance']['road_connection_m']=c['road_connection_m']
  i['all_entrances_world_m']=[transform_point_m(local,p,i['yaw_rad']) for local in i['all_entrances_local_m']]
  for entry in c.get('all_entrance_contracts',[]):
   if abs(entry['floor_minus_ground_m'])>.1+1e-8:entry_exceptions.append({'id':i['id'],**entry})
 inf=scene['infrastructure'];removed=set(layer['replace_r1_placement_ids'])|set(layer['replace_urban_fabric_placement_ids']);oldids={x['id'] for x in inf['placements']}
 missing=removed-oldids
 if missing:raise ValueError(('Terrain replacement IDs missing from input',sorted(missing)))
 inf['placements']=[x for x in inf['placements'] if x['id'] not in removed]
 if set(layer['assets']).intersection(inf['assets']):raise ValueError('Terrain asset key collision')
 inf['assets'].update(layer['assets']);inf['placements'].extend(layer['placements'])
 walls=[]
 if wall:
  # Supplement owns exact source-backed support geometry and rigid curtain-wall anchors.
  if not wall.get('status','').startswith('compiled'):raise ValueError('Incomplete curtain-wall supplement')
  anchors=wall.get('wall_projection_contracts',wall.get('wall_projections',[]));lookup={x['id']:x for x in inf['placements']}
  for c in anchors:
   sid=c.get('source_placement_id',c.get('id'));p=lookup[sid];new=c['position_m']
   if [p['position_m'][0],p['position_m'][2]]!=[new[0],new[2]]:raise ValueError(('Wall XZ changed',sid))
   p['position_m']=new;p.setdefault('transform',{})['translation']=new;p['terrain_projection']=c;walls.append(sid)
  if set(wall.get('assets',{})).intersection(inf['assets']):raise ValueError('Wall support asset key collision')
  inf['assets'].update(wall.get('assets',{}));inf['placements'].extend(wall.get('placements',[]))
 # Project existing property pieces only using their declared finite support anchors.
 anchor_checks=[];problems=[];omitted=[]
 for p in inf['placements']:
  anchor=p.get('ground_anchor')
  if not anchor:continue
  points=anchor.get('support_points_xz_m') or [anchor['sample_center_xz_m']]
  heights=[field.height(*pt) for pt in points];low,high=min(heights),max(heights);delta=high-low
  limit=anchor.get('maximum_support_height_delta_m',.75)
  if delta>limit+1e-8:
   issue={'id':p['id'],'reason':'support height variation exceeds authored embedding contract','delta_m':delta,'limit_m':limit,'source_action':anchor.get('exceedance_action')}
   if 'or_omit_do_not_float' in str(anchor.get('exceedance_action','')):omitted.append(issue)
   else:problems.append(issue)
   continue
  h=(low+high)/2;datum=anchor.get('datum_y_m',0);old=p['position_m'][1]
  p['position_m'][1]=old+h-datum
  if 'transform' in p:p['transform']['translation']=p['position_m']
  p['terrain_anchor']={'support_min_y_m':low,'support_max_y_m':high,'placed_y_m':p['position_m'][1],'root_anchor_only':True}
  anchor_checks.append({'id':p['id'],'delta_m':delta,'anchor_y_m':h})
 if problems:raise ValueError(('Do not float unsupported property pieces',problems))
 omit_ids={x['id'] for x in omitted};inf['placements']=[p for p in inf['placements'] if p['id'] not in omit_ids]
 # The viewer honors each world-coordinate resource's stream address; geometry remains identity placed.
 used={p['asset_key'] for p in inf['placements']};inf['assets']={k:v for k,v in inf['assets'].items() if k in used}
 for n in scene['road_nodes']:
  if n.get('id','').startswith('WALL_'):continue
  x,_,z=n['position_m'];n['position_m'][1]=field.height(x,z)
 scene['revision']='recovered_r2_graded_property_candidate';scene['status']='compiled_exterior_grade_candidate_pending_visual_and_collision_review'
 scene['terrain_grade_policy']={'scope':'graded source surfaces with .5m medium/2m macro distant visuals and bounded .1m sample','primary_building_anchors':len(contracts),'secondary_door_exceptions':entry_exceptions,'curtain_wall_anchors':walls,'collision_scope':'No implicit medium/macro voxel-walk approval; see dedicated proxy/step candidate tests','wall_supports_present':wall is not None,'omitted_property_pieces':omitted}
 scene['camera_scope']='graded exterior candidate; secondary thresholds, wall-access gameplay and full-city collision remain under review'
 scene['urban_fabric_layer_scope']='r2 flat-review geometry projected onto actual grade; manor/forest visual corrections pending'
 scene['grade_layer']={'source_plan_path':layer['source_plan_path'],'source_plan_sha256':layer['source_plan_sha256'],'fine_region':layer['tested_fine_region'],'budgets':layer['budgets'],'execution':layer['execution']}
 scene['grade_field_regions']=field.regions
 scene['inspection_cameras']={
  'graded_castle':{'position_m':[-525,82,-190],'target_m':[-440,39,-350]},
  'graded_climb':{'position_m':[-566,field.height(-566,-229)+1.7,-229],'target_m':[-552,field.height(-552,-249)+1.7,-249]},
  'north_wall':{'position_m':[-450,65,-590],'target_m':[-440,24,-500]},
  'graded_cathedral':{'position_m':[455,110,-200],'target_m':[350,41,-330]}
 }
 return scene,{'building_anchors':len(contracts),'secondary_door_exceptions':entry_exceptions,'property_anchor_checks':anchor_checks,'wall_projection_ids':walls,'omitted_property_pieces':omitted,'replaced_infrastructure':len(removed),'infra_placements':len(inf['placements']),'infra_resources':len(inf['assets']),'no_building_xz_changes':True,'unverified':['Actual integrated visual review','Production controller/nav/NPC/camera','Secondary doorway threshold design','Elevated wallwalk access']}

def main():
 p=argparse.ArgumentParser();p.add_argument('--layer',default=str(RUNTIME/'generated/r2_topography/layer_manifest.json'));p.add_argument('--walls');p.add_argument('--out',default=str(RUNTIME/'generated/r2/scene.graded_property.json'));args=p.parse_args()
 src=RUNTIME/'generated/r2/scene.flat_property.json';lp=Path(args.layer);wp=Path(args.walls) if args.walls else None
 s,r=integrate(json.loads(src.read_text()),json.loads(lp.read_text()),json.loads(wp.read_text()) if wp else None)
 fabric_path=RUNTIME/'revisions/r3/urban_fabric.access_repaired.json';fabric=json.loads(fabric_path.read_text());projected={x['id']:x for x in s['infrastructure']['placements']};omitted={x['id'] for x in r['omitted_property_pieces']};fabric['placements']=[copy.deepcopy(projected[x['id']]) for x in fabric['placements'] if x['id'] in projected];fabric['terrain_omission_ledger']=r['omitted_property_pieces'];fabric['revision']='r2_graded_fabric_access_repaired';write(RUNTIME/'generated/r2/urban_fabric.graded.json',fabric)
 r['inputs']={'flat_scene_sha256':sha(src),'terrain_layer_sha256':sha(lp),'wall_layer_sha256':sha(wp) if wp else None};s['graded_integration_sources']=r['inputs'];write(Path(args.out),s);write(RUNTIME/'evidence/r2_graded_integration.json',r)
 print(json.dumps({k:v for k,v in r.items() if k not in ['secondary_door_exceptions','property_anchor_checks']},indent=2))
if __name__=='__main__':main()
