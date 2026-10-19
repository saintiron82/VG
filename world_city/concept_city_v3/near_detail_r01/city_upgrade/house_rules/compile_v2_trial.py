"""One approved new small asset; no automatic next asset or old-checkpoint migration."""
import fcntl
import json
from pathlib import Path
import sys
import time
import adapter as a
import layered_compile_v2 as layer
import compile_batch as batch
import compile_house_queue as queue
from output_reservations_v1 import ReservationBook

HERE=Path(__file__).resolve().parent
KEY='ordinary_d4fcb5b21ffb18'
CATALOG=HERE.parent/'house_extensions/generated/active_catalog.json'
OUTPUT=HERE/'compiled/v2_trial_r01'
RULES=HERE/'v2_small_trial.rules.v1.json'
LEDGER=HERE/'generated/sampler_migration_queue.r01.json'


def run():
    begin=time.perf_counter()
    with (HERE/'queue.lock').open('a') as queue_lock:
        try:fcntl.flock(queue_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Original controller still active; wait for its normal boundary')
        pending=a.load(HERE/'compiled/extensions_r01/attached_native_row_0f0bbe769178b1.layered.resumable.json')
        if pending['status']!='PENDING_RESUMABLE_CHECKPOINT' or pending['session']!=1:
            raise ValueError('Original 0f0 checkpoint is not safely parked after session 1')
        state=a.load(LEDGER);state.update(state='RUNNING_NEW_V2_TRIAL',updated_utc=batch.now())
        batch.atomic_json(LEDGER,state)
        existing=OUTPUT/(KEY+'.layered.stats.json')
        result=a.load(existing) if existing.exists() else layer.run(KEY,OUTPUT,RULES,CATALOG,True)
        if not result['status'].startswith('PASS'):raise ValueError('Trial production compile did not finish')
        stats=OUTPUT/(KEY+'.layered.stats.json');qa_path=OUTPUT/(KEY+'.layered.qa.json');rp=OUTPUT/(KEY+'.layered.replay.json')
        logs=HERE/'compile_logs/v2_trial';logs.mkdir(exist_ok=True)
        reservation=result['output_reservation'];config=a.load(RULES)['shared_output_reservation']
        book=ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/p for p in config['retained_roots']],config['limit_bytes'])
        book.check(reservation['key'],262144)
        if not qa_path.exists():queue.checked_report([sys.executable,str(HERE/'render_only_qa.py'),'--stats',str(stats),'--source-catalog',str(CATALOG),'--output',str(qa_path)],logs/(KEY+'.qa.log'),qa_path)
        book.check(reservation['key'],262144)
        queue.checked_report([sys.executable,str(HERE/'run_bounded_reference_replay.py'),'--stats',str(stats),'--output',str(rp)],logs/(KEY+'.replay.bounded_r02.log'),rp)
        record=batch.inspect_output(KEY,OUTPUT)
        if not record['independent_qa']['pass'] or not record['independent_replay']['pass']:raise ValueError('Trial independent gates failed')
        entry=next(r for r in a.load(CATALOG)['assets'] if r['asset_key']==KEY)
        override={k:v for k,v in {'stats_path':record['stats_path'],'stats_sha256':record['stats_sha256'],
            'qa_path':str(qa_path.relative_to(a.ROOT)),'qa_sha256':a.sha(qa_path),'replay_path':str(rp.relative_to(a.ROOT)),'replay_sha256':a.sha(rp),
            'source_catalog_path':str(CATALOG.relative_to(a.ROOT)),'source_catalog_sha256':a.sha(CATALOG),
            'source_master_path':entry['source_master_path'],'source_master_sha256':entry['source_sha256'],
            'emitted_master_path':entry['emitted_master_path'],'emitted_master_sha256':entry['emitted_master_sha256'],
            'reason':'New explicit v2 sampler; full ownership/exterior QA and four independent preserved-reference-core chunk replays passed.'}.items()}
        op=HERE/'compiled/selection_overrides.json';overrides=a.load(op)
        if KEY in overrides['assets']:raise ValueError('Existing selection must not be overwritten by a trial')
        overrides['assets'][KEY]=override;batch.atomic_json(op,overrides)
        state.update(state='PAUSED_AFTER_VERIFIED_V2_TRIAL',updated_utc=batch.now(),trial_result=record,
            trial_finalization_retry_seconds=time.perf_counter()-begin,next_asset_requires_parent_approval=True,
            selection_override_sha256=a.sha(op))
        batch.atomic_json(LEDGER,state)
        reservation_record=book.record(reservation['key'])
        book.release(reservation['key'],reservation_record['identity'],'Full production domain and independent original-core replay passed')
        print(json.dumps(state),flush=True)

if __name__=='__main__':run()
