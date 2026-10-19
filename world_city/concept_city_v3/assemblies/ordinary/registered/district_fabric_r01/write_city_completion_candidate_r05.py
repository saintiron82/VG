"""Source-bound city completion candidate, before exact final-scene activation.

All geometry areas are XZ projections. Raster inventory remains explicitly
sampled; this report never turns a labelled sampling grid into an exact residual
land or enclosure certificate.
"""
from . import geometry as g
from .check_final_city_activation import expected_sources
from .rebind_coherent_datums import require
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import Counter, defaultdict
import time
OUT=g.HERE/'city_completion_candidate_r05'


def area(polygons):
 return sum(g.geo.polygon_area(p) for p in a.common.disjoint_union(polygons)) if polygons else 0.0


def run():
 start=time.monotonic()
 assert not OUT.exists(), 'Preserve candidate bytes; use a new version for later activation.'
 prior, final, withdrawal, groups, deferred_back = expected_sources()
 refs=dict(prior_r04_ledger=g.ref(g.HERE/'city_completion_ledger_r04/completion_ledger.json'),
  initial_coverage_ledger=g.ref(g.CITY/'registered_integration/r8/coverage_plan/COMPLETION_LEDGER.md'),
  baseline_blocks=g.ref(g.CITY/'registered_integration/r8/coverage_plan/baseline_blocks.json'),
  latest_private61_layout=g.ref(g.CITY/'registered_topography/revisions/r17_district_batches/coherent_batch20_r01/effective_source_layout_r03.json'),
  final23_source=g.ref(g.HERE/'final24_source_addendum_r01/atomic_source_addendum.json'),
  final_source_continuation=g.ref(g.HERE/'final24_source_continuation_r01/handoff.json'),
  final23_matching_release=g.ref(g.CITY/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/integration_handoff.json'),
  hall_withdrawal=g.ref(g.HERE/'b08_market_hall_withdrawal_r01/handoff.json'),
  roof_projection=g.ref(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json'),
  old_native_identity_ledger=g.ref(g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01/retirement_candidates.json'),
  integration_candidate=g.ref(g.CITY/'registered_integration/r8/final_exterior_candidate_r01/port_atomic_activation_r02/activation_binding.json'),
  residual_material_trial=g.ref(g.CITY/'registered_integration/r8/residual_material_activation_r02/actual_authored_trial.json'),
  residual_material_binding=g.ref(g.CITY/'registered_integration/r8/residual_material_activation_r02/plan_binding.json'),
  independent_backland_r05_review=prior['source_references']['independent_r05_surface_acceptance'],
  residual_ground_plan=prior['source_references']['residual_land_use_plan'],
  small_and_legacy_margin_plan=prior['source_references']['ground_margin_closure'],
  backland_native=prior['source_references']['backland_native'],author=g.ref(__file__))
 base=require(refs['baseline_blocks']); baseline={r['block_id']:r for r in base['blocks']}
 continuation=require(refs['final_source_continuation'])
 latest=require(refs['latest_private61_layout']); holders={h['id']:h for h in latest['holdings']}
 b15=require(groups[0]['pack']['layout']);holders.update({h['id']:h for h in b15['holdings']});refs['B15_layout']=groups[0]['pack']['layout']
 final_records={r['holding_id']:r for r in final['records']};final_records.update({r['holding_id']:r for r in continuation['replacement_records']})
 holders.update({hid:r['replacement_holding'] for hid,r in final_records.items()})
 projections={r['id']:r for r in require(refs['roof_projection'])['instances']}
 retired_identity={r['source_id']:r['block_id'] for r in require(refs['old_native_identity_ledger'])['rows']}
 all_retired=set(); by_block=defaultdict(list); selected_native=[]; selected_roofs=defaultdict(list); old_by_block=defaultdict(set); releases=[]
 for group in groups:
  pack=group['pack'];selected_native += [p['id'] for p in pack['placements']]
  if not group['holding_ids']:continue
  releases.append(dict(label=group['label'],holding_ids=group['holding_ids'],native_pack=group['pack_ref'],matching_release=group.get('contract',refs['final23_matching_release']),native_instances=len(pack['placements'])))
  for old in pack.get('retired_source_ids',pack.get('replaced_placement_ids',[])):
   all_retired.add(old);old_by_block[retired_identity[old]].add(old)
  for hid in group['holding_ids']:
   h=holders[hid];bid=hid.split(':')[0];poses=[p for p in pack['placements'] if p.get('holding_id')==hid]
   roofs=[q for p in poses for q in p.get('native_roof_polygons_xz_m',[])];selected_roofs[bid]+=roofs
   role=h.get('planned_role') or 'attached_poorer_lodging_craft_and_storage_court'
   native_roles=sorted({p['role'] for p in poses if p.get('native_roof_polygons_xz_m') and p.get('role')})
   floor_values=sorted({p.get('holding_floor_y_m',p.get('finished_floor_y_m')) for p in poses if p.get('native_roof_polygons_xz_m')})
   assert floor_values==[h['floor_y_m']],(hid,floor_values,h['floor_y_m'])
   row=dict(id=hid,source_release=group['label'],planned_function=role,native_range_functions=native_roles,implementation_tier='exterior_only',
    floor_y_m=h['floor_y_m'],logical_holding_polygon_xz_m=h['holding_polygon_xz_m'],logical_holding_area_m2=g.geo.polygon_area(h['holding_polygon_xz_m']),
    native_roof_union_m2=area(roofs),native_placement_ids=[p['id'] for p in poses],actual_entrance_ids=sorted({i for p in poses for i in p.get('actual_door_ids',[])}),
    public_road_id=h.get('public_road_id'),external_width_m=h.get('external_width_m'),boundary_status=h.get('boundary_status','NO_NEW_COMPLETE_OUTER_ENCLOSURE_CERTIFICATE'),
    flat_core_partition_explicit=bool(h.get('flat_owner_polygons_xz_m')),source_record_locator=dict(path=refs['final_source_continuation']['path'] if hid in continuation['changed_profile_holding_ids'] else refs['final23_source']['path'] if group['label']=='final23' else refs['B15_layout']['path'] if group['label']=='B15' else refs['latest_private61_layout']['path'],holding_id=hid))
   by_block[bid].append(row)
 blocks=[]
 for prior_block in prior['blocks']:
  bid=prior_block['block_id'];bb=baseline[bid];holds=sorted(by_block[bid],key=lambda h:h['id']);newroof=area(selected_roofs[bid]);oldroof=area([q for i in sorted(old_by_block[bid]) for q in projections[i]['roof_parts_xz_m']]);land=area([h['logical_holding_polygon_xz_m'] for h in holds])
  held=[p for p in final['explicit_deferred_source_placements'] if p['holding_id'].startswith(bid+':')]
  exact=dict(registered_block_gross_m2=g.geo.polygon_area(bb['polygon_xz_m']),selected_holding_union_m2=land,selected_new_native_roof_union_m2=newroof,
   retired_R7_native_roof_union_m2=oldroof,incremental_net_native_roof_gain_m2=newroof-oldroof,
   roof_fraction_within_selected_holding_land=newroof/land if land else None,
   backland_r05_same_plane_material_m2=prior_block['same_plane_material_area_m2'],
   last16_original_source_plane_functional_assignment_m2=prior_block['new_residual_existing_plane_functional_area_m2'],
   final_actual_material_area_m2=None,final_exact_unassigned_land_m2=None)
  sampled=dict(pitch_m=1,ordinary_replanning_domain_estimate_m2=bb['ordinary_replanning_domain_m2'],protected_or_retained_estimate_m2=bb['protected_or_retained_m2'],
   R7_screened_all_roof_estimate_m2=bb['actual_R7_all_screened_roof_m2'],last16_assignment_source_grid_m2=prior_block['new_residual_source_area_m2'],
   small_margin_source_grid_m2=prior_block['assigned_small_ground_margin_area_m2'],legacy_nonpublic_margin_source_grid_m2=prior_block['closed_legacy_margin_area_m2'])
  exclusions=['Retained public corridors, water and dry service banks, protected precincts and retained native owners keep their exact integration reservations.',
   'Logical holding, route, roof and material areas describe different layers and must not be added into an occupied city total.',
   'Source-plane slopes and declared missing-top holes remain preserved; original-grid labels do not establish exact residual closure.']
  disposition='Selected exterior holdings and named same-plane backland functions; final scene activation and traversal still gated.'
  if bid=='BLOCK_012':
   disposition='Retained protected market. No ordinary infill or new ordinary holding is selected.'
   exclusions+=['The full market block is excluded from ordinary replanning. The 6,218 m² protected grid estimate is not the exact 6,222.516 m² source polygon.']
  if bid=='BLOCK_013':
   disposition='Retained dense poorer native roofscape with shared domestic/work grounds; zero new whole holdings is intentional.'
   exclusions+=['The 6,966 m² retained screened roof quantity is a 1 m R7 sampling estimate, not a fresh exact-scene roof measurement.']
  if bid=='BLOCK_008':
   exclusions+=['BLOCK_008:R8_C003 is withdrawn before activation; its 960 m² domain remains north market-hall/service-ground ownership. Its 546.5 m² proposed roof and fourteen native proposals are excluded from construction.']
  blocks.append(dict(block_id=bid,district_id=prior_block['district_id'],public_boundary_road_ids=prior_block['public_boundaries'],disposition=disposition,
   selected_holding_ids=[h['id']for h in holds],selected_holding_count=len(holds),source_release_counts=dict(Counter(h['source_release']for h in holds)),planned_holding_functions=dict(Counter(h['planned_function']for h in holds)),holdings=holds,
   exact_source_projected_area_m2=exact,sampling_estimates=sampled,retired_old_native_ids=sorted(old_by_block[bid]),
   functional_backlands=dict(material_owner_components=prior_block['same_plane_material_components'],functions_source_r05_area_m2=prior_block['same_plane_ground_functions_m2'],selected_native_instances=prior_block['selected_backland_native_uses'],native_uses_by_asset=prior_block['selected_native_uses_by_asset'],complete_gated_subyard_ids=prior_block['complete_gated_subyard_ids']),
   residual_dispositions=dict(last16_region_ids=prior_block['new_residual_land_use_ids'],small_margin_ids=prior_block['assigned_small_ground_margin_ids'],small_margin_functions=prior_block['small_margin_dispositions'],legacy_nonpublic_margin_ids=prior_block['closed_legacy_margin_ids'],legacy_access_status='Unactivated occupied-yard claims withdrawn; no public backland spur claimed.'),
   enclosure_exclusions=dict(held_complete_old_perimeter_owner_ids=sorted({p['holding_id']for p in held if p['reason'].startswith('ENTIRE_UNACTIVATED_ENCLOSURE_HELD')}),deferred_native_ids=[p['id']for p in held],global_outer_enclosure_certified=False),
   superseded_unbuilt_domain_ids=['BLOCK_008:R8_C003']if bid=='BLOCK_008'else[],exclusions=exclusions,remaining_activation_and_traversal_gate_ids=['G1','G2','G3','G4','G5'],actual_activation_scene=None))
 trial=require(refs['residual_material_trial'])['reports'][0]
 summary=dict(registered_blocks=len(blocks),ordinary_replanning_blocks=17,adopted_whole_holdings=sum(b['selected_holding_count']for b in blocks),prior_released_holdings=87,final_released_holdings=23,
  superseded_unbuilt_domains=1,superseded_domain_area_m2=withdrawal['summary']['affected_holding_area_m2'],selected_native_parts_and_assemblies=len(selected_native),selected_backland_native_instances=835,
  deferred_original_backland_native_instances=len(deferred_back),old_native_retirements=len(all_retired),final_old_native_retirements=69,
  selected_holding_union_m2=area([h['logical_holding_polygon_xz_m']for b in blocks for h in b['holdings']]),new_native_roof_union_m2=area([q for p in selected_roofs.values()for q in p]),
  retired_R7_native_roof_union_m2=area([q for i in sorted(all_retired)for q in projections[i]['roof_parts_xz_m']]),
  source_r05_same_plane_backland_area_m2=sum(b['exact_source_projected_area_m2']['backland_r05_same_plane_material_m2']for b in blocks),
  last16_source_plane_functional_area_m2=sum(b['exact_source_projected_area_m2']['last16_original_source_plane_functional_assignment_m2']for b in blocks),
  final_exact_unassigned_land_m2=None,final_exact_unassigned_component_count=None,final_actual_scene_bound=False)
 summary['incremental_net_native_roof_gain_m2']=summary['new_native_roof_union_m2']-summary['retired_R7_native_roof_union_m2']
 checks=dict(all18_registered_blocks_present=set(baseline)=={b['block_id']for b in blocks},unique110_adopted_holdings=len({h['id']for b in blocks for h in b['holdings']})==summary['adopted_whole_holdings']==110,
  exact2006_native_selections_unique=len(selected_native)==len(set(selected_native))==2006,backland835_block_counts_sum=sum(b['functional_backlands']['selected_native_instances']for b in blocks)==835,
  gated22_subyards_only=sum(len(b['functional_backlands']['complete_gated_subyard_ids'])for b in blocks)==22,
  withdrawal_not_counted=not any('BLOCK_008:R8_C003'in b['selected_holding_ids']for b in blocks),
  no_exact_unassigned_zero_claim=all(b['exact_source_projected_area_m2']['final_exact_unassigned_land_m2']is None for b in blocks),
  holding_union_not_double_counted=abs(sum(b['exact_source_projected_area_m2']['selected_holding_union_m2']for b in blocks)-summary['selected_holding_union_m2'])<1e-6,
  roofs_not_double_counted=abs(sum(b['exact_source_projected_area_m2']['selected_new_native_roof_union_m2']for b in blocks)-summary['new_native_roof_union_m2'])<1e-6,
  registered_market_no_infill=not by_block['BLOCK_012'],retained_B13_no_replacement=not by_block['BLOCK_013'])
 assert all(checks.values()),checks
 gates=[dict(id='G1',name='Exact final native activation',status='AWAITING_PARENT_FINAL_MANIFEST_AND_SCENE_SHA',requirement='Run the sealed activation checker: all 110 holding selections, 835 backlands, step native and exact assets/poses present once; all 295 old owners/foundations and all explicit deferred proposals absent; retained hall unchanged.'),
  dict(id='G2',name='Composed terrain and native ownership',status='SOURCE_RELEASES_PASS_FINAL_COMPOSITION_PENDING',requirement='Bind final top/side/support and reservation audits, including the micrometre float32 winding continuation and cross-pack priority. Source producer passes are not exact composed-scene acceptance.'),
  dict(id='G3',name='Final public/private traversal',status='PRIOR61_REPLAY_REPORTED_PASS_FINAL110_REPLAY_PENDING',requirement='Replay final private/public joins, narrow pedestrian routes, approved step collider and continuous walking envelopes using the unchanged controller. Preserve declared pedestrian-only and local-grade limits.'),
  dict(id='G4',name='Actual material application',status='TESTED_NOBLE61_TRIAL_BOUND_IN_CANDIDATE_FINAL_RESULT_PENDING',requirement='Verify final applied same-plane areas against final exact reservations. Preserve conservative original boundary triangles and existing holes; no new native facility is claimed by a material label.'),
  dict(id='G5',name='Rendered layout review and exact residual scope',status='LAYOUT_REVIEW_BUILD_RUNNING',requirement='Review the final view and bind the exact scene ledger. Existing sampling dispositions cover the initial source inventory; a final exact unassigned-land result has not been recomputed and is not claimed.')]
 ledger=dict(schema='riverstone.ordinary_city.source_selected_completion_candidate.v5',status='SOURCE_SELECTED_110_CANDIDATE_AWAITING_EXACT_FINAL_ACTIVATION',source_references=refs,releases=releases,summary=summary,blocks=blocks,
  withdrawn_market_hall_domain=dict(source=refs['hall_withdrawal'],holding_id=withdrawal['holding_id'],retained_native_id=withdrawal['actual_retained_hall']['id'],exact_projected_partition_m2=withdrawal['summary'],new_construction=False),
  residual_material_application=dict(status='TESTED_UNBOUND_UNTIL_FINAL_SCENE_REPORT',source_trial=refs['residual_material_trial'],source_plan_bound_in_integration_candidate=True,tested_reclassified_area_m2=trial['reclassified_area_m2'],tested_already_matching_area_m2=trial['already_target_material_area_m2'],tested_conservatively_original_boundary_material_m2=trial['conservatively_retained_boundary_material_area_m2'],arithmetic_unpainted_color_residue_budget_m2=1e-6,zero_height_change=True,new_native_facilities=0),
  enclosure_accounting=dict(complete_gated_backland_subyards=22,held_complete_old_final_perimeters=8,held_whole_perimeter_panels=105,intentional_final_entry_opening_panels=2,deferred_final_other_fixtures=3,withdrawn_B008_proposals=14,deferred_original_backland_native_proposals=68,global_outer_plot_enclosure_claim=False),
  sampling_disposition_accounting=dict(last_large_components=16,last_large_source_grid_m2=3859,small_components=869,small_source_grid_m2=2507,legacy_unactivated_occupied_claims_withdrawn=29,legacy_source_grid_m2=1046,initial_grid_inventory_all_named=True,exact_final_unassigned_area_or_zero_result_claimed=False),
  measurement_policy=['All geometric areas are XZ projections, not sloping surface areas. Exact means evaluated from source polygons/triangles at floating-point precision, not a sampling estimate.',
   'Registered gross area is the finite source block polygon. Ordinary replanning, protected inventory and screened R7 roof estimates use the original 1 m grid.',
   'Selected holding and roof unions are assigned to the registered owner block by holding ID, not clipped again to the coarse block outline. Roof net gain compares the selected native masks with only explicitly retired R7 native roofs.',
   'Backland r05 material areas are exact source-plane accounting for that release. Later integration owner-priority cuts may change the applied material areas; final quantities await the composed-scene report.',
   'Holding, roof, private entry, backland material and retained protected ownership overlap by definition. Do not sum these layers into total occupied land or calculate city coverage from mixed denominators.',
   '110 counts adopted whole holdings. The 2,006 selected native objects are parts/assemblies, and 835 of them are backland fixtures. Inherited 703 planning masses and actual-scene instance totals are not building counts.',
   'Exterior role labels describe visible planned use only; open interiors, simulated commerce, universal cart access and complete outer enclosure are not claimed.'],
  remaining_gates=gates,checks=checks,passed=all(checks.values()),seconds=time.monotonic()-start)
 OUT.mkdir();g.write(OUT/'completion_ledger.json',ledger)
 lines=['# Whole-city ordinary completion candidate','',
 '110 adopted exterior holdings are selected in matching source releases: 26 B15, 61 earlier private holdings and 23 final holdings. The unbuilt B008 C003 proposal is explicitly superseded by retained market-hall/service ground. This ledger awaits the final exact-scene activation check.','',
 f"The selected holdings occupy {summary['selected_holding_union_m2']:,.3f} m² of logical XZ land and carry {summary['new_native_roof_union_m2']:,.3f} m² of new native roof union. Removing {summary['retired_R7_native_roof_union_m2']:,.3f} m² of explicitly retired R7 roofs gives a net increment of {summary['incremental_net_native_roof_gain_m2']:,.3f} m². These are source-selected increments, not total city roof coverage.",'',
 '835 supported backland native selections accompany 440 source material owners. Their r05 same-plane source accounting is 76,988.978 m²; the final integration may cede material pieces to higher-priority physical owners. Only 22 listed subyards have an explicit complete gated enclosure claim. Eight old proposed perimeters remain wholly held (105 panels), three other fixtures are deferred, and two panels are intentional entry openings.','',
 'The 16 last large residual regions total 3,859 m² on the original 1 m grid, with 3,343.749 m² of exact clipped functional source-plane assignment. The latest tested material trial reclassifies 3,297.910 m², leaves 45.460 m² already matching and preserves 0.274 m² of complete original boundary triangles; the tiny arithmetic unpainted residue stays below 0.000001 m². Exact E7 ownership has priority. Final application is still unbound to an actual final-scene result.','',
 'The 869 small fragments (2,507 m² sampled) and 29 legacy fragments (1,046 m² sampled) have named drainage, maintenance, visibility or clearance dispositions. The latter withdraw unactivated occupied-yard claims; no unsupported courtyard spur is declared connected. All original sampling inventory is named, but no exact final zero-unassigned result is claimed.','',
 '## Measurement key','',
 '- Exact areas below are projected source-polygon or source-triangle areas. They are not sloping surface areas.',
 '- Estimates explicitly use the initial 1 m inventory grid.',
 '- Holding, roof, material, road and protected-owner layers must not be added together.',
 '- Whole holdings and native part/assembly counts are different inventories. All use remains exterior-only.','']
 for b in blocks:
  ex=b['exact_source_projected_area_m2'];est=b['sampling_estimates'];fun=b['functional_backlands']
  lines += [f"## {b['block_id']} · {b['district_id']}",'',b['disposition'],
   f"Source-selected holdings ({b['selected_holding_count']}): "+(', '.join(b['selected_holding_ids'])or'none')+'.',
   f"Exact gross source block: {ex['registered_block_gross_m2']:,.3f} m². Ordinary replanning estimate: {est['ordinary_replanning_domain_estimate_m2']:,.0f} m² (1 m sampling).",
   f"Exact selected holding union: {ex['selected_holding_union_m2']:,.3f} m²; new roof union: {ex['selected_new_native_roof_union_m2']:,.3f} m²; retired roof union: {ex['retired_R7_native_roof_union_m2']:,.3f} m²; incremental net roof: {ex['incremental_net_native_roof_gain_m2']:+,.3f} m²."]
  if b['planned_holding_functions']:lines+=['Holding functions: '+ '; '.join(f"{k.replace('_',' ')} ({v})"for k,v in b['planned_holding_functions'].items())+'.']
  lines += [f"Backland r05 exact source material: {ex['backland_r05_same_plane_material_m2']:,.3f} m² across {fun['material_owner_components']} components; {fun['selected_native_instances']} native selections; {len(fun['complete_gated_subyard_ids'])} complete gated subyards."]
  if fun['functions_source_r05_area_m2']:lines+=['Ground uses: '+ '; '.join(f"{k.replace('_',' ')} {v:,.1f} m²"for k,v in sorted(fun['functions_source_r05_area_m2'].items()))+'.']
  if b['residual_dispositions']['last16_region_ids']:lines += [f"Last large source regions: {', '.join(b['residual_dispositions']['last16_region_ids'])}; {est['last16_assignment_source_grid_m2']:,.0f} m² sampled, {ex['last16_original_source_plane_functional_assignment_m2']:,.3f} m² exact source-plane functional assignment."]
  lines += [f"Named small margins: {est['small_margin_source_grid_m2']:,.0f} m² sampled; legacy nonpublic margins: {est['legacy_nonpublic_margin_source_grid_m2']:,.0f} m² sampled."]
  if b['enclosure_exclusions']['held_complete_old_perimeter_owner_ids']:lines+=['Entire old proposed perimeters held: '+', '.join(b['enclosure_exclusions']['held_complete_old_perimeter_owner_ids'])+'.']
  if b['superseded_unbuilt_domain_ids']:lines+=['Withdrawn B008 C003: 960.000 m² = 658.219 m² retained hall projection + 301.777 m² existing service ground + 0.003932 m² preserved missing-top edges. No new construction or private entry obligation.']
  if b['block_id']=='BLOCK_013':lines+=['Retained R7 screened roof estimate: 6,966 m² (1 m grid); no new roof batch is needed to make this retained roofscape count.']
  lines+=['Public boundary references: '+', '.join(b['public_boundary_road_ids'])+'.','Exact final material and unassigned-land areas: not yet measured. Global gates G1–G5 apply. Outer enclosure is not globally certified.','']
 lines+=['## Remaining actual activation and traversal gates','']
 for gate in gates:lines += [f"- {gate['id']} {gate['name']}: {gate['status']}. {gate['requirement']}"]
 lines += ['', '## Bound evidence','',*['- '+k+': '+v['path']+' (SHA-256 '+v['sha256']+')'for k,v in refs.items()], '','The initial all-open coverage ledger and R04 ledger remain unchanged. This candidate makes no final-scene activation or runtime-completion claim.']
 (OUT/'COMPLETION_LEDGER.md').write_text('\n'.join(lines)+'\n')
 g.write(OUT/'manifest.json',dict(status=ledger['status'],data=g.ref(OUT/'completion_ledger.json'),readable=g.ref(OUT/'COMPLETION_LEDGER.md'),source_author=g.ref(__file__),checks=checks,summary=summary))
 print(summary,flush=True);print(checks,flush=True);print(g.ref(OUT/'manifest.json'),flush=True)

if __name__=='__main__':run()
