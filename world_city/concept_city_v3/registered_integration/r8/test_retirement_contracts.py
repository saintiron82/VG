import copy,unittest
from .promotion import explicit_retirements
from ..r6 import apply_packs as a

class RetirementTests(unittest.TestCase):
 def fixture(self):
  p=lambda name:dict(id=name,asset_key='cached',position_m=[0,0,0],palette_id='native')
  scene=dict(common_instances=[p('SITE_COMMON'),p('UNCHANGED')],common_assets={'cached':{}},surfaces={'land':[]},boxes=[])
  pack=dict(assets={},placements=[p('NEW_BASE'),p('NEW_ACCESS')],replacement_ledger={'existing_native_placements_removed':['SITE_COMMON']})
  return scene,pack
 def test_ledger_removes_old_and_retains_replacements_without_mutation(self):
  scene,pack=self.fixture();before=copy.deepcopy((scene,pack))
  out,ledger=a.apply_pack(scene,pack,'repair',extra_retire_ids=explicit_retirements(pack))
  self.assertEqual({p['id']for p in out['common_instances']},{'UNCHANGED','NEW_BASE','NEW_ACCESS'})
  self.assertEqual(ledger['retired_native_ids'],['SITE_COMMON']);self.assertEqual((scene,pack),before)
  self.assertIs(out['surfaces'],scene['surfaces'])
 def test_matching_dual_contracts(self):
  _,pack=self.fixture();pack['replaced_placement_ids']=['SITE_COMMON'];self.assertEqual(explicit_retirements(pack),['SITE_COMMON'])
 def test_conflicting_contracts_rejected(self):
  _,pack=self.fixture();pack['replaced_placement_ids']=['OTHER']
  with self.assertRaises(ValueError):explicit_retirements(pack)
 def test_unknown_runtime_id_rejected(self):
  scene,pack=self.fixture();scene['common_instances']=scene['common_instances'][1:]
  with self.assertRaises(ValueError):a.apply_pack(scene,pack,'repair',extra_retire_ids=explicit_retirements(pack))
 def test_malformed_or_duplicate_ids_rejected(self):
  for value in ['SITE_COMMON',[None],[''],['x','x']]:
   with self.subTest(value=value),self.assertRaises(ValueError):explicit_retirements({'replaced_placement_ids':value})
 def test_empty_prose_ledger_does_not_change_retirements(self):
  self.assertEqual(explicit_retirements({'replacement_ledger':{'note':'preserved'}}),[])
 def test_actual_common_source_declares_old_instance(self):
  path=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/common_entry_repair_r02/resolved_placements.json'
  pack=a.load(path);self.assertEqual(explicit_retirements(pack),['REGISTERED_LANDSCAPE:SITE_COMMON'])
if __name__=='__main__':unittest.main()
