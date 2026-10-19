import unittest,math
from . import profile_mesh as m
from .. import author as a

def rect(x0,z0,x1,z1):return[[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
class Profiles(unittest.TestCase):
 def test_affine_shared_seam_and_upward(self):
  domains=[rect(0,0,6,3),rect(4,1,9,4)];plane=[.04,.03,2.]
  fixed=[dict(polygon_xz_m=rect(0,0,1,3),plane_y_xz_m=plane),dict(polygon_xz_m=rect(8,1,9,4),plane_y_xz_m=plane)]
  r=m.solve(domains,fixed,lambda p:a.common.height(plane,p));self.assertEqual(r['status'],'PASSED_FINITE_TRIANGLE_GRADE');self.assertEqual(r['downward_triangles'],0);self.assertAlmostEqual(r['finite_domain_area_m2'],29.);self.assertLessEqual(r['maximum_gradient'],.12+1e-8)
  vertices={}
  for t in r['triangles']:
   for x,y,z in t['vertices_xyz_m']:
    self.assertAlmostEqual(y,a.common.height(plane,[x,z]),places=7)
    if(x,z)in vertices:self.assertEqual(vertices[x,z],y)
    vertices[x,z]=y
 def test_fixed_cliff_is_rejected(self):
  r=m.solve([rect(0,0,2,2)],[dict(polygon_xz_m=rect(0,0,.5,2),plane_y_xz_m=[0,0,0]),dict(polygon_xz_m=rect(1.5,0,2,2),plane_y_xz_m=[0,0,1])],lambda p:p[0]/2)
  self.assertEqual(r['status'],'INFEASIBLE_FIXED_FINITE_PROFILE')
 def test_conflicting_fixed_overlap_is_not_averaged(self):
  r=m.solve([rect(0,0,3,2)],[dict(polygon_xz_m=rect(0,0,2,2),plane_y_xz_m=[0,0,0]),dict(polygon_xz_m=rect(1,0,3,2),plane_y_xz_m=[0,0,.2])],lambda p:0.)
  self.assertEqual(r['status'],'INCOMPATIBLE_FIXED_REGIONS')
 def test_near_vertex_welding(self):
  points,tris,proof=m.topology([rect(0,0,1,1),[[1+4e-10,0],[2,0],[2,1],[1+4e-10,1]]]);self.assertGreater(proof['maximum_vertex_weld_distance_m'],0);self.assertLess(proof['maximum_vertex_weld_distance_m'],1e-9)
if __name__=='__main__':unittest.main()
