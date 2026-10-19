import unittest,json,math
from . import support as s
class SupportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.compiled=json.loads((s.HERE/'support/abbey_support.compiled.json').read_bytes());cls.render=json.loads((s.HERE/'support/abbey_support.render.json').read_bytes());cls.cells={tuple(c[:3]) for c in cls.compiled['cells']}
 def test_exact_native_bearing_columns(self):
  want=set()
  for r in s.BEARINGS:
   p=r['polygon_xz_m'];xs=[q[0]-s.ORIGIN[0] for q in p];zs=[q[1]-s.ORIGIN[2] for q in p]
   for x in range(round(min(xs)/s.PITCH),round(max(xs)/s.PITCH)):
    for z in range(round(min(zs)/s.PITCH),round(max(zs)/s.PITCH)):
     if s.geo.point_in_convex_polygon([s.ORIGIN[0]+(x+.5)*s.PITCH,s.ORIGIN[2]+(z+.5)*s.PITCH],p,1e-9):
      for y in range(round(s.BOTTOM/s.PITCH),round(s.TOP/s.PITCH)):want.add((x,y,z))
  self.assertEqual(self.cells,want)
 def test_top_contact_and_burial(self):
  columns={}
  for x,y,z in self.cells:columns.setdefault((x,z),[]).append(y)
  for (x,z),ys in columns.items():
   self.assertEqual((max(ys)+1)*s.PITCH,s.TOP);self.assertEqual(min(ys)*s.PITCH,s.BOTTOM)
   for dx,dz in ((0,0),(0,1),(1,0),(1,1),(.5,.5)):
    land=s.terrain.land_height_at(s.ORIGIN[0]+(x+dx)*s.PITCH,s.ORIGIN[2]+(z+dz)*s.PITCH)
    self.assertGreaterEqual(land-s.BOTTOM,.2-1e-8)
 def test_render_top_union(self):
  area=0
  for g in self.render['groups']:
   for q in g['quads']:
    a=[q[1][i]-q[0][i] for i in range(3)];b=[q[2][i]-q[0][i] for i in range(3)]
    if a[2]*b[0]-a[0]*b[2]>1e-9:
     self.assertEqual(q[0][1],s.TOP);area+=s.geo.polygon_area([[v[0],v[2]] for v in q])
  self.assertAlmostEqual(area,51.5)
 def test_source_budget_and_reservations(self):
  d=json.loads((s.HERE/'support_preflight.json').read_bytes())
  self.assertEqual(d['road_water_conflicts'],[]);self.assertLessEqual(self.compiled['candidate_cells'],s.CAP)
if __name__=='__main__':unittest.main()
