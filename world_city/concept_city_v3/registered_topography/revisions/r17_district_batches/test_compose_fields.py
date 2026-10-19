import unittest
from . import author as a,compose_fields as c,regeneration_interfaces as r,side_clearance as s
class FieldTests(unittest.TestCase):
 def scene(self):
  p=[[0,0],[4,0],[4,4],[0,4]]
  return dict(materials={'ground_earth':{},'ground_stone':{}},surfaces={'ground_earth':[v for t in a.fan_upward([[x,0,z]for x,z in p])for v in t]},boxes=[])
 def test_profile_is_emitted_once(self):
  owner=dict(id='FIELD',action='field',kind='ramp',polygon_xz_m=[[1,1],[3,1],[3,3],[1,3]],plane_y_xz_m=[.1,0,0],material='ground_stone')
  patch,report=c.build(self.scene(),[owner]);vs=patch['appended_surfaces']['ground_stone'];self.assertAlmostEqual(sum(a.normal_y(vs[j:j+3])/2 for j in range(0,len(vs),3)),4);self.assertEqual(len(report['finite_regenerated_fields']),1);self.assertTrue(all(a.normal_y(vs[j:j+3])>0 for j in range(0,len(vs),3)))
  for v in vs:self.assertAlmostEqual(v[1],.1*v[0])
 def test_hole_priority(self):
  hole=dict(id='NATIVE',action='hole',polygon_xz_m=[[1,1],[2,1],[2,2],[1,2]])
  field=dict(id='FIELD',action='field',polygon_xz_m=[[0,0],[4,0],[4,4],[0,4]],plane_y_xz_m=[0,0,1],material='ground_stone')
  patch,report=c.build(self.scene(),[hole,field]);self.assertAlmostEqual(report['finite_regenerated_fields'][0]['area_m2'],15)
 def test_undefined_field_rejected(self):
  field=dict(id='FIELD',action='field',polygon_xz_m=[[3,3],[5,3],[5,5],[3,5]],plane_y_xz_m=[0,0,1],material='ground_stone')
  with self.assertRaises(ValueError):c.build(self.scene(),[field])
 def test_retained_vertical_partition(self):
  triangle=[[0,0,0],[4,0,0],[4,2,0]];outside,inside=r.subtract_plan(triangle,[[1,-1],[3,-1],[3,1],[1,1]]);self.assertAlmostEqual(sum(s.area3d(p)for p in outside)+s.area3d(inside),s.area3d(triangle));self.assertGreater(s.area3d(inside),0)
 def test_boundary_wall_is_not_erased(self):
  t=[[0,0,0],[4,0,0],[4,2,0]];out,inside=r.subtract_plan(t,[[0,0],[4,0],[4,4],[0,4]]);self.assertEqual(out,[t]);self.assertFalse(inside)
if __name__=='__main__':unittest.main()
