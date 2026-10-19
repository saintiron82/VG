"""Timed worker under the parent controller's already-checked asset boundary.

A pause requested during an active asset applies to the NEXT asset. A committed
second execution of the same asset must not spend its 900-second budget waiting
in the legacy CLI pause gate. Actual sampling, source hashes and compile.lock are
still enforced by the unchanged layered engine.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import layered_compile as layer

HERE=Path(__file__).resolve().parent

def verify_controller(asset_key):
    marker=HERE/'.queue_handoff'
    if not marker.exists() or os.environ.get('RIVERSTONE_QUEUE_HANDOFF_SHA256')!=hashlib.sha256(marker.read_bytes()).hexdigest():
        raise ValueError('No current parent boundary acknowledgement')
    state=json.loads((HERE/'compiled/house_queue.json').read_text())
    if state.get('state')!='RUNNING' or state.get('asset_key')!=asset_key:
        raise ValueError('Controller does not own this active asset')
    with (HERE/'queue.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        fcntl.flock(lock,fcntl.LOCK_UN)
    raise ValueError('No live controller lock; refuse detached sampling')


def run(key,output,catalog,rules=None,render_only=False,checkpoint_policy=None,resume=False):
    verify_controller(key)
    hold=HERE/'.checkpoint_pause'
    if resume and hold.exists():
        request=json.loads(hold.read_text())
        if request.get('asset_key')==key:
            print(json.dumps({'status':'PAUSED_BEFORE_CHECKPOINT_RESUME','asset_key':key,
                'cell_sampling_started':False,'execution_budget_consumed':False,
                'hold_sha256':hashlib.sha256(hold.read_bytes()).hexdigest()}),flush=True)
            return 78
    if not render_only or not Path(output).resolve().is_relative_to((HERE/'compiled').resolve()):
        raise ValueError('Parent worker is restricted to approved render-only house outputs')
    result=layer.run(key,output,rules,catalog,render_only,checkpoint_policy,resume)
    return {'PENDING_RESUMABLE_CHECKPOINT':75,'PENDING_CHECKPOINT_SESSION_LIMIT':76}.get(result.get('status'),0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('key');p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--catalog',type=Path,required=True);p.add_argument('--rules',type=Path);p.add_argument('--render-only',action='store_true')
    p.add_argument('--checkpoint-policy',type=Path);p.add_argument('--resume-checkpoint',action='store_true')
    x=p.parse_args();raise SystemExit(run(x.key,x.output_dir,x.catalog,x.rules,x.render_only,x.checkpoint_policy,x.resume_checkpoint))
