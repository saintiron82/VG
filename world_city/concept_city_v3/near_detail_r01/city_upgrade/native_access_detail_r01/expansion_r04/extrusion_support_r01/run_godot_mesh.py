"""Tiny isolated project, unchanged common mesh helpers, hard AS/CPU budgets."""
from pathlib import Path
import os,resource,subprocess,json,time
H=Path(__file__).resolve().parent;PROJECT=H.parent;env=dict(os.environ)
for k,d in [('XDG_CACHE_HOME','xdg_cache'),('XDG_CONFIG_HOME','xdg_config'),('XDG_DATA_HOME','xdg_data')]:env[k]=str(PROJECT/d)
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(90,90));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
limits();start=time.perf_counter()
with (H/'godot_mesh.log').open('w') as log:
 p=subprocess.run(['godot','--headless','--path',str(PROJECT/'mesh_validation'),'--script','res://verify_extrusion.gd'],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=90)
report={'exit_code':p.returncode,'elapsed_seconds':time.perf_counter()-start,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'address_space_limit_bytes':256*1024*1024,'cpu_limit_seconds':90};(H/'godot_process.json').write_text(json.dumps(report,indent=2)+'\n');print(report);print((H/'godot_mesh.log').read_text()[-1200:]);raise SystemExit(p.returncode)
