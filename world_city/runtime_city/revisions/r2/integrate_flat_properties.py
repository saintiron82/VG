"""Bind compiled property geometry to a separate flat visual staging scene."""
from pathlib import Path
import copy,json,math,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT));OUT=ROOT/'world_city/runtime_city/generated/r2'
from world_city.runtime_city.assemble_city import write,sha
from world_city.runtime_city.checks.placement import validate_placements,transform_point_m

def main():
 s=json.loads((OUT/'scene.buildings.json').read_text());f=json.loads((OUT/'urban_fabric.json').read_text())
 plan=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text());effective=copy.deepcopy(plan)
 fsrc=json.loads((ROOT/'world_city/runtime_city/urban_fabric/generated/urban_fabric.json').read_text())
 assert f['compiled_source_sha256']==sha(ROOT/'world_city/runtime_city/urban_fabric/generated/urban_fabric.json')
 ids={b['id']:b for b in effective['building_plans']}
 for o in fsrc['building_override_specs']:
  b=ids[o['id']];b['footprint_xz_m']=o['footprint_xz_m'];b['entrance']['position_xz_m']=o['entrances'][0]['position_xz_m']
  b['road_access']['road_id']=o['entrances'][0]['road_id'];b['road_access']['connection_xz_m']=o['entrances'][0]['road_connection_xz_m']
 for p in effective['plots']:
  if p['id'] in fsrc['repurposed_courtyard_plot_ids']:
   p['original_v2_courtyard_xz_m']=p.get('courtyard_xz_m');p['courtyard_xz_m']=None;p['status']='r2_documented_functional_reparcel_with_explicit_access'
 for i in s['instances']:
  asset=s['assets'][i['asset_key']]['coarse'];m=asset.get('author_metadata',{})
  ent=m.get('entrance',{})
  if not ent and asset.get('author_extensions',{}).get('entrances'):ent={'position':asset['author_extensions']['entrances'][0]['threshold_local_m']}
  if ent.get('position') is None:raise ValueError(('missing authored entrance',i['id']))
  local=ent['position'];e=i['entrance'];e['local_position_m']=local;e['authored_local_position_m']=local
  e['facade_inset_m']=i['local_bounds']['max'][2]-local[2];e['position_m']=transform_point_m(local,i['position_m'],i['yaw_rad']);e['author_metadata_verified']=True
  i['all_entrances_local_m']=ent.get('all_positions',[local]);i['all_entrances_world_m']=[transform_point_m(p,i['position_m'],i['yaw_rad']) for p in i['all_entrances_local_m']]
 inf=copy.deepcopy(json.loads((ROOT/'world_city/runtime_city/generated/r1/infrastructure.json').read_text()))
 assert not set(inf['assets']).intersection(f['assets'])
 inf['assets'].update(f['assets']);inf['placements'].extend(f['placements']);s['infrastructure']=inf
 s['urban_fabric_summary']=f['coverage'];s['urban_property_records']=f['properties'];s['vegetation_land_use']=f['vegetation_land_use']
 s['urban_fabric_source_sha256']=f['compiled_source_sha256'];s['urban_fabric_layer_scope']='flat property staging; grade layer not integrated'
 s['status']='compiled_flat_property_staging_pending_independent_all_door_audit'
 s['terrain_grade_policy']='flat staging only; graded layer is separate and not yet integrated'
 s['camera_scope']='flat property comparison; not graded-city completion'
 report=validate_placements(s,effective)
 report['source_revision_scope']='r2 effective property plan; exactly17documented re-parcels, original v2 bytes untouched'
 report['original_brief_sha256']=sha(ROOT/'world_city/data/city_brief.v2.json');report['override_ledger']=f['source_building_supersessions']
 write(OUT/'effective_plan.json',effective);write(OUT/'scene.flat_property.json',s);write(ROOT/'world_city/runtime_city/evidence/r2_flat_placement.json',report)
 print(json.dumps({'passed':report['passed'],'failures':report['failures'],'unverified':report['unverified'],'buildings':len(s['instances']),'infra_and_fabric':len(inf['placements'])},ensure_ascii=False,indent=2))
 return int(not report['passed'])
if __name__=='__main__':raise SystemExit(main())
