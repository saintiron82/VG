"""R2 orchestration: property/era choices before common-master cache generation.

No sampler, mesher or geometry scaling lives here. R1 resources remain immutable.
"""
from pathlib import Path
import collections,copy,hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
HERE=Path(__file__).parent
from world_city.runtime_city.assemble_city import seed,write,sha,palette,PROTECTED

ERA_MAP={'crossing_fort':'early','religious_precinct':'early','chartered_market':'early','river_trade':'rebuilt','market_rebuilding':'rebuilt','outer_infill':'late'}

def weighted(weights,key):
 u=(seed(key)%1000000)/1000000;total=sum(weights.values());v=0
 for item,w in weights.items():
  v+=w/total
  if u<v:return item
 return next(reversed(weights))

def cluster_key(i):
 # Property clusters tie adjacent plots to a shared growth period. They are not
 # a claim of exact historical lot boundaries, and individual repaired houses
 # remain possible through explicit exceptions rather than random cell colors.
 x,_,z=i['position_m'];return f"{i['district_id']}:{math.floor(x/96)}:{math.floor(z/96)}"

def choose_regular(i,oldspec,h):
 did=i['district_id'];cluster=cluster_key(i);rule=h['district_rules'][did]
 eras=copy.deepcopy(rule['era_mix'])
 if did not in ['D03','D04']:eras.pop('market_rebuilding',None)
 era=weighted(eras,cluster+':era');geometry_era=ERA_MAP[era]
 style=oldspec['style'];cls='regular_house';floors=oldspec['floors']
 is_annex=i['functional_role']=='rear_workshop_or_store'
 if is_annex:
  cls='stable' if did in ['D08','S01'] else 'regular_house';floors=1
 elif did=='D07' and seed(cluster+':tenure')%100<64:
  cls='poor_row';floors=1+(seed(cluster+':floors')%2)
 elif did=='S01' and seed(cluster+':tenure')%100<45:
  cls='servant_lodge';floors=1
 material=weighted(rule['roof']['material_weights'],cluster+':material')
 if style=='artisan' and geometry_era!='early':material='clay_red'
 if is_annex and geometry_era=='early':material='wood_brown'
 w,d=oldspec['width_m'],oldspec['depth_m']
 f=seed(cluster+':roof')%100
 if is_annex:form='shed' if d<=6 else 'gable'
 elif style=='garden' and w>=8 and f<42:form='hip'
 elif style=='merchant' and w>=12 and f<35:form='hip'
 elif w>=14 and f<75:form='twin_gable_z'
 else:form='gable'
 # Discrete functional pitches keep shared archetypes reusable; material is
 # not an excuse to produce a unique roof mesh for every color choice.
 pitch={'merchant':46,'old_timber':48,'port':38,'artisan':42,'garden':45,'institutional':50}[style]
 if cls in ['poor_row','servant_lodge']:pitch=44
 if form=='shed':pitch=26
 floorheight=2.5 if cls in ['poor_row','servant_lodge'] else 2.8 if style in ['old_timber','garden'] else 3.1
 spec={'family':'ordinary_r2','width_m':w,'depth_m':d,'floors':floors,'style':style,
       'assembly_class':cls,'roof_form':form,'roof_pitch_degrees':pitch,'floor_height_m':floorheight,
       'construction_era':geometry_era}
 return spec,era,cluster,material

def authored_metadata(master):
 m=master['metadata'];return m['envelope'],m['entrance']

def build_plan():
 from world_city.runtime_city.archetypes.ordinary_r2 import make_master
 base=json.loads((ROOT/'world_city/runtime_city/generated/r1/scene.json').read_text())
 h=json.loads((HERE/'city_history.r2.candidate.json').read_text())
 out=copy.deepcopy(base);out.pop('infrastructure',None)
 out['revision']='recovered_r2_property_landuse';out['status']='authoring_not_compiled_or_validated'
 out['catalog_complete']=False;out['assets']={};out['asset_specs']={};out['instances']=[]
 out['sources']['r1_scene_sha256']=sha(ROOT/'world_city/runtime_city/generated/r1/scene.json')
 out['sources']['history']='world_city/runtime_city/revisions/r2/city_history.r2.candidate.json'
 out['sources']['history_sha256']=sha(HERE/'city_history.r2.candidate.json')
 out['district_rules']=h['district_rules'];out['history_snapshot']=h
 out['open_space_policy']='explicit functional landuse with preserved route network and declared property consolidation'
 out['revision_provenance']={'original_building_ids':[i['id'] for i in base['instances']],
  'superseded_buildings':[],'added_buildings':[],'retained_protected_records':list(PROTECTED),
  'r1_source_layout_unchanged':True,'not_original_r4_mesh_restoration':True}
 for original in base['instances']:
  i=copy.deepcopy(original);oldspec=base['asset_specs'][i['asset_key']]
  if i['id'] in PROTECTED or oldspec['family']=='landmark':
   out['asset_specs'][i['asset_key']]=copy.deepcopy(oldspec)
   out['assets'][i['asset_key']]=copy.deepcopy(base['assets'][i['asset_key']])
   i['geometry_policy']='reuse_unchanged_r1_master'
   if i['id'] not in PROTECTED:
    material='slate_gray' if oldspec.get('kind') not in ['warehouse','monastery'] else 'clay_red'
    i['palette_override'].update(h['roof_material_families'][material]);i['palette_id']=material+'__approved_gray';i['roof_material_family']=material
   out['instances'].append(i);continue
  spec,era,cluster,material=choose_regular(i,oldspec,h)
  key='ordinary_r2_'+hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:14]
  spec['asset_id']=key
  if key not in out['asset_specs']:
   master=make_master({k:v for k,v in spec.items() if k!='family'})
   bounds,entry=authored_metadata(master)
   spec['derived_height_m']=bounds['max'][1]
   out['asset_specs'][key]=spec
  else:
   master=make_master({k:v for k,v in out['asset_specs'][key].items() if k not in ['family','derived_height_m']})
   bounds,entry=authored_metadata(master)
  i['asset_key']=key;i['era_id']=era;i['era_cluster']=cluster;i['construction_era']=spec['construction_era'];i['assembly_class']=spec['assembly_class']
  i['roof_material_family']=material;i['roof_pitch_degrees']=spec['roof_pitch_degrees'];i['local_bounds']=bounds
  i['height_delta_m']=round(bounds['max'][1]-i['source_height_candidate_m'],6)
  i['palette_override'].update(h['roof_material_families'][material]);i['palette_id']=material+'__'+i['palette_id'].split('__')[-1]
  local=entry['position'];c,s=math.cos(i['yaw_rad']),math.sin(i['yaw_rad']);p=i['position_m']
  i['entrance']['authored_local_position_m']=local;i['entrance']['position_m']=[p[0]+c*local[0]+s*local[2],p[1]+local[1],p[2]-s*local[0]+c*local[2]]
  i['all_entrances_local_m']=entry.get('all_positions',[local]);i['geometry_policy']='common_master_dimension_authored_r2';out['instances'].append(i)
 # Deliberate property consolidations replace source instances once, preserving
 # original v2 IDs and footprints in explicit provenance.
 fabric_path=ROOT/'world_city/runtime_city/urban_fabric/generated/urban_fabric.json'
 if fabric_path.exists():
  fabric=json.loads(fabric_path.read_text());by_id={i['id']:i for i in out['instances']}
  for ov in fabric['building_override_specs']:
   i=by_id[ov['id']];spec={'family':'ordinary_r2','width_m':ov['width_m'],'depth_m':ov['depth_m'],
    'floors':ov['floors'],'floor_height_m':ov['floor_height_m'],'roof_pitch_degrees':ov['roof_pitch_degrees'],
    'assembly_class':ov['assembly_class'],'construction_era':ERA_MAP[ov['era_id']],
    'style':ov.get('style','institutional' if ov['assembly_class'] in ['older_stone_manor','merchant_palazzo'] else 'old_timber')}
   if ov['assembly_class']=='poor_row':
    # Explicit sub-footprint fit: total integer dimensions put both exterior
    # faces on the .5m sampler grid, avoiding outward half-cell rounding.
    spec['width_m']=float(math.floor(spec['width_m']));spec['depth_m']=float(math.floor(spec['depth_m']))
   for optional in ['roof_form','attached_units']:
    if optional in ov:spec[optional]=ov[optional]
   key='ordinary_r2_'+hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:14];spec['asset_id']=key
   master=make_master({k:v for k,v in spec.items() if k!='family'});bounds,entry=authored_metadata(master)
   spec['derived_height_m']=bounds['max'][1];out['asset_specs'][key]=spec
   i['original_v2_footprint_xz_m']=copy.deepcopy(i['source_footprint_xz_m'])
   i['source_footprint_xz_m']=ov['footprint_xz_m'];i['source_footprint_revision']='r2_authorized_property_reparcel'
   i['position_m']=ov['position_m'];i['yaw_rad']=ov['yaw_rad'];i['asset_key']=key;i['local_bounds']=bounds
   i['override_geometry_fitting']='integer metre envelope inside planned property footprint for half-metre sampling' if ov['assembly_class']=='poor_row' else 'exact authored property envelope'
   i['property_id']=ov['property_id'];i['property_type']=ov['property_type'];i['assembly_class']=ov['assembly_class']
   i['era_id']=ov['era_id'];i['construction_era']=spec['construction_era'];i['era_cluster']=ov['property_id']
   material={'gray_slate':'slate_gray','brown_wood':'wood_brown','red_clay':'clay_red'}.get(ov['roof_material_family'],ov['roof_material_family'])
   i['roof_material_family']=material;i['palette_override'].update(h['roof_material_families'][material]);i['palette_id']=material+'__'+i['palette_id'].split('__')[-1]
   i['roof_pitch_degrees']=spec['roof_pitch_degrees'];i['height_delta_m']=bounds['max'][1]-i['source_height_candidate_m']
   e=ov['entrances'][0];local=entry['position'];c,s=math.cos(i['yaw_rad']),math.sin(i['yaw_rad']);p=i['position_m']
   i['entrance']={'position_m':[p[0]+c*local[0]+s*local[2],p[1]+local[1],p[2]-s*local[0]+c*local[2]],
    'authored_local_position_m':local,'road_id':e['road_id'],'road_connection_m':[e['road_connection_xz_m'][0],0,e['road_connection_xz_m'][1]],
    'status':'closed_exterior_door_approach_only','authored_access_polyline_xz_m':e['access_polyline_xz_m']}
   i['all_entrances_local_m']=entry.get('all_positions',[local]);i['reparcel_provenance']=ov['provenance']
   i['chunk_id']=f'{math.floor(p[0]/64)}_{math.floor(p[2]/64)}'
  used={i['asset_key'] for i in out['instances']};out['asset_specs']={k:v for k,v in out['asset_specs'].items() if k in used};out['assets']={k:v for k,v in out['assets'].items() if k in used}
  out['revision_provenance']['superseded_buildings']=fabric['source_building_supersessions']
  out['urban_fabric_source']='world_city/runtime_city/urban_fabric/generated/urban_fabric.json'
  out['urban_fabric_building_overrides_sha256']=hashlib.sha256(json.dumps(fabric['building_override_specs'],sort_keys=True).encode()).hexdigest()
 out['authoring_summary']={'building_instances':len(out['instances']),'unique_masters':len(out['asset_specs']),
  'roof_materials':dict(collections.Counter(i.get('roof_material_family','protected_r1') for i in out['instances'])),
  'assembly_classes':dict(collections.Counter(i.get('assembly_class','protected_or_landmark') for i in out['instances']))}
 return out

if __name__=='__main__':
 out=build_plan();write(HERE/'authoring_plan.base.json',out);print(json.dumps(out['authoring_summary'],indent=2))
