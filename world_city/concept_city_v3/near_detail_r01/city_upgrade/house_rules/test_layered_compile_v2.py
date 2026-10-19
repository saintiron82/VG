"""New opt-in engine contract and exact old-core evidence, without global replacement."""
import ast
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import adapter as a
import layered_compile as old
import layered_compile_v2 as new
import output_reservations_v1 as reservations
import replay_certificate_qa as replay
import render_only_qa as qa
from test_connected_constraints import ConnectedConstraintContracts


class StaticV2Contracts(unittest.TestCase):
    def test_original_core_and_engine_remain_frozen(self):
        self.assertEqual(a.sha(a.core.__file__),'2a64ed2cdf43c9adb27a821170192f69fef0153c7be98cc85c903e34ff2a407b')
        self.assertEqual(a.sha(old.__file__),'5e567fb48a2a5f67bae674adbe8bec990e4d6fa0c8123ec916d1b0a5decc4b33')
    def test_only_explicit_v2_sampling_calls(self):
        tree=ast.parse(Path(new.__file__).read_text());calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertEqual(calls.count('exact_sampling_v2.compile_master_v2'),2)
        self.assertNotIn('a.core.compile_master',calls)
    def test_reviewed_module_hash_required(self):
        p=new.verified_sampler_provenance();self.assertEqual(p['implementation_sha256'],new.EXPECTED_SAMPLER_SHA256)
        altered={**p,'implementation_sha256':'0'*64}
        with patch.object(new.exact_sampling_v2,'get_sampler_provenance',return_value=altered):
            with self.assertRaises(a.UnsupportedSurface):new.verified_sampler_provenance()
    def test_independent_replay_uses_original_core(self):
        text=Path(replay.__file__).read_text();self.assertIn("snapshot=contract['code_snapshots']['core']",text)
        self.assertIn('result=core.compile_master(master',text);self.assertNotIn('compile_master_v2',text)


class ActualV2Parity(unittest.TestCase):
    def test_retained_old_core_exact_v2_geometry_and_independent_replay(self):
        with tempfile.TemporaryDirectory(dir=old.HERE) as directory:
            d=Path(directory);out=d/'outputs';out.mkdir()
            master=ConnectedConstraintContracts().master([([-.15,-.1,-.1],[.15,.15,.15])])
            master['constraints']=[{'id':'joined','kind':'connected','selector':{}}]
            master['materials']['accent']='888888'
            master['components'][0]['operations']+=[
                {'id':'cut','action':'cut','part':'foundation','shape':{'kind':'box','min':[-.05,.05,-.1],'max':[.05,.15,.05]}},
                {'id':'repaint','action':'paint','part':'foundation','material':'accent','feature':'repaint','shape':{'kind':'extrusion','polygon':[[-.1,-.1],[.1,-.1],[0,.1]],'z_min':-.1,'z_max':0}}]
            source=d/'source.json';source.write_text(json.dumps(master))
            catalog=d/'catalog.json';catalog.write_text(json.dumps({'assets':[{'asset_key':'v2_fixture','source_master_path':str(source.relative_to(a.ROOT)),'source_sha256':a.sha(source),'emitted_master_path':str(source.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(source)}]}))
            rules=a.load(old.HERE/'layer_rules.v1.json');rules['chunk_edge_fine_cells']=4
            rules['shared_output_reservation']={'book_path':str((d/'book.json').relative_to(a.ROOT)),
                'retained_roots':[str(out.relative_to(a.ROOT)),str((old.HERE/'replay_code').relative_to(a.ROOT))],
                'limit_bytes':10_000_000,'asset_cap_bytes':1_000_000}
            rp=d/'rules.json';rp.write_text(json.dumps(rules))
            slow=old.run('v2_fixture',out/'slow',rp,catalog)
            fast=new.run('v2_fixture',out/'fast',rp,catalog,render_only=True)
            for field in ('full_fine_fingerprint','fine_face_fingerprint','constraints','quads','reference_full_fine_cells'):
                self.assertEqual(slow[field],fast[field],field)
            with gzip.open(a.ROOT/slow['files']['.render.json']['path'],'rt') as f:sr=json.load(f)
            with gzip.open(a.ROOT/fast['files']['.render.json']['path'],'rt') as f:fr=json.load(f)
            for field in ('groups','materials','bounds','cell_count'):self.assertEqual(sr[field],fr[field],field)
            fast_stats=out/'fast/v2_fixture.layered.stats.json';slow_stats=out/'slow/v2_fixture.layered.stats.json'
            self.assertTrue(qa.verify(fast_stats,catalog,slow_stats)['pass'])
            with patch.object(new.exact_sampling_v2,'compile_master_v2',side_effect=AssertionError('Independent replay cannot call v2')):
                report=replay.verify(fast_stats);self.assertTrue(report['pass'],report)
            self.assertTrue(fast['replay_contract']['command'][1].endswith('layered_compile_v2.py'))
            self.assertEqual(fast['compiled_header']['sampling_backend']['implementation_sha256'],new.EXPECTED_SAMPLER_SHA256)
            self.assertIn('exact_sampling_v2',fast['replay_contract']['code_snapshots'])
            config=rules['shared_output_reservation'];book=reservations.ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/p for p in config['retained_roots']],config['limit_bytes'])
            key=fast['output_reservation']['key'];record=book.record(key)
            self.assertEqual(record['state'],'ACTIVE');book.release(key,record['identity'],'Synthetic exact parity and independent old-core replay passed')

if __name__=='__main__':unittest.main()
