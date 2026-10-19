"""Assemble reviewed finite packs and terrain edits, without regenerating terrain.

A later review_binding.json supplies exact frozen hashes and producer evidence.
This command has no permissive default and refuses unreviewed/missing changes.
"""
import argparse,copy,json,time
from pathlib import Path
from . import apply_packs as assets
from . import merge_patches
from .cameras import add_review_cameras


def verified(row):
 p=assets.source_file(row['path'])
 return assets.load(p,row['sha256'])

def build(binding):
 if binding.get('status')!='sources_reviewed_ready_for_visual':raise ValueError('Source review has not accepted this binding')
 if binding['base_scene']['sha256']!=assets.BASE_SHA256:raise ValueError('Unknown base scene')
 scene=verified(binding['base_scene'])
 if not binding['patches'] or not binding['packs']:raise ValueError('Empty activation is not an R6 deliverable')
 for row in binding['producer_evidence']:verified(row)
 rawpatches=[verified(row) for row in binding['patches']]
 merged=merge_patches.merge(rawpatches);merge_patches.validate_against_scene(scene,merged)
 # R15 is the project-local finite scene-patch orchestrator, not a voxel engine.
 module=assets.source_file(binding['patch_apply']['path'])
 if assets.sha(module)!=binding['patch_apply']['sha256']:raise ValueError('Changed reviewed patch applier')
 from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import frozen
 if Path(frozen.__file__).resolve()!=module.resolve():raise ValueError('Unexpected patch module')
 result=frozen.apply_edits(scene,merged)
 ledgers=[]
 for row in binding['packs']:
  pack=verified(row)
  result,ledger=assets.apply_pack(result,pack,row['name'],dict(path=row['path'],sha256=row['sha256']))
  ledgers.append(ledger)
  if pack.get('collision_contracts'):
   result['collision_contracts']=copy.deepcopy(result.get('collision_contracts',[]))+copy.deepcopy(pack['collision_contracts'])
 for key,value in binding.get('new_materials',{}).items():
  old=result['materials'].get(key)
  if old is not None and old!=value:raise ValueError('Material alias would recolor old city: '+key)
  if result['materials'] is scene['materials']:result['materials']=dict(result['materials'])
  result['materials'][key]=value
 unknown=set(result['surfaces'])-set(result['materials'])
 if unknown:raise ValueError('No material for appended terrain: '+str(unknown))
 result=add_review_cameras(result)
 counts=dict(result['counts']);result['counts']=counts
 result['counts_source_snapshot_note']='building_masses and by_social_role describe the registered source mass plan; common_instances includes trees, walls, furniture and support and is not a building or household count.'
 counts.update(common_instances=len(result['common_instances']),actual_remaining_proxy_boxes=len(result['boxes']),support_proxies=len(result['boxes']),r6_local_patches=len(rawpatches),r6_replacement_terrain_triangles=sum(len(r['replacement_triangles_xyz_m']) for r in merged['surface_edits']),r6_appended_terrain_triangles=sum(len(v)//3 for v in merged['appended_surfaces'].values()),terrain_triangles=sum(len(v)//3 for v in result['surfaces'].values()))
 used={p['asset_key'] for p in result['common_instances']}|set(result['bridge_mechanism']['asset_keys'])
 result['common_assets']={key:a for key,a in result['common_assets'].items() if key in used};counts['common_unique_assets']=len(used)
 assets.validate_instances(result)
 result['status']='r6_local_exterior_candidate_pending_actual_review'
 result['r6_provenance']=dict(binding_sha256=assets.digest(binding),base_scene=binding['base_scene'],pack_ledgers=ledgers,patch_sources=merged['source_patches'],source_evidence=binding['producer_evidence'],registered_camera_unchanged=True,whole_city_complete=False,geometry_engine='Existing common voxel master/coordinate_planes/render_data; finite city terrain orchestration only.')
 result['limits']=copy.deepcopy(binding['limits'])
 assert result['inspection_cameras']['registered']==scene['inspection_cameras']['registered']
 assert result['bridge_mechanism']==scene['bridge_mechanism']
 return result,merged


def main():
 parser=argparse.ArgumentParser();parser.add_argument('binding');parser.add_argument('destination');args=parser.parse_args()
 dest=Path(args.destination);dest.mkdir(parents=True,exist_ok=True);scene_path=dest/'scene.json'
 if scene_path.exists():raise ValueError('Do not overwrite a prior actual scene')
 start=time.monotonic();binding_path=Path(args.binding);binding=assets.load(binding_path)
 scene,patch=build(binding)
 temp=dest/'scene.pending.json';temp.write_text(json.dumps(scene,separators=(',',':'),allow_nan=False)+'\n');temp.replace(scene_path)
 (dest/'local_patch.json').write_text(json.dumps(patch,separators=(',',':'),allow_nan=False)+'\n')
 record=dict(scene=dict(path=assets.rel(scene_path),sha256=assets.sha(scene_path)),binding=dict(path=assets.rel(binding_path),sha256=assets.sha(binding_path)),counts=scene['counts'],elapsed_s=time.monotonic()-start,status='source_assembled_waiting_actual_view',whole_city_complete=False)
 (dest/'build_record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
