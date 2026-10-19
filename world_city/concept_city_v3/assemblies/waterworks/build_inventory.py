"""Evidence-separated facility inventory. Does not imply scene integration."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.assemblies.waterworks.author import HERE,KINDS,ref,write

LABELS={
 'spring_intake':('수원 취수구 / Spring intake','Observed spring/source network; intake detailing inferred','Connect 2 m feeder; upstream spring head and source protection require placement review.'),
 'covered_wellhouse':('지붕 있는 급수정 / Covered wellhouse','Draw point inferred from supply use','Local shaft/head depth must be adapted to the actual cistern or conduit node; bucket/rope not implemented.'),
 'reservoir_lining_segment':('저수지 벽체 구간 / Reservoir lining segment','Reservoir observed; exact lining inferred','8 m repeat segment and 2 m bed apron only; full floor, corners, inlet, outlet and spillway remain missing.'),
 'sluice_bay':('수문 제어 베이 / Sluice control bay','Canal control inferred','2 m gate bay; requires 6-to-2 m transition/bypass and runtime gate/stem synchronization.'),
 'covered_clean_conduit':('보호 급수관 / Covered supply conduit','Covered route is functional inference','A 4 m local shell; exact route, falls, seals and pressure controls remain unimplemented.'),
 'service_channel_segment':('공업 수로 구간 / Industrial canal segment','Open service canal observed','6 m wet width and 6 m length; joins, bends and local longitudinal grading require source authoring.'),
 'undershot_mill_wheel':('낙차가 작은 물레바퀴 / Low-head mill wheel','Water wheels observed; mechanism inferred','Single rotor part and axle hooks only; 0.8 m gross head does not establish useful power.'),
 'mill_bank_interface':('제방 쪽 방앗간 접점 / Bank-side mill interface','Mill location inferred from canal function','Bearing footings, axle tunnel and drive wall only; complete millhouse/gearing is missing.'),
 'canal_footbridge':('수로 보행교 / Canal footbridge','Crossings observed; exact span inferred','9 m span and 2.4 m route; landings, approach grading and guard continuity require placement review.'),
 'stone_road_bridge_bay':('석조 도로교 아치 구간 / Stone road-bridge bay','Multiarch bridge observed; exact arch inferred','16 m repeat, true barrel opening and half-piers; full bridge ends, river alignment and scour review are missing.'),
 'drain_outfall':('우수 배수구 / Storm outfall','Functional drainage inference','Outlet invert/receiving head and backwater controls must be checked; no sewer-to-supply connection.'),
 'retaining_stair_landing':('옹벽 계단과 층계참 / Retaining stair and landing','Terrace stairs observed; step dimensions inferred','Default 8×0.15 m source/sample; other riser counts are source variants requiring endpoint/pitch checks.')}
MISSING=[
 ('reservoir_complete_shell','raw_clean_source','Complete reservoir floor, corner pieces and sealed interfaces','Only one straight wall/apron module exists; 96×46 m reservoir remains a candidate domain.'),
 ('reservoir_overflow_spillway','raw_clean_source','Reservoir overflow and safe spillway','No controlled overflow geometry or flood/head calculation.'),
 ('settling_baffles_inlet_outlet','raw_clean_source','Settling inlet, baffles and protected offtake','Intake module is a spring source fixture, not a complete reservoir inlet/outlet train.'),
 ('covered_cistern','protected_supply','Covered storage cistern shell and inspection access','Wellhouse is only a draw-point structure; complete cistern source is missing.'),
 ('full_width_floodgate','industrial_nonpotable','6 m canal floodgate and full-width seal','The 2 m sluice bay is not a full-width floodgate.'),
 ('sluice_transition_bypass','industrial_nonpotable','6 m canal to 2 m sluice transition and bypass','No automatic taper, bypass or safe discharge path.'),
 ('millhouse_gearing_race_control','industrial_nonpotable','Complete millhouse, gearing, race splits and head-control weir','Wheel and bank interface are compiled separately; machinery/house shell remain incomplete.'),
 ('storm_underpass_culvert','storm','Drainage culvert crossing the service canal','Requires separate invert and sealed grade separation; protected conduit must not be reused as a cross-network connection.'),
 ('complete_bridge_assembly','crossing','Multiarch bridge assembly, end abutments and approach joins','Single bay and canal footbridge only; bridge-road width/heads must be resolved at each actual crossing.'),
 ('channel_bends_transitions','industrial_nonpotable','Canal bend, grade-change and junction liners','Straight module does not solve arbitrary path seams or water surface continuity.'),
 ('stair_endpoint_assemblies','pedestrian_terrace','Whole-slope stair flights and retaining landings','Default fixture and source parameter variants exist; city-specific endpoints, guards and collision remain unplaced.')]


def build():
 report=json.loads((HERE/'evidence/compile_report.json').read_text());by={r['id']:r for r in report['requests']};rows=[]
 for kind in KINDS:
  path=HERE/'masters'/f'{kind}.json';m=json.loads(path.read_text());r=by.get(kind);ok=bool(r and r['valid'] and r['source']==ref(str(path.relative_to(ROOT))) and r['render']==ref(r['render']['path']))
  label,basis,gap=LABELS[kind]
  rows.append({'id':kind,'label':label,'family_status':'partial_local_module','evidence_basis':basis,'network':m['extensions']['network'],'source_present':True,'source':ref(str(path.relative_to(ROOT))),'compiled_sample':ok,'compile_evidence':r if ok else None,'actual_placed':False,'visually_reviewed':False,'runtime_functional':False,'complete_facility':False,'datum':m['extensions']['datum'],'authored_parameters':m['extensions']['authored_parameters'],'footprint_xz_m':m['extensions']['footprint_xz_m'],'sockets':m['extensions']['sockets'],'supports':m['extensions']['supports'],'clearances':m['extensions']['clearances'],'animation_hooks':m['extensions']['animation_hooks'],'remaining_work':gap})
 for kind,net,label,gap in MISSING:rows.append({'id':kind,'label':label,'network':net,'family_status':'missing_or_incomplete_assembly','source_present':False,'compiled_sample':False,'actual_placed':False,'visually_reviewed':False,'runtime_functional':False,'complete_facility':False,'remaining_work':gap})
 result={'schema':'riverstone.city.waterworks_inventory.v1','author':ref('world_city/concept_city_v3/assemblies/waterworks/build_inventory.py'),'status':'local_modules_only_pending_layout_approval','prior_city_inventory':ref('world_city/runtime_city/parts/inventory.json'),'head_contract':ref(str((HERE/'head_contract.json').relative_to(ROOT))),'counts':{'compiled_local_modules':sum(r['compiled_sample'] for r in rows),'missing_or_incomplete_families':len(MISSING),'actual_placed':0,'visually_reviewed':0,'complete_facilities':0},'status_definition':{'source_present':'A local continuous standard master is authored.','compiled_sample':'Matching source and cache hashes passed one bounded common compilation.','actual_placed':'Integrated into the approved whole-city source/scene with support/access ownership. All false here.','visually_reviewed':'Reviewed in actual target scene. All false here.','complete_facility':'System/assembly and functional integration completed. All false here.'},'entries':rows}
 write(HERE/'inventory.json',result)
 text=['# 수리 시설 부품 목록 / Waterworks inventory','', '현재 로컬 원본 12개, 공통 컴파일 샘플 12개입니다. 실제 도시 배치, 화면 검토, 완성된 시설은 각각 0개입니다. 아래의 미완료 11개 시설군은 완성된 것으로 계산하지 않습니다.','', '| 부품 / 시설 | 원본 | 컴파일 샘플 | 실제 배치 | 화면 검토 | 남은 작업 |','|---|---|---|---|---|---|']
 for r in rows:text.append('| '+r['label']+' | '+('있음' if r['source_present'] else '미완료')+' | '+('통과' if r['compiled_sample'] else '없음')+' | 없음 | 없음 | '+r['remaining_work']+' |')
 (HERE/'INVENTORY.md').write_text('\n'.join(text)+'\n')
 print(json.dumps(result['counts']))
 return result
if __name__=='__main__':build()
