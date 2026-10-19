import unittest,math
from . import finite_geometry_r03 as g
class Tests(unittest.TestCase):
 def setUp(self):self.square=[[0.,0.],[1.,0.],[1.,1.],[0.,1.]]
 def test_half_partition(self):
  p=[[.5,-1.],[1.5,-1.],[1.5,2.],[.5,2.]];self.assertAlmostEqual(g.area(g.clip(self.square,p))+sum(g.area(x)for x in g.difference(self.square,p)),1.,places=14)
 def test_nanometre_strip_is_retained(self):
  p=[[.5,0.],[.500000001,0.],[.500000001,1.],[.5,1.]];self.assertGreater(g.area(g.clip(self.square,p)),9e-10);self.assertAlmostEqual(g.area(g.clip(self.square,p))+sum(g.area(x)for x in g.difference(self.square,p)),1.,places=14)
 def test_no_cross_epsilon_expansion(self):
  p=[[1.+1e-10,0.],[1.+2e-10,0.],[1.+2e-10,1.],[1.+1e-10,1.]];self.assertEqual(g.clip(self.square,p),[])
 def test_cw_ccw(self):self.assertEqual(g.area(g.clip(self.square,self.square[::-1])),1.)
 def test_touching_boundary_has_no_area(self):self.assertEqual(g.clip(self.square,[[1.,0.],[2.,0.],[2.,1.],[1.,1.]]),[])
 def test_union_disjoint(self):
  p=[[.5,0.],[1.5,0.],[1.5,1.],[.5,1.]];u=g.union([self.square,p]);self.assertAlmostEqual(sum(g.area(x)for x in u),1.5);self.assertEqual(g.clip(u[0],u[1]),[])
 def test_translation(self):
  p=[[x+368.625,z-110.25]for x,z in self.square];self.assertAlmostEqual(g.area(p),1.,places=14)
if __name__=='__main__':unittest.main()
