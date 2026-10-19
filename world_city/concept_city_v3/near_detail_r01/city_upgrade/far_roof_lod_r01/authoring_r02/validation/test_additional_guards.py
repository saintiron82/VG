from pathlib import Path
import argparse,contextlib,copy,fcntl,hashlib,io,json,os,subprocess,sys
V=Path(__file__).resolve().parent;A=V.parent;R=next(p for p in A.parents if(p/'voxel_character/common/core.py').is_file());sys.path.insert(0,str(A));import author_far_batch as author
F=V/'incremental_fixtures_r02';out=F/'outputs/candidate_batch_r01';author.OUTPUT_ROOT=F/'outputs';author.CATALOG=F/'catalog.json';keys=json.loads((out/'input.lock.json').read_text())['asset_keys'];rows=[]
def load(p):return json.loads(p.read_bytes())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def refuse(name,fn):
 try:
  with contextlib.redirect_stdout(io.StringIO()):fn()
  rows.append({'name':name,'pass':False,'error':'accepted'})
 except (author.Refused,ValueError,AssertionError)as e:rows.append({'name':name,'pass':True,'error':str(e)})
args=argparse.Namespace(output_revision='candidate_batch_r01',asset_key=[],max_assets=8,missing_near=True)
original=author.MAPPING;mapping=load(original);mapping={'assets':{k:mapping['assets'][k]for k in keys}};mapping['assets'][keys[0]]['pitch_m']=0.25;p=F/'changed_mapping.json';write(p,mapping);author.MAPPING=p;refuse('changed_mapping_entry_refused',lambda:author.run(args));author.MAPPING=original
proof=out/keys[0]/'candidate.provenance.json';saved=proof.read_bytes();bad=load(proof);lock=load(out/'input.lock.json');other=next(p for p in lock['pins']if p['asset_key']!=keys[0]);bad['source_master']=other['source_master'];write(proof,bad)
try:refuse('valid_but_other_source_ref_cross_pin_rejected',lambda:author.verify_candidate(out,keys[0]))
finally:proof.write_bytes(saved)
busy=F/'outputs/busy_revision_r01';key=load(busy/'input.lock.json')['asset_keys'][0];fd=os.open(busy/('.asset_'+key+'.lock'),os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 p=subprocess.run([sys.executable,str(A/'build_one.py'),key,'--output',str(busy)],capture_output=True,text=True,timeout=30);rows.append({'name':'active_asset_writer_refused','pass':p.returncode!=0 and 'active writer'in p.stderr,'error':p.stderr.splitlines()[-1]if p.stderr else ''})
finally:os.close(fd)
report={'all_pass':all(r['pass']for r in rows),'case_count':len(rows),'cases':rows,'author_sha256':author.sha(A/'author_far_batch.py'),'builder_sha256':author.sha(A/'build_one.py')};write(V/'additional_guards_r02.json',report);print(json.dumps(report,indent=2));raise SystemExit(0 if report['all_pass']else 2)
