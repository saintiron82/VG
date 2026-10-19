"""Coarse semantic envelopes derived from frozen continuous landmark operations.

Only source bounds and rigid transforms are evaluated. No sampling/compilation or
scene edits. Envelopes are silhouette-review aids, not collision solids.
"""
from pathlib import Path
import copy,json,math,sys,itertools
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from voxel_character.common import core,coordinate_planes
from world_city.concept_city_v3.assemblies.landmarks.author import HERE,ref,write,placement


def build():
 manifest=json.loads((HERE/'assemblies.json').read_text());groups=[]
 for entry in manifest['assemblies']:
  kind=entry['assembly_source'];source=json.loads((HERE/'masters'/f'{kind}.json').read_text());numeric,_=coordinate_planes.resolve_master(source,{'pitch':.01})
  instances={i['component']:core.transform(i.get('transform')) for i in numeric['instances']}
  ops=[]
  for c in numeric['components']:
   for op in c['operations']:
    if op['action']!='paint':continue
    lo,hi=core.shape_bounds(core.prepare_shape(op['shape'],.01));t=core.compose(instances[c['id']],core.transform(op.get('transform')))
    points=[core.apply(t,p) for p in itertools.product(*zip(lo,hi))]
    ops.append((c['id'],op['id'],points))
  rows=[]
  def mass(key,role,select,shape='box_envelope'):
   selected=[o for o in ops if select(o[0],o[1])]
   if not selected:return
   points=[p for o in selected for p in o[2]]
   lo=[min(p[j] for p in points) for j in range(3)];hi=[max(p[j] for p in points) for j in range(3)]
   rows.append({'id':key,'semantic_role':role,'position_local_xyz_m':[(lo[j]+hi[j])/2 for j in range(3)],'size_xyz_m':[hi[j]-lo[j] for j in range(3)],'yaw_degrees':0,'bounds_local_m':{'min':lo,'max':hi},'proxy_shape':shape,'bounds_baked_to_anchor_axes':True,'source_operation_ids':[o[1] for o in selected]})
  def body(key,prefix):mass(key,'masonry_body',lambda c,o:o.startswith(prefix) and c.endswith('__masonry') and '_gable_' not in o)
  def roof(key,prefix,shape='gable_roof_envelope'):mass(key,'roof',lambda c,o:o.startswith(prefix) and c.endswith('__roof'),shape)
  if kind=='cathedral':
   for key in ['nave','aisle_-1','aisle_1','transept']:
    body(key+'_body','nave__'+key+'_');roof(key+'_roof','nave__'+key+'_')
   for side in (-1,1):
    key='front_tower_'+str(side);body(key+'_body','nave__'+key+'_');roof(key+'_spire','nave__'+key+'_','pointed_spire_envelope')
   for side in (-1,1):
    for i in range(8):mass(f'aisle_buttress_{side}_{i}','stepped_buttress',lambda c,o,p=f'nave__buttress_{side}_{i}_':o.startswith(p))
   for item in source['extensions']['source_assemblies']:
    if item['key'].startswith('fly_'):
     for component in ('pier','arch'):mass(item['key']+'_'+component,'flying_buttress_'+component,lambda c,o,p=item['key']+'__'+component:c==p)
  elif kind=='castle':
   # Each thin curtain side is separate. The rear keep never fills the court.
   for side in ('west','east','rear','front'):
    mass('curtain_'+side,'curtain_wall',lambda c,o,s=side:o=='keep__curtain_'+s)
   # Split the source front wall using its actual 8 m by 6 m door cut.
   front=rows.pop();lo=front['bounds_local_m']['min'];hi=front['bounds_local_m']['max']
   cut=next(op for c in numeric['components'] for op in c['operations'] if op['id']=='keep__curtain_door_opening')['shape']
   left,right,top=cut['min'][0],cut['max'][0],cut['max'][1]
   for suffix,low,high in [('west',[lo[0],lo[1],lo[2]],[left,hi[1],hi[2]]),('east',[right,lo[1],lo[2]],[hi[0],hi[1],hi[2]]),('header',[left,top,lo[2]],[right,hi[1],hi[2]])]:
    row=copy.deepcopy(front);row.update(id='curtain_front_'+suffix,bounds_local_m={'min':low,'max':high},position_local_xyz_m=[(low[j]+high[j])/2 for j in range(3)],size_xyz_m=[high[j]-low[j] for j in range(3)],source_cut_id='keep__curtain_door_opening');rows.append(row)
   body('rear_keep_body','keep__rear_keep_');roof('rear_keep_roof','keep__keep_')
   for sx in (-1,1):
    for sz in (-1,1):
     prefix=f'keep__corner_{sx}_{sz}_';mass(f'corner_tower_{sx}_{sz}','crenellated_tower',lambda c,o,p=prefix:o.startswith(p) and not c.endswith('__windows'))
   for side in (-1,1):body('gate_tower_'+str(side),'south_gate__gate_tower_'+str(side)+'_')
   mass('gate_gallery','gate_gallery',lambda c,o:o.startswith('south_gate__gallery'))
  elif kind=='monastery':
   for key in ('west_wing','east_wing','rear_wing','chapel'):
    body(key+'_body','monastic_wings__'+key+'_');roof(key+'_roof','monastic_wings__'+key+'_')
  elif kind=='civic_grain':
   body('town_hall_body','town_hall__hall_');roof('town_hall_roof','town_hall__great_roof_')
   body('civic_tower_body','town_hall__civic_tower_');roof('civic_tower_spire','town_hall__civic_tower_','pointed_spire_envelope')
   mass('civic_arcade_upper','arcade_spandrels',lambda c,o:c=='town_hall__arcade' and 'spandrel' in o)
   for i in range(10):mass('civic_arcade_pier_'+str(i),'arcade_pier',lambda c,o,k='town_hall__pier_'+str(i):o==k)
   body('grain_hall_body','grain_hall__warehouse_');roof('grain_hall_roof','grain_hall__warehouse_')
  elif kind=='port_cluster':
   for side in ('west','east'):
    key='warehouse_'+side;body(key+'_body',key+'__warehouse_');roof(key+'_roof',key+'__warehouse_')
  covered=('keep','nave','monastic_wings','town_hall','grain_hall','warehouse_west','warehouse_east','south_gate')
  for item in source['extensions']['source_assemblies']:
   key=item['key']
   if key in covered or key.startswith(('court_','terrace_','hall_forecourt_','loading_yard_','fly_','apron_foundation','quay_foundation')):continue
   mass(key,'service_or_enclosure',lambda c,o,p=key+'__':c.startswith(p))
  for d in entry['fine_details']:
   fine=json.loads((HERE/'masters'/('fine_'+d['cache_key']+'.json')).read_text());b=fine['extensions']['local_bounds_m']
   center=[(b['min'][j]+b['max'][j])/2 for j in range(3)];p=core.apply(placement(d['position_local_m'],d['yaw_degrees']),center)
   rows.append({'id':d['id'],'semantic_role':d['cache_key'],'position_local_xyz_m':p,'size_xyz_m':[b['max'][j]-b['min'][j] for j in range(3)],'yaw_degrees':d['yaw_degrees'],'proxy_shape':'small_facility_envelope','bounds_baked_to_anchor_axes':False,'datum':d['datum'],'source_detail_id':d['id']})
  groups.append({'id':entry['id'],'assembly_source':kind,'source_group_key':kind,'world_anchor_xyz_m':entry['world_translation_m'],'replaces_source_building_ids':entry['replaces_source_building_ids'],'source_master':ref(str((HERE/'masters'/f'{kind}.json').relative_to(ROOT))),'masses':rows,'access_reservations':source['extensions']['access_reservations'],'open_space_policy':'Do not fill a group bounding box. Courtyards and the spaces between these separate masses remain open. Box envelopes themselves are not collision/traversal geometry.'})
 result={'schema':'riverstone.city.landmark_proxy_masses.v1','status':'semantic_silhouette_envelopes_for_blockout_only','source_manifest':ref(str((HERE/'assemblies.json').relative_to(ROOT))),'author':ref('world_city/concept_city_v3/assemblies/landmarks/build_proxy_masses.py'),'coordinate_contract':'Each group anchor is world XYZ. Each mass position is an anchor-relative BOX CENTER; size is local XYZ; yaw rotates around +Y. Baked boxes use yaw=0. Boat datum must resolve separately against river_water_y, not host ground.','no_new_compile':True,'no_actual_scene_edits':True,'groups':groups,'limitations':['Roof/spire boxes are envelopes, not final roof meshes; renderer may use indicated silhouette shape within that envelope.','Door cuts and arches are not represented by solid envelope collision; use the frozen master for later actual geometry.','Dimensions come from continuous operations, not concept pixels.']}
 plan=json.loads((ROOT/'world_city/concept_city_v3/source/plan.json').read_text())
 group_keys={'castle':['ASSEMBLY_CASTLE'],'cathedral':['ASSEMBLY_CATHEDRAL'],'monastery':['ASSEMBLY_MONASTERY'],'civic_grain':['ASSEMBLY_TOWN_HALL','ASSEMBLY_GRAIN_HALL'],'port_cluster':[]}
 for group in groups:
  group['source_plan_assembly_group_keys']=group_keys[group['assembly_source']]
  group['suppress_blockout_building_ids']=[b['id'] for b in plan['buildings'] if b.get('assembly_group_id') in group['source_plan_assembly_group_keys']]
 result['current_source_plan']=ref('world_city/concept_city_v3/source/plan.json')
 write(HERE/'proxy_masses.json',result)
 print(json.dumps({'groups':len(groups),'masses':sum(len(g['masses']) for g in groups),'by_group':{g['id']:len(g['masses']) for g in groups}}))
 return result
if __name__=='__main__':build()
