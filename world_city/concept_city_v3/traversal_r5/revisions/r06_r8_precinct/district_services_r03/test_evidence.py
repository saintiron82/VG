"""Regression guards for the repaired actual services batch."""
import pathlib,json,hashlib,unittest,collections
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bound_implementation_sha(p):
 record=read(H/'source_mutation_since_run.json')
 if str(p.relative_to(ROOT))==record['original_path']:
  snapshot=ROOT/record['archived_source']['path'];assert sha(snapshot)==record['preflight_and_audit_sha256'];return sha(snapshot)
 return sha(p)
class ServicesReplay(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=read(H/'prepared_runtime.json');cls.r=read(H/'evidence/services_replay.json');cls.s=read(H/'evidence/summary.json');cls.lookup={r['id']:r for r in cls.p['routes']}
 def test_original_controller_and_loader(self):
  self.assertEqual((H/'Traversal.gd').read_bytes(),(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes());self.assertEqual((H/'RenderData.gd').read_bytes(),(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes())
 def test_source_and_implementation_hashes(self):
  for r in self.p['sources'].values():self.assertEqual(sha(pathlib.Path(r['path'])),r['sha256'])
  for p,h in self.p['implementation_hashes'].items():self.assertEqual(bound_implementation_sha(ROOT/p),h)
 def test_three_lanes_four_bridges_both_directions(self):
  rows=[r for r in self.p['routes']if r['case_class']=='canal_crossing'];self.assertEqual(len(rows),24);self.assertEqual(len({r['bridge_id']for r in rows}),4)
  for r in rows:
   if not r['id'].endswith('_REVERSE'):self.assertEqual(self.lookup[r['id']+'_REVERSE']['points'],list(reversed(r['points'])))
 def test_common_and_network_both_directions(self):
  for cls in['common_entry','local_crossing_network']:
   rows=[r for r in self.p['routes']if r['case_class']==cls];self.assertEqual(len(rows),6)
   for r in rows:
    if not r['id'].endswith('_REVERSE'):self.assertEqual(self.lookup[r['id']+'_REVERSE']['points'],list(reversed(r['points'])))
 def test_45_passes_and_one_failure_retained(self):
  self.assertEqual(len(self.r['routes']),46);self.assertFalse(self.r['errors']);self.assertEqual(sum(bool(r['pass'])for r in self.r['routes']),45);self.assertEqual(self.s['status'],'FAILED_CASES_RETAINED');self.assertFalse(self.s['checks']['all_cases_pass_strict_original_acceptance']);self.assertTrue(all(v for k,v in self.s['checks'].items()if k!='all_cases_pass_strict_original_acceptance'))
 def test_no_ground_ray_miss_or_teleport(self):
  for r in self.r['routes']:
   for k in['ground_ray_miss_frames','not_on_floor_frames','within_route_teleports']:self.assertEqual(r[k],0)
 def test_ten_native_negative_controls(self):
  rows=[r for r in self.r['routes']if self.lookup[r['id']]['case_class'].endswith('_negative')];self.assertEqual(len(rows),10)
  for r in rows:self.assertTrue(r['pass']);self.assertEqual(r['status'],'blocked');self.assertIn(self.lookup[r['id']]['expected_contact_id'],r['obstacle_contact_ids'])
 def test_exact_inputs_and_finite_world(self):
  self.assertEqual(self.s['prepared']['sha256'],sha(H/'prepared_runtime.json'));self.assertEqual(self.s['result']['sha256'],sha(H/'evidence/services_replay.json'));self.assertFalse(self.s['exact_input_parity']['asset_errors']);self.assertFalse(self.s['exact_input_parity']['placement_errors']);self.assertFalse(self.r['collision_world']['infinite_ground_plane']);self.assertFalse(read(H/'evidence/preparation.json')['unsupported_hints'])
 def test_common_five_pass_one_outer_seam_block(self):
  rows=[r for r in self.r['routes']if self.lookup[r['id']]['case_class']=='common_entry'];self.assertEqual(len(rows),6);self.assertEqual(sum(r['pass']for r in rows),5);self.assertEqual([r['id']for r in rows if not r['pass']],['COMMON_FINE_ENTRY_LANE_2_REVERSE'])
 def test_updated_normalized_side_audit(self):
  d=read(H/'evidence/normalized_side_audit.json');self.assertEqual(d['actual_new_scene']['status'],'PASS');self.assertFalse(d['actual_new_scene']['contacts']);self.assertTrue(d['known_old_blocker_detected']);self.assertEqual(bound_implementation_sha(ROOT/d['shared_checker']['path']),d['shared_checker']['sha256']);self.assertEqual(d['scene']['sha256'],self.p['sources']['scene']['sha256'])
 def test_exact_common_retirement_and_collision_contract(self):
  scene=read(pathlib.Path(self.p['sources']['scene']['path']));ids={p['id']for p in scene['common_instances']};self.assertNotIn('REGISTERED_LANDSCAPE:SITE_COMMON',ids);self.assertTrue({'R06_COMMON_R02:retained_base','R06_COMMON_R02:fine_access'}<=ids);disabled={pid for c in scene['collision_contracts']for pid in c.get('disable_native_mesh_collider_ids',[])};self.assertIn('R06_COMMON_R02:fine_access',disabled)
 def test_previous_failures_remain_sealed(self):
  folder=H.parent/'district_services_r02';seal=read(folder/'freeze_manifest.json')
  for p,h in seal['owned_files'].items():self.assertEqual(sha(folder/p),h)
  self.assertEqual(read(folder/'evidence/summary.json')['status'],'FAILED_CASES_RETAINED')
if __name__=='__main__':unittest.main(verbosity=2)
