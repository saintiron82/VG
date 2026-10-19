"""Evidence integrity guards; observed physical failures remain failures."""
import pathlib,json,hashlib,unittest,collections
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class ServicesReplay(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=read(H/'prepared_runtime.json');cls.r=read(H/'evidence/services_replay.json');cls.s=read(H/'evidence/summary.json');cls.lookup={r['id']:r for r in cls.p['routes']}
 def test_original_controller_and_loader(self):
  self.assertEqual((H/'Traversal.gd').read_bytes(),(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes());self.assertEqual((H/'RenderData.gd').read_bytes(),(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes())
 def test_source_and_implementation_hashes(self):
  for r in self.p['sources'].values():self.assertEqual(sha(pathlib.Path(r['path'])),r['sha256'])
  for p,h in self.p['implementation_hashes'].items():self.assertEqual(sha(ROOT/p),h)
 def test_three_lanes_four_bridges_both_directions(self):
  rows=[r for r in self.p['routes']if r['case_class']=='canal_crossing'];self.assertEqual(len(rows),24);self.assertEqual(len({r['bridge_id']for r in rows}),4)
  for r in rows:
   if not r['id'].endswith('_REVERSE'):self.assertEqual(self.lookup[r['id']+'_REVERSE']['points'],list(reversed(r['points'])))
 def test_common_and_network_both_directions(self):
  for cls in['common_entry','local_crossing_network']:
   rows=[r for r in self.p['routes']if r['case_class']==cls];self.assertEqual(len(rows),6)
   for r in rows:
    if not r['id'].endswith('_REVERSE'):self.assertEqual(self.lookup[r['id']+'_REVERSE']['points'],list(reversed(r['points'])))
 def test_46_cases_and_eight_failures_preserved(self):
  self.assertEqual(len(self.r['routes']),46);self.assertFalse(self.r['errors']);self.assertEqual(sum(bool(r['pass'])for r in self.r['routes']),38);self.assertEqual(self.s['status'],'FAILED_CASES_RETAINED');self.assertFalse(self.s['checks']['all_cases_pass_strict_original_acceptance']);self.assertTrue(all(v for k,v in self.s['checks'].items()if k!='all_cases_pass_strict_original_acceptance'))
 def test_no_ground_ray_miss_or_teleport(self):
  for r in self.r['routes']:
   for k in['ground_ray_miss_frames','within_route_teleports']:self.assertEqual(r[k],0)
 def test_ten_native_negative_controls(self):
  rows=[r for r in self.r['routes']if self.lookup[r['id']]['case_class'].endswith('_negative')];self.assertEqual(len(rows),10)
  for r in rows:self.assertTrue(r['pass']);self.assertEqual(r['status'],'blocked');self.assertIn(self.lookup[r['id']]['expected_contact_id'],r['obstacle_contact_ids'])
 def test_exact_inputs_and_finite_world(self):
  self.assertEqual(self.s['prepared']['sha256'],sha(H/'prepared_runtime.json'));self.assertEqual(self.s['result']['sha256'],sha(H/'evidence/services_replay.json'));self.assertFalse(self.s['exact_input_parity']['asset_errors']);self.assertFalse(self.s['exact_input_parity']['placement_errors']);self.assertFalse(self.r['collision_world']['infinite_ground_plane']);self.assertFalse(read(H/'evidence/preparation.json')['unsupported_hints'])
 def test_failed_common_descents_are_not_passes(self):
  rows=[r for r in self.r['routes']if self.lookup[r['id']]['case_class']=='common_entry'];self.assertEqual(sum(r['not_on_floor_frames']for r in rows),89);self.assertTrue(all(not r['pass']for r in rows));self.assertEqual(collections.Counter(r['status']for r in rows),{'reached':3,'blocked':3})
if __name__=='__main__':unittest.main(verbosity=2)
