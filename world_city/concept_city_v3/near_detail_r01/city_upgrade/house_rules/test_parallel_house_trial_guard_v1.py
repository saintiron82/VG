"""Small isolated fixtures only. No production masters, ledgers, or samplers."""
import copy
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import tempfile
import time
import unittest
from unittest import mock

import parallel_house_trial_guard_v1 as g
TEST_METRICS = {}


def contract_for(root, resume=7):
    base = dict(source_sha256='1'*64, authored_master_sha256='2'*64,
                core_sha256='3'*64, sampler_sha256='4'*64, engine_sha256='5'*64,
                output_directory='compiled/isolated_fixture', resume_start=resume)
    return {'schema': 'riverstone.parallel_house_trial_guard.v1', 'run_id': 'isolated_test',
            'authorization_ref': 'fixture-only-parent-approval', 'limits': dict(g.LIMITS),
            'slots': {slot: {'identity': dict(base, asset_key='ordinary_fixture_' + slot),
                            'compile_lock_path': str(root / name),
                            'slot_authorization_ref': 'fixture-only-' + slot}
                      for slot, name in [('primary', 'compile.lock'), ('secondary', 'compile_trial_second.lock')]}}


def real_worker(path, contract, root, slot, pipe):
    """One real PID, own AS limit and own external flock; no sampling."""
    try:
        resource.setrlimit(resource.RLIMIT_AS, (128*g.MIB, 128*g.MIB))
        started = time.monotonic()
        with open(contract['slots'][slot]['compile_lock_path'], 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            worker = g.TrialGuard(path, contract, generated_root=root)
            worker.register(slot, contract['slots'][slot]['identity'], '6'*64,
                            compile_lock_fd=lock.fileno(), worker_started_monotonic=started)
            pipe.send(('ready', os.getpid(), g.current_rss()))
            while True:
                command = pipe.recv()
                if command == 'chunk':
                    before = worker.before_chunk(7)
                    after = worker.after_chunk(8) if before.allowed else before
                    pipe.send((before.action, after.action))
                elif command == 'finish':
                    worker.finish(completed=8, checkpoint_identity_sha256='6'*64,
                                  checkpoint_manifest_sha256='7'*64)
                    pipe.send(('finished',)); break
    except Exception as error:
        pipe.send(('error', repr(error)))
    finally:
        pipe.close()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.path = self.root / (g.PREFIX + 'fixture.json')
        self.contract = contract_for(self.root)
        self.now = 1000.; self.pid = 9000001
        self.live = {p: {'pid': p, 'start': 'fixture:' + str(p)} for p in (9000001, 9000002, 9000003, 9000004)}
        self.rss = {p: 100*g.MIB for p in self.live}; self.peaks = dict(self.rss)
        def process(pid=None):
            pid = self.pid if pid is None else pid
            if pid not in self.live: raise g.GuardError('unknown_fixture_pid')
            return dict(self.live[pid])
        patches = [mock.patch.object(g, 'process_identity', side_effect=process),
                   mock.patch.object(g.time, 'monotonic', side_effect=lambda: self.now),
                   mock.patch.object(g, 'current_rss', side_effect=lambda: (self.rss[self.pid], 'proc_self_status_current')),
                   mock.patch.object(g, 'peak_rss', side_effect=lambda: self.peaks[self.pid]),
                   mock.patch.object(g, 'peer_rss', side_effect=lambda p: self.rss.get(p)),
                   mock.patch.object(g, '_known_exited', side_effect=lambda o: o['pid'] not in self.live),
                   mock.patch.object(g, '_check_compile_lock'), mock.patch.object(g, '_check_as_limit')]
        for patch in patches:
            patch.start(); self.addCleanup(patch.stop)
        self.coordinator = g.TrialGuard(self.path, self.contract, generated_root=self.root).create()

    def worker(self, slot, pid, started=None):
        self.pid = pid; worker = g.TrialGuard(self.path, self.contract, generated_root=self.root)
        worker.register(slot, self.contract['slots'][slot]['identity'], ('6' if slot == 'primary' else '8')*64,
                        compile_lock_fd=42, worker_started_monotonic=self.now if started is None else started)
        return worker

    def pair(self):
        a = self.worker('primary', 9000002); b = self.worker('secondary', 9000003)
        self.pid = 9000001; self.assertTrue(self.coordinator.release_barrier())
        return a, b

    def state(self): return json.loads(self.path.read_text())
    def alter(self, edit):
        state = self.state(); edit(state); self.path.write_text(json.dumps(state))

    def finish_pair(self):
        a, b = self.pair()
        for worker, pid, sha in [(a, 9000002, '6'), (b, 9000003, '8')]:
            self.pid = pid
            worker.finish(completed=7, checkpoint_identity_sha256=sha*64, checkpoint_manifest_sha256='9'*64)
        self.pid = 9000001
        return a, b

    def authorization(self):
        row = self.state()['slots']['primary']
        result = {'mode': 'SOLO_CONTINUATION', 'scheduler_authorization_ref': 'explicit-fixture-ledger-entry',
                'trial_contract_sha256': self.coordinator.digest,
                'slot': 'primary', 'identity_sha256': row['identity_sha256'],
                'checkpoint_identity_sha256': row['checkpoint_identity_sha256'],
                'checkpoint_manifest_sha256': row['checkpoint_manifest_sha256'], 'resume_start': row['completed'],
                'max_workers': 1, 'compile_lock_path': self.contract['slots']['primary']['compile_lock_path']}
        self.ledger = self.root/'fixture_scheduler_ledger.json'
        self.ledger.write_text(json.dumps({'schema': 'riverstone.parallel_house_solo_scheduler_ledger.v1', 'authorizations': [result]}))
        result['scheduler_ledger_sha256'] = hashlib.sha256(self.ledger.read_bytes()).hexdigest()
        return result

    def authorize(self, entry):
        return self.coordinator.authorize_solo_continuation(entry, scheduler_ledger_path=self.ledger)

    def test_barrier_is_explicit_and_never_authorizes_work_early(self):
        a = self.worker('primary', 9000002)
        self.assertEqual(a.before_chunk(7).action, 'WAIT_PEERS')
        self.pid = 9000001
        with self.assertRaisesRegex(g.GuardError, 'peer_not_ready'): self.coordinator.release_barrier()
        self.worker('secondary', 9000003); self.pid = 9000001
        self.assertTrue(self.coordinator.release_barrier())
        self.pid = 9000002; self.assertTrue(a.before_chunk(7).allowed)

    def test_exact_16_completed_chunks_relative_to_resume(self):
        a, b = self.pair(); self.pid = 9000002
        for completed in range(7, 23):
            self.assertTrue(a.before_chunk(completed).allowed)
            result = a.after_chunk(completed+1)
        self.assertEqual(result.reason, 'completed_chunk_limit')
        self.assertEqual(result.completed_since_resume, 16)
        self.assertFalse(a.before_chunk(23).allowed)
        self.pid = 9000003
        self.assertTrue(b.before_chunk(7).allowed)  # Independent count limit.

    def test_chunk_permit_and_commit_are_exactly_once(self):
        a, _ = self.pair(); self.pid = 9000002
        with self.assertRaises(g.GuardError): a.after_chunk(8)
        with self.assertRaises(g.GuardError): a.before_chunk(8)
        a.before_chunk(7)
        with self.assertRaises(g.GuardError): a.before_chunk(7)
        with self.assertRaises(g.GuardError): a.after_chunk(9)
        a.after_chunk(8)
        with self.assertRaises(g.GuardError): a.after_chunk(8)

    def test_current_rss_not_stored_rss_crosses_900_and_latches_both(self):
        a, b = self.pair(); self.pid = 9000002
        self.rss[9000002] = 450*g.MIB; self.rss[9000003] = 450*g.MIB
        self.assertTrue(a.before_chunk(7).allowed)  # Exactly 900 is permitted.
        a.after_chunk(8); self.rss[9000003] += 1024
        stop = a.before_chunk(8)
        self.assertEqual(stop.reason, 'combined_child_rss_limit')
        self.assertEqual(stop.combined_child_rss_bytes, 900*g.MIB+1024)
        self.rss[9000002] = self.rss[9000003] = 50*g.MIB
        self.pid = 9000003
        self.assertEqual(b.before_chunk(7).reason, 'combined_child_rss_limit')

    def test_peer_proc_unavailable_uses_recent_conservative_peak(self):
        self.peaks[9000003] = 850*g.MIB
        a, _ = self.pair(); self.pid = 9000002
        with mock.patch.object(g, 'peer_rss', return_value=None):
            self.assertEqual(a.before_chunk(7).reason, 'combined_child_rss_limit')

    def test_stale_peer_stops_even_when_proc_rss_is_available(self):
        a, _ = self.pair(); self.now += 30.01; self.pid = 9000002
        self.assertEqual(a.before_chunk(7).reason, 'stale_or_future_peer_heartbeat')

    def test_unknown_or_reused_pid_fails_closed(self):
        a, _ = self.pair(); self.pid = 9000002
        self.live[9000003]['start'] = 'different-process'
        self.assertEqual(a.before_chunk(7).reason, 'peer_process_or_rss_unknown')

    def test_malformed_peer_rss_latches_stop(self):
        a, _ = self.pair(); self.pid = 9000002
        with mock.patch.object(g, 'peer_rss', side_effect=g.GuardError('malformed')):
            self.assertEqual(a.before_chunk(7).action, 'STOP')

    def test_102_seconds_includes_preparation_and_barrier(self):
        a = self.worker('primary', 9000002, started=self.now-102)
        self.assertEqual(a.before_chunk(7).reason, 'checkpoint_time_limit')
        self.assertEqual(self.state()['slots']['primary']['completed'], 7)

    def test_boundary_time_stop_preserves_chunk_already_permitted(self):
        a, _ = self.pair(); self.pid = 9000002
        # Keep peer heartbeat fresh while moving past the time boundary.
        self.now += 101.9
        self.alter(lambda s: s['slots']['secondary'].update(heartbeat=self.now))
        self.assertTrue(a.before_chunk(7).allowed)
        self.now += .2
        result = a.after_chunk(8)
        self.assertEqual(result.reason, 'checkpoint_time_limit')
        self.assertEqual(result.completed_since_resume, 1)

    def test_duplicate_writer_and_distinct_child_pid(self):
        self.worker('primary', 9000002)
        with self.assertRaisesRegex(g.GuardError, 'duplicate_slot'): self.worker('primary', 9000004)
        with self.assertRaisesRegex(g.GuardError, 'distinct_child'): self.worker('secondary', 9000002)

    def test_coordinator_cannot_register_as_child(self):
        with self.assertRaisesRegex(g.GuardError, 'coordinator_is_not_child'): self.worker('primary', 9000001)

    def test_wrong_job_and_engine_are_rejected(self):
        worker = g.TrialGuard(self.path, self.contract, generated_root=self.root)
        identity = copy.deepcopy(self.contract['slots']['primary']['identity']); identity['engine_sha256'] = 'b'*64
        with self.assertRaisesRegex(g.GuardError, 'wrong_slot_or_job'):
            worker.register('primary', identity, '6'*64, compile_lock_fd=42, worker_started_monotonic=self.now)

    def test_forked_object_cannot_write(self):
        a, _ = self.pair(); self.pid = 9000004
        with self.assertRaisesRegex(g.GuardError, 'forked_writer'): a.before_chunk(7)

    def test_unknown_malformed_and_missing_peer_state_fail_closed(self):
        a, _ = self.pair(); self.pid = 9000002
        pristine = self.path.read_text()
        for edit in [lambda s: s['slots']['secondary'].update(rss_bytes='unknown'),
                     lambda s: s['slots'].pop('secondary'),
                     lambda s: s['slots']['secondary'].update(phase='UNKNOWN'),
                     lambda s: s['contract']['slots']['primary']['identity'].update(core_sha256='c'*64)]:
            self.path.write_text(pristine); self.alter(edit)
            with self.assertRaises(g.GuardError): a.before_chunk(7)
        self.path.write_text('{bad json')
        with self.assertRaises(g.GuardError): a.before_chunk(7)

    def test_existing_state_and_symlink_are_not_overwritten(self):
        original = self.path.read_bytes()
        with self.assertRaises(g.GuardError): self.coordinator.create()
        self.assertEqual(original, self.path.read_bytes())
        target = self.root / 'not_owned.json'; target.write_text('preserve')
        alias = self.root / (g.PREFIX + 'symlink.json'); alias.symlink_to(target)
        guard = g.TrialGuard(alias, self.contract, generated_root=self.root)
        with self.assertRaises(g.GuardError): guard.create()
        self.assertEqual(target.read_text(), 'preserve')

    def test_finish_preserves_identity_and_rejects_inflight_chunk(self):
        a, _ = self.pair(); self.pid = 9000002; a.before_chunk(7)
        with self.assertRaises(g.GuardError): a.finish(completed=7, checkpoint_identity_sha256='6'*64, checkpoint_manifest_sha256='9'*64)
        a.after_chunk(8)
        with self.assertRaises(g.GuardError): a.finish(completed=8, checkpoint_identity_sha256='0'*64, checkpoint_manifest_sha256='9'*64)
        a.finish(completed=8, checkpoint_identity_sha256='6'*64, checkpoint_manifest_sha256='9'*64)
        self.assertEqual(self.state()['slots']['primary']['checkpoint_identity_sha256'], '6'*64)

    def test_finished_child_live_rss_still_counts(self):
        a, b = self.pair(); self.pid = 9000002
        a.finish(completed=7, checkpoint_identity_sha256='6'*64, checkpoint_manifest_sha256='9'*64)
        self.rss[9000002] = 850*g.MIB; self.pid = 9000003
        self.assertEqual(b.before_chunk(7).reason, 'combined_child_rss_limit')

    def test_solo_requires_explicit_ledger_and_both_children_exited(self):
        self.finish_pair(); authorization = self.authorization()
        with self.assertRaisesRegex(g.GuardError, 'children_must_exit'): self.authorize(authorization)
        del self.live[9000002]; del self.live[9000003]
        for key, value in [('mode', 'PAIRED_TRIAL'), ('max_workers', 2), ('checkpoint_identity_sha256', '0'*64),
                           ('scheduler_ledger_sha256', ''), ('resume_start', 23)]:
            bad = dict(authorization, **{key: value})
            with self.assertRaises(g.GuardError): self.authorize(bad)
        self.pid = 9000004  # A later, explicitly authorized scheduler can validate.
        result = self.authorize(authorization)
        self.assertEqual(result['max_workers'], 1); self.assertEqual(self.state()['phase'], 'CLOSED')
        with self.assertRaises(g.GuardError): self.coordinator.release_barrier()
        with self.assertRaises(g.GuardError): self.authorize(authorization)
        with self.assertRaises(g.GuardError): self.worker('secondary', 9000004)

    def test_solo_ledger_bytes_and_checkpoint_entry_are_pinned(self):
        self.finish_pair(); authorization = self.authorization()
        del self.live[9000002]; del self.live[9000003]
        self.ledger.write_text(self.ledger.read_text() + '\n')
        with self.assertRaisesRegex(g.GuardError, 'ledger_bytes_changed'): self.authorize(authorization)
        authorization['scheduler_ledger_sha256'] = hashlib.sha256(self.ledger.read_bytes()).hexdigest()
        wrong = dict(authorization, checkpoint_manifest_sha256='c'*64)
        # A valid ledger containing the wrong checkpoint still cannot authorize it.
        entry = {k: v for k, v in wrong.items() if k != 'scheduler_ledger_sha256'}
        self.ledger.write_text(json.dumps({'schema': 'riverstone.parallel_house_solo_scheduler_ledger.v1', 'authorizations': [entry]}))
        wrong['scheduler_ledger_sha256'] = hashlib.sha256(self.ledger.read_bytes()).hexdigest()
        with self.assertRaisesRegex(g.GuardError, 'checkpoint_manifest_sha256_changed'): self.authorize(wrong)

    def test_scope_contract_limits_and_identity_are_small_and_exact(self):
        for field, value in [('hard_seconds', 121), ('completed_chunks', 17), ('combined_child_rss_bytes', 901*g.MIB)]:
            changed = copy.deepcopy(self.contract); changed['limits'][field] = value
            with self.assertRaises(g.GuardError): g.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        changed['slots']['secondary']['compile_lock_path'] = changed['slots']['primary']['compile_lock_path']
        with self.assertRaises(g.GuardError): g.validate_contract(changed)
        identity = copy.deepcopy(changed['slots']['primary']['identity']); identity['job_sha256'] = 'a'*64
        with self.assertRaises(g.GuardError): g.execution_identity(identity)
        with self.assertRaises(g.GuardError): g.TrialGuard(self.root/'unowned.json', self.contract, generated_root=self.root)
        self.assertLess(self.path.stat().st_size, 10000)


class OperatingSystemChecks(unittest.TestCase):
    def test_current_rss_and_fallback_are_self_only(self):
        rss, source = g.current_rss(); self.assertGreater(rss, 0)
        self.assertEqual(source, 'proc_self_status_current')
        with mock.patch.object(Path, 'read_text', side_effect=OSError('no proc')):
            peak, source = g.current_rss()
        self.assertGreater(peak, 0); self.assertEqual(source, 'ru_maxrss_self_conservative_peak')
        with mock.patch.object(Path, 'read_text', return_value='VmRSS: unknown kB\n'):
            with self.assertRaises(g.GuardError): g.current_rss()
            with self.assertRaises(g.GuardError): g.peer_rss(os.getpid())

    def test_lock_verification_does_not_acquire_unheld_external_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'compile.lock'
            with path.open('a') as lock:
                with self.assertRaises(g.GuardError): g._check_compile_lock(path, lock.fileno(), os.getpid())
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                g._check_compile_lock(path, lock.fileno(), os.getpid())
                with self.assertRaises(g.GuardError): g._check_compile_lock(path, lock.fileno(), os.getpid()+1)
                fcntl.flock(lock, fcntl.LOCK_UN)

    def test_unlimited_as_is_rejected(self):
        with mock.patch.object(resource, 'getrlimit', return_value=(-1, -1)):
            with self.assertRaises(g.GuardError): g._check_as_limit()
        with mock.patch.object(resource, 'getrlimit', return_value=(704*g.MIB, 704*g.MIB)):
            g._check_as_limit()

    def test_real_two_process_barrier_locks_and_atomic_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); contract = contract_for(root)
            path = root/(g.PREFIX+'real_process.json')
            coordinator = g.TrialGuard(path, contract, generated_root=root).create()
            context = multiprocessing.get_context('fork'); processes = []; pipes = []
            try:
                for slot in ('primary', 'secondary'):
                    parent, child = context.Pipe()
                    process = context.Process(target=real_worker, args=(path, contract, root, slot, child))
                    process.start(); child.close(); processes.append(process); pipes.append(parent)
                    self.assertTrue(parent.poll(5), 'child did not become ready')
                    ready = parent.recv(); self.assertEqual(ready[0], 'ready', ready)
                self.assertNotEqual(processes[0].pid, processes[1].pid)
                self.assertTrue(coordinator.release_barrier())
                # Simultaneous child calls exercise the shared atomic state lock.
                for pipe in pipes:
                    pipe.send('chunk')
                for pipe in pipes:
                    self.assertTrue(pipe.poll(5)); self.assertEqual(pipe.recv(), ('RUN', 'RUN'))
                for pipe in pipes:
                    pipe.send('finish'); self.assertTrue(pipe.poll(5)); self.assertEqual(pipe.recv(), ('finished',))
                for process in processes: process.join(5); self.assertEqual(process.exitcode, 0)
                state = json.loads(path.read_text())
                self.assertEqual(state['phase'], 'CLOSED')
                self.assertEqual([r['completed'] for r in state['slots'].values()], [8, 8])
                pair_peak = sum(r['peak_rss_bytes'] for r in state['slots'].values())
                aggregate = pair_peak + g.peak_rss()
                TEST_METRICS.update(real_pair_peak_rss_bytes=pair_peak, conservative_test_aggregate_peak_rss_bytes=aggregate)
                self.assertLess(aggregate, 128*g.MIB)
                self.assertEqual(list(root.glob('*.tmp.*')), [])
            finally:
                for pipe in pipes: pipe.close()
                for process in processes:
                    if process.is_alive(): process.terminate(); process.join(5)


if __name__ == '__main__': unittest.main()
