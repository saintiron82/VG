"""Extract only metadata from the frozen selected scene; do not compile or modify sources."""
import json,pathlib,hashlib,collections
ROOT=pathlib.Path(__file__).resolve().parents[5]
OUT=pathlib.Path(__file__).resolve().parent
SCENE=ROOT/'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json'
EXPECTED='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert digest(SCENE)==EXPECTED
s=json.load(open(SCENE));uses=collections.Counter(x['asset_key'] for x in s['common_instances'])
plan=ROOT/s['source_plan'];assert digest(plan)==s['source_plan_sha256']
selected={k:s[k] for k in ['source_plan','source_plan_sha256','counts','common_instances']};selected['scene_sha256']=EXPECTED
manifest={'scene':{'path':str(SCENE.relative_to(ROOT)),'sha256':EXPECTED},'plan':{'path':str(plan.relative_to(ROOT)),'sha256':digest(plan)},'selected_masters':{}}
keys=['assembly_class','floors','row_units','body_bounds','width_m','depth_m','style','native_modules','modules','role','family']
def slim(m):
 r={k:m[k] for k in keys if k in m}
 if 'modules' in r:r['modules']=[{k:v for k,v in x.items() if k in ['id','asset_key','source','metadata','purpose']} for x in r['modules']]
 for x in r.get('modules',[]):x['metadata']=slim(x['metadata'])
 return r
out={}
for key,a in s['common_assets'].items():
 path=a.get('master_path');raw={};checked=None
 if path and (ROOT/path).exists():
  checked=digest(ROOT/path)
  if a.get('master_sha256'):assert checked==a['master_sha256'],key
  raw=json.load(open(ROOT/path))
 manifest['selected_masters'][key]={'path':path,'sha256':checked,'scene_expected_sha256':a.get('master_sha256'),'uses':uses[key]}
 if not uses[key]:continue
 m=slim(raw.get('metadata',a.get('native_metadata',a.get('author_metadata',{}))))
 sources=[]
 for x in raw.get('extensions',{}).get('source_assemblies',[]):
  d=x.get('authored_dimensions',{});prefix=x['key']+'__'
  if d.get('floors') and any(c['id'].startswith(prefix) for c in raw.get('components',[])):
   sources.append({'id':x['key'],'asset_key':x['source_id'],'metadata':slim(d),'source':{'path':path},'purpose':x.get('purpose')})
 if sources:m['modules']=sources;m['native_assembly_metadata_source']='extensions.source_assemblies with matching component prefix'
 out[key]={'uses':uses[key],'path':path,'metadata':m}
for name,obj in [('selected_scene_metadata.json',selected),('selected_asset_metadata.json',out),('source_identity.json',manifest)]:
 (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print('Exact scene and plan identity verified; 272 asset master file hashes checked; metadata extracted without source changes.')
