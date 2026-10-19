import copy,unittest
from . import compose_finite_patches as c
from ..r6 import merge_patches as m
S={'surfaces':{'ground':[[0.,0.,0.],[4.,0.,0.],[0.,0.,4.]]},'boxes':[]};HASH='base'
def patch(pid,mask,raise_by=0):
 source=S['surfaces']['ground'];poly=[[p[0],p[2]]for p in source];ret=c.a.subtract([poly],[mask]);ts=[]
 for p in ret:
  for i in range(1,len(p)-1):ts.append([[q[0],0.,q[1]]for q in(p[0],p[i],p[i+1])])
 if raise_by:
  p=c.a.geo.convex_intersection(poly,mask)
  for i in range(1,len(p)-1):ts.append([[q[0],raise_by,q[1]]for q in(p[0],p[i],p[i+1])])
 return dict(id=pid,base_scene_sha256=HASH,source_surface_hashes={'ground':m.canonical_sha(source)},surface_edits=[dict(material='ground',triangle_index=0,source_triangle_sha256=m.canonical_sha(source),replacement_triangles_xyz_m=ts)],appended_surfaces={})
class Test(unittest.TestCase):
 def test_disjoint_shared_source(self):
  p=patch('left',[[0,0],[1,0],[0,1]]);q=patch('right',[[3,0],[4,0],[3,1]]);before=copy.deepcopy([p,q]);r=c.compose(S,[p,q],HASH);self.assertEqual([p,q],before);proof=r['finite_shared_triangle_composition'][0];self.assertAlmostEqual(proof['remaining_original_plane_area'],7.)
 def test_overlap_rejected(self):
  p=patch('a',[[0,0],[2,0],[0,2]]);q=copy.deepcopy(p);q['id']='b'
  with self.assertRaisesRegex(ValueError,'ownership overlap'):c.compose(S,[p,q],HASH)
 def test_new_height_retained(self):
  p=patch('a',[[0,0],[1,0],[0,1]],.25);q=patch('b',[[3,0],[4,0],[3,1]]);r=c.compose(S,[p,q],HASH);self.assertTrue(any(v[1]==.25 for t in r['surface_edits'][0]['replacement_triangles_xyz_m']for v in t))
 def test_changed_source_rejected(self):
  p=patch('a',[[0,0],[1,0],[0,1]]);bad=copy.deepcopy(S);bad['surfaces']['ground'][0][1]=1
  with self.assertRaises(ValueError):c.compose(bad,[p],HASH)
 def test_source_axis_vertical(self):
  n,l,d,project,unproject=c.project_frame([[2,0,0],[2,3,0],[2,0,3]])
  self.assertEqual(unproject(project([2,1,1])),[2.,1,1])
 def test_explicit_same_side_retirement_union(self):
  source=[[0.,0.,0.],[0.,4.,0.],[0.,0.,4.]];scene={'surfaces':{'bank':source},'boxes':[]}
  def row(pid):return dict(id=pid,base_scene_sha256=HASH,source_surface_hashes={'bank':m.canonical_sha(source)},surface_edits=[dict(material='bank',triangle_index=0,source_triangle_sha256=m.canonical_sha(source),replacement_triangles_xyz_m=[])],appended_surfaces={})
  p,q=row('a'),row('b')
  with self.assertRaisesRegex(ValueError,'ownership overlap'):c.compose(scene,[p,q],HASH)
  r=c.compose(scene,[p,q],HASH,physical_side_retirements=True);self.assertEqual(r['surface_edits'][0]['replacement_triangles_xyz_m'],[]);self.assertAlmostEqual(r['finite_shared_triangle_composition'][0]['shared_retired_source_projection_area_m2'],8)
 def test_side_union_does_not_allow_top_priority(self):
  p=patch('a',[[0,0],[2,0],[0,2]]);q=copy.deepcopy(p);q['id']='b'
  with self.assertRaisesRegex(ValueError,'ownership overlap'):c.compose(S,[p,q],HASH,physical_side_retirements=True)
 def test_positive_tiny_replacement_is_not_reversed(self):
  source=S['surfaces']['ground'];row=dict(source_triangle_sha256=m.canonical_sha(source),replacement_triangles_xyz_m=[[[0.,0.,0.],[1e-8,0.,0.],[0.,0.,1e-8]]])
  c.compound_row(S,('ground',0),[('tiny',row)])
 def test_missing_normalization_prerequisite_rejected(self):
  p=patch('a',[[0,0],[1,0],[0,1]]);p['requires_patch_ids']=['retired-before-reclassification']
  with self.assertRaisesRegex(ValueError,'prerequisite'):c.compose(S,[p],HASH)
 def test_changed_normalization_prerequisite_rejected(self):
  p=patch('a',[[0,0],[1,0],[0,1]]);q=patch('b',[[3,0],[4,0],[3,1]]);q['requires_patch_canonical_sha256']={'a':'changed'}
  with self.assertRaisesRegex(ValueError,'Changed finite retirement prerequisite'):c.compose(S,[p,q],HASH)
if __name__=='__main__':unittest.main()
