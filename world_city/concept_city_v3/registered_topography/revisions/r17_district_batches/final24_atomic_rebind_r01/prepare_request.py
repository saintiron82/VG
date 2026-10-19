"""One matched final24 source request; unfinished profiles cannot be published."""
import json
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
FABRIC=a.CITY/'assemblies/ordinary/registered/district_fabric_r01'
SOURCE=a.HERE/'coherent_batch20_r01';B07=FABRIC/'b07_terrace_refit_r02/BLOCK_007';REPLACEMENTS=FABRIC/'final_source_preparation_r01/native_owner_replacements.json'
FILES={
'BLOCK_001:R8_C003':'final_private_wedge_refinement_r01/BLOCK_001_R8_C003.json',
'BLOCK_001:R8_C004':'final_district_profiles_r01/BLOCK_001_R8_C004.json',
'BLOCK_002:R8_C004':'incident_risers_r03/BLOCK_002_R8_C004.json',
'BLOCK_003:R8_C001':'final_district_profiles_r01/BLOCK_003_R8_C001.json',
'BLOCK_003:R8_C003':'final_district_profiles_r01/BLOCK_003_R8_C003.json',
'BLOCK_004:R8_C004':'final_grade_continuation_r01/BLOCK_004_R8_C004_15.json',
'BLOCK_004:R8_C006':'contour_bulk_r01/private_profiles_r02/PRIVATE_GROUP_BLOCK_004_R8_C006.json',
'BLOCK_005:R8_C003':'public_owner_completion_r10/BLOCK_005_R8_C003_12.json',
'BLOCK_005:R8_C008':'public_owner_completion_r09/BLOCK_005_R8_C008_15.json',
'BLOCK_005:R8_C006':'c006_dogleg_profile_r01/BLOCK_005_R8_C006.json',
'BLOCK_006:R8_C001':'final_district_profiles_r03/BLOCK_006_R8_C001.json',
'BLOCK_006:R8_C002':'contour_bulk_r01/private_profiles_r02/PRIVATE_GROUP_BLOCK_006_R8_C002.json',
'BLOCK_006:R8_C003':'incident_risers_r03/BLOCK_006_R8_C003.json',
'BLOCK_008:R8_C001':'final_district_profiles_r05/BLOCK_008_R8_C001.json',
'BLOCK_011:R8_C009':'entry_continuation_r01/source_refit_profiles_r02/BLOCK_011_R8_C009_0.json',
'BLOCK_017:R8_I004':'public_owner_completion_r02/BLOCK_017_R8_I004_profile.json',
'BLOCK_007:R8_C001':'final_b07_source_rebind_r01/BLOCK_007_R8_C001.json',
'BLOCK_007:R8_C002':'b07_private_profiles_r01/BLOCK_007_R8_C002.json',
'BLOCK_007:R8_C003':'b07_private_profiles_r01/BLOCK_007_R8_C003_datum.json',
'BLOCK_007:R8_C004':'b07_private_profiles_r01/BLOCK_007_R8_C004.json',
'BLOCK_007:R8_C005':'b07_private_profiles_r01/BLOCK_007_R8_C005_datum.json',
'BLOCK_007:R8_C006':'b07_private_profiles_r01/BLOCK_007_R8_C006.json',
'BLOCK_007:R8_C007':'b07_private_profiles_r01/BLOCK_007_R8_C007.json'}
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def nested_result(d):
 r=d['result']
 return r['result']if 'triangles'not in r and 'result'in r else r
def run():
 # A separate completed binding provides the last two; no pending placeholder
 # is accepted by this publishing operation.
 extra=json.loads((HERE/'last_two_selected_profiles.json').read_bytes());bindings={**FILES,**extra['profile_paths']};assert len(bindings)==24
 layout=json.loads((SOURCE/'effective_source_layout_r03.json').read_bytes());prep=json.loads((SOURCE/'effective_prepared_parcels_r03.json').read_bytes());b07=json.loads((B07/'selected_layout.json').read_bytes());b07hand=json.loads((B07/'terrain_handoff.json').read_bytes());holdings={h['id']:h for h in layout['holdings']+b07['holdings']};native=json.loads(REPLACEMENTS.read_bytes());replacements={r['holding_id']:r for r in native['records']};active=set()
 for folder in ['contour_bulk_r01','coherent_batch18_r01','coherent_batch20_r01']:active.update(json.loads((a.HERE/folder/'physical_owner_handoff_r02.json').read_bytes())['accepted_holding_ids'])
 selected=set(bindings);assert not selected&active;profiles={};changes=[];partitions={};selected_floors={};entry_refits={}
 for hid,path in sorted(bindings.items()):
  p=a.HERE/path;d=json.loads(p.read_bytes());r=nested_result(d);assert r['status']in ['PASSED_FINITE_TRIANGLE_GRADE','FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE'],(hid,r['status']);profiles[hid]=dict(kind='final_source_bound_finite_profile',**ref(p));floor=holdings[hid]['floor_y_m']
  if 'candidate'in d:
   c=d['candidate'];floor=c['floor_y_m'];entry_refits[hid]=dict(candidate_index=c['candidate_index'],source_candidate_batch=d['source'])
   if 'flat_owner_polygons_xz_m'in c:partitions[hid]={k:c[k]for k in ['flat_owner_polygons_xz_m','profile_domain_polygons_xz_m','surface_following_margin_polygons_xz_m','shared_inner_seams_xz_m']}
  for c in r.get('datum_changes',[]):
   if c['holding_id']==hid:floor=c['candidate_floor_y_m']
  selected_floors[hid]=floor
  if abs(floor-holdings[hid]['floor_y_m'])>1e-10:changes.append(dict(holding_id=hid,original_floor_y_m=holdings[hid]['floor_y_m'],candidate_floor_y_m=floor,delta_y_m=floor-holdings[hid]['floor_y_m'],baked_into_explicit_native_replacement=hid in replacements))
 retire=[r for r in prep['retirement_records']if set(r['affected_holding_ids'])&selected]
 assert all(set(r['affected_holding_ids'])<=selected|active for r in retire)
 retids=sorted({r['source_id']for r in retire}|set(b07hand['retired_source_ids']))
 out=dict(schema='riverstone.r17.atomic_final24_source_request.v1',status='FINITE_PROFILE_PASS_ATOMIC_NATIVE_REBIND_PENDING',source_layout=ref(SOURCE/'effective_source_layout_r03.json'),source_prepared_parcels=ref(SOURCE/'effective_prepared_parcels_r03.json'),source_native_pack=ref(SOURCE/'prepared_native_pack_r03.json'),b07_sources={k:ref(B07/v)for k,v in [('layout','selected_layout.json'),('terrain_handoff','terrain_handoff.json'),('native_pack','resolved_placements.json')]},explicit_eight_native_replacements=ref(REPLACEMENTS),matched_next_batch_holding_ids=sorted(selected),already_sealed_holding_ids=sorted(active),profile_bindings=profiles,selected_floor_y_m=selected_floors,datum_changes=changes,entry_refits=entry_refits,explicit_flat_profile_margin_partitions=partitions,exact_retirement_ids=retids,unchanged_neighbor_holding_ids=sorted(selected-set(entry_refits)-{r['holding_id']for r in changes}),b07_obsolete_pad_interpretation=ref(FABRIC/'b07_terrace_refit_r02/c006_retired_pad_interpretation.json'),profile_native_extensions=[ref(FABRIC/'final_pedestrian_step_skins_r01/native_step_handoff.json')],public_prerequisites=extra.get('public_prerequisites',[]),entry_route_supersessions=extra.get('entry_route_supersessions',[]),inherited_public_limitations=[ref(a.HERE/'water_public_precedence_review_r01/traffic_boundary_review.json')],scope='Atomic native, doorway, finite earth, profile and old ordinary retirement rebind. Explicit flat-core layouts do not flatten their logical holding margins. Unsupported unactivated enclosure claims are withdrawn as complete units. All actual routes require unchanged-controller replay.',activation=False)
 write(HERE/'atomic_final24_request.json',out);print(ref(HERE/'atomic_final24_request.json'));print('holdings',len(selected),'retirements',len(retids),'datum_changes',len(changes))
if __name__=='__main__':run()
