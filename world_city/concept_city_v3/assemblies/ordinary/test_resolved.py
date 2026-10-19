"""Read-only contract tests for the cache-only ordinary candidate pack."""
import hashlib,json,math,unittest
from pathlib import Path
from . import resolve_cached as r
HERE=Path(__file__).parent
PACK=HERE/'resolved_placements.json'
FROZEN='b341bdf4547dffd3a8ca8e7c2e4ed5bae8520c36bcfa13e3bea925bd9e89f89a'

def world(local,pose,yaw):
 x,y,z=local;c,s=math.cos(yaw),math.sin(yaw)
 return [pose[0]+x*c+z*s,pose[1]+y,pose[2]-x*s+z*c]
def on_segment(p,a,b,tol=1e-6):
 return abs(math.dist(p,a)+math.dist(p,b)-math.dist(a,b))<tol

class ResolvedCacheTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=json.loads(PACK.read_text());cls.plan=json.loads(r.PLAN.read_text());cls.old=json.loads(r.CACHE.read_text())
  cls.by={p['id']:p for p in cls.d['placements']};cls.masses={b['id']:b for b in cls.plan['buildings']};cls.plots={p['id']:p for p in cls.plan['plots']}
  cls.routes={p['id']:p for p in cls.plan['roads']+cls.plan['paths']}
  cls.links={p['id']:p for p in cls.d['access_proposals']}
 def test_01_frozen_provenance(self):
  self.assertEqual(r.sha(r.PLAN),FROZEN);self.assertEqual(self.d['source_plan_sha256'],FROZEN)
  self.assertEqual(r.sha(r.CACHE),self.d['source_cache_sha256'])
  self.assertEqual(r.sha(r.terrain.__file__),self.d['terrain_author_sha256'])
 def test_02_complete_owned_partition(self):
  resolved=set(self.by);excluded={x['source_mass_id'] for x in self.d['excluded_source_records']};unresolved={x['source_mass_id'] for x in self.d['unresolved']}
  self.assertFalse(resolved & excluded);self.assertFalse(resolved & unresolved);self.assertEqual(resolved|excluded|unresolved,set(self.masses))
  self.assertEqual(len(resolved),1112);self.assertEqual(len(excluded),93)
 def test_03_recipe_landmark_exclusions(self):
  suppressed=set(self.plan['landmark_component_suppressed_building_ids'])
  for p in self.by.values():
   self.assertNotIn(p['id'],suppressed)
   self.assertNotIn(self.plots[p['source_plot_id']]['property_type'],('noble_estate','merchant_court','poor_block'))
   self.assertFalse(self.masses[p['id']].get('replace_by_assembly_key'))
 def test_04_exact_immutable_cache(self):
  for p in self.by.values():
   self.assertEqual(self.d['assets'][p['asset_key']],self.old['assets'][p['asset_key']][p['lod']])
   self.assertEqual(p['scale'],[1,1,1])
  for a in self.d['cache_manifest']:
   for typ in ('master','render'):self.assertEqual(r.sha(r.ROOT/a[typ+'_path']),a[typ+'_sha256'])
  self.assertEqual(self.d['summary']['new_compile_count'],0)
 def test_05_outer_bounds_fit_source(self):
  for p in self.by.values():
   b=self.masses[p['id']];c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad'])
   for x,z in p['actual_outer_footprint_xz_m']:
    dx,dz=x-p['position_m'][0],z-p['position_m'][2];lx,lz=c*dx-s*dz,s*dx+c*dz
    self.assertLessEqual(abs(lx),b['width_m']/2+1e-6);self.assertLessEqual(abs(lz),b['depth_m']/2+1e-6)
   self.assertTrue(r.g.convex_polygon_contains(self.plots[p['source_plot_id']]['polygon_xz_m'],p['actual_outer_footprint_xz_m'],1e-6))
 def test_06_actual_door_transform(self):
  for p in self.by.values():
   meta=self.d['assets'][p['asset_key']]['author_metadata']['entrance'];entries=meta.get('all_positions') or [meta['position']]
   self.assertEqual(len(entries),len(p['actual_entrance_ids']))
   for i,e in enumerate(entries):
    link=self.links[p['actual_entrance_ids'][i]]
    for got,want in zip(link['actual_door_xyz_m'],world(e,p['position_m'],p['yaw_rad'])):self.assertAlmostEqual(got,want,places=7)
    self.assertEqual(link['door_local_m'],e)
 def test_07_bounded_complete_connection(self):
  for l in self.links.values():
   self.assertLessEqual(l['external_length_m'],8);self.assertEqual(l['width_m'],1.8)
   full=l['complete_proposed_connection_xz_m'];self.assertEqual(full[0],l['threshold_lip_xz_m'])
   self.assertEqual(full[1],l['interaction_anchor_xz_m']);self.assertEqual(l['threshold_landing_polyline_xz_m'],full[:2])
   self.assertAlmostEqual(math.dist(*l['threshold_landing_polyline_xz_m']),1,places=6)
   route=self.routes[l['connects_source_path_or_road_id']]['polyline_xz_m'];self.assertTrue(any(on_segment(full[-1],a,b) for a,b in zip(route,route[1:])))
 def test_08_complete_ribbon_clearance(self):
  obstacles=[];index=r.g._SpatialIndex(32)
  for b in self.plan['buildings']:
   index.add(len(obstacles),b['footprint_xz_m']);obstacles.append((b['id'],b['footprint_xz_m']))
  for p in self.plan['plots']:
   index.add(len(obstacles),p['polygon_xz_m']);obstacles.append((p['id'],p['polygon_xz_m']))
  for l in self.links.values():
   own={l['source_mass_id'],l['source_plot_id']};line=l['complete_proposed_connection_xz_m']
   for a,b in zip(line,line[1:]):
    poly=r.g.road_ribbon(a,b,l['width_m'])
    for j in index.candidates(poly):
     identity,other=obstacles[j]
     if identity not in own:self.assertFalse(r.g.positive_area_overlap(poly,other,1e-6),(l['id'],identity))
    self.assertFalse(r.g.positive_area_overlap(poly,self.by[l['source_mass_id']]['actual_body_footprint_xz_m'],1e-6),l['id'])
 def test_09_exact_height_and_explicit_vertical_gate(self):
  for p in self.by.values():
   f=p['foundation_support']
   for x,z,h in f['support_samples_xzy_m']:self.assertAlmostEqual(h,r.terrain.height_at(x,z),places=7)
   self.assertAlmostEqual(p['position_m'][1],f['proposed_base_y_m'],places=7)
  for l in self.links.values():
   self.assertTrue(l['proposal_only']);self.assertIn('requires_',l['vertical_status'])
   for x,h,z in l['exact_H_sampled_profile_xyz_m']:self.assertAlmostEqual(h,r.terrain.height_at(x,z),places=7)
   self.assertAlmostEqual(l['threshold_to_standing_rise_m'],l['actual_door_xyz_m'][1]-l['interaction_anchor_xyz_m'][1],places=7)
 def test_10_protected_designs_and_palettes(self):
  original={p['id']:p for p in self.old['instances']};status=self.d['protected_design_resolution']
  self.assertEqual({q['source_design_id'] for q in status},set(self.old['protected_design_records']))
  for q in status:
   if q['status'].startswith('resolved'):
    p=self.by[q['source_mass_id']];o=original[q['source_design_id']]
    self.assertEqual(p['asset_key'],o['asset_key']);self.assertEqual(p['palette_id'],o['palette_id']);self.assertEqual(p['palette_override'],o['palette_override'])
   else:self.assertIn('No scaling',q['constraint'])
  self.assertEqual(sum(q['status'].startswith('resolved') for q in status),3)
 def test_11_summary_arithmetic_and_variation(self):
  s=self.d['summary'];self.assertEqual(s['resolved_placements'],len(self.by));self.assertEqual(s['actual_doors'],len(self.links))
  self.assertEqual(s['selected_unique_cached_assets'],len(self.d['assets']));self.assertEqual(s['selected_unique_quads'],sum(a['quad_count'] for a in self.d['assets'].values()))
  self.assertEqual(s['drawn_instance_quads'],sum(self.d['assets'][p['asset_key']]['quad_count'] for p in self.by.values()))
  self.assertEqual(set(s['era_counts']),{'early','late','rebuilt'});self.assertGreater(len(s['roof_form_counts']),1)
 def test_12_no_scene_or_compile_output(self):
  self.assertFalse(any(p.suffix in ('.tscn','.tres','.glb','.obj') for p in HERE.iterdir()))
  self.assertIn('No Godot scene',self.d['scope']);self.assertIn('unverified open doorway',self.d['scope'])

if __name__=='__main__':unittest.main()
