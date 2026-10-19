"""Verify every archived byte, rebuild the chosen binding and load its scene."""
import os,json,pathlib,subprocess,sys,zipfile,time,shutil,hashlib
from ..r6 import apply_packs as a
HERE=pathlib.Path(__file__).resolve().parent

def extraction_selection(z,manifest):
 """All archived bytes are checked; only the executable closure needs a copy."""
 files=manifest['files'];names=set(z.namelist())
 if names!=set(files)|{'INTEGRATED_R8_MANIFEST.json'}:raise ValueError('Archive manifest coverage mismatch')
 for n in names:
  p=pathlib.PurePosixPath(n)
  if p.is_absolute()or'..'in p.parts or '\\'in n:raise ValueError('Unsafe archive path: '+n)
 if len(z.namelist())!=len(names):raise ValueError('Duplicate archive entries')
 for n,h in files.items():
  digest=hashlib.sha256()
  with z.open(n)as f:
   for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
  if digest.hexdigest()!=h:raise ValueError('Archived bytes differ: '+n)
 ref=manifest.get('clean_extract_closure')
 if not ref:return set(files),'complete_archive_extraction'
 def read_ref(ref):
  if files.get(ref['path'])!=ref['sha256']:raise ValueError('Unbound dependency: '+ref['path'])
  return json.loads(z.read(ref['path']))
 closure=read_ref(ref)
 if closure['schema']!='riverstone.scene_build_read_closure.v1':raise ValueError('Unsupported closure')
 for k in ('authored_scene','build_binding'):
  if closure[k]!=manifest[k]:raise ValueError('Closure binds different '+k)
 for n,h in closure['files'].items():
  if files.get(n)!=h:raise ValueError('Changed read dependency: '+n)
 # Code, shaders, configuration, images and other resources are small relative
 # to the historical JSON scene copies. Keep them all; omit only unneeded JSON.
 selected={n for n in files if pathlib.PurePosixPath(n).suffix.lower()!='.json'}
 selected.update(closure['files']);selected.add(ref['path'])
 for k in ('actual_scene','authored_scene','build_binding','runtime_precision_ledger','runtime_winding_ledger'):
  if manifest.get(k):read_ref(manifest[k]);selected.add(manifest[k]['path'])
 if manifest.get('runtime_precision_ledger'):
  ledger=read_ref(manifest['runtime_precision_ledger']);read_ref(ledger['retained_source_index_map']);selected.add(ledger['retained_source_index_map']['path'])
 if manifest.get('runtime_winding_ledger'):
  ledger=read_ref(manifest['runtime_winding_ledger'])
  refs=[ledger[k]for k in ('source_scene','derived_scene')]+ledger['implementation_refs']
  for ref in refs:
   if files.get(ref['path'])!=ref['sha256']:raise ValueError('Unbound winding dependency: '+ref['path'])
   selected.add(ref['path'])
 # Explicit final validation assets may extend the observed build input set.
 # They can be JSON collision data, native caches or source scripts. Verify
 # bytes without pretending every dependency is a JSON document.
 for ref in closure.get('additional_runtime_dependencies',[]):
  if files.get(ref['path'])!=ref['sha256']:raise ValueError('Unbound runtime dependency: '+ref['path'])
  selected.add(ref['path'])
 return selected,'full_archive_verified_executable_closure_extracted'

def main(archive,destination):
 archive=pathlib.Path(archive).resolve();dest=pathlib.Path(destination).resolve();assert not dest.exists();dest.mkdir(parents=True);start=time.monotonic()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('INTEGRATED_R8_MANIFEST.json'))
  selected,policy=extraction_selection(z,manifest)
  for n in sorted(selected|{'INTEGRATED_R8_MANIFEST.json'}):z.extract(n,dest)
 for n in selected:assert a.sha(dest/n)==manifest['files'][n],n
 ev=HERE/('clean_smoke_'+dest.name);ev.mkdir(exist_ok=False);env=dict(os.environ);env.pop('PYTHONPATH',None)
 with(ev/'imports.log').open('w')as log:
  result=subprocess.run([sys.executable,'-m','world_city.concept_city_v3.registered_integration.r8.smoke_imports',str(dest/'clean_r8_imports.json'),str(a.ROOT)],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert result.returncode==0,'Clean generation failed; inspect imports.log';shutil.copy2(dest/'clean_r8_imports.json',ev/'imports.json')
 home=pathlib.Path('/workspace/shared/city-r8-smoke-home');env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),XDG_CACHE_HOME=str(home/'.cache'),XDG_DATA_HOME=str(home/'.local/share'),LIBGL_ALWAYS_SOFTWARE='1')
 scene=dest/manifest['actual_scene']['path'];project=dest/'world_city/concept_city_v3/preview_r4'
 with(ev/'godot.log').open('w')as log:
  result=subprocess.run(['/opt/godot/4.6.3/Godot_v4.6.3-stable_linux.x86_64','--headless','--path',str(project),'--','--manifest='+str(scene),'--repo-root='+str(dest),'--headless-check=true','--view=registered','--report='+str(ev/'runtime.json')],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert result.returncode==0,'Clean Godot load failed';runtime=a.load(ev/'runtime.json');assert runtime['status']=='runtime_loaded'
 report=dict(status='pass',archive_sha256=a.sha(archive),verified_files=len(manifest['files']),extracted_files=len(selected),omitted_archival_files=len(manifest['files'])-len(selected),extraction_policy=policy,exact_source_generation='pass',actual_scene_sha256=a.sha(scene),clean_actual_scene_loaded=True,godot_exit=0,seconds=time.monotonic()-start,limits='Every archived byte checked; clean build and actual scene load from independent executable closure. Historical outputs remain in archive. Headless resource verification; separate actual images and route physics remain mandatory.')
 (ev/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
