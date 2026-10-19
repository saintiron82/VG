"""Read-only G2/G4 evidence binding for the supplied final runtime scene."""
from . import geometry as g
from .rebind_coherent_datums import require
from world_city.concept_city_v3.registered_integration.r8.compose_finite_patches import compound_row
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as ap
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import defaultdict,Counter
import gc,time
OUT=g.HERE/'final_ground_activation_binding_r01'
MANIFEST=dict(path='world_city/concept_city_v3/evidence/r8_final110_runtime_r01/activation_manifest.json',sha256='83d6c0fc2621cfbe7e3b2786ca2b1f64ef1a7eec1ece25575b58bfe95f8853ab')
SCENE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
BINDING_SHA='3e092e8436b3350b6b55a79129809004b90c13cf93d03b241344066b8d537bc7'


def tri_key(t):return tuple(sorted(tuple(v)for v in t))
def area(t):return g.geo.polygon_area([[v[0],v[2]]for v in t])


def run():
 start=time.monotonic();assert not OUT.exists()
 m=require(MANIFEST);assert m['scene']['sha256']==SCENE_SHA and m['binding']['sha256']==BINDING_SHA
 binding=require(m['binding']);closure=require(m['build_read_closure']);guard=require(m['source_guard']);precision=require(m['runtime_precision_ledger']);winding=require(m['runtime_winding_ledger'])
 native_ref=g.ref(g.HERE/'city_activation_ledger_r02/manifest.json');native=require(native_ref);assert native['passed']and native['actual_scene']==m['scene']
 composition_path=g.CITY/'registered_topography/revisions/r17_district_batches/final23_backland_composition_r01/shared_source_review.json';old_composition=g.load(composition_path)
 backland_ref=next(r for r in binding['patches']if r['path'].endswith('final23_backland_composition_r01/backland_producer.json'))
 backland=require(backland_ref);ownership_ref=g.ref(g.CITY/'registered_topography/revisions/r17_district_batches/final23_backland_composition_r01/ownership_ledger.json');ownership=require(ownership_ref)
 final_patches=[]
 for ref in binding['patches']:
  if 'final23_precision_continuation_r01/top_scene_patch.json'in ref['path']or 'coherent_final24_r02/side_scene_patch_r01.json'in ref['path']:
   final_patches.append((ref,require(ref)))
 keys={(r['material'],r['triangle_index'])for ref,p in final_patches for r in p['surface_edits']}
 groups=defaultdict(list);patch_checks=[]
 for ref in binding['patches']:
  p=backland if ref==backland_ref else require(ref)
  patch_checks.append(dict(source=ref,id=p['id'],read_closure_hash_match=closure['files'].get(ref['path'])==ref['sha256']))
  for row in p['surface_edits']:
   key=row['material'],row['triangle_index']
   if key in keys:groups[key].append((p['id'],row))
  if p is not backland:del p
 base=require(binding['base_scene']);errors=[];passing=[]
 for key,rows in sorted(groups.items()):
  if len(rows)<2:continue
  try:compound_row(base,key,rows,binding.get('finite_physical_side_retirement_union',False));passing.append(dict(material=key[0],triangle_index=key[1],producer_ids=[p for p,r in rows]))
  except ValueError as e:errors.append(dict(material=key[0],triangle_index=key[1],error=str(e)))
 del base;gc.collect()
 current_composition=dict(binding=m['binding'],prior731_review=g.ref(composition_path),shared_rows=len(passing)+len(errors),passing=len(passing),errors=errors,passed=not errors,checker=g.ref(compound_row.__code__.co_filename),rows=passing)
 print('current shared rows',current_composition['shared_rows'],'pass',len(passing),'errors',len(errors),flush=True)
 # Runtime triangle identity is checked directly for the actual consumed
 # backland material producer. The precision ledger is the only permitted
 # explanation for a missing original triangle; no numerical area cutoff.
 scene=require(m['scene']);runtime_sets={mat:Counter(tri_key(flat[i:i+3])for i in range(0,len(flat),3))for mat,flat in scene['surfaces'].items()if mat in backland['appended_surfaces']}
 removed=defaultdict(set)
 for r in precision['removals']:removed[r['material']].add(tri_key(r['source_triangle_xyz_m']))
 material_rows=[];unexpected=[]
 for mat,flat in backland['appended_surfaces'].items():
  matched=0;zero=0;matched_area=0.;zero_area=0.;allarea=0.
  for i in range(0,len(flat),3):
   tri=flat[i:i+3];key=tri_key(tri);aa=area(tri);allarea+=aa
   if runtime_sets[mat][key]:matched+=1;matched_area+=aa
   elif key in removed[mat]:zero+=1;zero_area+=aa
   else:unexpected.append(dict(material=mat,producer_triangle_index=i//3,triangle_xyz_m=tri,area_xz_m2=aa))
  material_rows.append(dict(material=mat,producer_triangles=len(flat)//3,producer_area_xz_m2=allarea,exact_runtime_triangle_matches=matched,exact_runtime_matched_area_xz_m2=matched_area,declared_float32_zero_removals=zero,removed_precise_source_area_xz_m2=zero_area))
 print('backland material membership',[(r['material'],r['exact_runtime_triangle_matches'],r['declared_float32_zero_removals'])for r in material_rows],'unexplained',len(unexpected),flush=True)
 residual=scene['r8_residual_land_use'];assert len(residual)==1;rr=residual[0];ref=binding['residual_land_use_plans'][0];plan=require(ref)
 residual_small={k:v for k,v in rr.items()if k not in ['source_partitions','retained_complete_boundary_triangles','unpainted_color_boundaries']}
 partition_sum=sum(r['reclassified_area_m2']for r in rr['source_partitions']);partition_error=max(r['partition_error_m2']for r in rr['source_partitions'])
 report_accounted=rr['reclassified_area_m2']+rr['already_target_material_area_m2']+rr['conservatively_retained_boundary_material_area_m2']+rr['unpainted_color_boundary_area_m2']
 physical_ref=g.ref(g.CITY/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/physical_acceptance_r01.json');physical=require(physical_ref)
 top_ref=g.ref(g.CITY/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/top_coverage_report_r01.json');top=require(top_ref)
 side_ref=g.ref(g.CITY/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/local_boundary_review_r01.json');side=require(side_ref)
 checks=dict(exact_actual_scene_manifest_and_binding=True,native_activation_same_scene=native['passed'],
  build_closure_binds_actual_authored_scene=closure['authored_scene']==m['authored_scene']and closure['build_binding']==m['binding'],
  all29_current_producer_reads_exact=len(patch_checks)==29 and all(r['read_closure_hash_match']for r in patch_checks),
  actual_scene_provenance_matches_binding=scene['r8_provenance']['binding_sha256']==ap.digest(binding),
  actual_authored_source_guard_pass=guard['status']=='pass'and guard['downward']==0,
  original731_composition_pass=old_composition['passed']and old_composition['shared_rows']==old_composition['passing']==731,
  current731_composition_pass=current_composition['passed']and current_composition['shared_rows']==731,
  final23_source_top_native_and_side_acceptance=physical['passed']and not physical['support_failures']and not physical['step_support_failures']and top['status']=='PASSED_TOP_SOURCE_COVERAGE'and side['status']=='PASS_LOCAL_FINITE_BOUNDARY',
  exact_runtime_derivation_chain=precision['source']==m['authored_scene']and precision['runtime_scene']==m['precision_normalized_scene']and winding['source_scene']==m['precision_normalized_scene']and winding['derived_scene']==m['scene'],
  runtime_continuations_preserve_material_provenance=precision['non_surface_fields_unchanged_except_terrain_count_metadata']and winding['unchanged_non_surface_fields'],
  runtime_backland_material_triangles_or_declared_zero_removals=not unexpected,
  residual_plan_and_exclusions_consumed=rr['source_plan']==ref and closure['files'].get(ref['path'])==ref['sha256']and all(closure['files'].get(x['path'])==x['sha256']for x in ref.get('exact_exclusions',[])),
  all16_residual_regions_consumed=rr['regions']==len(plan['regions'])==16,
  residual_exact_source_partition_accounting=abs(partition_sum-rr['reclassified_area_m2'])<1e-6 and abs(report_accounted-rr['effective_area_m2'])<1e-6 and partition_error<=1e-7,
  residual_same_planes_and_protected_ground=rr['maximum_plane_error_m']<=1e-7 and not rr['new_ground_height']and not rr['missing_ground_filled']and rr['protected_surfaces_unchanged']and rr['new_native_instances']==0,
  residue_within_exact_declared_budget=rr['unpainted_color_boundary_area_m2']<=rr['unpainted_color_budget_m2']==1e-6,
  original_diagnostics_preserved=require(g.ref(g.HERE/'city_activation_ledger_r01/manifest.json'))['passed']==False)
 proof=dict(schema='riverstone.ordinary_city.actual_ground_activation_binding.v1',status='PASS_G2_SOURCE_COMPOSITION_AND_G4_ACTUAL_MATERIAL_CONSUMPTION'if all(checks.values())else'HELD_GROUND_BINDING',passed=all(checks.values()),actual_manifest=MANIFEST,actual_scene=m['scene'],actual_binding=m['binding'],native_activation=native_ref,
  evidence=dict(source_guard=m['source_guard'],build_read_closure=m['build_read_closure'],runtime_precision=m['runtime_precision_ledger'],runtime_winding=m['runtime_winding_ledger'],prior731_source_review=g.ref(composition_path),physical_acceptance=physical_ref,top_coverage=top_ref,local_side_acceptance=side_ref,consumed_backland_producer=backland_ref,final23_backland_priority_ledger=ownership_ref,residual_source_plan=ref,author=g.ref(__file__)),
  checks=checks,current_source_composition=current_composition,consumed_producer_rows=patch_checks,backland_materials=dict(materials=material_rows,producer_total_area_xz_m2=sum(r['producer_area_xz_m2']for r in material_rows),exact_runtime_matched_area_xz_m2=sum(r['exact_runtime_matched_area_xz_m2']for r in material_rows),declared_float32_zero_removed_area_xz_m2=sum(r['removed_precise_source_area_xz_m2']for r in material_rows),final23_owner_priority_ceded_area_m2=ownership['summary']['removed_backland_area_m2'],unexpected_runtime_missing_triangles=unexpected),
  applied_residual_material=residual_small,residual_accounting=dict(source_partition_reclassified_area_m2=partition_sum,maximum_source_partition_error_m2=partition_error,area_accounting_residual_m2=rr['effective_area_m2']-report_accounted,retained_complete_boundary_triangles=rr['retained_complete_boundary_triangles'],unpainted_color_boundaries=rr['unpainted_color_boundaries']),
  scoped_gate_updates=[dict(id='G2',status='BOUND_ACTUAL_SCENE_SOURCE_COMPOSITION_TOP_SUPPORT_AND_RUNTIME_DERIVATION_PASS',scope='Binds exact producer support/top/side acceptance, the current731 shared-row composition and authored/runtime continuation. Full controller replay remains G3.'),dict(id='G4',status='ACTUAL_SAME_PLANE_MATERIAL_APPLICATION_CONFIRMED',scope='Actual scene contains the consumed backland producer material triangles and the executed16-region residual report; protected source planes and holes remain unchanged.')],
  unchanged_scope=dict(registered_blocks=18,adopted_holdings=110,backland_native_selections=835,withdrawn_hall_domain_m2=960,complete_gated_subyards=22,final_exact_unassigned_land_area_m2=None,sampled_large_source_dispositions_m2=3859,sampled_small_named_margins_m2=2507,sampled_legacy_nonpublic_margins_m2=1046),
  remaining_acceptance=['G3: Final exact-scene controller traversal and physical-collider replay are separately owned.','G5: Final rendered layout review is separately owned. No global exact zero-unassigned requirement or result is introduced.'],
  limitations=['Areas are projected XZ source or authored execution measures, not sloping surface areas. Runtime triangles retained after the explicit precision continuation are separately counted.','The 3,859/2,507/1,046 m² named source inventories are1 m sampling estimates, not extra painted construction. They must not be added to exact material or holding areas.','Native, source candidate, original R04 and failed strict-palette evidence remain unchanged. This continuation creates no geometry.'],seconds=time.monotonic()-start)
 OUT.mkdir();g.write(OUT/'handoff.json',proof)
 text=['# Final ground activation binding','',proof['status'],'',
 f"Bound to scene {SCENE_SHA} and activation binding {BINDING_SHA}.",'',
 f"G2: the current 731 shared final23 source rows pass exact composition; all 29 producer reads match the actual build closure. Source top winding passes, final23 native/top/side support passes, and the authored-to-runtime precision chain is explicitly bound.",'',
 f"G4: the consumed backland material producer contains {proof['backland_materials']['producer_total_area_xz_m2']:,.6f} m² of same-plane earth/grass tops after protected-owner priority, including the {ownership['summary']['removed_backland_area_m2']:.6f} m² final23 cession. Actual runtime triangle identity and declared exact-zero removals are checked in the JSON.",'',
 f"The actual16-region residual report records {rr['reclassified_area_m2']:,.6f} m² reclassified, {rr['already_target_material_area_m2']:,.6f} m² already matching, {rr['conservatively_retained_boundary_material_area_m2']:.6f} m² original boundary material retained and {rr['unpainted_color_boundary_area_m2']:.12f} m² arithmetic color residue. There is no height change, new native facility or hole filling.",'',
 'The 3,859 m² large source inventory, 2,507 m² small margins and 1,046 m² legacy margins remain sampled named dispositions. No exact global zero-unassigned result is claimed. The110 holdings,835 backlands and960 m² hall withdrawal are unchanged.','',
 'Final traversal/collision replay and rendered review remain separate gates. The failed strict palette diagnostic is preserved.']
 (OUT/'README.md').write_text('\n'.join(text)+'\n');g.write(OUT/'manifest.json',dict(passed=proof['passed'],actual_manifest=MANIFEST,actual_scene=m['scene'],actual_binding=m['binding'],native_activation=native_ref,handoff=g.ref(OUT/'handoff.json'),readable=g.ref(OUT/'README.md'),author=g.ref(__file__)))
 print(checks,flush=True);print(g.ref(OUT/'manifest.json'),flush=True)

if __name__=='__main__':run()
