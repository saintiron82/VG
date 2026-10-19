"""Narrow acceptance of the existing semantic/default palette promotion.

The strict metadata failure is immutable. Only its fourteen empty semantic
roof overrides and one anonymous step palette label may be resolved, and only
against the exact base catalog, actual provenance and unchanged source cache.
No source placement, scene, engine, geometry or material byte is edited.
"""
from . import check_final_city_activation_r02 as r2
from .rebind_coherent_datums import require
from world_city.concept_city_v3.registered_integration.r8 import promotion
from world_city.concept_city_v3.registered_integration.r6 import apply_packs
import copy,gc,time
c=r2.c;g=c.g
PRIOR=g.HERE/'city_activation_ledger_r01'
OUT=g.HERE/'city_activation_ledger_r02'
STEP='BLOCK_001:R8_C003:PEDESTRIAN_STEP_SKIN'


def run():
 started=time.monotonic();assert not OUT.exists()
 previous=g.load(PRIOR/'manifest.json');strict=require(previous['audit']);assert not strict['passed']
 assert all(v for k,v in strict['checks'].items()if k!='all_expected_native_instances_exact')
 manifest=require(previous['actual_manifest']);binding=require(manifest['binding']);base=require(binding['base_scene']);catalog=promotion.palette_catalog(base);del base;gc.collect()
 prior,final,withdrawal,groups,deferred=c.expected_sources();assert catalog==final['palette_semantic_mapping']
 sourcefinal=next(q for q in groups if q['label']=='final23');sourcebyid={p['id']:p for p in sourcefinal['pack']['placements']}
 bad={r['label']:r for r in strict['native_groups']if not r['passes']};assert set(bad)=={'final23','profile_extension_0'}
 roofbad=bad['final23']['pose_asset_palette_mismatches'];assert len(roofbad)==14 and not bad['final23']['missing_or_duplicate']
 assert all(r['differing_fields']==['palette_override']for r in roofbad)
 assert bad['profile_extension_0']['pose_asset_palette_mismatches']==[dict(id=STEP,differing_fields=['palette_id'])]
 assert not bad['profile_extension_0']['missing_or_duplicate']
 scene=require(previous['actual_scene']);assert scene['r8_provenance']['base_scene']==binding['base_scene']
 actual={p['id']:p for p in scene['common_instances']};proof=[]
 for mismatch in roofbad:
  sid=mismatch['id'];raw=sourcebyid[sid];key=raw['palette_id'];effective=catalog[key];records=[r for r in scene['r8_provenance']['palette_bindings']if r['id']==sid]
  checks=dict(raw_override_empty_or_absent=not raw.get('palette_override'),exact_named_palette_preserved=actual[sid]['palette_id']==key,
   actual_mapping_matches_approved_base=actual[sid]['palette_override']==effective,
   one_exact_provenance_record=len(records)==1,
   provenance_matches_empty_source=records==[dict(id=sid,palette_id=key,mapping_sha256=apply_packs.digest(effective),was_explicit=False)])
  assert all(checks.values()),(sid,checks)
  proof.append(dict(id=sid,change='EXPAND_DECLARED_SEMANTIC_PALETTE_FROM_UNCHANGED_BASE_CATALOG',raw_palette_id=key,raw_override_present='palette_override'in raw,raw_override=raw.get('palette_override'),effective_override=effective,provenance=records[0],checks=checks))
 effectivegroups=[]
 for q in groups:
  qq=dict(q)
  if q['label']=='final23':
   qq['pack'],resolved=promotion.resolve_palettes(q['pack'],catalog)
   changes=[(p['id'],k)for p,old in zip(qq['pack']['placements'],q['pack']['placements'])for k in set(p)|set(old)if p.get(k)!=old.get(k)]
   assert set(changes)=={(x['id'],'palette_override')for x in roofbad}
  elif q['label']=='profile_extension_0':
   qq['pack']=copy.deepcopy(q['pack']);p=qq['pack']['placements'][0];assert p['id']==STEP and 'palette_id'not in p and not p.get('palette_override')
   owner=[x for x in binding['packs']if any(y['id']==STEP for y in require(x)['placements'])] if False else [x for x in binding['packs']if x['name']=='final23_whole_holdings_and_step']
   assert len(owner)==1;sourcepack=require(owner[0]);step_source=[x for x in sourcepack['placements']if x['id']==STEP];assert step_source==[p]
   default='native_'+owner[0]['name'];p.setdefault('palette_id',default);p.setdefault('palette_override',{})
   ass=q['pack']['assets'][p['asset_key']];cache=require(dict(path=ass['render_path'],sha256=ass['render_sha256']))
   stepchecks=dict(raw_source_has_no_palette_id='palette_id'not in step_source[0],existing_applier_default_exact=actual[STEP]['palette_id']==default,
    empty_override_keeps_cache_colors=actual[STEP]['palette_override']=={},actual_cache_hash_unchanged=scene['common_assets'][p['asset_key']]['render_sha256']==ass['render_sha256'])
   assert all(stepchecks.values())
   stepproof=dict(id=STEP,change='APPLY_EXISTING_PACK_DEFAULT_PALETTE_LABEL_WITH_EMPTY_OVERRIDE',source_pack=owner[0],generated_palette_id=default,cache=dict(path=ass['render_path'],sha256=ass['render_sha256']),source_cache_material_mapping=cache['materials'],effective_actual_material_mapping={k:actual[STEP]['palette_override'].get(k,v)for k,v in cache['materials'].items()},checks=stepchecks)
   assert stepproof['source_cache_material_mapping']==stepproof['effective_actual_material_mapping']
  effectivegroups.append(qq)
 audit=c.inspect(scene,effectivegroups,withdrawal,deferred,final);assert audit['passed'],audit['checks']
 candidate=require(dict(path=str(r2.CANDIDATE.relative_to(g.ROOT)),sha256=r2.CANDIDATE_SHA))
 ledger=r2.bind_ledger(candidate,audit,previous['actual_manifest'],previous['actual_scene'],dict(native_part_and_assembly_instances=len(scene['common_instances']),inherited_planning_building_masses=scene.get('counts',{}).get('building_masses'),not_a_building_count=True))
 ledger['schema']='riverstone.ordinary_city.exact_scene_effective_palette_activation.v3'
 ledger['source_references'].update(strict_metadata_failure=g.ref(PRIOR/'manifest.json'),effective_palette_acceptance_author=g.ref(__file__),existing_palette_promoter=g.ref(promotion.__file__),existing_pack_applier=g.ref(apply_packs.__file__))
 ledger['status']='EXACT_NATIVE_ACTIVATION_AND_APPROVED_EFFECTIVE_PALETTES_PASS; FINAL_SPATIAL_TRAVERSAL_ACCEPTANCE_SEPARATE'
 paletteproof=dict(schema='riverstone.ordinary_city.effective_palette_acceptance.v1',actual_manifest=previous['actual_manifest'],actual_scene=previous['actual_scene'],strict_failure=g.ref(PRIOR/'manifest.json'),base_scene=binding['base_scene'],approved_semantic_catalog=catalog,semantic_resolutions=proof,step_default_resolution=stepproof,existing_promotion_source=g.ref(promotion.__file__),existing_pack_applier_source=g.ref(apply_packs.__file__),exact_declared_transform_count=15,changed_geometry_or_pose_or_asset_count=0,source_scene_changes=0,passed=True,author=g.ref(__file__))
 OUT.mkdir();g.write(OUT/'effective_palette_acceptance.json',paletteproof);ledger['effective_palette_acceptance']=g.ref(OUT/'effective_palette_acceptance.json');g.write(OUT/'completion_ledger.json',ledger);g.write(OUT/'native_activation_audit.json',audit)
 text=['# Exact-scene ordinary activation ledger','', 'PASS: all 110 adopted holdings, 835 selected backland native objects and the approved step skin match the exact final scene. All 295 old ordinary owners/foundations and explicit deferred proposals are absent. The 960 m² unbuilt B008 holding remains withdrawn and the retained north market hall matches exactly.','',
  'The strict metadata result is preserved. Fourteen source range instances omitted their overrides while naming the approved clay/wood/slate palettes. Their actual mappings exactly match the unchanged R7 catalog and one explicit scene provenance record each. The step skin receives the existing pack-generated palette ID with an empty override; every cache material color is unchanged. Only these fifteen fully explained metadata transformations are accepted.','',
  'No pose, geometry, asset, source cache, source scene or native selection was changed for this acceptance. The 2,006 selected native objects are parts/assemblies, not buildings.','',
  'Source-bound selected holding land: 74,614.973 m². New roof union: 40,793.000 m². Explicitly retired R7 roof union: 28,844.750 m². Net roof increment: 11,948.250 m². Exact final unassigned-land and applied-material totals remain outside this bounded native audit.','',
  'Only the 22 listed gated backland subyards carry a complete enclosure claim. Eight entire old proposed perimeters (105 panels), three other fixtures, two intentional entry openings and 68 original backland deferrals remain explicitly accounted.','',
  '## Registered blocks','']
 for b in ledger['blocks']:text += [f"- {b['block_id']}: {b['selected_holding_count']} adopted holdings; {b['functional_backlands']['selected_native_instances']} backland native selections. "+(', '.join(b['selected_holding_ids'])or b['disposition'])]
 text += ['', 'Final composed support/ownership, collision, rendered review and the full traversal replay remain separate exact-scene acceptance gates. Initial coverage, R04, the candidate and the strict metadata failure are preserved.', '', 'Scene: '+previous['actual_scene']['path'],'SHA-256: '+previous['actual_scene']['sha256']]
 (OUT/'COMPLETION_LEDGER.md').write_text('\n'.join(text)+'\n')
 g.write(OUT/'manifest.json',dict(status=ledger['status'],passed=True,actual_manifest=previous['actual_manifest'],actual_scene=previous['actual_scene'],strict_failure=g.ref(PRIOR/'manifest.json'),source_candidate=g.ref(r2.CANDIDATE),palette_acceptance=g.ref(OUT/'effective_palette_acceptance.json'),ledger=g.ref(OUT/'completion_ledger.json'),audit=g.ref(OUT/'native_activation_audit.json'),readable=g.ref(OUT/'COMPLETION_LEDGER.md'),author=g.ref(__file__),seconds=time.monotonic()-started))
 print(audit['checks'],flush=True);print(g.ref(OUT/'manifest.json'),flush=True)

if __name__=='__main__':run()
