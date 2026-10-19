"""Main-run only: build a fresh E7 catalog candidate, never publish it.

Raw JSON fragments preserve every other asset/module row byte for byte. Source
and collision inputs are streamed twice and must remain identical. No sampling.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,os,re,resource,sys,time
H=Path(__file__).resolve().parent;R=H.parents[6]
D=R/'world_city/concept_city_v3/playable_detail_r01'
KEY='registered_precinct_noble_entry_r01_e7_retained_base'
INDEX=R/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json'
CANDIDATE_INDEX_SHA='0a3b0f037006799290449d32633fe597feac4d74997a9fe738dd4ca9fcc1a721'

def require(condition,message):
 if not condition:raise ValueError(message)
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def unique(pairs):
 result={}
 for k,v in pairs:require(k not in result,'Duplicate JSON key '+k);result[k]=v
 return result
def bad_constant(value):raise ValueError('Nonfinite JSON '+value)
DECODER=json.JSONDecoder(object_pairs_hook=unique,parse_constant=bad_constant)
def loads(data):return json.loads(data,object_pairs_hook=unique,parse_constant=bad_constant)
def payload(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False,ensure_ascii=False)+'\n').encode()
def path_for(value):
 require(isinstance(value,str)and value and '\\'not in value and ':'not in value,'Invalid repository reference')
 p=Path(value);require(not p.is_absolute()and '..'not in p.parts,'Reference must stay repository relative');out=(R/p).resolve();require(out.is_relative_to(R.resolve()),'Reference leaves repository');return out
def reference(path):return {'path':str(path.relative_to(R)),'sha256':sha(path),'bytes':path.stat().st_size}
def verify_ref(ref):
 require(isinstance(ref,dict)and isinstance(ref.get('sha256'),str)and re.fullmatch('[0-9a-f]{64}',ref['sha256']),'Invalid reference SHA')
 path=path_for(ref.get('path'));require(path.is_file()and sha(path)==ref['sha256'],'Reference hash mismatch '+str(path));return path

def whitespace(text,pos):
 while pos<len(text)and text[pos].isspace():pos+=1
 return pos
def field_span(text,key):
 pos=whitespace(text,0);require(text[pos]=='{','Root object required');pos+=1
 while True:
  pos=whitespace(text,pos)
  if text[pos]=='}':break
  name,end=DECODER.raw_decode(text,pos);pos=whitespace(text,end);require(text[pos]==':','Expected colon');start=whitespace(text,pos+1);_,end=DECODER.raw_decode(text,start)
  if name==key:return start,end
  pos=whitespace(text,end)
  if text[pos]=='}':break
  require(text[pos]==',','Expected object comma');pos+=1
 raise ValueError('Missing root field '+key)
def array_rows(text,key):
 start,end=field_span(text,key);require(text[start]=='[','Array required '+key);pos=start+1;rows=[]
 while True:
  pos=whitespace(text,pos)
  if text[pos]==']':break
  first=pos;row,pos=DECODER.raw_decode(text,pos);require(isinstance(row,dict),'Object rows required');rows.append((row,first,pos,text[first:pos].encode()))
  pos=whitespace(text,pos)
  if text[pos]==']':break
  require(text[pos]==',','Expected array comma');pos+=1
 require(pos+1==end,'Unexpected array end');return rows,start,end

def replace_field(text,key,value):
 start,end=field_span(text,key);return text[:start]+payload(value).decode().strip()+text[end:]
def rows_by(rows,key):
 result={}
 for row,start,end,raw in rows:require(row[key]not in result,'Duplicate row '+str(row[key]));result[row[key]]=(row,start,end,raw)
 return result

def original_collision_fingerprint(index,assets):
 files={str(INDEX.relative_to(R)):sha(INDEX)}
 for filename in ['CityWorld.gd','RenderData.gd']:
  p=D/filename;require(p.is_file(),'Missing original collider helper');files[str(p.relative_to(R))]=sha(p)
 for asset in assets:
  src=index['common_assets'][asset['asset_key']]
  for kind in ['master','render']:
   require(asset['source_'+kind+'_sha256']==src[kind+'_sha256'],'Indexed source changed '+asset['asset_key'])
   p=verify_ref({'path':src[kind+'_path'],'sha256':src[kind+'_sha256']});require(path_for(asset['source_'+kind+'_path'])==p,'Source reference mismatch');files[str(p.relative_to(R))]=src[kind+'_sha256']
 tiles=index['tiles'].values()if isinstance(index['tiles'],dict)else index['tiles']
 for tile in tiles:
  for kind in ['terrain','instances']:
   p=verify_ref({'path':tile[kind+'_path'],'sha256':tile[kind+'_sha256']});files[str(p.relative_to(R))]=tile[kind+'_sha256']
 manifest={'source_index_sha256':sha(INDEX),'collision_contracts_sha256':digest(payload(index.get('collision_contracts',[]))),'disabled_native_instance_ids_sha256':digest(payload(index.get('disabled_native_instance_ids',[]))),'source_and_collider_input_file_shas':files,'scope':'All indexed terrain/instance files, all 16 original asset master/render files and original CityWorld/RenderData collider helpers. No scene instantiated.'}
 return manifest,digest(payload(manifest))

def write_new(path,data):
 require(not path.exists(),'Existing output is preserved; choose another revision: '+str(path));path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb')as f:f.write(data)
 require(path.read_bytes()==data,'Write verification failed')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--revision',required=True);ap.add_argument('--expected-catalog-sha256',required=True);args=ap.parse_args();require(re.fullmatch('[a-zA-Z0-9_]{1,64}',args.revision),'Simple new revision required');require(re.fullmatch('[0-9a-f]{64}',args.expected_catalog_sha256),'Expected catalog SHA required')
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(60,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));started=time.monotonic()
 out=H/'integration'/args.revision;require(not out.exists(),'Revision already exists; no overwrite')
 catalog_path=D/'native_access_catalog.json';catalog_bytes=catalog_path.read_bytes();require(digest(catalog_bytes)==args.expected_catalog_sha256,'Production catalog changed; re-audit before proceeding');catalog=loads(catalog_bytes)
 require(catalog.get('schema')=='riverstone.native_access_detail.runtime.v1'and catalog.get('collision_change')is False,'Invalid native catalog');require(catalog.get('maximum_active_modules')==120 and catalog.get('maximum_mesh_bytes')==24000000 and catalog.get('fade_end_m')==7,'Frozen budget/fade contract changed')
 oldpp=verify_ref({'path':catalog['source_plan_path'],'sha256':catalog['source_plan_sha256']});oldcp=verify_ref({'path':catalog['module_catalog_path'],'sha256':catalog['module_catalog_sha256']});oldpb=oldpp.read_bytes();oldcb=oldcp.read_bytes();oldp=loads(oldpb);oldc=loads(oldcb)
 require(oldp.get('schema')=='riverstone.native_access_detail.plan.v1'and oldp.get('runtime_projection')is True,'Only current compact production plans are supported');require(oldc.get('schema')=='riverstone.native_access_detail.module_catalog.v1'and oldc.get('source_plan_sha256')==catalog['source_plan_sha256']and oldc.get('original_collision_unchanged')is True,'Invalid original module catalog')
 require(sha(INDEX)==catalog['source_city_index_sha256']==oldp['source_city_index_sha256'],'Source index changed');index=loads(INDEX.read_bytes())
 oldtext=oldpb.decode();assetrows,_,_=array_rows(oldtext,'assets');byasset=rows_by(assetrows,'asset_key');require(len(byasset)==16 and KEY in byasset,'Expected exactly 16 original access assets including E7')
 for asset,*_ in assetrows:
  require(asset.get('existing_collision_unchanged')is True,'Source collision contract false');proof=asset.get('full_source_proof',{});require(proof.get('asset_key')==asset['asset_key'],'Full proof key mismatch');verify_ref(proof)
  for key in ['geometry_validation','source_application_audit']:
   if key in proof:verify_ref(proof[key])
 collision_before,collision_before_sha=original_collision_fingerprint(index,[v[0]for v in assetrows])
 require(sha(H/'candidate_index.json')==CANDIDATE_INDEX_SHA,'E7 candidate index changed');candidate=loads((H/'candidate_index.json').read_bytes());require(candidate['asset_key']==KEY and candidate['all_candidate_tests_pass']is True,'Unapproved candidate');require(candidate.get('production_binding_changed')is False,'Unexpected published candidate')
 for test in candidate['tests']:require(loads(verify_ref(test).read_bytes()).get('all_pass')is True,'Candidate validation failed')
 newpp=verify_ref(candidate['runtime_source_plan']);newcp=verify_ref(candidate['runtime_module_catalog']);newp=loads(newpp.read_bytes());newc=loads(newcp.read_bytes());require(newp.get('runtime_projection')is True and len(newp['assets'])==1,'Single compact candidate required');newasset=newp['assets'][0];require(newasset['asset_key']==KEY and newc['source_plan_sha256']==sha(newpp),'Candidate source binding mismatch');verify_ref(newasset['full_source_proof'])
 full=loads(verify_ref(candidate['full_source_plan']).read_bytes());require(len(full['assets'])==1 and full['assets'][0]['asset_key']==KEY,'Full source proof asset mismatch');fullasset=full['assets'][0]
 projection=loads(verify_ref(candidate['tests'][-1]).read_bytes());require(projection.get('copied_asset_fields')is not None,'Missing projection field contract')
 for field in projection['copied_asset_fields']:require(newasset[field]==fullasset[field],'Projection altered field '+field)
 original=byasset[KEY][0]
 for field in ['asset_key','source_master_path','source_master_sha256','source_render_path','source_render_sha256','existing_collision_unchanged','rule']:require(original[field]==newasset[field],'Replacement changed original source/semantic field '+field)
 require(len(original['placements'])==170 and len(newasset['placements'])==307,'Unexpected replacement counts');require(all(p.get('collision_changed')is False for p in newasset['placements']),'New collision requested')
 for asset,*_ in assetrows:
  for placement in asset['placements']:require(placement.get('collision_changed')is False,'Existing collision flag changed')
 moduletext=oldcb.decode();modrows,_,_=array_rows(moduletext,'modules');bymodule=rows_by(modrows,'id');newrows=rows_by(array_rows(newcp.read_text(),'modules')[0],'id');add=[]
 for key,(row,_,_,raw)in newrows.items():
  if key in bymodule:require(row==bymodule[key][0],'Existing shared module definition changed '+key)
  else:add.append(raw)
  for kind in ['master','render']:
   file=verify_ref({'path':row[kind+'_path'],'sha256':row[kind+'_sha256']})
   if 'decoded_'+kind+'_sha256'in row:
    with gzip.open(file,'rb')as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
    require(h==row['decoded_'+kind+'_sha256'],'Decoded geometry SHA mismatch')
 require(len(add)==216 and len(newrows)==223,'Unexpected new module demand')
 for row,*_ in modrows:
  for kind in ['master','render']:verify_ref({'path':row[kind+'_path'],'sha256':row[kind+'_sha256']})
 require(all(p['module_key']in bymodule for a,*_ in assetrows for p in a['placements']),'Original unbound placement')
 require(all(p['module_key']in newrows for p in newasset['placements']),'Candidate unbound placement')
 # Preserve all non-E7 asset fragments verbatim, including numeric spelling.
 _,start,end,_=byasset[KEY];mergedtext=oldtext[:start]+payload(newasset).decode().strip()+oldtext[end:];mergedtext=replace_field(mergedtext,'revision',args.revision);mergedpb=mergedtext.encode();mergedp=loads(mergedpb);after_assets=rows_by(array_rows(mergedtext,'assets')[0],'asset_key')
 require(set(after_assets)==set(byasset),'Asset list changed');unchanged_assets=[]
 for key,(row,_,_,raw)in byasset.items():
  if key==KEY:continue
  require(raw==after_assets[key][3],'Other asset raw bytes changed '+key);unchanged_assets.append({'asset_key':key,'raw_row_sha256':digest(raw),'raw_row_bytes':len(raw)})
 require(after_assets[KEY][0]==newasset,'Replacement differs from candidate')
 # Add definitions only; preserve every old module row, even if now unused.
 _,_,end=array_rows(moduletext,'modules');mergedmodtext=moduletext[:end-1]+(','if modrows and add else '')+','.join(raw.decode()for raw in add)+moduletext[end-1:];mergedmodtext=replace_field(mergedmodtext,'source_plan_sha256',digest(mergedpb));mergedcb=mergedmodtext.encode();after_modules=rows_by(array_rows(mergedmodtext,'modules')[0],'id')
 require(len(after_modules)==len(bymodule)+216,'Unexpected merged module count');require(all(v[3]==after_modules[k][3]for k,v in bymodule.items()),'Existing module raw row changed')
 pp=out/'source_plan.json';cp=out/'modules.json';candidate_catalog=copy.deepcopy(catalog);candidate_catalog.update({'binding_revision':args.revision,'source_plan_path':str(pp.relative_to(R)),'source_plan_sha256':digest(mergedpb),'module_catalog_path':str(cp.relative_to(R)),'module_catalog_sha256':digest(mergedcb)})
 mutable={'binding_revision','source_plan_path','source_plan_sha256','module_catalog_path','module_catalog_sha256'};require({k:v for k,v in catalog.items()if k not in mutable}=={k:v for k,v in candidate_catalog.items()if k not in mutable},'Catalog settings changed')
 # Refuse concurrent source/catalog changes before creating any output.
 require(catalog_path.read_bytes()==catalog_bytes and oldpp.read_bytes()==oldpb and oldcp.read_bytes()==oldcb,'Production inputs changed while preparing');require(sha(INDEX)==catalog['source_city_index_sha256'],'Source index changed while preparing')
 out.mkdir(parents=True,exist_ok=False)
 for filename,data in [('before/native_access_catalog.json',catalog_bytes),('before/source_plan.json',oldpb),('before/modules.json',oldcb),('source_plan.json',mergedpb),('modules.json',mergedcb),('native_access_catalog.candidate.json',payload(candidate_catalog))]:write_new(out/filename,data)
 before_refs={'catalog':reference(catalog_path),'plan':reference(oldpp),'modules':reference(oldcp)};write_new(out/'before/input_refs.json',payload(before_refs))
 collision_after,collision_after_sha=original_collision_fingerprint(index,[v[0]for v in assetrows]);require(collision_after==collision_before and collision_after_sha==collision_before_sha,'Original collision inputs changed')
 require(catalog_path.read_bytes()==catalog_bytes and oldpp.read_bytes()==oldpb and oldcp.read_bytes()==oldcb,'Production files changed during candidate write')
 require(all(write_path.read_bytes()==data for write_path,data in [(pp,mergedpb),(cp,mergedcb)]),'Merged bytes changed')
 require(time.monotonic()-started<60,'Integration exceeded 60-second bound')
 report={'all_pass':True,'asset_key':KEY,'candidate_index':reference(H/'candidate_index.json'),'production_before':before_refs,'source_plan':reference(pp),'module_catalog':reference(cp),'catalog_candidate':reference(out/'native_access_catalog.candidate.json'),'original_assets':16,'unchanged_other_assets':unchanged_assets,'other_asset_raw_byte_identity_count':len(unchanged_assets),'unchanged_module_raw_byte_identity_count':len(bymodule),'added_module_refs':216,'original_collision_input_fingerprint_before':collision_before_sha,'original_collision_input_fingerprint_after':collision_after_sha,'original_collision_manifest':collision_before,'source_collision_inputs_unchanged':True,'existing_active_cap':120,'existing_mesh_budget_bytes':24000000,'production_files_written':False,'catalog_published':False,'runtime_patch_applied':False,'sampler_run':False,'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'address_space_limit_bytes':256*1024*1024,'author':reference(Path(__file__))}
 write_new(out/'validation.json',payload(report));print(json.dumps({'all_pass':True,'catalog_candidate':report['catalog_candidate'],'validation':reference(out/'validation.json'),'other_assets_byte_identical':len(unchanged_assets),'collision_inputs_unchanged':True,'production_files_written':False},indent=2))

if __name__=='__main__':
 try:main()
 except Exception as exc:print('REFUSED: '+str(exc),file=sys.stderr);raise
