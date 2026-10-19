"""Hash every extracted byte, rebuild local source, and load the actual R6 scene."""
from . import apply_packs as a
import os,sys,json,zipfile,subprocess,time,shutil
from pathlib import Path
def main(archive,destination):
    archive=Path(archive);dest=Path(destination);assert not dest.exists();dest.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read('INTEGRATED_R6_MANIFEST.json'))
        for n in z.namelist():
            p=Path(n);assert not p.is_absolute() and '..' not in p.parts,n
        z.extractall(dest)
    for n,h in manifest['files'].items():assert a.sha(dest/n)==h,n
    ev=a.HERE/('clean_smoke_'+dest.name);ev.mkdir(exist_ok=False);env=dict(os.environ);env.pop('PYTHONPATH',None);start=time.monotonic()
    with (ev/'imports.log').open('w') as log:
        result=subprocess.run([sys.executable,'-m','world_city.concept_city_v3.registered_integration.r6.smoke_imports',str(dest/'clean_r6_imports.json')],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,'Clean source generation failed; inspect imports.log'
    shutil.copy2(dest/'clean_r6_imports.json',ev/'imports.json')
    home=Path('/workspace/shared/city-r6-smoke-home')
    env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),XDG_CACHE_HOME=str(home/'.cache'),XDG_DATA_HOME=str(home/'.local/share'),LIBGL_ALWAYS_SOFTWARE='1')
    scene=dest/manifest['actual_scene']['path'];assert a.sha(scene)==manifest['actual_scene']['sha256']
    project=dest/'world_city/concept_city_v3/preview_r4'
    with (ev/'godot.log').open('w') as log:
        result=subprocess.run(['/opt/godot/4.6.3/Godot_v4.6.3-stable_linux.x86_64','--headless','--path',str(project),'--','--manifest='+str(scene),'--repo-root='+str(dest),'--headless-check=true','--view=registered','--report='+str(ev/'runtime.json')],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,'Clean Godot load failed'
    runtime=a.load(ev/'runtime.json');assert runtime['status']=='runtime_loaded'
    report={'status':'pass','archive_sha256':a.sha(archive),'verified_files':len(manifest['files']),
      'generation_imports':'pass_no_original_repository_reads','actual_scene_sha256':a.sha(scene),
      'actual_r6_scene_loaded':True,'godot_exit':result.returncode,'seconds':time.monotonic()-start,
      'limits':'Clean headless load verifies self-contained resources; actual images and route physics have separate reports.'}
    (ev/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
