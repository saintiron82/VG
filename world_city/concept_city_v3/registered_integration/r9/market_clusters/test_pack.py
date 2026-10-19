"""Independent source-bound invariants, geometry checks, and adversarial controls."""
import collections,copy,json,math,unittest
from .author import *
from .route_links import path_clear,support_route
from world_city.concept_city_v3.registered_integration.r9.port_market.author import Reservations,CERTIFIED,CATALOG,BASE,MARKET

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.ctx=Context();cls.pack=load(HERE/'pack.json');cls.layout=load(HERE/'layout.json');cls.report=load(HERE/'static_clearance_report.json');cls.new=cls.pack['add_instances']
  cls.base_ctx=Context()
  for p in cls.new:cls.ctx.solids.append(dict(id=p['id'],polygon=p['footprint_xz_m'],y_min=p['native_bottom_y_m'],y_max=p['native_top_y_m'],source='candidate'))
  cls.ctx.reindex()
 def test_source_hashes_and_frozen_native_assets(self):
  self.assertEqual(sha(BASE),BASE_SHA)
  for r in self.report['source_refs']:self.assertEqual(sha(ROOT/r['path']),r['sha256'],r['path'])
  frozen=load(HERE.parent/'port_market/market_canopy/pack.json')['common_assets'];self.assertEqual(self.pack['common_assets'],frozen)
  for a in frozen.values():
   for k in ['master','render']:self.assertEqual(sha(ROOT/a[k+'_path']),a[k+'_sha256'])
   self.assertEqual(load(ROOT/a['render_path'])['bounds'],a['bounds'])
 def test_remove_add_schema_and_source_ledger(self):
  old={p['id']:p for p in self.ctx.c['old_stalls']};newids={p['id'] for p in self.new}
  self.assertEqual(set(self.pack['remove_instance_ids']),set(old));self.assertEqual(len(old),104);self.assertEqual(len(newids),66);self.assertFalse(newids&set(old));self.assertEqual(self.pack['replace_instances'],[])
  self.assertEqual(len({p['source_original_instance_id'] for p in self.new}),66)
  for p in self.new:
   o=old[p['source_original_instance_id']];self.assertEqual(p['source_original_position_m'],o['position_m']);self.assertEqual(p['source_original_yaw_rad'],o['yaw_rad']);self.assertEqual(p['source_original_asset_key'],o['asset_key']);self.assertNotEqual(p['position_m'],o['position_m'])
   self.assertEqual(self.pack['common_assets'][p['asset_key']]['source_asset_key'],o['asset_key'])
 def test_whole_native_bounds_site_and_support(self):
  for p in self.new:
   b=self.pack['common_assets'][p['asset_key']]['bounds'];self.assertEqual(p['scale'],[1,1,1]);self.assertEqual(ring(b,p),p['footprint_xz_m']);self.assertEqual(p['native_bottom_y_m'],p['position_m'][1]+b['min'][1]);self.assertEqual(p['native_top_y_m'],p['position_m'][1]+b['max'][1]);self.assertTrue(geo.convex_polygon_contains(self.ctx.site,p['footprint_xz_m'],0));self.assertEqual(len(p['support_samples']),9);self.assertIsNotNone(self.ctx.support(p['footprint_xz_m']))
 def test_exact_493_exclusions_rebuilt_independently(self):
  f=next(p for p in load(MARKET)['placements'] if p['id']=='MARKET_FOUNTAIN');res=Reservations({'common_instances':[f]});self.assertEqual(len(load(CERTIFIED)['routes']),493);self.assertEqual(len(load(CATALOG)['routes']),254)
  rows=[r for r in res.rows if r['kind']!='market_customer_2.4m'];idx=geo._SpatialIndex(10)
  for i,r in enumerate(rows):idx.add(i,r['polygon'])
  for p in self.new:
   poly=p['footprint_xz_m'];hits=[rows[i]['id'] for i in idx.candidates(poly) if overlap(poly,rows[i]['polygon'])];self.assertEqual(hits,[],p['id'])
  bad=square(f['position_m'][0],f['position_m'][2],2);self.assertTrue(any(overlap(bad,r['polygon']) for r in rows if r['kind']=='gathering'))
  self.assertTrue(any(overlap(square(98.41505784216918,48.75638652919374,2),r['polygon']) for r in rows if r['kind']=='certified_493_exact'))
 def test_no_new_existing_or_crosspack_overlap(self):
  for p in self.new:self.assertEqual(self.base_ctx.blocked(p['footprint_xz_m'],3.5,p['native_top_y_m']),[],p['id'])
  for i,p in enumerate(self.new):
   for q in self.new[i+1:]:self.assertFalse(overlap(p['footprint_xz_m'],q['footprint_xz_m']),(p['id'],q['id']))
 def test_all_routes_exact_width_caps_and_ground(self):
  routes=self.layout['routes'];self.assertEqual(len(routes),132);self.assertEqual(collections.Counter(r['route_type'] for r in routes),{'customer':66,'service':66})
  for r in routes:
   self.assertTrue(path_clear(self.ctx,r['path_xz_m'],r['width_m']),r['id']);samples,bad=support_route(self.ctx,r['path_xz_m'],r['width_m']);self.assertFalse(bad,r['id']);self.assertEqual(len(samples),r['support_sample_count']);self.assertEqual(r['points_xyz_m'],[w['position_m'] for w in r['waypoints']]);self.assertEqual(r['points_xyz_m'][-1],r['entrance_target']['position_m']);self.assertEqual(r['runtime_status'],'NOT_REPLAYED')
   road=r['entrance_target']['source_road_id'];self.assertTrue(any(geo.point_in_convex_polygon(r['path_xz_m'][-1],q['polygon'],0) for q in self.ctx.res if q['id']=='ROAD:'+road and q['kind']=='source_public_road'))
  self.assertEqual(len({w['id'] for r in routes for w in r['waypoints']}),sum(len(r['waypoints']) for r in routes))
 def test_retirement_and_seven_functional_courts(self):
  retire=load(HERE/'customer_link_retirement.json');self.assertEqual(retire['retired_customer_link_count'],104);self.assertEqual(retire['certified_493_retirement_count'],0);self.assertEqual({r['stall_id'] for r in retire['retired_links']},set(self.pack['remove_instance_ids']))
  self.assertEqual(len(self.layout['clusters']),7);self.assertEqual({p['asset_key'] for p in self.new},set(self.pack['common_assets']))
  self.assertEqual(collections.Counter(g['trade'] for g in self.layout['clusters']),{'grain':2,'produce':2,'textile':3})
 def test_collision_and_unsupported_ground_negative_controls(self):
  p=self.new[0];x,_,z=p['position_m'];self.assertFalse(path_clear(self.ctx,[[x-1,z],[x+1,z]],2.4));self.assertIsNone(self.ctx.height(500,500));self.assertIsNone(self.ctx.support(square(500,500,3)))
  q=copy.deepcopy(p);q['position_m']=self.new[1]['position_m'];q['yaw_rad']=self.new[1]['yaw_rad'];self.assertTrue(overlap(ring(self.pack['common_assets'][q['asset_key']]['bounds'],q),self.new[1]['footprint_xz_m']))
if __name__=='__main__':unittest.main(verbosity=2)
