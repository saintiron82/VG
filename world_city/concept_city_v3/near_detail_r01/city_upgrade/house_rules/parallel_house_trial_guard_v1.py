"""Isolated two-house trial capacity guard. No sampler imports or launches.

The caller owns both external compile locks, AS limits, a hard 120-second alarm,
checkpoint commits, and exclusion of GUI/character work. Callers must treat
GuardError as STOP and preserve the checkpoint. This module only writes its own
small, atomically replaced generated/parallel_house_trial_guard_v1.* state.

Coordinator: create -> workers register -> release_barrier (one explicit call).
Child: register -> before_chunk -> commit one real chunk -> after_chunk;
finish after checkpoint commit. No heartbeat thread; peer freshness is 30 s.
WAIT_PEERS never grants sampling and contains no sleep or polling. The start
clock is supplied from child launch, so preparation/barrier time is included.
Limits request a stop at a boundary; they cannot interrupt a chunk or guarantee
that its commit fits before the caller's hard deadline. No checkpoint identity
or engine recipe is changed to enter/leave the bounded trial.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import stat
import sys
import time
import uuid

PREFIX = 'parallel_house_trial_guard_v1.'
HERE = Path(__file__).resolve().parent
MIB = 1024 * 1024
LIMITS = {'child_as_bytes': 704 * MIB, 'combined_child_rss_bytes': 900 * MIB,
          'hard_seconds': 120, 'checkpoint_seconds': 102, 'completed_chunks': 16,
          'heartbeat_stale_seconds': 30}
IDENTITY_FIELDS = {'asset_key', 'source_sha256', 'authored_master_sha256',
                   'core_sha256', 'sampler_sha256', 'engine_sha256',
                   'output_directory', 'resume_start'}


class GuardError(RuntimeError):
    """Fail closed: do not start another chunk; preserve committed work."""


def _need(ok, reason):
    if not ok:
        raise GuardError(reason)


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def execution_identity(value):
    """No whole job/policy SHA: those may contain this contract's SHA."""
    _need(isinstance(value, dict) and set(value) == IDENTITY_FIELDS, 'identity_fields')
    _need(isinstance(value['asset_key'], str) and value['asset_key'].startswith('ordinary_'), 'ordinary_house_required')
    for key in IDENTITY_FIELDS:
        if key.endswith('_sha256'):
            _need(_sha(value[key]), 'invalid_' + key)
    _need(_integer(value['resume_start']), 'invalid_resume_start')
    output = value['output_directory']
    _need(isinstance(output, str) and output and not Path(output).is_absolute()
          and '..' not in Path(output).parts and str(Path(output)) == output, 'invalid_output_directory')
    return canonical_digest(value)


def validate_contract(contract):
    _need(isinstance(contract, dict) and set(contract) == {'schema', 'run_id', 'authorization_ref', 'limits', 'slots'}, 'contract_fields')
    _need(contract['schema'] == 'riverstone.parallel_house_trial_guard.v1', 'contract_schema')
    _need(isinstance(contract['run_id'], str) and re.fullmatch('[A-Za-z0-9_-]{1,96}', contract['run_id']), 'run_id')
    _need(isinstance(contract['authorization_ref'], str) and bool(contract['authorization_ref'].strip()), 'missing_trial_authorization')
    _need(contract['limits'] == LIMITS, 'fixed_trial_limits_changed')
    _need(isinstance(contract['slots'], dict) and set(contract['slots']) == {'primary', 'secondary'}, 'two_explicit_slots_required')
    identities = []; locks = []
    for slot, spec in contract['slots'].items():
        _need(isinstance(spec, dict) and set(spec) == {'identity', 'compile_lock_path', 'slot_authorization_ref'}, 'slot_fields')
        execution_identity(spec['identity']); identities.append(spec['identity'])
        path = spec['compile_lock_path']
        _need(isinstance(path, str) and Path(path).is_absolute() and str(Path(path).resolve()) == path, 'compile_lock_path')
        _need(Path(path).name == 'compile.lock' if slot == 'primary' else Path(path).name != 'compile.lock', 'primary_secondary_lock_confusion')
        _need(isinstance(spec['slot_authorization_ref'], str) and bool(spec['slot_authorization_ref'].strip()), 'separate_slot_authorization_required')
        locks.append(path)
    _need(locks[0] != locks[1], 'compile_locks_must_differ')
    _need(identities[0]['asset_key'] != identities[1]['asset_key'], 'jobs_must_differ')
    _need(identities[0]['engine_sha256'] == identities[1]['engine_sha256'], 'same_frozen_engine_required')
    return canonical_digest(contract)


def process_identity(pid=None):
    """Linux PID + process-start tick prevents PID reuse. Unknown is unsafe."""
    pid = os.getpid() if pid is None else pid
    try:
        data = Path('/proc/%d/stat' % pid).read_text()
        tail = data[data.rindex(')') + 2:].split()
        _need(tail[0] not in ('Z', 'X'), 'process_dead')
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        _need(bool(boot), 'boot_identity_missing')
        return {'pid': pid, 'start': boot + ':' + tail[19]}
    except (OSError, ValueError, IndexError) as error:
        raise GuardError('process_identity_unknown') from error


def current_rss():
    """Current child RSS; fall back to SELF peak (never RUSAGE_CHILDREN)."""
    try:
        text = Path('/proc/self/status').read_text()
    except OSError:
        text = None
    if text is not None:
        match = re.search(r'^VmRSS:\s+(\d+)\s+kB\s*$', text, re.MULTILINE)
        _need(match is not None and int(match.group(1)) > 0, 'malformed_current_rss')
        return int(match.group(1)) * 1024, 'proc_self_status_current'
    return peak_rss(), 'ru_maxrss_self_conservative_peak'


def peak_rss():
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    _need(_number(peak) and peak > 0, 'rss_unavailable')
    return int(peak) if sys.platform == 'darwin' else int(peak) * 1024


def peer_rss(pid):
    """Caller verifies PID/start identity before AND after this near-time sample."""
    try:
        text = Path('/proc/%d/status' % pid).read_text()
    except OSError:
        return None
    match = re.search(r'^VmRSS:\s+(\d+)\s+kB\s*$', text, re.MULTILINE)
    _need(match is not None and int(match.group(1)) > 0, 'malformed_peer_current_rss')
    return int(match.group(1)) * 1024


def _known_exited(owner):
    try:
        return process_identity(owner['pid']) != owner
    except GuardError:
        try:
            os.kill(owner['pid'], 0)
        except OSError as error:
            if error.errno == errno.ESRCH:
                return True
        return False


def _check_as_limit():
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    _need(0 < soft <= LIMITS['child_as_bytes'] and 0 < hard <= LIMITS['child_as_bytes'], 'caller_must_set_child_as_limit')


def _check_compile_lock(path, fd, pid):
    """Observe caller's flock in /proc/locks. Never acquire/release that lock."""
    try:
        info = os.fstat(fd); target = os.stat(path, follow_symlinks=False)
        _need(stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == (target.st_dev, target.st_ino), 'wrong_compile_lock_fd')
        device = (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
        for row in Path('/proc/locks').read_text().splitlines():
            fields = row.split()
            if len(fields) < 8 or fields[1:4] != ['FLOCK', 'ADVISORY', 'WRITE']:
                continue
            dev = fields[5].split(':')
            if int(fields[4]) == pid and (int(dev[0], 16), int(dev[1], 16), int(dev[2])) == device:
                return
    except (OSError, ValueError, IndexError) as error:
        raise GuardError('compile_lock_ownership_unknown') from error
    raise GuardError('caller_does_not_own_compile_lock')


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    completed_since_resume: int
    combined_child_rss_bytes: int | None
    checkpoint_required: bool

    @property
    def allowed(self):
        return self.action == 'RUN'


class TrialGuard:
    def __init__(self, state_path, contract, *, generated_root=None):
        root = Path(generated_root or HERE / 'generated').resolve()
        self.path = Path(state_path).absolute()
        _need(self.path.parent == root and self.path.name.startswith(PREFIX)
              and self.path.name.endswith('.json'), 'guard_output_scope')
        _need(root.is_dir(), 'generated_root_missing')
        self.lock_path = self.path.with_name(self.path.name + '.lock')
        self.contract = json.loads(json.dumps(contract))
        self.digest = validate_contract(self.contract)
        self.slot = None; self.owner = None; self.lock_fd = None

    @contextmanager
    def _locked(self):
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
        fd = os.open(self.lock_path, flags, 0o600)
        try:
            info = os.fstat(fd)
            _need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1, 'unowned_guard_lock')
            # Kernel wait, never a polling loop; caller's hard alarm still applies.
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _load(self):
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd) as stream:
                info = os.fstat(stream.fileno())
                _need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                      and info.st_nlink == 1 and info.st_size <= 65536, 'unowned_or_oversize_state')
                state = json.load(stream, parse_constant=lambda x: (_ for _ in ()).throw(GuardError('nonfinite_state')))
        except (OSError, ValueError) as error:
            raise GuardError('guard_state_unreadable') from error
        self._validate_state(state)
        return state

    def _validate_state(self, state):
        _need(isinstance(state, dict) and set(state) == {'schema', 'contract', 'contract_sha256', 'coordinator', 'phase', 'stop_reason', 'slots', 'solo_authorization', 'observed_combined_rss_bytes'}, 'state_fields')
        _need(state['schema'] == 'riverstone.parallel_house_trial_guard.state.v1'
              and state['contract_sha256'] == self.digest and state['contract'] == self.contract, 'contract_identity_changed')
        _need(state['phase'] in ('REGISTERING', 'RUNNING', 'CLOSED'), 'unknown_guard_phase')
        _need(state['stop_reason'] is None or isinstance(state['stop_reason'], str), 'invalid_stop_reason')
        _need(state['observed_combined_rss_bytes'] is None or _integer(state['observed_combined_rss_bytes']), 'invalid_observed_rss')
        _need(isinstance(state['coordinator'], dict) and set(state['coordinator']) == {'pid', 'start'}, 'coordinator_fields')
        _need(isinstance(state['slots'], dict) and set(state['slots']) <= {'primary', 'secondary'}, 'unknown_slot')
        seen = set()
        for slot, row in state['slots'].items():
            fields = {'owner', 'identity_sha256', 'checkpoint_identity_sha256', 'started', 'heartbeat', 'rss_bytes', 'peak_rss_bytes', 'rss_source', 'completed', 'in_chunk', 'phase', 'stop_reason', 'checkpoint_manifest_sha256'}
            _need(isinstance(row, dict) and set(row) == fields, 'heartbeat_fields')
            owner = row['owner']; _need(isinstance(owner, dict) and set(owner) == {'pid', 'start'} and _integer(owner['pid'], 1) and isinstance(owner['start'], str), 'worker_identity_unknown')
            _need(owner['pid'] not in seen, 'duplicate_worker_pid'); seen.add(owner['pid'])
            _need(row['identity_sha256'] == execution_identity(self.contract['slots'][slot]['identity']) and _sha(row['checkpoint_identity_sha256']), 'wrong_job_identity')
            _need(_number(row['started']) and _number(row['heartbeat']) and row['heartbeat'] >= row['started'], 'invalid_heartbeat_time')
            _need(_integer(row['rss_bytes'], 1) and row['rss_source'] in ('proc_self_status_current', 'ru_maxrss_self_conservative_peak'), 'invalid_rss')
            _need(_integer(row['peak_rss_bytes'], 1) and row['peak_rss_bytes'] >= row['rss_bytes'], 'invalid_peak_rss')
            start = self.contract['slots'][slot]['identity']['resume_start']
            _need(_integer(row['completed']) and start <= row['completed'] <= start + 16, 'invalid_chunk_progress')
            _need(type(row['in_chunk']) is bool and row['phase'] in ('READY', 'ACTIVE', 'STOPPING', 'FINISHED'), 'unknown_worker_phase')
            _need(row['stop_reason'] is None or isinstance(row['stop_reason'], str), 'worker_stop_reason')
            _need(row['checkpoint_manifest_sha256'] is None or _sha(row['checkpoint_manifest_sha256']), 'checkpoint_manifest_identity')
            if row['phase'] == 'FINISHED':
                _need(not row['in_chunk'] and _sha(row['checkpoint_manifest_sha256']), 'unfinished_checkpoint')
        if state['phase'] == 'RUNNING':
            _need(set(state['slots']) == {'primary', 'secondary'}, 'running_peer_missing')
        if state['phase'] == 'CLOSED':
            _need(set(state['slots']) == {'primary', 'secondary'} and all(r['phase'] == 'FINISHED' for r in state['slots'].values()), 'premature_close')
        _need(isinstance(state['solo_authorization'], dict)
              and set(state['solo_authorization']) <= {'primary', 'secondary'}, 'solo_authorization_state')
        _need(not state['solo_authorization'] or state['phase'] == 'CLOSED', 'solo_before_closed')

    def _save(self, state):
        self._validate_state(state)
        data = (json.dumps(state, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
        _need(len(data) <= 65536, 'state_too_large')
        temp = self.path.with_name(self.path.name + '.tmp.' + uuid.uuid4().hex)
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, self.path)
        directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def create(self):
        with self._locked():
            _need(not os.path.lexists(self.path), 'existing_trial_preserved')
            self._save({'schema': 'riverstone.parallel_house_trial_guard.state.v1', 'contract': self.contract,
                        'contract_sha256': self.digest, 'coordinator': process_identity(),
                        'phase': 'REGISTERING', 'stop_reason': None, 'slots': {}, 'solo_authorization': {},
                        'observed_combined_rss_bytes': None})
        return self

    def register(self, slot, identity, checkpoint_identity_sha256, *, compile_lock_fd, worker_started_monotonic):
        _need(slot in self.contract['slots'] and identity == self.contract['slots'][slot]['identity'], 'wrong_slot_or_job')
        _need(self.slot is None and _sha(checkpoint_identity_sha256), 'already_registered_or_invalid_checkpoint')
        owner = process_identity(); now = time.monotonic()
        _need(_number(worker_started_monotonic) and 0 <= worker_started_monotonic <= now, 'invalid_worker_start')
        _check_as_limit(); _check_compile_lock(self.contract['slots'][slot]['compile_lock_path'], compile_lock_fd, owner['pid'])
        rss, source = current_rss()
        with self._locked():
            state = self._load()
            _need(state['phase'] == 'REGISTERING' and state['stop_reason'] is None, 'trial_not_registering')
            _need(slot not in state['slots'], 'duplicate_slot_writer')
            _need(all(r['owner']['pid'] != owner['pid'] for r in state['slots'].values()), 'distinct_child_pids_required')
            _need(owner['pid'] != state['coordinator']['pid'], 'coordinator_is_not_child')
            state['slots'][slot] = {'owner': owner, 'identity_sha256': execution_identity(identity),
                'checkpoint_identity_sha256': checkpoint_identity_sha256, 'started': worker_started_monotonic,
                'heartbeat': now, 'rss_bytes': rss, 'peak_rss_bytes': max(rss, peak_rss()), 'rss_source': source, 'completed': identity['resume_start'],
                'in_chunk': False, 'phase': 'READY', 'stop_reason': None, 'checkpoint_manifest_sha256': None}
            if now - worker_started_monotonic >= LIMITS['checkpoint_seconds']:
                self._stop(state, 'checkpoint_time_limit')
            self._save(state)
        self.slot = slot; self.owner = owner; self.lock_fd = compile_lock_fd
        return self

    def _coordinator(self, state):
        _need(state['coordinator'] == process_identity(), 'coordinator_identity_mismatch')

    @staticmethod
    def _stop(state, reason):
        if state['stop_reason'] is None:
            state['stop_reason'] = reason
        for row in state['slots'].values():
            if row['phase'] != 'FINISHED':
                row['phase'] = 'STOPPING'; row['stop_reason'] = state['stop_reason']

    def _check_peers(self, state, now):
        total = 0
        for row in state['slots'].values():
            if row['phase'] == 'FINISHED' and _known_exited(row['owner']):
                continue
            age = now - row['heartbeat']
            if age < 0 or age > LIMITS['heartbeat_stale_seconds']:
                self._stop(state, 'stale_or_future_peer_heartbeat'); return
            try:
                _need(process_identity(row['owner']['pid']) == row['owner'], 'peer_identity_reused')
                # The two RSS reads are near-contemporaneous, not an atomic OS snapshot.
                rss = peer_rss(row['owner']['pid'])
                _need(process_identity(row['owner']['pid']) == row['owner'], 'peer_identity_reused')
                total += row['peak_rss_bytes'] if rss is None else rss
            except GuardError:
                self._stop(state, 'peer_process_or_rss_unknown'); return
        state['observed_combined_rss_bytes'] = total if len(state['slots']) == 2 else None
        if total > LIMITS['combined_child_rss_bytes']:
            self._stop(state, 'combined_child_rss_limit')

    def release_barrier(self):
        """Coordinator invokes once after both children report READY; no polling."""
        with self._locked():
            state = self._load(); self._coordinator(state)
            _need(state['phase'] == 'REGISTERING' and set(state['slots']) == {'primary', 'secondary'}, 'peer_not_ready')
            now = time.monotonic(); self._check_peers(state, now)
            if any(now - row['started'] >= LIMITS['checkpoint_seconds'] for row in state['slots'].values()):
                self._stop(state, 'checkpoint_time_limit')
            if state['stop_reason'] is None:
                state['phase'] = 'RUNNING'
                for row in state['slots'].values(): row['phase'] = 'ACTIVE'
            self._save(state)
            return state['stop_reason'] is None

    def _owned(self, state):
        _need(self.slot in state['slots'] and self.owner == process_identity(), 'unregistered_or_forked_writer')
        row = state['slots'][self.slot]
        _need(row['owner'] == self.owner, 'worker_identity_changed')
        _check_compile_lock(self.contract['slots'][self.slot]['compile_lock_path'], self.lock_fd, self.owner['pid'])
        _check_as_limit()
        return row

    def _decision(self, state, row):
        count = row['completed'] - self.contract['slots'][self.slot]['identity']['resume_start']
        rss = state['observed_combined_rss_bytes']
        reason = state['stop_reason'] or row['stop_reason']
        if reason or row['phase'] in ('STOPPING', 'FINISHED'):
            return Decision('STOP', reason or 'finished', count, rss, True)
        if state['phase'] != 'RUNNING':
            return Decision('WAIT_PEERS', 'coordinator_barrier', count, rss, False)
        return Decision('RUN', 'within_trial_limits', count, rss, False)

    def _pulse(self, state, row):
        now = time.monotonic(); row['heartbeat'] = now
        row['rss_bytes'], row['rss_source'] = current_rss()
        row['peak_rss_bytes'] = max(row['rss_bytes'], peak_rss())
        self._check_peers(state, now)
        if now - row['started'] >= LIMITS['checkpoint_seconds']:
            row['phase'] = 'STOPPING'; row['stop_reason'] = row['stop_reason'] or 'checkpoint_time_limit'
        if row['completed'] - self.contract['slots'][self.slot]['identity']['resume_start'] >= LIMITS['completed_chunks']:
            row['phase'] = 'STOPPING'; row['stop_reason'] = row['stop_reason'] or 'completed_chunk_limit'

    def before_chunk(self, completed):
        with self._locked():
            state = self._load(); row = self._owned(state)
            _need(_integer(completed) and completed == row['completed'] and not row['in_chunk'], 'chunk_count_or_permit_mismatch')
            self._pulse(state, row); decision = self._decision(state, row)
            if decision.allowed:
                row['in_chunk'] = True
            self._save(state); return decision

    def after_chunk(self, completed):
        """Only after the real chunk record AND checkpoint commit succeeded."""
        with self._locked():
            state = self._load(); row = self._owned(state)
            _need(row['in_chunk'] and _integer(completed) and completed == row['completed'] + 1, 'one_committed_chunk_required')
            row['completed'] = completed; row['in_chunk'] = False
            self._pulse(state, row); self._save(state)
            return self._decision(state, row)

    def finish(self, *, completed, checkpoint_identity_sha256, checkpoint_manifest_sha256):
        """Record preserved checkpoint; never signal/kill/release caller locks."""
        with self._locked():
            state = self._load(); row = self._owned(state)
            _need(not row['in_chunk'] and completed == row['completed'], 'unfinished_chunk_cannot_finish')
            _need(row['phase'] != 'FINISHED' and checkpoint_identity_sha256 == row['checkpoint_identity_sha256']
                  and _sha(checkpoint_manifest_sha256), 'checkpoint_identity_changed')
            row['heartbeat'] = time.monotonic(); row['rss_bytes'], row['rss_source'] = current_rss()
            row['peak_rss_bytes'] = max(row['rss_bytes'], peak_rss())
            row['phase'] = 'FINISHED'; row['checkpoint_manifest_sha256'] = checkpoint_manifest_sha256
            if len(state['slots']) == 2 and all(r['phase'] == 'FINISHED' for r in state['slots'].values()):
                state['phase'] = 'CLOSED'
            self._save(state)
            return self._decision(state, row)

    def authorize_solo_continuation(self, authorization, *, scheduler_ledger_path):
        """Validate/record an explicit scheduler ledger entry, never launch.

        Entry is supplied by an authorized scheduler, not minted by this guard.
        It binds exact preserved checkpoint bytes. New ledger authorization is
        required per house; only one SOLO continuation is recorded per house.
        The caller must use the primary compile.lock and ordinary solo scheduler.
        A later scheduler process may validate a ledger; the original coordinator
        need not remain alive. This method never opens a compile lock or starts work.
        """
        fields = {'mode', 'scheduler_authorization_ref', 'scheduler_ledger_sha256',
                  'trial_contract_sha256', 'slot', 'identity_sha256', 'checkpoint_identity_sha256',
                  'checkpoint_manifest_sha256', 'resume_start', 'max_workers', 'compile_lock_path'}
        _need(isinstance(authorization, dict) and set(authorization) == fields, 'solo_authorization_fields')
        try:
            with Path(scheduler_ledger_path).open('rb') as stream:
                data = stream.read(65537)
            _need(len(data) <= 65536 and hashlib.sha256(data).hexdigest() == authorization['scheduler_ledger_sha256'], 'scheduler_ledger_bytes_changed')
            ledger = json.loads(data)
            _need(isinstance(ledger, dict) and set(ledger) == {'schema', 'authorizations'}
                  and ledger['schema'] == 'riverstone.parallel_house_solo_scheduler_ledger.v1'
                  and isinstance(ledger['authorizations'], list), 'scheduler_ledger_schema')
            entry = {key: value for key, value in authorization.items() if key != 'scheduler_ledger_sha256'}
            _need(ledger['authorizations'].count(entry) == 1, 'scheduler_ledger_entry_missing_or_duplicate')
        except (OSError, ValueError) as error:
            raise GuardError('scheduler_ledger_unreadable') from error
        with self._locked():
            state = self._load()
            _need(state['phase'] == 'CLOSED' and authorization['slot'] not in state['solo_authorization'], 'trial_not_closed_or_solo_already_authorized')
            _need(authorization['mode'] == 'SOLO_CONTINUATION' and authorization['max_workers'] == 1
                  and authorization['trial_contract_sha256'] == self.digest, 'solo_mode_only')
            _need(authorization['slot'] in state['slots'], 'solo_slot_unknown')
            row = state['slots'][authorization['slot']]
            for key in ('identity_sha256', 'checkpoint_identity_sha256', 'checkpoint_manifest_sha256'):
                _need(authorization[key] == row[key], 'solo_' + key + '_changed')
            _need(authorization['resume_start'] == row['completed'], 'solo_resume_start_changed')
            _need(authorization['compile_lock_path'] == self.contract['slots']['primary']['compile_lock_path'], 'solo_requires_primary_compile_lock')
            _need(_sha(authorization['scheduler_ledger_sha256']) and isinstance(authorization['scheduler_authorization_ref'], str)
                  and authorization['scheduler_authorization_ref'].strip(), 'explicit_scheduler_ledger_authorization_required')
            for peer in state['slots'].values():
                _need(_known_exited(peer['owner']), 'trial_children_must_exit_before_solo')
            state['solo_authorization'][authorization['slot']] = json.loads(json.dumps(authorization)); self._save(state)
            return dict(authorization)
