"""Collect source-backed local regression vectors; no final R18 route release claim."""
import pathlib,json,hashlib
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3'
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
 services=H.parent/'district_services_r03';north=H.parent/'north_connector_r02';rows=[]
 for folder,kind in[(services,'services'),(north,'north')]:
  prepared=folder/'prepared_runtime.json';d=read(prepared)
  for r in d['routes']:
   if r['id'].endswith('_REVERSE')or r['id']in{'NEGATIVE_UNBRIDGED_RIVER','NEGATIVE_ACTUAL_SOLID_WALL'}:continue
   negative=bool(r.get('expected_failure'))
   if kind=='services':
    cls={'canal_crossing':'canal_crossing','local_crossing_network':'junction_turn','common_entry':'common_entry','bridge_rail_negative':'blocked_native_negative','common_wall_negative':'blocked_native_negative'}[r['case_class']]
   else:cls='water_edge_negative'if r.get('expected_failure')=='ground_lost'else'secured_bridge_negative'if r['id'].startswith('NEGATIVE_SECURED')else'blocked_native_negative'if negative else'native_bridge'if r['id']=='BRIDGE_CLOSED_LEAF_HINGE'else'bridge_approach'
   row=dict(id=r['id'],case_class=cls,points_xyz_m=r['points'],source_road_ids=r['source_road_ids'],test_scope=r['test_scope'],provenance=[ref(prepared),ref(folder/'freeze_manifest.json')],bidirectional=not negative)
   for key in['expected_failure','expected_contact_id','expected_contact_prefix','minimum_allowed_feet_y_m','bridge_state','bridge_id','lane_offset_m','lane_fraction']:
    if key in r:row[key]=r[key]
   if not negative:row['resolved_geometry_proof']=ref(prepared)
   row['activation_condition']='Final scene must include these exact native/field interfaces; actual final-scene replay remains required.'
   rows.append(row)
 out=dict(schema='riverstone.bound_public_local_controls.r18.v1',status='SOURCE_BACKED_SUPPLEMENTAL_CONTROLS_PENDING_JOINT_SCENE',sources=dict(services=ref(services/'prepared_runtime.json'),north=ref(north/'prepared_runtime.json')),routes=rows,expanded_case_count=sum(2 if r['bidirectional']else 1 for r in rows),limits=['These controls supplement resolved canonical R18 road/junction routes; they do not replace them.','Common outer lane reverse remains a known failure until the canonical public terminal field is activated.','Original failed evidence and the two isolated fixture controls remain separately retained.'])
 with(H/'bound_local_controls.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print('BOUND_LOCAL_CONTROLS',len(rows),'expanded',out['expanded_case_count'])
if __name__=='__main__':main()
