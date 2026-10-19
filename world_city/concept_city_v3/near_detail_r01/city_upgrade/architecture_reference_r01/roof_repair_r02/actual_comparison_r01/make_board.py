"""Literal source panels and actual same-camera captures; no image geometry editing."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np,json,hashlib
P=Path(__file__).resolve().parent;H=P.parent;R=next(p for p in P.parents if (p/'voxel_character').is_dir());O=H/'actual_godot_r01';B=H.parent/'roof_repair_r01/actual_godot_r01'
source=R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
ref=Image.open(source).convert('RGB');font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';title=ImageFont.truetype(font,25);small=ImageFont.truetype(font,15)
br=json.loads((B/'before/capture_report.json').read_text());ar=json.loads((O/'after/capture_report.json').read_text());bs={x['view']:x for x in br['records']};aa={x['view']:x for x in ar['records']}
for v in bs:
 for k in ['eye','target','up','projection','size_m','viewport_size']:assert bs[v][k]==aa[v][k],(v,k)
views=['front','right','back','left','top','bottom'];panel={'front':(0,0,512,512),'right':(512,0,1024,512),'back':(1024,0,1536,512),'left':(0,512,512,1024),'top':(512,512,1024,1024),'bottom':(1024,512,1536,1024)}
def fit(im,w,h):
 im=im.copy();im.thumbnail((w,h),Image.Resampling.LANCZOS);return im
def place(board,im,box):
 x,y,w,h=box;im=fit(im,w,h);board.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
b=Image.new('RGB',(1580,2040),'#faf9f6');d=ImageDraw.Draw(b);d.text((20,14),'ROOF r02 | SIX ACTUAL ORTHOGRAPHIC VIEWS',font=title,fill='#222222')
d.text((20,49),'REFERENCE PANEL (not globally registered)          BEFORE: foundation repaired          AFTER: measured tile regions + declared curvature',font=small,fill='#333333')
summary=[]
for i,v in enumerate(views):
 y=82+i*306;d.text((20,y),v.upper(),font=small,fill='#222222')
 ib=Image.open(B/'before'/f'{v}.png').convert('RGB');ia=Image.open(O/'after'/f'{v}.png').convert('RGB');nb=np.array(ib);na=np.array(ia);mask=np.any(na!=nb,axis=2);ys,xs=np.where(mask)
 # Fixed same-camera subject crop; same coordinates for before and after.
 crop=(260,80,930,760) if v in ['front','back'] else (300,80,880,760) if v in ['left','right'] else (300,170,880,642)
 place(b,ref.crop(panel[v]),(10,y+22,490,270));place(b,ib.crop(crop),(520,y+22,500,270));place(b,ia.crop(crop),(1050,y+22,500,270))
 summary.append({'view':v,'literal_same_pixel_crop':crop,'changed_pixels':int(mask.sum()),'changed_bbox':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]if len(xs)else None})
d.text((20,1932),'PARTIAL IMPROVEMENT: long bands removed; fine roof steps remain noisy. Underside and full fidelity unresolved.',font=small,fill='#9a2340')
d.text((20,1960),'Six-view evidence exposes defects. It does not establish reference fidelity or whole-house approval.',font=small,fill='#9a2340')
b.save(P/'roof_six_views_r02.png')
b=Image.new('RGB',(1600,870),'#faf9f6');d=ImageDraw.Draw(b);d.text((20,15),'ROOF r02 | SAME-CAMERA ACTUAL BEFORE / AFTER',font=title,fill='#222222')
for x,n in [(10,'before'),(810,'after')]:
 d.text((x+10,53),n.upper(),font=small,fill='#333333');im=Image.open((B if n=='before' else O)/n/'oblique.png').convert('RGB');place(b,im.crop((240,78,950,785)),(x,80,780,720))
d.text((20,822),'Long bands removed; individual tiles still too coarse/noisy to read clearly. Body and foundation unchanged.',font=small,fill='#9a2340');b.save(P/'roof_oblique_before_after_r02.png')
(P/'comparison.json').write_text(json.dumps({'same_cameras_all_7':True,'source':str(source.relative_to(R)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'actual_views_opened':['front','back','left','right','top','bottom','oblique'],'reference_panels_resized_for_display_only':True,'pixel_alignment_pass':False,'art_pass':False,'views':summary},indent=2))
