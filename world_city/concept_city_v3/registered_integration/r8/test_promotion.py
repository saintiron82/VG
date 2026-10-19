import unittest,copy
from .promotion import *
T=[[0,0,0],[0,0,1],[1,0,0]];U=[[3,0,0],[3,0,1],[4,0,0]]
class PromotionTests(unittest.TestCase):
 def fixture(self):
  scene={'surfaces':{'land':T}};patch={'base_scene_sha256':'old','source_surface_hashes':{'land':canonical_sha(T)},'surface_edits':[{'material':'land','triangle_index':0,'source_triangle_sha256':canonical_sha(T),'replacement_triangles_xyz_m':[T]}],'appended_surfaces':{}}
  return scene,patch
 def test_index_shift_exact(self):
  old,p=self.fixture();new={'surfaces':{'land':U+T}};out=rebind_unchanged_triangles(p,old,new,'old','new');self.assertEqual(out['surface_edits'][0]['triangle_index'],1);self.assertEqual(out['surface_edits'][0]['replacement_triangles_xyz_m'],[T]);self.assertEqual(p['base_scene_sha256'],'old')
 def test_identical_full_array_proves_duplicate_index(self):
  old,p=self.fixture();old['surfaces']['land']=T+T;p['source_surface_hashes']['land']=canonical_sha(T+T);p['surface_edits'][0]['triangle_index']=1
  out=rebind_unchanged_triangles(p,old,copy.deepcopy(old),'old','new');self.assertEqual(out['surface_edits'][0]['triangle_index'],1)
 def test_reject_changed_geometry(self):
  old,p=self.fixture();new={'surfaces':{'land':U}}
  with self.assertRaises(ValueError):rebind_unchanged_triangles(p,old,new,'old','new')
 def test_reject_reversed_winding(self):
  old,p=self.fixture()
  with self.assertRaises(ValueError):rebind_unchanged_triangles(p,old,{'surfaces':{'land':list(reversed(T))}},'old','new')
 def test_reject_duplicate_exact_match(self):
  old,p=self.fixture()
  with self.assertRaises(ValueError):rebind_unchanged_triangles(p,old,{'surfaces':{'land':T+T}},'old','new')
 def test_reject_bad_source_hash(self):
  old,p=self.fixture();p['source_surface_hashes']['land']='bad'
  with self.assertRaises(ValueError):rebind_unchanged_triangles(p,old,old,'old','new')
 def test_palette_resolve_without_leak(self):
  catalog={k:{'slate':k} for k in SEMANTIC_ROOFS};p={'placements':[{'id':'a','palette_id':'clay_red'},{'id':'b','palette_id':'clay_red'}]};out,r=resolve_palettes(p,catalog);out['placements'][0]['palette_override']['slate']='x';self.assertEqual(out['placements'][1]['palette_override']['slate'],'clay_red');self.assertNotIn('palette_override',p['placements'][0]);self.assertEqual(catalog['clay_red']['slate'],'clay_red')
 def test_palette_mismatch_rejected(self):
  with self.assertRaises(ValueError):resolve_palettes({'placements':[{'id':'a','palette_id':'clay_red','palette_override':{'slate':'wrong'}}]},{'clay_red':{'slate':'right'}})
 def test_ambiguous_existing_catalog_rejected(self):
  rows=[{'palette_id':k,'palette_override':{'slate':k}} for k in SEMANTIC_ROOFS];rows.append({'palette_id':'clay_red','palette_override':{'slate':'wrong'}})
  with self.assertRaises(ValueError):palette_catalog({'common_instances':rows})
if __name__=='__main__':unittest.main()
