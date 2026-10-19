"""Explicit two-house trial only; no automatic successor or final PASS publication.

The two workers retain normal primary/separate-secondary compile leases. This
coordinator holds both existing queue leases, preserves every checkpoint, and
records current/peak child RSS. Later solo continuation requires its own exact
scheduler ledger and uses the same immutable engine/checkpoint recipe.
"""
import argparse,fcntl,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
import adapter as a
import layered_compile_parallel_capacity_v4_r02 as layer
import compile_batch as batch
import render_only_qa
import replay_certificate_qa
import parallel_house_capacity_guard_v2 as guard
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
    expected={'asset_key':job['asset_key'],'source_sha256':job['source_sha256'],'authored_master_sha256':job['emitted_master_sha256'],'core_sha256':a.sha(a.core.__file__),'sampler_sha256':a.sha(layer.prepared_sampling_v3.__file__),'engine_sha256':a.sha(layer.__file__),'output_directory':job['output_directory'],'resume_start':job['resume_start']}
    if identity!=expected:raise ValueError('Trial identity mismatch')
    return job,rules,contract

def hard_timeout(signum,frame):raise TimeoutError('Paired full-asset child hard limit900 seconds')

def worker(path):
    begun=time.monotonic();signal.signal(signal.SIGALRM,hard_timeout);signal.alarm(900)
    resource.setrlimit(resource.RLIMIT_AS,(704*1024**2,704*1024**2))
    job,rules,contract=validate_job(path)
    context={'contract_path':a.ROOT/job['inputs']['parallel_trial']['path'],'contract_sha256':job['inputs']['parallel_trial']['sha256'],'state_path':a.ROOT/job['trial_state_path'],'slot':job['trial_slot'],'worker_started_monotonic':begun}
    result=layer.run(job['asset_key'],a.ROOT/job['output_directory'],a.ROOT/job['inputs']['rules']['path'],a.ROOT/job['inputs']['catalog']['path'],True,a.ROOT/job['inputs']['checkpoint_policy']['path'],job['resume_start']>0,runtime_trial=context)
    signal.alarm(0)
    print(json.dumps({'worker_terminal':True,'asset_key':job['asset_key'],'result_status':result['status'],'wall_seconds':time.monotonic()-begun,'cpu_user_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime,'cpu_system_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_stime,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
    return 0 if result['status'].startswith('PASS') else (75 if result['status']=='PENDING_RESUMABLE_CHECKPOINT' else 76)

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
    key='parallel_house_capacity_r02:shared_snapshots';scopes=[{'directory':str(k.parent.relative_to(a.ROOT)),'prefix':k.name} for k in targets]
    book.reserve(key,scopes,sum(v.stat().st_size for v in targets.values())+262144,identity)
    with book.writer(key):
        for dst,src in targets.items():
            data=src.read_bytes();book.check(key,len(data)+65536)
            with dst.open('xb',buffering=0) as stream:stream.write(data);os.fsync(stream.fileno())
            if a.sha(dst)!=a.sha(src):raise ValueError('Snapshot copy mismatch')
        book.release(key,identity,'Exact replay dependencies published before both asset reservations; source bytes unchanged')

def finalize(job,entry,catalog,rules,output,begin):
    key=job['asset_key'];stats_path=output/(key+'.layered.stats.json');stats=a.load(stats_path)
    if not stats['status'].startswith('PASS'):raise ValueError('Cannot finalize incomplete sampling')
    expected={'layer_engine_sha256':a.sha(layer.__file__),'layer_rules_sha256':a.sha(rules),
              'input_catalog_sha256':a.sha(catalog),'source_master_sha256':entry['source_sha256'],
              'authored_master_sha256':entry['emitted_master_sha256']}
    if any(stats['compiled_header'][k]!=value for k,value in expected.items()):
        raise ValueError('Complete output belongs to a different explicit source/engine recipe')
    config=a.load(rules)['shared_output_reservation']
    book=ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/p for p in config['retained_roots']],
                         config['limit_bytes'],min_free_disk_bytes=config['min_free_disk_bytes'])
    reservation_key=stats['output_reservation']['key']
    def save(path,value,allow_update=False):
        if path.exists() and not allow_update:raise ValueError('Existing artifact preserved: '+str(path))
        data=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
        book.check(reservation_key,len(data)+65536)
        temporary=path.with_name(path.name+'.tmp')
        if temporary.exists():raise ValueError('Preserve an existing failed atomic write: '+str(temporary))
        with temporary.open('wb',buffering=0) as stream:stream.write(data);os.fsync(stream.fileno())
        os.replace(temporary,path)
    with book.writer(reservation_key):
        qa_path=output/(key+'.layered.qa.json');replay_path=output/(key+'.layered.replay.json')
        qa_tick=time.perf_counter()
        if not qa_path.exists():save(qa_path,render_only_qa.verify(stats_path,catalog))
        structural_qa_seconds=time.perf_counter()-qa_tick
        if not a.load(qa_path)['pass']:raise ValueError('Structural QA failed; evidence preserved')
        replay_tick=time.perf_counter()
        if not replay_path.exists():
            report=replay_certificate_qa.verify(stats_path)
            report['entrypoint_sha256']=a.sha(__file__);report['verifier_sha256']=a.sha(replay_certificate_qa.__file__)
            save(replay_path,report)
        independent_replay_seconds=time.perf_counter()-replay_tick
        if not a.load(replay_path)['pass']:raise ValueError('Independent reference replay failed; evidence preserved')
        master=layer.load_master(a.ROOT/entry['emitted_master_path'])
        source_master=layer.load_master(a.ROOT/entry['source_master_path'])
        if master['materials']!=source_master['materials']:raise ValueError('Original material definitions differ')
        source=layer.SpatialSource(master,.05,range_only=True)
        expected=layer.chunk_enumeration.enumerate_paint_chunks(source,stats['compiled_header']['grid_origin'],
                   stats['compiled_header']['chunk_edge_fine_cells'],a.core.EPS)
        edge=stats['compiled_header']['chunk_edge_fine_cells']
        expected={tuple(v//edge for v in low) for low in expected['owned_lows']}
        actual=[tuple(c['chunk']) for c in stats['chunks']]
        if len(actual)!=len(expected) or set(actual)!=expected:raise ValueError('Source-domain ownership coverage mismatch')
        record=batch.inspect_output(key,output)
        handoff={**entry,**record,'complete_authored_source_domain_coverage':True,
                 'source_bounds_analytic':{'min':source.bounds[0],'max':source.bounds[1]},
                 'compile_checks':{'all_source_domain_chunks_compiled':True,'original_native_bounds':True,
                    'all_chunk_exterior_face_match':stats['all_chunks_exact_exterior_face_match'],
                    'all_chunk_overlap_free':stats['all_chunks_overlap_free'],
                    'all_global_constraints_pass':all(c['pass'] for c in stats['constraints']),
                    'materials_preserved':True,'independent_replay_pass':True},
                 'source_operation_coverage':{'full_authored_master_immutable_plan':True,'shape_or_cut_crop':False,
                    'fine_plan_key':stats['prepared_plans']['fine']['plan_key'],
                    'original_shape_operations_retained':True},
                 'global_constraints':stats['constraints'],'baseline_structure_unchanged':True,'runtime_activation':False,
                 'sampling_backend':stats['sampling_backend'],'prepared_plans':stats['prepared_plans'],
                 'connected_frontier':stats['connected_frontier'],
                 'phase_measurements':{**stats['phase_measurements'],'structural_qa_seconds':structural_qa_seconds,'independent_original_core_replay_seconds':independent_replay_seconds},
                 'end_to_end_seconds':time.perf_counter()-begin,
                 'independent_replay_backend':'preserved original common core, complete unpruned authored master'}
        path=output/(key+'.layered.handoff.json');save(path,handoff)
        if job['kind']=='house':
            path=HERE/'compiled/selection_overrides.json';overrides=a.load(path)
            if key in overrides['assets']:raise ValueError('Existing selection override is immutable to this new-asset job')
            overrides['assets'][key]={'stats_path':record['stats_path'],'stats_sha256':record['stats_sha256'],
                'qa_path':str(qa_path.relative_to(a.ROOT)),'qa_sha256':a.sha(qa_path),
                'replay_path':str(replay_path.relative_to(a.ROOT)),'replay_sha256':a.sha(replay_path),
                'source_catalog_path':str(catalog.relative_to(a.ROOT)),'source_catalog_sha256':a.sha(catalog),
                'source_master_path':entry['source_master_path'],'source_master_sha256':entry['source_sha256'],
                'emitted_master_path':entry['emitted_master_path'],'emitted_master_sha256':entry['emitted_master_sha256'],
                'reason':'Explicit immutable prepared v3 full-domain sampling; all exterior/ownership gates and independent original-core replay passed.'}
            save(path,overrides,allow_update=True)
        else:
            path=output/'handoff_manifest.json';manifest=a.load(path) if path.exists() else {'schema':'riverstone.facility_roof.compiled_expansion.v1','assets':[]}
            if any(r['asset_key']==key for r in manifest['assets']):raise ValueError('Existing facility handoff must not be overwritten')
            manifest['assets'].append(handoff);manifest.update(updated_utc=batch.now(),retained_voxel_payload=False)
            save(path,manifest,allow_update=True)
        current=book.record(reservation_key)
        book.release(reservation_key,current['identity'],'Complete source domain, structural QA, independent preserved-core replay and handoff passed')
    print(json.dumps({'status':'PASS','asset_key':key,'compile_seconds':stats['elapsed_seconds'],
        'end_to_end_seconds':time.perf_counter()-begin,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'quads':stats['quads'],'files':stats['files'],'handoff':str((output/(key+'.layered.handoff.json')).relative_to(a.ROOT))}),flush=True)

def coordinator(paths,result_path):
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,704*1024**2))
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
        handoffs=[]
        resource.setrlimit(resource.RLIMIT_AS,(704*1024**2,704*1024**2))
        for job,code in zip(jobs,codes):
            if code==0:
                catalog=a.ROOT/job['inputs']['catalog']['path'];entry=next(v for v in a.load(catalog)['assets'] if v['asset_key']==job['asset_key']);output=a.ROOT/job['output_directory']
                finalize(job,entry,catalog,a.ROOT/job['inputs']['rules']['path'],output,begin)
                handoff=output/(job['asset_key']+'.layered.handoff.json');handoffs.append({'asset_key':job['asset_key'],'path':str(handoff.relative_to(a.ROOT)),'sha256':a.sha(handoff)})
        result={'schema':'riverstone.two_house_capacity.result.v1','status':'PASS_COMPLETE_PAIR' if len(handoffs)==2 else 'PENDING_PAIR_WITH_PRESERVED_RESULTS',
            'global_constraints_pass':len(handoffs)==2,'runtime_activation':False,'complete_assets':len(handoffs),'handoffs':handoffs,'coordinator_wall_seconds':time.monotonic()-begin,'child_returncodes':codes,'barrier_released':released,'observed_combined_child_rss_peak_bytes':peak_pair,'rss_observations':observations,'rss_observation_interval_seconds':.1,
            'contract_path':jobs[0]['inputs']['parallel_trial']['path'],'contract_sha256':jobs[0]['inputs']['parallel_trial']['sha256'],'state_path':str(state_path.relative_to(a.ROOT)),'state_sha256':a.sha(state_path),'state':state,
            'jobs':[{'path':str(Path(p).relative_to(a.ROOT)),'sha256':a.sha(p)} for p in paths],
            'independent_original_core_replay':'Each completed asset passes four original-core chunks before handoff','automatic_successor':False,'later_resume_requires_new_execution_contract_and_same_source_engine_checkpoint_identity':True}
        if result_path.exists():raise ValueError('Prior result preserved')
        a.write(result_path,result);print(json.dumps({k:v for k,v in result.items() if k not in ('state','jobs')}),flush=True)
        return 0 if result['status']=='PASS_COMPLETE_PAIR' else 2
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
