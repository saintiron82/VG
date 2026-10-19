"""Measured, source-bound r3 visual export. Retains previous scene/evidence bytes."""
from pathlib import Path
import subprocess,resource,time,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[4];CITY=ROOT/'world_city/concept_city_v3';HERE=Path(__file__).resolve().parent
OUT=CITY/'evidence/visual_registered_common_r3';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 if (OUT/'scene.json').exists():raise ValueError('Existing evidence is immutable; create a new revision.')
 paths=[CITY/'registered_source/plan.json',HERE/'candidate.json',HERE/'assemble.py',CITY/'build_blockout.py',CITY/'review_geometry.py',CITY/'preview/City.gd',CITY/'preview/BridgeMechanism.gd']
 d=json.loads((HERE/'candidate.json').read_bytes())
 for part in ['r01_ownership','r02_assembly_overlay','r03_external_interfaces','r04_assembly_ownership','r05_preview_lod','r07_native_interfaces',d['terrain_module'].split('.')[-2]]:
  paths+=list((CITY/'registered_topography/revisions'/part).glob('*.py'))
 paths+=[CITY/'registered_topography/author.py']
 d=json.loads((HERE/'candidate.json').read_bytes());paths += [ROOT/r['path'] for r in d['provenance']['input_packs']]
 paths=list(dict.fromkeys(paths));before={str(p.relative_to(ROOT)):sha(p) for p in paths}
 for p in paths:
  dest=OUT/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 (OUT/'input_hashes.json').write_text(json.dumps(before,indent=2)+'\n')
 cmd=['python',str(CITY/'build_blockout.py'),'--source='+str(CITY/'registered_source/plan.json'),'--integration='+str(HERE/'candidate.json'),'--terrain-pitch=8','--terrain-module='+d['terrain_module'],'--out='+str(OUT/'scene.json'),'--audit-out='+str(OUT/'source_audit.json'),'--source-snapshot='+str(OUT/'source_plan.snapshot.json')]
 t=time.monotonic()
 with (OUT/'build.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
 report=dict(exit_code=p.returncode,wall_seconds=time.monotonic()-t,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,before_hashes=before,after_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths})
 (OUT/'build_runtime.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert p.returncode==0 and report['before_hashes']==report['after_hashes']
if __name__=='__main__':main()
