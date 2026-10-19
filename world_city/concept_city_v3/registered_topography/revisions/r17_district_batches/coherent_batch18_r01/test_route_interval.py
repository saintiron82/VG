import json,unittest,math
from .route_interval import interval
from .screen import HERE
from .. import author as a
from ..audit_retired_boundaries import interval as old_interval
class RouteInterval(unittest.TestCase):
 def test_exact_failed_diagonal_is_covered(self):
  d=json.loads((HERE/'profiles/PRIVATE_GROUP_BLOCK_010_R8_C001.json').read_bytes());u=[147.75,-56.25];v=[140.75,-63.25];rs=[r for r in d['public_fixed_regions']if r['id'].endswith(('6277:8','6278:9'))];old=sorted(old_interval(u,v,r['polygon_xz_m'])for r in rs);new=sorted(interval(u,v,r['polygon_xz_m'])for r in rs);self.assertGreater(old[1][0]-old[0][1],1e-4);self.assertLessEqual(new[1][0]-new[0][1],1e-10)
 def test_true_millimetre_gap_is_retained(self):
  u=[0,0];v=[2,0];a0=[[0,-1],[.9995,-1],[.9995,1],[0,1]];b0=[[1.0005,-1],[2,-1],[2,1],[1.0005,1]];self.assertAlmostEqual((interval(u,v,b0)[0]-interval(u,v,a0)[1])*2,.001,places=12)
 def test_true_parallel_outside_is_rejected(self):
  self.assertIsNone(interval([0,-.001],[1,-.001],[[0,0],[1,0],[1,1],[0,1]]))
 def test_winding_parity(self):
  p=[[0,0],[2,0],[2,2],[0,2]];self.assertEqual(interval([-1,1],[3,1],p),interval([-1,1],[3,1],p[::-1]))
 def test_failed_routes_preserved_and_new_chains_pass(self):
  old=json.loads((HERE/'route_handoff_ready_r02.json').read_bytes());new=json.loads((HERE/'route_handoff_ready_r03.json').read_bytes());self.assertEqual(set(old['failures']),{'BLOCK_010:R8_C001','BLOCK_010:R8_C002'});self.assertEqual(new['failures'],[]);self.assertEqual(len(new['entries']),18);self.assertEqual(len(new['internal_door_routes']),84)
if __name__=='__main__':unittest.main()
