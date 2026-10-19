import unittest
from . import compose_districts as c
from .. import author as a

def rect(x0,z0,x1,z1):return[[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def scene(poly):
 ts=a.fan_upward([[x,0,z]for x,z in poly]);return dict(surfaces=dict(ground=[v for t in ts for v in t],bank=[]),boxes=[])
def field(id,p,y):return dict(id=id,polygon_xz_m=p,plane_y_xz_m=[0,0,y],material='ground_earth',kind='coherent_holding',action='field')
class Compose(unittest.TestCase):
 def test_upward_and_exact_partition(self):
  sc=scene(rect(-1,-1,2,2));o=[field('COURT',rect(0,0,1,1),1)];patch,report,index=c.build(sc,o,[],[])
  self.assertTrue(all(a.normal_y(v[j:j+3])>0 for v in patch['appended_surfaces'].values()for j in range(0,len(v),3)))
  for r in report['source_partitions']:self.assertAlmostEqual(r['original_area_m2'],r['retained_area_m2']+r['reowned_area_m2'])
 def test_new_public_plane_closes_same_level(self):
  sc=scene(rect(-1,-1,3,2));o=[field('COURT',rect(0,0,1,1),1)];_,_,idx=c.build(sc,o,[],[]);new=[field('PUBLIC_ACCEPTED',rect(1,0,2,1),1)];r=c.interfaces(sc,idx,o,new)
  edge=[s for s in r['boundary_seams']if s['other_owner'][0]=='accepted_adjacent_owner']
  self.assertTrue(edge);self.assertTrue(all(s['maximum_delta_m']==0 for s in edge))
 def test_native_hole_is_not_duplicate_top(self):
  sc=scene(rect(-1,-1,3,3));hole=dict(id='BODY',polygon_xz_m=rect(.25,.25,.75,.75),action='hole',kind='native_footing');o=[hole,field('COURT',rect(0,0,1,1),1)];patch,report,_=c.build(sc,o,[],[])
  area=sum(a.normal_y(v[j:j+3])/2 for v in patch['appended_surfaces'].values()for j in range(0,len(v),3));self.assertAlmostEqual(area,.75)
 def test_unknown_hole_requires_evidence(self):
  sc=scene(rect(-1,-1,.5,2))
  with self.assertRaises(c.UnownedSourceHole)as caught:c.build(sc,[field('COURT',rect(0,0,1,1),1)],[],[])
  self.assertAlmostEqual(caught.exception.record['area_m2'],.5)
if __name__=='__main__':unittest.main()
