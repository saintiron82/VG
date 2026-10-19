import pathlib,json,subprocess,os,time,resource
H=pathlib.Path(__file__).resolve().parent
prepared=H/'prepared_runtime.json';report=H/'evidence/north_replay.json';log=report.with_suffix('.log');metrics=H/'evidence/north_replay_metrics.json'
assert not any(p.exists()for p in [report,log,metrics])
env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1',XDG_CACHE_HOME=str(H/'.runtime/cache'),XDG_DATA_HOME=str(H/'.runtime/data'),XDG_CONFIG_HOME=str(H/'.runtime/config'))
args=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(H),'res://Traversal.tscn','--','--prepared='+str(prepared),'--report='+str(report)]
start=time.monotonic()
with log.open('x')as f:result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=env)
out={'exit_code':result.returncode,'wall_seconds':time.monotonic()-start,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'command':args}
with metrics.open('x')as f:json.dump(out,f,indent=2)
print(json.dumps(out))
raise SystemExit(0 if result.returncode in [0,2]else result.returncode)
