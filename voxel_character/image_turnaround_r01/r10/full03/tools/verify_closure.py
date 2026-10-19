"""Read-only closure integrity, scoped evidence gates, and current storage checks."""
from pathlib import Path
import hashlib,json,sys,shutil
BASE=Path(__file__).resolve().parents[1];REPO=BASE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 cp=BASE/'closure.json';c=json.loads(cp.read_text());bad=[]
 for item in c['files']:
  p=REPO/item['path']
  if not p.is_file():bad.append({'path':item['path'],'reason':'missing'})
  elif sha(p)!=item['sha256']:bad.append({'path':item['path'],'reason':'sha256 mismatch'})
  elif p.stat().st_size!=item['bytes']:bad.append({'path':item['path'],'reason':'byte count mismatch'})
 reg=json.loads((BASE/'evidence/coupled_regression.json').read_text());projection=json.loads((BASE/'evidence/coupled_projection.json').read_text());boundary=json.loads((BASE/'evidence/field_boundary_audit.json').read_text());used=sum(p.stat().st_size for p in BASE.parent.rglob('*') if p.is_file());free=shutil.disk_usage(BASE).free
 result={'closure_sha256':sha(cp),'files_checked':len(c['files']),'mismatches':bad,'byte_integrity_pass':not bad,'limited_regression_pass':reg['limited_regression_pass'],'geometry_boundary_failure_retained':boundary['status']=='FAIL_FINITE_DOMAIN_CLOSURE','source_coverage':{k:v['full_target_coverage']for k,v in projection['metrics'].items()},'r10_file_bytes':used,'r10_cap_bytes':66*1048576,'free_disk_bytes':free,'minimum_disk_bytes':1073741824,'current_budget_pass':used<=66*1048576 and free>=1073741824,'common_compile_ready':False,'art_or_full_contract_pass':False}
 print(json.dumps(result,indent=2));return 0 if not bad else 1
if __name__=='__main__':sys.exit(run())
