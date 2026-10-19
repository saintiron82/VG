"""Small reproducible regressions for the bounded seven-compound candidate."""
import json,math,unittest
from .grammar import HERE,ROOT,PLAN,ORDINARY,ref,g

def read(name):return json.loads((HERE/name).read_text())

class MerchantCandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=read('resolved_placements.json');cls.s=read('proposal.json');cls.b=read('compile_budget.json');cls.c=read('compile_report.json')
 def test_source_binding(self):
  self.assertEqual(self.p['proposal'],ref(HERE/'proposal.json'));self.assertEqual(self.s['sources']['plan'],ref(PLAN));self.assertEqual(self.s['sources']['ordinary'],ref(ORDINARY));self.assertEqual(self.b['grammar'],ref(HERE/'grammar.py'))
 def test_bounded_shared_compile(self):
  self.assertEqual(len(self.p['assets']),3);self.assertEqual(self.c['total_candidate_visits'],452636)
  for a in self.c['progress']:
   self.assertLessEqual(a['candidate_cells'],240000);self.assertLessEqual(a['cell_count'],70000);self.assertTrue(a['valid']);self.assertEqual(a['missing_unit_faces'],0);self.assertEqual(a['duplicate_or_internal_unit_faces'],0)
 def test_render_hashes(self):
  for a in self.p['assets'].values():
   for kind in ('master','compiled','render'):self.assertEqual(ref(ROOT/a[kind+'_path'])['sha256'],a[kind+'_sha256'])
 def test_rigid_group_ownership(self):
  members=[x for p in self.p['placements'] for x in p['source_member_ids']];self.assertEqual(len(members),34);self.assertEqual(len(set(members)),34);self.assertEqual(len(self.p['placements']),14)
  for p in self.p['placements']:self.assertEqual(p['scale'],[1,1,1]);self.assertAlmostEqual(p['pad_floor_y_m']-p['position_m'][1],.5)
 def test_all_native_thresholds(self):
  self.assertEqual(len(self.p['actual_doors']),48)
  for d in self.p['actual_doors']:
   self.assertTrue(d['actual_union_threshold_evidence']);self.assertAlmostEqual(d['actual_runtime_door_local_xyz_m'][1],.5);self.assertFalse(d['population_or_household_inference'])
 def test_all_full_width_native_routes(self):
  r=read('native_review.json');self.assertEqual(r['pack'],ref(HERE/'resolved_placements.json'));self.assertEqual(r['issues'],[]);self.assertEqual(r['counts']['rounded_joins'],136);self.assertEqual(r['counts']['foundation_regions'],74)
 def test_exact_replacement_ledger(self):
  old=json.loads(ORDINARY.read_text());ids={p['id'] for p in old['placements']};self.assertEqual(len(self.p['replaced_placement_ids']),39);self.assertTrue(set(self.p['replaced_placement_ids'])<=ids);self.assertEqual(set(self.p['replaced_placement_ids']),{x for p in self.s['properties'] for x in p['source_retired_native_ids']})
 def test_whole_block_roofs(self):
  c=read('coverage_report.json');self.assertEqual(c['pack'],ref(HERE/'resolved_placements.json'))
  for block in c['blocks']:self.assertGreater(block['after_roof_area_m2'],block['before_roof_area_m2']);self.assertLess(block['after_roof_coverage'],1)
 def test_finite_material_floor_handoff(self):
  h=read('terrain_handoff.json');self.assertEqual(h['pack'],ref(HERE/'resolved_placements.json'));self.assertEqual(len(h['properties']),7)
  for q in h['checks']:self.assertLess(q['partition_error_m2'],1e-4);self.assertLess(q['gate_public_profile_error_m'],1e-7)
  for p in h['properties']:
   a=p['finite_gate_approach'];self.assertEqual(len(a['endpoint_profile']),17);self.assertEqual(a['width_m'],3.5);self.assertLessEqual(a['maximum_profile_grade'],.12)
 def test_unreviewed_ground_not_promoted(self):
  self.assertFalse(self.p['runtime_ready']);self.assertFalse(self.p['applied_to_scene']);self.assertTrue(self.p['retired_source_residuals']);self.assertTrue(all('unresolved' in q['access_status'].lower() or 'require' in q['access_status'].lower() for q in self.p['retired_source_residuals']))
 def test_reusable_fixed_cache(self):
  from .reuse import resolve_recipe_ranges
  expected={p['id']:p for p in self.p['placements']}
  for prop in self.s['properties']:
   result=resolve_recipe_ranges(prop);self.assertEqual(result['unresolved'],[]);self.assertEqual(result['compile_count'],0)
   for p in result['placements']:
    for field in ('asset_key','position_m','yaw_rad','scale','source_member_ids'):self.assertEqual(p[field],expected[p['id']][field])
 def test_finite_handoff_regression(self):
  r=read('handoff_review.json');self.assertEqual(r['issues'],[]);self.assertEqual(r['handoff'],ref(HERE/'terrain_handoff.json'));self.assertEqual(r['counts']['retaining_edges'],27)

if __name__=='__main__':unittest.main()
