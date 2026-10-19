import unittest,pathlib,json,hashlib,sys,math,numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
O=pathlib.Path(__file__).resolve().parent;N=O.parent;ROOT=N.parents[4];read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class FinalClosure(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.graph=read(O/'final_graph.json');c.certs=read(O/'accepted_certificate_edges.json');c.rows=read(O/'final_residential_ledger.json');c.report=read(O/'final_access_metrics.json');c.bind=read(O/'accepted_certificate_binding.json')
 def test_no_geometry_or_old_graph_node_change(self):
  old=read(N/'graph_r02/observed_graph.json');self.assertEqual(old['nodes_xyz_m'],self.graph['nodes_xyz_m']);self.assertEqual(old['routes'],self.graph['routes']);self.assertEqual(old['edges'],self.graph['edges'][:len(old['edges'])])
 def test_positive_certificates_only(self):
  self.assertEqual(len(self.certs),13);self.assertEqual(self.bind['new_native_positive_directions'],24);self.assertEqual(self.bind['new_negative_controls'],2)
  for c in self.certs:
   self.assertNotIn('NEGATIVE',c['id']);self.assertEqual(len(c['source_case_results']),2);self.assertTrue(all(x['pass']for x in c['source_case_results'].values()))
 def test_every_actual_endpoint_strict(self):
  for c in self.certs:
   for s in c['endpoint_stations_r02']:self.assertLessEqual(s['horizontal_gap_m'],.00005);self.assertLessEqual(s['height_gap_m'],.02)
 def test_source_bindings(self):
  for r in self.bind['sources']:
   p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p;self.assertEqual(sha(p),r['sha256'])
 def test_exact_remaining_outer_bridge_diagnostics(self):
  unknown=[r for r in self.rows if r['certificate_overlay_distances_m']['market']is None];self.assertEqual(len(unknown),2);self.assertEqual({r['station']['route_ids'][0]for r in unknown},{'CROSSING_EAST_RADIAL_LANE_0','CROSSING_EAST_RADIAL_LANE_2'});self.assertTrue(all(r['station_assignment']=='nearest_declared_public_vector_diagnostic_only'for r in unknown));self.assertTrue(all(not r['door_last_mile_proven']for r in self.rows))
 def test_fair_water_and_gate_populations(self):
  for v in self.report['metrics'].values():self.assertEqual(v['count'],536);self.assertEqual(v['reachable'],534);self.assertEqual(v['unreachable'],2)
  for r in self.rows:
   d=r['certificate_overlay_distances_m']
   if d['market']is None:continue
   self.assertLessEqual(d['three_actual_public_draw_usepoints'],d['actual_market_low_draw']+1e-7);self.assertLessEqual(d['nearest_general_gate'],d['south_gate_only']+1e-7)
 def test_reconstruct_final_matrix_market_distances(self):
  public={i for i,r in enumerate(self.graph['routes'])if r['public_assumption']!='restricted_destination_not_public_through'};source=[e for e in self.graph['edges']if e['kind']=='source_vector'and public.intersection(e['route_indices'])];active={n for e in source for n in[e['u'],e['v']]};allow=source+[e for e in self.graph['edges']if e['kind']=='height_tolerant_intersection'and e['height_gap_m']<=.02 and e['u']in active and e['v']in active]+[e for e in self.graph['edges']if e['kind']=='source_bound_runtime_certificate_path'];adj={}
  for e in allow:
   k=tuple(sorted([e['u'],e['v']]));adj[k]=min(adj.get(k,float('inf')),e['length_m'])
  u=[];v=[];w=[]
  for(a,b),x in adj.items():u.extend([a,b]);v.extend([b,a]);w.extend([x,x])
  G=csr_matrix((w,(u,v)),shape=(len(self.graph['nodes_xyz_m']),)*2);targets=read(N/'observed_market_targets.json');D=[]
  for t in targets:
   st=t['station'];ds=np.asarray(dijkstra(G,directed=False,indices=[n for n,x in st['end_nodes']]));D.append(np.min(ds+np.array([x for n,x in st['end_nodes']])[:,None],axis=0))
  dd=np.min(D,axis=0)
  for r in self.rows:
   got=min(dd[n]+w for n,w in r['station']['end_nodes']);expected=r['certificate_overlay_distances_m']['market']
   if expected is None:self.assertFalse(math.isfinite(got))
   else:self.assertAlmostEqual(got,expected,places=6)
 def test_north_local_parity(self):
  d=read(O/'north_source_parity.json');self.assertEqual(d['status'],'PASS');self.assertEqual(d['retained_exact_floor_triangles'],926);self.assertEqual(len(d['retained_native_instance_ids']),3);self.assertEqual(d['new_or_relocated_native_bounds_entering_crop'],0)
if __name__=='__main__':unittest.main(verbosity=2)
