import unittest,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];CITY=ROOT/'world_city/concept_city_v3'
class CandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.d=json.loads((Path(__file__).parent/'ordinary_woodland_candidate.json').read_text())
 def test_source_binding(self):self.assertEqual(self.d['source_plan_sha256'],hashlib.sha256((CITY/'registered_source/plan.json').read_bytes()).hexdigest())
 def test_native_scale(self):self.assertTrue(all(p['scale']==[1,1,1] for p in self.d['common_instances']))
 def test_unique_instances(self):self.assertEqual(len({p['id'] for p in self.d['common_instances']}),len(self.d['common_instances']))
 def test_all_assets_bound(self):self.assertTrue(all(p['asset_key'] in self.d['common_assets'] for p in self.d['common_instances']))
 def test_common_render_hashes(self):
  for a in self.d['common_assets'].values():self.assertEqual(hashlib.sha256((ROOT/a['render_path']).read_bytes()).hexdigest(),a['render_sha256'])
 def test_declared_counts(self):
  self.assertEqual(sum(p['source_pack']=='ordinary' for p in self.d['common_instances']),673)
  self.assertEqual(sum(p['source_pack']=='woodland' for p in self.d['common_instances']),1391)
 def test_only_original_proxy_replacements(self):
  ids={p['id'] for p in self.d['common_instances'] if p['source_pack']=='ordinary'}
  self.assertEqual(set(self.d['remove_proxy_ids']),ids|{x+':support' for x in ids})
 def test_no_estate_route_promotion(self):
  self.assertFalse(self.d['replace_plot_ids']);self.assertFalse(self.d['access_overlay'])
if __name__=='__main__':unittest.main()
