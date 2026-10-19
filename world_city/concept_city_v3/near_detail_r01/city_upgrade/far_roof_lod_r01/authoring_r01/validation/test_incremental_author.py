"""Isolated registry metadata; shared source assets are read-only, never duplicated."""
from pathlib import Path
import argparse,contextlib,copy,hashlib,importlib.util,io,json,sys
V=Path(__file__).resolve().parent;A=V.parent;R=next(p for p in A.parents if(p/'voxel_character/common/core.py').is_file());C=R/'world_city/concept_city_v3';F=V/'incremental_fixtures_r04';F.mkdir(exist_ok=True)
sys.path.insert(0,str(A));import author_far_batch as author
KEYS=['registered_cathedral_north_cloister_range','attached_native_row_0dfc8fc7367b4c']
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
watched=[C/'playable_detail_r01/near_catalog.json',C/'playable_r01/generated/tile_r01/index.json',A.parent/'expansion_r01/integration_manifest.json',A.parent/'expansion_r02/integration_manifest.json'];before={str(p):sha(p)for p in watched}
cat=load(C/'playable_detail_r01/near_catalog.json');fixture={'assets':{k:{n:v for n,v in cat['assets'][k].items()if not n.startswith('far_visual_')}for k in KEYS}}
cp=F/'catalog.json';write(cp,fixture);author.CATALOG=cp;author.OUTPUT_ROOT=F/'outputs';author.OUTPUT_ROOT.mkdir(exist_ok=True)
rows=[]
def args(rev='candidate_batch_r01',keys=None,limit=8):return argparse.Namespace(output_revision=rev,asset_key=keys or [],max_assets=limit,missing_near=True)
def check(name,a,expected,expected_status=None):
 try:
  with contextlib.redirect_stdout(io.StringIO())as capture:result=author.run(a)
  accepted=True;error='';status=result['status']
 except (author.Refused,ValueError,AssertionError,KeyError,OSError)as exc:accepted=False;error=type(exc).__name__+': '+str(exc);status='REFUSED';result=None
 okay=accepted==expected and(expected_status is None or status==expected_status)
 rows.append({'name':name,'pass':okay,'accepted':accepted,'status':status,'error':error,'result':result})
 print(json.dumps(rows[-1]),flush=True)
 return result
check('bounded_limit_rejects_without_output',args(limit=1),False)
check('missing_selection_builds_two',args(),True,'COMPLETE_CANDIDATES_ONLY')
out=author.OUTPUT_ROOT/'candidate_batch_r01';snapshot={str(p.relative_to(out)):(sha(p),p.stat().st_mtime_ns)for p in out.rglob('*')if p.is_file()}
check('exact_completed_skip_no_writes',args(),True,'SKIPPED_EXACT_COMPLETE');after={str(p.relative_to(out)):(sha(p),p.stat().st_mtime_ns)for p in out.rglob('*')if p.is_file()};rows[-1]['output_bytes_and_mtimes_unchanged']=snapshot==after;rows[-1]['pass']&=snapshot==after
check('selection_change_refused',args(keys=[KEYS[0]]),False)
for field,mode in [('sha256','changed_near_sha'),('source_master_sha256','changed_near_source_sha'),('render_path','changed_near_path')]:
 bad=copy.deepcopy(fixture);bad['assets'][KEYS[0]][field]='wrong';write(cp,bad);check(mode,args(),False);write(cp,fixture)
original_index=author.INDEX;ip=F/'index.json';idx=load(original_index);idx={'common_assets':{k:idx['common_assets'][k]for k in KEYS}}
for field,mode in [('master_sha256','changed_master_sha'),('render_sha256','changed_original_far_sha')]:
 bad=copy.deepcopy(idx);bad['common_assets'][KEYS[0]][field]='wrong';write(ip,bad);author.INDEX=ip;check(mode,args(),False);author.INDEX=original_index
render=out/KEYS[0]/'candidate.render.json.gz';data=render.read_bytes();render.write_bytes(data+b'changed');check('changed_completed_output_refused',args(),False);render.write_bytes(data)
# Later runtime binding of the exact assets does not cause rebuild or forget pinned keys.
bound=copy.deepcopy(fixture)
for e in bound['assets'].values():e['far_visual_contract_path']='bound-after-review'
write(cp,bound);check('exact_resume_after_binding_skips',args(),True,'SKIPPED_EXACT_COMPLETE');check('new_revision_with_no_missing_no_write',args('candidate_batch_empty'),True,'NO_MISSING_NEAR_ASSETS');rows[-1]['pass']&=not(author.OUTPUT_ROOT/'candidate_batch_empty').exists();write(cp,fixture)
for revision in ['../escape','/tmp/escape','xx'] :check('unsafe_revision_'+revision,args(revision),False)
unmanaged=author.OUTPUT_ROOT/'unmanaged_r01';unmanaged.mkdir(exist_ok=True);(unmanaged/'sentinel').write_text('keep');check('unmanaged_existing_revision_refused',args('unmanaged_r01'),False);rows[-1]['pass']&=(unmanaged/'sentinel').read_text()=='keep'
# A newly added asset is not silently included in a resumed frozen revision.
more=copy.deepcopy(fixture);extra=next(k for k in cat['assets']if k not in KEYS);more['assets'][extra]={k:v for k,v in cat['assets'][extra].items()if not k.startswith('far_visual_')};write(cp,more);check('unrelated_new_missing_asset_does_not_expand_resume',args(),True,'SKIPPED_EXACT_COMPLETE');write(cp,fixture)
import subprocess,fcntl,os
# Existing directory symlink must be rejected before traversal/writes.
link=author.OUTPUT_ROOT/'symlink_revision';link.symlink_to(out,target_is_directory=True)
check('symlink_revision_refused',args('symlink_revision'),False)
member=out/'redirect';member.symlink_to(out/KEYS[0],target_is_directory=True)
check('symlink_member_refused',args(),False);member.unlink()
# Simulate an interrupted revision by copying only locks and a completed asset's
# small generated files (never original source assets), then remove progress.
recovery=author.OUTPUT_ROOT/'recover_crash_r01';recovery.mkdir(exist_ok=True)
lock=load(out/'input.lock.json');lock['asset_keys']=[KEYS[0]];lock['pins']=[p for p in lock['pins']if p['asset_key']==KEYS[0]];write(recovery/'input.lock.json',lock)
# First run builds normally; then simulate missing progress/complete while retaining exact candidate.
check('recovery_fixture_positive',args('recover_crash_r01',keys=[KEYS[0]]),True,'COMPLETE_CANDIDATES_ONLY')
(recovery/'complete.json').unlink();(recovery/'progress.json').unlink()
retained={n:(sha(recovery/KEYS[0]/n),(recovery/KEYS[0]/n).stat().st_mtime_ns)for n in ['candidate.render.json.gz','candidate.provenance.json','input.contract.json']}
check('crash_after_candidate_before_progress_recovers_without_rebuild',args('recover_crash_r01',keys=[KEYS[0]]),True,'COMPLETE_CANDIDATES_ONLY')
rows[-1]['pass']&=retained=={n:(sha(recovery/KEYS[0]/n),(recovery/KEYS[0]/n).stat().st_mtime_ns)for n in retained}
# Refuse active revision writer before any candidate writes.
busy=author.OUTPUT_ROOT/'busy_revision_r01';busy.mkdir(exist_ok=True);write(busy/'input.lock.json',lock)
fd=os.open(busy/'.writer.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
check('active_revision_writer_refused',args('busy_revision_r01',keys=[KEYS[0]]),False)
p=subprocess.run([sys.executable,str(A/'build_one.py'),KEYS[0],'--output',str(busy)],capture_output=True,text=True,timeout=30)
rows.append({'name':'direct_child_respects_batch_revision_lock','pass':p.returncode!=0 and 'revision already has active writer'in p.stderr,'returncode':p.returncode,'error':p.stderr.splitlines()[-1]if p.stderr else ''});os.close(fd)
for name,target in [('direct_child_rejects_old_r01',A.parent/'expansion_r01'),('direct_child_rejects_old_r02',A.parent/'expansion_r02'),('direct_child_rejects_completed_revision',out)]:
 p=subprocess.run([sys.executable,str(A/'build_one.py'),KEYS[0],'--output',str(target)],capture_output=True,text=True)
 rows.append({'name':name,'pass':p.returncode!=0,'returncode':p.returncode,'error':p.stderr.splitlines()[-1]if p.stderr else ''})
need_preserved=before=={str(p):sha(p)for p in watched};report={'all_pass':all(r['pass']for r in rows)and need_preserved,'case_count':len(rows),'cases':rows,'watched_production_and_old_revision_hashes_unchanged':need_preserved,'author_sha256':sha(A/'author_far_batch.py'),'shared_builder_sha256':sha(A/'build_one.py'),'shared_manifest_sha256':sha(A/'manifest.py'),'fixture_output_bytes':sum(p.stat().st_size for p in F.rglob('*')if p.is_file())}
write(V/'incremental_author_tests_r04.json',report);print(json.dumps({'all_pass':report['all_pass'],'case_count':len(rows),'fixture_output_bytes':report['fixture_output_bytes']}));raise SystemExit(0 if report['all_pass']else 2)
