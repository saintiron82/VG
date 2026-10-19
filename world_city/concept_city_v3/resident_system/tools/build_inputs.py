#!/usr/bin/env python3
"""Deterministic RPG content templates + strict historical route import. No geometry edits."""
import argparse, copy, hashlib, json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1]
NETWORK = HERE.parent/'registered_integration/r10_functional_audit/network'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def read(p): return json.loads(Path(p).read_text())
def write(p,d): Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def rel(p): return str(Path(p).resolve().relative_to(ROOT))
def ref(p): return {'path':rel(p),'sha256':sha(p)}

def templates():
    shops={
      'port_secondhand': {'name':'닻과 헌칼','district':'harbor','specialty':'salvaged adventuring equipment','price_band':'budget',
        'owner_personality':'blunt, practical, remembers sailors','pitch':'새것은 드물어도 손에 맞는 장비는 있지. 흠집 난 사연까지 골라 보게.',
        'catalog':[{'id':'worn_sabre','label':'수리한 선원 칼','price_units':18},{'id':'rope_bundle','label':'소금 밴 밧줄','price_units':5},{'id':'patched_coat','label':'기운 방수 외투','price_units':12}],
        'signage':{'symbol':'anchor_crossed_with_old_blade','materials':['weathered_wood','rope'],'accent':'faded_teal'},'quest':'lost_cargo'},
      'custom_smith': {'name':'세 번 두드린 쇠','district':'artisan','specialty':'made-to-order arms and repairs','price_band':'mid_to_premium',
        'owner_personality':'patient perfectionist, dislikes rushed orders','pitch':'손잡이부터 자네 손에 맞추지. 제대로 만들 시간은 주게.',
        'catalog':[{'id':'fitted_blade_order','label':'맞춤 검 주문 상담','price_units':90},{'id':'armour_repair','label':'갑옷 수선','price_units':24}],
        'signage':{'symbol':'three_hammer_marks','materials':['black_iron','oak'],'accent':'ember_orange'},'quest':'missing_pattern'},
      'noble_jeweler': {'name':'은빛 매듭','district':'noble_frontage','specialty':'signet rings and discreet heirloom appraisal','price_band':'luxury',
        'owner_personality':'formal, discreet, notices family crests','pitch':'문장에는 주인이 있고, 보석에는 내력이 있지요.',
        'catalog':[{'id':'signet_ring','label':'문장 반지','price_units':240},{'id':'pearl_pin','label':'진주 옷깃 핀','price_units':160}],
        'signage':{'symbol':'silver_knot_ring','materials':['polished_wood','silver_leaf'],'accent':'deep_blue'},'quest':'borrowed_signet'},
      'herbalist': {'name':'서쪽 창가의 풀','district':'clergy_edge','specialty':'herbs, field dressings and ingredient identification','price_band':'low_to_mid',
        'owner_personality':'observant, gentle, skeptical of miracle cures','pitch':'길에서 딴 풀이라면 이름부터 확인해 드릴게요.',
        'catalog':[{'id':'field_bandage','label':'여행용 붕대','price_units':4},{'id':'bitter_herb','label':'쓴잎 묶음','price_units':7}],
        'signage':{'symbol':'hanging_three_herb_bundles','materials':['linen','twig'],'accent':'sage_green'},'quest':'marsh_sample'},
      'map_seller': {'name':'돌아오는 길','district':'market','specialty':'regional maps and annotated travel notes','price_band':'mid',
        'owner_personality':'curious storyteller, marks uncertainty clearly','pitch':'지도 빈칸은 실수일 수도, 아직 아무도 돌아오지 않은 길일 수도 있지.',
        'catalog':[{'id':'river_map','label':'강변 길 지도','price_units':16},{'id':'ruin_note','label':'폐허 탐사 쪽지','price_units':22}],
        'signage':{'symbol':'rolled_map_and_compass','materials':['canvas','brass'],'accent':'ochre'},'quest':'unmarked_bridge'},
      'cheap_inn': {'name':'낮은 처마','district':'poor_quarter','specialty':'cheap lodging and local rumors','price_band':'budget',
        'owner_personality':'warm, sharp memory for debts','pitch':'젖은 신발은 문가에 두고, 사정은 앉아서 얘기하게.',
        'catalog':[{'id':'common_bed','label':'공용방 침상','price_units':3},{'id':'stew','label':'따뜻한 스튜','price_units':2}],
        'signage':{'symbol':'low_roof_and_bowl','materials':['rough_wood'],'accent':'brick_red'},'quest':'missing_guest'}}
    quests={
      'lost_cargo':('물에 젖은 상자 하나가 명부에서 빠졌어.','Find the marked crate and return its ledger tag.'),
      'missing_pattern':('옛 스승의 칼틀이 돌아오면 다시 만들 수 있겠지.','Recover the maker’s missing blade pattern.'),
      'borrowed_signet':('이 문장의 주인을 조용히 확인해 주시겠어요?','Identify the owner of the borrowed signet.'),
      'marsh_sample':('강 하류에서 같은 풀이 다른 빛을 띤다더군요.','Bring a labeled marsh plant sample.'),
      'unmarked_bridge':('이 다리가 아직 있다면 지도를 고쳐야겠어.','Confirm whether the marked footbridge remains.'),
      'missing_guest':('짐은 두고 나갔는데 이틀째 소식이 없네.','Find the traveler who left their pack at the inn.')}
    return shops,{k:{'hook':v[0],'objective':v[1],'scope':'RPG quest hook; quest execution/content not implemented'} for k,v in quests.items()}

def base_config():
    shops,quests=templates()
    return {'schema':'riverstone.rpg_npcs.config.v1','seed':41029,'mode':'logical_fixture','start_tick':0,'day_ticks':240,'retry_ticks':5,
      'interaction_radius_m':3,'event_history_limit':1024,'names':{'given':['Ada','Bryn','Cora','Darin','Elin','Finn','Gwen','Hugh','Ira','Joss','Kira','Leon'],
      'family':['Miller','Reed','Stone','Baker','Wood','Brook','Carter','Ash']},
      'roles':{'shopkeeper':{'greeting':'어서 와요. 제 이름은 {name}입니다.','personality':'practical','schedule':[{'start_tick':0,'target':'home','activity':'rest'},{'start_tick':40,'target':'work','activity':'service'},{'start_tick':170,'target':'rest','activity':'rest'}]},
      'watch':{'greeting':'길은 비워 주세요. 무슨 일인가요?','personality':'observant','patrol_interval_ticks':35,'schedule':[{'start_tick':0,'target':'patrol','activity':'patrol'},{'start_tick':180,'target':'rest','activity':'rest'}]},
      'townsfolk':{'greeting':'오늘도 좋은 길 되세요.','personality':'reserved','schedule':[{'start_tick':0,'target':'home','activity':'rest'},{'start_tick':50,'target':'work','activity':'work'},{'start_tick':175,'target':'rest','activity':'rest'}]}},
      'shops':shops,'quests':quests,'anchors':{},'routes':[],'facilities':[],'limits':['Seeded fictional RPG identities, not a census.','Catalog prices are authored game units, not historical research.','No economy, production, household consumption or automatic trading.']}

def fixture(count=100):
    c=base_config(); names=list(c['shops'])
    for i in range(12): c['anchors'][f'A{i}']={'position_m':[i*8,0,0],'binding':'synthetic_fixture'}
    for i in range(11):
        for a,b in [(i,i+1),(i+1,i)]:
            points=[c['anchors'][f'A{a}']['position_m'],c['anchors'][f'A{b}']['position_m']]
            payload=json.dumps(points,separators=(',',':'))
            c['routes'].append({'id':f'FIXTURE:{a}:{b}','from':f'A{a}','to':f'A{b}','points':points,'profile_payload':payload,'profile_sha256':hashlib.sha256(payload.encode()).hexdigest(),'travel_ticks':8,'evidence':'synthetic_fixture','pedestrian':True})
    for i in range(count):
        role='shopkeeper' if i<len(names) else ('watch' if i%4==0 else 'townsfolk')
        shop=names[i] if role=='shopkeeper' else ''
        c['facilities'].append({'id':f'FIXTURE_SITE_{i:03}','npc_slots':{role:1},'home_anchor':f'A{i%12}',
          'work_anchor':f'A{(i+2)%12}','rest_anchor':f'A{i%12}','spawn_anchor':f'A{i%12}',
          'patrol_anchors':[f'A{i%12}',f'A{(i+1)%12}'],'shop_id':shop,
          'personality':c['shops'][shop]['owner_personality'] if shop else c['roles'][role]['personality'],
          'quest_ids':[c['shops'][shop]['quest']] if shop else [],'binding':'synthetic_fixture'})
    c['coverage']={'npc_slots':count,'unique_shop_templates':len(names),'geometrically_verified_city_shopfronts':0,'purpose':'CPU/state/view budget and behavior fixture only'}
    return c

def import_verified_routes(prepared, evidence, mapping):
    p=read(prepared); e=read(evidence)
    if e.get('prepared_sha256')!=sha(prepared): raise ValueError('evidence/prepared hash mismatch')
    results={r['id']:r for r in e['routes']}; profiles={r['id']:r for r in p['routes']}
    sources={k:v['sha256'] for k,v in p['sources'].items() if k in ['base_scene','finite_patch','visual_index']}
    source_refs={k:ref(Path(v['path'])) for k,v in p['sources'].items() if k in sources}
    for k,v in source_refs.items():
        if v['sha256']!=sources[k]: raise ValueError('source hash drift:'+k)
    routes=[]; anchors={}
    for rid,(start,end) in sorted(mapping.items()):
        r=profiles[rid]; result=results[rid]
        if r.get('expected_failure') or r.get('kind')=='negative_control': raise ValueError('negative control is not traversable')
        if result.get('pass') is not True or result.get('status')!='reached': raise ValueError('not positive pedestrian runtime evidence')
        pts=r['points']; payload=json.dumps(pts,separators=(',',':'),allow_nan=False)
        length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
        for name,pos in [(start,pts[0]),(end,pts[-1])]:
            if name in anchors and anchors[name]['position_m']!=pos: raise ValueError('endpoint mismatch')
            anchors[name]={'position_m':pos,'binding':'exact_route_endpoint','route_id':rid,'not_a_household_or_interior':True}
        routes.append({'id':rid,'from':start,'to':end,'points':pts,'profile_payload':payload,'profile_sha256':hashlib.sha256(payload.encode()).hexdigest(),
          'travel_ticks':math.ceil(length/1.4),'evidence':'runtime_verified','pedestrian':True,'source_hashes':sources,
          'prepared':ref(prepared),'runtime_evidence':ref(evidence),'source_road_ids':r.get('source_road_ids',[]),
          'scope':r.get('test_scope','Exact positive tested direction only. No whole-city navigation claim.')})
    return routes,anchors,sources,source_refs

def city_pilot(prepared=None,evidence=None):
    c=base_config(); c['mode']='source_bound_city'; c['day_ticks']=86400;c['retry_ticks']=30;c['start_tick']=28800
    for role in c['roles'].values():
        for row in role['schedule']: row['start_tick']*=360
        if 'patrol_interval_ticks' in role: role['patrol_interval_ticks']=1800
    c['roles']['shopkeeper']['schedule']=[{'start_tick':0,'target':'rest','activity':'rest'},{'start_tick':25200,'target':'work','activity':'service'},{'start_tick':64800,'target':'rest','activity':'rest'}]
    prepared=prepared or NETWORK/'port_full_chain/replay_r01/prepared_height_corrected_r03.json'
    evidence=evidence or NETWORK/'port_full_chain/replay_r01/evidence/runtime_r03/capsule.json'
    mapping={}
    for i in [0,5]:
        rid=f'PORT_SHED_{i}:FULL_MARKET_CHAIN'; mapping[rid]=(f'PORT_SHED_{i}:LOADING_BAY','MARKET:PUBLIC_GOAL');mapping[rid+'_REVERSE']=tuple(reversed(mapping[rid]))
    c['routes'],c['anchors'],c['active_source_hashes'],c['source_refs']=import_verified_routes(prepared,evidence,mapping)
    c['facilities']=[{'id':'RPG:PORT_SECONDHAND','npc_slots':{'shopkeeper':1},'work_anchor':'PORT_SHED_0:LOADING_BAY','home_anchor':'',
      'rest_anchor':'PORT_SHED_0:LOADING_BAY','spawn_anchor':'PORT_SHED_0:LOADING_BAY','shop_id':'port_secondhand',
      'personality':c['shops']['port_secondhand']['owner_personality'],'quest_ids':['lost_cargo'],
      'source_instance_id':'PORT_SHED_0','binding':'exact native loading-bay endpoint; authored RPG retail-use proposal',
      'interaction_space':'warehouse doorway/open bay; no shop interior modeled; lodging unbound'},
      {'id':'RPG:PORT_WATCH','npc_slots':{'watch':2},'work_anchor':'PORT_SHED_5:LOADING_BAY','home_anchor':'',
      'rest_anchor':'PORT_SHED_5:LOADING_BAY','spawn_anchor':'PORT_SHED_5:LOADING_BAY','patrol_anchors':['PORT_SHED_5:LOADING_BAY','MARKET:PUBLIC_GOAL'],
      'binding':'bounded patrol on exact tested directional profiles; repeated route is not distinct shop coverage'}]
    c['coverage']={'npc_slots':3,'unique_shop_templates':6,'operational_interaction_point_proposals':1,'instantiated_shop_interiors':0,
      'household_doors_certified':0,'geometry_status':'Historical source binding only until final composite evidence is selected.'}
    c['limits']+=['Port shop is an authored RPG reuse proposal at a real loading bay, not proof of an existing retail interior.',
      'Market public route goal is not a shop door and is never treated as one.','Other shop templates need reviewed facade/door/signage bindings before placement.',
      'Waypoint motion is live kinematic path following, not a fresh physics/crowd collision certificate.']
    return c

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=HERE/'fixtures');ap.add_argument('--prepared',type=Path);ap.add_argument('--evidence',type=Path)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    write(args.out/'rpg_100_fixture.json',fixture());write(args.out/'city_pilot.json',city_pilot(args.prepared,args.evidence))
    write(args.out/'shop_templates.json',{'shops':templates()[0],'quests':templates()[1],'status':'Authored RPG content; signage contract is not built geometry.'})
    print(json.dumps({'fixture':str(args.out/'rpg_100_fixture.json'),'city_pilot':str(args.out/'city_pilot.json'),'fixture_npcs':100,'city_pilot_npcs':3,'economy_enabled':False}))
if __name__=='__main__':main()
