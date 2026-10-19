import json,math,unittest
from .author_density import HERE,ROOT,ref,PLAN,PRIOR
from world_city.runtime_city.checks import placement as geo

def read(name):return json.loads((HERE/name).read_text())
class DensityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=read('resolved_placements.json');cls.d=read('candidate.json');cls.g=read('owned_grounds.json');cls.proof=read('actual_geometry_proof.json')
 def test_hash_bindings(self):
  for key in ('candidate','compile_report','actual_geometry_proof','baseline_native_pack'):
   r=self.p[key];self.assertEqual(r,ref(ROOT/r['path']))
  self.assertEqual(self.p['source_plan_sha256'],ref(PLAN)['sha256']);self.assertEqual(self.g['candidate'],ref(HERE/'candidate.json'))
 def test_measured_density(self):
  s=self.p['summary'];self.assertGreaterEqual(s['after_body_coverage'],.4);self.assertLessEqual(s['after_body_coverage'],.55);self.assertGreater(s['after_body_coverage'],s['before_body_coverage']*2)
  self.assertEqual(len(self.p['replaced_placement_ids']),56);self.assertEqual(len(self.p['component_placements']),45);self.assertEqual(len(self.p['placements']),16)
 def test_all_native_openings_recorded(self):
  expected=sum(len(self.d['assets'][p['asset_key']]['author_metadata']['entrance'].get('all_positions',[])) or 1 for p in self.d['placements']);self.assertEqual(expected,104);self.assertEqual(len(self.p['access_proposals']),expected)
  for p in self.p['access_proposals']:self.assertFalse(p['population_or_household_inference']);self.assertTrue(p['physical_opening_only']);self.assertAlmostEqual(p['actual_door_xyz_m'][1],2.5)
 def test_common_unions_have_no_internal_faces(self):
  self.assertEqual(len(self.proof['assets']),12);self.assertEqual(self.proof['internal_render_unit_faces'],0);self.assertEqual(self.proof['missing_render_unit_faces'],0)
  for a in self.p['assets'].values():self.assertEqual(ref(ROOT/a['render_path'])['sha256'],a['render_sha256']);self.assertTrue(all(c['pass'] for c in a['constraints']))
 def test_horizontal_review(self):
  review=read('geometry_review.json');self.assertTrue(review['valid_horizontal_source']);self.assertEqual(review['issues'],[]);self.assertEqual(review['candidate'],ref(HERE/'candidate.json'));self.assertGreater(review['projection']['after']['roof_union_inside_block_ratio'],review['projection']['before']['roof_union_inside_block_ratio'])
 def test_all_grounds_owned_and_access_linked(self):
  self.assertLess(abs(self.g['area_accounting_delta_m2']),1e-4);self.assertEqual(len(self.g['grounds']),19);self.assertEqual(len(self.g['paths']),19);self.assertFalse(self.g['unwalkable_narrow_margin_ids']);paths={p['id'] for p in self.g['paths']}
  for g in self.g['grounds']:self.assertGreater(g['area_m2'],0);self.assertTrue(g['access_ids']);self.assertTrue(set(g['access_ids'])<=paths)
 def test_ground_links_clear_actual_roofs(self):
  for path in self.g['paths']:
   for poly in path['reserved_polygons_xz_m']:
    for p in self.d['placements']:self.assertFalse(geo.positive_area_overlap(poly,p['actual_outer_footprint_xz_m'],1e-5),(path['id'],p['id']))
 def test_native_scale_floor_semantics(self):
  for p in self.p['component_placements']:self.assertEqual(p['scale'],[1,1,1]);self.assertAlmostEqual(p['position_m'][1]+p['cached_primary_door_local_y_m'],p['pad_floor_y_m'])
if __name__=='__main__':unittest.main()
