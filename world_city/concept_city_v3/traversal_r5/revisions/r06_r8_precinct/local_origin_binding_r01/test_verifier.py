import copy,unittest
from test_binding import BindingTests
from bind_origins import transform
from verify_replay import validate_origin_asset
class VerifierTests(unittest.TestCase):
 def fixture(self):
  d,a=BindingTests().fixture([[[64.,16.,-288.],[66.,16.,-288.],[64.,16.,-286.]],[[66.,16.,-288.],[66.,16.,-286.],[64.,16.,-286.]]]);local,t,p=transform(d,'S',a);poses=[dict(d['placements']['S'],position_m=t)];return d,a,local,poses,p
 def test_exact_stage(self):
  d,a,l,poses,p=self.fixture();self.assertEqual(validate_origin_asset(d,'S',a,l,poses,p),[64,16,-288])
 def test_reject_wrong_origin(self):
  d,a,l,poses,p=self.fixture();poses[0]['position_m'][0]+=16
  with self.assertRaises(AssertionError):validate_origin_asset(d,'S',a,l,poses,p)
 def test_reject_reordered_faces(self):
  d,a,l,poses,p=self.fixture();l['triangles'].reverse()
  with self.assertRaises(AssertionError):validate_origin_asset(d,'S',a,l,poses,p)
 def test_reject_relabelled_source(self):
  d,a,l,poses,p=self.fixture();l['source_face_indices'][0]=['road',88]
  with self.assertRaises(AssertionError):validate_origin_asset(d,'S',a,l,poses,p)
 def test_reject_changed_other_transform(self):
  d,a,l,poses,p=self.fixture();poses[0]['yaw_rad']=.1
  with self.assertRaises(AssertionError):validate_origin_asset(d,'S',a,l,poses,p)
 def test_reject_misreported_proof(self):
  d,a,l,poses,p=self.fixture();p['removed_faces']=1
  with self.assertRaises(AssertionError):validate_origin_asset(d,'S',a,l,poses,p)
if __name__=='__main__':unittest.main()
