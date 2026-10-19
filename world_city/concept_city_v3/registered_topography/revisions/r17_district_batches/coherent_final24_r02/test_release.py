import json,math,unittest
from .prepare import HERE,REQUEST,load
from .. import author as a
from .....registered_integration.r7 import surface_guard
class FinalRelease(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.request=json.loads(REQUEST.read_bytes());cls.hand=json.loads((HERE/'physical_owner_handoff_r03.json').read_bytes());cls.pack=json.loads((HERE/'native_pack_ready_r03.json').read_bytes());cls.patch=json.loads((HERE/'top_scene_patch_r01.json').read_bytes());cls.accept=json.loads((HERE/'physical_acceptance_r01.json').read_bytes());cls.routes=json.loads((HERE/'route_handoff_ready_r05.json').read_bytes());cls.scene=a.load_scene()
 def test_matched23(self):
  ids=set(self.hand['accepted_holding_ids']);self.assertEqual(len(ids),23);self.assertEqual(ids,set(self.request['matched_next_batch_holding_ids']));self.assertEqual(ids,{r['holding_id']for r in self.pack['placements']});self.assertEqual(len(self.pack['placements']),215);self.assertEqual(len(self.pack['actual_doors']),123)
 def test_retirement69(self):self.assertEqual(len(self.hand['retirement_records']),69);self.assertEqual(set(self.request['exact_retirement_ids']),set(self.pack['replaced_placement_ids']))
 def test_existing_hall_preserved(self):
  self.assertNotIn('BLOCK_008:R8_C003',self.hand['accepted_holding_ids']);self.assertTrue(self.hand['superseded_protected_domains']);self.assertFalse(any(r.get('holding_id')=='BLOCK_008:R8_C003'for r in self.pack['placements']))
 def test_native_support(self):self.assertTrue(self.accept['passed']);self.assertEqual(self.accept['summary']['ordinary_bearings'],574);self.assertEqual(self.accept['summary']['variable_bottom_sections'],704)
 def test_index_hash(self):
  seen=set()
  for r in self.patch['surface_edits']:
   key=r['material'],r['triangle_index'];self.assertNotIn(key,seen);seen.add(key);self.assertEqual(r['source_triangle_sha256'],a.canonical_sha(self.scene['surfaces'][key[0]][key[1]*3:key[1]*3+3]))
 def test_preserved_remainder_planes(self):
  for r in self.patch['surface_edits']:
   source=self.scene['surfaces'][r['material']][r['triangle_index']*3:r['triangle_index']*3+3];plane=a.common.plane(source)
   for tr in r['replacement_triangles_xyz_m']:
    for x,y,z in tr:self.assertLessEqual(abs(y-a.common.height(plane,[x,z])),1e-7)
 def test_upward_emission(self):self.assertEqual(surface_guard.audit_patch(self.patch)['downward'],0)
 def test_actual_route_planes(self):self.assertFalse(self.routes['failures']);self.assertEqual(len(self.routes['entries']),23);self.assertEqual(len(self.routes['internal_door_routes']),123)
 def test_inner_chains_bound(self):self.assertEqual(len(load(self.request['inner_entry_chain_handoff'])['records']),8)
 def test_local_grade_exceptions(self):
  exceptions={r['holding_id']:r['limit']for r in self.accept['grade_records']if r['pedestrian_exception']};self.assertEqual(exceptions,{'BLOCK_001:R8_C003':.25,'BLOCK_004:R8_C004':.15,'BLOCK_005:R8_C008':.15})
 def test_top_source_coverage(self):self.assertEqual(json.loads((HERE/'top_coverage_report_r01.json').read_bytes())['status'],'PASSED_TOP_SOURCE_COVERAGE')
 def test_local_sides(self):self.assertEqual(json.loads((HERE/'local_boundary_review_r01.json').read_bytes())['status'],'PASS_LOCAL_FINITE_BOUNDARY')
 def test_no_water_changes(self):self.assertNotIn('water',self.patch['appended_surfaces']);self.assertFalse(any(r['material']=='water'for r in self.patch['surface_edits']))
 def test_accepted61_domains(self):self.assertTrue(all(r['positive_intersection_area_m2']<1e-8 for r in json.loads((HERE/'accepted61_composition_ledger_r01.json').read_bytes())['comparisons']))
 def test_atomic_native_source_binding(self):self.assertTrue(load(load(json.loads((HERE/'input_binding.json').read_bytes())['atomic_source_addendum'])['native_audit'])['passed'])
 def test_current_generated_producer_binding(self):
  ledger=json.loads((HERE/'generated_bank_source_ledger_r01.json').read_bytes());self.assertEqual(ledger['source_main_binding'],self.request['current_main_binding']);self.assertEqual(ledger['source_main_binding']['sha256'],'c9476a7251e2977bb7bed77590bf80ebe2bc580ccccd3a2960cd080946af3f90');self.assertEqual([r['producer_index']for r in ledger['producer_replacements']],[6,16]);self.assertEqual(len(ledger['rows']),587)
 def test_generated_producer_exact_remainders(self):
  ledger=json.loads((HERE/'generated_bank_source_ledger_r01.json').read_bytes())
  for rep in ledger['producer_replacements']:
   old=load(rep['original']);new=load(rep['replacement']);rows={r['appended_triangle_index']:r for r in ledger['rows']if r['producer_index']==rep['producer_index']};expected=[];vs=old['appended_surfaces']['bank']
   for i in range(len(vs)//3):
    tr=vs[i*3:i*3+3]
    if i in rows:self.assertEqual(a.canonical_sha(tr),rows[i]['source_triangle_sha256']);self.assertEqual(tr,rows[i]['source_vertices_xyz_m'])
    expected.extend(v for t in rows[i]['replacement_triangles_xyz_m']for v in t) if i in rows else expected.extend(tr)
   self.assertEqual(expected,new['appended_surfaces']['bank'])
   self.assertEqual({k:v for k,v in old.items()if k!='appended_surfaces'},{k:v for k,v in new.items()if k not in ('appended_surfaces','final23_bank_retirement')})
   self.assertEqual({k:v for k,v in old['appended_surfaces'].items()if k!='bank'},{k:v for k,v in new['appended_surfaces'].items()if k!='bank'})
 def test_incident_metadata_parity(self):
  p=json.loads((HERE/'incident_metadata_parity_r01.json').read_bytes());self.assertTrue(p['passed']);self.assertEqual(len(p['explicit_private_risers']),4);self.assertEqual(p['explicit_private_risers'],self.hand['explicit_profile_risers'])
 def test_b17_prerequisite(self):
  r=[r for r in self.request['public_prerequisites']if r['path'].endswith('b17_local_alley_r01/scene_patch.json')];self.assertEqual(len(r),1);load(r[0])
 def test_final_source_and_route_metadata(self):
  load(self.hand['source_continuation']);load(self.hand['step_collision_contract']);self.assertEqual(self.routes['terrain_handoff']['sha256'],a.sha(HERE/'physical_owner_handoff_r03.json'));self.assertTrue(any(r['existing_public_top_overlaps']for r in self.routes['entries']))
if __name__=='__main__':unittest.main()

