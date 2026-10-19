from pathlib import Path
import subprocess,resource,time,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];CITY=ROOT/'world_city/concept_city_v3';o=CITY/'evidence/visual_registered_common_r1_cached';o.mkdir(exist_ok=True)
rel=['registered_source/plan.json','registered_topography/author.py','registered_topography/revisions/r01_ownership/author.py','registered_topography/revisions/r01_ownership/contract.json','registered_topography/revisions/r02_assembly_overlay/author.py','registered_topography/revisions/r02_assembly_overlay/contract.json','registered_integration/common_city_candidate.json','build_blockout.py','review_geometry.py','preview/City.gd','registered_topography/revisions/r03_external_interfaces/review.py']
paths=[CITY/p for p in rel];before={p:hashlib.sha256((CITY/p).read_bytes()).hexdigest() for p in rel}
cmd=['python',str(CITY/'build_blockout.py'),'--source='+str(CITY/'registered_source/plan.json'),'--integration='+str(CITY/'registered_integration/common_city_candidate.json'),'--terrain-pitch=8','--terrain-module=world_city.concept_city_v3.registered_topography.revisions.r03_external_interfaces.review','--out='+str(o/'scene.json'),'--audit-out='+str(o/'source_audit.json'),'--source-snapshot='+str(o/'source_plan.snapshot.json')];t=time.monotonic()
with (o/'build.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
r={'exit_code':p.returncode,'wall_seconds':time.monotonic()-t,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'before_hashes':before,'after_hashes':{p:hashlib.sha256((CITY/p).read_bytes()).hexdigest() for p in rel}}
(o/'build_runtime.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));print((o/'build.log').read_text()[-3000:]);assert p.returncode==0 and r['before_hashes']==r['after_hashes']
for path,relative in zip(paths,rel):
 target=o/'source_snapshot'/relative;target.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(path,target)
