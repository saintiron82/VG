"""Execute one hash-pinned new asset, then exact QA/replay; never select a successor.

The immutable JSON job is data, not another house-specific authoring engine.
A global queue lock and the engine's original compile lock remain authoritative.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import sys
import time

import adapter as a
import layered_compile_v3_r02 as layer
import compile_batch as batch
import checkpoint_queue
import render_only_qa
import replay_certificate_qa
from output_reservations_v3 import ReservationBook

HERE=Path(__file__).resolve().parent


def validated_job(path):
    path=Path(path).resolve();job=a.load(path)
    if job['schema']!='riverstone.reserved_asset_job.v3':raise ValueError('Unsupported explicit job contract')
    for role,row in job['inputs'].items():
        if a.sha(a.ROOT/row['path'])!=row['sha256']:raise ValueError('Pinned input changed: '+role)
    for role,row in job['tools'].items():
        if a.sha(a.ROOT/row['path'])!=row['sha256']:raise ValueError('Pinned tool changed: '+role)
    if job['tools']['engine']['sha256']!=a.sha(layer.__file__):raise ValueError('Job selects another engine')
    if job['tools']['runner']['sha256']!=a.sha(__file__):raise ValueError('Job selects another runner')
    catalog=a.ROOT/job['inputs']['catalog']['path'];rules=a.ROOT/job['inputs']['rules']['path']
    entry=next(r for r in a.load(catalog)['assets'] if r['asset_key']==job['asset_key'])
    if any(entry[k]!=job[k] for k in ('source_sha256','emitted_master_sha256')):raise ValueError('Job source selection changed')
    for field,sha in (('source_master_path','source_sha256'),('emitted_master_path','emitted_master_sha256')):
        if a.sha(a.ROOT/entry[field])!=entry[sha]:raise ValueError('Source/master bytes changed')
    output=(a.ROOT/job['output_directory']).resolve()
    allowed=[HERE/'compiled',HERE.parent/'facility_roofs/compiled_expansion_r01']
    if not any(output.is_relative_to(p.resolve()) for p in allowed):raise ValueError('Unapproved output root')
    if job['kind'] not in ('house','facility_roof'):raise ValueError('Unsupported asset kind')
    actual_rules=a.load(rules);baseline=a.load(HERE/'layer_rules.v1.json')
    for field,value in baseline.items():
        if field not in ('memory_limit_bytes','total_output_budget_bytes') and actual_rules.get(field)!=value:
            raise ValueError('Job cannot alter geometry/sampling rules: '+field)
    if actual_rules['memory_limit_bytes']!=738197504 or actual_rules['total_output_budget_bytes']!=350000000 or actual_rules.get('wall_time_limit_seconds',900)!=900:
        raise ValueError('Job must preserve the approved process/shared limits')
    config=actual_rules['shared_output_reservation'];published=a.load(HERE/'shared_output_budget.v2.json')
    for k in ('book_path','retained_roots','limit_bytes','min_free_disk_bytes'):
        if config[k]!=published[k]:raise ValueError('Shared budget mismatch: '+k)
    if not 0<config['asset_cap_bytes']<=job['approved_asset_cap_bytes']:raise ValueError('Per-asset cap mismatch')
    return job,entry,catalog,rules,output


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
        if not qa_path.exists():save(qa_path,render_only_qa.verify(stats_path,catalog))
        if not a.load(qa_path)['pass']:raise ValueError('Structural QA failed; evidence preserved')
        if not replay_path.exists():
            report=replay_certificate_qa.verify(stats_path)
            report['entrypoint_sha256']=a.sha(__file__);report['verifier_sha256']=a.sha(replay_certificate_qa.__file__)
            save(replay_path,report)
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


def run(path,worker=False,resume=False):
    begin=time.perf_counter();job,entry,catalog,rules,output=validated_job(path)
    _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=738197504 if hard==resource.RLIM_INFINITY else min(738197504,hard)
    resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    policy=a.ROOT/job['inputs']['checkpoint_policy']['path']
    if worker:
        result=layer.run(job['asset_key'],output,rules,catalog,True,policy,resume)
        return {'PENDING_RESUMABLE_CHECKPOINT':75,'PENDING_CHECKPOINT_SESSION_LIMIT':76}.get(result['status'],0)
    if resume:raise ValueError('Only the checkpoint manager may select a resume')
    with (HERE/'queue.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another full-asset controller owns the boundary')
        existing=output/(job['asset_key']+'.layered.stats.json')
        if not existing.exists():
            command=[sys.executable,str(Path(__file__).resolve()),'--job',str(Path(path).resolve()),'--worker']
            result=checkpoint_queue.execute(command,output,job['asset_key'],a.ROOT/job['log_directory'])
            if result['state']!='COMPILE_COMPLETE':print(json.dumps(result),flush=True);return 2
        finalize(job,entry,catalog,rules,output,begin)
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',required=True,type=Path)
    p.add_argument('--worker',action='store_true');p.add_argument('--resume-checkpoint',action='store_true')
    x=p.parse_args();raise SystemExit(run(x.job,x.worker,x.resume_checkpoint))
