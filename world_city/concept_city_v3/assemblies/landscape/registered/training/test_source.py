import json,math,unittest
from . import author as t,ground
from world_city.concept_city_v3.assemblies.property.registered import author as a
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=json.loads((t.OUT/'source_pack.json').read_text());cls.d=t.source_inputs();cls.w=json.loads((t.OUT/'ground_wrapper.json').read_text())
 def test_source_binding_counts_and_replacements(self):
  p=self.p;self.assertEqual(p['sources'],self.d['sources']);self.assertEqual(len(p['placements']),11);self.assertEqual(len(p['actual_doors']),8);self.assertEqual(len(p['internal_routes']),9);self.assertEqual(p['replacement_ledger']['source_building_ids'],['B_TRAIN_0','B_TRAIN_1']);self.assertEqual(p['replacement_ledger']['source_owned_path_ids'],['B_TRAIN_0:DOOR','B_TRAIN_1:DOOR'])
 def test_large_connected_exercise_core(self):
  core=self.p['central_exercise_reservation']['polygon_xz_m'];self.assertTrue(a.contained(core,self.p['source_space']['polygon_xz_m']));self.assertGreater(a.geom.polygon_area(core),6000)
  for p in self.p['placements']:self.assertFalse(a.overlap(core,p['footprint_xz_m']))
  for e in self.d['exclusions']:
   if e['kind'] in ('public_road_and_half_metre_shoulder','native_fortification_outer_envelope','native_landmark_outer_envelope','native_ordinary_outer_envelope','finite_water'):self.assertFalse(a.overlap(core,e['polygon_xz_m']),e['id'])
 def test_finite_placement_and_road_clearance(self):
  for i,p in enumerate(self.p['placements']):
   self.assertEqual(p['scale'],[1,1,1]);self.assertTrue(a.contained(p['footprint_xz_m'],self.p['source_space']['polygon_xz_m']))
   for q in self.p['placements'][:i]:self.assertFalse(a.overlap(p['footprint_xz_m'],q['footprint_xz_m']))
   for e in self.d['exclusions']:self.assertFalse(a.overlap(p['footprint_xz_m'],e['polygon_xz_m']),(p['id'],e['id']))
 def test_exact_door_floors_and_support(self):
  for door in self.p['actual_doors']:self.assertEqual(door['door_xyz_m'][1],18)
  for row in self.p['native_support_samples']:
   for s in row['samples']:self.assertAlmostEqual(s['floor_delta_m'],0,8);self.assertEqual(s['owner_id'],'TRAIN')
  for tri in a.triangulate(t.CORE):
   for p in tri+[a.centre(tri)]:self.assertAlmostEqual(t.terrain.land_height_at(*p),18,8)
 def test_all_doors_connect_and_core_stays_clear(self):
  doors={d['id'] for d in self.p['actual_doors']};self.assertEqual(doors,{r['door_id'] for r in self.p['internal_routes'] if 'door_id' in r})
  for r in self.p['internal_routes']:
   if 'door_id' in r:self.assertEqual(r['polyline_xz_m'][-1],self.p['gate']['center_xz_m'])
   for poly in r['ribbon_polygons_xz_m']:
    self.assertTrue(a.contained(poly,self.p['source_space']['polygon_xz_m']))
    for p in self.p['placements']:self.assertFalse(a.overlap(poly,p['footprint_xz_m']),(r['id'],p['id']))
    if 'door_id' in r:self.assertFalse(a.overlap(poly,t.CORE),r['id'])
 def test_finite_approach_profile_and_road_endpoint(self):
  s=self.p['external_surface'];self.assertLessEqual(s['maximum_service_ramp_grade'],.1);self.assertLessEqual(s['maximum_inherited_public_landing_grade'],.12);self.assertLess(s['maximum_cut_fill_m'],.21)
  road=next(r for r in self.d['plan']['roads'] if r['id']=='CASTLE_APPROACH');rs=[a.geom.road_ribbon(u,v,road['width_m']) for u,v in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])];self.assertTrue(a.polygon_covered_by_union(s['polygon_regions_xz_m'][-1],rs,1e-6))
  for p in s['polygon_regions_xz_m']:
   for e in self.d['exclusions']:
    if e['kind'] in ('native_fortification_outer_envelope','native_landmark_outer_envelope','native_ordinary_outer_envelope','finite_water'):self.assertFalse(a.overlap(p,e['polygon_xz_m']),e['id'])
 def test_finite_common_ground_and_caps(self):
  for r in self.w['owned_floor_regions']:
   self.assertTrue(a.contained(r['polygon_xz_m'],self.p['source_space']['polygon_xz_m']))
   for e in self.d['exclusions']:
    if e['kind'] in ('public_road_and_half_metre_shoulder','native_fortification_outer_envelope','native_landmark_outer_envelope','native_ordinary_outer_envelope','finite_water'):self.assertFalse(a.overlap(r['polygon_xz_m'],e['polygon_xz_m']),e['id'])
  records=[self.w]+[v for v in self.p['assets'].values() if v['kind']=='new_common'];self.assertEqual(len(records),4)
  for r in records:self.assertLessEqual(r['candidate_budget']['exact_candidate_visits_without_cell_sampling'],300000);self.assertEqual(a.file_sha(t.c.ROOT/r['source_path']),r['source_sha256'])
if __name__=='__main__':unittest.main()
