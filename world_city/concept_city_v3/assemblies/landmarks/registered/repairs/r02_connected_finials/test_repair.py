"""Read-only integrity and connectivity-evidence tests for the isolated repair."""
import json
import unittest
from repair import HERE,REGISTERED,ROOT,ref
from voxel_character.common import core

class RepairTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=json.loads((HERE/'resolved_placements.json').read_text());cls.o=json.loads((HERE/'asset_replacement_overlay.json').read_text());cls.r=json.loads((HERE/'evidence/compile_connectivity_report.json').read_text());cls.old=json.loads((ROOT/cls.o['base_pack']['path']).read_text())
 def test_original_pack_and_sources_preserved(self):
  self.assertEqual(ref(ROOT/self.o['base_pack']['path']),self.o['base_pack'])
  for r in self.r['requests']:self.assertEqual(ref(ROOT/r['old_source']['path']),r['old_source'])
 def test_three_asset_replacements_only(self):
  changes={r['placement_id'] for r in self.o['replacements']};self.assertEqual(len(changes),3);self.assertEqual(len(self.p['placements']),80)
  for a,b in zip(self.old['placements'],self.p['placements']):
   if a['id'] not in changes:self.assertEqual(a,b)
   else:
    for k in ('id','position_m','yaw_rad','scale','outer_footprint_xz_m','world_y_range_m','actual_cached_bounds_local_m'):self.assertEqual(a[k],b[k])
  for key in ('owned_floors','entrances','replacement_overlay'):self.assertEqual(self.old[key],self.p[key])
 def test_all_sources_and_caches_match(self):
  for a in self.p['assets']:
   self.assertEqual(ref(ROOT/a['source']['path']),a['source']);self.assertEqual(ref(ROOT/a['cache']['path']),a['cache']);self.assertEqual(core.digest(json.loads((ROOT/a['source']['path']).read_text())),a['master_hash']);self.assertEqual(json.loads((ROOT/a['cache']['path']).read_text())['master_hash'],a['master_hash'])
 def test_compiled_connectivity(self):
  self.assertEqual(self.r['status'],'pass')
  for r in self.r['requests']:
   self.assertGreater(r['before']['connectivity']['roof_cells_disconnected_from_body'],0)
   c=r['after']['connectivity'];self.assertEqual(c['roof_cells_disconnected_from_body'],0);self.assertTrue(c['top_layer_body_connected']);self.assertFalse(c['empty_roof_layers']);self.assertLessEqual(r['after']['candidate_cells'],400000)
 def test_no_false_visual_or_runtime_claim(self):
  self.assertFalse(self.o['actual_scene_integration']);self.assertFalse(self.o['actual_visual_review']);self.assertFalse(self.p['completion_claims']['actual_visual_review'])

if __name__=='__main__':unittest.main(verbosity=2)
