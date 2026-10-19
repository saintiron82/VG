import importlib.util
import unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'prepare.py'
spec=importlib.util.spec_from_file_location('prepare',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def volume(b):return __import__('math').prod(b['max'][a]-b['min'][a] for a in range(3))

class SubtractionTests(unittest.TestCase):
 def test_contained_hole(self):
  box={'min':[-9,0,-7],'max':[9,22,7]};hole={'min':[-5,0,-7.5],'max':[5,5,7.5]}
  pieces=module.subtract_box(box,hole)
  self.assertAlmostEqual(sum(map(volume,pieces)),volume(box)-10*5*14)
  self.assertEqual(len(pieces),3)
 def test_outside_no_change(self):
  box={'min':[0,0,0],'max':[1,1,1]}
  self.assertEqual(module.subtract_box(box,{'min':[2,0,0],'max':[3,1,1]}),[box])
 def test_full_removal(self):
  box={'min':[0,0,0],'max':[1,1,1]};self.assertEqual(module.subtract_box(box,box),[])
 def test_multiple_holes_are_disjoint(self):
  box={'min':[-10,0,-10],'max':[10,20,10]}
  holes=[{'min':[-2,0,-10],'max':[2,5,10]},{'min':[-10,0,-2],'max':[10,5,2]}]
  pieces=[box]
  for h in holes:pieces=[p for b in pieces for p in module.subtract_box(b,h)]
  self.assertAlmostEqual(sum(map(volume,pieces)),8000-400-400+80)
 def test_route_deduplicates_only_identical_endpoints(self):
  r=module.route_record('x',[[0,0],[0,0],[1,0],[1,1]],'test',[])
  self.assertEqual(len(r['points']),3);self.assertEqual(r['length_m'],2)
 def test_dock_uses_authored_runtime_access(self):
  dock={'id':'F_PIER_2','accessible_polyline_xz_m':[[-120.287,464.206],[-120,464.206],[-120,503]],'source_footprint_xz_m':[[-123.5,457],[-116.5,503]]}
  points,origin=module.dock_access_points(dock)
  self.assertEqual(points[1],[-120,464.206]);self.assertEqual(points[-1],[-120,502.25])
  self.assertEqual(origin,'authored_accessible_polyline_xz_m')
 def test_dock_access_does_not_accept_unsafe_tail(self):
  with self.assertRaises(ValueError):module.dock_access_points({'id':'bad','accessible_polyline_xz_m':[[0,0],[0,.5]]})
if __name__=='__main__':unittest.main()
