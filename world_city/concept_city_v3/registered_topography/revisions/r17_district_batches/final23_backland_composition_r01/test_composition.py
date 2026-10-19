import json,unittest
from .author import HERE,load
from .. import author as a
class Composition(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.ledger=json.loads((HERE/'ownership_ledger.json').read_bytes());cls.old=load(cls.ledger['source_backland_producer']);cls.new=json.loads((HERE/'backland_producer.json').read_bytes());cls.binding=json.loads((HERE/'activation_binding.json').read_bytes());cls.review=json.loads((HERE/'shared_source_review.json').read_bytes())
 def test_all731_source_rows(self):self.assertTrue(self.review['passed']);self.assertEqual((self.review['shared_rows'],self.review['passing'],len(self.review['errors'])),(731,731,0))
 def test_exact_scope(self):self.assertEqual(len(self.ledger['source_rows']),119);self.assertEqual(len(self.ledger['appended_rows']),294)
 def test_same_cut_and_paint_area(self):self.assertLess(abs(self.ledger['summary']['removed_backland_area_m2']-self.ledger['summary']['source_cut_overlap_m2']),1e-9)
 def test_normalization_bound(self):
  self.assertLess(self.ledger['summary']['normalization_absolute_area_delta_m2'],2e-11)
  self.assertTrue(all(v['distance_to_retained_edge_m']<=1e-9 for r in self.ledger['normalization']for v in r['removed']))
 def test_source_rows_exact(self):
  changed={(r['material'],r['triangle_index']):r for r in self.ledger['source_rows']}
  self.assertEqual(len(self.old['surface_edits']),len(self.new['surface_edits']))
  for old,new in zip(self.old['surface_edits'],self.new['surface_edits']):
   key=old['material'],old['triangle_index']
   if key in changed:self.assertEqual(changed[key]['old_backland_row'],old);self.assertEqual(changed[key]['replacement_backland_row'],new)
   else:self.assertEqual(old,new)
 def test_unaffected_appended_rows_and_order(self):
  grouped={}
  for r in self.ledger['appended_rows']:grouped[r['material'],r['source_appended_triangle_index']]=r
  for m,vs in self.old['appended_surfaces'].items():
   expected=[]
   for i in range(len(vs)//3):
    old=vs[3*i:3*i+3];r=grouped.get((m,i))
    if r:self.assertEqual(a.canonical_sha(old),r['source_triangle_sha256']);self.assertEqual(old,r['source_vertices_xyz_m']);expected.extend(v for t in r['replacement_triangles_xyz_m']for v in t)
    else:expected.extend(old)
   self.assertEqual(expected,self.new['appended_surfaces'][m])
 def test_original_planes(self):
  for r in self.ledger['appended_rows']:
   plane=a.common.plane(r['source_vertices_xyz_m'])
   for t in r['replacement_triangles_xyz_m']:
    self.assertGreater(a.normal_y(t),0)
    for x,y,z in t:self.assertLessEqual(abs(y-a.common.height(plane,[x,z])),1e-8)
 def test_no_new_float32_inversions(self):self.assertFalse(self.ledger['new_float32_inversions'])
 def test_prior_native_and_binding_fields(self):
  old=load(self.ledger['source_main_binding'])
  for k,v in old.items():
   if k!='patches':self.assertEqual(v,self.binding[k])
  for i,r in enumerate(old['patches']):
   if i not in(13,24):self.assertEqual(r,self.binding['patches'][i])
 def test_other_producer_fields(self):
  for k,v in self.old.items():
   if k not in('surface_edits','appended_surfaces'):self.assertEqual(v,self.new[k])
if __name__=='__main__':unittest.main()
