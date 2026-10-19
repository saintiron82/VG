import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import geometry as g
from check_source import route_graph,components
class GeometryTests(unittest.TestCase):
 def test_crossing_segments(self):self.assertEqual(g.segment_hit([0,0],[2,0],[1,-1],[1,1])[0],[1.,0.])
 def test_parallel_overlap_distance(self):self.assertEqual(g.segment_distance([0,0],[3,0],[1,0],[2,0])[0],0)
 def test_disjoint_distance(self):self.assertAlmostEqual(g.segment_distance([0,0],[1,0],[2,1],[2,2])[0],2**.5)
 def test_touching_polygons_are_not_area_conflicts(self):self.assertEqual(g.area(g.convex_intersection([[0,0],[1,0],[1,1],[0,1]],[[1,0],[2,0],[2,1],[1,1]])),0)
 def test_erosion_prevents_too_narrow_route_connection(self):
  lines=[{'id':'a','width_m':1.,'polyline_xz_m':[[0,0],[2,0]]},{'id':'b','width_m':1.,'polyline_xz_m':[[0,.5],[2,.5]]}]
  graph,_=route_graph(lines);self.assertEqual(len(components(graph)),2)
 def test_shared_intersection_is_connected(self):
  lines=[{'id':'a','width_m':2.,'polyline_xz_m':[[0,0],[2,0]]},{'id':'b','width_m':2.,'polyline_xz_m':[[1,-1],[1,1]]}]
  graph,_=route_graph(lines);self.assertEqual(len(components(graph)),1)
if __name__=='__main__':unittest.main()
