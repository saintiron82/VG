"""Lightweight tests only. No Godot, no terrain import or scene generation."""
import json,unittest,hashlib,math,importlib.util,pathlib
H=pathlib.Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('fixture_prepare',H/'prepare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_six_exact_cases(self):
  d=m.read(H/'route_plan.json');self.assertEqual(len(d['routes']),6);self.assertEqual(sum('expected_failure' in r for r in d['routes']),2)
 def test_original_sources_intact(self):
  d=m.read(H/'reuse_manifest.json')
  for p,h in d['original_sources'].items():self.assertEqual(m.sha(m.ROOT/p),h)
 def test_motion_functions_unchanged(self):
  original=(m.CITY/'traversal/Traversal.gd').read_text();new=(H/'Traversal.gd').read_text()
  for name in ['_physics_process','next_route','finish_route','finish_suite']:
   def extract(s):return s.split('func '+name+'(',1)[1].split('\nfunc ',1)[0]
   self.assertEqual(extract(original),extract(new),name)
 def test_loader_byte_identical(self):self.assertEqual(m.sha(H/'RenderData.gd'),m.sha(m.ROOT/'voxel_character/common/preview/RenderData.gd'))
 def test_reverse_preserves_route(self):
  routes=m.read(H/'route_plan.json')['routes']
  for i in [0,2]:self.assertEqual(routes[i]['points'],list(reversed(routes[i+1]['points'])))
 def test_bound_source_inputs(self):
  for r in m.read(H/'route_plan.json')['sources'].values():self.assertEqual(m.sha(r['path']),r['sha256'])
 def test_native_control(self):
  d=m.read(H/'controls/actual_wall.compiled.json');self.assertTrue(d['valid']);cells={tuple(r[:3]) for r in d['cells']};self.assertEqual(len(cells),len(d['cells']));self.assertIn((0,1,0),cells);self.assertNotIn((-5,1,0),cells);self.assertIn((-5,-1,0),cells)
 def test_transform_conventions(self):
  p={'position_m':[2,3,4],'yaw_rad':math.pi/2};q=m.transform([1,0,0],p);self.assertAlmostEqual(q[0],2);self.assertAlmostEqual(q[2],3)
 def test_all_source_stations_retained(self):
  d=m.read(H/'route_plan.json');south=m.read(m.CITY/'registered_topography/road_extensions/south_country_r1/contract.json');self.assertEqual(d['routes'][0]['points'][1:],south['centerline_xyz_m']);self.assertEqual(d['routes'][2]['points'][-1],[7.361826819370155,4,84.84799902241383])
if __name__=='__main__':unittest.main(verbosity=2)
