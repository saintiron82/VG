"""Small source/preflight gates. No scene output or compilation."""
import json,unittest,math
from . import author as a

def rect(x0,z0,x1,z1):return[[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def square_scene(y=2.5):
 vs=[v for t in a.fan_upward([[0,y,0],[8,y,0],[8,y,8],[0,y,8]])for v in t]
 return dict(surfaces={'ground':vs,'water':[],'bank':[]})
class TestPreflight(unittest.TestCase):
 def test_exact_flat_coverage(self):
  s=square_scene();p=rect(1,1,7,7);r=a.audit_polygon(a.TriangleIndex(s,[p]),p,2.5)
  self.assertTrue(r['passes_existing_surface']);self.assertAlmostEqual(r['covered_area_m2'],36);self.assertEqual(r['missing_area_m2'],0)
 def test_full_width_catches_edge_height(self):
  s=square_scene();s['surfaces']['ground']=[[x,2.5+.2*x,z]for x,y,z in s['surfaces']['ground']];p=rect(1,1,7,7)
  r=a.audit_polygon(a.TriangleIndex(s,[p]),p,2.5)
  self.assertFalse(r['passes_existing_surface']);self.assertAlmostEqual(r['max_actual_triangle_grade'],.2)
 def test_no_fill_at_native_hole(self):
  s=square_scene();s['surfaces']['ground']=s['surfaces']['ground'][:3];p=rect(1,1,7,7)
  r=a.audit_polygon(a.TriangleIndex(s,[p]),p,2.5);self.assertFalse(r['passes_existing_surface']);self.assertGreater(r['missing_area_m2'],10)
 def test_duplicate_top_rejected(self):
  s=square_scene();s['surfaces']['ground']*=2;p=rect(1,1,7,7)
  r=a.audit_polygon(a.TriangleIndex(s,[p]),p,2.5);self.assertFalse(r['passes_existing_surface']);self.assertAlmostEqual(r['excess_area_m2'],36)
 def test_both_windings_emit_upward(self):
  p=[[0,1,0],[1,1,0],[1,1,1],[0,1,1]]
  for q in(p,p[::-1]):self.assertTrue(all(a.normal_y(t)>0 for t in a.fan_upward(q)))
 def test_downward_source_not_floor(self):
  s=square_scene();s['surfaces']['ground']=[v for j in range(0,6,3)for v in s['surfaces']['ground'][j:j+3][::-1]];p=rect(1,1,7,7)
  self.assertFalse(a.audit_polygon(a.TriangleIndex(s,[p]),p,2.5)['passes_existing_surface'])
 def test_batch_protected_lane(self):
  p=rect(1,1,3,3);b=dict(base_scene_sha256=a.SCENE_SHA256,parcels=[dict(id='A',floor_y_m=2.5,footing_polygons_xz_m=[p],walk_polygons_xz_m=[],court_polygons_xz_m=[])],protected_regions=[dict(id='LANE',kind='public_lane',polygon_xz_m=p)])
  r=a.preflight_batch(square_scene(),b);self.assertEqual(r['parcels'][0]['status'],'REQUIRES_FINITE_REPLAN_OR_RESTORATION')
 def test_stale_batch_rejected(self):
  with self.assertRaises(ValueError):a.preflight_batch(square_scene(),dict(base_scene_sha256='old',parcels=[]))
 def test_exact_scene_and_priority_band_provenance(self):
  scene=a.load_scene();report=json.loads((a.HERE/'terrain_bands.json').read_text());self.assertEqual(report['base_scene_sha256'],a.SCENE_SHA256);self.assertEqual(len(report['blocks']),18)
  rows=report['priority_exact_band_regions'];self.assertGreater(len(rows),100)
  for r in rows[::max(1,len(rows)//100)]:
   t=scene['surfaces'][r['material']][3*r['triangle_index']:3*r['triangle_index']+3];plane=a.common.plane(t)
   self.assertGreater(a.normal_y(t),0)
   self.assertTrue(all(abs(a.common.height(plane,p)-r['floor_y_m'])<=a.BAND_TOLERANCE_M for p in r['polygon_xz_m']))
   self.assertAlmostEqual(a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],[[q[0],q[2]]for q in t])),a.geo.polygon_area(r['polygon_xz_m']),places=6)
if __name__=='__main__':unittest.main()
