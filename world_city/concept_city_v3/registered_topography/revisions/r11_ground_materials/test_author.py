import unittest,math,json
from . import author as a
class Tests(unittest.TestCase):
 def test_height_aliases(self):
  for n in ('height_at','land_height_at','surface_height_at','source_surface_height_at','road_height_at','path_height_at'):self.assertIs(getattr(a,n),getattr(a.prior,n))
 def test_protected_kinds(self):
  for k in ('road','road_shoulder','door_landing','door_approach','b015_entry','density_entry','water_hole','building_body_hole','b015_native_hole','landmark_public_hole'):self.assertFalse(a.eligible(dict(kind=k,render_land=True)))
 def test_region_policy(self):
  self.assertEqual(len({r['semantic_ground_id'] for r in a.REGIONS}),36);self.assertEqual({r['material'] for r in a.REGIONS},{'earth','grass','stone'})
 def test_bounded_clipping(self):
  results=[]
  for box in ([304,120,312,128],[344,208,352,216],[328,204,336,212],[260,100,268,108]):
   old=a.prior.surface_domains(box,False);new=a.surface_domains(box,False);self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in new),64,places=6)
   for r in new:
    p=r['polygon_xz_m'];q=[sum(x[k] for x in p)/len(p) for k in (0,1)]
    self.assertAlmostEqual(a.source_surface_height_at(r,*q),a.prior.source_surface_height_at(a.prior.owner_at(*q),*q),places=6)
    if r.get('material_change_only'):self.assertTrue(a.eligible(r));results.append(r['material'])
  self.assertTrue(results)
 def test_complete_contract(self):
  c=a.build_contract();self.assertEqual(len(c['water_surfaces']),6);self.assertEqual(len(c['ordinary_foundations']),579);self.assertIn('south_country_road',c);self.assertIn('reservoir_service_interface',c)
if __name__=='__main__':unittest.main()
