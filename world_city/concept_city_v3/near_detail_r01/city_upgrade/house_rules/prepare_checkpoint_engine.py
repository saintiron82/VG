"""Prepare checkpoint integration; apply only between production processes."""
from pathlib import Path
import argparse

HERE=Path(__file__).resolve().parent

def build(source):
    if 'import checkpoint_store\n' in source:raise ValueError('Checkpoint integration already present')
    source=source.replace('import chunk_enumeration\n','import chunk_enumeration\nimport checkpoint_store\n')
    source=source.replace('def run(asset_key,output_dir=None,rules_path=None,catalog_path=None,render_only=False):',
        'def run(asset_key,output_dir=None,rules_path=None,catalog_path=None,render_only=False,checkpoint_policy_path=None,resume_checkpoint=False):')
    source=source.replace("    wall_limit=rules.get('wall_time_limit_seconds',900)","""    policy_path=Path(checkpoint_policy_path or HERE/'checkpoint_policy.v1.json').resolve()
    policy=a.load(policy_path) if policy_path.exists() else {}
    checkpoint_enabled=render_only and asset_key in policy.get('enabled_asset_keys',[])
    a.fail(not resume_checkpoint or checkpoint_enabled,'checkpoint_resume_not_enabled')
    if checkpoint_enabled:
        a.fail(policy.get('max_sessions')==2 and policy.get('per_session_wall_seconds')==900 and
            0<policy.get('soft_stop_seconds',0)<=840,'checkpoint_policy_limit_contract')
    wall_limit=rules.get('wall_time_limit_seconds',900)
    a.fail(not checkpoint_enabled or wall_limit==900,'checkpoint_session_wall_limit_contract')""")
    source=source.replace("    protected=list(paths.values())+list(partial.values())+[progress_path,output/(asset_key+'.layered.blocked.json')]",
        "    protected=list(paths.values())+list(partial.values())+([] if resume_checkpoint else [progress_path,output/(asset_key+'.layered.blocked.json')])")
    source=source.replace("    header['chunk_enumeration']=chunk_plan", """    header['chunk_enumeration']=chunk_plan
    header['checkpoint_store_sha256']=a.sha(checkpoint_store.__file__)
    if policy_path.exists():header['checkpoint_policy_sha256']=a.sha(policy_path)""")
    source=source.replace("    previous_alarm=signal.signal(signal.SIGALRM,time_limit);signal.alarm(wall_limit)\n    try:\n", """    previous_alarm=signal.signal(signal.SIGALRM,time_limit);signal.alarm(wall_limit)
    checkpoint=None;resume_start=0;prior_elapsed=0.;sessions_started=1;execution_ledger=None;ledger_path=None;session_registered=False
    try:
        if checkpoint_enabled:
            checkpoint_path=output/(asset_key+'.layered.checkpoint')
            a.fail(checkpoint_path.exists()==resume_checkpoint,'checkpoint_explicit_resume_required')
            identity={'schema':'riverstone.house_detail.checkpoint_identity.v1','header':header,'owned_lows':[list(v) for v in owned_lows],
                'policy':policy,'helper_sha256':a.sha(checkpoint_store.__file__),
                'source_paths':{'master':str(master_path.relative_to(a.ROOT)),'source':str(source_path.relative_to(a.ROOT)),
                    'catalog':str(catalog_path.relative_to(a.ROOT)),'rules':str(rules_path.relative_to(a.ROOT))}}
            if not resume_checkpoint:reserve_bytes(len(encoded_json(identity))+16384)
            checkpoint=checkpoint_store.Store(checkpoint_path,identity)
            ledger_path=output/(asset_key+'.layered.checkpoint_sessions.json')
            execution_ledger=a.load(ledger_path) if ledger_path.exists() else {'identity_digest':checkpoint.identity_digest,'sessions':[]}
            a.fail(execution_ledger['identity_digest']==checkpoint.identity_digest,'checkpoint_session_identity_mismatch')
            a.fail(len(execution_ledger['sessions'])<policy['max_sessions'],'checkpoint_total_session_limit')
            a.fail(bool(execution_ledger['sessions'])==resume_checkpoint,'checkpoint_session_history_mismatch')
            sessions_started=len(execution_ledger['sessions'])+1
            execution_ledger['sessions'].append({'session':sessions_started,'started_epoch_seconds':time.time(),
                'wall_limit_seconds':wall_limit,'status':'RUNNING','resumed':resume_checkpoint})
            commit_progress(ledger_path,execution_ledger)
            session_registered=True
            if resume_checkpoint:
                saved=checkpoint.load_state();resume_start=checkpoint.completed_count
                a.fail(saved is not None and 0<resume_start<=chunk_count,'checkpoint_empty_or_invalid_resume')
                a.fail(saved['sessions_started']<sessions_started,'checkpoint_saved_session_mismatch')
                prior_elapsed=saved['elapsed_seconds']
                for number,saved_record in enumerate(checkpoint.load_records()):
                    summary=saved_record['chunk_stats']
                    a.fail(summary['chunk']==[v//edge for v in owned_lows[number]],'checkpoint_chunk_order_mismatch')
                    a.fail(summary['quads']==len(saved_record['quads']),'checkpoint_quad_count_mismatch')
                    chunk_stats.append(summary)
                    for material,quad in saved_record['quads']:groups[material].append(quad)
                for target,values in ((all_fp,saved['all_fingerprint']),(face_fp,saved['face_fingerprint'])):
                    target.count=values['count'];target.xor=int(values['xor256'],16);target.sum=int(values['sum256'],16)
                total_fine=saved['total_fine'];total_core=saved['total_core'];candidate_total=saved['candidate_total']
                mins=saved['mins'] if saved['mins'] is not None else [math.inf]*3
                maxs=saved['maxs'] if saved['maxs'] is not None else [-math.inf]*3
                constraints=Counter(saved['constraints'])
                a.fail(set(saved['connected'])==set(connected),'checkpoint_constraint_set_mismatch')
                connected={key:checkpoint_store.restore_connected(value) for key,value in saved['connected'].items()}
                replayed_occupancy=Fingerprint()
                for summary in chunk_stats:
                    values=summary['full_fine_fingerprint'];part=Fingerprint()
                    part.count=values['count'];part.xor=int(values['xor256'],16);part.sum=int(values['sum256'],16)
                    replayed_occupancy.merge(part)
                a.fail(all_fp.value()==replayed_occupancy.value(),'checkpoint_occupancy_certificate_aggregate_mismatch')
                a.fail(candidate_total==sum(r['near_candidate_cells']+r['core_candidate_cells'] for r in chunk_stats),'checkpoint_candidate_count_mismatch')
                a.fail(all_fp.count==sum(r['reference_owned_fine_cells'] for r in chunk_stats) and
                    face_fp.count==sum(r['visible_unit_faces'] for r in chunk_stats) and
                    total_fine==sum(r['stored_fine_cells'] for r in chunk_stats) and
                    total_core==sum(r['stored_core_cells'] for r in chunk_stats),'checkpoint_accumulated_count_mismatch')
                progress={'schema':'riverstone.house_detail.chunk_progress.v1','asset_key':asset_key,'status':'RESUMED',
                    'completed':resume_start,'chunks':chunk_count,'stored_fine':total_fine,'stored_core':total_core,
                    'fine_equivalent_cells':all_fp.count,'quads':sum(len(g) for g in groups.values()),'visible_unit_faces':face_fp.count,
                    'seconds':prior_elapsed,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
""")
    source=source.replace("            for number,lo in enumerate(owned_lows):\n                tick=time.perf_counter();lo=list(lo);hi=[x+edge for x in lo]", """            for number,lo in enumerate(owned_lows):
                if number<resume_start:continue
                if checkpoint_enabled and (time.perf_counter()-start>=policy['soft_stop_seconds'] or
                    (policy.get('fixture_stop_after_chunks') and number-resume_start>=policy['fixture_stop_after_chunks'])):
                    report={'schema':'riverstone.house_detail.resumable_checkpoint.v1','status':'PENDING_RESUMABLE_CHECKPOINT' if sessions_started<policy['max_sessions'] else 'PENDING_CHECKPOINT_SESSION_LIMIT','asset_key':asset_key,
                        'completed_chunks':checkpoint.completed_count,'total_chunks':chunk_count,'session':sessions_started,
                        'session_elapsed_seconds':time.perf_counter()-start,'max_sessions':policy['max_sessions'],
                        'total_wall_budget_seconds':policy['max_sessions']*policy['per_session_wall_seconds'],
                        'checkpoint_directory':str(checkpoint_path.relative_to(a.ROOT)),
                        'checkpoint_manifest_sha256':a.sha(checkpoint.manifest_path),'source_and_recipe_unchanged':True,
                        'resampling_completed_chunks_required':False,'retained_cell_payload':False}
                    execution_ledger['sessions'][-1].update(status=report['status'],elapsed_seconds=time.perf_counter()-start,
                        completed_chunks=checkpoint.completed_count)
                    commit_progress(ledger_path,execution_ledger)
                    commit_progress(output/(asset_key+'.layered.resumable.json'),report)
                    progress.update(status=report['status'],session=sessions_started)
                    commit_progress(progress_path,progress);print(json.dumps(report),flush=True);return report
                tick=time.perf_counter();lo=list(lo);hi=[x+edge for x in lo]""")
    needle="                commit_progress(progress_path,progress)\n                if number%10==0"
    replacement="""                if checkpoint_enabled:
                    saved={'all_fingerprint':all_fp.value(),'face_fingerprint':face_fp.value(),'total_fine':total_fine,'total_core':total_core,
                        'candidate_total':candidate_total,'mins':mins if all_fp.count else None,'maxs':maxs if all_fp.count else None,
                        'constraints':dict(constraints),'connected':{key:checkpoint_store.serialize_connected(value) for key,value in connected.items()},
                        'sessions_started':sessions_started,'elapsed_seconds':prior_elapsed+time.perf_counter()-start}
                    checkpoint.append(number,{'chunk_stats':chunk_stats[-1],'quads':[[material,quad] for material,quad in quads]},saved,
                        budget_check=reserve_bytes)
                    progress.update(checkpoint_committed_chunks=checkpoint.completed_count,checkpoint_manifest_sha256=a.sha(checkpoint.manifest_path),session=sessions_started)
                commit_progress(progress_path,progress)
                if number%10==0"""
    assert needle in source;source=source.replace(needle,replacement)
    source=source.replace("'elapsed_seconds':time.perf_counter()-start,'authoring_seed'", "'elapsed_seconds':prior_elapsed+time.perf_counter()-start,'authoring_seed'")
    source=source.replace("        if render_only:\n            stats['compiled_header']=header", """        if checkpoint_enabled:
            execution_ledger['sessions'][-1].update(status='COMPLETED_SAMPLING',elapsed_seconds=time.perf_counter()-start,completed_chunks=checkpoint.completed_count)
            commit_progress(ledger_path,execution_ledger)
            stats['checkpoint']={'directory':str(checkpoint_path.relative_to(a.ROOT)),'committed_chunks':checkpoint.completed_count,
                'resumed_chunks':resume_start,'sessions_started':sessions_started,'max_sessions':policy['max_sessions'],
                'per_session_wall_seconds':wall_limit,'max_total_execution_budget_seconds':policy['max_sessions']*wall_limit,
                'retained_cell_arrays':False,'completed_checkpoints_preserved':True,'policy_sha256':a.sha(policy_path),
                'elapsed_scope':'Sum of prior committed checkpoint time and current execution; interrupted incomplete work is excluded.',
                'execution_ledger_path':str(ledger_path.relative_to(a.ROOT)),'execution_records':copy.deepcopy(execution_ledger['sessions'])}
        if render_only:
            stats['compiled_header']=header""")
    source=source.replace("'rules':rules_path,'catalog':catalog_path})", "'rules':rules_path,'catalog':catalog_path,'checkpoint_store':checkpoint_store.__file__,**({'checkpoint_policy':policy_path} if policy_path.exists() else {})})")
    source=source.replace("        progress.update(status='COMPLETE',stats_path=str(paths['.stats.json'].relative_to(a.ROOT)),stats_sha256=a.sha(paths['.stats.json']))", """        if checkpoint_enabled:
            checkpoint.mark_complete(paths['.stats.json'],a.sha(paths['.stats.json']))
            execution_ledger['sessions'][-1].update(status='COMPLETE',elapsed_seconds=time.perf_counter()-start,
                final_stats_path=str(paths['.stats.json'].relative_to(a.ROOT)),final_stats_sha256=a.sha(paths['.stats.json']))
            commit_progress(ledger_path,execution_ledger)
        progress.update(status='COMPLETE',stats_path=str(paths['.stats.json'].relative_to(a.ROOT)),stats_sha256=a.sha(paths['.stats.json']),
            seconds=stats['elapsed_seconds'],max_rss_kib=stats['max_rss_kib'])""")
    source=source.replace("        a.write(output/(asset_key+'.layered.blocked.json'),report)", """        failure_path=output/(asset_key+'.layered.blocked.json')
        suffix=1
        while failure_path.exists():
            suffix+=1;failure_path=output/(asset_key+'.layered.blocked.resume_'+str(suffix)+'.json')
        a.write(failure_path,report)
        if session_registered:
            execution_ledger['sessions'][-1].update(status='FAILED_PRESERVED',elapsed_seconds=time.perf_counter()-start,
                failure_path=str(failure_path.relative_to(a.ROOT)))
            commit_progress(ledger_path,execution_ledger)""")
    source=source.replace("    args=parser.parse_args();run(args.asset_key,args.output_dir,args.rules,args.catalog,args.render_only)", """    parser.add_argument('--checkpoint-policy',type=Path);parser.add_argument('--resume-checkpoint',action='store_true')
    args=parser.parse_args();result=run(args.asset_key,args.output_dir,args.rules,args.catalog,args.render_only,args.checkpoint_policy,args.resume_checkpoint)
    if result.get('status')=='PENDING_RESUMABLE_CHECKPOINT':raise SystemExit(75)
    if result.get('status')=='PENDING_CHECKPOINT_SESSION_LIMIT':raise SystemExit(76)""")
    source=source.replace("    header['checkpoint_store_sha256']=a.sha(checkpoint_store.__file__)","""    replay_paths={'core':a.core.__file__,'engine':__file__,'adapter':a.__file__,
        'connected_constraints':connected_constraints.__file__,'polygon_crop_guard':polygon_crop_guard.__file__,
        'retention':render_only_retention.__file__,'chunk_enumeration':chunk_enumeration.__file__,
        'render_data':sys.modules[make_render_data.__module__].__file__,'mesh':sys.modules['mesh'].__file__,
        'rules':rules_path,'catalog':catalog_path,'checkpoint_store':checkpoint_store.__file__,
        **({'checkpoint_policy':policy_path} if policy_path.exists() else {})}
    header['replay_dependency_hashes']={key:a.sha(path) for key,path in replay_paths.items()}
    header['checkpoint_store_sha256']=a.sha(checkpoint_store.__file__)
    def reserve_bytes(additional,emergency=False):
        current=sum(p.stat().st_size for root in budget_roots for p in root.rglob('*') if p.is_file())
        current+=sum(p.stat().st_size for p in (HERE/'replay_code').rglob('*') if p.is_file())
        a.fail(current+additional+(0 if emergency else 65536)<=rules['total_output_budget_bytes'],
            'layer_prewrite_budget_exceeded',{'current':current,'additional_peak_bytes':additional,'limit':rules['total_output_budget_bytes']})
    def encoded_json(value):
        return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\\n').encode('utf-8')
    def commit_checked(path,value,emergency=False):
        payload=encoded_json(value);reserve_bytes(len(payload),emergency)
        temporary=path.with_name(path.name+'.tmp')
        with temporary.open('wb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory_fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)
    class BudgetedWriter:
        def __init__(self,raw):self.raw=raw
        def write(self,data):reserve_bytes(len(data));return self.raw.write(data)
        def flush(self):return self.raw.flush()
        def tell(self):return self.raw.tell()""")
    source=source.replace('commit_progress(ledger_path,execution_ledger)','commit_checked(ledger_path,execution_ledger)')
    source=source.replace('commit_progress(progress_path,progress)','commit_checked(progress_path,progress)')
    source=source.replace("commit_progress(output/(asset_key+'.layered.resumable.json'),report)","commit_checked(output/(asset_key+'.layered.resumable.json'),report)")
    source=source.replace("        a.fail(header['compiler_source_sha256']==a.sha(a.core.__file__),'common_source_changed_during_run')", """        a.fail(header['compiler_source_sha256']==a.sha(a.core.__file__),'common_source_changed_during_run')
        a.fail(header['replay_dependency_hashes']=={key:a.sha(path) for key,path in replay_paths.items()},'replay_dependency_changed_during_run')
        a.fail(a.sha(master_path)==header['authored_master_sha256'],'authored_master_changed_during_run')
        a.fail(a.sha(source_path)==header['source_master_sha256'],'original_source_changed_during_run')""")
    source=source.replace("with partial['.render.json'].open('wb') as raw:","with partial['.render.json'].open('wb',buffering=0) as raw:")
    source=source.replace("fileobj=raw,mtime=0,compresslevel=5","fileobj=BudgetedWriter(raw),mtime=0,compresslevel=5")
    begin="            stats['replay_contract']=render_only_retention.preserve_replay_sources("
    start=source.index(begin);end=source.index('\n        for key in active_file_keys:',start)
    source=source[:start]+"""            snapshot_growth=0
            for role,path in replay_paths.items():
                path=Path(path);snapshot=HERE/'replay_code'/(role+'_'+a.sha(path)[:16]+path.suffix)
                if not snapshot.exists():snapshot_growth+=path.stat().st_size
            reserve_bytes(snapshot_growth)
            stats['replay_contract']=render_only_retention.preserve_replay_sources(a,HERE,asset_key,master_path,source_path,catalog_path,rules_path,replay_paths)
            if checkpoint_enabled:
                stats['replay_contract']['command'].extend(['--checkpoint-policy',str(policy_path.relative_to(a.ROOT))])
                stats['replay_contract']['checkpoint_resume']={'soft_exit_code':75,'resume_argument':'--resume-checkpoint',
                    'max_sessions':2,'per_session_wall_seconds':900,'soft_stop_seconds':policy['soft_stop_seconds']}
""".rstrip()+source[end:]
    source=source.replace("        a.write(partial['.stats.json'],stats)","        reserve_bytes(len(encoded_json(stats)));a.write(partial['.stats.json'],stats)")
    source=source.replace("checkpoint.mark_complete(paths['.stats.json'],a.sha(paths['.stats.json']))", "checkpoint.mark_complete(paths['.stats.json'],a.sha(paths['.stats.json']),budget_check=reserve_bytes)")
    source=source.replace('        a.write(failure_path,report)', '        reserve_bytes(len(encoded_json(report)),emergency=True);a.write(failure_path,report)')
    source=source.replace("            commit_checked(ledger_path,execution_ledger)\n        print(json.dumps(report)","            commit_checked(ledger_path,execution_ledger,emergency=True)\n        print(json.dumps(report)")
    source=source.replace("'completed_chunks':len(chunk_stats),'max_rss_kib'", "'completed_chunks':len(chunk_stats),'durable_checkpoint_chunks':checkpoint.completed_count if checkpoint else None,'max_rss_kib'")
    begin=source.index("                    report={'schema':'riverstone.house_detail.resumable_checkpoint.v1'")
    end=source.index('                tick=time.perf_counter()',begin)
    block=source[begin:end]
    source=source[:begin]+'                    return stop_checkpoint()\n'+source[end:]
    helper='    def stop_checkpoint():\n'+'\n'.join(line[12:] for line in block.rstrip().splitlines())+'\n'
    source=source.replace('    previous_alarm=signal.signal(signal.SIGALRM,time_limit);signal.alarm(wall_limit)',helper+'    previous_alarm=signal.signal(signal.SIGALRM,time_limit);signal.alarm(wall_limit)')
    source=source.replace("        a.fail(all_fp.count>0,'layer_no_visible_occupancy')", "        if checkpoint_enabled and time.perf_counter()-start>=policy['soft_stop_seconds']:return stop_checkpoint()\n        a.fail(all_fp.count>0,'layer_no_visible_occupancy')")
    source=source.replace("        with partial['.render.json'].open('wb',buffering=0) as raw:", "        if checkpoint_enabled and time.perf_counter()-start>=policy['soft_stop_seconds']:return stop_checkpoint()\n        with partial['.render.json'].open('wb',buffering=0) as raw:")
    return source

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');x=parser.parse_args()
    target=HERE/('layered_compile.py' if x.apply else 'checkpoint_candidate_engine.py')
    target.write_text(build((HERE/'layered_compile.py').read_text()))
    print(target)
