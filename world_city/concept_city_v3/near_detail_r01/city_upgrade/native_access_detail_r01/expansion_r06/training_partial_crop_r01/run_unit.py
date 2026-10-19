"""Hard remaining wall-time guard; retains incomplete outputs as failure evidence."""
from pathlib import Path
import hashlib,json,os,resource,subprocess,sys,time
H=Path(__file__).resolve().parent
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
 resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def main():
 source=H/'prepared_inputs.json';data=json.loads(source.read_bytes());elapsed=data['summary']['elapsed_seconds'];remaining=60-elapsed
 assert remaining>0 and not(H/'validation/process_report.json').exists()
 digest=hashlib.sha256(source.read_bytes()).hexdigest();start=time.monotonic();timed_out=False;code=None
 with (H/'validation/build.log').open('x')as log:
  try:
   proc=subprocess.run([sys.executable,str(H/'build.py'),'--prepared-sha256',digest],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,timeout=remaining);code=proc.returncode
  except subprocess.TimeoutExpired:timed_out=True
 duration=time.monotonic()-start;report_path=H/'validation/build_report.json';proof=json.loads(report_path.read_bytes())if report_path.exists()else{}
 report={'all_pass':not timed_out and code==0 and proof.get('all_pass',False)and elapsed+duration<60,'source_only_preparation_seconds':elapsed,'compile_and_validation_process_seconds':duration,'combined_seconds':elapsed+duration,'hard_combined_wall_limit_seconds':60,'hard_remaining_process_seconds':remaining,'timed_out':timed_out,'exit_code':code,'address_space_limit_bytes':256*1024*1024,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'prepared_inputs_sha256':digest,'geometry_bytes':sum(p.stat().st_size for p in (H/'modules').glob('*.json')if p.name!='catalog.json'),'geometry_limit_bytes':8*1024*1024,'production_binding_changed':False}
 report['all_pass']&=report['geometry_bytes']<=report['geometry_limit_bytes'];(H/'validation/process_report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report));return 0 if report['all_pass']else 2
if __name__=='__main__':raise SystemExit(main())
