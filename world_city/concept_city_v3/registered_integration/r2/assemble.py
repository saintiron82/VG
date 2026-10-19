"""Hash-bound orchestration of existing common geometry; no sampling or core edits."""
import json,copy,hashlib,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent; CITY=HERE.parents[1]; ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):
 p=Path(p);return str(p.relative_to(ROOT)) if p.is_absolute() else str(p)
def main():
 source=CITY/'registered_source/plan.json'; source_sha=sha(source)
 baseline=CITY/'registered_integration/common_city_candidate.json'; out=json.loads(baseline.read_bytes())
 assert out['source_plan_sha256']==source_sha
 for a in out['common_assets'].values():
  a.setdefault('master_sha256',a.get('master_file_sha256'))
  if 'quad_count' not in a:a['quad_count']=json.loads((ROOT/a['render_path']).read_bytes())['quad_count']
 out['schema']='riverstone.registered_integration.r2';out['status']='assemblies_and_ownership_candidate_not_final_city'
 inputs=[{'name':'preserved_common_r1','path':rel(baseline),'sha256':sha(baseline)}]
 def read(name,path):
  p=CITY/path;d=json.loads(p.read_bytes());bound=d.get('source_plan_sha256',d.get('registered_source_sha256',d.get('source_plan',{}).get('sha256')))
  assert bound==source_sha,(name,'source revision mismatch',bound);inputs.append({'name':name,'path':rel(p),'sha256':sha(p)});return d
 def asset(key,a):
  e=copy.deepcopy(a)
  if 'source' in a:e.update(master_path=a['source']['path'],master_sha256=a['source']['sha256'],render_path=a['cache']['path'],render_sha256=a['cache']['sha256'])
  else:e.update(master_path=a['master_path'],master_sha256=a.get('master_file_sha256',a.get('master_sha256')),render_path=a.get('render_path',a.get('compiled_asset_ref')),render_sha256=a['render_sha256'])
  e['master_path']=rel(e['master_path']);e['render_path']=rel(e['render_path'])
  assert sha(ROOT/e['master_path'])==e['master_sha256'],(key,'master hash')
  assert sha(ROOT/e['render_path'])==e['render_sha256'],(key,'render hash')
  e.setdefault('pitch_m',a.get('sampling_resource',{}).get('pitch',.5))
  old=out['common_assets'].get(key)
  if old and old['render_sha256']!=e['render_sha256']:
   raise ValueError('Cache key reused for different geometry: '+key)
  out['common_assets'][key]=e
 def instances(name,items):
  for p in items:
   assert p.get('scale',p.get('scale_xyz',[1,1,1]))==[1,1,1],p['id']
   q={k:copy.deepcopy(p[k]) for k in ('id','asset_key','position_m','yaw_rad','palette_id','palette_override') if k in p}
   q.setdefault('palette_id','native_'+name);q.setdefault('palette_override',{});q.update(scale=[1,1,1],source_pack=name)
   assert len(q['position_m'])==3 and q['asset_key'] in out['common_assets']
   out['common_instances'].append(q)
 def remove(ids,paths=()):
  ids=set(ids);out['common_instances']=[p for p in out['common_instances'] if p['id'] not in ids]
  out['remove_proxy_ids']+=sorted(ids|{v+':support' for v in ids}|{v+':owned_foundation' for v in ids})
  out['access_overlay'].setdefault('remove_path_ids',[]).extend(paths)
 # Only the three repaired source/cache references differ from the original80.
 lm=read('landmarks_connected_finials','assemblies/landmarks/registered/repairs/r02_connected_finials/resolved_placements.json')
 old_lm_keys={p['asset_key'] for p in out['common_instances'] if p['source_pack']=='registered_landmarks'}
 out['common_instances']=[p for p in out['common_instances'] if p['source_pack']!='registered_landmarks']
 for key in old_lm_keys:out['common_assets'].pop(key,None)
 for a in lm['assets']:asset(a['id'],a)
 instances('landmarks',lm['placements'])
 prop=read('property_repaired','assemblies/property/registered/r1/repair_01/resolved_placements.json')
 for key,a in prop['asset_manifest'].items():asset(key,a)
 instances('property',prop['placements'])
 for row in prop['replacement_ledger']:
  remove(row['source_building_ids'],row['source_owned_path_ids']);out['replace_plot_ids'].append(row['property_id'])
 port=read('port','assemblies/landmarks/registered/port_r01/resolved_placements.json')
 # Full piecewise profile proof allows one visible common apron without a cut.
 proofpath=CITY/'assemblies/landmarks/registered/port_r02_ownership/finite_coownership_addendum.json'
 proof=json.loads(proofpath.read_bytes());inputs.append({'name':'port_apron_finite_coownership','path':rel(proofpath),'sha256':sha(proofpath)})
 for a in port['assets']:asset(a['id'],a)
 instances('port',port['placements'])
 remove(port['replacement_overlay']['remove_building_ids'],port['replacement_overlay']['remove_path_ids'])
 bridge=read('bridge','assemblies/waterworks/registered_bridge/resolved_placements.json')
 for key,a in bridge['assets'].items():asset(key,a)
 instances('bridge',bridge['placements'])
 market=read('market','assemblies/market/registered/resolved_placements.json')
 for key,a in market['assets'].items():asset('registered_market_'+key,a)
 items=copy.deepcopy(market['placements'])
 for p in items:p['asset_key']='registered_market_'+p['asset_key']
 instances('market',items);out['replace_landmark_groups']+=market['replace_landmark_groups']
 out['access_overlay']['replace_roads']+=market['access_overlay']['replace_roads']
 # Native property, port, and dry bridge holes are exact owners inside r04;
 # do not add broad masks that would erase water/beds below elevated wet decks.
 out['terrain_module']='world_city.concept_city_v3.registered_topography.revisions.r05_preview_lod.review'
 out['floor_ownership_masks']=[]
 ids=[p['id'] for p in out['common_instances']];assert len(ids)==len(set(ids)),'Duplicate instance IDs'
 used={p['asset_key'] for p in out['common_instances']};out['common_assets']={k:v for k,v in out['common_assets'].items() if k in used}
 for k in ('remove_proxy_ids','replace_plot_ids','replace_landmark_groups'):out[k]=sorted(set(out[k]))
 out['access_overlay']['remove_path_ids']=sorted(set(out['access_overlay']['remove_path_ids']))
 out['provenance']={'input_packs':inputs,'common_core_modified':False,'new_voxel_compile_count_by_integrator':0,'geometry_policy':'rigid placements of hash-verified common assemblies','open_exceptions':['Ordinary blocks still use sparse r0 cache dimensions; density r1 is in progress.','13 inferred alley grades are known to create deep trenches and remain under repair.','Landscape gardens and native outer fortifications are staged separately.','Native .25/.5m floor quantization requires smooth-profile collision and capsule tests.','No complete interiors, gameplay, flood or structural certification.']}
 out['counts']=dict(collections.Counter(p['source_pack'] for p in out['common_instances']));out['counts'].update(instances=len(ids),unique_assets=len(used),unique_cached_quads=sum(a.get('quad_count',0) for a in out['common_assets'].values()))
 output=HERE/'candidate.json';output.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps({'path':rel(output),'sha256':sha(output),'counts':out['counts']},indent=2))
if __name__=='__main__':main()
