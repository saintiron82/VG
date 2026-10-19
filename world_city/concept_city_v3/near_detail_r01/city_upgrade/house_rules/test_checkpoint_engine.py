"""Interrupted/restarted production native sampling preserves exact geometry."""
import contextlib
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
import inspect
from unittest.mock import patch
import adapter as a
import layered_compile as layer
if 'checkpoint_policy_path' not in inspect.signature(layer.run).parameters:
    import checkpoint_candidate_engine as layer
import test_connected_constraints as fixtures


class CheckpointEngineContracts(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self,stop_after=4):
        with tempfile.TemporaryDirectory(dir=layer.HERE) as directory:
            root=Path(directory)
            master=fixtures.ConnectedConstraintContracts().master([([-.3,-.1,-.1],[.35,.2,.2])])
            master['constraints']=[{'id':'joined','kind':'connected','selector':{}}]
            source=root/'source.json';source.write_text(json.dumps(master))
            catalog=root/'catalog.json';catalog.write_text(json.dumps({'assets':[{'asset_key':'checkpoint_toy',
                'source_master_path':str(source.relative_to(a.ROOT)),'source_sha256':a.sha(source),
                'emitted_master_path':str(source.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(source)}]}))
            rules=a.load(layer.HERE/'layer_rules.v1.json');rules['chunk_edge_fine_cells']=4
            rules_path=root/'rules.json';rules_path.write_text(json.dumps(rules))
            policy=root/'policy.json';policy.write_text(json.dumps({'enabled_asset_keys':['checkpoint_toy'],
                'max_sessions':2,'per_session_wall_seconds':900,'soft_stop_seconds':840,
                **({'fixture_stop_after_chunks':stop_after} if stop_after else {})}))
            yield root,lambda resume=False:layer.run('checkpoint_toy',root/'out',rules_path,catalog,True,policy,resume)

    def test_two_partial_sessions_exhaust_budget_without_third_sampling(self):
        with self.fixture() as (root,run),contextlib.redirect_stdout(io.StringIO()):
            first=run();second=run(True)
            self.assertEqual(first['completed_chunks'],4)
            self.assertEqual(second['completed_chunks'],8)
            self.assertEqual(second['status'],'PENDING_CHECKPOINT_SESSION_LIMIT')
            ledger=root/'out/checkpoint_toy.layered.checkpoint_sessions.json';old=ledger.read_bytes()
            with patch.object(a.core,'compile_master') as compile,self.assertRaisesRegex(a.UnsupportedSurface,'checkpoint_total_session_limit'):
                run(True)
            compile.assert_not_called();self.assertEqual(ledger.read_bytes(),old)

    def test_recipe_and_dependency_hash_changes_refuse_resume_before_sampling(self):
        with self.fixture() as (root,run),contextlib.redirect_stdout(io.StringIO()):
            run();ledger=root/'out/checkpoint_toy.layered.checkpoint_sessions.json';old=ledger.read_bytes()
            original_sha=a.sha
            def altered(path):return '0'*64 if Path(path).resolve()==Path(a.__file__).resolve() else original_sha(path)
            with patch.object(a,'sha',side_effect=altered),patch.object(a.core,'compile_master') as compile,self.assertRaises(ValueError):run(True)
            compile.assert_not_called();self.assertEqual(ledger.read_bytes(),old)
            rules=root/'rules.json';rules.write_text(rules.read_text()+' ')
            with patch.object(a.core,'compile_master') as compile,self.assertRaises(ValueError):run(True)
            compile.assert_not_called();self.assertEqual(ledger.read_bytes(),old)

    def test_all_chunks_checkpoint_can_finalize_without_resampling(self):
        with self.fixture(None) as (root,run),contextlib.redirect_stdout(io.StringIO()):
            original_compile=a.core.compile_master;original_time=layer.time.perf_counter;calls=[]
            def compile(*args,**kwargs):calls.append(1);return original_compile(*args,**kwargs)
            def late():return original_time()+(841 if len(calls)>=32 else 0)
            with patch.object(a.core,'compile_master',side_effect=compile),patch.object(layer.time,'perf_counter',side_effect=late):paused=run()
            self.assertEqual(paused['completed_chunks'],16)
            with patch.object(a.core,'compile_master') as compile:finished=run(True)
            compile.assert_not_called();self.assertEqual(finished['checkpoint']['resumed_chunks'],16)

    def test_checkpoint_rejects_1800_second_single_execution(self):
        with self.fixture() as (root,run),contextlib.redirect_stdout(io.StringIO()):
            path=root/'rules.json';rules=json.loads(path.read_text());rules['wall_time_limit_seconds']=1800;path.write_text(json.dumps(rules))
            with self.assertRaisesRegex(a.UnsupportedSurface,'checkpoint_session_wall_limit_contract'):run()

    def test_two_sessions_equal_uninterrupted_bytes_fingerprints_and_connected(self):
        with tempfile.TemporaryDirectory(dir=layer.HERE) as directory:
            root=Path(directory)
            master=fixtures.ConnectedConstraintContracts().master([([-.3,-.1,-.1],[.35,.2,.2])])
            master['constraints']=[{'id':'joined','kind':'connected','selector':{}}]
            source=root/'source.json';source.write_text(json.dumps(master))
            catalog=root/'catalog.json';catalog.write_text(json.dumps({'assets':[{'asset_key':'checkpoint_toy',
                'source_master_path':str(source.relative_to(a.ROOT)),'source_sha256':a.sha(source),
                'emitted_master_path':str(source.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(source)}]}))
            rules=a.load(layer.HERE/'layer_rules.v1.json');rules['chunk_edge_fine_cells']=4
            rules_path=root/'rules.json';rules_path.write_text(json.dumps(rules))
            policy={'enabled_asset_keys':['checkpoint_toy'],'max_sessions':2,'per_session_wall_seconds':900,'soft_stop_seconds':840}
            full_policy=root/'full.policy.json';full_policy.write_text(json.dumps(policy))
            paused_policy=root/'paused.policy.json';paused_policy.write_text(json.dumps({**policy,'fixture_stop_after_chunks':8}))
            with contextlib.redirect_stdout(io.StringIO()):
                full=layer.run('checkpoint_toy',root/'full',rules_path,catalog,True,full_policy)
                paused=layer.run('checkpoint_toy',root/'paused',rules_path,catalog,True,paused_policy)
            self.assertEqual(paused['status'],'PENDING_RESUMABLE_CHECKPOINT')
            self.assertEqual(paused['completed_chunks'],8)
            self.assertFalse((root/'paused/checkpoint_toy.layered.stats.json').exists())
            self.assertFalse(list((root/'paused').glob('*cells*')))
            core_compile=a.core.compile_master;calls=[]
            def recording(*args,**kwargs):
                calls.append(kwargs['cell_bounds']);return core_compile(*args,**kwargs)
            with contextlib.redirect_stdout(io.StringIO()),patch.object(a.core,'compile_master',recording):
                resumed=layer.run('checkpoint_toy',root/'paused',rules_path,catalog,True,paused_policy,True)
            self.assertEqual(len(calls),2*(len(full['chunks'])-8))
            self.assertEqual(resumed['checkpoint']['resumed_chunks'],8)
            self.assertEqual(resumed['checkpoint']['sessions_started'],2)
            for key in ('full_fine_fingerprint','fine_face_fingerprint','constraints','quads','reference_full_fine_cells'):
                self.assertEqual(full[key],resumed[key],key)
            self.assertEqual(full['files']['.render.json']['sha256'],resumed['files']['.render.json']['sha256'])
            self.assertTrue((root/'paused/checkpoint_toy.layered.checkpoint').exists())
            with self.assertRaises(a.UnsupportedSurface):layer.run('checkpoint_toy',root/'paused',rules_path,catalog,True,paused_policy,True)

if __name__=='__main__':unittest.main()
