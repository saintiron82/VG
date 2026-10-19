import json,math,unittest
from pathlib import Path
from .coverage import audit
from .. import author as a
HERE=Path(__file__).resolve().parent
class BundleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=json.loads((HERE/'profile_bundle.json').read_bytes())
 def test_source_hashes(self):
  for r in self.d['source_refs']:self.assertEqual(a.sha(a.ROOT/r['path']),r['sha256'])
 def test_six_profiles_and_unchanged_e3(self):
  self.assertEqual([r['owner_id']for r in self.d['owners']],['E1','E2','E4','E5','E6','E7']);self.assertEqual(self.d['unchanged_owner_ids'],['E3'])
 def test_positive_upward_finite(self):
  for r in self.d['owners']:
   for t in r['triangles']:
    self.assertGreater(a.normal_y(t['vertices_xyz_m']),0);self.assertTrue(all(math.isfinite(x)for p in t['vertices_xyz_m']for x in p))
 def test_exact_domain_coverage(self):
  for r in self.d['owners']:
   c=audit(r['private_domain_polygons_xz_m'],r['triangles']);self.assertLess(c['missing_area_m2']+c['outside_area_m2'],1e-7);self.assertLess(c['positive_overlap_area_m2'],1e-7)
 def test_actual_plane_grade(self):
  for r in self.d['owners']:
   self.assertLessEqual(max(math.hypot(*a.common.plane(t['vertices_xyz_m'])[:2])for t in r['triangles']),r['grade_limit']+1e-7)
 def test_actual_fixed_seam_evidence(self):
  for r in self.d['owners']:
   p=json.loads((a.ROOT/r['source_proposal']['path']).read_bytes());self.assertEqual(p['result']['boundary_errors'],[]);self.assertLessEqual(p['result']['result']['maximum_fixed_error_m'],1e-10)
 def test_explicit_vertical_steps(self):
  for r in self.d['owners']:
   for s in r['vertical_risers']:
    for t in s['triangles_xyz_m']:self.assertLess(abs(a.normal_y(t)),1e-10)
 def test_e1_split_tapers_to_exact_inner_profile(self):
  r=next(r for r in self.d['owners']if r['owner_id']=='E1');p=json.loads((a.ROOT/r['source_proposal']['path']).read_bytes());field=p['result']['result'];ys=field['heights_m']
  for left,right,delta in p['result']['linear_taper_equalities']:self.assertAlmostEqual(ys[right]-ys[left],delta,places=10)
  self.assertAlmostEqual(p['result']['linear_taper_equalities'][-1][2],0.,places=12)
 def test_native_sources_are_not_regenerated_here(self):
  self.assertFalse(self.d['activation']);self.assertTrue(all(not r['runtime_approval'] for r in self.d['owners']))
 def test_exceptions_are_explicit_and_not_runtime(self):
  r={r['owner_id']:r for r in self.d['owners']};self.assertEqual(r['E2']['grade_limit'],.35);self.assertIn('steps',r['E2']['design_policy']);self.assertEqual(r['E5']['grade_limit'],.25);self.assertFalse(self.d['runtime_approval']);self.assertFalse(self.d['activation'])
if __name__=='__main__':unittest.main()
