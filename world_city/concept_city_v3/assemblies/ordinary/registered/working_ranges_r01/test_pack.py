"""Focused staged-pack validation; never activates a scene or edits prior inputs."""
import unittest
from .design import *
from .ground import geo
from voxel_character.common import core
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.finalize_rows import face_bijection

class PackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.s=load(HERE/'selection.json');cls.n=load(HERE/'native_geometry.json');cls.a=load(HERE/'access_handoff.json');cls.h=load(HERE/'terrain_handoff.json');cls.c=load(HERE/'compile_report.json');cls.p=load(HERE/'resolved_placements.json')
 def test_all_input_hashes_unchanged(self):
  for r in self.s['references']+self.h['protection_refs']+[self.h['bound_terrain_author'],self.h['bound_terrain_contract']]:self.assertEqual(ref(ROOT/r['path']),r)
 def test_exact_budget_and_common_faces(self):
  self.assertEqual(sum(x['candidate_cells']for x in self.c['progress']),98465)
  for a in self.c['assets'].values():
   for typ in ('master','compiled','render'):self.assertEqual(ref(ROOT/a[typ+'_path'])['sha256'],a[typ+'_sha256'])
   c=load(ROOT/a['compiled_path']);r=load(ROOT/a['render_path']);self.assertTrue(c['valid']);self.assertEqual(core.digest(c['cells']),r['payload_hash']);proof=face_bijection(c,r);self.assertEqual(proof['duplicate_or_internal_unit_faces'],0);self.assertEqual(proof['missing_unit_faces'],0)
 def test_native_masks_contained(self):
  for p in self.n['placements']:
   env=p['source_parcel']['building_envelope_xz_m'];self.assertEqual(p['scale'],[1,1,1])
   for key in ('native_foundation_polygons_xz_m','native_roof_polygons_xz_m','body_envelope_polygons_xz_m'):
    for poly in p[key]:self.assertAlmostEqual(geo.polygon_area(poly),geo.intersection_area(poly,env),places=6)
 def test_true_door_leaf_provenance(self):
  self.assertEqual(len(self.n['actual_doors']),15)
  for d in self.n['actual_doors']:
   self.assertTrue(d['native_face_evidence']);self.assertLessEqual(abs(d['native_sampling_delta_m']),.251);self.assertEqual(d['actual_door_xyz_m'][1],2.5)
 def test_full_width_native_clear_internal_routes(self):
  self.assertEqual(len(self.a['unresolved_doors']),0);self.assertEqual({d['id']for d in self.n['actual_doors']},{r['door_id']for r in self.a['internal_routes']})
  obstacles=[q for p in self.n['placements']for q in p['native_walking_obstacles_xz_m']]
  for r in self.a['internal_routes']:
   g=r['ground_audit'];self.assertTrue(g['fully_covered']);self.assertAlmostEqual(g['min_y_m'],2.5);self.assertAlmostEqual(g['max_y_m'],2.5)
   for p in r['ribbon_and_join_polygons_xz_m']:
    for q in obstacles:self.assertLess(geo.intersection_area(p,q),1e-6)
 def test_internal_routes_stay_in_their_preserved_holding(self):
  holds={h['id']:h for h in self.s['selected_holdings']}
  indexes={}
  for key,h in holds.items():
   index=geo._SpatialIndex(8)
   for i,q in enumerate(h['polygon_parts_xz_m']):index.add(i,q)
   indexes[key]=index
  for r in self.a['internal_routes']:
   parts=holds[r['holding_id']]['polygon_parts_xz_m'];index=indexes[r['holding_id']]
   for p in r['ribbon_and_join_polygons_xz_m']:
    area=sum(geo.intersection_area(p,parts[i])for i in index.candidates(p));self.assertAlmostEqual(area,geo.polygon_area(p),places=6)
 def test_foundations_finite_and_embedded(self):
  self.assertEqual(len(self.h['native_foundation_owners']),4)
  for p in self.h['native_foundation_owners']:self.assertEqual(p['required_ground_hole_y_m'],2.0);self.assertEqual(p['embed_depth_m'],.5);self.assertFalse(p['additional_support_required'])
  for r in self.n['native_ground_proofs']:self.assertTrue(r['actual_foundation_ground']['fully_covered'])
 def test_public_seam_holds_are_not_approval(self):
  self.assertEqual(len(self.h['terminal_grade_holds']),2)
  for r in self.h['terminal_grade_holds']:
   self.assertTrue(r['status'].startswith('INACTIVE'));self.assertEqual(r['review_length_m'],12);self.assertGreater(r['maximum_actual_triangle_gradient_m_per_m'],.12);self.assertTrue(r['existing_actual_terrain']['fully_covered'])
  self.assertEqual(self.p['replaced_placement_ids'],[]);self.assertEqual(self.p['superseded_path_ids'],[])
 def test_all_original_candidates_retained(self):
  original=load(PLAN/'implementation_sequence.json')['range_design_queue'];self.assertEqual(len(self.p['unimplemented_range_ledger']),26);self.assertEqual({p['parcel_id']for p in original},{p['parcel_id']for p in self.p['unimplemented_range_ledger']});self.assertEqual(sum(p['status'].startswith('compiled')for p in self.p['unimplemented_range_ledger']),4)
 def test_courts_are_finite_unimplemented_sources(self):
  courts=load(HERE/'court_plan.json');self.assertEqual(courts['total_reserved_court_m2'],110)
  for c in courts['courts']:self.assertIn('Unimplemented',c['native_implementation_status']);self.assertTrue(c['ground_audit']['fully_covered']);self.assertAlmostEqual(c['ground_audit']['max_y_m'],2.5)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(PackTests);result=unittest.TextTestRunner(verbosity=2).run(suite);write(HERE/'test_results.json',dict(schema='riverstone.working_ranges.tests.v1',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),resolved_pack=ref(HERE/'resolved_placements.json'),scope='Focused source/native geometry, finite terrain and pending-state checks. No engine/GUI/capsule test.'));raise SystemExit(not result.wasSuccessful())
