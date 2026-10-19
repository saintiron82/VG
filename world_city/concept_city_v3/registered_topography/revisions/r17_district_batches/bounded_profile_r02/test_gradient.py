import math,unittest
from .gradient import solve_field
from .. import author as a
class GradientTest(unittest.TestCase):
 def test_exact_limit_at_angles(self):
  p=[[0.,0.],[1.,0.],[0.,1.],[1.,1.]];t=[[0,1,2],[1,3,2]]
  for angle in [0,.031,.17,.5,1.,2.,3.7,5.9]:
   y=[.12*(x*math.cos(angle)+z*math.sin(angle))+8 for x,z in p];r=solve_field(p,t,dict(enumerate(y)),y)
   self.assertEqual(r['status'],'PASSED_FINITE_TRIANGLE_GRADE');self.assertLessEqual(r['maximum_gradient'],.12000001);self.assertEqual(r['heights_m'],y)
   self.assertTrue(all(a.normal_y(f['vertices_xyz_m'])>0 for f in r['triangles']))
 def test_excess_fixed_plane_rejected(self):
  p=[[0.,0.],[1.,0.],[0.,1.]];y=[0.,.121,0.]
  self.assertEqual(solve_field(p,[[0,1,2]],dict(enumerate(y)),y)['status'],'INFEASIBLE_FIXED_FINITE_PROFILE')
 def test_free_vertex_and_fixed_seam(self):
  p=[[0.,0.],[1.,0.],[0.,1.]];r=solve_field(p,[[0,1,2]],{0:8.,1:8.1},[8.,8.1,10.])
  self.assertEqual(r['status'],'PASSED_FINITE_TRIANGLE_GRADE');self.assertEqual(r['heights_m'][:2],[8.,8.1]);self.assertLessEqual(r['maximum_gradient'],.12000001)
if __name__=='__main__':unittest.main()
