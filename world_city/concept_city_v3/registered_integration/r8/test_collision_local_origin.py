import unittest
from .collision_local_origin import rebase
class Test(unittest.TestCase):
 def test_exact_world_and_order(self):
  t=[[[61.0,15.5,-282.0],[65.0,15.75,-282.0],[61.0,15.5,-278.0]]];o,p,r=rebase(t,[[60,15,-276],[70,16,-294]])
  self.assertEqual(p,[64.,16.,-288.]);self.assertEqual([[[v[i]+p[i]for i in range(3)]for v in f]for f in o],t);self.assertEqual(r['removed_faces'],0);self.assertIsNone(r['fallback_reason'])
 def test_no_rounding_authorized(self):
  t=[[[1e-20,15.0,-282.0],[65.0,15.75,-282.0],[61.0,15.5,-278.0]]];o,p,r=rebase(t,[[60,15,-276],[70,16,-294]])
  self.assertEqual(p,[0.,0.,0.]);self.assertEqual(o,t);self.assertIsNotNone(r['fallback_reason'])
 def test_invalid(self):
  with self.assertRaises(ValueError):rebase([],[[0,0,0]])
  with self.assertRaises(ValueError):rebase([[[0,0,0],[1,0,0],[0,0,1]]],[[float('nan'),0,0]])
if __name__=='__main__':unittest.main()
