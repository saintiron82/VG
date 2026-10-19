import unittest,math
from . import bridge as a
from world_city.runtime_city.checks import placement as g
class Tests(unittest.TestCase):
 def test_regions_disjoint(self):
  for i,r in enumerate(a.REGIONS):
   for s in a.REGIONS[:i]:
    if a.review.base._overlap(a.review.base._bounds(r['polygon_xz_m']),a.review.base._bounds(s['polygon_xz_m'])):
     self.assertLess(g.polygon_area(g.convex_intersection(r['polygon_xz_m'],s['polygon_xz_m'])),1e-7)
 def test_profile_split_preserves_area_and_planes(self):
  parts=a.bridge_surface_domains();self.assertAlmostEqual(sum(g.polygon_area(r['polygon_xz_m']) for r in parts),sum(g.polygon_area(r['polygon_xz_m']) for r in a.REGIONS),places=5)
  for r in parts:
   p=r['polygon_xz_m'];y=r['vertex_y_m'];q=[sum(v[k] for v in p)/len(p) for k in(0,1)]
   self.assertAlmostEqual(a.bridge_surface_height_at(r,*q),sum(y)/len(y),places=8)
 def test_dry_masks_preserve_water(self):
  for r in a.dry_ground_replacement_domains():
   for w in a.review.finite_water_polygons():
    if a.review.base._overlap(a.review.base._bounds(r['polygon_xz_m']),a.review.base._bounds(w['polygon_xz_m'])):
     self.assertLess(g.polygon_area(g.convex_intersection(r['polygon_xz_m'],w['polygon_xz_m'])),1e-7)
 def test_fixed_datums_and_bounded_grade(self):
  self.assertTrue(a.endpoint_audit()['all_fixed_centerline_datums_preserved']);self.assertLessEqual(a.DATA['maximum_profile_grade'],.10000001)
if __name__=='__main__':unittest.main()
