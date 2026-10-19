"""Fast source/output invariants; does not rerun Godot or edit geometry."""
import json,pathlib,unittest,hashlib,math,collections
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
import numpy as np
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[4]
def read(n):
 with open(O/n) as f:return json.load(f)
class AuditTests(unittest.TestCase):
 def test_census_and_scope(self):
  for prefix in ['', 'observed_']:
   r=read(prefix+'residential_access_ledger.json');self.assertEqual(len(r),536);self.assertEqual(len({x['module_id'] for x in r}),536);self.assertEqual(len({x['instance_id'] for x in r}),378)
   self.assertTrue(all(x['complete_door_route_certified'] is False and x['potable_distance_m'] is None for x in r))
 def test_positive_only_graph(self):
  for prefix in ['', 'observed_']:
   g=read(prefix+'graph.json');ids=[x['id'] for x in g['routes']];self.assertEqual(len(ids),253);self.assertFalse(any(x.startswith('NEGATIVE_') for x in ids));self.assertEqual(len(ids),len(set(ids)))
 def test_sources_bound(self):
  s=read('summary.json')
  for r in s['sources']:
   p=ROOT/r['path']
   with open(p,'rb') as f:self.assertEqual(hashlib.file_digest(f,'sha256').hexdigest(),r['sha256'])
 def test_each_complete_certified_route_remains_connected(self):
  # Certified full goal must never be split by its waypoint elevations or a
  # junction-height policy. Connectivity uses its own source-vector edges only.
  for prefix in ['', 'observed_']:
   g=read(prefix+'graph.json');n=len(g['nodes_xyz_m']);target={i for i,r in enumerate(g['routes']) if r['id'].startswith('GOAL:')}
   for ri in target:
    e=[x for x in g['edges'] if x['kind']=='source_vector' and ri in x['route_indices']];used=sorted({v for x in e for v in (x['u'],x['v'])});m={v:i for i,v in enumerate(used)};G=csr_matrix((np.ones(len(e)),([m[x['u']] for x in e],[m[x['v']] for x in e])),shape=(len(used),len(used)));count,_=connected_components(G,directed=False);self.assertEqual(count,1,g['routes'][ri]['id'])
 def test_observed_mapping_retains_every_source_corner(self):
  maps=read('observed_route_observation_mapping.json');self.assertEqual(len(maps),253)
  for r in maps:
   orig=r['original_points_xyz_m'];actual=r['observed_graph_points_xyz_m'];keys={(round(p[0],6),round(p[2],6)) for p in actual}
   for p in orig:self.assertIn((round(p[0],6),round(p[2],6)),keys)
   self.assertTrue(r['observations']);self.assertFalse(r['is_new_collision_evidence'])
 def test_main_gate_observed_model_is_connected(self):
  a=next(x for x in read('observed_logistics_access_ledger.json') if x['id']=='GATE:GATE_MAIN_BRIDGE_17');self.assertTrue(400<a['pedestrian_network_to_market_m']<500)
 def test_facility_proposals_monotone(self):
  for prefix in ['', 'observed_']:
   r=read(prefix+'facility_location_candidates.json')['selected'];self.assertEqual(len(r),6)
   self.assertTrue(all(a['summary']['unreachable']>=b['summary']['unreachable'] for a,b in zip(r,r[1:])))
 def test_junction_fail_preserved(self):
  r=read('junction_evidence_audit.json');self.assertEqual(r['positive_passed'],23);self.assertEqual(r['negative_controls_passed'],2);self.assertEqual(sum(x['junction_all_requested_directions_pass'] for x in r['groups']),5)
if __name__=='__main__':unittest.main()
