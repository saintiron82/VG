"""Rebind only after current actual source/coarse/near/proof identities are verified."""
from pathlib import Path
import hashlib,json,subprocess,sys
V=Path(__file__).resolve().parent;U=V.parents[1];R=next(p for p in V.parents if(p/'voxel_character/common/core.py').is_file());C=R/'world_city/concept_city_v3';CP=C/'playable_detail_r01/near_catalog.json';M=V.parent/'expansion_r02/integration_manifest.json'
KEYS=['ordinary_r2_'+s for s in ['4091baa595d757','46347177698aad','6079d6c5f22c0f','661e6b2a06cce8','ae7b4482a249e0','cc43ce6d7a0b84','d993572b700703']]
def load(p):return json.loads(p.read_bytes())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify(x):assert sha(R/x['path'])==x['sha256'];return load(R/x['path'])if x['path'].endswith('.json')else None
before=load(CP);assert sha(CP)==sha(V/'near_catalog.before.json');idx=load(C/'playable_r01/generated/tile_r01/index.json')['common_assets'];manifest=load(M);entries={x['asset_key']:x for x in manifest['entries']};holds=load(U/'house_rules/compiled/provenance_holds.json')['assets'];overrides=load(U/'house_rules/compiled/selection_overrides.json')['assets'];rows=[]
for key in KEYS:
 e=before['assets'][key];m=entries[key];s=idx[key];contract=load(V.parent/'expansion_r02'/key/'runtime.contract.json');q=verify(m['candidate_provenance']);inp=verify(m['source_roof_input_contract'])
 checks={'missing_far_binding':not e.get('far_visual_contract_path'),'held_key':holds[key]['status']=='PENDING_NATIVE_REISSUE','verified_override_present':key in overrides,'near_sha_and_path_match':{'path':e['render_path'],'sha256':e['sha256']}==m['near_render_identity_observed'],'actual_near_sha_matches':sha(R/e['render_path'])==e['sha256'],'actual_source_master_matches':sha(R/s['master_path'])==s['master_sha256']==e['source_master_sha256']==m['original_source_master_sha256'],'actual_coarse_render_matches':sha(R/s['render_path'])==s['render_sha256']==m['original_source_render_sha256'],'candidate_render_matches':sha(R/m['render_path'])==m['render_sha256'],'runtime_contract_near_matches':contract['near_render_identity_observed']['sha256']==e['sha256'],'candidate_proof_source_matches':q['source_master']['sha256']==s['master_sha256']and q['baseline_far_render']['sha256']==s['render_sha256'],'candidate_proof_identity_matches':q['asset_key']==key and q['render']['sha256']==m['render_sha256']and q['input_contract']==m['source_roof_input_contract'],'geometry_tests_pass':q['all_geometry_tests_pass']and all(q['tests'].values()),'input_contract_supported':inp['asset_key']==key and inp['schema']=='riverstone.source_roof_lod_input.v1'and inp['status']=='SUPPORTED_INPUT_UNBUILT'}
 assert all(checks.values()),(key,checks);rows.append({'asset_key':key,'all_pass':True,'near_render_sha256':e['sha256'],'candidate_render_sha256':m['render_sha256'],'checks':checks})
report={'all_pass':True,'rows':rows,'root_cause':'Pre-hold entry popped before verified selection_overrides re-registration; previous_entry then lost valid derived far fields.','before_catalog_sha256':sha(CP),'prior_manifest_sha256':sha(M),'builder_regression_report_sha256':sha(V/'hold_override_regression.json')};(V/'recovery_preflight.json').write_text(json.dumps(report,indent=2)+'\n')
p=subprocess.run([sys.executable,str(U/'bind_source_roof_far_visual.py'),'--manifest',str(M)],cwd=R,capture_output=True,text=True);(V/'recovery_binder.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
after=load(CP);allowed={'far_visual_contract_path','far_visual_contract_sha256','far_visual_render_path','far_visual_render_sha256'}
assert set(before['assets'])==set(after['assets'])
changed=[]
for key,old in before['assets'].items():
 new=after['assets'][key]
 assert {k:v for k,v in old.items()if k not in allowed}=={k:v for k,v in new.items()if k not in allowed},key
 if old!=new:changed.append(key)
assert set(changed)==set(KEYS);assert sum(bool(e.get('far_visual_contract_path'))for e in after['assets'].values())==32
(V/'near_catalog.after_recovery.json').write_bytes(CP.read_bytes());report.update(after_catalog_sha256=sha(CP),changed_keys=changed,all_nonfar_catalog_fields_preserved=True,near_count=len(after['assets']),native_count=sum(bool(e.get('native_scene_path'))for e in after['assets'].values()),far_count=32);(V/'recovery_result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'recovered_count':len(changed),'far_count':32,'near_count':report['near_count'],'before_sha256':report['before_catalog_sha256'],'after_sha256':report['after_catalog_sha256']}))
