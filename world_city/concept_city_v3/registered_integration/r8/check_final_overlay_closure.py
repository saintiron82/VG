"""Recheck a sealed overlay from archive bytes in an independent executable closure.

The complete baseline and overlay archives are retained. Only current runtime
and source-build dependencies are materialized here; historical physics assets
have a separate relocation/case-identity certificate. This is not a full install.
"""
import argparse,hashlib,json,subprocess,zipfile,os
from pathlib import Path

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def run(base,overlay,clean,out):
 clean=Path(clean).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(base)as bz,zipfile.ZipFile(overlay)as oz:
  om=json.loads(oz.read('VG_OVERLAY_MANIFEST.json'));assert digest(base)==om['base_archive_sha256']
  index=json.loads(oz.read('VG_PROJECT_INDEX.json'));expected={**index['runtime_files'],**index['build_files']}
  for n in ['VG_PROJECT_INDEX.json','world_city/concept_city_v3/review_final_city.sh']:
   z=oz if n in oz.namelist()else bz;expected[n]=hashlib.sha256(z.read(n)).hexdigest()
  changes=[]
  for n,h in sorted(expected.items()):
   p=clean/n
   if not p.resolve().is_relative_to(clean):raise ValueError('Unsafe input '+n)
   if p.is_file()and digest(p)==h:continue
   z=oz if n in oz.namelist()else bz
   b=z.read(n)
   if hashlib.sha256(b).hexdigest()!=h:raise ValueError('Archive/index disagreement '+n)
   if p.exists():
    old=digest(p);row=om['changes'].get(n,{})
    if old not in row.get('accepted_prior_sha256',[]):raise ValueError('Unexpected independent prior '+n)
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);changes.append(n)
  if any(digest(clean/n)!=h for n,h in expected.items()):raise ValueError('Independent dependency check failed')
 reports={}
 for scope in ('runtime','build'):
  run=subprocess.run(['python',str(clean/'Verify-Project.py'),'--scope',scope],cwd=clean,capture_output=True,text=True)
  (out/(scope+'.log')).write_text(run.stdout+run.stderr)
  if run.returncode:raise ValueError('Independent verifier failed '+scope)
  reports[scope]=json.loads(run.stdout)
 env=dict(os.environ,CITY_HEADLESS='1');run=subprocess.run(['sh',str(clean/'world_city/concept_city_v3/review_final_city.sh')],cwd=clean,env=env,capture_output=True,text=True)
 (out/'godot.log').write_text(run.stdout+run.stderr)
 if run.returncode or 'SCRIPT ERROR' in run.stdout+run.stderr or 'Parse Error' in run.stdout+run.stderr:raise ValueError('Actual archived scene/addendum load failed')
 report={'status':'pass','base_archive_sha256':digest(base),'overlay_sha256':digest(overlay),'independent_root':str(clean),'verified_current_dependency_files':len(expected),'archive_sourced_updates':changes,'scopes':reports,'actual_scene_and_visible_addendum_load_exit':run.returncode,'limits':'Independent archived runtime/build closure only. Full archive bytes and history separately verified; selected493 source identity and bounded escaped-name physics smoke separately certified. Windows runtime is pending.'}
 (out/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('archive_sourced_updates','scopes')},indent=2))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('base');ap.add_argument('overlay');ap.add_argument('clean');ap.add_argument('output');a=ap.parse_args();run(a.base,a.overlay,a.clean,a.output)
if __name__=='__main__':main()
