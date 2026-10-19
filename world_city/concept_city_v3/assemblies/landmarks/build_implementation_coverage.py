"""Cross-facility implementation ledger; evidence stages never imply placement."""
from pathlib import Path
import json,sys,copy,collections
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.assemblies.landmarks.author import HERE,ref,write

def read(rel):return json.loads((ROOT/rel).read_text())
def build():
 old=read('world_city/runtime_city/parts/inventory.json');water=read('world_city/concept_city_v3/assemblies/waterworks/inventory.json');land=read('world_city/concept_city_v3/assemblies/landmarks/assemblies.json');cache=read('world_city/concept_city_v3/assemblies/landmarks/evidence/compile_report.json');recipe=read('world_city/concept_city_v3/assemblies/landmarks/resolved_placements.json');smoke=read('world_city/runtime_city/parts/evidence/smoke_report.json')
 group_for={'timber_dock':['port_cluster'],'warehouse_buildings':['port_cluster'],'quay_retaining_segment':['port_cluster'],'timber_harbor_crane':['port_cluster'],'river_cargo_barge':['port_cluster'],'cargo_crate':['port_cluster'],'timber_dock_piles_bents':['port_cluster'],'cathedral_nave_transept':['cathedral'],'cathedral_twin_steeples':['cathedral'],'cathedral_existing_buttresses':['cathedral'],'cathedral_flying_buttress':['cathedral'],'pointed_arch_cloister_bay':['cathedral','monastery'],'castle_keep_courtyard':['castle'],'castle_curtain_towers':['castle'],'gatehouses':['castle'],'civic_hall':['civic_grain'],'grain_hall':['civic_grain'],'monastery_hospital':['monastery'],'garden_beds_orchards':['monastery']}
 water_for={'multi_arch_bridge_vaults':'stone_road_bridge_bay','water_source_intake_headworks':'spring_intake','water_covered_clean_conduit':'covered_clean_conduit','water_millrace':'service_channel_segment','water_sluice':'sluice_bay','water_outfall':'drain_outfall','water_well_drawpoint':'covered_wellhouse','water_canal_footbridge':'canal_footbridge','water_protective_edge':'service_channel_segment'}
 related={'water_reservoir_settling_pond':['reservoir_lining_segment'],'water_clean_cistern':['covered_wellhouse','covered_clean_conduit'],'water_floodgate':['sluice_bay'],'water_storm_drain':['drain_outfall'],'craft_equipment_and_mills':['undershot_mill_wheel','mill_bank_interface'],'harbor_floodwall_and_water_stairs':['retaining_stair_landing'],'neighborhood_terrace_assemblies':['retaining_stair_landing']}
 wby={r['id']:r for r in water['entries']};rows=[]
 for e in old['entries']:
  id=e['id'];r={'id':id,'family':e['facility_family'],'source_refs':copy.deepcopy(e.get('source_refs',[])),'prior_status':e['status'],'source_present':e['status'] in ('existing_implemented','staged_prototype'),'compiled_sample':False,'compiled_cache':False,'resolved_placement':False,'actual_common_asset_placed_in_v3':False,'actual_viewed_in_v3':False,'complete_facility':False,'partial_coverage':True,'stage':'source_only' if e['status'] in ('existing_implemented','staged_prototype') else 'missing','remaining_work':copy.deepcopy(e.get('remaining_work',[])),'observation':e.get('observation')}
  if any(m['kind']==id and m['valid'] for m in smoke['compile_measurements']):r['compiled_sample']=True;r['sample_evidence']=ref('world_city/runtime_city/parts/evidence/smoke_report.json')
  samplepath=ROOT/'world_city/runtime_city/parts/evidence'/f'{id}.smoke.render.json'
  if samplepath.exists():r.update(compiled_cache=True,stage='compiled_cache',cache_refs=[ref(str(samplepath.relative_to(ROOT)))])
  if id in group_for:
   groups=group_for[id];r.update(source_present=True,compiled_sample=True,compiled_cache=True,resolved_placement=True,stage='resolved_placement',assembly_sources=groups,placement_evidence=ref(str((HERE/'resolved_placements.json').relative_to(ROOT))),placement_application='Candidate rigid transforms only; not applied to actual common city scene.')
   r['source_refs'] += [ref(str((HERE/'masters'/f'{g}.json').relative_to(ROOT))) for g in groups]
   r['cache_refs']=[x['render'] for x in cache['requests'] if x['id'] in groups]
  if id in water_for:
   w=wby[water_for[id]];r.update(source_present=True,compiled_sample=True,compiled_cache=True,stage='compiled_cache',current_local_module_id=w['id'],cache_refs=[w['compile_evidence']['render']]);r['source_refs'].append(w['source']);r['remaining_work'].append(w['remaining_work'])
  if id in related:r['related_partial_modules']=[{'id':k,'source':wby[k]['source'],'compiled_cache':wby[k]['compiled_sample']} for k in related[id]]
  if id in ('full_cloister_corners_and_court','cathedral_tracery_and_roof_detail'):
   r['related_partial_assembly']='cathedral';r['remaining_work'].append('Frozen cathedral cache supplies partial cloister/silhouette only; this full-detail family is not complete.')
  rows.append(r)
 for w in water['entries']:
  rows.append({'id':'waterworks/'+w['id'],'family':'water_bridge_terrace','stage':'compiled_cache' if w['compiled_sample'] else 'missing','source_present':w['source_present'],'compiled_sample':w['compiled_sample'],'compiled_cache':w['compiled_sample'],'resolved_placement':False,'actual_common_asset_placed_in_v3':False,'actual_viewed_in_v3':False,'complete_facility':False,'partial_coverage':True,'source_refs':[w['source']] if w.get('source') else [],'cache_refs':[w['compile_evidence']['render']] if w.get('compile_evidence') else [],'network':w['network'],'remaining_work':[w['remaining_work']]})
 extras=[
 ('castle_stables','castle','resolved_placement','castle','Two purpose-authored stables in castle cache. Doors remain closed; livestock/interior/operation unimplemented.'),
 ('cathedral_partial_cloister','cathedral','resolved_placement','cathedral','Two open-ended runs only; closed court corners and secondary access remain incomplete.'),
 ('monastery_cloister_garden_enclosure','monastery','resolved_placement','monastery','Partial cloister, planted-bed proxies and enclosure exist in cache; complete gardens/interiors remain pending.'),
 ('port_land_apron_quay_foundations','port','resolved_placement','port_cluster','Candidate land fill, quay footings and twelve pile locations pass source support checks; structural/scene ownership pending.'),
 ('castle_actual_primary_access','castle','source_only','castle','Actual openings exist; old parent path supersession and bounded R_CASTLE proposal await approved source-plan application.'),
 ('perimeter_gate_assemblies','gates','source_only',None,'Existing gatehouse factory; new V3 perimeter gate placements, door mechanics and traversal not resolved here.'),
 ('park_and_garden_recipe_families','park','source_only',None,'Eight V3 landscape sources/fixtures, no persistent caches or resolved V3 scene output from recipe worker.'),
 ('property_compound_and_service_families','social','source_only',None,'25 frozen property source specs, 15 unique sampled assets; no persistent caches or actual V3 scene placement from recipe worker.'),
 ('terrace_retaining_structure_assemblies','retaining','source_only',None,'Terrain source contains terrace/stair contracts; whole-slope exact common solids, ownership and collision remain pending.')]
 for id,fam,stage,g,gap in extras:
  refs=[]
  if g:refs=[ref(str((HERE/'masters'/f'{g}.json').relative_to(ROOT)))]
  rows.append({'id':id,'family':fam,'stage':stage,'source_present':True,'compiled_sample':bool(g) or id in ('park_and_garden_recipe_families','property_compound_and_service_families'),'compiled_cache':stage=='resolved_placement','resolved_placement':stage=='resolved_placement','actual_common_asset_placed_in_v3':False,'actual_viewed_in_v3':False,'complete_facility':False,'partial_coverage':True,'source_refs':refs,'remaining_work':[gap]})
 workers={
 'property':{'catalog':ref('world_city/concept_city_v3/assemblies/property/generated/cache_catalog.json'),'sampling':ref('world_city/concept_city_v3/assemblies/property/generated/sampling_report.json'),'source_specs':25,'unique_sampled_assets':15,'persistent_cache_payloads':0,'actual_v3_placement':False,'resolver':'Synthetic fixture tests only; zero actual scene output.'},
 'landscape':{'freeze':ref('world_city/concept_city_v3/assemblies/landscape/freeze_manifest.json'),'source_families':8,'persistent_cache_payloads':0,'actual_v3_placement':False,'visual_evidence':'Prior R3 woodland was viewed only in the rejected old-city repair cycle; no V3 actual asset review.'}}
 addon_specs=[('cathedral_service_lodge_addon','cathedral','resolved_placement','world_city/concept_city_v3/assemblies/landmarks/integration/evidence/annex_compile_report.json','Two candidate annex placements are held for image/world registration. Closed doors and service access remain unresolved.'),('stone_bridge_9m_deck_addon','bridge','compiled_cache','world_city/concept_city_v3/assemblies/waterworks/additions/evidence/compile_report.json','Width-correct local sample only. Bridge deck/approach discrepancy is recorded; no world placement or terrain override.')]
 for id,family,stage,path,gap in addon_specs:
  if not (ROOT/path).exists():continue
  a=read(path);rows.append({'id':id,'family':family,'stage':stage,'source_present':True,'compiled_sample':True,'compiled_cache':True,'resolved_placement':stage=='resolved_placement','actual_common_asset_placed_in_v3':False,'actual_viewed_in_v3':False,'complete_facility':False,'partial_coverage':True,'source_refs':[a['source']],'cache_refs':[a['render']],'remaining_work':[gap]})
 # Other workers may finish bounded packs after the earlier source-only snapshot.
 property_pack='world_city/concept_city_v3/assemblies/property/resolved_placements.json'
 property_cache='world_city/concept_city_v3/assemblies/property/cache/manifest.json'
 landscape_pack='world_city/concept_city_v3/assemblies/landscape/resolved_placements.json'
 if (ROOT/property_cache).exists():
  pp,pc=read(property_pack),read(property_cache)
  workers['property'].update(persistent_cache_payloads=len(pc['assets']),cache_manifest=ref(property_cache),resolved_pack=ref(property_pack),resolved_compounds=len(pp['resolved_properties']),resolved_placements=sum(len(p['placements']) for p in pp['resolved_properties']),actual_v3_placement=False,resolver='Current bounded pack for seven noble compounds; eleven merchant/poor compounds remain unresolved and six poor-pad candidates are inactive during registration.')
  for r in rows:
   if r['id'] in ('property_compound_and_service_families','large_noble_compound_container','service_housing_container','attached_housing_manors'):
    r.update(stage='resolved_placement',source_present=True,compiled_sample=True,compiled_cache=True,resolved_placement=True,placement_evidence=ref(property_pack),cache_manifest=ref(property_cache),remaining_work=['Seven noble compounds only; 133 candidate placements use ten caches. Eleven merchant/poor compounds remain unresolved. No actual V3 scene integration or viewing.'])
   if r['id']=='poorer_row_quarter_container':r.update(stage='source_only',source_present=True,compiled_sample=True,remaining_work=['Poor-block source recipes/sample fixtures exist. No active resolved poor-quarter pack; six pad candidates remain inactive during image registration.'])
 if (ROOT/landscape_pack).exists():
  lp=read(landscape_pack)
  workers['landscape'].update(persistent_cache_payloads=8,resolved_pack=ref(landscape_pack),resolved_placements=len(lp['placements']),actual_v3_placement=False,visual_evidence='No actual V3 scene review; old rejected-city R3 woodland review is not transferable.',remaining='Public common unresolved because large crowns do not fit; clergy cemetery still lacks a burial recipe.')
  for r in rows:
   if r['id'] in ('park_grove_trees','park_and_garden_recipe_families'):
    r.update(stage='resolved_placement',source_present=True,compiled_sample=True,compiled_cache=True,resolved_placement=True,placement_evidence=ref(landscape_pack),remaining_work=['1,274 terrain-projected candidates across six sites reuse eight caches: 824 trees, 438 understory, 12 beds. Public common and burial recipe remain unresolved. No actual V3 scene integration/viewing.'])
 counts=collections.Counter(r['stage'] for r in rows)
 result={'schema':'riverstone.city.implementation_coverage.v1','author':ref('world_city/concept_city_v3/assemblies/landmarks/build_implementation_coverage.py'),'coverage_scope':'All 75 prior required facility families, all 23 waterworks local/missing rows, plus 9 assembly/support/recipe families. Rows overlap intentionally; counts are not unique finished assets.','stage_definition':{'missing':'Required family/assembly not implemented completely; related partial sources may be linked.','source_only':'Continuous source/factory or explicit recipe exists; persistent V3 common cache/placement is not evidenced.','compiled_cache':'A persistent common render cache exists; local compile is not placement.','resolved_placement':'Candidate world transforms/support contract exist; not applied or approved actual scene geometry.','actual_viewed':'Actual common asset viewed in current V3 scene. No rows are assigned this stage.'},'counts':dict(counts),'actual_viewed_in_v3':0,'actual_common_asset_placed_in_v3':0,'complete_facilities_claimed':0,'entries':rows,'worker_evidence':workers,'landmark_access_gate':{'status':'blocked_pending_approved_supersession','proposal':ref(str((HERE/'access_supersession_proposal.json').relative_to(ROOT))),'obsolete_parent_paths':12,'primary_actual_opening_link_proposals':5,'castle_route_proposal':'Validator reports zero component overlaps and minimum 2.0 m strip-to-tower clearance; source-plan edit not applied.'},'viewing_boundary':'V3 source massing/blockout screenshots and old-city screenshots do not prove that these common caches were placed or viewed.','next_gates':['Approve revised blockout layout and actual-opening access supersession.','Apply surface ownership masks and correct terrain/bed/level support before common placements.','Compile only bounded unresolved parts; no new large compile before blockout QA.','Review actual common assets in scene, then controller/animation/hydraulic/structural work as applicable.']}
 result['coverage_scope']='All 75 prior required families, all 23 waterworks local/missing rows, nine assembly/support/recipe families and available bounded add-ons. Rows intentionally overlap; counts are not finished assets.'
 result['current_application_gate']='Held for direct concept-image/world registration; candidate placement and access overlays are not approved actual scene placement.'
 integration=HERE/'integration/landmark_integration_pack.json'
 if integration.exists():
  result['held_integration_pack']=ref(str(integration.relative_to(ROOT)))
  ip=json.loads(integration.read_text());result['landmark_access_gate'].update(obsolete_parent_paths=len(ip['suppress_path_ids']),unresolved_port_approach_links=len(ip.get('unresolved_port_access',[])))
 write(HERE/'implementation_coverage.json',result)
 doc=['# 전체 시설 구현 단계 / Implementation coverage','',f'총 {len(rows)}행입니다. 시설군과 해당 부품 행은 의도적으로 겹칩니다. 완성 시설 수로 더하지 않습니다.','', '현재 V3 실제 공통 자산 배치/화면 검토를 입증한 행은 0개입니다. 블록아웃 프록시 화면과 공통 마스터 화면은 다른 증거입니다.','', '단계: source_only=소스만, compiled_cache=로컬 렌더 캐시, resolved_placement=아직 적용하지 않은 월드 배치 후보, missing=필수 시설군 미완료.','', '| 시설 ID | 계열 | 확인 단계 | 남은 작업 |','|---|---|---|---|']
 for r in rows:doc.append('| '+r['id']+' | '+r['family']+' | '+r['stage']+' | '+' '.join(r['remaining_work']).replace('|','/')+' |')
 doc += ['', '## 접근로 보류', '', '옛 랜드마크 부모 질량의 문 연결 12개와 옛 항만 창고 연결 3개는 실제 새 입구 증거가 아닙니다. 실제 주 입구 5개와 성 도로의 첫 점 수정 제안은 검토 후 적용해야 합니다. 새 항만 창고의 접근로 6개는 아직 미승인입니다. 성 도로 수정안은 별도 제한 검사에서 구성 요소 충돌 0개, 탑과 도로 띠 사이 최소 2.0 m로 확인됐으나 원본 도로는 변경하지 않았습니다.', '', '## 다음 순서', '', '콘셉트 이미지·월드 정합 → 수정 블록아웃 승인 → 옛 경로 대체/실제 입구 연결 → 지형·바닥 소유권 적용 → 공통 캐시 배치 → 실제 화면·이동 검토. 전체 도시에 필요한 미완료 시설은 이 목록에 계속 남깁니다.']
 (HERE/'IMPLEMENTATION_COVERAGE.md').write_text('\n'.join(doc)+'\n');print(json.dumps({'rows':len(rows),'stages':dict(counts),'actual_common_placed':0,'actual_viewed':0}))
if __name__=='__main__':build()
