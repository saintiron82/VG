import json,math,unittest
from .screen import HERE
from .. import author as a
from world_city.concept_city_v3.registered_integration.r7 import surface_guard

class ReadySubset(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());cls.pack=json.loads((HERE/'native_pack_ready_r02.json').read_bytes());cls.patch=json.loads((HERE/'top_scene_patch_r02.json').read_bytes());cls.accept=json.loads((HERE/'ready_subset_acceptance_r01.json').read_bytes());cls.routes=json.loads((HERE/'route_handoff_ready_r02.json').read_bytes());cls.scene=a.load_scene()
 def test_base_scene_hash(self):self.assertEqual(self.patch['base_scene_sha256'],a.SCENE_SHA256)
 def test_matching_native_subset(self):
  ids=set(self.hand['accepted_holding_ids']);self.assertEqual(len(ids),23);self.assertEqual({r['holding_id']for r in self.pack['placements']},ids);self.assertEqual({r['holding_id']for r in self.pack['actual_doors']},ids);self.assertEqual(len(self.pack['actual_doors']),102)
 def test_atomic_retirement(self):
  ids=set(self.hand['accepted_holding_ids']);retired={r['source_id']for r in self.hand['retirement_records']};self.assertEqual(len(retired),60);self.assertEqual(retired,set(self.pack['replaced_placement_ids']))
  for r in self.hand['retirement_records']:self.assertLessEqual(set(r['affected_holding_ids']),ids)
 def test_original_edit_index_and_hash(self):
  seen=set()
  for r in self.patch['surface_edits']:
   k=(r['material'],r['triangle_index']);self.assertNotIn(k,seen);seen.add(k);tri=self.scene['surfaces'][k[0]][3*k[1]:3*k[1]+3];self.assertEqual(a.canonical_sha(tri),r['source_triangle_sha256'])
 def test_unchanged_remainder_planes(self):
  for r in self.patch['surface_edits']:
   tri=self.scene['surfaces'][r['material']][3*r['triangle_index']:3*r['triangle_index']+3];plane=a.common.plane(tri)
   for tr in r['replacement_triangles_xyz_m']:
    for x,y,z in tr:self.assertLessEqual(abs(y-a.common.height(plane,[x,z])),1e-7)
 def test_upward_actual_emission(self):self.assertEqual(surface_guard.audit_patch(self.patch)['downward'],0)
 def test_actual_emitted_grade(self):
  for r in self.accept['emitted_top_report']:self.assertEqual(r['over_grade'],0);self.assertLessEqual(r['maximum_actual_gradient'],.12000001)
 def test_native_support_and_no_duplicate_top(self):
  self.assertEqual(self.accept['support_failures'],[]);self.assertEqual(self.accept['native_top_overlaps'],[]);self.assertEqual(self.accept['summary']['native_conflicts'],0);self.assertEqual(self.accept['summary']['native_bearings'],687)
 def test_exact_finite_source_coverage(self):
  report=json.loads((HERE/'top_coverage_report_r02.json').read_bytes());self.assertEqual(report['status'],'PASSED_TOP_SOURCE_COVERAGE');self.assertEqual(report['failures'],[])
 def test_lacuna_owner_protection(self):
  report=json.loads((HERE/'source_lacuna_classification_r01.json').read_bytes());self.assertEqual(report['summary']['existing_owner_hits'],0);self.assertLess(report['summary']['area_m2'],.011)
  for r in report['records']:self.assertLessEqual(max(r['adjacent_cut_max_m'],r['adjacent_fill_max_m']),2.5)
 def test_shared_public_routes(self):
  self.assertEqual(self.routes['failures'],[]);self.assertEqual(len(self.routes['entries']),23);self.assertEqual(len(self.routes['internal_door_routes']),102)
  for r in self.routes['entries']:self.assertEqual(r['errors'],[]);self.assertLessEqual(r['maximum_centerline_grade'],.12000001)
 def test_no_independent_bank_or_water_patch(self):
  self.assertNotIn('bank',self.patch['appended_surfaces']);self.assertNotIn('water',self.patch['appended_surfaces']);self.assertFalse(any(r['material']in('bank','water')for r in self.patch['surface_edits']))
if __name__=='__main__':unittest.main()
