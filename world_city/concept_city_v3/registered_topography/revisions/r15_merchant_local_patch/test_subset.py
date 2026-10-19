"""Bounded accepted-subset regression; no city terrain solve or native compile."""
import json,math,unittest
from pathlib import Path
from . import author as a, subset as s, frozen as f, restore_ground as rg

class SubsetTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.g=json.loads((s.HERE/'ground_and_edges.json').read_bytes());cls.profiles=json.loads((a.HERE/'public_interfaces/accepted_public_profiles.json').read_bytes())['profiles']
  cls.rows=cls.g['triangles']+[dict(r,kind='public_gate') for p in cls.profiles for r in p['triangles']];cls.idx=rg.MeshIndex(cls.rows)
 def test_seven_binding(self):
  self.assertEqual(len(s.IDS),7);self.assertEqual(len(s.RETIRED),22);self.assertEqual({r['property_id'] for r in self.profiles},s.IDS)
 def test_filter_all_native_and_door_records(self):
  p=s.filtered_pack();self.assertEqual(len(p['placements']),14);self.assertEqual(len(p['actual_doors']),46);self.assertEqual(len(p['access_proposals']),46);self.assertEqual(len(p['ownership_masks']),14)
  for k in ('actual_doors','component_placements','courts','access_proposals','placements','native_union_mask_proofs'):
   for r in p[k]:self.assertTrue(any(str(r.get(f,''))==i or str(r.get(f,'')).startswith(i+':') for f in ('id','owner_id','group_id','property_id') for i in s.IDS),(k,r))
  self.assertEqual(len(s.filtered_support()['placements']),0)
 def test_no_double_top_ownership(self):
  largest=0.;total=0.
  for i,r in enumerate(self.rows):
   for j in self.idx.index.candidates(r['polygon_xz_m']):
    if j<=i:continue
    q=a.polygon(a.geo.convex_intersection(r['polygon_xz_m'],self.rows[j]['polygon_xz_m']))
    if q:
     area=a.geo.polygon_area(q);largest=max(largest,area);total+=area
  self.assertLess(largest,1e-7);self.assertLess(total,1e-6)
 def test_native_holes_have_no_new_ground(self):
  area=0.
  for hole in s.HOLES:
   for i in self.idx.index.candidates(hole['polygon_xz_m']):
    p=a.polygon(a.geo.convex_intersection(hole['polygon_xz_m'],self.rows[i]['polygon_xz_m']))
    if p:area+=a.geo.polygon_area(p)
  self.assertLess(area,1e-6)
 def test_water_is_preserved(self):
  area=0.
  for wet in a.base.finite_water_polygons():
   p=wet['polygon_xz_m']
   for i in self.idx.index.candidates(p):
    q=a.polygon(a.geo.convex_intersection(p,self.rows[i]['polygon_xz_m']))
    if q:area+=a.geo.polygon_area(q)
  self.assertLess(area,1e-6)
 def test_profile_actual_triangle_grades(self):
  for p in self.profiles:
   self.assertTrue(p['accepted']);self.assertLessEqual(p['proof']['maximum_frozen_boundary_error_m'],1e-9)
   for r in p['triangles']:self.assertLessEqual(math.hypot(*a.affine_plane(r['vertices_xyz_m'])[:2]),.120000001)
 def test_restored_edges_never_increase_steps(self):
  review=self.g['edge_review'];self.assertFalse(review['issues']);self.assertEqual(review['failed_edges'],0)
  for e in review['edges']:self.assertLessEqual(e['max_step_increase_m'],1e-7);self.assertFalse(e['walkable_crossing'])
 def test_no_missing_retaining_side_owner(self):
  sides=json.loads((s.HERE/'finite_sides.json').read_bytes());self.assertFalse(sides['issues'])
  for r in sides['records']:self.assertFalse(r['walkable_crossing']);self.assertTrue(r['triangles_xyz_m'])
 def test_frozen_helper_is_still_sealed(self):
  self.assertEqual(a.sha(a.HERE/'frozen.py'),'e6bd4122c25f0deab911089e65127107b774626053e17dc5dd2e620b252fbc08')
 def test_partition_expected_area(self):
  expected=sum(a.geo.polygon_area(p) for prop in s.PROPERTIES for mat in prop['materials'] if mat['material']!='native_asset_owned' for p in mat['polygons_xz_m'])+sum(a.geo.polygon_area(r['polygon_xz_m']) for r in s.restoration_domains())
  masks=[r['polygon_xz_m'] for p in self.profiles for r in p['ownership_masks']]
  overlap=sum(a.geo.polygon_area(q) for r in s.restoration_domains() for mask in masks if(q:=a.polygon(a.geo.convex_intersection(r['polygon_xz_m'],mask))))
  expected+=sum(p['mask_area_m2'] for p in self.profiles)-overlap
  actual=sum(a.geo.polygon_area(r['polygon_xz_m']) for r in self.rows)
  self.assertAlmostEqual(actual,expected,6)

if __name__=='__main__':unittest.main(verbosity=2)
