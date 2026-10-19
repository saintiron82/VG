"""Bounded, read-only final-scene native activation and ordinary-land ledger.

No ledger is emitted without an explicit final manifest/scene pair and exact
hashes. Terrain support, traversal and rendered evidence remain separate gates.
"""
from . import geometry as g
from .rebind_coherent_datums import require
from collections import Counter,defaultdict
from pathlib import Path
import argparse,copy,math,time
FINAL=g.HERE/'final24_source_addendum_r01/atomic_source_addendum.json'
FINAL_SHA='ef9ad01b583d26c7fdbe19f7d90f2247e9391b317dd6aa563e4126e010687f76'
PRIOR=g.HERE/'city_completion_ledger_r04/completion_ledger.json'
WITHDRAW=g.HERE/'b08_market_hall_withdrawal_r01/handoff.json'
WITHDRAW_SHA='ab746d2a9fc2c792498510ad07b66938626a9cbca8ef32dafaee11e99e72cca9'
OUT=g.HERE/'city_activation_ledger_r01'

def references(obj):
 if isinstance(obj,dict):
  if isinstance(obj.get('path'),str)and isinstance(obj.get('sha256'),str):yield dict(path=obj['path'],sha256=obj['sha256'])
  for v in obj.values():yield from references(v)
 elif isinstance(obj,list):
  for v in obj:yield from references(v)

def expected_sources():
 prior=g.load(PRIOR);groups=[]
 for label,ref in [('B15',prior['source_references']['B15_release'])]+[(f'private_release_{i}',x)for i,x in enumerate(prior['source_references']['private_release_contracts'],1)]:
  contract=require(ref);pack=require(contract['native_pack']);ids=contract.get('accepted_holding_ids')or sorted({p['holding_id']for p in pack['placements']});groups.append(dict(label=label,contract=ref,pack_ref=contract['native_pack'],pack=pack,holding_ids=ids))
 assert sum(len(q['holding_ids'])for q in groups)==87
 assert g.ref(FINAL)['sha256']==FINAL_SHA and g.ref(WITHDRAW)['sha256']==WITHDRAW_SHA
 final=g.load(FINAL);groups.append(dict(label='final23',pack_ref=g.ref(FINAL),pack=final,holding_ids=final['matched_next_batch_holding_ids']))
 for i,ref in enumerate(final['profile_native_extensions']):groups.append(dict(label=f'profile_extension_{i}',pack_ref=ref,pack=require(ref),holding_ids=[]))
 backref=prior['source_references']['backland_native'];back=require(backref);groups.append(dict(label='backland835',pack_ref=backref,pack=back,holding_ids=[]));assert len(back['placements'])==835
 oldback=require(back['sealed_source']);deferredback=sorted({p['id']for p in oldback['placements']}-{p['id']for p in back['placements']});assert len(deferredback)==68
 ids=[p['id']for q in groups for p in q['pack']['placements']];holds=[h for q in groups for h in q['holding_ids']];assert len(ids)==len(set(ids)) and len(holds)==len(set(holds))==110
 return prior,final,g.load(WITHDRAW),groups,deferredback

def compare_pose(expected,actual,assets,source_assets):
 failures=[]
 for k in ['asset_key','position_m','yaw_rad','scale']:
  if actual.get(k)!=expected.get(k):failures.append(k)
 for k in ['palette_id','palette_override']:
  e=expected.get(k,{} if k=='palette_override'else None);v=actual.get(k,{} if k=='palette_override'else None)
  if e!=v:failures.append(k)
 key=expected['asset_key'];source=source_assets[key];active=assets.get(actual.get('asset_key'),{})
 if active.get('render_sha256')!=source.get('render_sha256'):failures.append('render_sha256')
 if active.get('master_sha256')!=source.get('master_sha256'):failures.append('master_sha256')
 return failures

def inspect(scene,groups,withdrawal,deferredback,final):
 common=scene['common_instances'];counts=Counter(p['id']for p in common);actual={p['id']:p for p in common};boxes={p['id']for p in scene.get('boxes',[])};rows=[];expectedids=[];retired=set();retired_groups={};source_assets=[];holding_rows=[]
 for group in groups:
  pack=group['pack'];missing=[];different=[]
  for p in pack['placements']:
   expectedids.append(p['id'])
   if counts[p['id']]!=1:missing.append(dict(id=p['id'],actual_count=counts[p['id']]))
   elif (errors:=compare_pose(p,actual[p['id']],scene['common_assets'],pack['assets'])):different.append(dict(id=p['id'],differing_fields=errors))
  old=set(pack.get('retired_source_ids',pack.get('replaced_placement_ids',[])));retired.update(old);retired_groups[group['label']]=sorted(old)
  rows.append(dict(label=group['label'],source=group['pack_ref'],expected_placements=len(pack['placements']),missing_or_duplicate=missing,pose_asset_palette_mismatches=different,passes=not missing and not different))
  source_assets += list(pack['assets'].values())
  for hid in group['holding_ids']:
   owned=[p['id']for p in pack['placements']if p.get('holding_id')==hid];holding_rows.append(dict(id=hid,block_id=hid.split(':')[0]if hid.startswith('BLOCK_')else'BLOCK_015',source_group=group['label'],native_placement_ids=owned,all_native_placements_present_once=all(counts[i]==1 for i in owned),implementation_tier='exterior_only'))
 cachechecks=[];seen=set()
 for ass in source_assets:
  for pathkey,hashkey in [('render_path','render_sha256'),('master_path','master_sha256')]:
   if pathkey not in ass:continue
   pair=(ass[pathkey],ass[hashkey])
   if pair in seen:continue
   seen.add(pair);cachechecks.append(dict(path=pair[0],expected_sha256=pair[1],passes=g.ref(g.ROOT/pair[0])['sha256']==pair[1]))
 deferred=[p['id']for p in final['explicit_deferred_source_placements']]+withdrawal['withdrawn_unactivated_native_ids']+deferredback
 forbidden=sorted(set(deferred)&set(actual));oldpresent=sorted(retired&set(actual));oldboxes=sorted({i+':owned_foundation'for i in retired}&boxes);hall=withdrawal['actual_retained_hall'];hallerrors=['absent_or_duplicate']if counts[hall['id']]!=1 else compare_pose(hall,actual[hall['id']],scene['common_assets'],{hall['asset_key']:withdrawal['retained_hall_asset']})
 checks=dict(expected_native_ids_unique=len(expectedids)==len(set(expectedids)),scene_native_ids_unique=len(counts)==len(common),all_expected_native_instances_exact=all(r['passes']for r in rows),all_source_cache_and_master_bytes_match=all(r['passes']for r in cachechecks),all_prior87_plus_final23_holdings_counted_once=len(holding_rows)==len({r['id']for r in holding_rows})==110,all_backland835_selected_once=next(r['passes']and r['expected_placements']==835 for r in rows if r['label']=='backland835'),all_retired_old_native_absent=not oldpresent,all_retired_foundation_proxies_absent=not oldboxes,all_explicitly_deferred_native_absent=not forbidden,retained_market_hall_exact=not hallerrors,withdrawal960_square_metres_accounted=withdrawal['passed']and abs(withdrawal['summary']['affected_holding_area_m2']-960)<1e-7,withdrawn_B008_not_counted_as_new_holding=all(r['id']!='BLOCK_008:R8_C003'for r in holding_rows),final69_retirements_exact=len(retired_groups['final23'])==69)
 return dict(checks=checks,passed=all(checks.values()),native_groups=rows,holding_rows=holding_rows,source_cache_checks=cachechecks,retirement_groups=retired_groups,unexpected_retained_old_native_ids=oldpresent,unexpected_retained_foundation_proxy_ids=oldboxes,unexpected_deferred_native_ids=forbidden,retained_hall_mismatches=hallerrors,summary=dict(adopted_holdings=110,prior_adopted_holdings=87,final_adopted_holdings=23,accounted_superseded_domains=1,expected_distinct_native_parts_and_assemblies=len(expectedids),selected_backland_native_instances=835,final_ordinary_native_instances=214,approved_profile_native_step_instances=1,all_explicit_old_native_retirements=len(retired),final_old_native_retirements=69,unresolved_ordinary_source_designs=0))

def run(manifest_path,manifest_sha,scene_path,scene_sha):
 start=time.monotonic();mp=g.ROOT/manifest_path if not manifest_path.is_absolute()else manifest_path;sp=g.ROOT/scene_path if not scene_path.is_absolute()else scene_path;assert g.ref(mp)['sha256']==manifest_sha;assert g.ref(sp)['sha256']==scene_sha
 manifest=g.load(mp);sr=g.ref(sp);assert sr in list(references(manifest)), 'Final manifest does not bind the supplied exact scene.'
 assert not OUT.exists(),'Never overwrite a prior exact-scene activation ledger; choose a new version.'
 prior,final,withdrawal,groups,deferredback=expected_sources();scene=g.load(sp);audit=inspect(scene,groups,withdrawal,deferredback,final)
 ledger=copy.deepcopy(prior);ledger.update(schema='riverstone.ordinary_city.exact_scene_activation_ledger.v1',status='EXACT_NATIVE_ACTIVATION_PASS_TERRAIN_AND_RUNTIME_AUDITS_SEPARATE'if audit['passed']else'HELD_NATIVE_ACTIVATION_MISMATCH',actual_final_manifest=g.ref(mp),actual_final_scene=sr,activation_audit=audit,final23_source=g.ref(FINAL),superseded_domain_handoffs=[g.ref(WITHDRAW)],source_counting_policy='110 adopted whole holdings; one960m² unbuilt B008 proposal explicitly superseded by existing protected hall/service ground. Native instances are parts and assemblies, never a building count.')
 ledger['source_references'].update(prior_r04_ledger=g.ref(PRIOR),final23_source=g.ref(FINAL),withdrawal=g.ref(WITHDRAW),author=g.ref(__file__))
 ledger['summary']['prior_r04_sealed_ordinary_holdings_total']=ledger['summary'].pop('sealed_ordinary_holdings_total')
 ledger['summary']['prior_r04_sealed_private_holdings']=ledger['summary'].pop('sealed_private_holdings')
 ledger['summary']['inherited_material_area_status']='R04 source accounting only; final material activation quantities remain owned by the supplied integration manifest.'
 ledger['summary'].update(audit['summary'],native_activation_passed=audit['passed'],remaining_building_and_entry_source_queue=0,remaining_private_holdings=0,separate_B07_holdings=0,physically_accounted_source_holdings=110)
 for block in ledger['blocks']:
  bid=block['block_id'];block['prior_pending_private_source_provenance']=block.pop('remaining_private17_holdings');block['prior_pending_B07_source_provenance']=block.pop('separate_B07_refit_holdings');block['actual_adopted_holding_ids']=[r['id']for r in audit['holding_rows']if r['block_id']==bid];block['actual_final23_holding_ids']=[r['id']for r in audit['holding_rows']if r['block_id']==bid and r['source_group']=='final23'];block['accounted_superseded_domain_ids']=['BLOCK_008:R8_C003']if bid=='BLOCK_008'else[];block['completion_status']='EXACT_NATIVE_ACTIVATION_CHECKED; FINAL_TERRAIN_TRAVERSAL_REPORT_SEPARATE'
 ledger['enclosure_accounting']=dict(complete_gated_backland_subyards=22,complete_old_final_source_enclosures_held=8,held_whole_enclosure_panels=105,intentional_final_entry_opening_panels=2,deferred_final_other_fixtures=3,withdrawn_B008_native_proposals=14,deferred_original_backland_native_placements=68,global_outer_plot_enclosure_claim=False,policy='Eight entire proposed perimeters remain held, rather than selectively activating broken rails. Two further panels are intentional gate openings. Only the22 explicit complete backland subyards carry a closed/gated claim.')
 material_trial=g.CITY/'registered_integration/r8/residual_material_activation_r02/actual_authored_trial.json';mr=g.load(material_trial)['reports'][0]
 ledger['residual_material_application']=dict(tested_source_trial=g.ref(material_trial),plan_binding=g.ref(g.CITY/'registered_integration/r8/residual_material_activation_r02/plan_binding.json'),tested_reclassified_area_m2=mr['reclassified_area_m2'],tested_already_matching_area_m2=mr['already_target_material_area_m2'],tested_retained_original_boundary_material_area_m2=mr['conservatively_retained_boundary_material_area_m2'],activation_claim='This bounded native checker does not prove material application. Refer to the final integration manifest and its exact terrain/material report.')
 ledger['global_completion_gates']=['This exact-scene check validates IDs, native poses/assets/palettes, retirement absence and source accounting. It does not replace final terrain ownership/support/side closure, traversal replay or rendered review.','Keep tested residual material activation separate from actual construction claims unless the supplied final manifest explicitly binds its applied result.','Preserve existing slopes, protected owners, public corridors and declared source holes.']
 ledger['note']='The R04 ledger is preserved. This ledger is emitted only for the supplied exact final manifest and scene.'
 OUT.mkdir();g.write(OUT/'completion_ledger.json',ledger);g.write(OUT/'native_activation_audit.json',audit);(OUT/'completion_ledger.md').write_text('# Exact-scene ordinary activation ledger\n\n'+('PASS'if audit['passed']else'HELD')+f":110 adopted holdings,1 explicitly superseded unbuilt domain,835 backland native selections.\n\nFinal batch:23 holdings,214 ordinary native instances,1 step skin,69 old-native retirements.\n\nEight complete old source enclosures remain held;105 perimeter panels and3 fixtures are excluded. Two further panels are intentional openings. The22 existing backland subyards alone carry the explicit complete gated claim.\n\nNative instance counts describe parts/assemblies, not buildings. Terrain and runtime evidence remain separately bound.\n")
 g.write(OUT/'manifest.json',dict(final_manifest=g.ref(mp),scene=sr,ledger=g.ref(OUT/'completion_ledger.json'),audit=g.ref(OUT/'native_activation_audit.json'),readable=g.ref(OUT/'completion_ledger.md'),passed=audit['passed'],seconds=time.monotonic()-start));print(audit['checks'],flush=True);print(g.ref(OUT/'manifest.json'),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--manifest-sha',required=True);p.add_argument('--scene',required=True,type=Path);p.add_argument('--scene-sha',required=True);v=p.parse_args();run(v.manifest,v.manifest_sha,v.scene,v.scene_sha)
