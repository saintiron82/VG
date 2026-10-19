import json,math,unittest
from pathlib import Path
from .. import author as a
HERE=Path(__file__).resolve().parent
class Closure(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.c=json.loads((HERE/'closure_contract.json').read_bytes())
 def test_source_hashes(self):
  for r in self.c['source_refs']:self.assertEqual(a.sha(a.ROOT/r['path']),r['sha256'])
 def test_exact_bottom(self):
  q=self.c['source_native']['vertices_xyz_m'];self.assertTrue(all(v[1]==12.5 for v in q));self.assertLess(a.normal_y(q[:3]),0)
  p=[[v[0],v[2]]for v in q]
  for v in self.c['support_owner']['polygon_xz_m']:self.assertTrue(a.geo.point_in_convex_polygon(v,p,1e-9))
 def test_exact_lacuna_scope(self):
  r=self.c['review'];self.assertLess(r['prior_lacuna_forward_difference_m2'],1e-9);self.assertLess(r['prior_lacuna_reverse_difference_m2'],1e-9);self.assertAlmostEqual(r['footprint_area_m2'],.023546778721096197,12)
 def test_no_walk_or_footing_cut(self):
  r=self.c['review']['protected_route_and_footing_intersections_m2'];self.assertEqual(set(r),{'walk_polygons_xz_m','footing_polygons_xz_m'});self.assertTrue(all(v==0 for v in r.values()))
 def test_vertical_connection_and_exact_heights(self):
  b=self.c['boundary_connection'];self.assertEqual(len(b['triangles_xyz_m']),2)
  for t in b['triangles_xyz_m']:self.assertEqual(a.normal_y(t),0);self.assertEqual({v[1]for v in t},{9.903458865348059,12.5})
  self.assertAlmostEqual(b['area_m2'],b['length_m']*b['rise_m'],12)
 def test_no_top_overlay(self):
  self.assertFalse(self.c['support_owner']['render_top']);self.assertFalse(self.c['support_owner']['walking']);self.assertEqual(self.c['rendered_top_suppression']['polygon_xz_m'],self.c['support_owner']['polygon_xz_m'])
if __name__=='__main__':unittest.main()
