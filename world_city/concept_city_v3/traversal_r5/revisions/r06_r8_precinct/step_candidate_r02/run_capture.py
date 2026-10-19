"""Bounded serial original-controller and input-pause runs; preserve every result."""
import pathlib,json,subprocess,time,resource,os
H=pathlib.Path(__file__).resolve().parent
def main():
 data=json.loads((H/'prepared.json').read_bytes());(H/'evidence').mkdir(exist_ok=True)
 for mode in ['baseline','pause']:
  selected=[r['id']for r in data['routes']if ('pause_points_xyz_m'in r)==(mode=='pause')]
  report=H/'evidence'/('capsule_'+mode+'_initial.json');log=report.with_suffix('.log');metrics=H/'evidence'/('capsule_'+mode+'_metrics.json');assert not any(p.exists()for p in [report,log,metrics])
  env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1',XDG_CACHE_HOME=str(H/'.runtime/cache'),XDG_DATA_HOME=str(H/'.runtime/data'),XDG_CONFIG_HOME=str(H/'.runtime/config'))
  scene='StepTraversal.tscn'if mode=='baseline'else 'PauseTraversal.tscn'
  args=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(H),'res://'+scene,'--','--prepared='+str(H/'prepared.json'),'--report='+str(report),'--routes='+','.join(selected)]
  start=time.monotonic()
  with log.open('x')as f:run=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=env)
  result={'mode':mode,'exit_code':run.returncode,'wall_seconds':time.monotonic()-start,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'command':args}
  with metrics.open('x')as f:json.dump(result,f,indent=2)
  print(json.dumps(result),flush=True)
  if run.returncode not in [0,2]:raise SystemExit(run.returncode)
if __name__=='__main__':main()
