import math,unittest
from . import interfaces as a
from . import review
from world_city.runtime_city.checks import placement as g
class Tests(unittest.TestCase):
 def test_civic_partition_and_interfaces(self):
  floors=[f for f in a.FLOORS if f['floor_y_m']==4];self.assertTrue(floors);count=0
  for f in floors:
   for p in f['polygon_xz_m']:
    x,z=8*math.floor(p[0]/8),8*math.floor(p[1]/8);b=[x,z,x+8,z+8];rs=a.clip_floor_domains(b)
    self.assertAlmostEqual(sum(g.polygon_area(r['polygon_xz_m']) for r in rs),64,places=6)
    for i,r in enumerate(rs):
     for q in rs[:i]:self.assertLess(g.polygon_area(g.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m'])),1e-7)
    for edge in a.floor_interface_quads(b,rs):
     count+=1;self.assertTrue(any(abs(y-4)<1e-9 for y in edge['left_y_m']+edge['right_y_m']))
  self.assertGreater(count,0)
 def test_floor_height_is_not_composite_boundary_height(self):
  for f in a.FLOORS:
   r=dict(kind='common_floor_hole',floor_y_m=f['floor_y_m'])
   for p in f['polygon_xz_m']:self.assertEqual(review.surface_height_at(r,*p),f['floor_y_m'])
 def test_previous_hashes_stay_valid(self):review.prior.snapshot_check()
if __name__=='__main__':unittest.main()
