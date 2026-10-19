"""Verify every archived byte, generation imports and existing actual scene load."""
import sys,os,zipfile,json,hashlib,subprocess,time,resource,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(archive,destination):
 archive=Path(archive);destination=Path(destination);assert not destination.exists();destination.mkdir(parents=True)
 with zipfile.ZipFile(archive) as z:
  manifest=json.loads(z.read('INTEGRATED_R5_SOURCES_MANIFEST.json'))
  for name in z.namelist():
   p=Path(name)
   if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe archive member '+name)
  z.extractall(destination)
 for name,h in manifest['files'].items():assert sha(destination/name)==h,name
 ev=HERE/('clean_smoke_'+destination.name);ev.mkdir(exist_ok=False);t=time.monotonic();env=dict(os.environ);env.pop('PYTHONPATH',None)
 # The isolated child may not access the original repository even to write its
 # report. Write inside the extraction; only the parent copies evidence back.
 import_report=destination/'r5_clean_imports.json'
 with (ev/'imports.log').open('w') as log:r=subprocess.run([sys.executable,'-m','world_city.concept_city_v3.registered_integration.r5.smoke_imports',str(import_report)],cwd=destination,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0,'Generation import/candidate smoke failed: '+str(ev/'imports.log')
 shutil.copy2(import_report,ev/'imports.json')
 home=Path('/workspace/shared/city-recovered-smoke-home');env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),XDG_CACHE_HOME=str(home/'.cache'),XDG_DATA_HOME=str(home/'.local/share'),LIBGL_ALWAYS_SOFTWARE='1')
 scene=destination/'world_city/concept_city_v3/evidence/visual_registered_common_r3/bridge_scene.json';project=destination/'world_city/concept_city_v3/preview_r4'
 with (ev/'godot.log').open('w') as log:r=subprocess.run(['/opt/godot/4.6.3/Godot_v4.6.3-stable_linux.x86_64','--headless','--path',str(project),'--','--manifest='+str(scene),'--repo-root='+str(destination),'--headless-check=true','--view=registered','--report='+str(ev/'runtime.json')],cwd=destination,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0;runtime=json.loads((ev/'runtime.json').read_bytes());assert runtime['status']=='runtime_loaded'
 report=dict(status='pass',archive_sha256=sha(archive),verified_files=len(manifest['files']),extracted_root=str(destination),generation_imports='pass_forbidden_original_repository_reads',candidate='r5_exact_source_and_all_native_cache_hashes_verified',actual_scene_load='existing_r3_complete_scene_pass',godot_exit=r.returncode,actual_scene_sha256=sha(scene),wall_seconds=time.monotonic()-t,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,limits='No R5 scene image exists in this pre-export source checkpoint. R3 runtime smoke proves local resource availability; R5 actual visual review follows.')
 (ev/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
