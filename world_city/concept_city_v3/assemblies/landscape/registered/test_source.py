"""Finite landscape source checks; these never claim sampled traversal or visual approval."""
import json,math,unittest
from pathlib import Path
from . import author as q,context as c
from world_city.concept_city_v3.assemblies.property.registered import author as a
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from world_city.concept_city_v3.assemblies.property.registered.r1.author import triangle_grade


def wall_solids(site):
 if not site['wall_height_m']:return []
 g=site['gates'][0];cut=a.geom.road_ribbon(g['inside_point_xz_m'],g['outside_point_xz_m'],g['width_m']);out=[];poly=site['polygon_xz_m']
 for u,v in zip(poly,poly[1:]+poly[:1]):
  direction=a.unit(u,v);n=[-direction[1],direction[0]];wall=[u,v,a.add(v,n,.75),a.add(u,n,.75)]
  out.extend(p for p in a.geom.convex_difference(wall,cut) if a.geom.polygon_area(p)>1e-7)
 return out

def circle(p,r,n=32):return [[p[0]+r/math.cos(math.pi/n)*math.cos(i*math.tau/n),p[1]+r/math.cos(math.pi/n)*math.sin(i*math.tau/n)] for i in range(n)]

class SourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=json.loads((q.OUT/'source_pack.json').read_text());cls.d=c.load();cls.idx=a.geom._SpatialIndex(20);cls.by={}
  for j,e in enumerate(cls.d['exclusions']):cls.idx.add(str(j),e['polygon_xz_m']);cls.by[str(j)]=e
 def hits(self,poly,kinds=None):return [self.by[k] for k in self.idx.candidates(poly) if (kinds is None or self.by[k]['kind'] in kinds) and a.overlap(poly,self.by[k]['polygon_xz_m'])]
 def test_source_hashes_and_counts(self):
  self.assertEqual(self.p['sources'],self.d['sources']);self.assertEqual(len(self.p['sites']),7);self.assertEqual(len(self.p['placements']),301);self.assertEqual(self.p['metrics']['burial_count'],36)
  self.assertFalse(self.p['runtime_ready']);self.assertFalse(self.p['applied_to_scene']);self.assertEqual(self.p['metrics']['finite_land_use_area_m2'],22240)
  self.assertEqual(len({p['id'] for p in self.p['placements']}),301)
 def test_blocks_are_bounded_and_disjoint(self):
  spaces={s['id']:s for s in self.d['plan']['spaces']}
  for i,s in enumerate(self.p['sites']):
   self.assertTrue(a.contained(s['polygon_xz_m'],spaces[s['space']]['polygon_xz_m']),s['id']);self.assertFalse(self.hits(s['polygon_xz_m']),s['id'])
   for o in self.p['sites'][:i]:self.assertFalse(a.overlap(s['polygon_xz_m'],o['polygon_xz_m']),(s['id'],o['id']))
 def test_native_props_full_crown_clearance_and_roots(self):
  for s in self.p['sites']:
   walls=wall_solids(s)
   for i,p in enumerate(s['placements']):
    foot=p['footprint_xz_m'];self.assertEqual(p['scale'],[1,1,1]);self.assertTrue(a.contained(foot,s['polygon_xz_m']));self.assertFalse(self.hits(foot),p['id'])
    for prior in s['placements'][:i]:self.assertFalse(a.overlap(foot,prior['footprint_xz_m']),(p['id'],prior['id']))
    for w in walls:self.assertFalse(a.overlap(foot,w),p['id'])
    for r in s['internal_paths']:
     for poly in r['ribbon_polygons_xz_m']:self.assertFalse(a.overlap(foot,poly),(p['id'],r['id']))
    if p['ground_anchor']['support_kind']=='trunk_root':self.assertLessEqual(a.geom.polygon_area(p['ground_anchor']['support_points_xz_m']),4.00001)
 def test_internal_paths_clear_continuous_boundary(self):
  for s in self.p['sites']:
   walls=wall_solids(s);self.assertEqual(len(s['gates']),1)
   self.assertEqual(s['wall_height_m']==0,s['kind']=='cloister_garden')
   for r in s['internal_paths']:
    for poly in r['ribbon_polygons_xz_m']:
     self.assertTrue(a.contained(poly,s['polygon_xz_m']),(s['id'],r['id']))
     for w in walls:self.assertFalse(a.overlap(poly,w),(s['id'],r['id']))
   g=s['gates'][0];gatewalk=next(r for r in s['internal_paths'] if r['id'].endswith(':gate_walk'));self.assertLess(math.dist(gatewalk['polyline_xz_m'][-1],g['center_xz_m']),1e-7)
 def test_six_native_approach_branches(self):
  spaces={s['id']:s for s in self.d['plan']['spaces']};routes={r['entrance_id']:r for r in self.d['approaches']['routes']}
  obstacles={'public_road_and_half_metre_shoulder','native_landmark_outer_envelope','native_ordinary_outer_envelope','finite_water'}
  for s in self.p['sites']:
   if s['kind']=='public_park':continue
   r=s['external_connection'];self.assertIn('horizontal_branch',r['status']);self.assertEqual(r['width_m'],2.2);target=routes[r['target_native_entrance_id']];domain=spaces['SITE_CLERGY' if s['space']=='SITE_CEMETERY' else s['space']]['polygon_xz_m']
   for poly in r['ribbon_polygons_xz_m']:
    self.assertTrue(a.contained(poly,domain),r['id']);self.assertFalse(self.hits(poly,obstacles),r['id'])
   for point in r['polyline_xz_m'][1:-1]:self.assertFalse(self.hits(circle(point,1.1),obstacles),r['id'])
   end=r['polyline_xz_m'][-1];self.assertLess(min(math.dist(end,a.near(u,v,end)[0]) for u,v in zip(target['polyline_xz_m'],target['polyline_xz_m'][1:])),1e-6)
 def test_finite_floor_ownership_does_not_cover_other_owners(self):
  kinds={'public_road_and_half_metre_shoulder','native_landmark_floor_owner','existing_source_path_reservation','native_door_approach_pending_vertical_repair','native_approach_round_join'}
  for w in self.p['wrappers']:
   for p in w['owned_floor_regions_xz_m']:self.assertFalse(self.hits(p,kinds),(w['id'],self.hits(p,kinds)))
 def test_park_finite_external_profile(self):
  s=next(s for s in self.p['sites'] if s['kind']=='public_park');conn=s['external_connection'];r=conn['external_surface'];self.assertEqual(r['surface_owner'],'REGISTERED_LANDSCAPE:SITE_COMMON')
  self.assertEqual(r['source_clear_width_m'],3);self.assertLessEqual(r['maximum_service_ramp_grade'],.1);self.assertLessEqual(r['maximum_inherited_public_landing_grade'],.12);self.assertLessEqual(r['maximum_cut_fill_m'],.7)
  for t in r['triangulated_top_surface']:self.assertAlmostEqual(triangle_grade(t['vertices_xyz_m']),t['source_grade'],10)
  for poly in r['polygon_regions_xz_m']:self.assertFalse(self.hits(poly,{'native_landmark_outer_envelope','native_ordinary_outer_envelope','finite_water','native_door_approach_pending_vertical_repair','native_approach_round_join'}))
  road=next(r for r in self.d['plan']['roads'] if r['id']==conn['candidate']['road_id']);road_regions=[a.geom.road_ribbon(u,v,road['width_m']) for u,v in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])];self.assertEqual(road['id'],'WEST_MONASTERY_EDGE');self.assertEqual(len(r['public_surface_override_regions']),2)
  self.assertTrue(a.polygon_covered_by_union(conn['candidate']['road_landing_polygon_xz_m'],road_regions,1e-6));self.assertIn('piecewise-linear',r['public_lane_endpoint']['shared_height_policy'])
 def test_seven_new_sources_fixed_budget_and_one_solid(self):
  records=self.p['wrappers']+[r for r in self.p['assets'].values() if r['kind']=='new_common'];self.assertEqual(len(records),7)
  for r in records:
   path=c.ROOT/r['source_path'];self.assertEqual(a.file_sha(path),r['source_sha256']);m=json.loads(path.read_text());self.assertEqual(len(m['components']),1);self.assertEqual(len(m['components'][0]['parts']),1);b=candidate_budget(m);self.assertEqual(b,r['candidate_budget']);self.assertTrue(b['within_candidate_cap']);self.assertEqual(b['candidate_cap'],300000);self.assertEqual(b['output_cap'],100000)
 def test_three_existing_cache_hashes(self):
  records=[r['cached'] for r in self.p['assets'].values() if r['kind']=='verified_native_cache'];self.assertEqual(len(records),3)
  for r in records:
   self.assertEqual(a.file_sha(r.get('compiled_asset_ref',r.get('render_path'))),r['render_sha256']);self.assertEqual(a.file_sha(r['master_path']),r['master_file_sha256'])

if __name__=='__main__':unittest.main()
