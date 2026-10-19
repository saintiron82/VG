import copy,json,unittest
from .author_canopies import HERE,ROOT,BASE,BASE_SHA,MARKET,WALK,sha,load,canonical,lowcells,lowcolors
from voxel_character.common.coordinate_planes import compile_master
from voxel_character.common.render_data import make_render_data
class CanopyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pack=load(HERE/'pack.json');cls.proof=load(HERE/'proof.json');cls.source={p['id']:p for p in load(MARKET)['placements']};cls.comp={}
  for a in cls.proof['assets']:
   old=compile_master(load(ROOT/a['source_master']['path']),{'pitch':.25},max_candidate_cells=150000,max_output_cells=50000)
   new=compile_master(load(ROOT/a['new_master']['path']),{'pitch':.25},max_candidate_cells=150000,max_output_cells=50000)
   cls.comp[a['new_asset_key']]=(old,new)
 def test_cache_and_source_hashes(self):
  for a in self.proof['assets']:
   for key in ['source_master','source_render','new_master','new_render']:self.assertEqual(sha(ROOT/a[key]['path']),a[key]['sha256'])
   old,new=self.comp[a['new_asset_key']];self.assertEqual(make_render_data(old),load(ROOT/a['source_render']['path']));self.assertEqual(make_render_data(new),load(ROOT/a['new_render']['path']))
 def test_exact_native_low_volume_and_materials(self):
  for key,(old,new)in self.comp.items():
   self.assertEqual(lowcells(old),lowcells(new));self.assertNotEqual(old['cells'],new['cells'])
   for p in self.pack['replace_instances']:
    if p['asset_key']!=key:continue
    self.assertEqual(lowcolors(old,self.source[p['id']]['palette_override']),lowcolors(new,p['palette_override']))
 def test_unchanged_footprint_and_floor(self):
  for a in self.proof['assets']:
   for bound in ['min','max']:
    self.assertEqual(a['old_bounds'][bound][0],a['new_bounds'][bound][0]);self.assertEqual(a['old_bounds'][bound][2],a['new_bounds'][bound][2])
   self.assertEqual(a['old_bounds']['min'][1],a['new_bounds']['min'][1]);self.assertLessEqual(a['new_bounds']['max'][1],4.5)
 def test_transactional_replacement_pose_guards(self):
  ids=[p['id']for p in self.pack['replace_instances']];self.assertEqual(len(ids),104);self.assertEqual(len(set(ids)),104);self.assertEqual(self.pack['add_instances'],[]);self.assertEqual(self.pack['remove_instance_ids'],[])
  for p in self.pack['replace_instances']:
   old=self.source[p['id']];self.assertEqual(p['expected_asset_key'],'market_r3_'+old['asset_key']);self.assertEqual(p['expected_position_m'],old['position_m']);self.assertEqual(p['expected_yaw_rad'],old['yaw_rad']);self.assertEqual(p['proof_sha256'],sha(ROOT/p['proof_path']))
 def test_customer_routes_untouched(self):
  self.assertEqual(sha(WALK),self.proof['original_customer_paths']['sha256']);self.assertEqual(len(load(WALK)['stall_routes']),104)
 def test_parity_negative_control(self):
  old,new=next(iter(self.comp.values()));broken=copy.deepcopy(new);broken['cells']=[r for r in broken['cells']if r!=lowcells(broken)[0]];self.assertNotEqual(lowcells(old),lowcells(broken))
 def test_original_cargo_pack_still_frozen(self):
  cargo=HERE.parent;handoff=load(cargo/'handoff.json');self.assertEqual(sha(cargo/'pack.json'),handoff['pack_sha256']);self.assertEqual(self.pack['base_scene_sha256'],BASE_SHA)
if __name__=='__main__':unittest.main(verbosity=2)
