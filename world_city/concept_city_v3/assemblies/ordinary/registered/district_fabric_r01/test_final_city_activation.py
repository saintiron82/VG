"""Non-activation regressions for the final native/ledger checker."""
from . import check_final_city_activation as c
import copy,unittest
class NativeActivationCheckerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.prior,cls.final,cls.withdrawal,cls.groups,cls.deferred=c.expected_sources();cls.base=c.g.load(c.g.CITY/'evidence/r8_district_61_assembly_preflight_r01/scene.json');cls.synthetic=dict(cls.base);ret=set(cls.final['retired_source_ids']);cls.synthetic['common_instances']=[p for p in cls.base['common_instances']if p['id']not in ret];cls.synthetic['boxes']=[p for p in cls.base['boxes']if p['id']not in {x+':owned_foundation'for x in ret}];cls.synthetic['common_assets']=dict(cls.base['common_assets'])
  for g in cls.groups:
   if g['label']in ['final23','profile_extension_0']:cls.synthetic['common_instances']+=g['pack']['placements'];cls.synthetic['common_assets'].update(g['pack']['assets'])
 def audit(self,scene):return c.inspect(scene,self.groups,self.withdrawal,self.deferred,self.final)
 def test_source_sets_are_unique(self):
  self.assertEqual(sum(len(x['holding_ids'])for x in self.groups),110);self.assertEqual(sum(len(x['pack']['placements'])for x in self.groups),2006)
 def test_known_incomplete_actual61_rejected(self):
  a=self.audit(self.base);self.assertFalse(a['passed']);self.assertTrue(all(r['passes']for r in a['native_groups']if r['label']not in ['final23','profile_extension_0']))
 def test_synthetic_id_pose_fixture_passes(self):self.assertTrue(self.audit(self.synthetic)['passed'])
 def test_wrong_native_pose_rejected(self):
  s=dict(self.synthetic);s['common_instances']=list(s['common_instances']);i=next(i for i,p in enumerate(s['common_instances'])if p['id']==self.final['placements'][0]['id']);s['common_instances'][i]=copy.deepcopy(s['common_instances'][i]);s['common_instances'][i]['position_m'][1]+=.01;self.assertFalse(self.audit(s)['checks']['all_expected_native_instances_exact'])
 def test_missing_step_rejected(self):
  s=dict(self.synthetic);s['common_instances']=[p for p in s['common_instances']if p['id']!='BLOCK_001:R8_C003:PEDESTRIAN_STEP_SKIN'];self.assertFalse(self.audit(s)['checks']['all_expected_native_instances_exact'])
 def test_old_retirement_reintroduced_rejected(self):
  s=dict(self.synthetic);s['common_instances']=s['common_instances']+[next(p for p in self.base['common_instances']if p['id']==self.final['retired_source_ids'][0])];self.assertFalse(self.audit(s)['checks']['all_retired_old_native_absent'])
 def test_duplicate_expected_id_rejected(self):
  s=dict(self.synthetic);s['common_instances']=s['common_instances']+[self.final['placements'][0]];self.assertFalse(self.audit(s)['checks']['scene_native_ids_unique'])
 def test_missing_backland_selection_rejected(self):
  bid=next(x for x in self.groups if x['label']=='backland835')['pack']['placements'][0]['id'];s=dict(self.synthetic);s['common_instances']=[p for p in s['common_instances']if p['id']!=bid];self.assertFalse(self.audit(s)['checks']['all_backland835_selected_once'])
 def test_withdrawn_source_cannot_reappear(self):
  s=dict(self.synthetic);s['common_instances']=s['common_instances']+[dict(id=self.withdrawal['withdrawn_unactivated_native_ids'][0])];self.assertFalse(self.audit(s)['checks']['all_explicitly_deferred_native_absent'])
if __name__=='__main__':unittest.main()
