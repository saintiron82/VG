"""Compare serial versus two processes on two small unsampled roof regions."""
import hashlib,json,os,pathlib,resource,signal,subprocess,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
def timeout(*args):raise TimeoutError('30 second process budget')
signal.signal(signal.SIGALRM,timeout);signal.alarm(30)
if '--worker' in sys.argv:
 from voxel_character.common import core
 master=json.loads(pathlib.Path(sys.argv[2]).read_text());bounds=json.loads(sys.argv[3]);target=pathlib.Path(sys.argv[4]);repeat=int(sys.argv[5]);start=time.perf_counter();cpu=time.process_time();hashes=[];candidates=cells=0
 for _ in range(repeat):
  r=core.compile_master(master,{'pitch':.05},cell_bounds=bounds,max_candidate_cells=300000,max_output_cells=100000)
  hashes.append(r['payload_hash']);candidates+=r['candidate_cells'];cells+=len(r['cells'])
 assert len(set(hashes))==1
 out={'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'repeat':repeat,'candidates':candidates,'cells':cells,'payload_hash':hashes[0]};target.write_text(json.dumps(out));print(json.dumps(out));sys.exit(0)
sys.path.insert(0,str(HERE.parent/'house_rules'));import layered_compile as layer
selection=json.loads((HERE/'selection.json').read_text());m=layer.load_master(ROOT/selection['source_path']);source=layer.SpatialSource(m,.05,range_only=True);origin=m.get('grid_origin',[0,0,0]);b={'min':[15,235,25],'max':[45,265,55]};lo=[origin[j]+b['min'][j]*.05 for j in range(3)];hi=[origin[j]+b['max'][j]*.05 for j in range(3)];(HERE/'bounded_master_b.json').write_text(json.dumps(source.bounded_master(lo,hi),separators=(',',':')))
jobs=[(HERE/'bounded_master.json',selection['bounds']),(HERE/'bounded_master_b.json',b)];env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
def cmd(n,tag):return [sys.executable,str(__file__),'--worker',str(jobs[n][0]),json.dumps(jobs[n][1]),str(HERE/f'{tag}_{n}.json'),'7']
start=time.perf_counter()
for n in range(2):subprocess.run(cmd(n,'serial'),env=env,stdout=subprocess.DEVNULL,check=True,timeout=30)
serial_wall=time.perf_counter()-start
start=time.perf_counter();children=[subprocess.Popen(cmd(n,'parallel'),env=env,stdout=subprocess.DEVNULL) for n in range(2)];peak=0
while any(p.poll() is None for p in children):
 rss=0
 for pid in [os.getpid()]+[p.pid for p in children]:
  try:
   for line in pathlib.Path(f'/proc/{pid}/status').read_text().splitlines():
    if line.startswith('VmRSS:'):rss+=int(line.split()[1])
  except FileNotFoundError:pass
 peak=max(peak,rss)
 if rss>1024**2:
  for p in children:p.terminate()
  raise RuntimeError('Aggregate RSS exceeded 1 GiB')
 time.sleep(.02)
parallel_wall=time.perf_counter()-start
assert all(p.returncode==0 for p in children),[p.returncode for p in children]
serial=[json.loads((HERE/f'serial_{n}.json').read_text()) for n in range(2)];parallel=[json.loads((HERE/f'parallel_{n}.json').read_text()) for n in range(2)]
assert all(serial[n]['payload_hash']==parallel[n]['payload_hash'] for n in range(2))
report={'serial_wall_seconds':serial_wall,'parallel_wall_seconds':parallel_wall,'aggregate_speedup':serial_wall/parallel_wall,'serial_workers':serial,'parallel_workers':parallel,'sampled_peak_aggregate_rss_kib_including_coordinator':peak,'two_process_effective_cpu_usage':sum(x['cpu_seconds'] for x in parallel)/parallel_wall,'total_audit_directory_bytes':sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()),'affinity_cpu_count':len(os.sched_getaffinity(0)),'scope':'two independent small unsampled roof regions; no shared queue lock changed; outputs are benchmark metrics only'}
(HERE/'concurrency.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));signal.alarm(0)
