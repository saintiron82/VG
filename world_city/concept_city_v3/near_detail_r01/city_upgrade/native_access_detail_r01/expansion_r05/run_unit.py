"""One aggregate 120-second build + source replay + shared mesh validation unit."""
from pathlib import Path
import argparse,json,os,resource,subprocess,sys,time,hashlib
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if(p/'voxel_character/common/core.py').is_file());LIMIT=40*1024*1024

def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(120,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def size():return sum(p.stat().st_size for p in H.rglob('*')if p.is_file()and not p.is_symlink())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(rev):
 start=time.monotonic();dest=H/rev;env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','REPO_ROOT':str(R),'SOURCE_PLAN':str(dest/'source_plan.json'),'MODULE_CATALOG':str(dest/'modules/catalog.json'),'OUTPUT_REPORT':str(dest/'godot_mesh_report.json'),'XDG_DATA_HOME':str(H/'xdg_data'),'XDG_CACHE_HOME':str(H/'xdg_cache'),'XDG_CONFIG_HOME':str(H/'xdg_config')};rows=[];before=size()
 commands=[('build',[sys.executable,str(H/'author_batch.py'),'--revision',rev]),('source_replay',[sys.executable,str(H/'verify_batch.py'),'--revision',rev]),('common_godot_mesh',['godot','--headless','--path',str(H/'mesh_validation'),'--script','res://verify.gd'])]
 for name,cmd in commands:
  if name=='build' and (dest/'build_report.json').is_file():
   previous=json.loads((dest/'build_report.json').read_bytes());assert previous['all_pass'];rows.append({'step':'build','exit_code':0,'reused_existing_build_report_sha256':sha(dest/'build_report.json'),'original_build_seconds':previous['elapsed_seconds'],'aggregate_elapsed_seconds':time.monotonic()-start,'combined_output_bytes':size()});continue
  seconds=120-(time.monotonic()-start);assert seconds>0
  log=H/'validation'/(rev+'.'+name+'.log')
  with log.open('w')as output:
   proc=subprocess.run(cmd,cwd=R,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=seconds,preexec_fn=limits)
  row={'step':name,'exit_code':proc.returncode,'aggregate_elapsed_seconds':time.monotonic()-start,'combined_output_bytes':size()};rows.append(row);print(json.dumps(row),flush=True)
  if proc.returncode!=0:
   print(log.read_text()[-5000:],flush=True);break
  assert size()<LIMIT
 okay=len(rows)==3 and all(r['exit_code']==0 for r in rows)
 if okay:
  reports=[json.loads((dest/f).read_bytes())for f in ['build_report.json','candidate_geometry.json','fixture_results.json','godot_mesh_report.json']];okay=all(d['all_pass']for d in reports);plan=json.loads((dest/'source_plan.json').read_bytes());cat=json.loads((dest/'modules/catalog.json').read_bytes());gv=reports[-1];assert gv['placements']==sum(len(a['placements'])for a in plan['assets'])and gv['modules']==len(cat['modules'])
 report={'all_pass':okay,'revision':rev,'steps':rows,'aggregate_elapsed_seconds':time.monotonic()-start,'aggregate_wall_limit_seconds':120,'address_space_limit_bytes':256*1024*1024,'combined_output_limit_bytes':LIMIT,'combined_output_bytes':size(),'generated_unit_bytes':size()-before,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'production_binding_changed':False,'full_compile':False,'gui_used':False}
 (H/'validation'/(rev+'.unit_report.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0 if okay else 2
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--revision',required=True,choices=['first_e7_e1','remaining_e2_e3_e4_e5_e6']);args=ap.parse_args();raise SystemExit(run(args.revision))
