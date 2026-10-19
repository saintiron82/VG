import unittest,json,hashlib,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Integration(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.d=load(HERE/'candidate.json');c.old=load(HERE.parent/'r3/candidate.json')
 def test_input_and_asset_hashes(self):
  for a in self.d['provenance']['input_packs']:self.assertEqual(sha(ROOT/a['path']),a['sha256'])
  for a in self.d['common_assets'].values():
   for k in ('master','render'):self.assertEqual(sha(ROOT/a[k+'_path']),a[k+'_sha256'])
 def test_rigid_unique_placements(self):
  rows=self.d['common_instances'];self.assertEqual(len(rows),len({p['id'] for p in rows}))
  for p in rows:self.assertEqual(p['scale'],[1,1,1]);self.assertIn(p['asset_key'],self.d['common_assets'])
 def test_atomic_b15_replacement(self):
  pack=load(CITY/'assemblies/property/registered/poor_block015_east/route_repair_01/effective_placements.json');ids={p['id'] for p in self.d['common_instances']};self.assertFalse(ids&set(pack['replaced_placement_ids']));self.assertEqual(sum(p['source_pack']=='ordinary_density_b15' for p in self.d['common_instances']),10)
  for bid in pack['replaced_placement_ids']:
   for suffix in ('',':support',':owned_foundation'):self.assertIn(bid+suffix,self.d['remove_proxy_ids'])
  self.assertTrue(set(pack['superseded_old_path_ids'])<=set(self.d['access_overlay']['remove_path_ids']))
 def test_palette_does_not_change_geometry(self):
  before={p['id']:p for p in self.old['common_instances']};rows=[p for p in self.d['common_instances'] if p['source_pack']=='ordinary_density'];self.assertEqual(len(rows),16)
  for p in rows:
   for k in ('asset_key','position_m','yaw_rad','scale'):self.assertEqual(p[k],before[p['id']][k])
  self.assertEqual(collections.Counter(p['palette_id'] for p in rows),{'b13_wood_brown':10,'b13_clay_red':4,'b13_weathered_slate_gray':2})
 def test_preserved_sealed_packs(self):
  for kind in ('property','landmarks','woodland','port','market','fortifications','landscape'):
   self.assertEqual([p for p in self.old['common_instances'] if p['source_pack']==kind],[p for p in self.d['common_instances'] if p['source_pack']==kind])
 def test_palette_cache_isolation(self):
  cache={}
  for p in self.d['common_instances']:
   key=p['asset_key'],p['palette_id'];value=json.dumps(p['palette_override'],sort_keys=True);self.assertEqual(cache.setdefault(key,value),value)
 def test_source_and_ground_bound(self):
  self.assertEqual(sha(CITY/'registered_source/plan.json'),self.d['source_plan_sha256']);b=load(HERE/'terrain_binding.json');self.assertEqual(sha(ROOT/b['contract_path']),b['contract_sha256']);self.assertEqual(b['module'],self.d['terrain_module'])
if __name__=='__main__':unittest.main(verbosity=2)
