import copy,unittest
from case_inputs import fingerprint,compare
class IdentityTests(unittest.TestCase):
 def fixture(self):
  d=dict(placements={'P':dict(id='P',asset_key='A',position_m=[0,0,0])},assets={'A':dict(render_path='old/path',render_sha256='abc',collision_format='actual_scene_triangles')},buildings={},sources={'scene':{'sha256':'scene'}});r=dict(id='R',points=[[0,1,0],[1,1,0]],placement_ids=['P'],building_ids=[],minimum_allowed_feet_y_m=0);return d,r,{'controller':'immutable'},{'A':'abc'}
 def digest(self,v):return fingerprint(*v)['sha256']
 def test_exact_and_relocated_bytes(self):
  f=self.fixture();g=copy.deepcopy(f);g[0]['assets']['A']['render_path']='new/path';self.assertEqual(self.digest(f),self.digest(g))
 def test_changed_pose(self):
  f=self.fixture();g=copy.deepcopy(f);g[0]['placements']['P']['position_m'][0]=1;self.assertNotEqual(self.digest(f),self.digest(g))
 def test_changed_asset_bytes(self):
  f=self.fixture();g=copy.deepcopy(f);g[0]['assets']['A']['render_sha256']='def';g[3]['A']='def';self.assertNotEqual(self.digest(f),self.digest(g))
 def test_changed_route_or_acceptance(self):
  for field,value in [('points',[[0,1,0],[2,1,0]]),('minimum_allowed_feet_y_m',-1)]:
   f=self.fixture();g=copy.deepcopy(f);g[1][field]=value;self.assertNotEqual(self.digest(f),self.digest(g))
 def test_changed_runner(self):
  f=self.fixture();g=copy.deepcopy(f);g[2]['controller']='changed';self.assertNotEqual(self.digest(f),self.digest(g))
 def test_changed_scene(self):
  f=self.fixture();g=copy.deepcopy(f);g[0]['sources']['scene']['sha256']='new';self.assertNotEqual(self.digest(f),self.digest(g))
 def test_add_remove_and_change(self):
  a={'cases':{'A':{'sha256':'1'},'B':{'sha256':'2'},'C':{'sha256':'3'}}};b={'cases':{'A':{'sha256':'1'},'B':{'sha256':'4'},'D':{'sha256':'5'}}};r=compare(a,b);self.assertEqual(r['identical_case_ids'],['A']);self.assertEqual(r['required_replay_case_ids'],['B','D']);self.assertEqual(r['removed_case_ids'],['C'])
if __name__=='__main__':unittest.main()
