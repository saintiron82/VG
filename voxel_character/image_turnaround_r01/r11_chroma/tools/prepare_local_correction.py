"""Measurement annotation overlay only; the source illustration is untouched."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib
B=Path(__file__).resolve().parents[1];p=B/'generated/violet_left_camera_single_r01.png';im=Image.open(p).convert('RGB');d=ImageDraw.Draw(im);f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
for label,y in [('TARGET CROWN 157',157),('TARGET CHIN 470',470),('TARGET SOLE 1097',1097)]:
 for x in range(42,1216,24):d.line((x,y,min(x+13,1216),y),fill=(255,40,40),width=2)
 d.text((48,y-25),label,font=f,fill=(255,30,30),stroke_width=1,stroke_fill='white')
d.line((960,418,1170,418),fill=(0,70,255),width=3);d.text((930,389),'CURRENT CHIN 418',font=f,fill=(0,60,255),stroke_width=1,stroke_fill='white');d.line((1030,418,1030,470),fill=(255,30,30),width=4);d.polygon([(1022,458),(1038,458),(1030,470)],fill=(255,30,30));d.text((1042,433),'+52px',font=f,fill=(255,30,30),stroke_width=1,stroke_fill='white')
out=B/'reference/local_correction_targets_r02.jpg';im.save(out,quality=93);j={'source':'generated/violet_left_camera_single_r01.png','source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'overlay':'reference/local_correction_targets_r02.jpg','overlay_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'actual_canvas':[1254,1254],'targets_crown_chin_sole_y':[157,470,1097],'original_observed_crown_chin_sole_y':[157,418,1113],'desired_head_ratio':940/313,'allowed_change':'One imagegen local proportion correction. Preserve identity, approved costume/skin/hair/halo design. Do not elongate only facial features or create head/shoulder intersection. Keep coherent neck attachment.','annotation_is_not_subject_color_or_geometry':True,'generated_result_not_yet_available':True};(B/'data/local_correction_targets_r02.json').write_text(json.dumps(j,indent=2)+'\n')
