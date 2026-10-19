"""Read-only source audit; writes derived reports only into this directory."""
import json, pathlib, collections, hashlib, csv
ROOT=pathlib.Path(__file__).resolve().parents[5]
OUT=pathlib.Path(__file__).resolve().parent
scene=json.load(open(OUT/'selected_scene_metadata.json'))
assets=json.load(open(OUT/'selected_asset_metadata.json'))
plan=json.load(open(ROOT/'world_city/concept_city_v3/registered_source/plan.json'))
plan_ids={b['id']:b for b in plan['buildings']}
cache={}
def meta_for(key):
 if key in cache:return cache[key]
 if key in assets:
  m=assets[key]['metadata'];path=assets[key]['path']
 else:
  paths=[ROOT/'world_city/runtime_city/generated/r2/masters'/f'{key}.json',ROOT/'world_city/concept_city_v3/assemblies/property/cache'/f'{key}.master.json']
  path=next((p for p in paths if p.exists()),None)
  if path is None:raise RuntimeError('Missing native module '+key)
  m=json.load(open(path)).get('metadata',{})
 cache[key]=(m,str(path));return cache[key]
def leaves(key,trail=()):
 m,path=meta_for(key)
 if m.get('modules'):
  for x in m['modules']:
   yield x['asset_key'], x['metadata'], x['source']['path'], trail+(x['id'],)
 elif m.get('native_modules'):
  for j,x in enumerate(m['native_modules']):yield from leaves(x['asset_key'],trail+(str(j),))
 elif m.get('floors'):yield key,m,path,trail

def category(ins, key, m, trail):
 fn=plan_ids.get(ins['id'],{}).get('function','')
 cls=m.get('assembly_class','regular_house');style=m.get('style',''); tag=' '.join(trail)
 if ins['id']=='TRAIN:stores' or any(t in tag.split() for t in ['bakehouse','kitchen','stores','fruit_store','tools','seed_store','records_house','kitchen_service','laundry','workshop','store']) or cls=='stable' or style=='port' or fn in ('noble_stable','noble_kitchen','port_warehouse_and_loading'):return 'work_or_storage'
 if cls=='poor_row' or cls=='servant_lodge' or any(t.startswith('canon_') or t in ['lay_workers','gardeners','service_dwelling','porter'] for t in tag.split()):return 'lodging'
 if fn=='noble_main_hall' or cls in ('older_stone_manor','merchant_palazzo','timber_courtyard_house'):return 'elite_residence_or_service_uncertain'
 if m['floors']==1 and any(x in tag for x in ['repair','workshop','joinery','craft']):return 'work_or_storage'
 if fn=='barracks_and_training_store':return 'institutional_uncertain'
 return 'mixed_house'
rows=[];represented=set();summary={}
for ins in scene['common_instances']:
 children=list(leaves(ins['asset_key']))
 if children:represented.add(ins['id'])
 for key,m,path,trail in children:
  bb=m['body_bounds'];area=(bb['max'][0]-bb['min'][0])*(bb['max'][2]-bb['min'][2]);floors=m['floors'];cat=category(ins,key,m,trail)
  # Scenarios are author assumptions, not historical ratios or measured net interiors.
  if cat=='lodging': low_factor,high_factor=.65,.85
  elif cat=='mixed_house':low_factor,high_factor=.65*max(0,floors-1)/floors,.85*(max(0,floors-1)+.3)/floors
  else:low_factor,high_factor=0,0
  rows.append(dict(instance_id=ins['id'],source_pack=ins.get('source_pack'),asset_key=ins['asset_key'],leaf_asset_key=key,leaf_role='/'.join(trail),category=cat,assembly_class=m.get('assembly_class','regular_house'),style=m.get('style'),floors=floors,row_units=m.get('row_units',1),body_footprint_m2=area,gross_shell_floor_area_m2=area*floors,residential_net_low_m2=area*floors*low_factor,residential_net_high_m2=area*floors*high_factor,source_master=path,registered_plan_function=plan_ids.get(ins['id'],{}).get('function')))
for cat in sorted(set(r['category'] for r in rows)):
 r=[x for x in rows if x['category']==cat]
 summary[cat]={'native_leaf_building_modules':len(r),'row_frontage_units_not_households':sum(x['row_units'] for x in r),'body_footprint_sum_m2':sum(x['body_footprint_m2'] for x in r),'gross_shell_floor_area_m2':sum(x['gross_shell_floor_area_m2'] for x in r),'net_residential_assumption_low_m2':sum(x['residential_net_low_m2'] for x in r),'net_residential_assumption_high_m2':sum(x['residential_net_high_m2'] for x in r)}
poly=plan['wall_registration']['polygon_xz_m'];area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2
result={'wall_polygon_area_m2':area,'registered_plan_buildings':len(plan['buildings']),'registered_plan_plots':len(plan['plots']),'selected_native_instances':len(scene['common_instances']),'unique_selected_instance_ids':len(set(i['id'] for i in scene['common_instances'])),'selected_instances_matching_original_plan_building_id':len(set(i['id'] for i in scene['common_instances'])&set(plan_ids)),'selected_instances_with_ordinary_building_metadata':len(represented),'decomposed_native_building_modules':len(rows),'categories':summary,'residential_net_assumption_low_m2':sum(x['residential_net_low_m2'] for x in rows),'residential_net_assumption_high_m2':sum(x['residential_net_high_m2'] for x in rows),'explicit_limit':'Not complete census: institutional shell masters without ordinary floors metadata are unquantified; residential allocation and floor internal partitions are not authored/verified. Leaf and row units are geometry counts, not households.'}
(OUT/'population_geometry_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(OUT/'building_module_ledger.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
with open(OUT/'building_module_ledger.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(json.dumps(result,indent=2))
