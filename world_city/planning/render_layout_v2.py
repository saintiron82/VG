#!/usr/bin/env python3
"""Draw existing planning data as SVG/standalone HTML. No voxel or game rendering."""
from pathlib import Path
import json, html
R=Path(__file__).resolve().parents[2];d=json.loads((R/'world_city/data/city_brief.v2.json').read_text());O=R/'world_city/maps';O.mkdir(exist_ok=True)
def esc(s):return html.escape(str(s),quote=True)
def pts(p):return' '.join(f'{x:.2f},{z:.2f}'for x,z in p)
n={n['id']:(n['position_m'][0],n['position_m'][2])for n in d['road_nodes']}
s=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-850 -850 1700 1650" role="img" aria-label="중세 핵심 도시 배치 계획도">', '''<style>text{font-family:'Noto Sans CJK KR','Noto Sans KR',Arial,sans-serif;fill:#283c3c} .district{font-size:21px;font-weight:700;paint-order:stroke;stroke:#fff9e8;stroke-width:5px;stroke-linejoin:round} .small{font-size:14px} .building{cursor:pointer;stroke:#654631;stroke-width:.6}.building:hover{stroke:#b34e28;stroke-width:3} .callout{font-size:15px;font-weight:600;paint-order:stroke;stroke:#fff9e8;stroke-width:4px}</style>''', '<rect x="-850" y="-850" width="1700" height="1650" fill="#eee8d6"/>', '<text x="-790" y="-784" font-size="34" font-weight="700">중세 핵심 도시 · 도시 구조 배치 v2</text>', '<text x="-790" y="-748" font-size="18">컨셉 v1 연계 / 수량보다 동선과 필지를 우선한 계획 / 기존 공통 복셀 프레임워크 참조</text>', '<text x="-790" y="-719" font-size="16" fill="#8a4a31">2D 설계도이며 실제 게임 화면이 아닙니다. 높이·배수·길찾기·새 건물 조립은 아직 미검증입니다.</text>']
# Quiet agricultural strips, distinct from city blocks.
for x in range(-760,740,85):s.append(f'<path d="M{x},625 l-18,100" stroke="#c6c08c" stroke-width="42" opacity=".32"/>')
water=d['river_reservation'];s.append(f'<polyline points="{pts(water["centerline_xz_m"])}" fill="none" stroke="#93bec2" stroke-width="{water["width_candidate_m"]}" stroke-linejoin="round"/>')
s.append('<text x="-610" y="560" font-size="18" fill="#386b75">강 · 서쪽에서 동쪽으로 → (설계 가정)</text>')
s.append(f'<polygon points="{pts(d["wall_outline_xz_m"])}" fill="#ded8bd" stroke="#7e8075" stroke-width="10"/>')
# Suggest the two high grounds without inventing contours.
for x,z,rx,rz in [(-430,-330,110,80),(350,-300,115,85)]:s.append(f'<ellipse cx="{x}" cy="{z}" rx="{rx}" ry="{rz}" fill="#b6b29a" opacity=".45"/>')
for f in d['site_features']:
    if f['kind'] in ('precinct','garden_reservation'):
        col='#c6c9a7' if f['kind']=='garden_reservation' else '#e9dfc3'
        s.append(f'<polygon points="{pts(f["footprint_xz_m"])}" fill="{col}" stroke="#c4b28b" stroke-width="1"/>')
    if f['kind']=='loading_pier':s.append(f'<polygon points="{pts(f["footprint_xz_m"])}" fill="#9e8766" stroke="#6a5845" stroke-width="1"/>')
for p in d.get('plots',[]):
    if p.get('courtyard_xz_m'):s.append(f'<polygon points="{pts(p["courtyard_xz_m"])}" fill="#bfc3a1" stroke="#8c997f" stroke-width=".6"/>')
for r in d['roads']:
    a,b=n[r['from_node']],n[r['to_node']];col='#8d8b76'if r['kind']=='wall_walk'else'#bcb28f'if r['kind']=='bridge'else'#f6f0db'
    s.append(f'<path d="M{a[0]},{a[1]} L{b[0]},{b[1]}" stroke="{col}" stroke-width="{r["width_m"]}" fill="none"><title>{esc(r["id"])}</title></path>')
for f in d['site_features']:
    if f['kind']=='market_square':s.append(f'<polygon points="{pts(f["footprint_xz_m"])}" fill="#ebe1c7" stroke="#c4b28b" stroke-width="1"/>')
for b in d['building_plans']:
    color={'exterior_only':'#658284','active_gameplay':'#ad8a48','interior_selected':'#d8c6a2'}[b['implementation_tier']]
    label=f'{b["id"]} {b["name"]} | {b["implementation_tier"]} | {b["road_access"]["road_id"]}'
    s.append(f'<polygon id="{b["id"]}" class="building" data-building="{b["id"]}" points="{pts(b["footprint_xz_m"])}" fill="{color}"><title>{esc(label)}</title></polygon>')
    x,z=b['entrance']['position_xz_m'];s.append(f'<circle cx="{x}" cy="{z}" r=".9" fill="#493729" pointer-events="none"/>')
for f in d['site_features']:
    if f['kind']=='water_postern':
        x,_,z=f['position_m'];s.append(f'<circle cx="{x}" cy="{z}" r="6" fill="#f6f0db" stroke="#687d77" stroke-width="2"><title>계획 수문 · 하역 통로</title></circle>')
    if f['kind']=='well_courtyard_reservation':
        x,_,z=f['position_m'];s.append(f'<circle cx="{x}" cy="{z}" r="3" fill="#418a9d" stroke="#e8dab7" stroke-width="1"><title>공동 우물 후보 · 공공 접근 검토 필요</title></circle>')
for b in d['building_plans']:
    if b['functional_role']=='gatehouse':
        x,z=b['road_access']['connection_xz_m'];s.append(f'<circle cx="{x}" cy="{z}" r="3.4" fill="#f6f0db"/><text x="{x+12}" y="{z-12}" class="callout">{esc(b["name"])}</text>')
s.append('<text x="255" y="558" class="callout">돌다리 → 남문</text>')
s.append('<text x="-340" y="498" class="callout">하역 부두 · 창고 진입</text>')
# First section remains an explicit planning highlight.
g=[b for b in d['building_plans']if b['id']==d['first_section']['start_gate_building']][0]
gx,gz=g['road_access']['connection_xz_m']
rt=next(r for r in d['street_routes'] if r['id']==d['first_section']['route_id'])
s.append(f'<polyline points="{pts(rt["polyline_xz_m"])}" stroke="#b46c42" stroke-width="4" stroke-dasharray="8 5" fill="none" opacity=".9"/>')
s.append(f'<text x="{gx+20}" y="{gz-65}" class="callout">첫 제작축: 남문 → 시장</text>')
for di in d['districts']:
    if di['id']=='D09':continue
    x,z=di['anchor_xz_m'];s.append(f'<text x="{x}" y="{z-48}" text-anchor="middle" class="district">{di["id"]} {esc(di["name"])}</text>')
s.append('<text x="-130" y="468" text-anchor="middle" class="callout">수문 2곳 · 하역길 → 창고</text>')
# Consistent landmark labels.
s.append('<text x="-20" y="24" text-anchor="middle" class="callout">분수·큰 시장</text>')
s.append('<circle cx="-20" cy="0" r="5" fill="#418a9d" stroke="#e8dab7" stroke-width="3"/>')
s.append('<text x="-750" y="-575" font-size="18" font-weight="700">N</text><path d="M-743,-555 v60 M-753,-544 l10,-18 10,18" fill="none" stroke="#3e5554" stroke-width="3"/>')
s.append('<path d="M-760,748 h200 m-200,-6 v12 m100,-12 v12 m100,-12 v12" stroke="#3e5554" stroke-width="2"/><text x="-760" y="777" class="small">0                    100                    200m</text>')
legend=[('#658284','외관 중심'),('#ad8a48','기능 상호작용'),('#d8c6a2','선택 실내'),('#b46c42','첫 제작축')]
for i,(color,label)in enumerate(legend):
    x=-250+i*210;s.append(f'<rect x="{x}" y="735" width="22" height="18" fill="{color}" stroke="#654631"/><text x="{x+31}" y="750" font-size="16">{label}</text>')
s.append(f'<text x="-250" y="777" class="small">계획 {len(d["building_plans"]):,}동 · 초록은 중정 / 모든 수량·위치 기획값</text></svg>')
svg='\n'.join(s);(O/'city_layout_v2.svg').write_text(svg)
# Self-contained, without remote libraries, telemetry or network requests.
payload=json.dumps({b['id']:b for b in d['building_plans']},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>중세 도시 배치 초안</title><style>body{margin:0;background:#eee8d6;color:#283c3c;font-family:system-ui,sans-serif}header{padding:16px 24px;background:#304f51;color:#fff}header h1{font-size:22px;margin:0 0 8px}header p{margin:0;font-size:14px}main{display:grid;grid-template-columns:minmax(0,1fr) 330px;min-height:90vh}.map{overflow:auto}.map svg{width:100%;min-width:1000px}aside{padding:22px;background:#fcf8ec;border-left:1px solid #c4b795;position:sticky;top:0;height:95vh;overflow:auto;box-sizing:border-box}input{padding:10px;width:90%;font-size:16px}button{padding:10px;margin:8px 0}dt{font-weight:700;margin-top:14px}dd{margin:5px 0;font-size:14px;line-height:1.5}.focus{stroke:#e55b22!important;stroke-width:4!important}@media(max-width:800px){main{display:block}aside{position:static;height:auto}.map{max-height:75vh}}</style><header><h1>중세 핵심 도시 · 도시 구조 배치 v2</h1><p>건물을 눌러 기능, 출입구, 연결 도로, 구현 수준을 확인하세요. 실제 복셀 도시·충돌·길찾기는 아직 구현되지 않았습니다.</p></header><main><section class="map">'''+svg+'''</section><aside><input id="search" placeholder="건물 ID 또는 이름 검색"><button id="find">찾기</button><p id="result">성·성당·시청과 서로 다른 필지 깊이를 갖춘 2D 배치입니다.</p><h2 id="name">건물을 선택하세요</h2><dl id="detail"></dl><p>표기 위치와 숨은 시설은 설계 추론입니다. 내부는 선택한 건물의 필요한 방만 제작하며 모든 건물을 개방하지 않습니다.</p></aside></main><script>const data='''+payload+''';let active;function show(id){let b=data[id];if(!b)return;if(active)document.getElementById(active)?.classList.remove('focus');active=id;document.getElementById(id)?.classList.add('focus');document.getElementById('name').textContent=b.name;const rows=[['ID',b.id],['기능',b.functional_role],['구현 등급',b.implementation_tier],['문 위치 X/Z',b.entrance.position_xz_m.join(', ')+' m'],['도로 연결',b.road_access.road_id+' / '+b.road_access.mode],['footprint',b.footprint_xz_m.map(p=>p.join(', ')).join(' | ')],['원본 참조 용도',b.asset_usage],['자산 원본',b.asset_ref.path],['조립 상태',b.assembly_status],['제작 경계',b.assembly_note],['검증 상태','계획 데이터. 높이·문 통과·길찾기는 아직 미검증']];const dl=document.getElementById('detail');dl.replaceChildren();for(const [a,v]of rows){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=a;dd.textContent=v;dl.append(dt,dd)}}document.querySelector('svg').addEventListener('click',e=>{const id=e.target.getAttribute('data-building');if(id)show(id)});document.getElementById('find').onclick=()=>{let q=document.getElementById('search').value.trim();if(!q){document.getElementById('result').textContent='건물 ID 또는 이름을 입력하세요.';return}let b=Object.values(data).find(b=>b.id===q||b.name.includes(q));document.getElementById('result').textContent=b?'찾음: '+b.id:'일치하는 건물이 없습니다.';if(b){show(b.id);document.getElementById(b.id).scrollIntoView({block:'center',inline:'center',behavior:'smooth'})}};</script></html>'''
(O/'city_layout_v2.html').write_text(page)
print(json.dumps({'svg_bytes':len(svg.encode()),'html_bytes':len(page.encode())}))
