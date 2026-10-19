import copy,pathlib,sys,unittest
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H));import private_emission_revision as r
A=[[0,0,0],[2,0,0],[0,0,2]];B=[[10,0,0],[11,0,0],[10,0,1]];C=[[0,0,0],[1,0,0],[0,0,1]];SIDE=[[0,0,0],[0,1,0],[1,1,0]]
def fixture():
 old=dict(base_scene_sha256='a'*64,appended_surfaces={'earth':A+B});new=dict(base_scene_sha256='a'*64,appended_surfaces={'earth':B+C,'bank':SIDE});review=dict(walking_geometry_changed=False,native_geometry_changed=False,source_rows=[dict(material='earth',appended_triangle_index=0,source_triangle_sha256=r.sha(A),removed_area_m2=1.5)])
 return old,new,review,{'bank':[SIDE]}
class Tests(unittest.TestCase):
 def test_exact_revision(self):self.assertEqual(r.validate(*fixture())['summary']['earth']['unchanged_triangle_instances'],1)
 def test_changed_unaffected_triangle_rejected(self):
  a,b,c,d=fixture();b['appended_surfaces']['earth'][0]=[10,1,0]
  with self.assertRaises(AssertionError):r.validate(a,b,c,d)
 def test_wrong_old_hash_rejected(self):
  a,b,c,d=fixture();c['source_rows'][0]['source_triangle_sha256']='x'
  with self.assertRaises(AssertionError):r.validate(a,b,c,d)
 def test_unapproved_side_rejected(self):
  a,b,c,d=fixture()
  with self.assertRaises(AssertionError):r.validate(a,b,c,{})
 def test_retired_original_still_present_rejected(self):
  a,b,c,d=fixture();b['appended_surfaces']['earth']+=A
  with self.assertRaises(AssertionError):r.validate(a,b,c,d)
 def test_outside_new_top_rejected(self):
  a,b,c,d=fixture();b['appended_surfaces']['earth'][3:]=[[3,0,0],[4,0,0],[3,0,1]]
  with self.assertRaises(AssertionError):r.validate(a,b,c,d)
 def test_wrong_area_rejected(self):
  a,b,c,d=fixture();c['source_rows'][0]['removed_area_m2']=1.4
  with self.assertRaises(AssertionError):r.validate(a,b,c,d)
 def test_changed_height_rejected(self):
  a,b,c,d=fixture();b['appended_surfaces']['earth'][3]=[0,.1,0]
  with self.assertRaises(AssertionError):r.validate(a,b,c,d)
if __name__=='__main__':unittest.main(verbosity=2)
