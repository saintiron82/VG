import unittest,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class AssemblyContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=load(HERE/'candidate.json')
 def test_all_sources_and_render_hashes(self):
  for k,a in self.d['common_assets'].items():
   with self.subTest(asset=k):
    self.assertEqual(sha(ROOT/a['master_path']),a['master_sha256']);self.assertEqual(sha(ROOT/a['render_path']),a['render_sha256'])
 def test_inputs_bound(self):
  for a in self.d['provenance']['input_packs']:self.assertEqual(sha(ROOT/a['path']),a['sha256'],a['name'])
 def test_unique_rigid_instances(self):
  ids=[p['id'] for p in self.d['common_instances']];self.assertEqual(len(ids),len(set(ids)))
  for p in self.d['common_instances']:
   self.assertEqual(p['scale'],[1,1,1]);self.assertIn(p['asset_key'],self.d['common_assets'])
 def test_every_superseded_body_support_and_door_removed(self):
  prop=load(CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json');bids={'B_PORT_0','B_REG_0191'};paths={'B_PORT_0:DOOR','B_REG_0191:DOOR'}
  for row in prop['replacement_ledger']:bids.update(row['source_building_ids']);paths.update(row['source_owned_path_ids'])
  self.assertEqual(len(bids),29)
  for b in bids:
   for suffix in ('',':support',':owned_foundation'):self.assertIn(b+suffix,self.d['remove_proxy_ids'])
  self.assertTrue(paths<=set(self.d['access_overlay']['remove_path_ids']))
  self.assertTrue(set('E'+str(i) for i in range(1,8))<=set(self.d['replace_plot_ids']))
 def test_no_broad_water_erasing_floor_mask(self):self.assertEqual(self.d['floor_ownership_masks'],[])
 def test_bridge_finite_owner_and_explicit_gradient_exception(self):
  d=load(CITY/'assemblies/waterworks/registered_bridge/resolved_placements.json');s=d['summary'];self.assertLessEqual(s['local_junction_maximum_gradient'],.15);self.assertEqual(s['main_span_profile_gradient_ceiling'],.1);self.assertEqual(s['internal_render_faces'],0)
  self.assertGreater(s['minimum_actual_navigation_clearance_m'],3);self.assertGreater(s['minimum_actual_foundation_embed_m'],.5)
 def test_common_palette_cache_cannot_leak(self):
  maps={}
  for p in self.d['common_instances']:
   key=(p['asset_key'],p['palette_id']);value=json.dumps(p['palette_override'],sort_keys=True)
   self.assertEqual(maps.setdefault(key,value),value,key)
 def test_preserved_ordinary_and_forest_transforms(self):
  old=load(CITY/'registered_integration/common_city_candidate.json');a={p['id']:p for p in old['common_instances'] if p['source_pack'] in ('ordinary','woodland')};b={p['id']:p for p in self.d['common_instances'] if p['source_pack'] in ('ordinary','woodland')};self.assertEqual(a,b)
 def test_market_route_bypass_bound(self):
  d=load(CITY/'assemblies/market/registered/resolved_placements.json');self.assertEqual(d['access_overlay']['replace_roads'],self.d['access_overlay']['replace_roads'])
if __name__=='__main__':unittest.main(verbosity=2)
