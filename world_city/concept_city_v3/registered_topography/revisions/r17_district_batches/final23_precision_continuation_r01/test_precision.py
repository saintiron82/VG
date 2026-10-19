import copy,json,unittest,hashlib
from .runtime_winding import HERE,contract,bind_scene,apply_runtime,normal,f32,canonical_sha
from .. import author as a
class Precision(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.c=contract();cls.patch=json.loads((HERE/'top_scene_patch.json').read_bytes());cls.ledger=json.loads((HERE/'source_retriangulation_ledger.json').read_bytes())
 def fixture(self):
  scene={'surfaces':{},'unchanged':{'native':'precise'}}
  for r in self.c['cases']+self.c['retained_nonzero_vertical_faces']:scene['surfaces'].setdefault(r['material'],[]).extend(copy.deepcopy(r['precise_source_vertices_xyz_m']))
  return scene
 def test_ten_named_rows(self):self.assertEqual(len(self.c['cases']),10);self.assertEqual(len({r['id']for r in self.c['cases']}),10)
 def test_exact_source_producer_rows(self):
  for r in self.c['cases']:
   k=r['producer_row']
   if k['kind']=='appended':vs=self.patch['appended_surfaces'][k['material']];t=vs[k['appended_triangle_index']*3:k['appended_triangle_index']*3+3]
   else:t=next(e for e in self.patch['surface_edits']if(e['material'],e['triangle_index'])==(k['material'],k['source_triangle_index']))['replacement_triangles_xyz_m'][k['replacement_triangle_index']]
   self.assertEqual(t,r['precise_source_vertices_xyz_m']);self.assertEqual(canonical_sha(t),r['source_triangle_sha256'])
 def test_runtime_vertex_sets(self):
  for r in self.c['cases']:
   before=r['runtime_before_vertices_xyz_m'];after=r['runtime_after_vertices_xyz_m'];self.assertEqual(sorted(map(tuple,before)),sorted(map(tuple,after)));self.assertLess(normal(before)[1],0);self.assertGreater(normal(after)[1],0)
 def test_source_retriangulation_domain(self):
  self.assertEqual(len(self.ledger['operations']),3)
  for r in self.ledger['operations']:
   self.assertLess(abs(r['source_area_m2']-r['replacement_area_m2']),1e-10);self.assertLess(r['missing_source_area_m2'],1e-10);self.assertLess(r['outside_source_area_m2'],1e-10);self.assertLess(max(abs(r['minimum_signed_height_deviation_m']),abs(r['maximum_signed_height_deviation_m'])),1e-8);self.assertLess(r['maximum_grade'],.12000001)
 def test_source_winding(self):
  for r in self.ledger['operations']:
   for t in r['replacement_triangles_xyz_m']:self.assertGreater(normal(t)[1],0);self.assertGreater(normal([[f32(v)for v in x]for x in t])[1],0)
 def test_precise_input_unchanged(self):
  s=self.fixture();before=copy.deepcopy(s);binding=bind_scene(s);out=apply_runtime(s,binding);self.assertEqual(s,before);self.assertEqual(out['unchanged'],s['unchanged']);self.assertEqual(len(binding['rows']),10)
 def test_seven_nonzero_verticals_retained(self):
  self.assertEqual(len(self.c['retained_nonzero_vertical_faces']),7);s=self.fixture();out=apply_runtime(s,bind_scene(s))
  for r in self.c['retained_nonzero_vertical_faces']:
   self.assertTrue(any(normal(r['runtime_before_vertices_xyz_m'])));self.assertEqual(normal(r['runtime_before_vertices_xyz_m'])[1],0);vs=out['surfaces'][r['material']];self.assertTrue(any(vs[i:i+3]==r['precise_source_vertices_xyz_m']for i in range(0,len(vs),3)))
 def test_missing_source_rejected(self):
  s=self.fixture();r=self.c['cases'][0];s['surfaces'][r['material']][:3]=[]
  with self.assertRaises(ValueError):bind_scene(s)
 def test_ambiguous_source_rejected(self):
  s=self.fixture();r=self.c['cases'][0];s['surfaces'][r['material']].extend(r['precise_source_vertices_xyz_m'])
  with self.assertRaises(ValueError):bind_scene(s)
 def test_changed_scene_rejected(self):
  s=self.fixture();b=bind_scene(s);s['unchanged']['native']='changed'
  with self.assertRaises(ValueError):apply_runtime(s,b)
 def test_changed_override_rejected(self):
  s=self.fixture();b=bind_scene(s);b['rows'][0]['runtime_after_vertices_xyz_m'][0][0]+=1
  with self.assertRaises(ValueError):apply_runtime(s,b)
 def test_unknown_faces_not_flipped(self):
  s=self.fixture();unknown=[[0.,0.,0.],[1.,0.,0.],[0.,0.,1.]];s['surfaces']['unrecognized']=[v[:]for v in unknown];out=apply_runtime(s,bind_scene(s));self.assertEqual(out['surfaces']['unrecognized'],unknown)
 def test_non_top_fields_preserved(self):
  old=json.loads((a.ROOT/self.c['original_precise_source']['path']).read_bytes())
  self.assertEqual(old['surface_edits'],self.patch['surface_edits']);self.assertEqual(old['removed_foundation_proxy_ids'],self.patch['removed_foundation_proxy_ids'])
  for m,vs in old['appended_surfaces'].items():
   if m!='ground_stone':self.assertEqual(vs,self.patch['appended_surfaces'][m])
if __name__=='__main__':unittest.main()
