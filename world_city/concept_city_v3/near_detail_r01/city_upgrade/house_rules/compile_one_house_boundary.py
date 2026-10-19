"""Run exactly the approved next house, then stop before another full asset."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import compile_house_queue as queue


def run(key,rules):
    prior=queue.a.load(queue.STATE);completed={r['asset_key'] for r in prior['completed']}
    planned=[k for phase in queue.phases() for k in phase['keys'] if k not in completed]
    if not planned or planned[0]!=key:raise ValueError('Requested asset is not the next approved queue boundary')
    marker=queue.HERE/'.queue_handoff'
    if not marker.exists():raise ValueError('Missing preserved controller handoff marker')
    os.environ['RIVERSTONE_QUEUE_HANDOFF_SHA256']=hashlib.sha256(marker.read_bytes()).hexdigest()
    with (queue.HERE/'queue.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another house controller is active')
        return queue.run(parent_boundary_worker=True,stop_after_asset=key,asset_rules={key:Path(rules).resolve()})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('key');p.add_argument('--rules',type=Path,required=True)
    x=p.parse_args();raise SystemExit(run(x.key,x.rules))
