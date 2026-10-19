"""R5 measured source-bound export; sealed terrain binding is mandatory."""
from pathlib import Path
import subprocess,resource,time,json,hashlib,shutil,sys,os,runpy,datetime
ROOT=Path(__file__).resolve().parents[4];CITY=ROOT/'world_city/concept_city_v3';HERE=Path(__file__).resolve().parent;OUT=CITY/'evidence/visual_registered_common_r5'
sys.path.insert(0,str(ROOT))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def child():
 accelerated='--r5-owner-prefilter' in sys.argv
 opened=set()
 def audit(event,args):
  if event!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
  p=Path(os.fsdecode(args[0])).absolute();mode=args[1] if len(args)>1 else None
  if isinstance(mode,str) and any(s in mode for s in ('w','a','+','x')):return
  if ROOT in p.parents and OUT not in p.parents and p.suffix in ('.py','.json','.gd','.txt','.png'):opened.add(p)
 sys.addaudithook(audit)
 try:
  d=json.loads((HERE/'candidate.json').read_bytes());assert d['status']=='native_exterior_candidate_pending_actual_review';assert 'UNBOUND' not in d['terrain_module'];sys.argv=[str(CITY/'build_blockout.py'),'--source='+str(CITY/'registered_source/plan.json'),'--integration='+str(HERE/'candidate.json'),'--terrain-pitch=8','--terrain-module='+d['terrain_module'],'--out='+str(OUT/'scene.json'),'--audit-out='+str(OUT/'source_audit.json'),'--source-snapshot='+str(OUT/'source_plan.snapshot.json'),'--terrain-cache-dir='+str(OUT/'terrain_cache'),'--terrain-cache-report='+str(OUT/'terrain_cache_runtime.json'),'--terrain-preflight-out='+str(OUT/'supplemental_preflight.json')]
  if accelerated:
   binding=json.loads((HERE/'owner_prefilter_binding.json').read_bytes())
   for name,h in binding['verified_inputs'].items():assert sha(ROOT/name)==h,('Changed prefilter input',name)
   from world_city.concept_city_v3.validation.owner_index_performance.activate_r5 import activate
   from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream
   from world_city.concept_city_v3.validation.owner_index_performance.excluded_memo import ExcludedMemo
   from world_city.concept_city_v3.registered_topography.revisions.r02_assembly_overlay import author as exclusion_source
   memo=ExcludedMemo(exclusion_source);memo_callable=memo.is_excluded
   handle=activate(upstream,opt_in=True,export_revision='r5')
   try:
    exclusion_source.is_excluded=memo_callable
    with handle:runpy.run_path(sys.argv[0],run_name='__main__',init_globals={'CACHE_DEPENDENCY_PATHS':opened})
   finally:
    unchanged=exclusion_source.is_excluded is memo_callable
    if unchanged:exclusion_source.is_excluded=memo.original
    handle.report['exclusion_memo']=dict(source_hash=sha(Path(exclusion_source.__file__)),candidate_hash=sha(Path(sys.modules[ExcludedMemo.__module__].__file__)),cache_info=memo.cached.cache_info()._asdict(),restored_exact_original=unchanged and exclusion_source.is_excluded is memo.original)
    (OUT/'owner_prefilter_runtime.json').write_text(json.dumps(handle.report,indent=2)+'\n')
    if not unchanged:raise RuntimeError('Exclusion callable changed while explicit r5 hook was active')
  else:runpy.run_path(sys.argv[0],run_name='__main__',init_globals={'CACHE_DEPENDENCY_PATHS':opened})
 finally:
  for m in tuple(sys.modules.values()):
   p=getattr(m,'__file__',None)
   if p:
    p=Path(p).absolute()
    if ROOT in p.parents and p.suffix=='.py':opened.add(p)
  records={str(p.relative_to(ROOT)):sha(p) for p in sorted(opened) if p.is_file()}
  (OUT/'read_dependency_hashes.json').write_text(json.dumps(records,indent=2)+'\n')

def main():
 OUT.mkdir(exist_ok=True);assert not (OUT/'scene.json').exists(),'Evidence cannot be overwritten'
 if (OUT/'build.log').exists():
  archive=OUT/'attempts'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');archive.mkdir(parents=True)
  for p in tuple(OUT.iterdir()):
   if p.name not in ('attempts','terrain_cache'):p.rename(archive/p.name)
 allfiles=[p for base in (ROOT/'world_city',ROOT/'voxel_character') for p in base.rglob('*') if p.is_file() and '.godot' not in p.parts and '__pycache__' not in p.parts and 'checkpoints' not in p.parts and p.suffix in ('.py','.json','.gd') and OUT not in p.parents]
 before={str(p.relative_to(ROOT)):sha(p) for p in allfiles};t=time.monotonic()
 with (OUT/'build.log').open('w') as log:process=subprocess.run([sys.executable,str(Path(__file__)),'--child']+(['--r5-owner-prefilter'] if '--r5-owner-prefilter' in sys.argv else []),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 records=json.loads((OUT/'read_dependency_hashes.json').read_bytes()) if (OUT/'read_dependency_hashes.json').exists() else {};changed=[p for p,h in records.items() if before.get(p)!=h or sha(ROOT/p)!=h]
 for name,h in records.items():
  p=ROOT/name;dest=OUT/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 report=dict(owner_prefilter_explicit_opt_in='--r5-owner-prefilter' in sys.argv,exit_code=process.returncode,wall_seconds=time.monotonic()-t,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,read_dependency_files=len(records),changed_during_build=changed,read_dependency_hashes=records)
 (OUT/'build_runtime.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='read_dependency_hashes'},indent=2));assert process.returncode==0 and records and not changed
if __name__=='__main__':child() if '--child' in sys.argv else main()
