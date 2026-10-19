"""Non-activation ledger continuation tests; no exact-scene output is written."""
from . import check_final_city_activation_r02 as c
from .test_final_city_activation import NativeActivationCheckerTests
import unittest
class CurrentLedgerBindingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=c.c.g.load(c.CANDIDATE);p,f,w,groups,d=c.c.expected_sources()
  cls.rows=[dict(id=hid,block_id=hid.split(':')[0],source_group=q['label'])for q in groups for hid in q['holding_ids']]
  cls.audit=dict(passed=True,holding_rows=cls.rows,summary=dict(all_explicit_old_native_retirements=295))
 def bind(self,audit=None):return c.bind_ledger(self.source,audit or self.audit,{'path':'synthetic_manifest.json','sha256':'test'},{'path':'synthetic_scene.json','sha256':'test'},{'not_a_building_count':True})
 def test_current_110_not_obsolete87(self):
  l=self.bind();self.assertEqual(l['summary']['adopted_whole_holdings'],110);self.assertEqual(sum(b['selected_holding_count']for b in l['blocks']),110)
 def test_source_unmodified_and_unknown_areas_preserved(self):
  l=self.bind();self.assertFalse(self.source['summary']['final_actual_scene_bound']);self.assertTrue(l['summary']['final_actual_scene_bound']);self.assertIsNone(l['summary']['final_exact_unassigned_land_m2']);self.assertTrue(all(b['exact_source_projected_area_m2']['final_exact_unassigned_land_m2']is None for b in l['blocks']))
 def test_runtime_material_gates_not_promoted(self):
  l=self.bind();self.assertEqual(l['remaining_gates'][2]['status'],'PRIOR61_REPLAY_REPORTED_PASS_FINAL110_REPLAY_PENDING');self.assertEqual(l['residual_material_application']['status'],'SEPARATE_FINAL_APPLICATION_REPORT_REQUIRED')
 def test_failed_native_stays_held(self):
  a=dict(self.audit,passed=False);l=self.bind(a);self.assertEqual(l['status'],'HELD_NATIVE_ACTIVATION_MISMATCH');self.assertIn('G1',l['blocks'][0]['remaining_activation_and_traversal_gate_ids'])
if __name__=='__main__':unittest.main()
