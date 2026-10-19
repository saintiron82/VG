"""Positive and negative source guards for the finite north connector."""
import unittest,math,copy
from .author import HERE,ROOT,read,old
from .profile import a
from world_city.concept_city_v3.registered_integration.r7 import surface_guard
from world_city.concept_city_v3.registered_integration.r6 import merge_patches

class Invariants(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=read(HERE/'profile.json');cls.pack=read(HERE/'resolved_placements.json');cls.patch=read(HERE/'surface_patch.json');cls.c=read(HERE/'collision_contract.json');cls.scene=a.load_scene()
 def test_fixed_delta_confined(self):
  src=HERE.parent/'south_approach_r02/cache/registered_south_approach_r02_recessed_fixed.compiled.json';oldc={tuple(r[:3]):r[3:]for r in read(src)['cells']};newc={tuple(r[:3]):r[3:]for r in read(ROOT/self.pack['assets'][0]['compiled']['path'])['cells']};self.assertFalse(newc.keys()-oldc.keys());removed=set(oldc)-set(newc);self.assertTrue(removed)
  for xyz in removed:
   x,y,z=[(v+.5)*.25 for v in xyz];self.assertTrue(-72<=x<=-64 and 1.3<=y<=2.2 and -3.15<=z<=3.15)
  for k in newc:self.assertEqual(newc[k],oldc[k])
 def test_navigation_swept_volume_disjoint(self):
  audit=read(HERE.parent/'drawbridge_candidate/geometry_audit.json');self.assertTrue(audit['valid'])
  for r in audit['navigation']:
   nav=r['full_source_cache_swept_envelope_bridge_m'];self.assertLess(max(q['bounds']['max'][0]for q in self.pack['assets'][1:]),nav['min'][0])
 def test_finite_original_binding(self):self.assertTrue(merge_patches.validate_against_scene(self.scene,self.patch));self.assertEqual(surface_guard.audit_patch(self.patch)['downward'],0)
 def test_collision_is_upward(self):
  self.assertEqual(surface_guard.audit_vertices([v for t in self.c['add_triangles_world_xyz_m']for v in t],'north')['downward'],0);self.assertEqual(self.c['disable_native_mesh_collider_ids'],['BRIDGE_MAIN_RIVER:NORTH_VISIBLE_ROAD'])
 def test_grade_gate_coverage(self):
  self.assertLessEqual(self.p['maximum_grade'],.12);r=read(HERE/'full_cell_audit.json');self.assertEqual(r['status'],'PASS');self.assertEqual(r['physical_profile_uncovered_area_m2'],0);self.assertEqual(r['unsupported_profile_under_native_cover_m2'],0);self.assertFalse(r['gate_cell_conflicts']);self.assertGreaterEqual(r['gate_clear_height_m'],3.1)
 def test_stale_source_rejected(self):
  p=copy.deepcopy(self.patch);p['surface_edits'][0]['source_triangle_sha256']='0'*64
  with self.assertRaises(ValueError):merge_patches.validate_against_scene(self.scene,p)
 def test_downward_surface_rejected(self):
  t=self.c['add_triangles_world_xyz_m'][0]
  with self.assertRaises(ValueError):surface_guard.audit_vertices([t[0],t[2],t[1]],'negative_control')
 def test_water_and_mechanism_unchanged(self):
  s=read(ROOT/'world_city/concept_city_v3/evidence/r8_north_water_r01/scene.json');self.assertEqual(s['bridge_mechanism'],self.scene['bridge_mechanism']);self.assertEqual(s['surfaces']['water'][:len(self.scene['surfaces']['water'])],self.scene['surfaces']['water'])
if __name__=='__main__':unittest.main()
