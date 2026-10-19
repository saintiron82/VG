import unittest,math,json,hashlib
from . import author as a,port_tie as t
class OwnershipTests(unittest.TestCase):
 def test_snapshot_and_exclusions(self):
  self.assertEqual(a.sha(a.PROPERTY_PATH),a.PROPERTY_SHA);self.assertEqual(len(a.EXCLUDED),29)
  self.assertNotIn('B_REG_0191',{r['source_mass_id'] for r in a.ordinary_foundation_contracts()})
  self.assertEqual(a.sha(t.HERE/'port_tie_contract.json'),'aaa241309d4c11a86464d57ba409b76d6535eba27965da5f9737cfd9356b7d9d')
 def test_monotone_full_tie(self):
  ys=[]
  for p,q in zip(t.ROAD['polyline_xz_m'],t.ROAD['polyline_xz_m'][1:]):
   for i in range(31):ys.append(t.height_at(*(p[k]+i/30*(q[k]-p[k]) for k in (0,1))))
  self.assertTrue(all(q>=p-1e-10 for p,q in zip(ys,ys[1:])))
  self.assertAlmostEqual(min(ys),2.2)
  for poly in t.qints:
   for p in poly:self.assertAlmostEqual(t.height_at(*p),2.2)
 def test_bridge_full_join_and_anchors(self):
  for poly in t.bints:
   for p,q in zip(poly,poly[1:]+poly[:1]):
    for i in range(9):
     v=[p[k]+i/8*(q[k]-p[k]) for k in (0,1)]
     self.assertAlmostEqual(t.height_at(*v),t.junction_height_at(*v),places=8)
  for p in t.bridge.DATA['fixed_endpoints']:
   self.assertAlmostEqual(t.junction_height_at(*p['world_xz_m']),t.bridge.deck_y(t.bridge.DATA,*p['world_xz_m']),places=10)
 def test_bounded_partitions(self):
  for x,z in [(110,433),(98,30),(-190,-252),(46,-32),(125,450)]:
   bounds=[x-4,z-4,x+4,z+4];rs=a.surface_domains(bounds,False)
   self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in rs),64,places=5)
   for i,r in enumerate(rs):
    self.assertFalse(a.prior.is_excluded(r,a.EXCLUDED))
    for s in rs[i+1:]:self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],s['polygon_xz_m'])),1e-6)
   for r in rs:
    if r['kind']=='water_hole':self.assertFalse(r['render_land'])
 def test_property_masks_actual_faces(self):
  owners=a._owners();faces=[r for r in owners if r['kind']=='property_common_hole']
  self.assertEqual(len(faces),sum(len(m['compiled_upward_faces']) for m in a.PROPERTY['ownership_masks']))
  self.assertTrue(all(not r['render_land'] for r in faces))
 def test_terminal_shared_mesh_edges(self):
  a._owners()
  road=dict(kind='road',owner_id='road',review_tile_bounds_xz_m=[-1000,-1000,1000,1000])
  for r in a.HANDOFFS:
   for p,q in zip(r['polygon_xz_m'],r['polygon_xz_m'][1:]+r['polygon_xz_m'][:1]):
    for f in (0,.3,.7,1):
     v=[p[k]+f*(q[k]-p[k]) for k in (0,1)]
     self.assertAlmostEqual(a.surface_height_at(road,*v),a.point_y(r['triangle_xyz_m'],*v),places=7)
 def test_market_bypass(self):
  road=a.MARKET['access_overlay']['replace_roads'][0]
  self.assertEqual(road['width_m'],7);self.assertEqual(a.road_height_at('MARKET_PROCESSION',100,40),4)
  self.assertFalse(any(r.get('road_id')=='MARKET_PROCESSION' and r['kind'] in ('road','road_shoulder') for r in a._owners()))
if __name__=='__main__':unittest.main()
