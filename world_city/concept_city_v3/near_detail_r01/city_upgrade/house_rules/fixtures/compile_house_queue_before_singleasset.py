"""Approved serial render-only queue: remaining base, native reissues, extensions."""
from __future__ import annotations
import json
import fcntl
from pathlib import Path
import subprocess
import sys
import time
import adapter as a
import compile_batch as b
import register_extension_outputs

HERE=Path(__file__).resolve().parent
ROOT_OUTPUT=HERE/'compiled'
STATE=ROOT_OUTPUT/'house_queue.json'


def phases():
    remaining=a.load(HERE/'generated/priority_pause.json')['remaining_base_keys']
    holds=a.load(ROOT_OUTPUT/'provenance_holds.json')['assets'];overrides=a.load(ROOT_OUTPUT/'selection_overrides.json')['assets']
    legacy=[key for key in holds if key not in overrides]
    extension=HERE.parent/'house_extensions/generated/active_catalog.json'
    return [
        {'name':'remaining_base','catalog':HERE/'generated/active_catalog.json','output':ROOT_OUTPUT,'keys':remaining},
        {'name':'native_legacy_reissues','catalog':HERE/'generated/active_catalog.json','output':ROOT_OUTPUT/'native_reissues_r02','keys':legacy},
        {'name':'house_extensions','catalog':extension,'output':ROOT_OUTPUT/'extensions_r01','keys':[r['asset_key'] for r in a.load(extension)['assets'] if r.get('emitted_master_path')]},
    ]


def checked_report(command,log_path,report_path,timeout=900):
    if report_path.exists() and a.load(report_path).get('pass'):return
    if report_path.exists():raise ValueError('Existing failed evidence is preserved; review it before retrying in a new report path: '+str(report_path))
    with log_path.open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    if result.returncode or not report_path.exists() or not a.load(report_path).get('pass'):raise ValueError('Independent report did not pass: '+str(report_path))


def wait_at_boundary(state,phase,key,start):
    """Wait in the controller before creating a timed child process."""
    if (HERE/'.compile_pause').exists():
        state.update(state='PAUSED_AT_ASSET_BOUNDARY',phase=phase,asset_key=key,updated_utc=b.now(),elapsed_seconds=time.monotonic()-start)
        b.atomic_json(STATE,state)
        print(json.dumps({'queue_status':'PAUSED_AT_ASSET_BOUNDARY','asset_key':key,'sampling_timer_started':False}),flush=True)
        while (HERE/'.compile_pause').exists():time.sleep(1)


def run(parent_boundary_worker=False):
    if (HERE/'.compile_pause').exists():raise ValueError('Priority compile pause remains active')
    plan=phases();prior=a.load(STATE) if STATE.exists() else {};completed=prior.get('completed',[])
    completed_keys={r['asset_key'] for r in completed}
    expected=max(prior.get('expected_new_outputs',0),len(completed_keys|{k for p in plan for k in p['keys']}))
    state={'schema':'riverstone.house_detail.serial_queue.v1','state':'RUNNING',
        'updated_utc':b.now(),'expected_new_outputs':expected,'completed':completed,'phases':[{'name':p['name'],'catalog':str(p['catalog'].relative_to(a.ROOT)),'keys':p['keys']} for p in plan],
        'storage_policy':'Existing cell payloads and failure evidence preserved. New outputs use actual transient common sampling with no permanent cell payload.',
        'geometry_reduction':False,'single_heavy_compiler':True,'total_output_budget_bytes':180000000}
    start=time.monotonic();logs=HERE/'compile_logs/house_queue';logs.mkdir(parents=True,exist_ok=True)
    try:
        for phase in plan:
            for key in phase['keys']:
                if key in completed_keys:
                    verified=b.inspect_output(key,phase['output'])
                    if not verified or not verified.get('independent_qa',{}).get('pass') or not verified.get('independent_replay',{}).get('pass'):
                        raise ValueError('Prior queue completion is no longer independently verified: '+key)
                    continue
                wait_at_boundary(state,phase['name'],key,start)
                state.update(state='RUNNING',phase=phase['name'],asset_key=key,updated_utc=b.now(),elapsed_seconds=time.monotonic()-start);b.atomic_json(STATE,state)
                result=b.run([key],phase['catalog'],phase['output'],render_only=True,parent_boundary_worker=parent_boundary_worker)
                if result:raise ValueError('Compile/structural QA did not pass for '+key)
                stats_path=phase['output']/(key+'.layered.stats.json');replay_path=phase['output']/(key+'.layered.replay.json')
                checked_report([sys.executable,str(HERE/'replay_certificate_qa.py'),'--stats',str(stats_path),'--output',str(replay_path)],
                               logs/(key+'.replay.log'),replay_path,timeout=900)
                stats=a.load(stats_path);record=b.inspect_output(key,phase['output'])
                record['independent_replay']={'path':str(replay_path.relative_to(a.ROOT)),'sha256':a.sha(replay_path),'pass':True,
                    'scope':'Deterministic selected owned chunks; complete unpruned authored master and preserved common core.'}
                if phase['name']=='native_legacy_reissues':
                    old=a.load(ROOT_OUTPUT/(key+'.layered.stats.json'))
                    record['legacy_comparison']={k:old[k]==stats[k] for k in ('full_fine_fingerprint','fine_face_fingerprint')}
                    # Comparison is evidence, never a requirement to reproduce a legacy crop error.
                    compare_path=phase['output']/(key+'.legacy_comparison.json')
                    b.atomic_json(compare_path,{'asset_key':key,'original_outputs_preserved':True,'native_output_authoritative':True,'fingerprint_matches':record['legacy_comparison'],
                        'old_stats_path':str((ROOT_OUTPUT/(key+'.layered.stats.json')).relative_to(a.ROOT)),'new_stats_path':str(stats_path.relative_to(a.ROOT))})
                    overrides_path=ROOT_OUTPUT/'selection_overrides.json';overrides=a.load(overrides_path)
                    overrides['assets'][key]={'stats_path':str(stats_path.relative_to(a.ROOT)),'stats_sha256':a.sha(stats_path),
                        'qa_path':record['independent_qa']['path'],'qa_sha256':record['independent_qa']['sha256'],
                        'replay_path':str(replay_path.relative_to(a.ROOT)),'replay_sha256':a.sha(replay_path),'reason':'Verified native-bounds render-only reissue; old cells and render preserved.'}
                    b.atomic_json(overrides_path,overrides)
                state['completed'].append({'asset_key':key,'phase':phase['name'],**record})
                state.update(state='ASSET_COMPLETE',updated_utc=b.now(),elapsed_seconds=time.monotonic()-start);b.atomic_json(STATE,state)
                b.refresh_manifest(phase['catalog'],phase['output'],{'state':'ASSET_COMPLETE_WITH_INDEPENDENT_REPLAY','asset_key':key})
                if phase['name']=='native_legacy_reissues':b.refresh_manifest(HERE/'generated/active_catalog.json',ROOT_OUTPUT,{'state':'NATIVE_REISSUE_COMPLETE','asset_key':key})
                if phase['name']=='house_extensions':register_extension_outputs.publish()
                print(json.dumps({'queue_asset_complete':key,'phase':phase['name'],'completed':len(state['completed']),'total':expected,
                    'stats_path':record['stats_path'],'quads':record['quads'],'cells':record['reference_full_fine_cells'],'max_rss_kib':record['max_rss_kib'],
                    'render':record['files']['.render.json'],'independent_replay':record['independent_replay']}),flush=True)
        state.update(state='COMPLETE',updated_utc=b.now(),elapsed_seconds=time.monotonic()-start);b.atomic_json(STATE,state)
        return 0
    except Exception as error:
        state.update(state='PENDING_REVIEW_NO_FALLBACK',error=str(error),updated_utc=b.now(),elapsed_seconds=time.monotonic()-start);b.atomic_json(STATE,state)
        print(json.dumps({'queue_status':state['state'],'asset_key':state.get('asset_key'),'error':str(error)}),flush=True);return 2

if __name__=='__main__':
    with (HERE/'queue.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Another house queue controller is active')
        raise SystemExit(run())
