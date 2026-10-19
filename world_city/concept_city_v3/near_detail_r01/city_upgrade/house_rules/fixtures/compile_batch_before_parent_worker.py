"""Sequential bounded common compilation; commit an atomic status manifest per asset.

Does not activate city assets. Existing outputs are accepted only after their
recorded hashes and an independent layered QA report have been checked.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a
import checkpoint_queue


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def now():return datetime.now(timezone.utc).isoformat()


def inspect_output(key,output):
    stats_path=output/(key+'.layered.stats.json')
    overrides_path=output/'selection_overrides.json';override={}
    if overrides_path.exists():override=a.load(overrides_path).get('assets',{}).get(key,{})
    if override:
        stats_path=a.ROOT/override['stats_path']
        if a.sha(stats_path)!=override['stats_sha256']:raise ValueError('Selection override stats hash mismatch')
    if not stats_path.exists():return None
    stats=a.load(stats_path)
    for record in stats['files'].values():
        path=a.ROOT/record['path']
        if not path.exists() or a.sha(path)!=record['sha256'] or path.stat().st_size!=record['bytes']:
            raise ValueError('Recorded output hash or size mismatch: '+str(path))
    result={'status':stats['status'],'stats_path':str(stats_path.relative_to(a.ROOT)),
            'stats_sha256':a.sha(stats_path),'files':stats['files'],
            'source_master_sha256':stats['source_master_sha256'],'authored_master_sha256':stats['authored_master_sha256'],
            'reference_full_fine_cells':stats['reference_full_fine_cells'],
            'stored_fine_cells':stats['stored_fine_cells'],'stored_core_cells':stats['stored_core_cells'],
            'quads':stats['quads'],'visible_unit_faces':stats['visible_unit_faces'],
            'max_rss_kib':stats['max_rss_kib'],'elapsed_seconds':stats['elapsed_seconds'],
            'core_visible_faces':stats['core_visible_faces'],'chunks':len(stats['chunks']),
            'source_unchanged':stats['source_unchanged'],'full_building_cell_merge_created':False,
            'visual_status':'PENDING','city_runtime_activation':'PENDING'}
    qa_path=a.ROOT/override['qa_path'] if override else output/(key+'.layered.qa.json')
    if override and a.sha(qa_path)!=override['qa_sha256']:raise ValueError('Selection override QA hash mismatch')
    if qa_path.exists():
        qa=a.load(qa_path)
        result['independent_qa']={'path':str(qa_path.relative_to(a.ROOT)),'sha256':a.sha(qa_path),'pass':qa.get('pass',False)}
    replay_path=a.ROOT/override['replay_path'] if override.get('replay_path') else qa_path.with_name(key+'.layered.replay.json')
    if replay_path.exists():
        if override.get('replay_sha256') and a.sha(replay_path)!=override['replay_sha256']:raise ValueError('Selection override replay hash mismatch')
        replay=a.load(replay_path)
        result['independent_replay']={'path':str(replay_path.relative_to(a.ROOT)),'sha256':a.sha(replay_path),'pass':replay.get('pass',False),
            'sampled_chunks':replay.get('sampled_chunks'),'total_compiled_chunks':replay.get('total_compiled_chunks'),'scope':replay.get('scope')}
    result['storage_mode']=stats.get('storage_mode','retained_layered_cells')
    result['spatial_sampling_contract']=stats.get('spatial_sampling_contract','legacy_shape_crop')
    holds_path=output/'provenance_holds.json'
    hold=a.load(holds_path).get('assets',{}).get(key) if holds_path.exists() else None
    if hold and not override:
        result['geometry_status']=result['status'];result['status']=hold['status'];result['activation_blocked']=True
        result['provenance_hold']=hold
    elif override:result['selection_override']=override
    return result


def refresh_manifest(catalog_path,output,progress=None):
    catalog=a.load(catalog_path);assets=[]
    for entry in catalog['assets']:
        key=entry['asset_key'];record={'asset_key':key,'source_master_sha256':entry.get('source_sha256')}
        if not entry.get('emitted_master_path'):
            record.update(status='AUTHORING_COVERAGE_PENDING',authoring=entry.get('reason',entry.get('validation',entry.get('status'))))
        else:
            record.update(status='COMPILE_PENDING',authored_master_sha256=entry['emitted_master_sha256'])
            finished=inspect_output(key,output)
            if finished:record.update(finished)
        assets.append(record)
    manifest={'schema':'riverstone.house_detail.compiled_catalog.v1','updated_utc':now(),
        'catalog_path':str(catalog_path.relative_to(a.ROOT)),'catalog_sha256':a.sha(catalog_path),
        'memory_limit_bytes':1500000000,'total_output_budget_bytes':180000000,
        'per_asset_timeout_seconds':900,'single_heavy_compiler':True,
        'progress':progress or {},'assets':assets,
        'summary':{'supported':sum(bool(e.get('emitted_master_path')) for e in catalog['assets']),
        'compiled':sum(r['status'].startswith('PASS') for r in assets),
        'independently_checked':sum(r['status'].startswith('PASS') and r.get('independent_qa',{}).get('pass',False) for r in assets),
        'coverage_pending':sum(r['status']=='AUTHORING_COVERAGE_PENDING' for r in assets),
        'compiled_directory_bytes':sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
        'max_rss_kib':max([r.get('max_rss_kib',0) for r in assets],default=0)}}
    atomic_json(output/'manifest.json',manifest)
    return manifest


def run(keys,catalog_path,output,refresh_only=False,render_only=False):
    output=Path(output).resolve();catalog_path=Path(catalog_path).resolve()
    output.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();catalog=a.load(catalog_path)
    if not keys:keys=[r['asset_key'] for r in catalog['assets'] if r.get('emitted_master_path')]
    refresh_manifest(catalog_path,output)
    if refresh_only:return
    logs=HERE/'compile_logs'/output.name;logs.mkdir(parents=True,exist_ok=True)
    for index,key in enumerate(keys):
        progress={'state':'RUNNING','asset_key':key,'sequence':index+1,'count':len(keys),'elapsed_seconds':time.monotonic()-start}
        refresh_manifest(catalog_path,output,progress)
        existing=inspect_output(key,output)
        if existing and not existing['status'].startswith('PASS'):
            raise ValueError('Existing output is held; compile into a new directory and commit a verified selection override: '+key)
        if not existing:
            command=[sys.executable,str(HERE/'layered_compile.py'),key,'--catalog',str(catalog_path),'--output-dir',str(output)]
            if render_only:command.append('--render-only')
            execution=checkpoint_queue.execute(command,output,key,logs)
            if execution['state']!='COMPILE_COMPLETE':
                progress.update(execution)
                refresh_manifest(catalog_path,output,progress)
                print(json.dumps(progress),flush=True);return 2
        qa=output/(key+'.layered.qa.json')
        if not qa.exists():
            command=[sys.executable,str(HERE/'layered_qa.py'),'--layered-cells',str(output/(key+'.layered.cells.jsonl.gz')),
                     '--layered-render',str(output/(key+'.layered.render.json')),'--layered-stats',str(output/(key+'.layered.stats.json')),'--source-catalog',str(catalog_path),
                     '--output',str(qa.with_suffix('.json.pending'))]
            emitted_stats=a.load(output/(key+'.layered.stats.json'))
            if emitted_stats.get('storage_mode')=='render_only_transient_cells':
                command=[sys.executable,str(HERE/'render_only_qa.py'),'--stats',str(output/(key+'.layered.stats.json')),
                         '--source-catalog',str(catalog_path),'--output',str(qa.with_suffix('.json.pending'))]
            # If an independently authored full reference exists, use the stronger retained gate.
            elif (output/(key+'.cells.json.gz')).exists():
                command.extend(['--reference-cells',str(output/(key+'.cells.json.gz')),'--reference-render',str(output/(key+'.render.json'))])
            with (logs/(key+'.qa.log')).open('w') as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=900)
            if result.returncode or not a.load(qa.with_suffix('.json.pending')).get('pass'):
                progress.update(state='PENDING_INDEPENDENT_QA_FAILURE',returncode=result.returncode)
                refresh_manifest(catalog_path,output,progress)
                print(json.dumps(progress),flush=True);return 2
            os.replace(qa.with_suffix('.json.pending'),qa)
        record=inspect_output(key,output)
        if not record.get('independent_qa',{}).get('pass'):
            raise ValueError('Independent QA is not passing for '+key)
        progress.update(state='ASSET_COMPLETE',elapsed_seconds=time.monotonic()-start)
        manifest=refresh_manifest(catalog_path,output,progress)
        print(json.dumps({'asset_key':key,**record,'batch_summary':manifest['summary']}),flush=True)
    refresh_manifest(catalog_path,output,{'state':'REQUESTED_BATCH_COMPLETE','elapsed_seconds':time.monotonic()-start})
    return 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('keys',nargs='*');p.add_argument('--catalog',type=Path,default=HERE/'generated/active_catalog.json')
    p.add_argument('--output-dir',type=Path,default=HERE/'compiled');p.add_argument('--refresh-only',action='store_true');p.add_argument('--render-only',action='store_true')
    x=p.parse_args();raise SystemExit(run(x.keys,x.catalog,x.output_dir,refresh_only=x.refresh_only,render_only=x.render_only))
