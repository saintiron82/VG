import copy,unittest
from . import runtime_contracts as r
from ..r6 import merge_patches as m
S={'surfaces':{'water':[]},'common_instances':[dict(id='well',asset_key='a',position_m=[0,0,0],yaw_rad=0)],'common_assets':{'a':{'bounds':{'min':[-2,-3,-2],'max':[2,5,2]},'render_sha256':'asset'}}}
def ext():return dict(base_water_sha256=m.canonical_sha([]),owner_ids=['well'],collision=False,append_vertices_xyz_m=[[0,-2,0],[.5,-2,0],[0,-2,.5]])
class Test(unittest.TestCase):
 def test_append_preserves_input(self):
  before=copy.deepcopy(S);out=r.append_water_extensions(S,S,[ext()]);self.assertEqual(S,before);self.assertEqual(len(out['surfaces']['water']),3)
 def test_absent_owner(self):
  e=ext();e['owner_ids']=['missing']
  with self.assertRaisesRegex(ValueError,'Unplaced'):r.append_water_extensions(S,S,[e])
 def test_outside_bound(self):
  e=ext();e['append_vertices_xyz_m'][0][0]=100
  with self.assertRaisesRegex(ValueError,'outside'):r.append_water_extensions(S,S,[e])
 def test_original_water_change(self):
  s=copy.deepcopy(S);s['surfaces']['water']=[[0,0,0]]
  with self.assertRaisesRegex(ValueError,'mutation'):r.append_water_extensions(s,S,[ext()])
 def test_duplicates(self):
  with self.assertRaisesRegex(ValueError,'Duplicate'):r.append_water_extensions(S,S,[ext(),ext()])
if __name__=='__main__':unittest.main()
