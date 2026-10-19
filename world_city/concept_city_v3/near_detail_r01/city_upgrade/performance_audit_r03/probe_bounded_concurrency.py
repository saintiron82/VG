"""Four immutable chunk replays: serial2 vs process-parallel2. No production writes."""
from pathlib import Path
import hashlib,json,subprocess,time,concurrent.futures,resource
H=Path(__file__).resolve().parent;U=H.parent;R=U.parents[3];tool=U/'house_rules/profile_completed_v3_chunk.py';stats=U/'house_rules/compiled/v3_r02/ordinary_r2_2b48237662aa54.layered.stats.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={str(p.relative_to(R)):sha(p)for p in [tool,stats,R/'voxel_character/common/core.py']}
def one(mode,n):
 out=H/f'{mode}_{n}.json';assert not out.exists();cmd=['python',str(tool),'--stats',str(stats),'--output',str(out),'--chunk-index','20'];start=time.perf_counter();p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,timeout=90);(H/f'{mode}_{n}.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
 d=json.loads(out.read_text());assert d['pass'];return {'wall_seconds':time.perf_counter()-start,'cpu_profiled_chunk_seconds':d['profiled_chunk_cpu_seconds'],'peak_rss_kib':d['max_rss_kib'],'process_address_space_cap_bytes':d['memory_limit_bytes'],'output_sha256':sha(out),'geometry_checks':d['checks']}
start=time.perf_counter();serial=[one('serial',n)for n in range(2)];serial_wall=time.perf_counter()-start
start=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:parallel=list(pool.map(lambda n:one('parallel',n),range(2)))
parallel_wall=time.perf_counter()-start
assert inputs=={p:sha(R/p)for p in inputs}
r={'schema':'riverstone.bounded_process_throughput_probe.v1','all_pass':True,'same_production_chunk_replays':4,'serial':serial,'parallel':parallel,'serial_pair_wall_seconds':serial_wall,'parallel_pair_wall_seconds':parallel_wall,'observed_pair_speedup':serial_wall/parallel_wall,'hard_address_space_sum_bytes':536870912,'peak_rss_sum_parallel_kib':sum(x['peak_rss_kib']for x in parallel),'protected_inputs':inputs,'environment':'Production single compiler and independent small workers may run concurrently; no GUI. Cgroup quota/RAM cap unavailable. Not a guaranteed dedicated2core allocation or full-city throughput.','scope':'Independent process execution only; no rendering/quality reduction or shared writable asset output. cProfile overhead included in both modes. Production concurrency not changed.'};(H/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ['all_pass','serial_pair_wall_seconds','parallel_pair_wall_seconds','observed_pair_speedup','peak_rss_sum_parallel_kib']}))
