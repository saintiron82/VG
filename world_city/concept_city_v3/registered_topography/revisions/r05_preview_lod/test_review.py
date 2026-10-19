import unittest,json,math
from . import review as r
class PreviewTests(unittest.TestCase):
 def test_contract_preserves_supports(self):
  c=r.build_contract();self.assertEqual(len(c['ordinary_foundations']),672)
  self.assertEqual(c['source_plan_sha256'],r.prior.old.SOURCE_SHA)
  self.assertIn('preview_lod',c);self.assertIn('references',c)
  self.assertTrue(any('same-level' in s for s in c['activation_requirements']))
 def test_plain_ground_coarsens(self):
  a=r.prior.surface_domains([-512,-480,-504,-472]);b=r.surface_domains([-512,-480,-504,-472])
  self.assertLess(sum(len(v['polygon_xz_m']) for v in b),sum(len(v['polygon_xz_m']) for v in a)/4)
 def test_shared_global_profiles(self):
  for x,z in [(-504,-472),(-120,120),(104,432),(96,32)]:
   for j in range(65):
    p=[x,z+j/8];owner=r.owner_at(*p)
    a=r.surface_height_at(dict(owner,review_tile_bounds_xz_m=[x-8,z,x,z+8]),*p)
    b=r.surface_height_at(dict(owner,review_tile_bounds_xz_m=[x,z,x+8,z+8]),*p)
    self.assertEqual(a,b)
 def test_port_flat_common_owner(self):
  for q in r.COOWN_REGIONS:
   p=[sum(v[k] for v in q['polygon_xz_m'])/len(q['polygon_xz_m']) for k in (0,1)]
   owner=r.owner_at(*p)
   self.assertIn(owner['kind'],('port_common_hole','bridge_hole','water_hole'))
   if owner['kind']=='port_common_hole':self.assertFalse(owner['render_land']);self.assertEqual(r.surface_height_at(owner,*p),2.2)
 def test_bounded_domain_area(self):
  for box in [[104,424,112,432],[112,432,120,440],[-128,120,-120,128]]:
   rs=r.surface_domains(box);self.assertAlmostEqual(sum(r.geo.polygon_area(v['polygon_xz_m']) for v in rs),64,places=5)
if __name__=='__main__':unittest.main()
