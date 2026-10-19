"""Independent handoff invariants and strict negative controls; no engine claim."""
import collections,copy,json,math,unittest
from .author import HERE,ROOT,BASE,BASE_SHA,CATALOG,PLAN,PORT,MARKET,WALK,sha,load,ring,overlap,Reservations
from world_city.runtime_city.checks import placement as geo

class PackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pack=load(HERE/'pack.json');cls.report=load(HERE/'static_clearance_report.json');cls.plan=load(HERE/'placement_plan.json');cls.assets=cls.pack['common_assets'];cls.instances=cls.pack['add_instances']
 def test_base_and_source_bindings(self):
  self.assertEqual(sha(BASE),BASE_SHA);self.assertEqual(self.pack['base_scene_sha256'],BASE_SHA)
  for ref in self.report['source_refs']:self.assertEqual(sha(ROOT/ref['path']),ref['sha256'])
 def test_exact_native_sources(self):
  for a in self.assets.values():
   for prefix in ['master','render']:self.assertEqual(sha(ROOT/a[prefix+'_path']),a[prefix+'_sha256'])
   rd=load(ROOT/a['render_path']);self.assertEqual(rd['bounds'],a['bounds']);self.assertEqual(rd['quad_count'],a['quad_count'])
 def test_no_base_mutation_or_duplicate_ids(self):
  self.assertEqual(self.pack['remove_instance_ids'],[]);ids=[p['id']for p in self.instances];self.assertEqual(len(set(ids)),len(ids));self.assertTrue(all(x.startswith(('R9_PORT_','R9_MARKET_'))for x in ids))
 def test_all_native_footprints_and_heights(self):
  for p in self.instances:
   a=self.assets[p['asset_key']];self.assertEqual(p['scale'],[1,1,1]);self.assertEqual(ring(a['bounds'],p),p['footprint_xz_m']);self.assertAlmostEqual(p['native_bottom_y_m'],p['position_m'][1]+a['bounds']['min'][1]);self.assertAlmostEqual(p['native_top_y_m'],p['position_m'][1]+a['bounds']['max'][1]);self.assertEqual(len(p['support_samples']),9)
   self.assertTrue(all(abs(s['y_m']-p['support_floor_y_m'])<=.03 for s in p['support_samples']))
 def test_new_native_solids_do_not_overlap(self):
  for i,p in enumerate(self.instances):
   for q in self.instances[i+1:]:
    if p['native_bottom_y_m']>=q['native_top_y_m']-1e-6 or q['native_bottom_y_m']>=p['native_top_y_m']-1e-6:continue
    self.assertFalse(overlap(p['footprint_xz_m'],q['footprint_xz_m']),(p['id'],q['id']))
 def test_stack_top_exact_support(self):
  byid={p['id']:p for p in self.instances}
  for p in self.instances:
   if 'stack_support_id'not in p:continue
   below=byid[p['stack_support_id']];self.assertAlmostEqual(below['native_top_y_m'],p['native_bottom_y_m']);self.assertTrue(geo.convex_polygon_contains(below['footprint_xz_m'],p['footprint_xz_m'],1e-6))
 def test_routes_independently_rebuilt_from_sources(self):
  market=load(MARKET);f=market['placements'][0];self.assertEqual(f['id'],'MARKET_FOUNTAIN');r=Reservations({'common_instances':[f]})
  self.assertEqual(r.directional_count,493);self.assertEqual(len(r.routes),254)
  for p in self.instances:self.assertEqual(r.hits(p['footprint_xz_m']),[],p['id'])
  # The same algorithm must detect a crate deliberately moved onto the public quay center.
  route=next(x for x in r.routes if x['id']=='ROAD:PORT_QUAY');x,_,z=route['points_xyz_m'][10];self.assertIn('ROAD:PORT_QUAY',r.hits([[x-.5,z-.5],[x+.5,z-.5],[x+.5,z+.5],[x-.5,z+.5]]))
 def test_functional_groups_are_complete(self):
  ids={p['id']for p in self.instances};union=set()
  for g in self.plan['groups']:
   self.assertTrue(g['kind']);self.assertTrue(g['owner']);self.assertTrue(set(g['placement_ids'])<=ids);self.assertFalse(union&set(g['placement_ids']));union.update(g['placement_ids'])
  self.assertEqual(union,ids);self.assertEqual(self.report['accepted_groups'],len(self.plan['groups']));self.assertEqual(self.report['accepted_instances'],len(self.instances))
 def test_scope_and_footprint_negative_controls(self):
  self.assertEqual(self.report['status'],'PASS');self.assertEqual(self.report['unique_public_paths_checked'],254);self.assertEqual(self.report['directional_replay_cases_preserved_by_static_exclusion'],493);self.assertEqual(self.report['port_loading_links_preserved'],18);self.assertEqual(self.report['market_customer_paths_preserved'],104)
  self.assertTrue(overlap([[0,0],[1,0],[1,1],[0,1]],[[.9,.9],[2,.9],[2,2],[.9,2]]));self.assertFalse(overlap([[0,0],[1,0],[1,1],[0,1]],[[1,0],[2,0],[2,1],[1,1]]))
if __name__=='__main__':unittest.main(verbosity=2)
