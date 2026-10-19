"""Final equivalent-representation checks; preserve the separately diagnosed road failure."""
import json,pathlib,hashlib
D=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in D.parents if(p/'voxel_character').is_dir());B=D.parent
ID='REGISTERED_WATER_CROSSING:EAST_RADIAL';OTHER_FAILURE='ROAD:EAST_WALL_SERVICE_REVERSE'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def can(j):return hashlib.sha256(json.dumps(j,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def put(p,j):assert not p.exists();p.write_text(json.dumps(j,indent=2,allow_nan=False)+'\n');return ref(p)
def closure(p,r):
 poses={k:p['placements'][k]for k in r['placement_ids']};return dict(route=r,placements=poses,assets={q['asset_key']:p['assets'][q['asset_key']]for q in poses.values()},buildings={k:p['buildings'][k]for k in r['building_ids']},implementation_hashes=p['implementation_hashes'],scene=p['sources']['scene'])
def main():
 proof=read(D/'representation_proof.json');srcp=ROOT/proof['source_prepared']['path'];assert sha(srcp)==proof['source_prepared']['sha256'];src=read(srcp);full=read(D/'prepared_all_candidate.json');part=read(D/'prepared_runtime.json');result=read(D/'evidence/public_network_replay.json');metrics=read(D/'evidence/public_network_replay_metrics.json');original=read(B/'public_network_final_runtime_r01/evidence/public_network_replay.json');origresults={r['id']:r for r in original['routes']};aff={r['case_id']for r in proof['case_frames']};aliases={f['instance_id']for f in proof['frames']};original_routes={r['id']:r for r in src['routes']};caseproof=[]
 assert len(result['routes'])==24 and {r['id']for r in result['routes']}==aff
 failed=[r for r in result['routes']if not r['pass']];assert len(failed)==1 and failed[0]['id']==OTHER_FAILURE
 for r in failed:
  o=origresults[r['id']];assert r['status']==o['status']=='reached'and r['ground_ray_miss_frames']==o['ground_ray_miss_frames']==2 and r['not_on_floor_frames']==o['not_on_floor_frames']==0
 for row in proof['case_frames']:assert row['terrain_origin_xyz_m']==row['native_origin_xyz_m']
 for old,new in zip(src['routes'],full['routes']):
  assert old['id']==new['id']and old['points']==new['points'];clean=dict(new,placement_ids=[ID if p in aliases else p for p in new['placement_ids']]);assert clean==old
  a=can(closure(src,old));b=can(closure(full,new));assert(a!=b)==(old['id']in aff)
  caseproof.append(dict(case_id=old['id'],original_transitive_collision_input_sha256=a,candidate_transitive_collision_input_sha256=b,exact_input_identity=a==b))
 assert full['buildings']==src['buildings'];assert full['sources']['scene']==src['sources']['scene'];assert full['implementation_hashes']==src['implementation_hashes']
 for key,pose in src['placements'].items():
  if key!=ID:assert full['placements'][key]==pose
 for key,a in src['assets'].items():assert full['assets'][key]==a
 for f,originalpath in [('Traversal.gd',ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd'),('RenderData.gd',ROOT/'voxel_character/common/preview/RenderData.gd'),('project.godot',B/'public_network_final_runtime_r01/project.godot')]:assert(D/f).read_bytes()==originalpath.read_bytes()
 assert metrics['peak_child_rss_kib']<1048576
 for f in proof['frames']:
  q=read(ROOT/f['asset']['path']);assert sha(ROOT/f['asset']['path'])==f['asset']['sha256'];back=[[[v[k]+f['origin_xyz_m'][k]for k in range(3)]for v in t]for t in q['triangles']];assert len(back)==504 and can(back)==proof['source_world_sha256']and not f['zero_or_reversed_faces']
 negatives=[r for r in result['routes']if original_routes[r['id']].get('expected_failure')];assert len(negatives)==4 and all(r['pass']for r in negatives)
 positives=[r for r in result['routes']if not original_routes[r['id']].get('expected_failure')];passed=[r for r in positives if r['pass']];assert len(passed)==19 and all(r['ground_ray_miss_frames']==0 and r['not_on_floor_frames']==0 for r in passed)
 identity=put(D/'case_input_identity.json',dict(source=ref(srcp),candidate=ref(D/'prepared_all_candidate.json'),unchanged=457,changed=24,rows=caseproof,runtime_claim=False))
 checks=put(D/'source_and_runtime_checks.json',dict(status='23_AFFECTED_CASES_PASS_ONE_UNCHANGED_SEPARATE_PUBLIC_SEAM_FAILURE',representation=ref(D/'representation_proof.json'),case_input_identity=identity,scene_unchanged=src['sources']['scene'],replay=ref(D/'evidence/public_network_replay.json'),original481=ref(B/'public_network_final_runtime_r01/evidence/public_network_replay.json'),metrics=metrics,positive_passes=19,negative_passes=4,changed_route_vectors=0,changed_controller_or_acceptance_bytes=0,every_case_same_native_terrain_frame=True,native_source_faces_preserved_per_case=504,source_world_roundtrip_error_m=0.,maximum_forward_float32_coordinate_error_m=max(f['maximum_forward_world_float32_coordinate_error_m']for f in proof['frames']),preserved_other_failure=failed[0],other_failure_diagnosis=ref(B/'final_road_contact_diagnosis_r01/diagnosis.json')))
 handoff=put(D/'integration_handoff.json',dict(schema='riverstone.equivalent_collision_extraction_handoff.v1',status='EAST_RADIAL_CORRECTION_VERIFIED_COMBINED_PUBLIC_FIXES_PENDING',source_prepared=proof['source_prepared'],source_scene=src['sources']['scene'],candidate_all481_prepared=ref(D/'prepared_all_candidate.json'),representation=ref(D/'representation_proof.json'),source_and_runtime_checks=checks,transitive_case_input_identity=identity,changed_cases=sorted(aff),mapping=[dict(frame=f['origin_xyz_m'],asset=full['assets'][f['asset_key']],placement=full['placements'][f['instance_id']],logical_native_owner=ID)for f in proof['frames']],integration_requirement='Use exactly one source-bound complete native collider variant per affected case, selected by its existing terrain origin. Keep original EAST_RADIAL ID for the direct/shared frame so unchanged rail contact expectations remain satisfied. The two other aliases map to that logical source owner. Retain all native sides, rails and floor triangles. Scene visual/native source bytes remain unchanged.',limits=['The remaining EAST_WALL_SERVICE_REVERSE two-ray-miss failure is at a separate public road seam near [188,370]; it remains failed and has not been waived.','Global acceptance still requires parent composition of the other four original failures and the case-input-certified final replay/reuse decision.','No general coordinate-system or controller change; only three explicitly enumerated collision variants for this one native source.'],freeze_manifest_path=str((D/'freeze_manifest.json').relative_to(ROOT))))
 files=[p for p in D.rglob('*')if p.is_file()and'.runtime'not in p.parts and'__pycache__'not in p.parts and'.godot'not in p.parts and p.name!='freeze_manifest.json'];freeze=put(D/'freeze_manifest.json',dict(status='BOUNDED_NATIVE_REPRESENTATION_VERIFIED_WITH_EXPLICIT_OTHER_ROUTE_HOLD',files=[ref(p)for p in sorted(files)]));print(json.dumps(dict(handoff=handoff,checks=checks,freeze=freeze,identity=identity),indent=2))
if __name__=='__main__':main()
