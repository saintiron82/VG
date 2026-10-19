"""Reconstructed r4 orchestration. Only hash-bound data/cache reuse; no core edits."""
import copy,hashlib,json,collections,importlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):
 p=Path(p);return str(p.relative_to(ROOT)) if p.is_absolute() else str(p)
def load(p):return json.loads(Path(p).read_bytes())
def build():
 source=CITY/'registered_source/plan.json';baseline=HERE.parent/'r3/candidate.json';out=load(baseline);source_sha=sha(source);assert out['source_plan_sha256']==source_sha
 inputs=[dict(name='preserved_r3_candidate',path=rel(baseline),sha256=sha(baseline))];ledgers=[]
 def read(name,path):
  p=ROOT/path if str(path).startswith('world_city/') else CITY/path;d=load(p)
  inputs.append(dict(name=name,path=rel(p),sha256=sha(p)))
  bound=d.get('source_plan_sha256',d.get('source_plan',{}).get('sha256'))
  if bound is not None:assert bound==source_sha,(name,'source plan changed')
  return d
 def asset(key,a):
  e=copy.deepcopy(a)
  if 'source' in a:e.update(master_path=a['source']['path'],master_sha256=a['source']['sha256'],render_path=a['cache']['path'],render_sha256=a['cache']['sha256'])
  else:e.update(master_path=a['master_path'],master_sha256=a.get('master_file_sha256',a.get('master_sha256')),render_path=a.get('render_path',a.get('compiled_asset_ref')),render_sha256=a['render_sha256'])
  for k in ('master_path','render_path'):e[k]=rel(e[k])
  for k in ('master','render'):assert sha(ROOT/e[k+'_path'])==e[k+'_sha256'],(key,k,'changed')
  rd=load(ROOT/e['render_path']);e.update(quad_count=rd['quad_count'],bounds=rd['bounds']);e.setdefault('pitch_m',a.get('sampling_resource',{}).get('pitch',rd['pitch']))
  old=out['common_assets'].get(key);assert not old or old['render_sha256']==e['render_sha256'],('key collision',key)
  out['common_assets'][key]=e
 def add_pack(name,d):
  items=d.get('assets',d.get('asset_manifest'));items=items.items() if isinstance(items,dict) else ((a['id'],a) for a in items)
  for k,a in items:asset(k,a)
  for p in d['placements']:
   assert p.get('scale',p.get('scale_xyz',[1,1,1]))==[1,1,1]
   q={k:copy.deepcopy(p[k]) for k in ('id','asset_key','position_m','yaw_rad','palette_id','palette_override') if k in p};q.setdefault('palette_id','native_'+name);q.setdefault('palette_override',{});q.update(scale=[1,1,1],source_pack=name)
   assert q['asset_key'] in out['common_assets'];out['common_instances'].append(q)
 def remove(ids,pathids=()):
  ids=set(ids);out['common_instances']=[p for p in out['common_instances'] if p['id'] not in ids]
  out['remove_proxy_ids']+=sorted(ids|{v+':support' for v in ids}|{v+':owned_foundation' for v in ids});out['access_overlay']['remove_path_ids']+=list(pathids)
 b15=read('poor_block015_dry_access','assemblies/property/registered/poor_block015_east/route_repair_01/effective_placements.json')
 remove(b15['replaced_placement_ids'],b15['superseded_old_path_ids']);add_pack('ordinary_density_b15',b15)
 ledgers.append(dict(pack='ordinary_density_b15',rendered_groups=len(b15['placements']),semantic_bodies=len(b15['component_placements']),removed_ids=b15['replaced_placement_ids'],component_records_rendered=False))
 reservoir=read('reservoir_connected_service','assemblies/waterworks/registered_reservoir/service_r02/resolved_placements.json')
 out['common_instances']=[p for p in out['common_instances'] if p['source_pack']!='reservoir'];add_pack('reservoir',reservoir)
 binding=load(HERE/'terrain_binding.json');assert sha(ROOT/binding['contract_path'])==binding['contract_sha256'];read('r4_bound_terrain',binding['contract_path'])
 training=read('fine_training_access',binding['training_pack_path']);assert sha(ROOT/binding['training_pack_path'])==binding['training_pack_sha256']
 out['common_instances']=[p for p in out['common_instances'] if p['source_pack']!='training'];add_pack('training',training)
 palette=read('b13_deterministic_palette','registered_integration/r4/b13_palette_overlay.json');assert palette['source']['sha256']==sha(baseline)
 byid={p['id']:p for p in out['common_instances']}
 for q in palette['placements']:
  p=byid[q['id']];a=out['common_assets'][p['asset_key']]
  for k in ('asset_key','position_m','yaw_rad','scale'):assert p[k]==q[k]
  for k in ('master_sha256','render_sha256'):assert a[k]==q[k]
  p.update(palette_id=q['palette_id'],palette_override=q['palette_override'])
 yards=read('b13_owned_workyards','assemblies/property/registered/b13_workyards_r1/resolved_placements.json');add_pack('b13_workyards',yards)
 read('south_country_road','registered_topography/road_extensions/south_country_r1/contract.json')
 ids=[p['id'] for p in out['common_instances']];assert len(ids)==len(set(ids));used={p['asset_key'] for p in out['common_instances']};out['common_assets']={k:v for k,v in out['common_assets'].items() if k in used}
 cache={}
 for p in out['common_instances']:
  key=(p['asset_key'],p['palette_id']);value=json.dumps(p['palette_override'],sort_keys=True);assert cache.setdefault(key,value)==value,'Palette leakage risk'
 for k in ('remove_proxy_ids','replace_plot_ids','replace_landmark_groups'):out[k]=sorted(set(out[k]))
 out['access_overlay']['remove_path_ids']=sorted(set(out['access_overlay']['remove_path_ids']))
 out.update(schema='riverstone.registered_integration.r4',status='reconstructed_native_candidate_pending_visual_and_full_city_passage',terrain_module=binding['module'],floor_ownership_masks=[])
 out['provenance']=dict(input_packs=inputs,supersession_ledger=ledgers,reconstructed_after_workspace_loss=True,restored_baseline_library_version=5,common_core_modified=False,new_voxel_compile_count_by_integrator=4,open_exceptions=['New B15 and B13 functional grounds are bounded improvements; other ordinary blocks and precincts remain incomplete.','Operational bridge fixture is separately verified; full city pedestrian/cart/NPC registration is not complete.','Terrain/source recovery uses separately labeled modules rather than changing sealed r07/r08 hash guards.','Southern country road remains source triangle preview; painted concept barbican is still missing.','No full city character, navigation, structural or hydraulic completion claim.'])
 out['counts']=dict(collections.Counter(p['source_pack'] for p in out['common_instances']));out['counts'].update(instances=len(ids),unique_assets=len(used),unique_cached_quads=sum(a['quad_count'] for a in out['common_assets'].values()))
 return out

def main():
 dest=HERE/'candidate.json';assert not dest.exists(),'Existing candidate immutable; create a new revision.'
 out=build();dest.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(dict(path=rel(dest),sha256=sha(dest),counts=out['counts']),indent=2))
if __name__=='__main__':main()
