import importlib.util,json,math,unittest
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('audit',H/'audit_exact_routes.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RouteAuditTests(unittest.TestCase):
 def hits(self,a,z):return m.slab_hits(np.array(a,dtype=float),np.array(z,dtype=float),np.array([0,0,0]),np.array([1,1,1])).tolist()
 def test_crossing_and_parallel_outside(self):self.assertEqual(self.hits([[-1,.5,.5],[-1,2,.5]],[[2,.5,.5],[2,2,.5]]),[0])
 def test_stationary_inside_and_outside(self):self.assertEqual(self.hits([[.5,.5,.5],[2,2,2]],[[.5,.5,.5],[2,2,2]]),[0])
 def test_corner_touch_and_near_miss(self):self.assertEqual(self.hits([[-1,-1,-1],[-1,1.001,-1]],[[0,0,0],[2,1.001,2]]),[0])
 def test_inverse_yaw_transform(self):
  p={'position_m':[2,3,4],'yaw_rad':math.pi/2};world=np.array([m.b.point(p,5,6,7)]);self.assertTrue(np.allclose(m.inv(world,p),[[5,6,7]]))
 def test_report_full_coverage_and_no_candidates(self):
  r=json.loads((H/'exact_route_impact_r01.json').read_text());self.assertEqual(r['status'],'pass');self.assertEqual(r['unresolved_candidates'],[])
  for x in r['coverage'].values():self.assertEqual(x['route_count'],493);self.assertEqual(x['instance_count'],162);self.assertEqual(x['world_aabb_candidate_segment_pairs'],0)
  self.assertEqual(m.b.sha(H/'pack.json'),m.PACK_SHA)
 def test_camera_separate_and_trace_bound(self):
  d=json.loads((H/'camera_addendum_r02.json').read_text());self.assertEqual(d['add_instances'],[]);self.assertEqual(d['common_assets'],{});c=d['inspection_cameras']['r9_cathedral_street_eye'];self.assertEqual(c['source_route'],'ROAD:CATHEDRAL_APPROACH');self.assertTrue(c['source_case_pass']);self.assertEqual(c['eye_height_m'],1.65)
if __name__=='__main__':unittest.main(verbosity=2)
