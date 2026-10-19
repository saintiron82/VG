import unittest
from .author_backland_materials_r05 import source_retirement_masks,g
SOURCE=[[0.,0.,0.],[0.,0.,2.],[2.,0.,0.]]
SCENE={'surfaces':{'ground_grass':SOURCE}}
def patch(ts):return {'surface_edits':[{'material':'ground_grass','triangle_index':0,'replacement_triangles_xyz_m':ts}]}
class Test(unittest.TestCase):
 def test_unchanged_has_no_retirement(self):
  self.assertEqual(source_retirement_masks(SCENE,patch([SOURCE]))[('ground_grass',0)],[])
 def test_finite_retirement_exact(self):
  r=source_retirement_masks(SCENE,patch([[[0.,0.,0.],[0.,0.,1.],[1.,0.,0.]]]))
  self.assertAlmostEqual(sum(g.geo.polygon_area(p)for p in r[('ground_grass',0)]),1.5)
 def test_new_height_not_misclassified_as_old_retained(self):
  with self.assertRaisesRegex(ValueError,'changed-height'):
   source_retirement_masks(SCENE,patch([[[0.,1.,0.],[0.,1.,1.],[1.,1.,0.]]]))
 def test_vertical_not_treated_as_walking_projection(self):
  scene={'surfaces':{'bank':[[0.,0.,0.],[0.,2.,0.],[0.,0.,2.]]}}
  self.assertEqual(source_retirement_masks(scene,{'surface_edits':[{'material':'bank','triangle_index':0,'replacement_triangles_xyz_m':[]}]}),{})
if __name__=='__main__':unittest.main()
