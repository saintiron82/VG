import ast,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
import author_facility_roofs as a
import finish_roofs as f
from prepare_handoff import baseline_check
class ActivationHandoffTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=a.read(a.HERE/'variant_selection.json');cls.new=a.read(a.HERE/'variant_selection.v2.json');cls.catalog=a.read(HERE/'all_72_layered_compile_catalog.v5.json');cls.plan=a.read(HERE/'compile_activation_plan.json')
 def test_previous_files_unchanged(self):self.assertEqual(baseline_check(),334)
 def test_exactly_one_selector_row_changes(self):
  before={r['placement_id']:r for r in self.old['placements']};after={r['placement_id']:r for r in self.new['placements']};self.assertEqual(before.keys(),after.keys());self.assertEqual([k for k in before if before[k]!=after[k]],['castle_registered:stable'])
 def test_new_choice_is_explicit_assumption(self):
  d=a.read(HERE/'castle_stable_covering_decision.json');self.assertEqual(d['decision_class'],'EXPLICIT_AUTHORED_ASSUMPTION');self.assertFalse(d['recovered_current_placement_fact']);self.assertFalse(d['rgb_used_for_classification']);self.assertEqual(d['specific_original_pitch_degrees_preserved'],32)
 def test_all_placements_resolve_without_fallback(self):
  self.assertEqual(len(self.new['placements']),332);self.assertFalse(self.new['pending']);self.assertTrue(all(r['selected_variant_asset_key'] and not r['fallback_allowed'] for r in self.new['placements']))
 def test_only_seventy_two_variants_are_required(self):
  allkeys={r['asset_key']:r for r in self.catalog['assets']};selected={r['selected_variant_asset_key'] for r in self.new['placements']};self.assertEqual(len(allkeys),82);self.assertEqual(len(selected),72);self.assertTrue(selected<=allkeys.keys());self.assertEqual(self.plan['summary']['unselected_retained_variants'],10)
 def test_original_81_source_references_preserved(self):
  old=a.read(a.HERE/'shape_extensions/all_72_layered_compile_catalog.json');self.assertEqual(self.catalog['assets'][:81],old['assets'])
 def test_stable_source_materials_and_bounds(self):
  r=self.catalog['assets'][-1];m=f.layers.load_master(a.ROOT/r['emitted_master_path']);s=a.read(a.ROOT/r['source_master_path']);self.assertEqual(m['materials'],s['materials']);v=a.read(HERE/'castle_stable_wood_shingle.validation.json');self.assertFalse(v['source']['structure_validation']['failures']);self.assertEqual(v['roi']['outside_original_position_material_cells'],0);self.assertGreater(v['roi']['removed_source_cells'],0)
 def test_chunk_grid_matches_production(self):
  self.assertEqual((self.plan['pitch_m'],self.plan['chunk_edge_fine_cells'],self.plan['halo_fine_cells']),(.05,60,2));r={v['native_asset_key']:v for v in self.plan['variants'] if v['required_by_current_placements']};self.assertEqual(r['registered_cathedral_nave_aisles_transept']['chunk_plan']['scheduled_chunks'],1050);self.assertEqual(r['registered_port_long_loading_shed']['chunk_plan']['scheduled_chunks'],192)
 def test_metadata_planner_never_calls_compiler(self):
  tree=ast.parse((HERE/'summarize_catalog.py').read_text());self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='compile_master' for n in ast.walk(tree)));self.assertEqual(self.plan['full_compiles_performed'],0)
 def test_all_activation_flags_remain_false(self):
  self.assertTrue(all(not r['replacement_allowed'] for r in self.catalog['assets']));self.assertTrue(all(not r['activation_allowed'] for r in self.plan['recommended_serial_queue']));self.assertEqual(len(self.plan['recommended_serial_queue']),70)

class NativeSamplingRevisionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.oldcat=a.read(HERE/'all_72_layered_compile_catalog.v5.json');cls.newcat=a.read(HERE/'all_72_layered_compile_catalog.v6.json');cls.oldsel=a.read(a.HERE/'variant_selection.v2.json');cls.newsel=a.read(a.HERE/'variant_selection.v3.json');cls.plan=a.read(HERE/'compile_activation_plan.v2.json');cls.validation=a.read(HERE/'native_seam_revision/validation.json')
 def test_only_stable_wood_source_revision_changes(self):
  before={r['asset_key']:r for r in self.oldcat['assets']};after={r['asset_key']:r for r in self.newcat['assets']};self.assertEqual(before.keys(),after.keys());self.assertEqual([k for k in before if before[k]!=after[k]],['registered_castle_stable__wood_shingle']);old=before['registered_castle_stable__wood_shingle'];self.assertEqual(a.shared.sha(a.ROOT/old['emitted_master_path']),old['emitted_master_sha256'])
 def test_native_revision_changes_no_semantic_selection(self):
  self.assertEqual(self.oldsel['placements'],self.newsel['placements']);self.assertEqual(self.oldsel['counts'],self.newsel['counts']);self.assertFalse(self.newsel['pending'])
 def test_native_seams_exist_inside_original_material_solid(self):
  v=self.validation;self.assertEqual(v['outside_original_position_material_cells'],0);self.assertGreater(v['removed_source_cells'],0);self.assertTrue(v['pruned_and_unpruned_native_samples_identical']);self.assertEqual(v['previous_positive_y_face_z_width_counts'],{'0.85':9});self.assertTrue(any(float(k)<.3 for k in v['new_positive_y_face_z_width_counts']));self.assertFalse(v['full_asset_compile']);self.assertFalse(v['global_constraints_evaluated']);self.assertFalse(v['replacement_allowed'])
 def test_all_current_catalog_source_hashes(self):
  for r in self.newcat['assets']:
   self.assertEqual(a.shared.sha(a.ROOT/r['emitted_master_path']),r['emitted_master_sha256']);self.assertFalse(r['replacement_allowed'])
 def test_current_plan_hashes_and_totals(self):
  for field in ('catalog','selector','rules','chunk_enumerator','layered_engine'):
   ref=self.plan[field];self.assertEqual(a.shared.sha(a.ROOT/ref['path']),ref['sha256'])
  selected=[r for r in self.plan['variants'] if r['required_by_current_placements']];self.assertEqual(len(selected),72);self.assertEqual(sum(r['source_gzip_bytes'] for r in selected),8582115);self.assertEqual(sum(r['operations'] for r in selected),427251);self.assertEqual(sum(r['chunk_plan']['scheduled_chunks'] for r in selected),13980)
 def test_other_wood_variants_have_explicit_sampling_gate(self):
  woods=[r for r in self.plan['variants'] if r['required_by_current_placements'] and r['covering']=='wood_shingle'];self.assertEqual(len(woods),10);pending=[r for r in woods if r['native_lateral_seam_gate']['status']=='PENDING_REPRESENTATIVE_NATIVE_ROI'];self.assertEqual(len(pending),9);self.assertTrue(all(r['native_lateral_seam_gate']['full_compile_blocked_until_checked'] for r in pending));self.assertTrue(all(not r['native_lateral_seam_gate']['known_failure_for_this_asset'] for r in pending))
 def test_refresh_planner_is_metadata_only(self):
  tree=ast.parse((HERE/'update_native_sampling_plan.py').read_text());self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='compile_master' for n in ast.walk(tree)));self.assertEqual(self.plan['full_compiles_performed'],0)
if __name__=='__main__':unittest.main()
