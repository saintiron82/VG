import copy,json,unittest
from external_addenda import ROOT,validate
BASE=ROOT/'world_city/concept_city_v3/assemblies/ordinary/registered/district_fabric_r01/primary_bent_goals_r01/castle'
class TestAddendum(unittest.TestCase):
 def setUp(self):self.a=json.loads((BASE/'sill_collision_addendum.json').read_bytes());self.p=json.loads((BASE/'surface_patch.json').read_bytes())
 def test_exact(self):self.assertEqual(len(validate(self.a,self.p)['add_triangles_world_xyz_m']),2)
 def test_wrong_base(self):
  self.a['base_scene']['sha256']='0'*64
  with self.assertRaises(AssertionError):validate(self.a,self.p)
 def test_moved_collision(self):
  self.a['collision_triangles_xyz_m'][0][0][0]+=.01
  with self.assertRaises(AssertionError):validate(self.a,self.p)
 def test_wrong_winding(self):
  self.a['collision_triangles_xyz_m']=copy.deepcopy(self.a['visual_triangles_xyz_m'])
  with self.assertRaises(AssertionError):validate(self.a,self.p)
 def test_extra_triangle(self):
  self.a['visual_triangles_xyz_m'].append(self.a['visual_triangles_xyz_m'][0])
  with self.assertRaises(AssertionError):validate(self.a,self.p)
 def test_source_retirement(self):
  self.p['surface_edits']=[dict(material='road',indices=[1])]
  with self.assertRaises(AssertionError):validate(self.a,self.p)
 def test_native_retirement(self):
  self.a['native_colliders_disabled']=['castle_registered:front_curtain']
  with self.assertRaises(AssertionError):validate(self.a,self.p)
if __name__=='__main__':unittest.main()
