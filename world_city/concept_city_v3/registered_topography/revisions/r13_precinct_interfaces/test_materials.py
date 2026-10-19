import math,unittest
from . import materials as m
class PartitionTests(unittest.TestCase):
 def test_known_failure(self):
  rs=m.surface_domains([320,304,336,320],False)
  self.assertAlmostEqual(sum(m.geo.polygon_area(r['polygon_xz_m']) for r in rs),256,places=6)
  for i,r in enumerate(rs):
   for q in rs[:i]:self.assertLess(m.geo.polygon_area(m.geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m'])),1e-7)
 def test_normalization_scope(self):
  self.assertEqual(len(m.NORMALIZATION),1)
  self.assertEqual(m.NORMALIZATION[0]['material_region_id'],'DENS_B15E_GROUP_006:SHARED_WORKYARD:7')
  self.assertLess(abs(m.NORMALIZATION[0]['area_delta_m2']),1e-10)
 def test_keep_collinear_knots(self):
  p=[[0,0],[1,0],[2,0],[2,2],[0,2],[0,0]]
  self.assertEqual(m.polygon(p),p[:-1])
 def test_unchanged_heights(self):
  for name in ['height_at','land_height_at','surface_height_at','source_surface_height_at','road_height_at']:
   self.assertIs(getattr(m,name),getattr(m.prior,name))
 def test_native_traffic_identity(self):
  original=m.prior.surface_domains([320,304,336,320],False)
  output=m.surface_domains([320,304,336,320],False)
  expected={r['owner_id'] for r in original if not m.eligible(r)}
  self.assertTrue(expected.issubset({r['owner_id'] for r in output}))
if __name__=='__main__':unittest.main()
