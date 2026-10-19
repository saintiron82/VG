"""Exact scene/source integrity, scope and honest omission checks."""
import collections,hashlib,json,pathlib,unittest
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class Coverage(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=read(H/'facility_coverage.json');cls.r=read(H/'actual_registry.json');cls.s=read(ROOT/cls.d['scene']['path']);cls.original=read(ROOT/cls.d['frozen_original_inventory']['path']);cls.lookup={r['id']:r for r in cls.r['instances']}
 def test_exact_scene_and_frozen_original_inventory(self):
  for ref in [self.d['scene'],self.d['frozen_original_inventory'],self.d['actual_registry'],self.d['retained_water_binding']]:self.assertEqual(sha(ROOT/ref['path']),ref['sha256'])
 def test_all_109_required_rows_once(self):
  self.assertEqual({r['id']for r in self.d['entries']},{r['id']for r in self.original['entries']});self.assertEqual(len(self.d['entries']),109)
 def test_complete_actual_registry(self):
  self.assertEqual(self.r['instances'],self.s['common_instances']);self.assertEqual(len(self.r['instances']),3567);self.assertEqual(set(self.r['assets']),set(self.s['common_assets']));self.assertEqual(len(self.r['assets']),263)
 def test_all_source_cache_hashes(self):
  for path,digest in read(H/'source_closure.json')['dependencies'].items():self.assertEqual(sha(ROOT/path),digest,path)
 def test_native_family_ids_and_asset_bindings(self):
  for row in self.d['entries']:
   self.assertEqual(len(row['native_instance_ids']),row['native_instance_count']);self.assertEqual(len(set(row['native_instance_ids'])),row['native_instance_count'])
   expected={self.lookup[x]['asset_key']for x in row['native_instance_ids']}|{r['asset_key']for r in row['bridge_pose_evidence']};self.assertEqual(set(row['asset_keys']),expected)
   self.assertEqual(row['actual_common_asset_placed_in_r04'],bool(row['native_instance_ids']or row['bridge_pose_evidence']))
   for ref in row['geometry_cache_refs']:
    self.assertEqual(ref['source'],self.r['assets'][ref['asset_key']]['source']);self.assertEqual(ref['cache'],self.r['assets'][ref['asset_key']]['cache'])
 def test_component_evidence_is_explicit_source_component(self):
  for row in self.d['entries']:
   for key,names in row['component_evidence'].items():self.assertTrue(set(names)<=set(self.r['assets'][key]['component_ids']));self.assertIn(key,row['asset_keys'])
 def test_source_only_and_missing_never_counted_as_actual(self):
  for row in self.d['entries']:
   if row['status']in['source_only','missing']:self.assertFalse(row['actual_common_asset_placed_in_r04']);self.assertFalse(row['surface_evidence']);self.assertIsNone(row['water_domain_evidence'])
 def test_every_family_has_remaining_scope(self):
  for row in self.d['entries']:self.assertTrue(row['omissions']);self.assertTrue(row['interiors']);self.assertTrue(row['runtime']);self.assertFalse(row['complete_facility_claim']);self.assertFalse(row['actual_viewed_in_this_audit'])
  self.assertFalse(self.d['whole_city_completion_claim'])
 def test_legacy_reference_hash_differences_are_not_hidden(self):
  changed=set()
  for row in self.d['entries']:
   for r in row['historical_source_refs']+row['historical_cache_refs']:
    if r['exists']:self.assertEqual(sha(ROOT/r['path']),r['current_sha256'])
    if r['historical_hash_matches']is False:changed.add(r['path'])
  self.assertEqual(changed,{'world_city/reference/revision_02/prompt.txt'})
 def test_runtime_evidence_retains_exact_failure(self):
  ref=self.d['exact_scene_runtime_evidence'];self.assertEqual(sha(ROOT/ref['path']),ref['sha256']);r=read(ROOT/ref['path']);self.assertEqual(r['scene'],self.d['scene']);self.assertEqual(r['status'],'FAILED_CASES_RETAINED');self.assertEqual(sum(x['passed']for x in r['coverage'].values()),45);self.assertEqual(sum(x['cases']for x in r['coverage'].values()),46)
 def test_water_source_membership_all_retained(self):
  w=read(H/'retained_water_binding.json');self.assertEqual(len(w['rows']),143);self.assertTrue(w['all_previous_water_triangles_present']);self.assertTrue(w['all_previous_bed_sources_present'])
 def test_counts_are_consistent_and_nonadditive(self):
  c=self.d['counts'];self.assertEqual(c['family_status'],dict(collections.Counter(r['status']for r in self.d['entries'])));self.assertEqual(sum(c['family_status'].values()),109);self.assertEqual(c['families_with_native_placements'],sum(r['actual_common_asset_placed_in_r04']for r in self.d['entries']))
if __name__=='__main__':unittest.main(verbosity=2)
