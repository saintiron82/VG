"""Seal explicit bounded candidate; never promotes it into the city scene."""
import pathlib,json,hashlib,sys,copy,math
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';A=CITY/'assemblies/waterworks/registered_bridge/south_approach_r02'
read=lambda p:json.loads(pathlib.Path(p).read_bytes())
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
 prepared=read(H/'prepared.json');raw=read(H/'evidence/capsule_continuous_cover.json');native=read(H/'evidence/native_audit.json');bear=read(H/'evidence/exact_bearing_audit.json');pack=read(A/'resolved_placements.json');profile=read(A/'profile.json');issues=[]
 for label,s in prepared['sources'].items():
  if sha(s['path'])!=s['sha256']:issues.append(['changed_source',label])
 for name,h in prepared['implementation_hashes'].items():
  if sha(ROOT/name)!=h:issues.append(['changed_implementation',name])
 for key,a in prepared['assets'].items():
  if sha(ROOT/a['render_path'])!=a['render_sha256']:issues.append(['changed_collision_asset',key])
 if raw['prepared_sha256']!=sha(H/'prepared.json'):issues.append(['prepared_hash'])
 if len(raw['routes'])!=6 or raw['status']!='pass':issues.append(['physics_failure'])
 assert native['status']=='pass_bounded_native_geometry';assert bear['status']=='pass_exact_finite_column_bearing_coverage'
 settings=raw['settings'];assert settings['physics_hz']==60 and settings['radius_m']==.3 and settings['height_m']==1.8
 for r in raw['routes']:
  assert r['within_route_teleports']==0 and r['spawn_ground_ray_hit'] and r['spawn_on_floor']
  if 'expected_failure' not in r:assert r['status']=='reached' and not r['obstacle_contact_ids'] and r['not_on_floor_frames']==0 and r['ground_ray_miss_frames']==0
 for file in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:assert sha(H/file)==sha(BASE/file)
 # Byte-identical outside the permitted removal: full occupied-cell records, not coordinates alone.
 old=read(A.parent/'drawbridge_candidate/cache/stone_approaches.pitch_0.25.compiled.json');new=read(ROOT/pack['assets']['recessed_fixed']['compiled']['path']);oldrows={tuple(v) for v in old['cells']};newrows={tuple(v) for v in new['cells']};assert newrows<=oldrows and len(oldrows-newrows)==224
 integrity={'status':'pass' if not issues else 'fail','issues':issues,'controller':ref(H/'Traversal.gd'),'common_loader':ref(H/'RenderData.gd'),'source_scene':{'path':'world_city/concept_city_v3/evidence/visual_registered_common_r5/bridge_scene.json','sha256':'a78e1b56bd59b06ec30d4bebec9f6da9d686dca87e6ef87f1d4da181f717a01a'},'prepared':ref(H/'prepared.json'),'raw_report':ref(H/'evidence/capsule_continuous_cover.json'),'physics_summary':raw['summary'],'spawn_y':{r['id']:r['spawn_surface_y_m'] for r in raw['routes']},'native':ref(H/'evidence/native_audit.json'),'whole_column_bearings':ref(H/'evidence/exact_bearing_audit.json'),'baseline_failure_preserved':ref(BASE/'freeze_initial.json'),'remaining_coarse_cell_records_identical':len(newrows),'native_removed_cell_records':224}
 write(H/'evidence/result_integrity.json',integrity);assert not issues,issues
 oldpack=read(A.parent/'drawbridge_candidate/resolved_placements.json');original=oldpack['placements'][0];assets={};placements=[]
 for key,record in pack['assets'].items():
  aid=record['id'];assets[aid]={'key':aid,'bounds':record['bounds'],'pitch_m':record['pitch_m'],'cell_count':record['cell_count'],'quad_count':record['quad_count']}
  for typ in ['master','compiled','render']:assets[aid][typ+'_path']=record[typ]['path'];assets[aid][typ+'_sha256']=record[typ]['sha256']
  placement={'id':original['id'] if key=='recessed_fixed' else 'BRIDGE_MAIN_RIVER:SOUTH_VISIBLE_GRADED_COVER','asset_key':aid,'position_m':profile['frame']['translation'],'transform':profile['frame'],'scale_xyz':[1,1,1],'scale':[1,1,1],'yaw_rad':math.atan2(profile['frame']['basis'][0][2],profile['frame']['basis'][0][0]),'palette_id':'native_drawbridge','category':'actual_native_common_mesh'}
  placement['collision_policy']='Actual derived concave native mesh; exact 224 cap-cell source recess.' if key=='recessed_fixed' else 'Visual and supported fill mass only for this fixture. Declared continuous finite profile supplies lane collision; do not activate all sampled top risers in parallel.'
  placements.append(placement)
 up=read(H/'geometry/visible_upward_faces.json');b=profile['frame']['basis'];t=profile['frame']['translation'];world=lambda v:[t[i]+sum(b[i][j]*v[j] for j in range(3)) for i in range(3)]
 floors=[]
 for i,face in enumerate(up['local_upward_faces']):
  vv=[world([x,face['y'],z]) for x,z in face['polygon_xz_m']];floors.append({'id':f'SOUTH_NATIVE_COVER_UPFACE:{i}','polygon_xz_m':[[v[0],v[2]] for v in vv],'top_y_m':face['y'],'quad_xyz_m':vv,'native_sampled_visual_owner':True})
 normalized={'schema':'riverstone.native_pack.south_approach_r02.v1','status':'bounded_native_and_generic_capsule_pass_pending_combined_scene_review','base_scene':integrity['source_scene'],'assets':assets,'placements':placements,'replacement_overlay':{'removed_instance_ids':[original['id']],'retained_same_id_replacement':original['id'],'all_other_instances_unchanged':True},'surface_edits':ref(H/'scene_patch.json'),'continuous_collision_profile':ref(A/'profile.json'),'owned_floor_regions':floors,'evidence':{'native':ref(H/'evidence/native_audit.json'),'exact_bearings':ref(H/'evidence/exact_bearing_audit.json'),'capsule':ref(H/'evidence/capsule_continuous_cover.json'),'integrity':ref(H/'evidence/result_integrity.json'),'original_failed_baseline':ref(BASE/'freeze_initial.json')},'limits':prepared['assumptions'],'activation':'No city file was changed. Parent must compose exact indexed terrain edits and native replacement before any R6 combined-view or gameplay claim.'}
 write(A/'normalized_resolved_placements.json',normalized)
 files={}
 for root in [H,A]:
  for p in sorted(root.rglob('*')):
   if not p.is_file() or any(v in p.parts for v in ['.godot','.runtime','__pycache__']):continue
   if p.name=='freeze_manifest.json':continue
   files[str(p.relative_to(ROOT))]=sha(p)
 seal={'schema':'riverstone.southern_repair_r02.freeze.v1','status':'sealed_bounded_candidate','base_scene':integrity['source_scene'],'files':files,'failed_baseline':ref(BASE/'freeze_initial.json'),'summary':raw['summary'],'limits':prepared['assumptions']};write(H/'freeze_manifest.json',seal)
 print(json.dumps({'freeze':ref(H/'freeze_manifest.json'),'native_pack':ref(A/'normalized_resolved_placements.json'),'scene_edits':ref(H/'scene_patch.json'),'integrity':ref(H/'evidence/result_integrity.json'),'geometry':native['visible_cover'],'physics':raw['summary']},indent=2))
if __name__=='__main__':main()
