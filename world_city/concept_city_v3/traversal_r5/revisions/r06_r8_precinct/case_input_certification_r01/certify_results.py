"""Certify case-level result reuse only from exact transitive input identities."""
import argparse,hashlib,json,pathlib
from case_inputs import manifest,compare,sha
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def index(rows):
 d={r['id']:r for r in rows};assert len(d)==len(rows),'Duplicate result case';return d
def certify(old,new,replay,old_report,new_report):
 assert old_report['settings']==new_report['settings'],'Changed controller settings';assert old_report['engine_version']==new_report['engine_version'],'Changed engine';assert not old_report['errors']and not new_report['errors'],'Controller errors'
 a=index(old_report['routes']);b=index(new_report['routes']);assert set(a)==set(old['cases']);assert set(b)==set(replay['cases']);assert set(b)<=set(new['cases']);cmp=compare(old,new)
 assert set(cmp['required_replay_case_ids'])<=set(b),'Changed or added case lacks actual replay'
 rows=[]
 for rid,inp in new['cases'].items():
  if rid in b:
   assert replay['cases'][rid]['sha256']==inp['sha256'],'Replayed case used different inputs';result=b[rid];source='selected_candidate_replay'
  else:
   assert rid in cmp['identical_case_ids'],'Unproved old result reuse';result=a[rid];source='baseline_exact_input_reuse'
  assert result['within_route_teleports']==0,'Within-case teleport'
  rows.append(dict(id=rid,pass_=bool(result['pass']),result_status=result['status'],input_sha256=inp['sha256'],result_source=source,prior_failure_retained=(source=='baseline_exact_input_reuse'and not result['pass']),result=result))
 return dict(comparison=cmp,cases=rows,passed=sum(r['pass_']for r in rows),failed=sum(not r['pass_']for r in rows),reused_cases=sum(r['result_source']=='baseline_exact_input_reuse'for r in rows),replayed_cases=len(b))
def main():
 ap=argparse.ArgumentParser();
 for n in ['baseline-prepared','baseline-report','selected-prepared','replay-prepared','replay-report','representation-handoff','output']:ap.add_argument('--'+n,type=pathlib.Path,required=True)
 q=ap.parse_args();ps={n:pathlib.Path(getattr(q,n.replace('-','_'))).resolve()for n in ['baseline-prepared','baseline-report','selected-prepared','replay-prepared','replay-report','representation-handoff','output']};assert ps['output'].is_relative_to(ROOT)and not ps['output'].exists();old=manifest(ps['baseline-prepared']);new=manifest(ps['selected-prepared']);rep=manifest(ps['replay-prepared']);a=read(ps['baseline-report']);b=read(ps['replay-report']);assert a['prepared_sha256']==sha(ps['baseline-prepared'])and b['prepared_sha256']==sha(ps['replay-prepared']);handoff=read(ps['representation-handoff']);assert handoff['schema']=='riverstone.equivalent_collision_extraction_handoff.v1';assert handoff['source_prepared']['sha256']==sha(ps['baseline-prepared'])and handoff['candidate_all481_prepared']['sha256']==sha(ps['selected-prepared']);assert handoff['source_scene']['sha256']==old['scene']['sha256']==new['scene']['sha256']
 def check_refs(v):
  if isinstance(v,dict):
   if 'path'in v and'sha256'in v:
    p=pathlib.Path(v['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==v['sha256']
   for x in v.values():check_refs(x)
  elif isinstance(v,list):
   for x in v:check_refs(x)
 check_refs(handoff);review_ref=handoff['source_and_runtime_checks'];review=read(ROOT/review_ref['path']);check_refs(review);assert review['replay']['sha256']==sha(ps['replay-report']);assert review['changed_route_vectors']==review['changed_controller_or_acceptance_bytes']==0 and review['source_world_roundtrip_error_m']==0 and review['every_case_same_native_terrain_frame'];assert review['native_source_faces_preserved_per_case']==504
 result=certify(old,new,rep,a,b)
 out=dict(schema='riverstone.case_level_actual_result_certification.v1',status='PASS_ALL_CERTIFIED_CASES'if result['failed']==0 else'CERTIFIED_FAILURES_RETAINED',sources={n:ref(p)for n,p in ps.items()if n!='output'},certifier=ref(pathlib.Path(__file__).resolve()),identity_implementation=ref(H/'case_inputs.py'),**result,limits=['This is an explicit case-by-case certification against selected inputs, not a relabeling of a previous whole batch.','Every changed or added case must appear in an unchanged-controller replay using exactly the selected transitive input digest. Only identical inputs may reuse an earlier actual result, and earlier failures stay failures.','Equivalent collision representation remains separately source-bound by the provided handoff. Native visuals, scene ownership and any source geometry change require their own acceptance.'])
 with ps['output'].open('x')as f:json.dump(out,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps(dict(output=ref(ps['output']),status=out['status'],cases=len(result['cases']),passed=result['passed'],failed=result['failed'],reused=result['reused_cases'],replayed=result['replayed_cases'])))
if __name__=='__main__':main()
