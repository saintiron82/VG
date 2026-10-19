"""Incremental, immutable-revision authoring of source-equivalent far roof visuals.

No production catalog writes. An explicit new revision pins selected missing-near
inputs. Exact completed revisions are verified and skipped, never regenerated.
"""
from pathlib import Path
import argparse,contextlib,copy,fcntl,hashlib,json,os,re,subprocess,sys,time
A=Path(__file__).resolve().parent;ROOT=A.parent;R=next(p for p in ROOT.parents if(p/'voxel_character/common/core.py').is_file());U=ROOT.parent;C=U.parents[1]
sys.path[:0]=[str(ROOT/'expansion_r01'),str(A)]
import input_contract_r02 as ic
from manifest import prepare as prepare_manifest
CATALOG=C/'playable_detail_r01/near_catalog.json';INDEX=C/'playable_r01/generated/tile_r01/index.json';MAPPING=U/'surface_mapping/material_surface_map.v1.json'
OUTPUT_ROOT=ROOT
CAP=30*1024*1024
class Refused(ValueError):pass
def need(ok,why):
 if not ok:raise Refused(why)
def load(p):return json.loads(Path(p).read_bytes())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def ref(p):p=Path(p);return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def write(p,data):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');tmp.replace(p)
def verify_ref(x):
 p=R/x['path'];need(p.is_file()and sha(p)==x['sha256'],'CHANGED_FILE: '+x['path']);return p
def size(p):return sum(x.stat().st_size for x in p.rglob('*')if x.is_file())
def check_cap(out):need(size(out)<=CAP,'OUTPUT_CAP_EXCEEDED')
def method():
 files=[A/'author_far_batch.py',A/'build_one.py',A/'manifest.py',A/'godot/validate.gd',A/'godot/RenderData.gd',A/'godot/project.godot',ROOT/'source_surface_adapter.py',ROOT/'expansion_r01/input_contract.py',A/'input_contract_r02.py',A/'source_bounds.py',U/'build_near_catalog.py',U/'build_facility_catalog.py',U/'facility_roofs/author_facility_roofs.py',U/'facility_roofs/validate_facility_roofs.py',U/'house_rules/adapter.py',R/'voxel_character/common/core.py',R/'voxel_character/tools/mesh.py',R/'world_city/runtime_city/topography/author.py']
 need((A/'godot/RenderData.gd').read_bytes()==(C/'playable_detail_r01/RenderData.gd').read_bytes(),'SHARED_RENDERER_CHANGED: update reviewed tool version first')
 return [ref(p)for p in files]
def pin(key,cat,idx,mapping):
 need(re.fullmatch(r'[A-Za-z0-9_-]{1,128}',key)is not None,'UNSAFE_ASSET_KEY')
 need(key in cat and key in idx and key in mapping,'MISSING_REGISTERED_SOURCE_OR_MAPPING: '+key)
 e=cat[key];s=idx[key];m=mapping[key]
 need(not e.get('source_revision'),'SOURCE_REVISED_NEAR_REQUIRES_SEPARATE_CONTRACT: '+key)
 need(e.get('source_master_sha256')==s['master_sha256']==m['master_sha256'],'SOURCE_NEAR_IDENTITY_MISMATCH: '+key)
 p={'asset_key':key,'source_master':{'path':s['master_path'],'sha256':s['master_sha256']},'baseline_far_render':{'path':s['render_path'],'sha256':s['render_sha256']},'near_render':{'path':e['render_path'],'sha256':e['sha256']},'near_source_master_sha256':e['source_master_sha256'],'source_index_entry_sha256':ic.core.digest(s),'mapping_entry_sha256':ic.core.digest(m)}
 for field in ['source_master','baseline_far_render','near_render']:verify_ref(p[field])
 return p
def inputs():return load(CATALOG)['assets'],load(INDEX)['common_assets'],load(MAPPING)['assets']
def verify_pins(lock):
 cat,idx,mapping=inputs()
 for old in lock['pins']:need(pin(old['asset_key'],cat,idx,mapping)==old,'CHANGED_INPUT: '+old['asset_key'])
 need(method()==lock['method'],'CHANGED_AUTHORING_METHOD: use a new reviewed revision')
def artifact_refs(out,key):return [ref(out/key/n)for n in ['input.contract.json','candidate.render.json.gz','candidate.provenance.json']if(out/key/n).is_file()]
def verify_candidate(out,key):
 # Independent identity/nonroof replay; frozen builder already audits CSG topology.
 import gzip
 p=load(out/key/'candidate.provenance.json');need(p['asset_key']==key and p['all_geometry_tests_pass']and all(p['tests'].values()),'GEOMETRY_FAILURE: '+key)
 pin=next(x for x in load(out/'input.lock.json')['pins']if x['asset_key']==key)
 need(p['source_master']==pin['source_master']and p['baseline_far_render']==pin['baseline_far_render'],'CANDIDATE_SOURCE_DIFFERS_FROM_PIN: '+key)
 inp=load(verify_ref(p['input_contract']));need(inp['source_master']==pin['source_master']and inp['baseline_far_render']==pin['baseline_far_render'],'INPUT_CONTRACT_SOURCE_DIFFERS_FROM_PIN: '+key)
 base_path=verify_ref(p['baseline_far_render']);render_path=verify_ref(p['render']);verify_ref(p['source_master'])
 need(inp['schema']=='riverstone.source_roof_lod_input.v1'and inp['status']=='SUPPORTED_INPUT_UNBUILT'and inp['asset_key']==key,'INVALID_INPUT_CONTRACT: '+key)
 def render(path):return json.loads(gzip.decompress(path.read_bytes())if path.suffix=='.gz'else path.read_bytes())
 base=render(base_path);data=render(render_path)
 need(data['provenance']['source_master']==pin['source_master']and data['provenance']['baseline_far_render']==pin['baseline_far_render'],'RENDER_SOURCE_DIFFERS_FROM_PIN: '+key)
 mats=set(inp['materials'])
 need({g['material']:g for g in base['groups']if g['material']not in mats}=={g['material']:g for g in data['groups']if g['material']not in mats},'NONROOF_CHANGED: '+key)
 need(base['materials']==data['materials'],'PALETTE_CHANGED: '+key)
 for x in data['provenance'].values():
  if isinstance(x,dict)and 'path'in x:verify_ref(x)
 return p

def reject_output_symlinks(out):
 need(not out.is_symlink(),'SYMLINK_OUTPUT_REFUSED')
 if out.exists():need(not any(p.is_symlink()for p in out.rglob('*')),'SYMLINK_OUTPUT_MEMBER_REFUSED')
@contextlib.contextmanager
def writer_lock(out):
 reject_output_symlinks(out)
 fd=os.open(out/'.writer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
 try:
  try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise Refused('REVISION_ALREADY_HAS_ACTIVE_WRITER')
  yield fd
 finally:os.close(fd)
def skip_complete(out,keys):
 reject_output_symlinks(out);done=load(out/'complete.json')
 for x in done['artifacts']:verify_ref(x)
 return {'status':'SKIPPED_EXACT_COMPLETE','asset_keys':keys,'output_revision':str(out.relative_to(R)),'manifest':done.get('manifest'),'no_writes':True}

def run(args):
 need(re.fullmatch(r'[a-z][a-z0-9_]{2,63}',args.output_revision)is not None,'INVALID_OUTPUT_REVISION')
 need(1<=args.max_assets<=32,'MAX_ASSETS_OUT_OF_RANGE_1_TO_32')
 raw_out=OUTPUT_ROOT/args.output_revision;need(not raw_out.is_symlink(),'SYMLINK_OUTPUT_REFUSED')
 out=raw_out.resolve();need(out.parent==OUTPUT_ROOT.resolve()and out!=A.resolve(),'OUTPUT_MUST_BE_NEW_DIRECT_REVISION')
 reject_output_symlinks(out)
 lock_path=out/'input.lock.json';cat,idx,mapping=inputs()
 if out.exists():
  need(lock_path.is_file(),'EXISTING_UNMANAGED_REVISION_REFUSED: '+str(out))
  lock=load(lock_path);keys=lock['asset_keys'];need(len(keys)<=args.max_assets,'PINNED_BATCH_EXCEEDS_MAX_ASSETS')
  if args.asset_key:need(set(args.asset_key)==set(keys),'PINNED_SELECTION_CHANGED: choose a new output revision')
  verify_pins(lock)
  if(out/'complete.json').is_file():return skip_complete(out,keys)
 else:
  missing=sorted(k for k,e in cat.items()if not e.get('far_visual_contract_path'))
  keys=sorted(set(args.asset_key or missing))
  need(set(keys)<=set(missing),'SELECTED_ASSET_ALREADY_HAS_FAR_OR_IS_NOT_REGISTERED')
  need(len(keys)<=args.max_assets,'MISSING_SET_EXCEEDS_MAX_ASSETS: use explicit --asset-key selection')
  if not keys:return {'status':'NO_MISSING_NEAR_ASSETS','asset_keys':[],'no_writes':True}
  pins=[pin(k,cat,idx,mapping)for k in keys]
  lock={'schema':'riverstone.source_roof_authoring_lock.v1','asset_keys':keys,'pins':pins,'method':method(),'selection':'currently registered near assets missing far_visual_contract_path','catalog_observed':ref(CATALOG),'city_index_observed':ref(INDEX),'output_cap_bytes':CAP,'runtime_activation':False}
  out.mkdir();write(lock_path,lock)
 with writer_lock(out)as writer_fd:
  verify_pins(lock)
  if(out/'complete.json').is_file():return skip_complete(out,keys)
  return build_locked(out,lock,keys,cat,idx,mapping,writer_fd)

def build_locked(out,lock,keys,cat,idx,mapping,writer_fd):
 lock_path=out/"input.lock.json"
 # Lock is immutable. Unrelated catalog additions do not alter this revision.
 progress_path=out/'progress.json';progress=load(progress_path)if progress_path.exists()else {'rows':[]};rows={r['asset_key']:r for r in progress['rows']}
 for key in keys:
  if key in rows:
   for x in rows[key]['artifacts']:verify_ref(x)
   continue
  if(out/key/'candidate.provenance.json').is_file():
   proof=verify_candidate(out,key)
   row={'asset_key':key,'status':'GEOMETRY_PASS','reason_codes':[],'artifacts':artifact_refs(out,key),'recovered_unjournaled_exact_candidate':True}
   rows[key]=row;write(progress_path,{'rows':[rows[k]for k in keys if k in rows]});continue
  need(not(out/key).exists()or not any((out/key).iterdir()),'EXISTING_PARTIAL_ASSET_REQUIRES_NEW_REVISION: '+key)
  contract=ic.inspect(key,mapping[key],idx[key],load(R/idx[key]['master_path']))
  dest=out/key;dest.mkdir(exist_ok=True)
  if contract['status']!='SUPPORTED_INPUT_UNBUILT':
   write(dest/'input.contract.json',contract);row={'asset_key':key,'status':contract['status'],'reason_codes':contract['reason_codes'],'artifacts':artifact_refs(out,key)}
  else:
   try:
    p=subprocess.run([sys.executable,str(A/'build_one.py'),key,'--output',str(out),'--writer-fd',str(writer_fd)],pass_fds=(writer_fd,),cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=30)
    (dest/'build.log').write_text(p.stdout+p.stderr)
    proof=load(dest/'candidate.provenance.json')if(dest/'candidate.provenance.json').exists()else {}
    okay=p.returncode==0 and proof.get('all_geometry_tests_pass',False)
    row={'asset_key':key,'status':'GEOMETRY_PASS'if okay else 'UNSUPPORTED_BUILD_OR_GEOMETRY','reason_codes':[]if okay else proof.get('reason_codes',['BOUNDED_BUILD_FAILED']),'artifacts':artifact_refs(out,key)}
   except subprocess.TimeoutExpired:
    (dest/'build.log').write_text('30-second per-asset build limit reached\n');row={'asset_key':key,'status':'UNSUPPORTED_BUILD_LIMIT','reason_codes':['BOUNDED_BUILD_TIMEOUT'],'artifacts':artifact_refs(out,key)}
  rows[key]=row;write(progress_path,{'rows':[rows[k]for k in keys if k in rows]});check_cap(out)
  print(json.dumps({'asset_key':key,'status':row['status']}),flush=True)
 verify_pins(lock)
 good=[k for k in keys if rows[k]['status']=='GEOMETRY_PASS'];unsupported=[rows[k]for k in keys if k not in good]
 for k in good:verify_candidate(out,k)
 validation=out/'validation';validation.mkdir(exist_ok=True)
 if good:
  start=time.monotonic();p=subprocess.run(['godot','--headless','--path',str(A/'godot'),'--script','res://validate.gd','--',*[str(out/k/'candidate.render.json.gz')for k in good]],env={**os.environ,'OUTPUT_REPORT':str(validation/'godot_validation.json'),'XDG_DATA_HOME':str(validation/'userdata'),'XDG_CACHE_HOME':str(validation/'cache')},capture_output=True,text=True,timeout=30)
  (validation/'godot_validation.log').write_text(p.stdout+p.stderr)
  gv=load(validation/'godot_validation.json');need(p.returncode==0 and gv['all_pass']and len(gv['reports'])==len(good),'SHARED_GODOT_VALIDATION_FAILED')
  manifest=prepare_manifest(out,good,INDEX,CATALOG);need(manifest['all_pass'],'INTEGRATION_MANIFEST_VALIDATION_FAILED')
 else:
  write(out/'integration_manifest.json',{'schema':'riverstone.source_roof_far_lod_integration_manifest.v1','source_city_index':ref(INDEX),'all_pass':True,'entries':[],'runtime_activation':False,'actual_city_review_required':True})
 write(out/'unsupported.json',{'selected_count':len(keys),'unsupported_count':len(unsupported),'unsupported':unsupported})
 write(out/'candidate_index.json',{'schema':'riverstone.source_roof_far_lod_batch_index.v1','asset_keys':keys,'supported_verified_keys':good,'unsupported_count':len(unsupported),'rows':[rows[k]for k in keys],'input_lock':ref(lock_path),'integration_manifest':ref(out/'integration_manifest.json'),'runtime_activation':False,'actual_city_visual_reviewed':False})
 verify_pins(lock);check_cap(out)
 files=[p for p in out.rglob('*')if p.is_file()and not any(n in p.parts for n in ['cache','userdata'])and p.name!='complete.json']
 done={'schema':'riverstone.source_roof_authoring_complete.v1','status':'COMPLETE_WITH_UNSUPPORTED'if unsupported else 'COMPLETE_CANDIDATES_ONLY','asset_keys':keys,'supported_verified_count':len(good),'unsupported_count':len(unsupported),'manifest':ref(out/'integration_manifest.json'),'artifacts':[ref(p)for p in sorted(files)],'runtime_activation':False,'actual_city_visual_reviewed':False}
 write(out/'complete.json',done);check_cap(out)
 return {k:done[k]for k in ['status','asset_keys','supported_verified_count','unsupported_count','manifest','runtime_activation','actual_city_visual_reviewed']}
def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-revision',required=True);parser.add_argument('--missing-near',action='store_true',required=True);parser.add_argument('--asset-key',action='append',default=[]);parser.add_argument('--max-assets',type=int,default=8)
 try:result=run(parser.parse_args(argv));print(json.dumps(result,indent=2));return 0
 except (Refused,OSError,KeyError,ValueError,AssertionError,subprocess.TimeoutExpired)as exc:print(json.dumps({'status':'REFUSED','reason':str(exc)}),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
