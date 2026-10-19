"""Bounded read-only tests of the sealed common bridge result; never compile."""
import json,math,unittest
from .author import HERE,ROOT,sha,bounds,overlaps
from .compile_bridge import deck_y,SEALED,CANDIDATE
from voxel_character.common import core
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_topography import author as terrain

def read(name):return json.loads((HERE/name).read_text())
class CompiledBridgeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pack=read('resolved_placements.json');cls.proof=read('actual_geometry_proof.json');cls.overlay=read('continuous_deck_overlay.json');cls.report=read('compile_report.json');cls.master=read('assembly_source.json')
 def test_bound_inputs_and_outputs(self):
  self.assertEqual(sha(CANDIDATE),SEALED)
  for container in (self.pack,self.proof,self.report):
   for value in container.values():
    if isinstance(value,dict) and set(('path','sha256'))<=value.keys():self.assertEqual(sha(ROOT/value['path']),value['sha256'])
  for value in self.master['provenance'].values():
   if isinstance(value,dict) and set(('path','sha256'))<=value.keys():self.assertEqual(sha(ROOT/value['path']),value['sha256'])
 def test_common_result_and_native_pose(self):
  self.assertTrue(self.report['valid']);self.assertTrue(all(r['pass'] for r in self.report['constraints']))
  self.assertEqual(len(self.pack['assets']),1);self.assertEqual(len(self.pack['placements']),1)
  self.assertEqual(self.pack['placements'][0]['scale_xyz'],[1,1,1]);core.transform(self.pack['placements'][0]['transform'])
  self.assertLessEqual(self.report['candidate_cells'],3000000);self.assertLess(self.report['peak_rss_mib'],850)
 def test_mesh_face_bijection_and_foundations(self):
  p=self.proof['render_face_proof'];self.assertEqual(p['render_expanded_unit_faces'],p['exposed_occupancy_unit_faces'])
  self.assertEqual(p['internal_or_duplicate_unit_faces'],0);self.assertEqual(p['missing_exterior_unit_faces'],0)
  self.assertEqual(len(self.proof['support_samples']),90);self.assertGreaterEqual(self.proof['minimum_actual_sampled_foundation_embed_m'],.5)
  self.assertTrue(all(p['occupied_below_bed'] for p in self.proof['support_samples']))
 def test_actual_navigation_and_port_opening(self):
  self.assertEqual(len(self.proof['navigation_samples']),1425);self.assertGreaterEqual(self.proof['minimum_actual_sampled_navigation_clearance_m'],3)
  self.assertTrue(self.proof['port_opening_samples']);self.assertFalse(any(p['overhead_blocked_cells'] for p in self.proof['port_opening_samples']))
  self.assertIn('concave',self.pack['placements'][0]['collision_policy'])
 def test_disjoint_exact_ownership(self):
  regions=self.overlay['regions']
  for i,r in enumerate(regions):
   for p,y in zip(r['polygon_xz_m'],r['vertex_y_m']):self.assertAlmostEqual(deck_y(self.overlay,*p),y,places=8)
   for q in regions[:i]:
    if overlaps(bounds(r['polygon_xz_m']),bounds(q['polygon_xz_m'])):self.assertLess(geo.polygon_area(geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m'])),1e-6)
 def test_grade_exception_is_explicit(self):
  d=read('local_junction_criterion.json');self.assertFalse(d['previous_10_percent_criterion_pass']);self.assertTrue(d['local_15_percent_criterion_pass'])
  self.assertLessEqual(d['measured_maximum_triangle_gradient'],.15);self.assertLessEqual(self.overlay['maximum_profile_grade'],.100000001)
  self.assertLessEqual(d['native_continuous_top_approximation']['maximum_sampled_top_plane_error_m'],.015)
 def test_terminal_tolerance_and_gate_width(self):
  for tr in self.overlay['terminal_transitions']:
   for e in tr['outer_edge_segments']:
    for p,y in ((e['a_xz_m'],e['a_y_m']),(e['b_xz_m'],e['b_y_m'])):self.assertLessEqual(abs(deck_y(self.overlay,*p)-y),.001)
  d=self.overlay['terminal_width_contract'];self.assertEqual(d['total_shared_corridor_m'],7);self.assertEqual(d['gate_cart_band_m'],4)
  self.assertEqual(self.overlay['terminal_continuity_tolerance_m'],.001)
 def test_no_false_physics_or_exact_floor_claim(self):
  self.assertGreater(self.proof['maximum_actual_floor_quantization_delta_m'],.1)
  self.assertIn('No capsule',self.proof['physics_claim']);self.assertTrue(any('Capsule' in x for x in self.pack['limits']))
if __name__=='__main__':unittest.main()
