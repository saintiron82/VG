"""Compose literal same-camera actual captures. No generative editing or scene-image repair."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;I=P.parent/'actual_godot_r01'
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';title=ImageFont.truetype(font,26);small=ImageFont.truetype(font,17)
b=Image.new('RGB',(1600,1530),'#faf9f6');d=ImageDraw.Draw(b);d.text((20,15),'ACTUAL GODOT | SOURCE-BOUND TILE NORMALS',font=title,fill='#202020');d.text((20,53),'Same voxel geometry, colors, lighting and cameras. Partial readability improvement; art NOT approved.',font=small,fill='#803040')
for y,stem,crop,h in [(100,'oblique',(240,78,950,785),700),(850,'roof_close',(0,70,1180,812),500)]:
 for x,suffix in [(10,'before'),(810,'after')]:
  d.text((x+10,y-25),stem.upper()+' '+suffix.upper(),font=small,fill='#202020');im=Image.open(I/(stem+'_'+suffix+'.png')).convert('RGB').crop(crop);im.thumbnail((780,h),Image.Resampling.LANCZOS);b.paste(im,(x+(780-im.width)//2,y))
d.text((20,1400),'Large tile divisions are more visible. Speckle, unsupported backing, pale edge fragments and body defects remain.',font=small,fill='#803040')
d.text((20,1432),'Source barrel shape is a declared geometric prior. No photographic curvature recovery or full-house approval.',font=small,fill='#803040')
d.text((20,1464),'All six unshaded orthographic views remain pixel-identical to r04 below the HUD; 1.7m eye pair retained separately.',font=small,fill='#803040');b.save(P/'roof_normal_full_before_after.png')
