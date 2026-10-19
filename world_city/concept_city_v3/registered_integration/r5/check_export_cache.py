"""Compare actual bounded export bytes before and after exact row-cache resume."""
import subprocess,sys,json,hashlib,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];CITY=HERE.parents[1];OUT=HERE/'cache_validation';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
common=[sys.executable,str(CITY/'build_blockout.py'),'--source='+str(CITY/'registered_source/plan.json'),'--integration='+str(HERE.parent/'r4/corrected_visual_candidate.json'),'--terrain-module=world_city.concept_city_v3.registered_integration.r5.cache_validation_terrain','--terrain-pitch=8','--terrain-cache-dir='+str(OUT/'rows')]
records=[]
for name in ('first','resume'):
 args=common+['--out='+str(OUT/(name+'.scene.json')),'--audit-out='+str(OUT/(name+'.audit.json')),'--source-snapshot='+str(OUT/(name+'.source.json')),'--terrain-preflight-out='+str(OUT/(name+'.preflight.json')),'--terrain-cache-report='+str(OUT/(name+'.cache.json'))]
 t=time.monotonic()
 with (OUT/(name+'.log')).open('w') as log:r=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 records.append(dict(name=name,exit_code=r.returncode,seconds=time.monotonic()-t));assert r.returncode==0,(name,r.returncode)
first=json.loads((OUT/'first.scene.json').read_bytes());second=json.loads((OUT/'resume.scene.json').read_bytes());assert first==second
cache=json.loads((OUT/'resume.cache.json').read_bytes());assert cache['cache_hits']==2 and cache['new_rows']==0,cache
report=dict(status='pass_exact_complete_bounded_scene_equal',scope='Four actual 8 m R13 tiles plus unchanged nonterrain source products, not full city or R14 clearance.',scene_sha256=sha(OUT/'first.scene.json'),resume_sha256=sha(OUT/'resume.scene.json'),cache=cache,processes=records)
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
