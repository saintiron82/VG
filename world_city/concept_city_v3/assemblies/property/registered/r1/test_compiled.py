import json,unittest
from pathlib import Path
from . import author as q
from .. import author as a
class CompiledTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.pack=json.loads((q.HERE/'resolved_placements.json').read_text())
 def test_counts_and_verified_cache(self):
  p=self.pack;self.assertEqual(len(p['placements']),86);self.assertEqual(len(p['asset_manifest']),16);self.assertEqual(len(p['actual_doors']),39);self.assertEqual(len(p['internal_routes']),53)
  for m in p['asset_manifest'].values():self.assertEqual(a.file_sha(m['compiled_asset_ref']),m['render_sha256']);self.assertEqual(a.file_sha(m['master_path']),m['master_file_sha256'])
 def test_source_bound_not_activated(self):
  self.assertFalse(self.pack['runtime_ready']);self.assertFalse(self.pack['applied_to_scene']);self.assertEqual(self.pack['registered_source_sha256'],a.file_sha(a.CITY/'registered_source/plan.json'));self.assertEqual(self.pack['source_overlay_sha256'],a.file_sha(q.OUT/'access_overlay.json'))
 def test_exact_replace_and_pose_ledgers(self):
  rows=self.pack['replacement_ledger'];self.assertEqual(sum(len(r['source_building_ids']) for r in rows),27);self.assertEqual(sum(len(r['source_owned_path_ids']) for r in rows),34);self.assertEqual(sum(len(r['property_pose_updates']) for r in rows),7);self.assertTrue(all(len(r['supersede_r0_route_ids'])>0 for r in rows))
 def test_actual_gate_and_owned_footprint(self):
  for m in self.pack['ownership_masks']:
   self.assertEqual(m['verified_sampled_gate_clear_band_m'],4);self.assertFalse(m['compiled_gate_intrusions']);self.assertTrue(m['terrain_exclusion_union_required']);self.assertEqual(len(m['external_access_domains_xz_m']),3);self.assertTrue(m['compiled_upward_faces'])
 def test_r0_seal_unchanged(self):
  seal=json.loads((a.HERE/'r0_seal.json').read_text())
  for path,digest in seal['files_sha256'].items():self.assertEqual(a.file_sha(a.HERE/path),digest,path)
 def test_bounded_sequential_results(self):
  r=json.loads((q.HERE/'cache_build_report.json').read_text());self.assertEqual(r['status'],'complete');self.assertEqual(len(r['results']),7);self.assertTrue(r['sequential'])
  for s in r['results']:self.assertLessEqual(s['candidate_cells'],300000);self.assertLessEqual(s['occupied_cells'],100000)
if __name__=='__main__':unittest.main()
