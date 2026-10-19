"""Code-authored correction diagram, not an edit of generated building pixels."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
im=Image.open(HERE/'blank_six_view_grid.png').convert('RGB')
d=ImageDraw.Draw(im)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',11)
t=json.loads((HERE/'template.json').read_text())
for name in ('front','right','back','left'):
 x0,y0,x1,y1=t['views'][name]['grid_bounds_px']
 for level,color in [('ridge','#cc297c'),('eaves','#1764b4'),('gallery_2','#0b9957'),('gallery_1','#a96814')]:
  y=int(y1-t['planned_height_planes_m'][level]*32)
  d.line((x0,y,x1,y),fill=color,width=2)
  d.rectangle((x0+4,y+2,x0+160,y+16),fill='#fffdf7')
  d.text((x0+5,y+3),level+' y='+str(y),fill=color,font=font)
for name in ('top','bottom'):
 x0,y0,x1,y1=t['views'][name]['grid_bounds_px']
 d.rectangle((x0,560,x1,654),fill='#efeeee',outline='#b40022',width=2)
 d.text((x0+12,575),'LEAVE THIS AREA EMPTY',fill='#b40022',font=font)
 d.text((x0+12,598),'DO NOT STRETCH GRID UPWARD',fill='#b40022',font=font)
 d.text((x0+12,621),'Drawing only y688 through1008',fill='#b40022',font=font)
 d.rectangle((x0,y0,x1,y1),outline='#b40022',width=2)
im.save(HERE/'correction_guide_r03.png')
