"""Regression guards for the immutable 104-case actual B15 result."""
import pathlib,json,hashlib,unittest
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class DistrictReplay(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=read(H/'prepared_runtime.json');cls.r=read(H/'evidence/district_replay.json');cls.s=read(H/'evidence/summary.json');cls.lookup={r['id']:r for r in cls.p['routes']}
 def test_original_controller_and_loader(self):
  self.assertEqual((H/'Traversal.gd').read_bytes(),(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes());self.assertEqual((H/'RenderData.gd').read_bytes(),(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes())
 def test_source_and_implementation_hashes(self):
  for r in self.p['sources'].values():self.assertEqual(sha(pathlib.Path(r['path'])),r['sha256'])
  for p,h in self.p['implementation_hashes'].items():self.assertEqual(sha(ROOT/p),h)
 def test_all_22_public_entries_both_directions(self):
  fixed=read(pathlib.Path(self.p['sources']['fixed_public_seams']['path']));expected={r['id']for r in fixed['roots']};routes=[r for r in self.p['routes']if r['case_class']=='public_entry'];self.assertEqual(len(routes),44);self.assertEqual({r['entry_id']for r in routes},expected)
  for r in routes:
   if not r['id'].endswith('_REVERSE'):self.assertEqual(self.lookup[r['id']+'_REVERSE']['points'],list(reversed(r['points'])))
 def test_all_26_holdings_both_directions(self):
  hand=read(pathlib.Path(self.p['sources']['route_handoff']['path']));expected={r['holding_id']for r in hand['door_routes']};routes=[r for r in self.p['routes']if r['case_class']=='court_to_door'];self.assertEqual(len(routes),52);self.assertEqual(len(expected),26);self.assertEqual({r['holding_id']for r in routes},expected)
  for r in routes:
   if not r['id'].endswith('_REVERSE'):self.assertEqual(self.lookup[r['id']+'_REVERSE']['points'],list(reversed(r['points'])))
 def test_all_104_strict_passes(self):
  self.assertEqual(len(self.r['routes']),104);self.assertEqual(self.r['status'],'pass');self.assertFalse(self.r['errors']);self.assertTrue(all(r['pass']for r in self.r['routes']));self.assertTrue(all(self.s['checks'].values()))
 def test_no_airborne_ground_miss_or_teleport(self):
  for r in self.r['routes']:
   for key in['ground_ray_miss_frames','not_on_floor_frames','within_route_teleports']:self.assertEqual(r[key],0)
 def test_eight_real_native_blocks(self):
  rows=[r for r in self.r['routes']if self.lookup[r['id']]['case_class']=='blocked_native_negative'];self.assertEqual(len(rows),8)
  for r in rows:self.assertEqual(r['status'],'blocked');self.assertIn(self.lookup[r['id']]['expected_contact_id'],r['obstacle_contact_ids'])
 def test_exact_collision_input_parity(self):
  self.assertEqual(self.s['status'],'PASS_BOUNDED_ACTUAL_DISTRICT_BATCH');self.assertEqual(self.s['prepared']['sha256'],sha(H/'prepared_runtime.json'));self.assertEqual(self.s['result']['sha256'],sha(H/'evidence/district_replay.json'));self.assertFalse(self.s['exact_input_parity']['asset_errors']);self.assertFalse(self.s['exact_input_parity']['placement_errors']);self.assertFalse(self.r['collision_world']['infinite_ground_plane'])
 def test_preparation_only_failure_retained(self):
  d=read(H/'rejected_initial_preparation/prepared_runtime.json');key=str((H/'prepare.py').relative_to(ROOT));self.assertEqual(sha(H/'rejected_initial_preparation/prepare_initial.py'),d['implementation_hashes'][key]);self.assertIn('TypeError',(H/'rejected_initial_preparation/prepare.log').read_text());self.assertFalse(list((H/'rejected_initial_preparation').glob('*replay*')))
if __name__=='__main__':unittest.main(verbosity=2)
