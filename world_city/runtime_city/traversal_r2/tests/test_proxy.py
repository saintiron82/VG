import importlib.util,math,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[2]))
from world_city.runtime_city.topography import author as a
import build_city_proxy as proxy
class ProxyGeometryTests(unittest.TestCase):
 def test_body_void_is_subtracted_not_filled(self):
  outer=a._rect([0,0,10,10]);hole=a._rect([3,3,7,7]);pieces=a._subtract_convex(outer,a._inside_planes(hole))
  self.assertAlmostEqual(sum(abs(a._area(p)) for p in pieces),84.)
  for p in pieces:
   cut=a._intersect(p,a._inside_planes(hole));self.assertFalse(cut and abs(a._area(cut))>1e-7)
 def test_bounded_adjacent_tiles_share_only_boundary(self):
  self.assertFalse(proxy.overlap([0,0,32,32],[32,0,64,32]));self.assertTrue(proxy.overlap([0,0,32,32],[31,0,63,32]))
 def test_godot_upward_fan_winding(self):
  p=[[0,0,0],[1,.12,0],[1,.12,1]]
  cross_y=(p[1][2]-p[0][2])*(p[2][0]-p[0][0])-(p[1][0]-p[0][0])*(p[2][2]-p[0][2])
  self.assertLess(cross_y,0) # clockwise front face as common RenderData triangle order
if __name__=='__main__':unittest.main()
