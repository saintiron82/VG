from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
import numpy as np
P=Path(__file__).resolve().parent;A=P.parent
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';t=ImageFont.truetype(font,24);f=ImageFont.truetype(font,16)
def place(b,im,box):
 x,y,w,h=box;im=im.copy();im.thumbnail((w,h),Image.Resampling.LANCZOS);b.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
reports={m:json.loads((P/m/'capture_report.json').read_text())for m in ['before','after']}
rows={m:{x['view']:x for x in r['records']}for m,r in reports.items()};diffs={}
for v in rows['after']:
 for k in ['eye','target','up','projection','size_m','viewport_size','unshaded','normal_patch','shadows_enabled']:assert rows['before'][v][k]==rows['after'][v][k],(v,k)
 a=np.array(Image.open(P/'before'/f'{v}.png').convert('RGB'));b=np.array(Image.open(P/'after'/f'{v}.png').convert('RGB'));different=(a!=b).any(2);different[:70]=False;y,x=np.where(different);diffs[v]={'changed_pixels_below_hud':int(different.sum()),'bbox':None if not len(x)else[list(map(int,[x.min(),y.min(),x.max()+1,y.max()+1]))][0]}
for mode in ['before','after']:assert (P/mode/'run.exit').read_text().strip()=='0'
(P/'pixel_comparison.json').write_text(json.dumps(diffs,indent=2))
b=Image.new('RGB',(1600,1290),'#faf9f6');d=ImageDraw.Draw(b);d.text((20,15),'ACTUAL GODOT | LOCAL ROOF CUT OWNERSHIP REPAIR',font=t,fill='#222222');d.text((20,50),'BEFORE: r04 + preserved gallery                                      AFTER: r05 + the same gallery',font=f,fill='#333333')
for y,stem,crop,h in [(83,'roof_close',(0,70,1180,812),500),(620,'oblique',(250,75,930,780),520)]:
 for x,m in [(10,'before'),(810,'after')]:place(b,Image.open(P/m/(stem+'.png')).convert('RGB').crop(crop),(x,y,780,h))
d.text((20,1180),'Recovered 18,965 tile cells; geometry and exact material exterior independently checked.',font=f,fill='#333333');d.text((20,1210),'Tile row separation improves, but orange saturation, stair-like speckling and unmeasured roof areas remain.',font=f,fill='#8a233c');d.text((20,1240),'This candidate does not pass whole-house art review. No city-wide propagation or playable build.',font=f,fill='#8a233c');b.save(P/'roof_gallery_before_after.png')
ref=Image.open(next(q for q in A.parents if q.name=='world_city')/'reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png').convert('RGB')
views=['front','right','back','left','top','bottom'];panels={'front':(0,0,512,512),'right':(512,0,1024,512),'back':(1024,0,1536,512),'left':(0,512,512,1024),'top':(512,512,1024,1024),'bottom':(1024,512,1536,1024)}
b=Image.new('RGB',(1580,2030),'#faf9f6');d=ImageDraw.Draw(b);d.text((20,12),'SOURCE REFERENCE / BEFORE / AFTER | SIX ACTUAL VIEWS',font=t,fill='#222222')
for i,v in enumerate(views):
 y=65+i*305;d.text((20,y),v.upper(),font=f,fill='#222222');crop=(260,80,930,760)if v in ['front','back']else(300,80,880,760)if v in ['left','right']else(300,170,880,642)
 place(b,ref.crop(panels[v]),(10,y+22,490,270))
 for x,m in [(520,'before'),(1050,'after')]:place(b,Image.open(P/m/(v+'.png')).convert('RGB').crop(crop),(x,y+22,500,270))
d.text((20,1930),'Source six-view contradictions remain. Ground/foundation retained; no claimed underside reconstruction.',font=f,fill='#8a233c');d.text((20,1962),'354 source tile operations; neighboring cuts isolated per tile. Exact-color facade work follows separately.',font=f,fill='#8a233c');b.save(P/'roof_gallery_six_views.png')
print(json.dumps(diffs))
