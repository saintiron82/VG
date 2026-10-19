import unittest
from . import materials as m
class Tests(unittest.TestCase):
 def test_exact_owner_mapping(self):
  for id,material in m.OWNER_MATERIAL.items():self.assertEqual(m.direct_material(dict(owner_id=id,kind='terrace')),material)
 def test_explicit_priority(self):self.assertEqual(m.direct_material(dict(owner_id='CLERGY',kind='terrace',material='grass')),'grass')
 def test_zero_geometry_direct(self):
  r=dict(owner_id='CLERGY',kind='terrace',floor_y_m=14,render_land=True,polygon_xz_m=[[0,0],[4,0],[0,4]])
  q=m.material_pieces(r)[0];self.assertEqual(q['polygon_xz_m'],r['polygon_xz_m']);self.assertEqual(q['floor_y_m'],14)
 def test_exact_partition(self):
  for box in ([224,-112,232,-104],[-280,-136,-272,-128],[500,600,508,608]):
   r=dict(owner_id='BASE_GROUND',kind='ground',render_land=True,polygon_xz_m=m.terrain.R04.old.rect(box));rs=m.material_pieces(r);self.assertAlmostEqual(sum(m.geo.polygon_area(q['polygon_xz_m']) for q in rs),64,places=6);self.assertTrue(all(q['owner_id']==r['owner_id'] for q in rs))
 def test_requested_api(self):
  r=dict(owner_id='CLERGY',kind='terrace',render_land=True)
  p=[[0,0],[2,0],[0,2]];self.assertEqual(m.classify_material_regions(r,p),[dict(polygon_xz_m=p,material='land_D_CLERGY')])
if __name__=='__main__':unittest.main()
