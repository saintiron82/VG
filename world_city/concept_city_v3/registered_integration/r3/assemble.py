"""Compose sealed native common packs. Existing evidence and asset masters stay immutable."""
import copy,hashlib,json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):
 p=Path(p);return str(p.relative_to(ROOT)) if p.is_absolute() else str(p)
def main():
 source=CITY/'registered_source/plan.json';source_sha=sha(source);baseline=HERE.parent/'r2/candidate.json';out=json.loads(baseline.read_bytes());assert out['source_plan_sha256']==source_sha
 out['schema']='riverstone.registered_integration.r3';out['status']='native_urban_fabric_candidate_pending_visual_and_passage_review'
 inputs=[dict(name='preserved_r2_candidate',path=rel(baseline),sha256=sha(baseline))];ledgers=[]
 def read(name,path):
  p=CITY/path;d=json.loads(p.read_bytes());bound=d.get('source_plan_sha256',d.get('source_plan',d.get('sources',{}).get('plan',{})).get('sha256'))
  assert bound==source_sha,(name,'source plan mismatch',bound);inputs.append(dict(name=name,path=rel(p),sha256=sha(p)));return d
 def reference(name,r):
  p=ROOT/r['path'];assert sha(p)==r['sha256'];inputs.append(dict(name=name,**r));return json.loads(p.read_bytes())
 def asset(key,a):
  e=copy.deepcopy(a)
  if 'source' in a:e.update(master_path=a['source']['path'],master_sha256=a['source']['sha256'],render_path=a['cache']['path'],render_sha256=a['cache']['sha256'])
  else:e.update(master_path=a['master_path'],master_sha256=a.get('master_file_sha256',a.get('master_sha256')),render_path=a.get('render_path',a.get('compiled_asset_ref')),render_sha256=a['render_sha256'])
  for k in ('master_path','render_path'):e[k]=rel(e[k])
  assert sha(ROOT/e['master_path'])==e['master_sha256'],(key,'master changed');assert sha(ROOT/e['render_path'])==e['render_sha256'],(key,'cache changed')
  rd=json.loads((ROOT/e['render_path']).read_bytes());e.update(quad_count=rd['quad_count'],bounds=rd['bounds']);e.setdefault('pitch_m',a.get('sampling_resource',{}).get('pitch',.5))
  old=out['common_assets'].get(key);assert not old or old['render_sha256']==e['render_sha256'],('asset key collision',key)
  out['common_assets'][key]=e
 def instances(name,items):
  for p in items:
   assert p.get('scale',p.get('scale_xyz',[1,1,1]))==[1,1,1],p['id']
   q={k:copy.deepcopy(p[k]) for k in ('id','asset_key','position_m','yaw_rad','palette_id','palette_override') if k in p};q.setdefault('palette_id','native_'+name);q.setdefault('palette_override',{});q.update(scale=[1,1,1],source_pack=name)
   assert q['asset_key'] in out['common_assets'] and len(q['position_m'])==3;out['common_instances'].append(q)
 def remove(ids,paths=()):
  ids=set(ids);out['common_instances']=[p for p in out['common_instances'] if p['id'] not in ids]
  out['remove_proxy_ids']+=sorted(ids|{v+':support' for v in ids}|{v+':owned_foundation' for v in ids});out['access_overlay']['remove_path_ids']+=list(paths)
 def replace_pack(name):out['common_instances']=[p for p in out['common_instances'] if p['source_pack']!=name]
 density=read('poor_attached_rows','assemblies/ordinary/registered/r1/resolved_placements.json')
 for key,a in density['assets'].items():asset(key,a)
 remove(density['replaced_placement_ids'],density['superseded_old_path_ids']);instances('ordinary_density',density['placements'])
 ledgers.append(dict(pack='ordinary_density',rendered_groups=len(density['placements']),semantic_body_components=len(density['component_placements']),removed_body_ids=density['replaced_placement_ids'],component_records_rendered=False))
 landscape=read('institutional_gardens','assemblies/landscape/registered/resolved_placements.json')
 for key,a in landscape['asset_manifest'].items():asset(key,a)
 instances('landscape',landscape['placements'])
 fort=read('native_fortifications','assemblies/fortifications/registered/placement_r02/resolved_placements.json')
 for a in fort['assets']:asset(a['id'],a)
 instances('fortifications',fort['placements']);wall_overlay=reference('wall_proxy_supersession',fort['replacement_overlay']);out['remove_proxy_ids']+=wall_overlay['remove_box_ids']
 port=read('continuous_native_quays','assemblies/landmarks/registered/port_r03_quay_unions/resolved_placements.json')
 replace_pack('port')
 for a in port['assets']:asset(a['id'],a)
 instances('port',port['placements']);reference('native_quay_supersession',port['quay_union_overlay'])
 market=read('functional_market_clusters','assemblies/market/registered/r3_clusters/resolved_placements.json')
 replace_pack('market')
 for key,a in market['assets'].items():asset('market_r3_'+key,a)
 items=copy.deepcopy(market['placements'])
 for p in items:p['asset_key']='market_r3_'+p['asset_key']
 instances('market',items);assert market['access_overlay']['replace_roads']==out['access_overlay']['replace_roads']
 reservoir=read('northern_reservoir','assemblies/waterworks/registered_reservoir/resolved_placements.json')
 for a in reservoir['assets']:asset(a['id'],a)
 instances('reservoir',reservoir['placements'])
 training=read('garrison_training','assemblies/landscape/registered/training/resolved_placements.json')
 for key,a in training['asset_manifest'].items():asset(key,a)
 remove(training['replacement_ledger']['source_building_ids'],training['replacement_ledger']['source_owned_path_ids']);instances('training',training['placements'])
 for name,path in [('market_walkspace','assemblies/market/registered/r3_clusters/walkspace_report.json'),('density_grounds','assemblies/ordinary/registered/r1/owned_grounds.json'),('r07_contract','registered_topography/revisions/r07_native_interfaces/contract.json')]:
  p=CITY/path;inputs.append(dict(name=name,path=rel(p),sha256=sha(p)))
 p=CITY/'registered_topography/revisions/r08_park_interface/contract.json';inputs.append(dict(name='r08_contract',path=rel(p),sha256=sha(p)))
 out['terrain_module']='world_city.concept_city_v3.registered_topography.revisions.r08_park_interface.author';out['floor_ownership_masks']=[]
 ids=[p['id'] for p in out['common_instances']];assert len(ids)==len(set(ids)),'Duplicate render instances';used={p['asset_key'] for p in out['common_instances']};out['common_assets']={k:v for k,v in out['common_assets'].items() if k in used}
 for k in ('remove_proxy_ids','replace_plot_ids','replace_landmark_groups'):out[k]=sorted(set(out[k]))
 out['access_overlay']['remove_path_ids']=sorted(set(out['access_overlay']['remove_path_ids']))
 out['provenance']=dict(input_packs=inputs,supersession_ledger=ledgers,common_core_modified=False,new_voxel_compile_count_by_integrator=0,geometry_policy='Hash-verified native assemblies at rigid original dimensions.',open_exceptions=['Attached-density correction currently covers BLOCK_013 only. Other ordinary blocks remain sparse.','The old fixed bridge remains pending the separately versioned lifting-span candidate.','13 inferred alley grades and complete character traversal remain unapproved.','Training public handoff has a known 0.211839m coarse-tread quantization excess; reservoir short entrance remains unresolved.','Approach/road landing profiles are exact source triangles represented as preview terrain, not compiled common or capsule certification.','No complete interiors, hydraulic or structural simulation claim.'])
 out['counts']=dict(collections.Counter(p['source_pack'] for p in out['common_instances']));out['counts'].update(instances=len(ids),unique_assets=len(used),unique_cached_quads=sum(a['quad_count'] for a in out['common_assets'].values()))
 output=HERE/'candidate.json';output.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(dict(path=rel(output),sha256=sha(output),counts=out['counts']),indent=2))
if __name__=='__main__':main()
