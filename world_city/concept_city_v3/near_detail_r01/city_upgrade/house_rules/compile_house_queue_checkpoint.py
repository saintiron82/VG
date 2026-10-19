"""Restart a pre-sampling fenced legacy controller with a fresh process timer."""
import fcntl
import hashlib
import os
import compile_house_queue as queue

if __name__=='__main__':
    marker=queue.HERE/'.queue_handoff'
    if not marker.exists():raise SystemExit('Expected preserved controller handoff marker')
    os.environ['RIVERSTONE_QUEUE_HANDOFF_SHA256']=hashlib.sha256(marker.read_bytes()).hexdigest()
    with (queue.HERE/'queue.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Another house queue controller is active')
        raise SystemExit(queue.run(parent_boundary_worker=True))
