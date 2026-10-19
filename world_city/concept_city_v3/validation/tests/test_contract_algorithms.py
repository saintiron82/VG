import sys
import unittest
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import geometry as g
from check_hydrology import directed_cycles


class AuditAlgorithmTests(unittest.TestCase):
 def test_concave_parcel_area_is_preserved(self):
  polygon=[[0,0],[4,0],[4,1],[1,1],[1,4],[0,4]]
  self.assertAlmostEqual(sum(g.area(t) for t in g.triangulate(polygon)),7)
  self.assertTrue(g.point_inside([.5,3],polygon))
  self.assertFalse(g.point_inside([3,3],polygon))
  self.assertAlmostEqual(g.intersection_area(polygon,[[2,2],[5,2],[5,5],[2,5]]),0)

 def test_concave_overlap_matches_union(self):
  polygon=[[0,0],[4,0],[4,1],[1,1],[1,4],[0,4]]
  self.assertAlmostEqual(g.intersection_area(polygon,[[.5,.5],[3,.5],[3,3],[.5,3]]),2.25)

 def test_reversed_collinear_polygon(self):
  polygon=[[0,0],[0,2],[2,2],[2,0],[1,0],[0,0]]
  self.assertAlmostEqual(sum(g.area(t) for t in g.triangulate(polygon)),4)

 def test_self_crossing_rejected(self):
  with self.assertRaises(ValueError):g.triangulate([[0,0],[2,2],[0,2],[2,0]])

 def test_cycle_reachable_from_source_is_found(self):
  graph=defaultdict(list,{'source':['a'],'a':['b'],'b':['a']})
  self.assertEqual(directed_cycles(['source','a','b'],graph),[['a','b','a']])

 def test_downhill_acyclic_graph(self):
  graph=defaultdict(list,{'source':['a','b'],'a':['c'],'b':['c']})
  self.assertEqual(directed_cycles(['source','a','b','c'],graph),[])

if __name__=='__main__':unittest.main()
