import unittest,copy
from unittest.mock import patch
from .landuse_dispositions import apply,g
TRI=[[0.,0.,0.],[0.,0.,2.],[2.,0.,0.]]
def scene(material='land_test',y=0):return {'surfaces':{material:[[x,y,z]for x,_,z in TRI],'road':[[4.,0.,0.],[4.,0.,1.],[5.,0.,0.]]}}
def plan(poly=None):return {'regions':[{'id':'margin','same_plane_functional_ground':[{'material':'land_test','proposed_material':'ground_earth','polygon_xz_m':poly or [[0,0],[0,1],[1,0]],'plane_y_xz_m':[0,0,0],'triangle_index':0}]}]}
class Test(unittest.TestCase):
 def test_partition_preserves_height_and_source(self):
  s=scene();before=copy.deepcopy(s);out,r=apply(s,plan());self.assertEqual(s,before);self.assertAlmostEqual(r['reclassified_area_m2'],.5);self.assertEqual(out['surfaces']['road'],s['surfaces']['road']);self.assertAlmostEqual(sum(g.geo.polygon_area([[v[0],v[2]]for v in out['surfaces'][m][i:i+3]])for m in ('land_test','ground_earth')for i in range(0,len(out['surfaces'][m]),3)),2.)
 def test_missing_height_is_not_filled(self):
  with self.assertRaisesRegex(ValueError,'no matching'):apply(scene(y=1),plan())
 def test_current_target_is_preserved(self):
  s=scene('ground_earth');out,r=apply(s,plan());self.assertEqual(out,s);self.assertEqual(r['source_triangle_edits'],0);self.assertAlmostEqual(r['already_target_material_area_m2'],.5)
 def test_reserved_part_is_excluded(self):
  _,r=apply(scene(),plan(),[[[0,0],[0,.5],[.5,0]]]);self.assertAlmostEqual(r['reclassified_area_m2'],.375)
 def test_protected_source_rejected(self):
  p=plan();p['regions'][0]['same_plane_functional_ground'][0]['material']='road'
  with self.assertRaisesRegex(ValueError,'Protected'):apply(scene(),p)
 def test_overlap_rejected(self):
  p=plan();p['regions']*=2
  with self.assertRaisesRegex(ValueError,'Overlapping'):apply(scene(),p)
 def test_ill_conditioned_recolor_keeps_complete_existing_top(self):
  original=g.common.subtract
  def damaged_partition(polys,cuts):
   if cuts and len(polys)==1 and abs(g.geo.polygon_area(polys[0])-2)<1e-9:return []
   return original(polys,cuts)
  s=scene()
  with patch.object(g.common,'subtract',side_effect=damaged_partition):out,r=apply(s,plan())
  self.assertEqual(out,s);self.assertEqual(r['source_triangle_edits'],0);self.assertEqual(r['reclassified_area_m2'],0);self.assertAlmostEqual(r['conservatively_retained_boundary_material_area_m2'],.5)
if __name__=='__main__':unittest.main()
