import json,hashlib,unittest
from pathlib import Path
from world_city.runtime_city.checks import placement as g
HERE=Path(__file__).parent
class ProposedLandscapeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raw=(HERE/'plan.json').read_bytes();cls.plan=json.loads(cls.raw);cls.p=json.loads((HERE/'proposed_landscape_sites.json').read_text());cls.exclusions={e['id']:e for e in cls.p['exclusion_catalog']}
 def test_frozen_source_unchanged(self):self.assertEqual(hashlib.sha256(self.raw).hexdigest(),self.p['frozen_source_plan_sha256'])
 def test_only_existing_owner_ids(self):
  ids={p['id'] for k in ('grounds','spaces','landscape_patches') for p in self.plan[k]}
  for site in self.p['sites']:self.assertTrue(set(site['source_ground_ids'])<=ids)
 def test_exact_area(self):
  for site in self.p['sites']:
   self.assertAlmostEqual(site['area_m2'],sum(g.polygon_area(p) for p in site['polygons_xz_m']),places=5)
   self.assertAlmostEqual(site['area_m2'],sum(o['area_m2'] for o in site['owned_ground_regions']),places=5)
 def test_source_exclusions_clear(self):
  for site in self.p['sites']:
   self.assertEqual(site['source_checks']['hard_exclusion_conflicts'],[])
   self.assertTrue(set(site['exclusion_ids'])<=set(self.exclusions))
 def test_formal_frames_proven(self):
  for site in self.p['sites']:
   if site['landscape_kind'] in ('monastery_garden','clergy_garden'):
    f=site['coherent_recipe_frame'];self.assertGreaterEqual(f['width_m'],40);self.assertGreaterEqual(f['depth_m'],40)
    self.assertTrue(any(g.convex_polygon_contains(p,f['polygon_xz_m'],1e-6) for p in site['polygons_xz_m']))
 def test_forest_is_outside(self):
  for site in self.p['sites']:
   if site['landscape_kind']=='outside_woodland':
    self.assertFalse(site['productive_ground']);self.assertEqual(site['wall_canopy_standoff_m'],12)
    for p in site['polygons_xz_m']:self.assertLess(g.polygon_area(g.convex_intersection(p,self.p['wall_polygon_xz_m'])),1e-6)
 def test_programs_not_interchangeable(self):
  sites={s['id']:s for s in self.p['sites']};self.assertEqual(sites['LAND_CLERGY_CEMETERY']['landscape_kind'],'cemetery_facility_pending');self.assertTrue(sites['LAND_MONASTERY_SOUTH']['productive_ground']);self.assertEqual(sites['LAND_PUBLIC_COMMON']['maximum_trees'],5)
 def test_no_scene_placement(self):
  self.assertEqual(self.p['totals']['actual_scene_placement_count'],0)
  self.assertTrue(all(not s['scene_placement_authorized'] for s in self.p['sites']))
if __name__=='__main__':unittest.main()
