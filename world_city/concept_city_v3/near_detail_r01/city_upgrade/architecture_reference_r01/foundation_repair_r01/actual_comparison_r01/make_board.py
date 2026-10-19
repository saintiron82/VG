"""Literal same-camera captures and crops; never edits geometry or source images."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import json, hashlib
O=Path(__file__).resolve().parent; P=O.parent; A=P.parent
b=A/'reconstruction_proof_r01/actual_godot_r02/front.png'
a=P/'actual_godot_r01/front.png'
ib=Image.open(b).convert('RGB'); ia=Image.open(a).convert('RGB')
d=np.any(np.array(ib)!=np.array(ia),axis=2); yy,xx=np.where(d)
br=json.loads((b.parent/'capture_report.json').read_text())['records']
ar=json.loads((a.parent/'capture_report.json').read_text())['records']
assert all(x['eye']==y['eye'] and x['target']==y['target'] and x['size_m']==y['size_m'] for x,y in zip(br,ar))
assert np.array_equal(np.array(ib)[:671],np.array(ia)[:671])
fp='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
small=ImageFont.truetype(fp,17); title=ImageFont.truetype(fp,28)
board=Image.new('RGB',(1500,980),'#faf9f6'); draw=ImageDraw.Draw(board)
draw.text((20,16),'FOUNDATION MASK REPAIR | ACTUAL GODOT, SAME CAMERA',fill='#222222',font=title)
draw.text((20,54),'Measured neutral stone + per-part ground registration. Upper geometry and palette unchanged.',fill='#333333',font=small)
for x,img,label in [(20,ib,'BEFORE: neutral stone lost during foreground masking'),(770,ia,'AFTER: 4,712 measured stone cells restored')]:
    draw.text((x,86),label,fill='#222222',font=small)
    board.paste(img.resize((708,487),Image.Resampling.LANCZOS),(x,115))
    draw.text((x,620),'Same pixel crop [310,625,870,740], displayed 1.25x',fill='#555555',font=small)
    board.paste(img.crop((310,625,870,740)).resize((700,144),Image.Resampling.NEAREST),(x,654))
for y,text,color in [(826,'Input r03 retained. Existing shaded pixel colors are not recovered physical albedo.','#555555'),(857,'Exact step count / concealed protrusion depth unresolved. Roof, railing and vegetation still need repair.','#8b2940'),(889,'Pipeline proof only. Not an approved final house, city replacement or gameplay-collision claim.','#8b2940')]:
    draw.text((20,y),text,fill=color,font=small)
board.save(O/'foundation_before_after.png')
report={'same_cameras':True,'upper_screenshot_rows_0_to_670_exactly_same':True,'changed_pixel_bbox_half_open':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'changed_pixels':int(d.sum()),'original_captures_unchanged':True,'display_only_resize_and_literal_crop':True,'crop_px':[310,625,870,740],'before_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'no_whole_house_art_approval':True}
(O/'comparison_replay.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
