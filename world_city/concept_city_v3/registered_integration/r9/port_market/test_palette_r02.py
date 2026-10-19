import copy,json,unittest
from .test_pack import PackTests
from .author import HERE,load,sha
from .repair_palette_r02 import canonical
class PaletteR02Tests(PackTests):
 @classmethod
 def setUpClass(cls):
  super().setUpClass();cls.original=cls.pack;cls.pack=load(HERE/'pack_r02.json');cls.assets=cls.pack['common_assets'];cls.instances=cls.pack['add_instances']
 def test_material_cache_identity(self):
  seen={}
  for p in self.instances:
   key=(p['asset_key'],p['palette_id']);value=canonical(p.get('palette_override',{}))
   self.assertTrue(key not in seen or seen[key]==value,key);seen[key]=value
 def test_no_geometry_pose_color_or_camera_changes(self):
  d=copy.deepcopy(self.pack);old={p['id']:p for p in self.original['add_instances']}
  for p in d['add_instances']:p['palette_id']=old[p['id']]['palette_id']
  self.assertEqual(d,self.original)
 def test_frozen_r01_and_report(self):
  self.assertEqual(sha(HERE/'pack.json'),load(HERE/'handoff.json')['pack_sha256']);r=load(HERE/'palette_identity_r02.json');self.assertEqual(r['corrected_pack']['sha256'],sha(HERE/'pack_r02.json'));self.assertEqual(r['material_cache_collisions'],0);self.assertEqual(len(r['changed_palette_ids']),4)
 def test_original_failure_negative_control(self):
  seen={};collisions=[]
  for p in self.original['add_instances']:
   key=(p['asset_key'],p['palette_id']);value=canonical(p.get('palette_override',{}))
   if key in seen and seen[key]!=value:collisions.append(key)
   seen[key]=value
  self.assertTrue(collisions);self.assertTrue(all(k==('r9_port_awning','port_weathered_canvas')for k in collisions))
if __name__=='__main__':
 unittest.main(defaultTest='PaletteR02Tests',verbosity=2)
