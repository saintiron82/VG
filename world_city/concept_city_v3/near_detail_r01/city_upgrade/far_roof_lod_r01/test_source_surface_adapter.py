import sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[4];sys.path.insert(0,str(R))
import source_surface_adapter as a

def box(name,low,high,priority=0,material='a',transform=None):
 return a.solid(dict(id=name,shape=dict(kind='box',min=low,max=high),priority=priority,material=material,transform=transform))
class SurfaceTests(unittest.TestCase):
 def check(self,solids,expected_area=None):
  faces,stats=a.regions(solids);_,quads=a.quads(faces);audit=a.audit_boundary(quads,solids)
  for field in ['interior_surface_area_m2','coincident_surface_overlap_m2']:self.assertLess(audit[field],1e-7)
  for field in ['normal_probe_errors','open_or_nonmanifold_edge_segments','edge_winding_errors']:self.assertEqual(audit[field],0,audit)
  if expected_area is not None:self.assertAlmostEqual(stats['boundary_area_m2'],expected_area)
  return faces
 def test_cube(self):self.check([box('one',[0,0,0],[1,1,1])],6.)
 def test_adjacent(self):self.check([box('one',[0,0,0],[1,1,1]),box('two',[1,0,0],[2,1,1],1)],10.)
 def test_overlapping(self):self.check([box('one',[0,0,0],[1,1,1]),box('two',[.5,.25,.25],[1.5,1.25,1.25],1)],9.375)
 def test_duplicate_paint(self):
  f=self.check([box('one',[0,0,0],[1,1,1]),box('two',[0,0,0],[1,1,1],1,'b')],6.)
  self.assertEqual(set(x['material']for x in f),{'b'})
 def test_rigid_transform(self):self.check([box('one',[0,0,0],[1,1,1],transform={'basis':[[0,0,-1],[0,1,0],[1,0,0]],'translation':[4,7,3]})],6.)
 def test_shared_sloped_ridge(self):
  records=[dict(id='left',priority=0,material='a',shape={'kind':'extrusion','polygon':[[-1,0],[0,1],[0,.8],[-1,-.2]],'z_min':0,'z_max':2}),dict(id='right',priority=1,material='a',shape={'kind':'extrusion','polygon':[[0,1],[1,0],[1,-.2],[0,.8]],'z_min':0,'z_max':2})]
  self.check([a.solid(r)for r in records]+[box('ridge',[-.1,.8,0],[.1,1,2],2,'b')])
if __name__=='__main__':unittest.main()
