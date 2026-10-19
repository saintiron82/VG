"""Immutable four-profile continuation of the complete matched final23 source."""
import json
from pathlib import Path
from .. import author as a
from ..coherent_final24_r01.prepare import ref,load
from ..final24_atomic_rebind_r01.prepare_request import nested_result
HERE=Path(__file__).resolve().parent;PRIOR=HERE.parent/'coherent_final24_r01';REQUEST=HERE/'accepted_source_request.json'
def write(name,value):
 p=HERE/name;assert not p.exists(),str(p);p.write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n')
def run():
 request=json.loads((HERE.parent/'final24_atomic_rebind_r01/completed_request_r01.json').read_bytes());new=HERE.parent/'final_incidental_public_r01';files={'BLOCK_003:R8_C001':'BLOCK_003_R8_C001_incidents_12.json','BLOCK_006:R8_C001':'BLOCK_006_R8_C001_incidents_12.json','BLOCK_008:R8_C001':'BLOCK_008_R8_C001_12.json','BLOCK_004:R8_C004':'BLOCK_004_R8_C004_rebound_15.json'}
 for h,n in files.items():request['profile_bindings'][h]=ref(new/n)
 extension=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/final_b04_entry_clearance_r01/source_candidates.json';c=json.loads(extension.read_bytes())['records'][0];hid=c['holding_id'];request['explicit_flat_profile_margin_partitions'][hid]={k:c[k]for k in request['explicit_flat_profile_margin_partitions'][hid]};request['finite_approach_continuation']=dict(prior_request=ref(HERE.parent/'final24_atomic_rebind_r01/completed_request_r01.json'),changed_profile_ids=sorted(files),source_route_addendum=ref(extension),court_native_pose_changes=0,reason='Exact current public fringe and one adjacent native footing are preserved.');request['step_collision_contract']=ref(a.CITY/'assemblies/ordinary/registered/district_fabric_r01/final_pedestrian_step_skins_r01/collision_r01/collision_contract.json');request['public_prerequisites'].append(ref(a.CITY/'registered_topography/revisions/public_corridors_r18/b17_local_alley_r01/scene_patch.json'));request['current_main_binding']=ref(a.CITY/'registered_integration/r8/final_exterior_candidate_r01/noble_cap_bridge_binding.json');write('accepted_source_request.json',request)
 for name in ['input_binding.json','atomic_rebind_binding_r01.json','prepared_native_pack_r03.json','effective_prepared_parcels_r03.json','effective_source_layout_r03.json','current_native_neighbors_r01.json','side_context_binding.json']:
  obj=json.loads((PRIOR/name).read_bytes())
  if name=='effective_source_layout_r03.json':
   for h in obj['holdings']:
    if h['id']==hid:
     h['external_route']=c['polyline_xz_m'];h['external_route_polygons_xz_m']=c['external_route_polygons_xz_m'];h['profile_domain_polygons_xz_m']=c['profile_domain_polygons_xz_m'];h['source_route_continuation']=ref(extension)
  if name=='effective_prepared_parcels_r03.json':
   for p in obj['parcels']:
    if p['id']==hid:p['profile_domain_polygons_xz_m']=c['profile_domain_polygons_xz_m'];p['selected_external_profile']=request['profile_bindings'][hid]
  if name=='atomic_rebind_binding_r01.json':obj['finite_approach_continuation']=request['finite_approach_continuation'];obj['step_collision_contract']=request['step_collision_contract']
  write(name,obj)
 (HERE/'profiles').mkdir();rows=[];public=[]
 for hid,binding in request['profile_bindings'].items():
  original=load(binding);result=dict(nested_result(original));assert result['status'] in ('PASSED_FINITE_TRIANGLE_GRADE','FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE');result['status']='PASSED_FINITE_TRIANGLE_GRADE';result['grade_limit']=original.get('grade_limit',result.get('grade_limit',.12));fixed=[dict(r,plane_y_xz_m=[0,0,request['selected_floor_y_m'][hid]])for r in original.get('court_fixed_regions',[])];record=dict(original,id='PRIVATE_GROUP:'+hid,holding_ids=[hid],result=result,court_fixed_regions=fixed,source_profile=binding,activation=False)
  if 'vertical_risers'not in record:record['vertical_risers']=original['result'].get('vertical_risers',[])
  name='profiles/'+hid.replace(':','_')+'.json';write(name,record);rows.append(dict(id=record['id'],holding_ids=[hid],status='PASSED_FINITE_TRIANGLE_GRADE',**ref(HERE/name)));public.extend(record['public_fixed_regions'])
 write('private_profiles_summary_r02.json',dict(groups=rows,source_request=ref(REQUEST),activation=False));write('resolved_public_inputs_r01.json',dict(public_fixed_regions=public,source_request=ref(REQUEST),public_prerequisites=request['public_prerequisites']));print('Prepared exact four-profile continuation',flush=True)
if __name__=='__main__':run()
