"""Finite source-polygon operations for the temporary spatial review mesh.
Uses the existing placement checker, not a replacement voxel engine/mesher.
Final voxel solids still compile through common coordinate_planes/core.
"""
from world_city.runtime_city.checks import placement as geo
EPS=1e-7

def clean(p):
 out=[]
 for q in p:
  if not out or abs(q[0]-out[-1][0])+abs(q[1]-out[-1][1])>EPS:out.append(q)
 if len(out)>1 and abs(out[0][0]-out[-1][0])+abs(out[0][1]-out[-1][1])<EPS:out.pop()
 return out if len(out)>=3 and geo.polygon_area(out)>EPS else []

class DomainCut:
 def __init__(self,records):
  self.records=records;self.index=geo._SpatialIndex(32)
  for n,r in enumerate(records):self.index.add(n,r['polygon_xz_m'])
 def subtract(self,polygon):
  pieces=[polygon]
  for n in self.index.candidates(polygon):
   clip=self.records[n]['polygon_xz_m'];nextp=[]
   for p in pieces:
    if geo.positive_area_overlap(p,clip,0):nextp.extend(q for s in geo.convex_difference(p,clip) if (q:=clean(s)))
    else:nextp.append(p)
   pieces=nextp
   if not pieces:break
  return pieces

def fan(poly):
 # convex-difference output is convex. Use original vertices so seam positions match.
 return [[poly[0],poly[i],poly[i+1]] for i in range(1,len(poly)-1)]


def prune_collinear_xyz(points,tolerance=1e-9):
 # Heights are evaluated before this optimization. Never simplify XZ first.
 import math
 out=[list(p) for p in points];changed=True
 while changed and len(out)>3:
  changed=False
  for i,b in enumerate(out):
   a=out[i-1];c=out[(i+1)%len(out)];ac=[c[k]-a[k] for k in range(3)];den=sum(v*v for v in ac)
   if den<1e-20:continue
   t=sum((b[k]-a[k])*ac[k] for k in range(3))/den
   if -1e-12<=t<=1+1e-12 and math.dist(b,[a[k]+t*ac[k] for k in range(3)])<=tolerance:
    out.pop(i);changed=True;break
 return out

if __name__=='__main__':
 import unittest
 class Tests(unittest.TestCase):
  def test_thin_channel(self):
   tile=[[0,0],[4,0],[4,4],[0,4]];cut=[[1.5,-2],[2.5,-2],[2.5,8],[1.5,8]]
   pieces=DomainCut([{'polygon_xz_m':cut}]).subtract(tile)
   self.assertAlmostEqual(sum(geo.polygon_area(p) for p in pieces),12)
   self.assertTrue(all(not geo.positive_area_overlap(p,cut,1e-6) for p in pieces))
  def test_complete_water_tile(self):
   p=[[0,0],[4,0],[4,4],[0,4]];self.assertEqual(DomainCut([{'polygon_xz_m':p}]).subtract(p),[])
  def test_join_union_no_double_cut(self):
   p=[[0,0],[4,0],[4,4],[0,4]];a=[[0,0],[3,0],[3,4],[0,4]];b=[[2,0],[4,0],[4,4],[2,4]]
   self.assertEqual(DomainCut([{'polygon_xz_m':a},{'polygon_xz_m':b}]).subtract(p),[])
  def test_convex_fan_area(self):
   p=[[0,0],[4,0],[5,3],[1,4]];self.assertAlmostEqual(sum(geo.polygon_area(t) for t in fan(p)),geo.polygon_area(p))
 unittest.main()
