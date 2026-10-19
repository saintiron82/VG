import unittest,json,pathlib,hashlib,sys,collections,numpy as np
from scipy.sparse.csgraph import connected_components
O=pathlib.Path(__file__).resolve().parent;N=O.parent;ROOT=N.parents[4];sys.path.insert(0,str(N/'graph_r02'));from evaluate import CorrectedPublicGraph
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class ClosureTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.old=read(N/'observed_graph.json');c.new=read(N/'graph_r02/observed_graph.json');c.joins=read(N/'graph_r02/registration_ledger.json');c.req=read(O/'request.json');c.report=read(O/'closure_report.json');c.ce=read(O/'certificate_edges.json')
 def test_old_nodes_and_routes_unchanged(self):
  self.assertEqual(self.old['nodes_xyz_m'],self.new['nodes_xyz_m'][:len(self.old['nodes_xyz_m'])]);self.assertEqual(self.old['routes'],self.new['routes'])
 def test_registration_thresholds_and_public_policy(self):
  for j in self.joins:
   self.assertLessEqual(j['horizontal_gap_m'],.00005);self.assertLessEqual(j['height_gap_m'],.02)
   for id in j['source_route_ids']+j['target_route_ids']:self.assertNotEqual(next(r for r in self.new['routes']if r['id']==id)['public_assumption'],'restricted_destination_not_public_through')
 def test_split_lengths_conserved(self):
  groups=collections.defaultdict(list)
  for e in self.new['edges']:
   if 'original_edge_index'in e:groups[e['original_edge_index']].append(e)
  for i,ee in groups.items():self.assertAlmostEqual(sum(e['length_m']for e in ee),self.old['edges'][i]['length_m'],places=8)
 def test_recovery_only19(self):
  d=read(N/'graph_r02/access_metrics.json');self.assertEqual(d['registration_recovered_market_modules'],19);self.assertEqual(d['registration_recovered_water_modules'],19);self.assertEqual(d['metrics']['market']['unreachable'],24);self.assertEqual(d['metrics']['three_actual_public_draw_usepoints']['unreachable'],16)
 def test_classification24_16_no_door_promotion(self):
  rows=read(O/'remaining_station_ledger.json');self.assertEqual(len(rows),24);self.assertEqual(sum(x['water_r02_unknown']for x in rows),16);self.assertTrue(all(not r['house_last_mile_verified']for r in rows));self.assertEqual(sum(r['public_station_assignment']=='nearest_declared_public_vector_diagnostic_only'for r in rows),11)
 def test_outer_lanes_excluded_from_probe_bundle(self):
  self.assertEqual(len(self.req['routes']),12)
  for r in self.req['routes']:self.assertFalse(r['cart_test']);self.assertNotIn(r['group'],['REMAINING_C4','REMAINING_C5'])
 def test_probe_source_refs_and_points(self):
  for r in self.req['producer_sources'].values():self.assertEqual(sha(ROOT/r['path']),r['sha256'])
  authored={r['id']:r for r in read(O/'native_probe_routes.json')['routes']}
  for r in self.req['routes']:
   self.assertEqual(r,authored[r['id']]);self.assertLessEqual(max(np.linalg.norm(np.diff(np.array(r['points']),axis=0),axis=1)),.25000001)
 def test_north_certificate_both_directions_and_strict_endpoint_match(self):
  c=self.ce[0];self.assertEqual(len(c['source_case_results']),2)
  for r in c['source_case_results'].values():self.assertTrue(r['pass']);self.assertEqual(r['ground_ray_miss_frames'],0);self.assertEqual(r['waypoints_reached'],r['waypoints_total'])
  for st in c['endpoint_stations_r02']:self.assertLessEqual(st['horizontal_gap_m'],.00005);self.assertLessEqual(st['height_gap_m'],.02)
 def test_block011_new_native_certificate(self):
  p=N.parent/'interface_runtime/graph_block011_replay_r01/evidence/runtime_r01';a=read(p/'audit.json');r=read(p/'capsule.json');self.assertEqual(a['status'],'PASS');self.assertEqual(r['status'],'pass');self.assertEqual(len([x for x in r['routes']if not x['id'].startswith('NEGATIVE')]),4);self.assertTrue(all(x['pass']for x in r['routes']))
 def test_same_graph_water_baseline(self):
  d=read(O/'certificate_access_metrics.json');self.assertEqual(d['analytic_thresholds'],{'xz_m':.00005,'height_m':.02});self.assertEqual(d['metrics']['market']['unreachable'],21);self.assertEqual(d['metrics']['three_actual_public_draw_usepoints']['unreachable'],13);rows=read(O/'certificate_residential_ledger.json');self.assertEqual(len(rows),536)
if __name__=='__main__':unittest.main(verbosity=2)
