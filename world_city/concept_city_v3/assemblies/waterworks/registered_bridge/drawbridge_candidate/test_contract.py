"""Read-only regression checks for the hash-bound lifting-span candidate."""
import unittest,math
from voxel_character.common import core
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_topography import author as terrain
from .author import HERE,ROOT,BASE,load,ref,corners,aabb,plate_transform,state
from .verify_and_resolve import box_hits,merged_row_boxes

class Contract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pack=load(HERE/'resolved_placements.json');cls.candidate=load(HERE/'candidate.json');cls.audit=load(HERE/'geometry_audit.json');cls.runtime=load(HERE/'state_contract.json')
 def test_hashes_and_frozen_inputs(self):
  for key in('candidate','state_contract','geometry_audit','compile_report'):
   q=self.pack[key];self.assertEqual(ref(ROOT/q['path']),q)
  for q in self.candidate['fixed_bridge_inputs'].values():self.assertEqual(ref(ROOT/q['path']),q)
  for a in self.pack['assets'].values():
   for kind in ('master','compiled','render'):
    if kind+'_path' in a:self.assertEqual(ref(ROOT/a[kind+'_path'])['sha256'],a[kind+'_sha256'])
 def test_native_checks_and_floor(self):
  self.assertTrue(self.audit['valid']);self.assertFalse(self.audit['closed_road_missing_top_cells'])
  for r in self.audit['render_face_bijections'].values():self.assertEqual(r['missing_faces']+r['internal_or_duplicate_faces'],0)
 def test_all_transition_states_interlocked(self):
  ids={q['id'] for q in self.runtime['states']['ROAD_OPEN']['movable_placements']}
  for name in('motion_samples','barrier_samples','hinge_cover_samples'):
   for s in self.runtime[name]:
    self.assertEqual({q['id'] for q in s['movable_placements']},ids);self.assertFalse(s['road_enabled']);self.assertFalse(s['navigation_enabled'])
  for s in self.runtime['states'].values():self.assertFalse(s['road_enabled'] and s['navigation_enabled'])
  self.assertTrue(self.runtime['states']['ROAD_OPEN']['road_enabled']);self.assertTrue(self.runtime['states']['NAVIGATION_OPEN']['navigation_enabled'])
 def test_cycle_endpoint_identity(self):
  stages=self.runtime['cycle_stages'];states=self.runtime['states']
  def ends(s):
   if 'pose_state' in s:return states[s['pose_state']],states[s['pose_state']]
   a=self.runtime[s['sample_array']];return a[s['start_angle']],a[s['end_angle']]
  for a,b in zip(stages,stages[1:]+stages[:1]):
   p,q=ends(a)[1],ends(b)[0]
   for x,y in zip(p['movable_placements'],q['movable_placements']):self.assertEqual(x['id'],y['id']);self.assertEqual(x['transform_bridge_local'],y['transform_bridge_local'])
 def test_cover_continuous_clearance_to_seated_leaves(self):
  report=load(HERE/'compile_report.json');cs={q['asset_key']:load(ROOT/q['compiled']['path']) for q in report['reports']};overlay=load(BASE/'continuous_deck_overlay.json');occ=set()
  for q in state(0,0,overlay,0)['movable_placements']:
   if q['id'].startswith('LEAF_'):
    for c in cs[q['asset_key']]['cells']:
     p=core.apply(q['transform_bridge_local'],[(v+.5)*.25 for v in c[:3]]);occ.add(tuple(math.floor(v/.25) for v in p))
  for side in(-1,1):
   for j in range(60):
    for box in merged_row_boxes(cs['sliding_hinge_cover'],.25):
     bb=aabb([core.apply(t,q) for t in(plate_transform(side,j/60),plate_transform(side,(j+1)/60)) for q in corners(box)])
     self.assertFalse(box_hits(bb,occ))
 def test_full_vessel_corridor_in_exact_finite_water(self):
  frame=self.candidate['bridge_to_world'];river=[q['polygon_xz_m'] for q in terrain.finite_water_polygons() if q['surface_id']=='MAIN_RIVER']
  for v in self.audit['navigation']:
   b=v['full_source_cache_swept_envelope_bridge_m'];lo,hi=b['min'],b['max'];p=[[w[0],w[2]] for w in(core.apply(frame,[x,0,z]) for x,z in[(lo[0],lo[2]),(hi[0],lo[2]),(hi[0],hi[2]),(lo[0],hi[2])])];area=geo.polygon_area(p);covered=sum(geo.polygon_area(geo.convex_intersection(p,q)) for q in river)
   self.assertAlmostEqual(area,covered,places=6)
 def test_full_rig_and_real_margin(self):
  v=next(q for q in self.candidate['navigation_vessels'] if 'rigged' in q['asset_key']);b=v['union_source_cache_bounds_local_m'];self.assertEqual(b['min'],[-3.,-1.2,-12]);self.assertEqual(b['max'],[8,17.5,12]);self.assertEqual(v['route_origin_bridge_x_m'],-2.5)
  q=next(q for q in self.audit['navigation'] if 'rigged' in q['asset_key']);self.assertGreaterEqual(q['minimum_actual_leaf_side_margin_m'],.75);self.assertEqual(q['fixed_cell_intersections'],0);self.assertFalse(q['open_movable_intersections']);self.assertFalse(q['open_chain_envelope_intersections'])
 def test_barrier_limit_disclosed(self):
  d=self.candidate['design'];self.assertEqual(d['barrier_closed_center_gap_m'],.5);self.assertIn('0.4m-radius',d['barrier_pedestrian_control_basis']);self.assertEqual(d['barrier_station_minimum_open_cart_and_walk_width_m'],10.5)

if __name__=='__main__':unittest.main(verbosity=2)
