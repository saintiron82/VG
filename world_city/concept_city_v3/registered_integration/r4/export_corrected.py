"""Measured export with read-dependency ledger, immutable output and no core edits."""
from pathlib import Path
import subprocess,resource,time,json,hashlib,shutil,sys,os,runpy
ROOT=Path(__file__).resolve().parents[4];CITY=ROOT/'world_city/concept_city_v3';HERE=Path(__file__).resolve().parent;OUT=CITY/'evidence/visual_registered_common_r4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def child():
 opened=set()
 def audit(event,args):
  if event!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
  p=Path(os.fsdecode(args[0])).absolute();mode=args[1] if len(args)>1 else None
  if isinstance(mode,str) and any(s in mode for s in ('w','a','+','x')):return
  if ROOT in p.parents and OUT not in p.parents and p.suffix in ('.py','.json','.gd','.txt','.png'):opened.add(p)
 sys.addaudithook(audit)
 d=json.loads((HERE/'corrected_visual_candidate.json').read_bytes());sys.argv=[str(CITY/'build_blockout.py'),'--source='+str(CITY/'registered_source/plan.json'),'--integration='+str(HERE/'corrected_visual_candidate.json'),'--terrain-pitch=8','--terrain-module='+d['terrain_module'],'--out='+str(OUT/'scene.json'),'--audit-out='+str(OUT/'source_audit.json'),'--source-snapshot='+str(OUT/'source_plan.snapshot.json')]
 runpy.run_path(sys.argv[0],run_name='__main__')
 for m in tuple(sys.modules.values()):
  p=getattr(m,'__file__',None)
  if p:
   p=Path(p).absolute()
   if ROOT in p.parents and p.suffix=='.py':opened.add(p)
 records={str(p.relative_to(ROOT)):sha(p) for p in sorted(opened) if p.is_file()}
 (OUT/'read_dependency_hashes.json').write_text(json.dumps(records,indent=2)+'\n')
def main():
 OUT.mkdir(exist_ok=True);assert not (OUT/'scene.json').exists(),'Evidence cannot be overwritten'
 allfiles=[p for base in (ROOT/'world_city',ROOT/'voxel_character') for p in base.rglob('*') if p.is_file() and '.godot' not in p.parts and '__pycache__' not in p.parts and 'checkpoints' not in p.parts and p.suffix in ('.py','.json','.gd') and OUT not in p.parents]
 before={str(p.relative_to(ROOT)):sha(p) for p in allfiles};t=time.monotonic()
 with (OUT/'build.log').open('w') as log:process=subprocess.run([sys.executable,str(Path(__file__)),'--child'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 records=json.loads((OUT/'read_dependency_hashes.json').read_bytes()) if (OUT/'read_dependency_hashes.json').exists() else {};changed=[p for p,h in records.items() if before.get(p)!=h or sha(ROOT/p)!=h]
 for name,h in records.items():
  p=ROOT/name;dest=OUT/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 report=dict(exit_code=process.returncode,wall_seconds=time.monotonic()-t,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,read_dependency_files=len(records),changed_during_build=changed,read_dependency_hashes=records)
 (OUT/'build_runtime.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='read_dependency_hashes'},indent=2));assert process.returncode==0 and records and not changed
if __name__=='__main__':child() if '--child' in sys.argv else main()
