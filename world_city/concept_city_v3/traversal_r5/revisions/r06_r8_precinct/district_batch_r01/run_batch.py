"""Run one bounded batch with the unmodified no-step controller."""
import pathlib,json,subprocess,os,time,resource,hashlib
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());prepared=H/'prepared_runtime.json';report=H/'evidence/district_replay.json';log=report.with_suffix('.log');metrics=H/'evidence/district_replay_metrics.json'
assert not any(p.exists()for p in[report,log,metrics])
d=json.loads(prepared.read_bytes())
for ref in d['sources'].values():assert hashlib.sha256(pathlib.Path(ref['path']).read_bytes()).hexdigest()==ref['sha256']
for p,h in d['implementation_hashes'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
assert(H/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes()
assert(H/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes()
env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1',XDG_CACHE_HOME=str(H/'.runtime/cache'),XDG_DATA_HOME=str(H/'.runtime/data'),XDG_CONFIG_HOME=str(H/'.runtime/config'))
args=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(H),'res://Traversal.tscn','--','--prepared='+str(prepared),'--report='+str(report)]
start=time.monotonic()
with log.open('x')as f:result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=env)
out=dict(exit_code=result.returncode,wall_seconds=time.monotonic()-start,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,command=args)
with metrics.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out));raise SystemExit(0 if result.returncode in[0,2]else result.returncode)
