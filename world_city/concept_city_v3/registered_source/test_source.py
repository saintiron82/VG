"""Bounded source-contract checks; no claim of full access approval."""
import unittest,json,hashlib,math
from pathlib import Path
from .author import Domain,nearest,box
from .controls import RAW,SOURCE
from .geometry import triangulate
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.validation.check_registration import project_xyz
P=Path(__file__).parent
class RegisteredSourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=json.loads((P/'plan.json').read_text());cls.roads={r['id']:r for r in cls.p['roads']};cls.plots={p['id']:p for p in cls.p['plots']}
 def test_frozen_original_unchanged(self):self.assertEqual(hashlib.sha256((P.parent/'source/plan.json').read_bytes()).hexdigest(),'b341bdf4547dffd3a8ca8e7c2e4ed5bae8520c36bcfa13e3bea925bd9e89f89a')
 def test_control_sha(self):self.assertEqual(self.p['registration']['controls_sha256'],hashlib.sha256(SOURCE.read_bytes()).hexdigest())
 def test_correspondence_projection(self):
  for q in self.p['correspondences']:
   for pixel,xyz in zip(q['trace_pixel_xy'],q['world_xyz_m']):self.assertLess(math.dist(pixel,project_xyz(RAW['camera_model'],xyz)),.00001)
 def test_road_projection(self):
  for r in self.p['roads']:
   if 'resolved_world_xyz_m' not in r:continue
   for pixel,xyz in zip(r['trace_pixel_xy'],r['resolved_world_xyz_m']):self.assertLess(math.dist(pixel,project_xyz(RAW['camera_model'],xyz)),.00001)
 def test_wall_projection(self):
  w=self.p['wall_registration']
  for pixel,xyz in zip(w['trace_pixel_xy'],w['world_xyz_m']):self.assertLess(math.dist(pixel,project_xyz(RAW['camera_model'],xyz)),.00001)
 def test_real_ordinary_footprints(self):
  domain=Domain([self.p['boundary_xz_m']])
  for b in self.p['buildings']:
   if not b['id'].startswith('B_REG_'):continue
   self.assertTrue(domain.contains(b['footprint_xz_m']));self.assertTrue(Domain([self.plots[b['plot_id']]['polygon_xz_m']]).contains(b['footprint_xz_m']))
   self.assertIn(b['width_m'],(6,8,10,12));self.assertIn(b['depth_m'],(10,14,18))
 def test_ordinary_routes_meet_actual_road(self):
  for path in self.p['paths']:
   if not path.get('owner_building_id','').startswith('B_REG_'):continue
   dist=nearest(path['polyline_xz_m'][-1],[self.roads[path['road_id']]])[0][0];self.assertLess(dist,1e-6)
 def test_ordinary_bodies_do_not_overlap(self):
  ds=Domain()
  for b in self.p['buildings']:
   self.assertFalse(ds.hits(b['footprint_xz_m']),b['id']);ds.add(b['footprint_xz_m'],b['id'])
 def test_noble_shared_edges_disjoint(self):
  for a,b in [('E3','E6'),('E5','E7')]:
   overlap=sum(g.polygon_area(g.convex_intersection(t,u)) for t in triangulate(self.plots[a]['polygon_xz_m']) for u in triangulate(self.plots[b]['polygon_xz_m']));self.assertLess(overlap,1e-5)
 def test_components_are_specialist_snapshot(self):
  original=json.loads((P/'snapshots/registered_r0_landmark_groups.json').read_text())
  self.assertEqual(self.p['landmark_components'][:4],original);self.assertEqual(sum(len(g['masses']) for g in self.p['landmark_components'][:4]),219)
 def test_finished_floor_not_origin(self):
  for b in self.p['buildings']:
   self.assertTrue(math.isfinite(b['pad_floor_y_m']));self.assertIn('floor_minus_door_local_y',b['ground_height_policy'])
 def test_honest_limits(self):self.assertFalse(self.p['source_policy']['whole_house_scaling']);self.assertEqual(self.p['source_policy']['compile_count'],0);self.assertNotIn('unassigned_area_after_ground_program_m2',self.p['coverage'])
if __name__=='__main__':unittest.main()
