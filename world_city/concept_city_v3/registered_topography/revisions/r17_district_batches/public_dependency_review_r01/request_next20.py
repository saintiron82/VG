"""One atomic source rebind request for the next complete retirement set."""
import json
from .review import HERE,OLD,write
from .. import author as a
CONT=HERE.parent/'entry_continuation_r01'

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def run():
 active=set()
 for folder in ('contour_bulk_r01','coherent_batch18_r01'):
  active.update(json.loads((HERE.parent/folder/'physical_owner_handoff_r02.json').read_bytes())['accepted_holding_ids'])
 profiles={};changes=[];refits={};ready=set()
 for r in json.loads((CONT/'source_refit_profile_summary_r01.json').read_bytes())['rows']:
  if r['selected_candidate_index']is None:continue
  q=next(t for t in r['trials']if t['candidate_index']==r['selected_candidate_index']);hid=r['holding_id'];ready.add(hid);profiles[hid]=dict(kind='selected_source_entry_refit',**ref(a.ROOT/q['path']));refits[hid]=dict(candidate_index=r['selected_candidate_index'],source_candidate_batch=ref(a.CITY/'assemblies/ordinary/registered/district_fabric_r01/held_private_entry_refit_r01/source_candidate_batch.json'))
 for r in json.loads((HERE/'private_boundary_summary_r01.json').read_bytes())['rows']:
  if r['status']=='PASSED_FINITE_TRIANGLE_GRADE':
   for h in r['holding_ids']:
    if h=='BLOCK_017:R8_I004':continue
    ready.add(h);profiles[h]=dict(kind='current_r04_private_boundary_profile',**ref(a.ROOT/r['path']))
 for fname in ('datum_summary_r01.json','datum_summary_r02.json'):
  for r in json.loads((HERE/fname).read_bytes())['rows']:
   if r['status']=='FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE':
    changes.extend(r['datum_changes'])
    for h in r['holding_ids']:ready.add(h);profiles[h]=dict(kind='current_r04_coherent_datum_profile',**ref(a.ROOT/r['path']))
 for r in json.loads((OLD/'private_profiles_summary_r02.json').read_bytes())['groups']:
  if r['status']=='PASSED_FINITE_TRIANGLE_GRADE':
   for h in r['holding_ids']:
    if h not in active and h not in ready:ready.add(h);profiles[h]=dict(kind='previously_ready_retirement_neighbor',**ref(a.ROOT/r['path']))
 prepared=json.loads((OLD/'effective_prepared_parcels_r03.json').read_bytes());ret=prepared['retirement_records'];excluded=set()
 while True:
  bad={h for r in ret if set(r['affected_holding_ids'])&(ready-excluded)and not set(r['affected_holding_ids'])<=(active|ready-excluded)for h in r['affected_holding_ids']if h in ready-excluded}
  if not bad:break
  excluded|=bad
 selected=ready-excluded;assert len(selected)==20;selected_ret=[r['source_id']for r in ret if set(r['affected_holding_ids'])&selected];datum_ids={r['holding_id']for r in changes};assert datum_ids<=selected
 out=dict(schema='riverstone.r17.atomic_next20_source_request.v1',status='FINITE_PRIVATE_PROFILE_PASS_ATOMIC_NATIVE_REBIND_PENDING',source_layout=ref(OLD/'effective_source_layout_r03.json'),source_prepared_parcels=ref(OLD/'effective_prepared_parcels_r03.json'),source_current_public_inputs=ref(HERE/'actual_public_inputs_r01.json'),matched_next_batch_holding_ids=sorted(selected),already_sealed_holding_ids=sorted(active),datum_changes=changes,entry_refits=refits,unchanged_neighbor_holding_ids=sorted(selected-datum_ids-set(refits)),profile_bindings={h:profiles[h]for h in sorted(selected)},exact_retirement_ids=sorted(selected_ret),retirement_dependency_holds=sorted(excluded),inherited_public_limitations={r['holding_id']:dict(maximum_gradient=r['maximum_inherited_public_gradient'],height_seam_count=len(r['inherited_public_height_seams']),height_seam_maximum_m=max((s['maximum_height_error_m']for s in r['inherited_public_height_seams']),default=0))for r in json.loads((HERE/'actual_public_inputs_r01.json').read_bytes())['entries']if r['holding_id']in selected},scope='Full native/door/bearing/court metadata must rebind atomically. Seven gate/circulation changes use alternative 0; four court datums change; nine neighbors retain source poses. Existing public geometry remains exact. Actual route replay and joint-side ownership remain pending.',whole78_counts=dict(already_sealed_source_ready=41,next20_source_candidates=20,remaining=17),activation=False)
 write(HERE/'next20_atomic_rebind_request_r01.json',out);print(ref(HERE/'next20_atomic_rebind_request_r01.json'));print('retirements',len(selected_ret))
if __name__=='__main__':run()
