import copy,json,pathlib,unittest
import catalog
H=pathlib.Path(__file__).resolve().parent
class VectorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=json.loads((H/'route_vectors_r01.json').read_bytes())
 def test_pending_cannot_launch(self):
  with self.assertRaisesRegex(ValueError,'not released'):catalog.validate(self.d)
 def test_strict_source_coverage_481(self):
  d=copy.deepcopy(self.d);d['status']='READY_FOR_ACTUAL_SCENE_REPLAY';self.assertEqual(len(catalog.validate(d)),481)
 def test_original_ids_and_values(self):
  old=json.loads(catalog.source(self.d['sources']['original_412_catalog']).read_bytes());now={r['id']:r for r in self.d['routes']};retired=self.d['vector_accounting']['retired_expectations'][0]['id'];self.assertEqual(set(r['id']for r in old['routes'])-set(now),{retired});self.assertTrue(all(now[r['id']]==r for r in old['routes']if r['id']!=retired))
 def test_protected12_exact_mapping(self):
  a=self.d['vector_accounting'];self.assertEqual(len(set(a['protected_required_12_directions'])),12);self.assertEqual(len(a['protected_preserved_original_4_directions']),4);self.assertEqual(len(a['protected_new_8_directions']),8)
 def test_full_ordinary_source_dispositions(self):
  rows=self.d['coverage']['ordinary_entries'];self.assertEqual(sum(r['status']=='accepted'for r in rows),106);self.assertEqual([r['holding_id']for r in rows if r['status']=='retired'],['BLOCK_008:R8_C003']);self.assertFalse([r for r in rows if r['status']=='held'])
 def test_no_invented_door_destinations(self):self.assertEqual(sum(r['case_class']=='ordinary_entry'for r in self.d['routes']),106)
if __name__=='__main__':unittest.main()
