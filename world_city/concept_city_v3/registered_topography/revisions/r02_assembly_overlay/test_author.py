import math,unittest
from . import author as a
from world_city.runtime_city.checks import placement as g
class OverlayTests(unittest.TestCase):
 def test_frozen_r01(self):a.snapshot_check()
 def test_only_explicit_source_removed(self):
  body=next(p for p in a.previous.ORDINARY['placements'] if p['id']=='B_REG_0191');p=a.previous.centroid(body['actual_body_footprint_xz_m'])
  self.assertEqual(a.previous.owner_at(*p)['owner_id'],'B_REG_0191:BODY')
  self.assertFalse(a.is_excluded(a.owner_at(*p),a.DEFAULT_EXCLUDED_SOURCE_IDS))
  self.assertEqual(a.owner_at(*p,excluded_source_ids=())['owner_id'],'B_REG_0191:BODY')
 def test_partition_no_stale_body_or_door_hole(self):
  body=next(p for p in a.previous.ORDINARY['placements'] if p['id']=='B_REG_0191');p=body['position_m'];x=8*math.floor(p[0]/8);z=8*math.floor(p[2]/8)
  for i in range(-1,2):
   for j in range(-1,2):
    b=[x+8*i,z+8*j,x+8*i+8,z+8*j+8];rs=a.surface_domains(b)
    self.assertAlmostEqual(sum(g.polygon_area(r['polygon_xz_m']) for r in rs),64,places=6)
    self.assertTrue(all(not a.is_excluded(r,a.DEFAULT_EXCLUDED_SOURCE_IDS) for r in rs))
    for edge in a.retaining_interfaces(b,rs):self.assertNotIn('B_REG_0191',edge['left_owner_id']+edge['right_owner_id'])
 def test_foundations_and_ledger(self):
  c=a.build_contract();self.assertEqual(len(c['ordinary_foundations']),672);self.assertEqual(c['exclusion_ledger'][0]['source_mass_id'],'B_REG_0191')
  self.assertFalse(any(p['source_mass_id']=='B_REG_0191' for p in c['ordinary_foundations']))
if __name__=='__main__':unittest.main()
