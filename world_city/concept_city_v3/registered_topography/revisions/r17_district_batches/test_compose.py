import unittest
from . import author as a,compose

def rect(x,z,w,h):return[[x,z],[x+w,z],[x+w,z+h],[x,z+h]]
def scene():
 vs=[v for t in a.fan_upward([[0,2.5,0],[8,2.5,0],[8,2.5,8],[0,2.5,8]])for v in t]
 return dict(surfaces={'ground':vs,'bank':[],'water':[]},materials={'ground':{},'ground_earth':{}},boxes=[])
class TestCompose(unittest.TestCase):
 def test_native_hole_precedes_material_paint(self):
  owners=[dict(id='HOLE',action='hole',polygon_xz_m=rect(2,2,2,2)),dict(id='YARD',action='paint',material='ground_earth',floor_y_m=2.5,polygon_xz_m=rect(1,1,6,6))]
  p,r=compose.build(scene(),owners);self.assertEqual(len(p['surface_edits']),2);self.assertAlmostEqual(sum(a.normal_y(vs[i:i+3])/2 for vs in p['appended_surfaces'].values()for i in range(0,len(vs),3)),32);self.assertTrue(r['all_emitted_top_normals_positive'])
 def test_paint_preserves_source_plane(self):
  p,r=compose.build(scene(),[dict(id='YARD',action='paint',material='ground_earth',floor_y_m=2.5,polygon_xz_m=rect(1,1,2,2))]);self.assertTrue(all(v[1]==2.5 for vs in p['appended_surfaces'].values()for v in vs))
 def test_mismatched_floor_rejected(self):
  with self.assertRaises(ValueError):compose.build(scene(),[dict(id='BAD',action='paint',material='ground_earth',floor_y_m=3,polygon_xz_m=rect(1,1,2,2))])
 def test_unknown_retired_hole_rejected(self):
  with self.assertRaises(ValueError):compose.build(scene(),[],[dict(id='BAD',source_id='FAKE',polygon_xz_m=rect(1,1,2,2),floor_y_m=2.5,boundary_status='COMPLETE_LEVEL_BODY_BOUNDARY')])
 def test_missing_old_proxy_rejected(self):
  with self.assertRaises(ValueError):compose.build(scene(),[],removed_foundation_proxy_ids=['FAKE'])
 def test_empty_patch_preserves_all_geometry(self):
  p,r=compose.build(scene(),[]);self.assertEqual(p['surface_edits'],[]);self.assertEqual(p['appended_surfaces'],{})
if __name__=='__main__':unittest.main()
