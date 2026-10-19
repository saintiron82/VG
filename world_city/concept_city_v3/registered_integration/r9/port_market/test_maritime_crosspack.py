import unittest
from .audit_maritime_crosspack import HERE,ROOT,DRAW,load,sha,world_box,overlap,poly_dist
class MaritimeCrossPackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=load(HERE/'maritime_crosspack_report.json')
 def test_source_bindings(self):
  for r in self.report['sources']:self.assertEqual(sha(ROOT/r['path']),r['sha256'])
  self.assertTrue(self.report['actual_base_bridge_frame_matches_source']);self.assertTrue(self.report['actual_base_geometry_pack_and_audit_hashes_match']);self.assertTrue(self.report['frozen_inputs_unchanged'])
 def test_all_reservations_clear(self):
  self.assertEqual(self.report['status'],'PASS');self.assertEqual(self.report['source_reservation_count'],709);self.assertEqual(self.report['cargo_instances_checked'],292);self.assertEqual(self.report['maritime_hits'],[])
  self.assertTrue(all(not r['cargo_intersection_ids']for r in self.report['all_reservation_results']))
 def test_rigged_envelope_is_exact_authoritative_bounds(self):
  r=next(r for r in self.report['full_vessel_reservations']if 'rigged'in r['id']);d=next(r for r in load(DRAW/'geometry_audit.json')['navigation']if 'rigged'in r['asset_key']);self.assertEqual(r['bounds_bridge_local_m'],d['full_source_cache_swept_envelope_bridge_m']);self.assertEqual(r['bounds_bridge_local_m']['min'][0],-5.5);self.assertEqual(r['bounds_bridge_local_m']['max'][2],52)
 def test_canopy_and_retained_ships_clear(self):
  self.assertEqual(self.report['canopy_replacements_checked'],104);self.assertEqual(self.report['canopy_crosscheck']['hits'],[]);self.assertGreater(self.report['canopy_crosscheck']['minimum_horizontal_gap_m'],4);self.assertEqual(len(self.report['retained_base_ships']),4);self.assertTrue(all(not r['cargo_intersection_ids']for r in self.report['retained_base_ships']))
 def test_intruding_cargo_negative_control(self):
  r=next(r for r in self.report['full_vessel_reservations']if 'rigged'in r['id']);x,y,z=self.report['bridge_to_world']['translation'];intruder=[[x-.5,z-.5],[x+.5,z-.5],[x+.5,z+.5],[x-.5,z+.5]];self.assertTrue(overlap(r['world_polygon_xz_m'],intruder));self.assertEqual(poly_dist(r['world_polygon_xz_m'],intruder),0)
 def test_source_sweep_counts(self):
  counts={r['kind']:r['source_volume_count']for r in self.report['reservation_summary']};self.assertEqual(counts['leaf_interval_sweep'],180);self.assertEqual(counts['other_mechanism_sweep'],492);self.assertEqual(counts['barrier_access_wait'],6);self.assertEqual(counts['navigation_hold'],2);self.assertEqual(counts['controller_barrier_sweep'],4)
if __name__=='__main__':unittest.main(verbosity=2)
