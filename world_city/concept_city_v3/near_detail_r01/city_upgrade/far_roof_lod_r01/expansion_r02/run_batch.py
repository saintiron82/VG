"""Bounded, explicit pending-near batch. Writes only this new candidate directory."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
E=Path(__file__).resolve().parent;R=next(p for p in E.parents if(p/'voxel_character/common/core.py').is_file())
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def size():return sum(p.stat().st_size for p in E.rglob('*')if p.is_file())
lock=load(E/'batch_scope.json');limit=lock['output_cap_bytes']
for p,h in lock['frozen_method'].items():assert sha(R/p)==h,(p,'frozen method changed')
priority=['registered_port_long_loading_shed','working_r01_bank_loft_store','c3_property_ordinary_r2_b10bcfbba43136a4']
items=sorted(lock['selected'],key=lambda x:(priority.index(x['asset_key'])if x['asset_key']in priority else len(priority),x['asset_key']))
rows=[];start=time.monotonic()
for item in items:
 k=item['asset_key'];out=E/k
 row={'asset_key':k,'status':item['input_status'],'reason_codes':item['reason_codes']}
 if row['status']=='SUPPORTED_INPUT_UNBUILT':
  try:
   p=subprocess.run([sys.executable,str(E/'build_candidate.py'),k],cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=30)
   (out/'build.log').write_text(p.stdout+p.stderr)
   if(out/'candidate.provenance.json').exists():
    proof=load(out/'candidate.provenance.json');row.update(status=proof['status'],reason_codes=proof['reason_codes'],provenance={'path':str((out/'candidate.provenance.json').relative_to(R)),'sha256':sha(out/'candidate.provenance.json')},render=proof['render'],roof_quad_count=proof['roof_quad_count'],output_quad_count=proof['output_quad_count'],seconds=proof['seconds'],max_rss_kib=proof['max_rss_kib'])
   else:row.update(status='UNSUPPORTED_BUILD_FAILURE',reason_codes=['BOUNDED_BUILD_FAILED'],returncode=p.returncode)
  except subprocess.TimeoutExpired as exc:
   (out/'build.log').write_text('30-second per-asset build limit reached\n');row.update(status='UNSUPPORTED_BUILD_FAILURE',reason_codes=['BOUNDED_BUILD_TIMEOUT'])
 rows.append(row)
 report={'schema':'riverstone.source_roof_far_lod_batch_index.v1','scope':{'path':str((E/'batch_scope.json').relative_to(R)),'sha256':sha(E/'batch_scope.json')},'rows':rows,'complete':len(rows)==len(items),'runtime_activation':False,'generated_bytes':size(),'output_cap_bytes':limit,'elapsed_seconds':time.monotonic()-start}
 write(E/'candidate_index.json',report)
 print(json.dumps(row),flush=True)
 if size()>limit:raise RuntimeError('Output cap exceeded; stop without further candidates')
print(json.dumps({'complete':True,'count':len(rows),'geometry_pass_count':sum(r['status']=='CANDIDATE_GEOMETRY_PASS_PENDING_GODOT'for r in rows),'generated_bytes':size(),'elapsed_seconds':time.monotonic()-start}),flush=True)
