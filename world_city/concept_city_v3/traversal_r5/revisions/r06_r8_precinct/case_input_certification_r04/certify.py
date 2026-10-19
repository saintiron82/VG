"""Exact transitive case certification across preserved, uninstrumented runs."""
import argparse,copy,hashlib,importlib.util,json,pathlib,shutil,sys
H=pathlib.Path(__file__).resolve().parent;B=H.parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
spec=importlib.util.spec_from_file_location('case_inputs',B/'case_input_certification_r01/case_inputs.py');ci=importlib.util.module_from_spec(spec);spec.loader.exec_module(ci)
sha=ci.sha
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def certify(selected,runs):
 rows=[];prior_failures=[];engine=None;settings=None
 for run in runs:
  inp,report=run['input'],run['report'];assert not report['errors'];assert report['prepared_sha256']==run['prepared_sha256'];assert {r['id']for r in report['routes']}==set(inp['cases']);assert len(report['routes'])==len(inp['cases'])
  if engine is None:engine=report['engine_version'];settings=report['settings']
  assert engine==report['engine_version']and settings==report['settings']
  run['results']={r['id']:r for r in report['routes']}
  for r in report['routes']:
   assert r['within_route_teleports']==0
   if not r['pass']:prior_failures.append(dict(id=r['id'],run=run['name'],input_sha256=inp['cases'][r['id']]['sha256'],result=r))
 for rid,case in selected['cases'].items():
  matches=[run for run in runs if rid in run['input']['cases']and run['input']['cases'][rid]['sha256']==case['sha256']]
  assert matches,'No actual replay of selected input: '+rid
  outcomes={bool(run['results'][rid]['pass'])for run in matches};assert len(outcomes)==1,'Conflicting outcomes for identical input: '+rid
  chosen=matches[-1];result=chosen['results'][rid]
  rows.append(dict(id=rid,pass_=bool(result['pass']),input_sha256=case['sha256'],selected_actual_run=chosen['name'],identical_actual_runs=[r['name']for r in matches],result=result))
 return dict(cases=rows,passed=sum(r['pass_']for r in rows),failed=sum(not r['pass_']for r in rows),prior_failures_preserved=prior_failures,engine_version=engine,settings=settings)
def check_refs(value):
 if isinstance(value,dict):
  if 'path'in value and'sha256'in value:
   p=pathlib.Path(value['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==value['sha256'],str(p)
  for v in value.values():check_refs(v)
 elif isinstance(value,list):
  for v in value:check_refs(v)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--selection',type=pathlib.Path,required=True);ap.add_argument('--runs',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);q=ap.parse_args();selected_path=q.selection.resolve();entries=read(q.runs.resolve());check_refs(entries);selected=ci.manifest(selected_path);runs=[]
 for entry in entries['runs']:
  p=ROOT/entry['prepared']['path'];rp=ROOT/entry['report']['path'];runs.append(dict(name=entry['name'],input=ci.manifest(p),report=read(rp),prepared_sha256=sha(p)))
 for p in entries['source_handoffs']:
  check_refs(read(ROOT/p['path']))
 result=certify(selected,runs);oldids=set(runs[0]['input']['cases']);original=[r for r in result['cases']if r['id']in oldids];add=[r for r in result['cases']if r['id']not in oldids]
 out=dict(schema='riverstone.strict_case_level_certified_actual_results.v2',status='ALL_SELECTED_CASES_PASS'if not result['failed']else'SELECTED_FAILURES_RETAINED',selected=ref(selected_path),run_sources=entries,implementation=ref(pathlib.Path(__file__)),identity_implementation=ref(B/'case_input_certification_r01/case_inputs.py'),original481=dict(cases=len(original),passed=sum(r['pass_']for r in original)),additive=dict(cases=len(add),passed=sum(r['pass_']for r in add)),**result,limits=['Every selected case is tied to an exact transitive runtime-input digest and an actual uninstrumented-controller report. No sum of unrelated focused passes substitutes for identity.','All previous failures and their exact input hashes remain in this report. A changed case can pass only from its own selected-input replay.','Visible source scene2d53ca4a remains exact. Selected collision inputs additionally bind the complete EAST_RADIAL shared-frame recipe, finite Civic/East-wall/B003 correction, and training continuous contract. These derived recipes must ship with the scene.','All seven original named full-chain goals are individually tracked. Castle includes the explicitly bound1.5m² visible/collision sill sidecar; source scene2d53 remains unchanged and must be delivered with that addendum.'])
 write(q.output.resolve(),out);print(json.dumps(dict(output=ref(q.output.resolve()),original481=out['original481'],additive=out['additive'],failed=result['failed'])))
if __name__=='__main__':main()
