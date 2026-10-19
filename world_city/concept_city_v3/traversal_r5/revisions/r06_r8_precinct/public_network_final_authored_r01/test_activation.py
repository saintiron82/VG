import copy,unittest
from final_activation import *
class ActivationTests(unittest.TestCase):
 def fixture(self):
  t=[[0,0,0],[0,0,1],[1,0,0]];return t,[dict(i=0,source_triangle_xyz_m=t,source_triangle_sha256=canonical(t),replacement_triangles_xyz_m=[])]
 def test_exact_retirement(self):
  t,r=self.fixture();self.assertEqual(apply_array_edits(t,r,'i'),[])
 def test_reject_unknown_index(self):
  t,r=self.fixture();r[0]['i']=1
  with self.assertRaises(AssertionError):apply_array_edits(t,r,'i')
 def test_reject_duplicate_row(self):
  t,r=self.fixture()
  with self.assertRaises(AssertionError):apply_array_edits(t,r+r,'i')
 def test_reject_changed_source(self):
  t,r=self.fixture();t=copy.deepcopy(t);t[0][0]=1
  with self.assertRaises(AssertionError):apply_array_edits(t,r,'i')
 def test_exact_current_public_lineage(self):
  d=read(pathlib.Path(__file__).resolve().parent.parent/'public_network_final_catalog_r01/route_vectors_r01.json');b=read(CITY/'registered_integration/r8/final_exterior_candidate_r01/whole_city_activation_r02/activation_binding.json');p=public_lineage(b,d);self.assertTrue(p['ordered_array_reconstruction_exact']);self.assertEqual(p['original_r07_changed_instances'],333)
if __name__=='__main__':unittest.main()
