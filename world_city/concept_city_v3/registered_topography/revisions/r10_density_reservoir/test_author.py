import unittest,json,math
from . import author as a
class Tests(unittest.TestCase):
 def test_inheritance(self):
  c=a.build_contract();self.assertEqual(len(c['water_surfaces']),6);self.assertEqual(len(a.finite_water_polygons()),80);self.assertEqual(len(c['ordinary_foundations']),579);self.assertEqual(len(c['excluded_source_ids']),124);self.assertIn('training_native_interface',c);self.assertGreaterEqual(c['review_bounds_xz_m'][3],656)
 def test_thresholds(self):
  for d in a.DENSITY['access_proposals']:
   x,y,z=d['actual_door_xyz_m'];self.assertAlmostEqual(a.height_at(x,z),y,places=7)
 def test_native_masks(self):
  rs=[r for r in a.OWNERS if r['kind']=='b015_native_hole'];self.assertEqual(len(rs),59)
  for r in rs:
   p=r['polygon_xz_m'];q=[sum(t[k] for t in p)/len(p) for k in (0,1)];self.assertEqual(a.owner_at(*q)['kind'],'b015_native_hole')
 def test_partitions(self):
  for bounds in ([312,300,320,308],[-34,-334,-26,-326],[132,562,148,570],[300,192,308,200]):
   rs=a.surface_domains(bounds,False);self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in rs),(bounds[2]-bounds[0])*(bounds[3]-bounds[1]),places=5)
   self.assertFalse(any(a.R04.prior.is_excluded(r,a.EXCLUDED) for r in rs))
 def test_south_seam_and_shoulders(self):
  u,v=a.SOUTH['native_shared_edge_xyz_m']
  for i in range(141):
   p=[u[k]+(v[k]-u[k])*i/140 for k in range(3)];self.assertAlmostEqual(a.road_height_at('SOUTH_COUNTRY_ROAD',p[0],p[2]),1.25,places=7)
  for x in (133,143):self.assertEqual(a.owner_at(x,566)['owner_id'],'R10_RESTORED_SOUTH_SHOULDER')
  self.assertEqual(a.owner_at(138,566)['road_id'],'SOUTH_COUNTRY_ROAD')
 def test_repaired_door_round_join(self):
  d=next(r for r in a.DENSITY['access_proposals'] if r['id']=='DENS_B15E_HOUSE_020:ACTUAL_DOOR:1');self.assertEqual(len(d['reserved_connection_polygons_xz_m']),2);self.assertEqual(len(d['reserved_round_join_polygons_xz_m']),1)
  for p in d['reserved_connection_polygons_xz_m']+d['reserved_round_join_polygons_xz_m']:
   self.assertAlmostEqual(sum(a.geo.intersection_area(p,w['polygon_xz_m']) for w in a.finite_water_polygons()),0,places=7)
 def test_future_hook_permissions(self):
  f=dict(owner_id='F',kind='external_flat_surface',priority=1,render_land=True,floor_y_m=0)
  self.assertFalse(a.can_overlay(dict(kind='water_hole'),f));self.assertFalse(a.can_overlay(dict(kind='building_body_hole',render_land=False),f));self.assertFalse(a.can_overlay(dict(kind='road',road_id='R'),f));self.assertTrue(a.can_overlay(dict(kind='road',road_id='R'),dict(f,replaces_road_ids=['R'])))
if __name__=='__main__':unittest.main()
