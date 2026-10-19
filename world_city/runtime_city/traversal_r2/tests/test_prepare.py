import importlib.util, math, unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'prepare.py';spec=importlib.util.spec_from_file_location('prepare_r2',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PreparationTests(unittest.TestCase):
 def test_bounds_identity_world_not_recentered(self):
  self.assertEqual(m.transformed_bounds({'min':[-576,17,-256],'max':[-572,18,-252]},{'position_m':[0,0,0],'yaw_deg':0}),[-576,-256,-572,-252])
 def test_bounds_godot_yaw(self):
  b=m.transformed_bounds({'min':[0,0,0],'max':[2,1,4]},{'position_m':[10,3,20],'yaw_deg':90})
  for actual,expected in zip(b,[10,18,14,20]):self.assertAlmostEqual(actual,expected)
 def test_route_corridor_preserves_touching_collider(self):
  self.assertTrue(m.corridor_intersects([0,4,1,5],[[0,0,0],[1,0,0]],4))
  self.assertFalse(m.corridor_intersects([0,4.01,1,5],[[0,0,0],[1,0,0]],4))
 def test_negative_control_route_height_not_support_plane(self):
  r=m.route_record('river',[[-700,490],[-698,490]],'negative_control',[])
  self.assertEqual(r['points'][0],[-700.,0.,490.])
 def test_subtract_only_explicit_opening(self):
  b={'min':[-10,0,-10],'max':[10,20,10]};h={'min':[-2,0,-10],'max':[2,5,10]}
  self.assertAlmostEqual(sum(math.prod(v['max'][i]-v['min'][i] for i in range(3)) for v in m.subtract_box(b,h)),7600)
 def test_approach_stops_before_recessed_shell(self):
  b={'yaw_rad':0,'local_bounds':{'min':[-16,0,-40],'max':[16,69.5,40]}}
  p={'position_m':[350,14,-330],'road_connection_m':[350,14,-270],'entrance_position_m':[350,14,-294]}
  self.assertEqual(m.approach_endpoint(b,p),[350.,-289.2])
if __name__=='__main__':unittest.main()
