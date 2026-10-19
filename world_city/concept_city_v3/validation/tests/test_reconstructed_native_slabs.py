import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_landmark_access_candidate import slab_rectangles,transform

def mesh(cells):
 cells=set(cells);quads=[]
 for x,y,z in cells:
  for axis in range(3):
   for sign in (-1,1):
    n=[x,y,z];n[axis]+=sign
    if tuple(n) in cells:continue
    others=[i for i in range(3) if i!=axis];p=[x,y,z];p[axis]+=1 if sign>0 else 0
    q=[]
    for a,b in [(0,0),(1,0),(1,1),(0,1)]:
     v=p.copy();v[others[0]]+=a;v[others[1]]+=b;q.append(v)
    u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[1][i] for i in range(3)];normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    if normal[axis]*sign<0:q.reverse()
    quads.append(q)
 return {'groups':[{'quads':quads}]}
def area(polys):return sum((max(p[0] for p in q)-min(p[0] for p in q))*(max(p[1] for p in q)-min(p[1] for p in q)) for q in polys)
def inside(poly,x,z):return min(p[0] for p in poly)<x<max(p[0] for p in poly) and min(p[1] for p in poly)<z<max(p[1] for p in poly)
class TestSlabs(unittest.TestCase):
 def test_single(self):self.assertEqual(area(slab_rectangles(mesh([(0,0,0)]),.1,.9)),1)
 def test_above(self):self.assertEqual(slab_rectangles(mesh([(0,0,0)]),1,2),[])
 def test_below(self):self.assertEqual(slab_rectangles(mesh([(0,0,0)]),-1,0),[])
 def test_door_below_lintel(self):
  m=mesh([(x,y,0) for x in range(3) for y in range(3) if x!=1 or y==2]);p=slab_rectangles(m,.05,1.85);self.assertEqual(area(p),2);self.assertFalse(any(inside(q,1.5,.5) for q in p))
 def test_lintel_inside_slab(self):self.assertEqual(area(slab_rectangles(mesh([(x,2,0) for x in range(3)]),1.9,2.1)),3)
 def test_courtyard(self):
  p=slab_rectangles(mesh([(x,0,z) for x in range(3) for z in range(3) if x!=1 or z!=1]),.1,.9);self.assertEqual(area(p),8);self.assertFalse(any(inside(q,1.5,1.5) for q in p))
 def test_vertical_union_not_sum(self):self.assertEqual(area(slab_rectangles(mesh([(0,0,0),(0,2,0)]),.1,2.9)),1)
 def test_stair_projection(self):self.assertEqual(area(slab_rectangles(mesh([(0,0,0),(1,0,0),(1,1,0)]),1.05,1.85)),1)
 def test_open_face_rejected(self):
  m=mesh([(0,0,0)]);m['groups'][0]['quads'].pop(0)
  with self.assertRaises(ValueError):slab_rectangles(m,.1,.9)
 def test_transform(self):self.assertAlmostEqual(transform([[1,2]],{'position_m':[10,7,20],'yaw_rad':math.pi/2})[0][0],12);self.assertAlmostEqual(transform([[1,2]],{'position_m':[10,7,20],'yaw_rad':math.pi/2})[0][1],19)
 def test_scale_rejected(self):
  with self.assertRaises(ValueError):transform([[1,2]],{'position_m':[0,0,0],'scale':[2,1,1]})
if __name__=='__main__':unittest.main()
