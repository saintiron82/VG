import unittest,json,pathlib,hashlib,math
O=pathlib.Path(__file__).resolve().parent
read=lambda n:json.loads((O/n).read_text())
class AddedEvidence(unittest.TestCase):
 def test_port_scopes(self):
  d=read('port_evidence_audit.json');self.assertTrue(all(d['checks'].values()))
  for k in ['capsule','cart']:self.assertEqual(d['result'][k]['positive_passed'],4);self.assertEqual(d['result'][k]['negative_passed'],2)
  self.assertTrue(all(abs(r['length_m']-14)<1e-4 for r in d['local_scopes']))
 def test_ray_original_fail_retained(self):
  d=read('exact_ray_diagnostic.json');self.assertEqual(d['observation']['frame'],94);self.assertFalse(d['observed_case_status']['pass']);self.assertEqual(d['inspection'][0]['exact_projected_containing_faces'],1);self.assertEqual(d['inspection'][1]['exact_projected_containing_faces'],0)
 def test_minimal_same_plane_split(self):
  d=read('seam_fix_candidate/proof.json');self.assertEqual(d['source_face_edits'],1);self.assertEqual(d['replacement_triangles'],3);self.assertLess(d['absolute_area_difference_m2'],1e-10)
 def test_water_actual_lengths(self):
  d=read('actual_water_branch_distances.json');self.assertEqual(d['before']['count'],536);self.assertEqual(d['after']['unreachable'],35);self.assertAlmostEqual(d['actual_draw_candidates'][0]['actual_branch_length_m'],5.7);self.assertAlmostEqual(d['actual_draw_candidates'][1]['actual_branch_length_m'],3.1);self.assertTrue(all('frozen_r01' in k for k in d['sources'] if 'public_water' in k))
 def test_strict_gate_join(self):
  d=read('gate_r05_partial_access_comparison.json');self.assertEqual(len(d['gates']),3)
  for r in d['gates'][1:]:self.assertTrue(any(a['strict20mm_observed_match'] for a in r['attachments']));self.assertTrue(all(a['old_public_station']['height_gap_m']<=.02 for a in r['attachments'] if a['strict20mm_observed_match']))
if __name__=='__main__':unittest.main()
