"""Bounded source/cache/ownership regression; no city build or GUI required."""
import json,unittest,math
from .grammar import HERE,ROOT,ref,g,estate,FAMILIES
from .author import triangle_grade
class FabricTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=json.loads((HERE/'effective_eligibility.json').read_text());cls.pack=json.loads((HERE/'resolved_placements.json').read_text());cls.budget=json.loads((HERE/'compile_budget.json').read_text());cls.compiled=json.loads((HERE/'compile_report.json').read_text());cls.review=json.loads((HERE/'native_review.json').read_text());cls.handoff=json.loads((HERE/'terrain_handoff.json').read_text());cls.hr=json.loads((HERE/'handoff_review.json').read_text())
 def test_01_effective_source_binding(self):
  self.assertEqual(self.source['base_eligibility'],ref(HERE/'eligibility.json'));self.assertEqual(self.pack['eligibility'],ref(HERE/'effective_eligibility.json'));self.assertEqual(len(self.source['properties']),19)
 def test_02_five_bounded_native_compiles(self):
  self.assertEqual(len(self.compiled['assets']),5);self.assertLessEqual(self.compiled['total_candidate_visits'],263705);self.assertTrue(all(q['valid'] for q in self.compiled['progress']))
 def test_03_native_exterior_bijections(self):
  for q in self.compiled['progress']:self.assertEqual(q['missing_unit_faces'],0);self.assertEqual(q['duplicate_or_internal_unit_faces'],0)
 def test_04_assets_are_hash_bound(self):
  for a in self.pack['assets'].values():
   for kind in ('master','render'):self.assertEqual(ref(ROOT/a[kind+'_path'])['sha256'],a[kind+'_sha256'])
 def test_05_rigid_native_placements(self):
  self.assertEqual(len(self.pack['placements']),38)
  for p in self.pack['placements']:self.assertEqual(p['scale'],[1,1,1]);self.assertAlmostEqual(p['pad_floor_y_m']-p['position_m'][1],.5);self.assertTrue(p['native_union_verified'])
 def test_06_thresholds_from_actual_union_quads(self):
  self.assertEqual(len(self.pack['actual_doors']),126)
  for d in self.pack['actual_doors']:self.assertTrue(d['actual_union_threshold_evidence']);self.assertGreater(min(q['native_leaf_width_m'] for q in d['actual_union_threshold_evidence']),0)
 def test_07_exact_source_native_mask_correspondence(self):
  for p in self.pack['native_union_mask_proofs']:
   for k,v in p.items():
    if k!='group_id':self.assertLess(v,1e-5)
 def test_08_full_width_static_clearance(self):
  self.assertEqual(self.review['pack'],ref(HERE/'resolved_placements.json'));self.assertEqual(self.review['issues'],[])
 def test_09_finite_material_partition(self):
  self.assertEqual(self.hr['handoff'],ref(HERE/'terrain_handoff.json'));self.assertEqual(self.hr['issues'],[])
  for q in self.handoff['checks']:self.assertLess(q['partition_error_m2'],1e-4)
 def test_10_public_gate_profiles(self):
  for p in self.handoff['properties']:
   gate=p['finite_gate_approach'];self.assertGreaterEqual(gate['minimum_connector_width_m'],3.49);self.assertLessEqual(max(triangle_grade(t) for t in gate['triangles_xyz_m']),.12+1e-7);self.assertFalse(gate['capsule_validated'])
 def test_11_exact_retirement_scope(self):
  self.assertEqual(len(self.pack['replaced_placement_ids']),58);self.assertEqual(len(set(self.pack['replaced_placement_ids'])),58)
  old=json.loads((HERE.parent/'merchant_block011/resolved_placements.json').read_text());self.assertFalse(set(old['replaced_placement_ids'])&set(self.pack['replaced_placement_ids']))
 def test_12_finite_frontage_and_court_program(self):
  self.assertEqual(self.source['summary']['continuous_native_street_front_m'],360);self.assertGreater(self.source['summary']['service_court_area_m2'],4800);self.assertEqual(set(p['family'] for p in self.source['properties']),set(FAMILIES))
 def test_13_no_implicit_scene_activation(self):
  self.assertFalse(self.pack['runtime_ready']);self.assertFalse(self.pack['applied_to_scene']);self.assertEqual(self.compiled['whole_house_scales'],0);self.assertEqual(self.compiled['output_cell_edits'],0)
 def test_14_owner_filter_preserves_rejected_estate_conflict(self):
  f=json.loads((HERE/'exact_owner_filter.json').read_text());self.assertEqual(len(f['rejected_ids']),1);self.assertTrue(any(q['conflicts'] for q in f['checks']));self.assertFalse(set(f['rejected_ids'])&set(q['id'] for q in self.source['properties']))
 def test_15_all_remaining_owned_ground_named(self):
  for p in self.handoff['properties']:
   self.assertEqual({q['role'] for q in p['materials']},{'native_foundation','connected_pedestrian_and_goods_access','productive_kitchen_garden','shared_goods_handling_court','service_apron_and_yard'});self.assertEqual(p['retained_lower_ground']['height_policy'],'retain exact inherited ground; no flattening');self.assertGreaterEqual(next(q['area_m2'] for q in p['materials'] if q['role']=='productive_kitchen_garden'),15.99)
if __name__=='__main__':unittest.main(verbosity=2)
