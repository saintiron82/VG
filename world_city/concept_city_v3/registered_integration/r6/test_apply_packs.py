import copy,unittest
from . import apply_packs as a

class PlacementTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.base=a.load(a.BASE_PATH,a.BASE_SHA256)
  cls.pack=a.load(a.MERCHANT_PATH,a.MERCHANT_SHA256)
  cls.result,cls.ledger=a.apply_pack(cls.base,cls.pack,'merchant_fabric_r02')
 def empty(self):return dict(assets={},placements=[])
 def test_sealed_source_count(self):
  self.assertEqual((len(self.ledger['retired_native_ids']),len(self.ledger['inserted_runtime_ids']),self.ledger['source_door_count']),(58,38,126))
 def test_only_old_foundations_retired(self):
  retired=set(self.pack['replaced_placement_ids']); expected={b['id'] for b in self.base['boxes'] if b['source_mass_id'] in retired}
  self.assertEqual(set(self.ledger['retired_foundation_proxy_ids']),expected);self.assertEqual(len(expected),58)
 def test_no_terrain_mutation(self):self.assertIs(self.result['surfaces'],self.base['surfaces'])
 def test_bridge_mechanism_unchanged(self):self.assertIs(self.result['bridge_mechanism'],self.base['bridge_mechanism'])
 def test_camera_unchanged(self):self.assertIs(self.result['inspection_cameras'],self.base['inspection_cameras'])
 def test_retained_instances_identical(self):
  retired=set(self.pack['replaced_placement_ids']);old={p['id']:p for p in self.base['common_instances']}
  for p in self.result['common_instances']:
   if p['id'] in old:self.assertIs(p,old[p['id']]);self.assertNotIn(p['id'],retired)
 def test_parent_untouched(self):
  self.assertEqual(len(self.base['common_instances']),3154);self.assertEqual(len(self.base['boxes']),540)
 def test_component_records_not_duplicated(self):
  added=set(self.ledger['inserted_runtime_ids']);member={p['id'] for p in self.pack['component_placements']}
  self.assertFalse(added&member);self.assertEqual(len(self.result['common_instances']),3134)
 def test_palette_override_survives(self):
  result={p['id']:p for p in self.result['common_instances']}
  for p in self.pack['placements']:self.assertEqual(result[p['id']]['palette_override'],p['palette_override'])
 def test_bad_retirement_rejected(self):
  p=self.empty();p['replaced_placement_ids']=['UNKNOWN']
  with self.assertRaisesRegex(ValueError,'Unknown retired'):a.apply_pack(self.base,p,'negative')
 def test_existing_id_reuse_rejected(self):
  p=self.empty();p['placements']=[copy.deepcopy(self.base['common_instances'][0])]
  with self.assertRaisesRegex(ValueError,'Unretired IDs'):a.apply_pack(self.base,p,'negative')
 def test_scaled_instance_rejected(self):
  d=copy.copy(self.base);p=dict(self.base['common_instances'][0],scale=[2,1,1]);d['common_instances']=[p]
  with self.assertRaisesRegex(ValueError,'scaling'):a.validate_instances(d)
 def test_palette_cache_alias_rejected(self):
  d=copy.copy(self.base);p=copy.deepcopy(self.base['common_instances'][0]);q=dict(p,id='OTHER',palette_override={'slate':'ffffff'});d['common_instances']=[p,q]
  with self.assertRaisesRegex(ValueError,'Palette cache alias'):a.validate_instances(d)
 def test_missing_asset_rejected(self):
  d=copy.copy(self.base);d['common_instances']=[dict(self.base['common_instances'][0],asset_key='missing')]
  with self.assertRaisesRegex(ValueError,'Missing asset'):a.validate_instances(d)
 def test_master_hash_tampering_rejected(self):
  key,x=next(iter(self.pack['assets'].items()));x=copy.deepcopy(x);x['master_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'Changed common master'):a.asset_record(x)
 def test_scene_activation_not_claimed(self):self.assertFalse(self.ledger['ground_activation'])

if __name__=='__main__':unittest.main(verbosity=2)
