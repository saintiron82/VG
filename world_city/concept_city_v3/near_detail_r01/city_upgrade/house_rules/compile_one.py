"""Bounded, serial unchanged-common-compiler execution for one authored asset.

Independent subprocess per asset. No pitch fallback, no compiler modifications.
"""
import argparse
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a
from voxel_character.common.render_data import make_render_data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset_key')
    parser.add_argument('--memory-bytes',type=int,default=1_500_000_000)
    parser.add_argument('--max-output-cells',type=int,default=2_000_000)
    parser.add_argument('--disk-budget-bytes',type=int,default=180_000_000)
    args=parser.parse_args()
    out=HERE/'compiled'
    out.mkdir(exist_ok=True)
    lock=(HERE/'compile.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('Another house compiler is active; no parallel heavy run allowed')
    resource.setrlimit(resource.RLIMIT_AS,(args.memory_bytes,args.memory_bytes))
    catalog=a.load(HERE/'generated/active_catalog.json')
    record=next((r for r in catalog['assets'] if r['asset_key']==args.asset_key),None)
    if not record or not record.get('emitted_master_path'):raise SystemExit('Asset has no approved structurally validated authored master')
    master_path=a.ROOT/record['emitted_master_path']
    if a.sha(master_path)!=record['emitted_master_sha256']:raise SystemExit('Master hash mismatch')
    source_path=a.ROOT/record['source_master_path']
    if a.sha(source_path)!=record['source_sha256']:raise SystemExit('Original source hash mismatch')
    paths={suffix:out/(args.asset_key+suffix) for suffix in ('.cells.json.gz','.render.json','.stats.json')}
    if any(p.exists() for p in paths.values()):raise SystemExit('Completed or previous output paths preserved; choose a separate explicit recovery step')
    temporary={k:p.with_suffix(p.suffix+'.partial') for k,p in paths.items()}
    if any(p.exists() for p in temporary.values()):raise SystemExit('Partial output exists; inspect before retry')
    used=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if used>args.disk_budget_bytes-20_000_000:raise SystemExit('Less than 20MB of authorized compile output budget remains')
    stats={'schema':'riverstone.house_detail.compile_stats.v1','status':'RUNNING','asset_key':args.asset_key,
           'source_master_sha256':record['source_sha256'],'authored_master_sha256':a.sha(master_path),
           'memory_limit_bytes':args.memory_bytes,'max_output_cells':args.max_output_cells,
           'pitch_m':.05,'compiler_source_sha256':a.sha(a.core.__file__),'compiler_changed':False,
           'geometry_fallback':False,'full_005':True}
    master=a.load(master_path)
    start=time.perf_counter()
    try:
        c=a.core.compile_master(master,{'pitch':.05},max_candidate_cells=record['near_005']['operation_aabb_candidate_cells']+1000,max_output_cells=args.max_output_cells)
        stats.update({'cells':len(c['cells']),'candidate_cells':c['candidate_cells'],'compile_seconds':time.perf_counter()-start,
                      'constraints':c['constraints'],'master_hash':c['master_hash'],'payload_hash':c['payload_hash']})
        print(json.dumps({'phase':'compiled','asset_key':args.asset_key,'cells':stats['cells'],'seconds':stats['compile_seconds']}),flush=True)
        if not c['valid']:raise ValueError('Common compiler semantic constraints failed')
        t=time.perf_counter()
        with gzip.open(temporary['.cells.json.gz'],'wt',encoding='utf-8',compresslevel=5) as f:
            json.dump(c,f,separators=(',',':'))
        stats['gzip_seconds']=time.perf_counter()-t
        t=time.perf_counter()
        render=make_render_data(c)
        with temporary['.render.json'].open('w') as f:
            json.dump(render,f,separators=(',',':'));f.write('\n')
        stats.update({'quads':render['quad_count'],'triangles':2*render['quad_count'],'bounds':render['bounds'],
                      'mesh_and_write_seconds':time.perf_counter()-t})
        output_size=temporary['.cells.json.gz'].stat().st_size+temporary['.render.json'].stat().st_size
        if used+output_size>args.disk_budget_bytes:raise ValueError('Authorized output disk budget exceeded; partial results are not activated')
        stats['max_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        stats['max_rss_bytes']=stats['max_rss_kib']*1024
        stats['status']='PASS'
        stats['files']={}
        for key in ('.cells.json.gz','.render.json'):
            temporary[key].rename(paths[key])
            stats['files'][key]={'path':str(paths[key].relative_to(a.ROOT)),'bytes':paths[key].stat().st_size,'sha256':a.sha(paths[key])}
        stats['source_unchanged']=a.sha(source_path)==record['source_sha256']
        stats['measurement_scope']='Cloud process peak including common compiler, gzip and generic greedy mesher; not runtime GPU/Windows FPS.'
        a.write(paths['.stats.json'],stats)
        print(json.dumps(stats),flush=True)
    except (MemoryError,a.core.BudgetExceeded,ValueError) as error:
        stats.update({'status':'BLOCKED_NO_FALLBACK','error':type(error).__name__,'reason':str(error),
                      'elapsed_seconds':time.perf_counter()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      'partial_files':[str(p.relative_to(a.ROOT)) for p in temporary.values() if p.exists()]})
        a.write(out/(args.asset_key+'.blocked.json'),stats)
        print(json.dumps(stats),flush=True)
        raise SystemExit(2)


if __name__=='__main__':main()
