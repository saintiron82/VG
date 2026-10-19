"""Exact 2+2+1 producer-chain continuation fixture; preserves all ancestors."""
import contextlib,copy,fcntl,io,json,resource,signal,time,unittest
from pathlib import Path
import test_frontier_engine_integration_r01 as base
import imported_checkpoint_chain_v2 as chain
import layered_compile_chain_frontier_v4_r02 as current
import verify_imported_chain_replay_v2 as replay
from unittest.mock import patch
base.RUN_ENGINES=True
H=Path(__file__).resolve().parent;a=base.a
class ChainReal(base.RealEngineIntegration):
    def test_three_stages_exact_without_resampling_prefix(self):
        old_policy=self.policy('old_policy',2)
        base.original.run(self.key,self.output/'old',self.rules_path,self.catalog,True,old_policy)
        oldcp=self.output/'old'/(self.key+'.layered.checkpoint');manifest=a.load(oldcp/'manifest.json')
        oldledger=self.output/'old'/(self.key+'.layered.checkpoint_sessions.json')
        first={'original_directory':str(oldcp.relative_to(a.ROOT)),'original_identity':manifest['identity'],'original_files':chain.file_inventory(oldcp),'original_count':2,'expected_owned_lows':manifest['identity']['owned_lows'],'original_session_ledger':{'path':str(oldledger.relative_to(a.ROOT)),'sha256':a.sha(oldledger)}}
        firstpath=self.root/'first.json';a.write(firstpath,first)
        firstqa=self.root/'firstqa.json'
        with base.compile_lease():base.prefix_replay.verify(firstpath,firstqa)
        signal.alarm(0)
        rules=copy.deepcopy(self.rules);rules['imported_checkpoint_prefix']={'path':str(firstpath.relative_to(a.ROOT)),'sha256':a.sha(firstpath),'independent_prefix_replay':{'path':str(firstqa.relative_to(a.ROOT)),'sha256':a.sha(firstqa)}}
        rulespath=self.root/'middle_rules.json';a.write(rulespath,rules)
        stopped,_=self.run_capture(base.imported,self.output/'middle',rulespath,self.policy('middle_policy',2))
        self.assertEqual(stopped['completed_chunks'],4);self.assertEqual(stopped['status'],'PENDING_CHECKPOINT_SESSION_LIMIT')
        cp=self.output/'middle'/(self.key+'.layered.checkpoint');m=a.load(cp/'manifest.json');ledger=self.output/'middle'/(self.key+'.layered.checkpoint_sessions.json')
        # Materialize this pending fixture's shared catalog snapshot under its own
        # existing reservation before a successor needs the same immutable input.
        config=rules['shared_output_reservation'];book=current.output_reservations_v3.ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/x for x in config['retained_roots']],config['limit_bytes'],min_free_disk_bytes=config['min_free_disk_bytes'])
        key=self.key+'@'+str((self.output/'middle').relative_to(a.ROOT))
        snapshot=H/'replay_code'/('catalog_'+a.sha(self.catalog)[:16]+'.json')
        if not snapshot.exists():
            with book.writer(key):
                payload=self.catalog.read_bytes();book.check(key,len(payload));snapshot.write_bytes(payload)
        pins=chain.file_inventory(cp);oldpins=chain.file_inventory(oldcp)
        reader=chain._ReadOnlyStore(cp,m['identity'],pins,repository_root=a.ROOT)
        spec={'original_directory':str(cp.relative_to(a.ROOT)),'original_identity':m['identity'],'original_files':pins,'original_count':4,'expected_owned_lows':m['identity']['owned_lows'],'original_session_ledger':{'path':str(ledger.relative_to(a.ROOT)),'sha256':a.sha(ledger)},'producer_segments':chain.producer_segments(reader.reader)}
        specpath=self.root/'continuation.json';a.write(specpath,spec);qapath=self.root/'chainqa.json'
        with base.compile_lease():replay.verify(specpath,qapath)
        signal.alarm(0)
        rules['wall_time_limit_seconds']=600;rules['imported_checkpoint_prefix']={'path':str(specpath.relative_to(a.ROOT)),'sha256':a.sha(specpath),'independent_prefix_replay':{'path':str(qapath.relative_to(a.ROOT)),'sha256':a.sha(qapath)}}
        rp=self.root/'last_rules.json';a.write(rp,rules)
        policy=self.root/'third_policy.json';a.write(policy,{'enabled_asset_keys':[self.key],'max_sessions':3,'per_session_wall_seconds':600,'soft_stop_seconds':540,'continuation_approval':'Synthetic 2+2+1 exact continuation contract test'})
        stats,captures=self.run_capture(current,self.output/'last',rp,policy)
        self.assertEqual(len(captures),2);self.assertEqual(stats['checkpoint']['sessions_started'],3)
        self.assertEqual(stats['checkpoint']['imported_complete_chunks'],4)
        self.assertEqual(chain.file_inventory(oldcp),oldpins);self.assertEqual(chain.file_inventory(cp),pins)
        self.assertEqual([c['producer']['producer_id'] for c in stats['chunks']],['imported_reference_core']*2+['new_prepared_v3']*2+['new_prepared_v3_continuation_session_3'])
        evidence=self.check_final(stats,self.reference(),captures,[16])
        evidence.update(original_two_stages_immutable=True,imported_complete_chunks=4,new_sampled_chunks=1,actual_producer_segments=spec['producer_segments'],all_historical_sessions_preserved=True)
        base.EVIDENCE['chain_continuation']=evidence
if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));begin=time.perf_counter()
    suite=unittest.TestSuite([ChainReal('test_three_stages_exact_without_resampling_prefix')])
    with (H/'queue.lock').open('a') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with contextlib.redirect_stdout(io.StringIO()):r=unittest.TextTestRunner(verbosity=2).run(suite)
    p=H/'generated/chain_engine_v4.r05.json'
    if p.exists():raise ValueError('Existing evidence preserved')
    report={'pass':r.wasSuccessful(),'tests':r.testsRun,'errors':[str(e[1]) for e in r.errors+r.failures],'elapsed_seconds':time.perf_counter()-begin,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'engine_sha256':a.sha(current.__file__),'helper_sha256':a.sha(chain.__file__),'verifier_sha256':a.sha(replay.__file__),'evidence':base.EVIDENCE};a.write(p,report);print(json.dumps({k:v for k,v in report.items() if k!='evidence'}));raise SystemExit(not r.wasSuccessful())
