"""Data diagram of the functional audit, not a game render or traversal certificate."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[4];C=R/'world_city/concept_city_v3';H=Path(__file__).resolve().parent
plan=json.loads((C/'registered_source/plan.json').read_text());water=json.loads((H/'network/observed_facility_location_candidates.json').read_text())['selected']
W,HIMG=1600,1200;im=Image.new('RGB',(W,HIMG),'#ecebe5');d=ImageDraw.Draw(im)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
f=lambda n:ImageFont.truetype(font,n)
def xy(p):return (40+(p[0]+560)*.92,70+(p[1]+510)*.92)
def line(points,fill,width=2):d.line([xy(p)for p in points],fill=fill,width=width,joint='curve')
colors={'D_CASTLE':'#aba4a0','D_TRAIN':'#c7b491','D_NOBLE':'#b1bea0','D_CLERGY':'#c8c5ae','D_MONASTERY':'#b4c19e','D_MARKET':'#dfcda7','D_POOR':'#ccb7a7','D_PORT':'#b8a68e','D_COMMON':'#c3ceae','D_BASIN':'#80a7b3'}
for r in plan['districts']:
 if r['id']in colors:d.polygon([xy(p)for p in r['polygon_xz_m']],fill=colors[r['id']],outline='#8a8880')
for r in plan['roads']:line(r['polyline_xz_m'],'#c8c9bd',max(1,round(r['width_m']*.92)))
for c in plan['water_reservations'].get('channels',[]):line(c['polyline_xz_m'],'#6394a4',max(2,round(c.get('width_m',3)*.92)))
b=plan['boundary_xz_m'];line(b+[b[0]],'#3a423f',5)
labels={'D_CASTLE':'CASTLE','D_TRAIN':'MILITARY','D_NOBLE':'NOBLE HOUSEHOLDS','D_CLERGY':'CATHEDRAL / CHAPTER','D_MONASTERY':'ABBEY / SERVICE','D_MARKET':'MARKET','D_POOR':'CRAFT / LOWER HOUSING','D_BASIN':'RESERVOIR'}
for row in plan['districts']:
 if row['id'] in labels:
  pts=row['polygon_xz_m'];p=[sum(q[i]for q in pts)/len(pts)for i in (0,1)];x,y=xy(p);d.text((x,y),labels[row['id']],font=f(13),fill='#303b36',anchor='mm',stroke_width=2,stroke_fill=colors[row['id']])
for i,row in enumerate(water,1):
 p=row['point_m'];x,y=xy([p[0],p[2]]);d.ellipse((x-11,y-11,x+11,y+11),fill='#f0cf6e',outline='#8b6929',width=2);d.text((x,y),str(i),font=f(14),fill='#342d1e',anchor='mm')
for row in plan['gates']:
 x,y=xy(row['position_xz_m']);d.rectangle((x-6,y-6,x+6,y+6),fill='#346c64');d.text((x+10,y), 'SOUTH PUBLIC' if 'MAIN'in row['id']else'NORTH SERVICE',font=f(12),fill='#203a34',anchor='lm')
for label,p in [('WEST candidate',[-400.108,-232.024]),('EAST candidate',[426.708,-3.431])]:
 x,y=xy(p);d.rectangle((x-7,y-7,x+7,y+7),fill='#dc9d58',outline='#704720',width=2);d.text((x,y-16),label,font=f(13),fill='#704720',anchor='mm')
d.rectangle((1090,0,W,HIMG),fill='#f7f6f0')
x,y=1120,58
for text,size in [('CITY FUNCTION AUDIT',25),('56.833 ha | design 6,000 residents',17),('SOURCE DIAGRAM — CANDIDATES',15)]:d.text((x,y),text,font=f(size),fill='#263b36');y+=size+17
items=[('37.07%','Castle, military, noble, clergy and abbey\ngross precinct union; not all private luxury.'),('20.92%','Clergy + abbey gross union. Includes real\ngardens, service yards, school and charity.'),('3.010 ha','Seven actual noble holdings. Distinct from\nthe 5.403 ha gross noble district.'),('1.375 ha','Market precinct. Regional market-day use\nis a design assumption, not measured demand.'),('493 / 536','Residential modules with a market-linked\npublic network station on observed heights.\n43 unproven; door last-mile not certified.'),('6 yellow circles','Analytical public water station candidates.\nActual tanks must move off the road into\nfinite public pockets. No flow/potability claim.'),('Orange gates','New east/west openings and external roads.\nFull-route capsule/cart QA in progress;\nnot counted as accepted public gates yet.')]
for title,body in items:
 d.text((x,y),title,font=f(21),fill='#36574c');y+=31
 for s in body.split('\n'):d.text((x,y),s,font=f(15),fill='#4d554f');y+=23
 y+=22
d.text((40,1134),'Plan geometry and observed-route analysis. Source roads shown; public/private entry rights and actual terrain tests remain separate.',font=f(16),fill='#334b42')
d.text((40,1160),'Water circles are network stations, not approved structure footprints. No institution size is judged from area ratio alone.',font=f(16),fill='#334b42')
out=H/'functional_plan_diagnostic_r01.png';im.save(out)
(H/'functional_plan_diagnostic_r01.json').write_text(json.dumps({'kind':'data_diagram_not_game_render','sources':[{'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in [C/'registered_source/plan.json',H/'network/observed_facility_location_candidates.json',H/'network/observed_summary.json']], 'limits':'Road lines are source geometry; water circles and orange gates are candidates, not runtime/supply acceptance.'},indent=2)+'\n')
print(out)
