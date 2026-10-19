"""Read-only registered cache candidate contract checks."""
import json,math,unittest,hashlib
from pathlib import Path
from . import resolve_cached as r
HERE=Path(__file__).parent
class RegisteredCacheTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=json.loads((HERE/'resolved_placements.json').read_text());cls.plan=json.loads(r.PLAN.read_text());cls.old=json.loads(r.CACHE.read_text());cls.ps={p['id']:p for p in cls.d['placements']};cls.bs={b['id']:b for b in cls.plan['buildings']};cls.plots={p['id']:p for p in cls.plan['plots']};cls.routes={p['id']:p for p in cls.plan['roads']+cls.plan['paths']}
 def test_01_exact_source_binding(self):
  self.assertEqual(r.sha(r.PLAN),self.d['source_plan_sha256']);self.assertEqual(r.sha(r.CACHE),self.d['source_cache_sha256']);self.assertEqual(r.sha(r.terrain.__file__),self.d['terrain_author_sha256'])
 def test_02_old_versions_unchanged(self):
  self.assertEqual(r.sha(HERE.parent/'resolved_placements.json'),'f106752a46df41fbdcf63cd292a4fc4e77f592a7226fc4cf0c82f57c4e5d3e18')
  self.assertEqual(r.sha(r.CITY/'source/plan.json'),'b341bdf4547dffd3a8ca8e7c2e4ed5bae8520c36bcfa13e3bea925bd9e89f89a')
 def test_03_source_partition(self):
  excluded={q['source_mass_id'] for q in self.d['excluded_source_records']};unresolved={q['source_mass_id'] for q in self.d['unresolved']};self.assertEqual(set(self.ps)|excluded|unresolved,set(self.bs));self.assertFalse(set(self.ps)&excluded)
 def test_04_coarse_native_assets_only(self):
  for p in self.ps.values():self.assertEqual(p['scale'],[1,1,1]);self.assertEqual(p['lod'],'coarse');self.assertEqual(self.d['assets'][p['asset_key']],self.old['assets'][p['asset_key']]['coarse'])
  for a in self.d['cache_manifest']:
   for t in ('master','render'):self.assertEqual(r.sha(r.ROOT/a[t+'_path']),a[t+'_sha256'])
 def test_05_nonconvex_boundary_and_actual_fit(self):
  wall=r.Domain([self.plan['boundary_xz_m']])
  for p in self.ps.values():
   self.assertTrue(wall.contains(p['actual_outer_footprint_xz_m']));self.assertTrue(r.Domain([self.bs[p['id']]['footprint_xz_m']]).contains(p['actual_outer_footprint_xz_m']));self.assertTrue(r.Domain([self.plots[p['source_plot_id']]['polygon_xz_m']]).contains(p['actual_outer_footprint_xz_m']))
 def test_06_floor_datum_translation(self):
  for p in self.ps.values():self.assertAlmostEqual(p['position_m'][1]+p['cached_primary_door_local_y_m'],self.bs[p['id']]['pad_floor_y_m'],places=8)
  for l in self.d['access_proposals']:self.assertAlmostEqual(l['actual_door_xyz_m'][1],l['pad_floor_y_m'],places=8);self.assertFalse(l['step_geometry_authored'])
 def test_07_real_anchor_transform(self):
  for l in self.d['access_proposals']:
   p=self.ps[l['source_mass_id']];e=l['door_local_m'];q=r.transform([e[0],e[2]],[p['position_m'][0],p['position_m'][2]],p['yaw_rad']);self.assertLess(math.dist(q,l['actual_door_xz_m']),1e-7);self.assertAlmostEqual(l['actual_door_xyz_m'][1],p['position_m'][1]+e[1],places=8)
 def test_08_complete_bounded_connection(self):
  for l in self.d['access_proposals']:
   line=l['complete_proposed_connection_xz_m'];self.assertEqual(line[0],l['threshold_lip_xz_m']);self.assertEqual(line[1],l['interaction_anchor_xz_m']);self.assertLessEqual(l['external_length_m'],10);self.assertEqual(l['width_m'],1.8)
   target=self.routes[l['connects_source_path_or_road_id']]['polyline_xz_m'];self.assertLess(r.closest(line[-1],target)[0],1e-6);self.assertEqual(len(l['reserved_connection_polygons_xz_m']),len(line)-1)
 def test_09_full_width_clearance(self):
  obs=r.Domain()
  for b in self.plan['buildings']:obs.add(b['footprint_xz_m'],b['id'])
  for p in self.plan['plots']:obs.add(p['polygon_xz_m'],p['id'])
  for w in self.plan['water_reservations']['finite_water_polygons']:obs.add(w['polygon_xz_m'],'water')
  for l in self.d['access_proposals']:
   for poly in l['reserved_connection_polygons_xz_m']:
    self.assertFalse(obs.hits(poly,(l['source_mass_id'],l['source_plot_id'])),l['id']);self.assertFalse(r.g.positive_area_overlap(poly,self.ps[l['source_mass_id']]['actual_body_footprint_xz_m'],1e-6))
 def test_10_support_and_grade_not_hidden(self):
  for p in self.ps.values():
   f=p['foundation_support'];self.assertTrue(f['no_automatic_origin_raise'])
   for x,h,z in f['support_samples_xyz_m']:self.assertAlmostEqual(h,r.terrain.height_at(x,z),places=8)
  for l in self.d['access_proposals']:
   self.assertTrue(l['proposal_only'])
   for x,h,z in l['exact_H_sampled_profile_xyz_m']:self.assertAlmostEqual(h,r.terrain.height_at(x,z),places=8)
 def test_11_protected_palette_provenance(self):
  old={p['id']:p for p in self.old['instances']}
  for p in self.ps.values():
   if p['source_design_id']:
    o=old[p['source_design_id']];self.assertEqual(p['asset_key'],o['asset_key']);self.assertEqual(p['palette_override'],o['palette_override']);self.assertEqual(p['palette_id'],o['palette_id'])
 def test_12_counts_no_compile_no_stairs(self):
  s=self.d['summary'];self.assertEqual(s['resolved_placements'],len(self.ps));self.assertEqual(s['actual_doors'],len(self.d['access_proposals']));self.assertEqual(s['finished_floor_datum_errors'],0);self.assertEqual(s['automatic_stair_count'],0);self.assertEqual(s['new_compile_count'],0);self.assertEqual(s['geometry_scaling_count'],0)
if __name__=='__main__':unittest.main()
