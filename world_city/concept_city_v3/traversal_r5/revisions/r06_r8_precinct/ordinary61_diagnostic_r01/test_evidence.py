import collections,hashlib,json,pathlib,sys,unittest
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(H));import catalog
read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class DiagnosticEvidence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=read(H/'prepared_runtime.json');cls.d=read(H/'route_catalog_bound_r02.json');cls.r=read(H/'evidence/public_network_replay.json');cls.s=read(H/'evidence/summary.json');cls.pre=read(H/'evidence/preparation.json')
 def test_exact_244_source_bound_cases(self):
  self.assertEqual(len(catalog.validate(self.d)),244);self.assertEqual(len(self.p['routes']),244);self.assertEqual(collections.Counter(r['case_class']for r in self.p['routes']),{'ordinary_entry':122,'ordinary_court_to_door':122})
 def test_all_61_holdings_in_both_classes_and_directions(self):
  for cls in ['ordinary_entry','ordinary_court_to_door']:
   rows=[r for r in self.p['routes']if r['case_class']==cls];self.assertEqual(len({r['holding_id']for r in rows}),61)
   for r in rows:
    if not r['id'].endswith('_REVERSE'):self.assertEqual(next(x for x in rows if x['id']==r['id']+'_REVERSE')['points'],list(reversed(r['points'])))
 def test_original_controller_loader_unchanged(self):
  for name,path in [('Traversal.gd','world_city/concept_city_v3/traversal_r5/Traversal.gd'),('RenderData.gd','voxel_character/common/preview/RenderData.gd')]:self.assertEqual((H/name).read_bytes(),(ROOT/path).read_bytes())
 def test_exact_source_hashes(self):
  for r in self.p['sources'].values():self.assertEqual(sha(pathlib.Path(r['path'])),r['sha256'])
  for path,digest in self.p['implementation_hashes'].items():self.assertEqual(sha(ROOT/path),digest)
 def test_all_original_results_retained(self):
  self.assertEqual({r['id']for r in self.r['routes']},{r['id']for r in self.p['routes']});self.assertEqual({r['case']for r in self.s['failures']},{r['id']for r in self.r['routes']if not r['pass']})
  expected='PASS_DECLARED_ORDINARY61_DIAGNOSTIC'if all(self.s['checks'].values())else'FAILED_CASES_RETAINED';self.assertEqual(self.s['status'],expected)
 def test_geometry_is_exact_scene_native_and_declared_contract(self):
  self.assertFalse(self.s['exact_input_parity']['asset_errors']);self.assertFalse(self.s['exact_input_parity']['placement_errors']);self.assertFalse(self.r['collision_world']['infinite_ground_plane']);self.assertFalse(self.pre['unsupported_positive_hints'])
 def test_activation_ownership_and_retirement(self):
  self.assertEqual(len(self.pre['activation_checks']),4)
  for r in self.pre['activation_checks']:self.assertFalse(r['missing_ids']);self.assertFalse(r['mismatched_ids']);self.assertFalse(r['retained_superseded_ids'])
  self.assertEqual(self.pre['finite_public_field_activation']['missing_triangle_instances'],0)
  self.assertEqual(len(self.pre['appended_surface_activation']['patches']),3)
  for row in self.pre['appended_surface_activation']['materials'].values():self.assertEqual(row['missing_triangle_instances'],0);self.assertEqual(row['retired_triangle_instances_still_present'],0)
 def test_non_diagnostic_network_is_held(self):
  for name in ['public_roads','primary_network_goals']:self.assertTrue(all(r['status']=='held'for r in self.d['coverage'][name]))
  self.assertEqual(sum(r['status']=='accepted'for r in self.d['coverage']['ordinary_entries']),61)
 def test_prior_412_catalog_unchanged(self):self.assertEqual(sha(H.parent/'public_network_r18_r01/route_catalog_61_ready_r05.json'),'443c8d56a73dad16ce73a36414f5de846b7c19011da7c7c6bca7725628aad1f6')
 def test_no_errors_or_within_case_teleports(self):
  self.assertFalse(self.r['errors']);self.assertTrue(all(r['within_route_teleports']==0 for r in self.r['routes']))
if __name__=='__main__':unittest.main(verbosity=2)
