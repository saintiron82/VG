"""Bind current actual neighboring owners without promoting un-emitted fields."""
import json
from .prepare import HERE,ref,load,write
from .. import author as a

def run():
 root=a.ROOT/'world_city/concept_city_v3';pub=root/'registered_topography/revisions/public_corridors_r18';noble=root/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02'
 rows=[];sources=[]
 audit=json.loads((noble/'physical_profile_audit.json').read_bytes());sources.append(ref(noble/'physical_profile_audit.json'))
 for owner in audit['owners']:
  source=owner['physical_top'];data=load(source);sources.append(source)
  for i,row in enumerate(data['top_pieces']):rows.append(dict(row,id=f"CURRENT_NOBLE_R02:{owner['owner_id']}:PHYSICAL:{i}",source=source,kind='actual_native_physical_top'))
 collars=json.loads((noble/'private_collars.json').read_bytes());sources.append(ref(noble/'private_collars.json'))
 rows.extend(collars['owners'])
 native=json.loads((noble/'native_ground_candidate_audit.json').read_bytes());sources.append(ref(noble/'native_ground_candidate_audit.json'))
 rows.extend(native['retained_base_upward_faces'])
 write('current_native_neighbors_r01.json',dict(schema='r17.actual_noble_neighbor_snapshot.v1',sources=sources,all_noble_physical_owners=rows,accepted_adjacent_physical_owners=[],policy='Actual R02 collision tops, emitted finite collars and retained base native tops only. Un-emitted private_field_pieces are excluded.'))
 write('side_context_binding.json',dict(current_scene=ref(root/'evidence/r8_district_61_noble_r02_contracts_runtime/authored_scene.json'),public_field=ref(pub/'finite_field_candidate_r07_native_bound.json'),native_boundary_owners=ref(HERE/'current_native_neighbors_r01.json'),public_local_corrections=[ref(pub/'north_junction_transition_r01/physical_owners.json'),ref(pub/'b17_local_alley_r01/physical_owners.json')],accepted_private_handoffs=[ref(a.HERE/p/'physical_owner_handoff_r02.json')for p in ['contour_bulk_r01','coherent_batch18_r01','coherent_batch20_r01']],current_main_binding=ref(root/'registered_integration/r8/final_exterior_candidate_r01/public_remnants_binding.json')))
 print('Bound',len(rows),'actual noble neighboring planes',flush=True)
if __name__=='__main__':run()
