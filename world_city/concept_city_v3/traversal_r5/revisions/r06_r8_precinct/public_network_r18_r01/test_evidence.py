"""Integrity checks for actual joint-scene evidence, including retained failures."""
import collections,hashlib,json,pathlib,sys,unittest
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
sys.path.insert(0,str(H))
import catalog
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class PublicNetworkEvidence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=read(H/'prepared_runtime.json');cls.r=read(H/'evidence/public_network_replay.json');cls.s=read(H/'evidence/summary.json');cls.pre=read(H/'evidence/preparation.json');cls.lookup={r['id']:r for r in cls.p['routes']};cls.doc=read(pathlib.Path(cls.p['sources']['resolved_route_catalog']['path']))
 def test_unchanged_controller_and_loader(self):
  self.assertEqual((H/'Traversal.gd').read_bytes(),(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes())
  self.assertEqual((H/'RenderData.gd').read_bytes(),(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes())
 def test_exact_sources_and_implementation_snapshots(self):
  for ref in self.p['sources'].values():self.assertEqual(sha(pathlib.Path(ref['path'])),ref['sha256'])
  for path,digest in self.p['implementation_hashes'].items():
   self.assertEqual(sha(ROOT/path),digest)
   snapshot=self.p['implementation_snapshots'][path];self.assertEqual(sha(pathlib.Path(snapshot['path'])),digest)
 def test_complete_coverage_schema(self):
  expanded=catalog.validate(self.doc)
  self.assertEqual({r['id']for r in expanded},set(self.lookup))
  self.assertEqual(self.doc['coverage'],self.s['ownership_coverage'])
  self.assertEqual(len(self.doc['coverage']['public_roads']),42)
  self.assertEqual(len(self.doc['coverage']['primary_network_goals']),7)
  self.assertEqual(len(self.doc['coverage']['ordinary_entries']),100)
 def test_bidirectional_actual_geometry(self):
  for row in self.doc['routes']:
   if row.get('bidirectional'):
    a=self.lookup[row['id']];b=self.lookup[row['id']+'_REVERSE']
    self.assertEqual(b['points'],list(reversed(a['points'])))
    self.assertEqual(a['placement_ids'],b['placement_ids'])
    self.assertEqual(a['building_ids'],b['building_ids'])
 def test_all_results_accounted_without_relabeling_failures(self):
  self.assertEqual({r['id']for r in self.r['routes']},set(self.lookup))
  self.assertEqual(len(self.r['routes']),len(self.lookup))
  failures={r['id']for r in self.r['routes']if not r['pass']}
  self.assertEqual(failures,{r['case']for r in self.s['failures']})
  self.assertEqual(self.s['checks']['all_cases_pass_strict_original_acceptance'],not failures)
  expected='PASS_DECLARED_ACTUAL_PUBLIC_ROUTES'if all(self.s['checks'].values())else'FAILED_CASES_RETAINED'
  self.assertEqual(self.s['status'],expected)
 def test_summary_counts_match_raw_results(self):
  for name,row in self.s['coverage'].items():
   cases=[r for r in self.r['routes']if self.lookup[r['id']]['case_class']==name]
   self.assertEqual(row['cases'],len(cases));self.assertEqual(row['passed'],sum(bool(r['pass'])for r in cases));self.assertEqual(row['failed'],sum(not r['pass']for r in cases))
   self.assertEqual(row['status_counts'],dict(collections.Counter(r['status']for r in cases)))
 def test_actual_inputs_have_exact_parity(self):
  self.assertFalse(self.s['exact_input_parity']['asset_errors']);self.assertFalse(self.s['exact_input_parity']['placement_errors'])
  self.assertTrue(self.s['checks']['exact_scene_native_contract_inputs']);self.assertTrue(self.s['checks']['native_poses_match_integrated_scene'])
  self.assertEqual(self.r['prepared_sha256'],sha(H/'prepared_runtime.json'))
  self.assertEqual(self.s['result']['sha256'],sha(H/'evidence/public_network_replay.json'))
 def test_no_synthesized_floor_or_positive_unsupported_hint(self):
  self.assertFalse(self.r['collision_world']['infinite_ground_plane']);self.assertFalse(self.pre['unsupported_positive_hints'])
  for r in self.p['routes']:self.assertNotEqual(r['case_class'],'isolated_control')
  for r in self.p['routes']:
   if not r['minimum_allowed_feet_y_explicit']:self.assertEqual(r['minimum_allowed_feet_y_m'],min(p[1]for p in r['points'])-2.)
 def test_exact_released_native_activation(self):
  self.assertTrue(self.pre['activation_checks'])
  for row in self.pre['activation_checks']:
   self.assertFalse(row['missing_ids']);self.assertFalse(row['mismatched_ids']);self.assertFalse(row['retained_superseded_ids'])
 def test_verbatim_finite_public_owner_activation(self):
  row=self.pre['finite_public_field_activation'];self.assertIsNotNone(row);self.assertGreater(row['required_triangle_instances'],0);self.assertEqual(row['missing_triangle_instances'],0)
  if'finite_public_emission_revision'in self.doc['activation_requirements']:
   rev=row['bounded_emission_revision'];self.assertEqual(rev['unchanged_owner_records'],30778);self.assertEqual(rev['changed_previous_owner_records'],70);self.assertEqual(rev['missing_unaffected_original_triangle_instances'],0);self.assertEqual(rev['retired_triangle_instances_still_present'],0);self.assertTrue(rev['unchanged_heights_and_grade_exceptions'])
 def test_all_private_field_appends_are_verbatim(self):
  if'ready_entries_next18'not in self.doc['sources']:self.skipTest('Next18 was not part of this catalog')
  row=self.pre['appended_surface_activation'];self.assertEqual(len(row['patches']),3 if 'ready_entries_next20' in self.doc['sources'] else 2)
  for item in row['materials'].values():self.assertGreater(item['required_triangle_instances'],0);self.assertEqual(item['missing_triangle_instances'],0);self.assertEqual(item.get('retired_triangle_instances_still_present',0),0)
  self.assertEqual(len(row.get('private_emission_revisions',[])),len(self.doc['activation_requirements'].get('private_append_revisions',[])))
 def test_noble_sources_and_collision_contracts_activated(self):
  if'noble_integration_handoff'not in self.doc['sources']:self.skipTest('Noble source batch was not part of this catalog')
  rows=self.pre['declared_collision_contract_activation'];self.assertEqual(len(rows),7)
  self.assertTrue(all(r['exact_physical_fields_match']for r in rows))
  rows=[r for r in self.p['routes']if r.get('source_route_id','').startswith('NOBLE_FINE_ENTRY:')];self.assertEqual(len(rows),14)
 def test_all_explicit_design_exception_sources_remain_accounted(self):
  account=self.doc['source_candidate_accounting'];rows=account['grade_exception_probes']
  self.assertEqual(len(rows),43);self.assertEqual(sum(r['piece_count']for r in rows),102)
  self.assertEqual(len({r['source_triangle_index']for r in rows}),43)
  for row in rows:
   if row['status']=='accepted':
    self.assertTrue(any(r['unsupported_tube_area_m2']<1e-7 for r in row['trials']))
    self.assertTrue(all(rid in self.lookup and rid+'_REVERSE'in self.lookup for rid in row['route_ids']))
   else:self.assertTrue(row['reason'])
 def test_all_released_entries_have_two_directions(self):
  rows=[r for r in self.p['routes']if r['case_class']=='ordinary_entry']
  expected=83 if'ready_entries_next20'in self.doc['sources']else(63 if'ready_entries_next18'in self.doc['sources']else 45)
  self.assertEqual(len(rows),expected*2)
  ledger=self.doc['coverage']['ordinary_entries'];self.assertEqual(sum(r['status']=='accepted'for r in ledger),expected);self.assertEqual(sum(r['status']=='held'for r in ledger),100-expected)
 def test_prior_actual_alley_passes_are_preserved_as_regressions(self):
  rows=read(H/'prior_alley_reconciliation.json')['rows'];self.assertEqual(len(rows),13)
  for row in rows:
   self.assertTrue(row['exact_old_forward_and_reverse_xz_match']);self.assertTrue(row['prior_both_directions_passed'])
   self.assertTrue(all(rid in self.lookup for rid in row['case_ids']))
  self.assertEqual(len(self.doc['source_candidate_accounting']['held_private_junctions']),37)
 def test_local_crossings_common_and_actual_negative_controls_retained(self):
  self.assertEqual(sum(r['case_class']=='canal_crossing'for r in self.p['routes']),24)
  self.assertEqual(sum(r['case_class']=='common_entry'for r in self.p['routes']),6)
  for row in self.doc['routes']:
   if row.get('expected_failure')=='ground_lost':self.assertEqual(self.lookup[row['id']]['minimum_allowed_feet_y_m'],row['minimum_allowed_feet_y_m'])
   if row.get('expected_failure')=='blocked':self.assertTrue(row.get('expected_contact_id')or row.get('expected_contact_prefix'))
 def test_no_controller_errors_or_within_route_teleports(self):
  self.assertFalse(self.r['errors'])
  for row in self.r['routes']:self.assertEqual(row['within_route_teleports'],0)
 def test_previous_bounded_replay_evidence_unchanged(self):
  for name in['district_batch_r01','district_services_r02','district_services_r03']:
   folder=H.parent/name;seal=read(folder/'freeze_manifest.json')
   for path,digest in seal['owned_files'].items():self.assertEqual(sha(folder/path),digest)
if __name__=='__main__':unittest.main(verbosity=2)
