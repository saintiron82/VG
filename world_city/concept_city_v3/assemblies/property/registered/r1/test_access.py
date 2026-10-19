import copy,json,math,unittest
from . import author as q
from .. import author as a
from .access_search import World
from world_city.concept_city_v3.registered_topography import author as terrain
class AccessTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.overlay=json.loads((q.OUT/'access_overlay.json').read_text());cls.recipes=[json.loads((q.OUT/(i+'.recipe.json')).read_text()) for i in a.IDS];cls.plan=json.loads((a.CITY/'registered_source/plan.json').read_text());cls.world=World(cls.plan,cls.recipes)
 def test_seven_source_bound_unactivated(self):
  self.assertEqual(self.overlay['status'],'source_complete_pending_independent_audit');self.assertEqual(len(self.overlay['records']),7);self.assertEqual(self.overlay['registered_source_sha256'],a.file_sha(a.CITY/'registered_source/plan.json'));self.assertFalse(self.overlay['runtime_ready']);self.assertFalse(self.overlay['applied_to_scene'])
 def test_native_buildings_unchanged(self):
  for r in self.recipes:
   old=json.loads((a.HERE/'generated'/(r['id']+'.recipe.json')).read_text());oldp={p['id']:p for p in old['placements']}
   for p in r['placements']:
    if p['source_provider']=='ordinary_r2':self.assertEqual(p,oldp[p['id']])
 def test_all_doors_and_service_courts_connected(self):
  self.assertEqual(sum(sum('door_id' in p for p in r['entrance_routes']) for r in self.recipes),39)
  for r in self.recipes:
   self.assertTrue(a.validate_recipe(r)['valid']);self.assertEqual(len(r['gates']),1)
   for path in r['entrance_routes']:self.assertEqual(path['polyline_xz_m'][-1],r['gates'][0]['center_xz_m'])
   self.assertTrue(any(p.get('kind')=='service_court_access' and p['width_m']==3 for p in r['entrance_routes']))
  e1=self.recipes[0];self.assertEqual(len(e1['garden_pose_revision_ledger']),7)
  for p in e1['entrance_routes']:
   if 'stable' in p.get('owner_id',''):self.assertEqual(p['width_m'],3.)
 def test_source_domains_clear_other_ownership(self):
  for r in self.recipes:
   for p in r['external_surface']['polygon_regions_xz_m']:
    self.assertTrue(a.contained(p,self.world.boundary));self.assertFalse(self.world.obstacle_hits(p,r['id']))
  for i,r in enumerate(self.recipes):
   for s in self.recipes[:i]:
    self.assertFalse(any(a.overlap(p,z) for p in r['external_surface']['polygon_regions_xz_m'] for z in s['external_surface']['polygon_regions_xz_m']))
 def test_grade_threshold_and_support_limits(self):
  for r in self.recipes:
   s=r['external_surface'];self.assertLessEqual(s['maximum_service_ramp_grade'],.10001);self.assertLessEqual(s['maximum_inherited_public_landing_grade'],.12001);self.assertLessEqual(s['maximum_cut_fill_m'],4.00001);self.assertEqual(s['finished_gate_floor_y_m'],r['plot']['pad_floor_y_m'])
   for t in s['triangulated_top_surface']:
    self.assertAlmostEqual(q.triangle_grade(t['vertices_xyz_m']),t['source_grade'])
    if t['kind']=='level_gate_turning_pocket':self.assertTrue(all(abs(p[1]-s['finished_gate_floor_y_m'])<1e-7 for p in t['vertices_xyz_m']))
 def test_full_road_landing_and_exact_datum_seam(self):
  for r in self.recipes:
   p=r['external_surface']['public_lane_endpoint'];poly=p['same_datum_landing_polygon_xz_m'];roads=[self.world.roads[k]['polygon'] for k in self.world.road_index.candidates(poly)];self.assertTrue(a.polygon_covered_by_union(poly,roads,1e-6))
   for x,y,z in p['seam_xyz_m']:self.assertAlmostEqual(y,terrain.dry_height_at(x,z),places=7)
 def test_ramp_and_turning_pocket_do_not_overlap(self):
  for r in self.recipes:
   c=r['gate_repair'];self.assertFalse(a.overlap(c['owned_ramp_polygon_xz_m'],c['gate_landing_polygon_xz_m']));self.assertFalse(a.overlap(c['owned_ramp_polygon_xz_m'],c['road_landing_polygon_xz_m']))
 def test_common_sources_one_solid_bounded(self):
  for row in self.overlay['records']:
   m=json.loads((q.OUT/row['master_file']).read_text());self.assertEqual(m['schema'],'riverstone.voxel.master.v1');self.assertEqual(len(m['components']),1);self.assertEqual(m['components'][0]['parts'],[{'id':'solid','pivot':[0,0,0]}]);self.assertTrue(row['candidate_budget']['within_candidate_cap']);self.assertLessEqual(row['candidate_budget']['exact_candidate_visits_without_cell_sampling'],300000)
if __name__=='__main__':unittest.main()
