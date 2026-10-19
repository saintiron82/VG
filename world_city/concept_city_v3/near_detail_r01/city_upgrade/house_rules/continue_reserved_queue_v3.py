"""Continue a frozen ordered job list at safe full-asset boundaries.

Only the existing per-asset runner samples cells and owns compile/queue locks.
Complete matching artifacts are verified and skipped. Failed evidence is retained.
An explicit boundary stop file pauses before the next asset. No quality fallback.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import compile_reserved_asset_v3_r02 as runner

HERE = Path(__file__).resolve().parent
ROOT = runner.a.ROOT


def save(path, value):
    temporary = path.with_name(path.name + '.tmp')
    if temporary.exists():
        raise ValueError('Preserve interrupted queue state: ' + str(temporary))
    with temporary.open('x') as f:
        json.dump(value, f, sort_keys=True, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


def complete_record(row):
    job_path = ROOT / row['job_path']
    if runner.a.sha(job_path) != row['job_sha256']:
        raise ValueError('Queue job identity changed')
    job, entry, catalog, rules, output = runner.validated_job(job_path)
    handoff_path = output / (job['asset_key'] + '.layered.handoff.json')
    if not handoff_path.exists():
        return None
    handoff = runner.a.load(handoff_path)
    if not handoff['status'].startswith('PASS') or not all(handoff['compile_checks'].values()):
        raise ValueError('Incomplete handoff cannot be selected')
    if handoff['authored_master_sha256'] != entry['emitted_master_sha256']:
        raise ValueError('Completed authored master identity mismatch')
    stats_path = ROOT / handoff['stats_path']
    if runner.a.sha(stats_path) != handoff['stats_sha256']:
        raise ValueError('Completed stats changed')
    stats = runner.a.load(stats_path)
    expected = {'layer_engine_sha256': job['tools']['engine']['sha256'],
                'layer_rules_sha256': runner.a.sha(rules), 'input_catalog_sha256': runner.a.sha(catalog),
                'source_master_sha256': entry['source_sha256'], 'authored_master_sha256': entry['emitted_master_sha256']}
    if any(stats['compiled_header'][k] != v for k, v in expected.items()):
        raise ValueError('Completed recipe identity mismatch')
    for record in [*handoff['files'].values(), handoff['independent_qa'], handoff['independent_replay']]:
        if runner.a.sha(ROOT / record['path']) != record['sha256']:
            raise ValueError('Completed artifact changed')
    if not handoff['independent_qa']['pass'] or not handoff['independent_replay']['pass']:
        raise ValueError('Incomplete verification cannot be selected')
    return {'asset_key': job['asset_key'], 'handoff_path': str(handoff_path.relative_to(ROOT)),
            'handoff_sha256': runner.a.sha(handoff_path), 'stats_path': handoff['stats_path'],
            'stats_sha256': handoff['stats_sha256'], 'compile_seconds': handoff['elapsed_seconds'],
            'end_to_end_seconds': handoff['end_to_end_seconds'], 'quads': handoff['quads'],
            'files': handoff['files'], 'status': 'PASS_STRUCTURAL_PENDING_VISUAL'}


def run(queue_path, state_path, stop_path):
    queue = runner.a.load(queue_path)
    identity = {'queue_path': str(queue_path.relative_to(ROOT)), 'queue_sha256': runner.a.sha(queue_path),
                'controller_sha256': runner.a.sha(__file__)}
    state = {'schema': 'riverstone.reserved_serial_queue.v3', 'identity': identity,
             'state': 'STARTING', 'completed': [], 'pending': [], 'pinned_old_partial': queue['pinned_old_partial']}
    if state_path.exists():
        state = runner.a.load(state_path)
        if state['identity'] != identity:
            raise ValueError('Queue/controller identity changed on resume')
    with (HERE / 'reserved_v3_queue.lock').open('a') as controller_lock:
        fcntl.flock(controller_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for row in queue['jobs']:
            if stop_path.exists():
                state.update(state='PAUSED_AT_ASSET_BOUNDARY', updated_utc=runner.batch.now())
                save(state_path, state)
                return 0
            # Wait for the authorized previous full asset; never bypass its lock.
            with (HERE / 'queue.lock').open('a') as boundary:
                fcntl.flock(boundary, fcntl.LOCK_EX)
                fcntl.flock(boundary, fcntl.LOCK_UN)
            record = complete_record(row)
            if record is None:
                job = runner.a.load(ROOT / row['job_path'])
                log = ROOT / job['log_directory'] / (row['asset_key'] + '.queue_controller.log')
                log.parent.mkdir(parents=True, exist_ok=True)
                if log.exists():
                    raise ValueError('Existing attempt log preserved; reconcile before retry: ' + str(log))
                state.update(state='RUNNING', asset_key=row['asset_key'], updated_utc=runner.batch.now())
                save(state_path, state)
                start = time.perf_counter()
                with log.open('x') as f:
                    result = subprocess.run([sys.executable, str(HERE / 'compile_reserved_asset_v3_r02.py'),
                                             '--job', str(ROOT / row['job_path'])], stdout=f, stderr=subprocess.STDOUT)
                if result.returncode:
                    state['pending'].append({'asset_key': row['asset_key'], 'returncode': result.returncode,
                        'log_path': str(log.relative_to(ROOT)), 'log_sha256': runner.a.sha(log),
                        'elapsed_seconds': time.perf_counter()-start})
                    state.update(state='PENDING_REVIEW_PRESERVE_EVIDENCE', updated_utc=runner.batch.now())
                    save(state_path, state)
                    return result.returncode
                record = complete_record(row)
                if record is None:
                    raise ValueError('Successful runner lacks verified handoff')
            state['completed'] = [r for r in state['completed'] if r['asset_key'] != row['asset_key']] + [record]
            state.update(state='AT_ASSET_BOUNDARY', updated_utc=runner.batch.now())
            save(state_path, state)
            print(json.dumps({'event': 'asset_complete', **record}), flush=True)
        state.update(state='NEW_JOBS_COMPLETE_OLD_PARTIAL_PENDING', updated_utc=runner.batch.now())
        save(state_path, state)
        return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue', type=Path, required=True)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--stop-file', type=Path, required=True)
    x = p.parse_args()
    raise SystemExit(run(x.queue.resolve(), x.state.resolve(), x.stop_file.resolve()))
