import unittest
from . import finite_boundary_index as f
def own(i,p,y):return dict(id=i,polygon_xz_m=p,plane_y_xz_m=[0,0,y])
def scene():return dict(surfaces={'ground': [[-3.,0.,-3.],[-3.,0.,4.],[4.,0.,4.],[-3.,0.,-3.],[4.,0.,4.],[4.,0.,-3.]],'bank':[[.5,-1.,0.],[.5,2.,0.],[.5,2.,1.]]})
def signature(rows):return sorted(tuple(tuple(round(v,10)for v in p)for p in t)for t in rows)
class Tests(unittest.TestCase):
 def compare(self,owners):
  s=scene();index=f.a.TriangleIndex(s,[r['polygon_xz_m']for r in owners]);old=f.c.interfaces(s,index,owners);new=f.interfaces(s,index,owners)
  self.assertEqual(signature(old['appended_retaining_triangles_xyz_m']),signature(new['appended_retaining_triangles_xyz_m']));self.assertEqual(old['side_surface_edits'],new['side_surface_edits']);self.assertEqual(old['unknown_exterior_segments'],new['unknown_exterior_segments']);return new
 def test_continuous_adjacent(self):
  r=self.compare([own('a',[[0,0],[1,0],[1,1],[0,1]],1),own('b',[[1,0],[2,0],[2,1],[1,1]],1)]);self.assertEqual(r['indexed_execution']['exact_continuous_edge_pairs'],1)
 def test_crosslevel_kept(self):
  r=self.compare([own('a',[[0,0],[1,0],[1,1],[0,1]],1),own('b',[[1,0],[2,0],[2,1],[1,1]],2)]);self.assertEqual(r['indexed_execution']['exact_continuous_edge_pairs'],0)
 def test_subdivided_boundary(self):self.compare([own('a',[[0,0],[1,0],[1,1],[0,1]],1),own('b',[[1,0],[2,0],[2,.5],[1,.5]],1),own('c',[[1,.5],[2,.5],[2,1],[1,1]],1)])
 def test_disjoint(self):self.compare([own('a',[[0,0],[1,0],[1,1],[0,1]],1),own('b',[[2,2],[3,2],[3,3],[2,3]],1)])
 def test_long_subnanometre_owner_preserved_in_queries(self):
  r=self.compare([own('thin',[[0,0],[2,0],[2,5e-10],[0,5e-10]],3)])
  self.assertEqual(r['indexed_execution']['authoritative_owners_removed'],0);self.assertEqual(len(r['indexed_execution']['proved_empty_inward_probe_owners']),1)
if __name__=='__main__':unittest.main()
