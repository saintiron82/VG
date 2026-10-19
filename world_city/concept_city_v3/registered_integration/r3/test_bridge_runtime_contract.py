import hashlib,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
PACK=CITY/'assemblies/waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class BridgeRuntimeContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=load(PACK)
 def test_geometry_evidence_bound(self):
  r=self.p['geometry_audit'];self.assertEqual(sha(ROOT/r['path']),r['sha256']);d=load(ROOT/r['path']);self.assertTrue(d['valid']);self.assertEqual(d['barrier_sample_conflicts'],[]);self.assertEqual(d['closed_road_missing_top_cells'],[])
 def test_route_states_exclusive(self):
  for name,s in self.p['states'].items():
   self.assertFalse(s['road_enabled'] and s['navigation_enabled'])
   if s['road_enabled']:self.assertEqual(name,'ROAD_OPEN');self.assertEqual(s['leaf_angle_degrees'],0)
   if s['navigation_enabled']:self.assertEqual(name,'NAVIGATION_OPEN');self.assertEqual(s['leaf_angle_degrees'],90);self.assertEqual(s['barrier_angle_degrees'],0)
 def test_barriers_close_before_covers_or_lift(self):
  stages=self.p['cycle_stages'];ids=[s['id'] for s in stages]
  self.assertLess(ids.index('CLOSE_BARRIERS'),ids.index('RETRACT_HINGE_COVERS'));self.assertLess(ids.index('RETRACT_HINGE_COVERS'),ids.index('LIFT'))
  self.assertLess(ids.index('LOWER'),ids.index('SEAT_HINGE_COVERS'));self.assertLess(ids.index('SEAT_HINGE_COVERS'),ids.index('OPEN_BARRIERS'))
  for key in ('motion_samples','hinge_cover_samples'):
   for s in self.p[key]:self.assertEqual(s['barrier_angle_degrees'],0)
  for s in self.p['barrier_samples']:self.assertEqual(s['leaf_angle_degrees'],0)
 def test_consistent_movable_ids_and_no_static_duplication(self):
  expected={p['id'] for p in self.p['states']['ROAD_OPEN']['movable_placements']};self.assertEqual(len(expected),12)
  for key in ('motion_samples','barrier_samples','hinge_cover_samples'):
   for s in self.p[key]:self.assertEqual({p['id'] for p in s['movable_placements']},expected)
  self.assertFalse(expected&{p['id'] for p in self.p['placements']})
 def test_full_rig_reused(self):
  self.assertEqual(self.p['summary']['source_and_cache_rig_width_m'],11);self.assertEqual(self.p['summary']['source_rig_air_height_m'],17.5);self.assertTrue(self.p['inspection_vessel']['full_rig_geometry_reused'])
 def test_actual_headless_loaded_open_pose(self):
  d=load(CITY/'evidence/visual_drawbridge_r1/headless_runtime.json');self.assertEqual(d['status'],'runtime_loaded');m=d['bridge_mechanism'];self.assertEqual(m['state'],'NAVIGATION_OPEN');self.assertEqual(m['movable_nodes'],12);self.assertTrue(m['navigation_enabled']);self.assertFalse(m['road_enabled'])
if __name__=='__main__':unittest.main(verbosity=2)
