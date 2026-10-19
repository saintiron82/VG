import unittest,json
from . import side_clearance as s
P=[[0,0],[4,0],[4,4],[0,4]]
class TestSides(unittest.TestCase):
 def test_vertical_wall_with_zero_plan_area_is_detected(self):
  tri=[[2,2.5,0],[2,3.5,4],[2,2.5,4]]
  self.assertGreater(s.area3d(s.clip_clear_volume(tri,P,[0,0,2.5])),1.9)
 def test_buried_support_is_not_obstruction(self):
  tri=[[2,1,0],[2,2.5,4],[2,1,4]]
  self.assertEqual(s.area3d(s.clip_clear_volume(tri,P,[0,0,2.5])),0)
 def test_overhead_is_not_obstruction(self):
  tri=[[2,5,0],[2,6,4],[2,5,4]]
  self.assertEqual(s.area3d(s.clip_clear_volume(tri,P,[0,0,2.5])),0)
 def test_sloped_floor_changes_envelope(self):
  tri=[[2,2.6,0],[2,2.7,4],[2,2.6,4]]
  self.assertGreater(s.area3d(s.clip_clear_volume(tri,P,[0,0,2.5])),0)
  self.assertEqual(s.area3d(s.clip_clear_volume(tri,P,[.2,0,2.5])),0)
 def test_only_finite_portion_retained(self):
  tri=[[2,2.5,-5],[2,3.5,9],[2,2.5,9]];q=s.clip_clear_volume(tri,P,[0,0,2.5])
  self.assertTrue(q);self.assertTrue(all(0<=v[2]<=4 for v in q));self.assertLess(s.area3d(q),s.area3d(tri))
 def test_missing_floor_rejected(self):
  ix=s.SideIndex({'surfaces':{'bank':[]}},[P])
  with self.assertRaises(ValueError):ix.audit([dict(id='BAD',polygon_xz_m=P)])
 def test_index_reports_exact_source_identity(self):
  tri=[[2,2.5,0],[2,3.5,4],[2,2.5,4]];ix=s.SideIndex({'surfaces':{'bank':tri}},[P]);r=ix.audit([dict(id='WALK',polygon_xz_m=P,floor_y_m=2.5)])
  self.assertEqual(len(r['contacts']),1);self.assertEqual(r['contacts'][0]['triangle_index'],0)
 def test_almost_vertical_road_is_detected_independent_of_plan_area(self):
  tri=[[2,2.5,0],[2+1e-8,3.5,4],[2,2.5,4]]
  self.assertGreater(abs(s.a.normal_y(tri)),1e-10)
  ix=s.SideIndex({'surfaces':{'road':tri}},[P]);r=ix.audit([dict(id='WALK',polygon_xz_m=P,floor_y_m=2.5)])
  self.assertEqual(len(r['contacts']),1)
 def test_sloped_tops_remain_with_the_top_grade_checker(self):
  self.assertFalse(s.physical_side([[0,0,0],[1,.1,0],[1,.1,1]],'road'))
  self.assertFalse(s.physical_side([[0,0,0],[1,.2,0],[1,.2,1]],'road'))
  self.assertTrue(s.physical_side([[0,0,0],[1,.2,0],[1,.2,1]],'bank'))
 def test_actual_failed_north_road_face_is_indexed(self):
  path=s.a.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r03/residual_audit.json'
  data=json.loads(path.read_bytes());row=next(r for r in data['candidates']if r['triangle_index']==1931)
  tri=row['vertices_xyz_m'];xs=[v[0]for v in tri];zs=[v[2]for v in tri]
  box=[[min(xs)-1,min(zs)-1],[max(xs)+1,min(zs)-1],[max(xs)+1,max(zs)+1],[min(xs)-1,max(zs)+1]]
  ix=s.SideIndex({'surfaces':{'road':tri}},[box]);report=ix.audit([dict(id='NORTH_SHARED_JUNCTION',polygon_xz_m=box,floor_y_m=15.6)])
  self.assertEqual(len(report['contacts']),1)
  self.assertGreater(report['contacts'][0]['clear_volume_contact_area_m2'],.04)
  for candidate in data['candidates']:
   self.assertTrue(s.physical_side(candidate['vertices_xyz_m'],candidate['material']),candidate['triangle_index'])
if __name__=='__main__':unittest.main()
