from pathlib import Path
import json,os,resource,subprocess,time
H=Path(__file__).resolve().parent;R=H.parents[6]
assert (R/'voxel_character').exists()
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(45,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
base={**os.environ,'REPO_ROOT':str(R),'XDG_DATA_HOME':str(H/'xdg_data'),'XDG_CACHE_HOME':str(H/'xdg_cache'),'XDG_CONFIG_HOME':str(H/'xdg_config')}
rows=[]
for script,projection,tag in [('verify.gd',False,'godot_mesh'),('verify_visibility.gd',True,'godot_visibility')]:
 env={**base,'SOURCE_PLAN':str(H/('runtime_projection/source_plan.json'if projection else 'source_plan.json')),'MODULE_CATALOG':str(H/('runtime_projection/modules.json'if projection else 'modules/catalog.json')),'VISIBILITY_REPORT':str(H/'validation/visibility_report.json'),'OUTPUT_REPORT':str(H/'validation'/(tag+'_report.json'))}
 start=time.monotonic()
 with (H/'validation'/(tag+'.log')).open('x')as log:result=subprocess.run(['/usr/local/bin/godot','--headless','--path',str(H/'mesh_validation'),'--script','res://'+script],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,timeout=45)
 report=json.loads(Path(env['OUTPUT_REPORT']).read_bytes())if Path(env['OUTPUT_REPORT']).exists()else {};assert result.returncode==0 and report.get('all_pass'),tag+' failed';rows.append({'test':tag,'all_pass':True,'elapsed_seconds':time.monotonic()-start});print(json.dumps(rows[-1]),flush=True)
(H/'validation/headless_runner.json').write_text(json.dumps({'all_pass':True,'results':rows,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'address_space_limit_bytes':256*1024*1024,'per_process_wall_seconds':45},sort_keys=True,indent=2)+'\n')
