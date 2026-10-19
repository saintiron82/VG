"""Explicit two-house trial only; no automatic successor or final PASS publication.

The two workers retain normal primary/separate-secondary compile leases. This
coordinator holds both existing queue leases, preserves every checkpoint, and
records current/peak child RSS. Later solo continuation requires its own exact
scheduler ledger and uses the same immutable engine/checkpoint recipe.
"""
import argparse,fcntl,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
import adapter as a
import layered_compile_parallel_trial_v4_r01 as layer
import parallel_house_trial_guard_v1 as guard
from output_reservations_v3 import ReservationBook
HERE=Path(__file__).resolve().parent

def validate_job(path):
    job=a.load(path)
    if job['schema']!='riverstone.reserved_asset_job.v3' or job['kind']!='house':raise ValueError('Explicit house job required')
    for group in ('inputs','tools'):
        for role,row in job[group].items():
            if a.sha(a.ROOT/row['path'])!=row['sha256']:raise ValueError('Pinned '+role+' changed')
    if job['tools']['engine']['sha256']!=a.sha(layer.__file__) or job['tools']['runner']['sha256']!=a.sha(__file__):raise ValueError('Wrong runner/engine')
    rules=a.load(a.ROOT/job['inputs']['rules']['path']);baseline=a.load(HERE/'layer_rules.v1.json')
    for field,value in baseline.items():
        if field not in ('memory_limit_bytes','total_output_budget_bytes') and rules.get(field)!=value:raise ValueError('Geometry rules changed '+field)
    if rules['memory_limit_bytes']!=704*1024**2 or rules['total_output_budget_bytes']!=350000000:raise ValueError('Process/shared limits changed')
    published=a.load(HERE/'shared_output_budget.v2.json');config=rules['shared_output_reservation']
    for field in ('book_path','retained_roots','limit_bytes','min_free_disk_bytes'):
        if config[field]!=published[field]:raise ValueError('Shared guard changed')
    if not 0<config['asset_cap_bytes']<=job['approved_asset_cap_bytes']:raise ValueError('Asset cap mismatch')
    catalog=a.load(a.ROOT/job['inputs']['catalog']['path']);entry=next(x for x in catalog['assets'] if x['asset_key']==job['asset_key'])
    for field,digest in (('source_master_path','source_sha256'),('emitted_master_path','emitted_master_sha256')):
        if entry[digest]!=job[digest] or a.sha(a.ROOT/entry[field])!=entry[digest]:raise ValueError('Master changed')
    output=(a.ROOT/job['output_directory']).resolve()
    if not output.is_relative_to((HERE/'compiled').resolve()):raise ValueError('Wrong output root')
    contract_path=a.ROOT/job['inputs']['parallel_trial']['path'];contract=a.load(contract_path);guard.validate_contract(contract)
    spec=contract['slots'][job['trial_slot']];identity=spec['identity']
    expected={'asset_key':job['asset_key'],'source_sha256':job['source_sha256'],'authored_master_sha256':job['emitted_master_sha256'],'core_sha256':a.sha(a.core.__file__),'sampler_sha256':a.sha(layer.prepared_sampling_v3.__file__),'engine_sha256':a.sha(layer.__file__),'output_directory':job['output_directory'],'resume_start':0}
    if identity!=expected:raise ValueError('Trial identity mismatch')
    return job,rules,contract

def hard_timeout(signum,frame):raise TimeoutError('Bounded two-house child hard limit 120 seconds')

def worker(path):
    begun=time.monotonic();signal.signal(signal.SIGALRM,hard_timeout);signal.alarm(120)
    resource.setrlimit(resource.RLIMIT_AS,(704*1024**2,704*1024**2))
    job,rules,contract=validate_job(path)
    context={'contract_path':a.ROOT/job['inputs']['parallel_trial']['path'],'contract_sha256':job['inputs']['parallel_trial']['sha256'],'state_path':a.ROOT/job['trial_state_path'],'slot':job['trial_slot'],'worker_started_monotonic':begun}
    result=layer.run(job['asset_key'],a.ROOT/job['output_directory'],a.ROOT/job['inputs']['rules']['path'],a.ROOT/job['inputs']['catalog']['path'],True,a.ROOT/job['inputs']['checkpoint_policy']['path'],False,runtime_trial=context)
    signal.alarm(0)
    print(json.dumps({'worker_terminal':True,'asset_key':job['asset_key'],'result_status':result['status'],'wall_seconds':time.monotonic()-begun,'cpu_user_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime,'cpu_system_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_stime,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
    return 75 if result['status']=='PENDING_RESUMABLE_CHECKPOINT' else 1

def snapshot_shared_dependencies(jobs):
    # Both jobs share code snapshots. Publish these once under one reservation
    # before either asset reserves them; avoid overlapping per-asset scopes.
    paths={'trial_guard':guard.__file__,'core':a.core.__file__,'engine':layer.__file__,'adapter':a.__file__,
        'bounded_surface_export':layer.bounded_surface_export_v1.__file__,'exact_sampling_v2':layer.exact_sampling_v2.__file__,'prepared_sampling_v3':layer.prepared_sampling_v3.__file__,'output_reservations_v3':layer.output_reservations_v3.__file__,
        'connected_constraints':layer.connected_constraints.__file__,'connected_frontier_v4':layer.connected_frontier_v4.__file__,'polygon_crop_guard':layer.polygon_crop_guard.__file__,
        'retention':layer.render_only_retention.__file__,'chunk_enumeration':layer.chunk_enumeration.__file__,
        'render_data':sys.modules[layer.make_render_data.__module__].__file__,'mesh':sys.modules['mesh'].__file__,'checkpoint_store':layer.checkpoint_store.__file__}
    targets={}
    for job in jobs:
        for role in ('rules','catalog','checkpoint_policy'):paths[role]=a.ROOT/job['inputs'][role]['path']
        for role,value in paths.items():
            src=Path(value);dst=HERE/'replay_code'/(role+'_'+a.sha(src)[:16]+src.suffix)
            if dst.exists():
                if a.sha(dst)!=a.sha(src):raise ValueError('Existing source snapshot changed')
            else:targets[dst]=src
    if not targets:return
    config=a.load(HERE/'shared_output_budget.v2.json');book=ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/p for p in config['retained_roots']],config['limit_bytes'],min_free_disk_bytes=config['min_free_disk_bytes'])
    identity={'schema':'riverstone.parallel_trial.shared_snapshots.v1','inputs':{str(k.relative_to(a.ROOT)):a.sha(v) for k,v in targets.items()}}
    key='parallel_house_trial_r01:shared_snapshots';scopes=[{'directory':str(k.parent.relative_to(a.ROOT)),'prefix':k.name} for k in targets]
    book.reserve(key,scopes,sum(v.stat().st_size for v in targets.values())+262144,identity)
    with book.writer(key):
        for dst,src in targets.items():
            data=src.read_bytes();book.check(key,len(data)+65536)
            with dst.open('xb',buffering=0) as stream:stream.write(data);os.fsync(stream.fileno())
            if a.sha(dst)!=a.sha(src):raise ValueError('Snapshot copy mismatch')
        book.release(key,identity,'Exact replay dependencies published before both asset reservations; source bytes unchanged')

def coordinator(paths,result_path):
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2))
    begin=time.monotonic();jobs=[validate_job(p)[0] for p in paths]
    if len(jobs)!=2 or {j['trial_slot'] for j in jobs}!={'primary','secondary'}:raise ValueError('Exactly two distinct slots required')
    if len({j['inputs']['parallel_trial']['sha256'] for j in jobs})!=1 or len({j['trial_state_path'] for j in jobs})!=1:raise ValueError('Pair contract mismatch')
    contract=a.load(a.ROOT/jobs[0]['inputs']['parallel_trial']['path']);state_path=a.ROOT/jobs[0]['trial_state_path']
    leases=[];children=[];logs=[];peak_pair=0;observations=0;released=False
    try:
        for name in ('queue.lock','queue_secondary_slot1.lock'):
            handle=(HERE/name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);leases.append(handle)
        snapshot_shared_dependencies(jobs)
        trial=guard.TrialGuard(state_path,contract).create()
        for path,job in zip(paths,jobs):
            logdir=a.ROOT/job['log_directory'];logdir.mkdir(parents=True,exist_ok=True);log=(logdir/(job['asset_key']+'.trial.log')).open('x');logs.append(log)
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--job',str(path)],cwd=a.ROOT,stdout=log,stderr=subprocess.STDOUT)
            children.append(child)
        while any(p.poll() is None for p in children):
            state=a.load(state_path)
            if not released and len(state['slots'])==2:
                trial.release_barrier();released=True
            total=0
            for child in children:
                if child.poll() is None:
                    try:total+=guard.peer_rss(child.pid) or 0
                    except guard.GuardError:pass
            peak_pair=max(peak_pair,total);observations+=1
            time.sleep(.1)
        for log in logs:log.flush()
        state=a.load(state_path);codes=[p.returncode for p in children]
        result={'schema':'riverstone.two_house_bounded_trial.result.v1','status':'PASS_BOUNDED_PREFIX' if codes==[75,75] and state['phase']=='CLOSED' else 'PENDING_PROBE_FAILURE_PRESERVED',
            'global_constraints_pass':False,'runtime_activation':False,'complete_assets':0,'coordinator_wall_seconds':time.monotonic()-begin,'child_returncodes':codes,'barrier_released':released,'observed_combined_child_rss_peak_bytes':peak_pair,'rss_observations':observations,'rss_observation_interval_seconds':.1,
            'contract_path':jobs[0]['inputs']['parallel_trial']['path'],'contract_sha256':jobs[0]['inputs']['parallel_trial']['sha256'],'state_path':str(state_path.relative_to(a.ROOT)),'state_sha256':a.sha(state_path),'state':state,
            'jobs':[{'path':str(Path(p).relative_to(a.ROOT)),'sha256':a.sha(p)} for p in paths],
            'independent_original_core_replay':'PENDING_SEPARATE_BOUNDED_REPLAY','automatic_successor':False,'later_solo_requires_explicit_checkpoint_identity_and_primary_compile_lock':True}
        if result_path.exists():raise ValueError('Prior result preserved')
        a.write(result_path,result);print(json.dumps({k:v for k,v in result.items() if k not in ('state','jobs')}),flush=True)
        return 0 if result['status']=='PASS_BOUNDED_PREFIX' else 2
    finally:
        for log in logs:log.close()
        for handle in reversed(leases):fcntl.flock(handle,fcntl.LOCK_UN);handle.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--worker',action='store_true');p.add_argument('--job',type=Path,action='append',required=True);p.add_argument('--result',type=Path);x=p.parse_args()
    if x.worker:
        if len(x.job)!=1:raise ValueError('One job per worker')
        raise SystemExit(worker(x.job[0].resolve()))
    if x.result is None:raise ValueError('Result path required')
    raise SystemExit(coordinator([v.resolve() for v in x.job],x.result.resolve()))
