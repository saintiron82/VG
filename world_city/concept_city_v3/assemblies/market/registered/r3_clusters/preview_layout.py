"""Code-native source diagram, not a game screenshot or generated concept image."""
import json,math
from pathlib import Path
from PIL import Image,ImageDraw
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[3]
d=json.loads((HERE/'resolved_placements.json').read_bytes());p=json.loads((CITY/'registered_source/plan.json').read_bytes());r=json.loads((HERE/'walkspace_report.json').read_bytes())
site=next(s for s in p['spaces'] if s['id']=='SITE_MARKET')['polygon_xz_m'];lo=[min(q[i] for q in site) for i in range(2)];hi=[max(q[i] for q in site) for i in range(2)]
im=Image.new('RGB',(1200,1040),'#242b2b');draw=ImageDraw.Draw(im);scale=min(1080/(hi[0]-lo[0]),860/(hi[1]-lo[1]))
def xy(q):return(60+(q[0]-lo[0])*scale,120+(q[1]-lo[1])*scale)
def poly(q,fill,outline=None):draw.polygon([xy(v) for v in q],fill=fill,outline=outline)
poly(site,'#b4aa91','#eee4cb')
road=d['access_overlay']['replace_roads'][0]
for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):poly(geo.road_ribbon(a,b,road['width_m']),'#e7dfcb')
for route in r['stall_routes']:draw.line([xy(q) for q in route['path_xz_m']],fill='#71885d',width=2)
colors={'grain':'#92734c','cloth_and_housewares':'#b66f50','produce':'#738363','fresh_food':'#779b9d'}
for stall in d['placements'][1:]:
 poly(stall['footprint_xz_m'],colors[stall['function']],'#41392f');x,y=xy(stall['customer_front_xz_m']);draw.ellipse((x-2,y-2,x+2,y+2),fill='#f9f1d1')
f=d['placements'][0]['position_m'];x,y=xy([f[0],f[2]]);rr=10*scale;draw.ellipse((x-rr,y-rr,x+rr,y+rr),outline='#e9dfc6',width=2);rr=2.4*scale;draw.ellipse((x-rr,y-rr,x+rr,y+rr),fill='#45848b',outline='#e7ddc5')
draw.text((40,25),'MARKET r3 - native clusters and reserved customer routes',fill='white',font_size=26)
draw.text((40,64),'104 stalls | 2.4 m customer routes | 7 m public bypass | original fountain',fill='#dbd4c0',font_size=20)
draw.text((40,1003),'Source plan diagram. All dimensions are game design values. No NPC / capsule approval.',fill='#dfd6c3',font_size=19)
im.save(HERE/'market_cluster_plan.png')
