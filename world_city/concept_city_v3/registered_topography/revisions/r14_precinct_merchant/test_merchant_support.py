import unittest,json
from . import merchant_support as s
class SupportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.compiled=json.loads((s.HERE/'support/merchant_support.compiled.json').read_bytes());cls.render=json.loads((s.HERE/'support/merchant_support.render.json').read_bytes());cls.cells={tuple(c[:3]) for c in cls.compiled['cells']}
 def test_exact_native_grid_columns(self):
  want=set()
  for poly in s.POLYS:
   p=[s.local(q) for q in poly];xs=[q[0] for q in p];zs=[q[1] for q in p]
   for x in range(round(min(xs)/s.PITCH),round(max(xs)/s.PITCH)):
    for z in range(round(min(zs)/s.PITCH),round(max(zs)/s.PITCH)):
     if s.a.geo.point_in_convex_polygon([(x+.5)*s.PITCH,(z+.5)*s.PITCH],p,1e-9):
      for y in range(round(s.BOTTOM/s.PITCH),round(s.TOP/s.PITCH)):want.add((x,y,z))
  self.assertEqual(self.cells,want)
 def test_top_area_and_contact(self):
  area=0
  for g in self.render['groups']:
   for q in g['quads']:
    u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[0][i] for i in range(3)]
    if u[2]*v[0]-u[0]*v[2]>1e-9:
     self.assertEqual(q[0][1],3.5);area+=s.a.geo.polygon_area([[v[0],v[2]] for v in q])
  self.assertAlmostEqual(area,679.5)
 def test_bottom_and_budget(self):
  self.assertEqual(min(y for x,y,z in self.cells)*s.PITCH,.5)
  self.assertLess(self.compiled['candidate_cells'],s.CAP)
  pre=json.loads((s.HERE/'merchant_support_preflight.json').read_bytes());self.assertGreaterEqual(pre['minimum_burial_m'],.5)
if __name__=='__main__':unittest.main()
