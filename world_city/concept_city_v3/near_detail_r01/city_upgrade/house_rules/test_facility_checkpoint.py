from pathlib import Path
import json
import tempfile
import hashlib
import unittest
from unittest.mock import patch
import compile_facility_checkpoint as f

class FacilityCheckpointContracts(unittest.TestCase):
    def run_manager(self,status):
        with patch.object(f,'validate'),patch.object(f.batch,'inspect_output',return_value=None),patch.object(Path,'mkdir'),\
             patch.object(f.checkpoint_queue,'execute',return_value={'state':status}) as execute,patch.object(f.finalizer,'run') as finish:
            result=f.run('registered_cathedral_north_cloister_range','catalog','output','policy')
            return result,execute.call_args.args,finish.call_count
    def test_pending_never_finalizes_or_passes(self):
        result,args,finished=self.run_manager('PENDING_CHECKPOINT_SESSION_LIMIT')
        self.assertEqual(result,2);self.assertEqual(finished,0);self.assertIn('--worker',args[0])
    def test_complete_only_then_runs_existing_finalizer(self):
        result,args,finished=self.run_manager('COMPILE_COMPLETE')
        self.assertEqual(result,0);self.assertEqual(finished,1)
    def test_worker_forwards_resume_and_returns_exact_status(self):
        for status,code in [('PENDING_RESUMABLE_CHECKPOINT',75),('PENDING_CHECKPOINT_SESSION_LIMIT',76),('PASS',0)]:
            with self.subTest(status=status),patch.object(f,'validate'),patch.object(f.layer,'run',return_value={'status':status}) as run:
                self.assertEqual(f.run('key','catalog','output','policy',worker=True,resume=True),code)
                self.assertTrue(run.call_args.kwargs['resume_checkpoint']);self.assertTrue(run.call_args.kwargs['render_only'])
    def test_unknown_asset_rejected_before_inputs(self):
        with self.assertRaisesRegex(ValueError,'outside the approved'):f.validate('other','catalog','output','policy')
    def test_manager_refuses_manual_resume_override(self):
        with patch.object(f,'validate'),self.assertRaisesRegex(ValueError,'committed ledger'):
            f.run('key','catalog','output','policy',resume=True)

    def validation_fixture(self,root):
        h=root/'house_rules';h.mkdir();(h/'.compile_pause').write_text('held');(h/'compiled').mkdir();(h/'compiled/baseline').write_bytes(b'x'*100)
        original=root/'source.json';original.write_text('{}');master=root/'master.json';master.write_text('{}')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();key='registered_cathedral_north_cloister_range'
        entry={'asset_key':key,'source_master_path':'source.json','emitted_master_path':'master.json','source_sha256':sha(original),'emitted_master_sha256':sha(master)}
        catalog=root/'catalog.json';catalog.write_text(json.dumps({'assets':[entry]}))
        policy=root/'policy.json';policy.write_text(json.dumps({'enabled_asset_keys':list(f.ALLOWED),'max_sessions':2,'per_session_wall_seconds':900,'soft_stop_seconds':840,'input_catalog_sha256':sha(catalog),'approved_inputs':{key:entry}}))
        base={'fine_pitch_m':.05,'total_output_budget_bytes':180000000};(h/'layer_rules.v1.json').write_text(json.dumps(base))
        rules=root/'rules.json';rules.write_text(json.dumps({**base,'total_output_budget_bytes':20000100,'facility_budget_guard':{'facility_output_cap_bytes':20000000,'baseline_retained_bytes':100}}))
        return h,key,catalog,root/'facility_roofs/compiled_expansion_r01',policy,rules
    def test_budget_only_rules_preserve_geometry_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);h,*args=self.validation_fixture(root)
            with patch.object(f.layer,'HERE',h),patch.object(f.a,'ROOT',root):self.assertEqual(f.validate(*args)['asset_key'],args[0])
    def test_pitch_change_rejected_even_if_budget_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);h,*args=self.validation_fixture(root);rules=args[-1];data=json.loads(rules.read_text());data['fine_pitch_m']=.1;rules.write_text(json.dumps(data))
            with patch.object(f.layer,'HERE',h),patch.object(f.a,'ROOT',root),self.assertRaisesRegex(ValueError,'only tighten'):
                f.validate(*args)
    def test_frozen_catalog_change_rejected_before_compilation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);h,*args=self.validation_fixture(root);args[1].write_text(args[1].read_text()+' ')
            with patch.object(f.layer,'HERE',h),patch.object(f.a,'ROOT',root),self.assertRaisesRegex(ValueError,'catalog changed'):
                f.validate(*args)
    def test_retained_baseline_cannot_shrink_and_expand_allowance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);h,*args=self.validation_fixture(root);(h/'compiled/baseline').write_bytes(b'x'*99)
            with patch.object(f.layer,'HERE',h),patch.object(f.a,'ROOT',root),self.assertRaisesRegex(ValueError,'baseline shrank'):
                f.validate(*args)

if __name__=='__main__':unittest.main()
