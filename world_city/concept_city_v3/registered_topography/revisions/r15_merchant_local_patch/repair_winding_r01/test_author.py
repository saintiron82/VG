import copy,json,unittest
from . import author as r

class OrientationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=r.load_scene();cls.patch=json.loads((r.HERE/'scene_patch.json').read_bytes());cls.fixed=r.apply_orientation(cls.scene)
 def test_exact_scope_and_all_upward(self):
  self.assertEqual(len(self.patch['surface_edits']),3406)
  self.assertFalse(any(r.normal_y(v[i:i+3])<-1e-10 for v in self.fixed['surfaces'].values() for i in range(0,len(v),3)))
 def test_all_unaffected_triangles_and_fields_exact(self):
  changed={(x['material'],x['triangle_index']) for x in self.patch['surface_edits']}
  for k,v in self.scene.items():
   if k!='surfaces':self.assertEqual(v,self.fixed[k])
  for m,v in self.scene['surfaces'].items():
   self.assertEqual(len(v),len(self.fixed['surfaces'][m]))
   for i in range(0,len(v),3):
    old=v[i:i+3];new=self.fixed['surfaces'][m][i:i+3]
    if (m,i//3) in changed:self.assertEqual([old[0],old[2],old[1]],new)
    else:self.assertEqual(old,new)
 def test_changed_coordinates_rejected(self):
  p=copy.deepcopy(self.patch);p['surface_edits'][0]['replacement_triangles_xyz_m'][0][0][1]+=.001
  with self.assertRaises(ValueError):r.apply_to_scene(self.scene,p)
 def test_wrong_base_rejected(self):
  p=dict(self.patch,base_scene_sha256='0'*64)
  with self.assertRaises(ValueError):r.apply_to_scene(self.scene,p)
 def test_duplicate_edit_rejected(self):
  p=dict(self.patch,surface_edits=self.patch['surface_edits']+[self.patch['surface_edits'][0]])
  with self.assertRaises(ValueError):r.apply_to_scene(self.scene,p)
 def test_second_application_rejected(self):
  with self.assertRaises(ValueError):r.apply_orientation(self.fixed)
 def test_future_fan_accepts_both_windings(self):
  p=[[0,1,0],[2,1,0],[2,1,3],[0,1,3]]
  for poly in [p,list(reversed(p))]:
   ts=list(r.fan_upward(poly));self.assertEqual(len(ts),2);self.assertTrue(all(r.normal_y(t)>0 for t in ts));self.assertAlmostEqual(sum(r.normal_y(t)/2 for t in ts),6)
 def test_source_record_plane_is_not_recomputed(self):
  old={'vertices_xyz_m':[[0,1,0],[2,1.2,0],[0,1,3]],'polygon_xz_m':[[0,0],[2,0],[0,3]],'plane':[.1,0,1],'owner_id':'test'}
  new=r.normalize_source_records([old])[0]
  self.assertGreater(r.normal_y(new['vertices_xyz_m']),0);self.assertEqual(new['plane'],old['plane']);self.assertEqual(new['owner_id'],old['owner_id']);self.assertLess(r.normal_y(old['vertices_xyz_m']),0)
 def test_parent_derived_scene_exact(self):
  p=r.a.CITY/'evidence/visual_registered_common_r6_winding_r01/scene.json'
  self.assertEqual(self.fixed,json.loads(p.read_bytes()))
if __name__=='__main__':unittest.main()
