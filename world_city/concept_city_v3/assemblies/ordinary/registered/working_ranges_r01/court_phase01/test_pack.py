"""Focused native, source preservation, route and exact-ground checks."""
import unittest
from .resolve import *
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.finalize_rows import face_bijection
class PackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.s=load(HERE/'source_plan.json');cls.p=load(HERE/'resolved_placements.json');cls.h=load(HERE/'terrain_handoff.json');cls.c=load(HERE/'compile_report.json');cls.g=load(HERE/'ground_proof.json')
 def test_sealed_parent_unchanged(self):
  for f in load(PARENT/'freeze_manifest.json')['files']:self.assertEqual(ref(ROOT/f['path']),f)
  self.assertEqual(ref(PARENT/'freeze_manifest.json')['sha256'],'ef46c6a28440eb82d749324a13ca1ae40c2437c1d27e0c50a390218d4da6de3d')
 def test_bound_native_input_hashes(self):
  for a in self.p['assets'].values():
   for kind in('master','render'):
    self.assertEqual(ref(ROOT/a[kind+'_path'])['sha256'],a[kind+'_sha256'])
  for v in ('source_plan','compile_report'):self.assertEqual(self.p[v],ref(HERE/(v+'.json')))
  self.assertEqual(self.g['terrain_handoff'],ref(HERE/'terrain_handoff.json'));self.assertEqual(self.g['placement_pack'],ref(HERE/'resolved_placements.json'))
 def test_exact_small_compile_and_faces(self):
  self.assertEqual(sum(p['candidate_cells']for p in self.c['progress']),7332)
  for a in self.c['assets'].values():
   comp=load(ROOT/a['compiled_path']);r=load(ROOT/a['render_path']);self.assertTrue(comp['valid']);self.assertEqual(core.digest(comp['cells']),r['payload_hash']);self.assertEqual(face_bijection(comp,r)['missing_unit_faces'],0)
 def test_actual_bearing_faces(self):
  assets=self.p['assets'];placements={p['id']:p for p in self.p['placements']}
  for b in self.h['native_bearing_owners']:
   p=placements[b['placement_id']];r=load(ROOT/assets[p['asset_key']]['render_path']);quad=r['groups'][b['group_index']]['quads'][b['quad_index']];self.assertTrue(all(abs(q[1]-b['bottom_y_local_m'])<1e-8 for q in quad));world=[xform([q[0],q[2]],[p['position_m'][0],p['position_m'][2]],p['yaw_rad'])for q in quad];self.assertEqual(world,b['polygon_xz_m']);self.assertAlmostEqual(b['required_ground_hole_y_m'],2.5+b['bottom_y_local_m'])
 def test_finite_disjoint_bearings(self):
  bs=self.h['native_bearing_owners'];self.assertEqual(len(bs),51);cuts=[b for b in bs if b['requires_finite_terrain_cut']];self.assertEqual(len(cuts),48);self.assertAlmostEqual(sum(geo.polygon_area(b['polygon_xz_m'])for b in cuts),7.25)
  for i,b in enumerate(bs):
   for c in bs[i+1:]:self.assertLess(geo.intersection_area(b['polygon_xz_m'],c['polygon_xz_m']),1e-7)
 def test_current_actual_ground(self):
  self.assertEqual(ref(R6)['sha256'],R6_HASH);self.assertTrue(self.g['all_actual_ground_exactly_2_5']);self.assertEqual(len(self.g['proofs']),53)
  for q in self.g['proofs']:self.assertAlmostEqual(q['area_m2'],q['covered_area_m2']);self.assertAlmostEqual(q['min_y_m'],2.5);self.assertAlmostEqual(q['max_y_m'],2.5);self.assertTrue(q['pieces'])
 def test_native_court_containment(self):
  cs={c['id']:c for c in self.s['courts']}
  for p in self.p['placements']:
   self.assertEqual(p['scale'],[1,1,1])
   for q in p['native_collision_polygons_xz_m']:self.assertAlmostEqual(geo.polygon_area(q),geo.intersection_area(q,cs[p['court_id']]['source']['polygon_xz_m']),places=7)
 def test_protected_entrances_and_finite_court_links(self):
  self.assertEqual(len([r for r in self.p['protected_routes']if r['kind']=='entrance_or_public_lane']),17)
  for p in self.p['placements']:
   for q in p['native_collision_polygons_xz_m']:
    for route in self.p['protected_routes']:
     for r in route['polygons']:self.assertLess(geo.intersection_area(q,r),1e-7)
  link=[r for r in self.p['protected_routes']if r['kind']=='court_link_correction'][0];self.assertGreater(math.dist(*link['polyline_xz_m']),1);self.assertEqual(link['width_m'],2)
 def test_native_three_dimensional_collisions(self):
  self.assertEqual(self.p['conflicts'],[]);self.assertEqual(len(self.p['native_mutual_collision_proofs']),6)
  for q in self.p['native_mutual_collision_proofs']:self.assertAlmostEqual(q['native_volume_overlap_m3'],0)
  native=load(PARENT/'native_geometry.json')
  for p in self.p['placements']:
   for q in p['native_collision_polygons_xz_m']:
    for building in native['placements']:
     for r in building['native_walking_obstacles_xz_m']:self.assertLess(geo.intersection_area(q,r),1e-7)
 def test_no_paving_and_deliberate_openings(self):
  self.assertTrue(self.p['no_native_paving']);self.assertTrue(self.h['no_whole_court_exclusion'])
  for key in ('domestic_boundary','work_boundary'):
   a=self.p['assets'][key];m=load(ROOT/a['master_path']);self.assertTrue(m['extensions']['no_floor_geometry']);self.assertTrue(m['extensions']['opening_intervals']);self.assertTrue(m['extensions']['boundary_segments'])
  self.assertEqual(self.p['replaced_placement_ids'],[])
 def test_runtime_ids_are_court_qualified(self):
  self.assertEqual(len({p['id'] for p in self.p['placements']}),6)
  for p in self.p['placements']:self.assertEqual(p['id'],p['court_id']+':'+p['local_component_id'])
  self.assertTrue(load(HERE/'id_qualification.json')['native_geometry_identical'])
 def test_functional_fronts_and_approaches(self):
  f=load(HERE/'functional_use.json');self.assertEqual(f['placement_pack'],ref(HERE/'resolved_placements.json'));self.assertEqual(len(f['use_fronts']),3)
  for z in f['use_fronts']:
   for p in self.p['placements']:
    for obstacle in p['native_collision_polygons_xz_m']:
     for q in [z['clear_workfront_polygon_xz_m']]+z['approach_polygons_xz_m']:self.assertLess(geo.intersection_area(q,obstacle),1e-7)
   for route in self.p['protected_routes']:
    for q in route['polygons']:self.assertLess(geo.intersection_area(z['clear_workfront_polygon_xz_m'],q),1e-7)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(PackTests);r=unittest.TextTestRunner(verbosity=2).run(suite);write(HERE/'test_results.json',dict(schema='riverstone.court_phase01.tests.v1',tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful(),placement_pack=ref(HERE/'resolved_placements.json'),terrain_handoff=ref(HERE/'terrain_handoff.json'),scope='Native/source/actual frozen-ground and exact geometry checks only; no GUI, full-city terrain export or character/capsule approval.'));raise SystemExit(not r.wasSuccessful())
