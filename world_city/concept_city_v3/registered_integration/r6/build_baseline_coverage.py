"""Actual R5 evidence overlay; earlier source catalogs stay historical snapshots."""
import collections,json
from . import apply_packs as a
HERE=a.HERE

def run():
 scene=a.load(a.BASE_PATH,a.BASE_SHA256); images=a.CITY/'evidence/visual_registered_common_r5'
 families=[
 ('ordinary_housing',['ordinary'],'registered','540 surviving ordinary instances use actual common caches. This is not the whole building count.','Long repeated frontage strips and large unassigned rear lands remain.'),
 ('attached_lower_housing',['ordinary_density','ordinary_density_b15'],'density_close','Attached common assemblies are present in two lower-city blocks.','More irregular inhabited courts and routes are required; household occupancy is not simulated.'),
 ('castle_cathedral_abbey_civic',['landmarks'],'registered','Main castle, cathedral, abbey and civic exterior masses are common geometry.','Detailed precinct use, fine tracery, defensive/internal circulation and final concept silhouette remain under review.'),
 ('noble_properties',['property'],'registered','Seven estate compounds retain distinct main/service buildings and enclosing infrastructure.','Productive grounds and remaining backlands need fuller functional treatment.'),
 ('outside_woodland',['woodland'],'registered','Irregular deterministic tree/understory placements exist outside walls.','Botanical/art polish and close-range forest traversal remain unfinished.'),
 ('institution_gardens',['landscape'],'clergy_compounds','Cloister, orchard, garden and selected burial components are native geometry.','The entire open precinct is not accounted for by these components.'),
 ('city_walls_and_gates',['fortifications'],'registered','Terrain-following common curtain/tower/gate components are present.','Whole-wall patrol paths, every gate approach and portcullis operation are not validated.'),
 ('river_port',['port'],'registered','Sheds, pile-supported piers, boats and crane components are present.','Workflows, every shed route, flood/wet stair access and cargo animation remain partial.'),
 ('central_market',['market'],'registered','Native stalls, goods and the protected fountain form the central market.','The fountain is small at city scale; logistics and street detail remain partial.'),
 ('north_reservoir',['reservoir'],'reservoir_north','Bed, banks, drawpoint, conduit, intake, sluice and service circuit are present in the upstream area.','No hydraulic or potable-water-quality simulation; source intake and city delivery remain design contracts.'),
 ('training_ground',['training'],'registered','Barracks, stores, stable and practice equipment are native geometry.','Gameplay actors, exercises and detailed access review remain pending.'),
 ('lower_workyards',['b13_workyards'],'density_close','Common workyard assemblies accompany one dense lower-city block.','Trade-specific machinery and additional coherent courts remain pending.'),
 ('new_clergy_abbey_service_compounds',['precinct_compounds'],'clergy_compounds','Six service compounds, productive gardens and planting are active in R5.','Rotated clergy unions have verified coarse façade striping; local-frame repair is pending.'),
 ('precinct_boundary_belts',['precinct_belts'],'abbey_compounds','Two native boundary/planting belt assemblies are active.','They are not proof that every large backland has an implemented use.'),
 ('seven_merchant_courts',['merchant_compounds'],'merchant_east','Seven properties replace detached frontage with 34 native modules in 14 runtime groups.','Only the M11 external court route has a positive capsule test; native closed doors are not playable interiors.'),
 ('finite_support_and_guard',['precinct_support','merchant_support','abbey_guard'],'abbey_compounds','Exact native bearing supports and an intentional retained-edge guard are active.','These are bounded repairs, not a whole-city support/traversal certificate.'),
 ('river_drawbridge_fixed_approaches',['drawbridge_fixed'],'south_road','Stone approaches coexist with the timber lifting mechanism.','The southern sampled road riser fails reverse traversal; bounded graded cover is pending.')]
 rows=[]
 for key,packs,view,present,remaining in families:
  instances=[p for p in scene['common_instances'] if p['source_pack'] in packs]
  assert instances,(key,packs)
  asset_keys=sorted({p['asset_key'] for p in instances})
  rows.append(dict(id=key,source_packs=packs,scene_instance_ids=[p['id'] for p in instances],scene_instance_count=len(instances),unique_asset_keys=asset_keys,
    geometry_stage='actual_common_geometry_in_sealed_scene',image_context=dict(path=a.rel(images/(view+'.png')),sha256=a.sha(images/(view+'.png'))),
    image_scope='Family visible in this actual context; individual hidden parts are not separately certified.',present=present,remaining=remaining,whole_function_complete=False))
 assert sum(r['scene_instance_count'] for r in rows)==len(scene['common_instances'])
 used={p['asset_key'] for p in scene['common_instances']}|set(scene['bridge_mechanism']['asset_keys'])
 refs=[]
 for key in sorted(used):
  x=scene['common_assets'][key]
  for kind in ['master','render']:
   path=a.source_file(x[kind+'_path']);assert a.sha(path)==x[kind+'_sha256'],(key,kind)
  refs.append(dict(key=key,master=dict(path=x['master_path'],sha256=x['master_sha256']),render=dict(path=x['render_path'],sha256=x['render_sha256'])))
 pending=['19 additional merchant holdings: compiled and sealed; finite R15 ground activation pending.',
 '60 remaining-land holdings / 26 range parcels: source programs only; productive-ground subset is in development.',
 'Southern reverse road passage: initial failure retained; new visible/collision cover under development.',
 'Clergy façade stair-striping: supported geometry diagnosed; aligned-frame caches under development.',
 'Whole-city interiors, NPC operations, live bridge actor registry, street detail, drainage and final concept-fidelity art are not complete.']
 out=dict(schema='riverstone.actual_city_exterior_evidence_overlay.v1',revision='r5_frozen_baseline_for_r6',
   scene=dict(path=a.rel(a.BASE_PATH),sha256=a.BASE_SHA256),
   prior_catalog_note='Older IMPLEMENTATION_COVERAGE/INVENTORY files describe their source-stage snapshot. This overlay provides later actual R5 evidence; it does not upgrade their unspecified details.',
   counts=dict(static_common_instances=len(scene['common_instances']),common_assets_including_mechanism=len(used),foundation_review_solids=len(scene['boxes'])),
   families=rows,asset_refs=refs,pending=pending,
   traversal=dict(market_court='60.53 m positive both directions in initial R5 capsule fixture.',southern_approach='FAIL: reverse 0.25 m riser contact; outward off-floor frames and low spawn hint retained.',negative_controls='Wall blocks and unsupported river loses floor as expected.',whole_city=False),
   actual_city_complete=False)
 dest=HERE/'actual_r5_coverage.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n')
 lines=['# R5 실제 도시 외관 증거 / R6 작업 기준','', '이 문서는 이전 부품 목록의 소스 단계 기록에 실제 R5 배치/화면 증거를 덧붙인다. 전체 도시 완성 판정은 아직 아니다.','',
 '| 구분 | 현재 실제 인스턴스 | 확인된 상태 | 남은 일 |','|---|---:|---|---|']
 for r in rows:lines.append('| '+r['id']+' | '+str(r['scene_instance_count'])+' | '+r['present']+' | '+r['remaining']+' |')
 lines+=['','인스턴스 수는 건물, 가구, 완성된 기능의 수가 아니다. 숲과 울타리, 지지대도 포함한다.','',
 '## 공정 입력','해시로 봉인한 R5 scene과 실제 Godot PNG 8개, 공통 master/cache, 초기 실제 캡슐 시험.','',
 '## 공정 조건','R5 원본 보존. 공통 geometry를 사용하며, 이후 변경은 새 R6 및 유한 지반/지지 패치로 적용한다.','',
 '## 공정 납품','actual_r5_coverage.json에 17개 가족별 실제 인스턴스 ID, 자산 해시와 화면 경로를 연결했다.','',
 '## 공정 완료 기준','실제 배치와 화면은 확인했지만, 주요 후면 부지·기능적인 구역·남쪽 역방향 통행과 조감도 충실도가 미완료다. 모든 가족의 whole_function_complete는 false다.','',
 '## 다음 작업']+['- '+x for x in pending]
 (HERE/'ACTUAL_COVERAGE_KO.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(dict(rows=len(rows),instances=len(scene['common_instances']),hash_verified_assets=len(refs),scene_sha256=a.BASE_SHA256,whole_city_complete=False)))
if __name__=='__main__':run()
