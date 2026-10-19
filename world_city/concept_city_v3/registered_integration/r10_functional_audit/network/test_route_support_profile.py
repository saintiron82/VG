import unittest
from route_support_profile import OwnerSurface,RouteSupportSampler,Hit,ProfileError,guard_support_ray,generate_waypoint_profile,guard_cart_input_profile

def plane(y):return [[[0,y,0],[2,y,0],[0,y,2]],[[2,y,0],[2,y,2],[0,y,2]]]
class ProfileTests(unittest.TestCase):
 def test_actual_top_contract(self):
  s=RouteSupportSampler([OwnerSurface('contract',plane(1.75),'a'),OwnerSurface('native',plane(1.5),'b')]);h,_=s.select(.5,.5,['contract','native'],1.75,.4,['contract']);self.assertEqual(h.y,1.75)
 def test_original_ray_start_rejected(self):
  with self.assertRaisesRegex(ProfileError,'RAY_START_NOT_ABOVE'):guard_support_ray(1.0375,Hit('contract',0,1.792517,1,'a'))
 def test_corrected_ray_start(self):
  self.assertGreater(guard_support_ray(1.75,Hit('contract',0,1.792517,1,'a'))['clearance_above_surface_m'],.7)
 def test_lower_native_layer_rejected(self):
  with self.assertRaisesRegex(ProfileError,'LOWER_NATIVE'):guard_support_ray(1.75,Hit('contract',0,1.792517,1,'a'),1.5,'native')
 def test_ambiguous_layer_rejected(self):
  s=RouteSupportSampler([OwnerSurface('a',plane(1),'a'),OwnerSurface('b',plane(1.1),'b')])
  with self.assertRaisesRegex(ProfileError,'AMBIGUOUS'):s.select(.5,.5,['a','b'],1,.2)
 def test_missing_owned_surface_rejected(self):
  s=RouteSupportSampler([OwnerSurface('a',plane(1),'a')])
  with self.assertRaisesRegex(ProfileError,'MISSING'):s.select(9,9,['a'],1)
 def test_coincident_faces_are_one_layer(self):
  s=RouteSupportSampler([OwnerSurface('a',plane(1),'a')]);h,_=s.select(1,1,['a'],1);self.assertEqual(h.y,1)
 def test_upper_layer_rejected(self):
  with self.assertRaisesRegex(ProfileError,'UPPER_LAYER'):guard_support_ray(1.75,Hit('contract',0,1.75,1,'a'),2.0,'other')
 def test_hints_retained_profile_generated(self):
  s=RouteSupportSampler([OwnerSurface('a',plane(1.75),'a')]);p=[[.2,1,.2],[1,1,.2]];o=[{'capsule_center':[.2,2.65,.2],'ground_y_m':1.75,'support_id':'a','frame':1},{'capsule_center':[1,2.65,.2],'ground_y_m':1.75,'support_id':'a','frame':2}]
  q,l=generate_waypoint_profile(p,o,s);self.assertEqual(q[0][1],1.75);self.assertEqual(l[0]['original_xyz_hint_m'][1],1)
 def test_any_guard_failure_is_failure(self):
  s=RouteSupportSampler([OwnerSurface('a',plane(1.75),'a')]);p=[[.01,1.75,.01],[.02,1.75,.01]];o=[{'capsule_center':[.01,2.65,.01],'ground_y_m':1.75,'support_id':'a','frame':1}]
  result=guard_cart_input_profile(p,o,s);self.assertEqual(result['status'],'FAIL');self.assertGreater(len(result['failures']),0)
if __name__=='__main__':unittest.main()
