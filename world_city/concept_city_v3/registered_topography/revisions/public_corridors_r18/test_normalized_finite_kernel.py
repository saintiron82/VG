"""Explicit bounded normalization behavior; legacy exact-strip failure retained."""
import math,unittest
from . import finite_geometry_r03 as g
class Tests(unittest.TestCase):
 def test_genuine_strip_above_bound_remains(self):
  square=[[0.,0.],[1.,0.],[1.,1.],[0.,1.]];p=[[.5,0.],[.500000002,0.],[.500000002,1.],[.5,1.]]
  self.assertGreater(g.area(g.clip(square,p)),1.9e-9)
  self.assertAlmostEqual(g.area(g.clip(square,p))+math.fsum(g.area(q)for q in g.difference(square,p)),1.,places=14)
 def test_below_bound_mask_collapses_explicitly(self):
  p=[[.5,0.],[.5000000005,0.],[.5000000005,1.],[.5,1.]]
  self.assertEqual(len(g.normalize_mask(p)),2)
  self.assertFalse(g.clip([[0,0],[1,0],[1,1],[0,1]],p))
 def test_near_duplicate_surviving_vertices_unchanged(self):
  p=[[0.,0.],[1e-13,1e-13],[1.,0.],[1.,1.],[0.,1.],[1e-13,1e-13]]
  self.assertEqual(g.normalize_mask(p),[p[i]for i in(0,2,3,4)])
 def test_ordinary_half_partition(self):
  p=[[0.,0.],[1.,0.],[1.,1.],[0.,1.]];q=[[.5,-1],[2,-1],[2,2],[.5,2]]
  self.assertAlmostEqual(g.area(g.clip(p,q)),.5)
  self.assertAlmostEqual(math.fsum(g.area(v)for v in g.difference(p,q)),.5)
if __name__=='__main__':unittest.main()
