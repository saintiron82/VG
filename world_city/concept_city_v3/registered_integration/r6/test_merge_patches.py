import copy,unittest
from . import merge_patches as m
T=[[0,0,0],[0,0,1],[1,0,0]]
class MergeTests(unittest.TestCase):
 def setUp(self):
  self.scene={'surfaces':{'earth':T+[[x+2,y,z] for x,y,z in T]},'boxes':[{'id':'one'}]}
 def patch(self,id,index):
  tri=self.scene['surfaces']['earth'][index*3:index*3+3]
  return dict(id=id,base_scene_sha256=m.BASE_SHA256,status='producer_test_pass',source_surface_hashes={'earth':m.canonical_sha(self.scene['surfaces']['earth'])},surface_edits=[dict(material='earth',triangle_index=index,source_triangle_sha256=m.canonical_sha(tri),replacement_triangles_xyz_m=[])],appended_surfaces={'earth':tri},removed_foundation_proxy_ids=['one'])
 def test_disjoint_indices_merge(self):
  p=m.merge([self.patch('a',0),self.patch('b',1)]);self.assertEqual(len(p['surface_edits']),2);self.assertTrue(m.validate_against_scene(self.scene,p));self.assertEqual(p['removed_foundation_proxy_ids'],['one'])
 def test_input_unchanged(self):
  p=self.patch('a',0);before=copy.deepcopy(p);m.merge([p]);self.assertEqual(p,before)
 def test_duplicate_index_rejected(self):
  with self.assertRaisesRegex(ValueError,'Overlapping source'):m.merge([self.patch('a',0),self.patch('b',0)])
 def test_duplicate_id_rejected(self):
  with self.assertRaisesRegex(ValueError,'Duplicate patch ID'):m.merge([self.patch('a',0),self.patch('a',1)])
 def test_changed_base_rejected(self):
  p=self.patch('a',0);p['base_scene_sha256']='other'
  with self.assertRaisesRegex(ValueError,'another frozen'):m.merge([p])
 def test_changed_surface_rejected(self):
  p=m.merge([self.patch('a',0)]);self.scene['surfaces']['earth'][0]=[9,9,9]
  with self.assertRaisesRegex(ValueError,'Changed source surface'):m.validate_against_scene(self.scene,p)
 def test_changed_triangle_rejected(self):
  p=m.merge([self.patch('a',0)]);p['surface_edits'][0]['source_triangle_sha256']='bad'
  with self.assertRaisesRegex(ValueError,'Changed source triangle'):m.validate_against_scene(self.scene,p)
 def test_bad_triangle_index_rejected(self):
  p=m.merge([self.patch('a',0)]);p['surface_edits'][0]['triangle_index']=99
  with self.assertRaisesRegex(ValueError,'Changed source triangle'):m.validate_against_scene(self.scene,p)
 def test_unknown_proxy_rejected(self):
  p=m.merge([self.patch('a',0)]);p['removed_foundation_proxy_ids']=['other']
  with self.assertRaisesRegex(ValueError,'Unknown foundation'):m.validate_against_scene(self.scene,p)
 def test_nan_rejected(self):
  p=self.patch('a',0);p['appended_surfaces']['earth']=[[float('nan'),0,0]]*3
  with self.assertRaisesRegex(ValueError,'Invalid XYZ'):m.merge([p])
 def test_incomplete_triangle_rejected(self):
  p=self.patch('a',0);p['appended_surfaces']['earth']=T[:2]
  with self.assertRaisesRegex(ValueError,'flat triangle'):m.merge([p])
 def test_rejected_producer_rejected(self):
  p=self.patch('a',0);p['status']='FAILED_GRADE'
  with self.assertRaisesRegex(ValueError,'Rejected patch'):m.merge([p])
if __name__=='__main__':unittest.main(verbosity=2)
