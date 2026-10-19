"""One difficult direction at a time; fixed code grid with known physical mapping."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json
B=Path(__file__).resolve().parents[1];im=Image.new('RGB',(1024,1024),(0,255,0));d=ImageDraw.Draw(im);f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
for x in range(32,993,32):d.line((x,64,x,960),fill=(0,188,0))
for y in range(64,961,32):d.line((32,y,992,y),fill=(0,188,0))
d.rectangle((32,64,992,960),outline='black',width=2)
for y,label in [(128,'HAIR CROWN: y128'),(384,'CHIN: y384'),(640,'2 HEADS: y640'),(896,'SOLE: y896')]:d.line((32,y,992,y),fill=(0,120,0),width=2);d.text((36,y+4),label,font=f,fill='black')
d.line((512,64,512,960),fill=(0,135,0),width=2);d.text((35,16),'LEFT CAMERA (-X): NOSE POINTS RIGHT  --->   3 HEADS',font=f,fill='black');d.text((35,977),'Same approved Violet | orthographic | background #00FF00',font=f,fill='black')
for x,y in [(18,64),(1006,64),(18,960),(1006,960)]:d.rectangle((x-6,y-6,x+6,y+6),fill='black');d.rectangle((x-2,y-2,x+2,y+2),fill='white')
p=B/'reference/left_camera_single_template.png';im.save(p);j={'schema':'riverstone.single_view_template.v1','canvas':[1024,1024],'canonical_view':'left','camera_axis':[-1,0,0],'subject_nose_in_image':'right','crown_chin_sole_y':[128,384,896],'target_head_ratio':3,'axis_x':512,'grid_px':32,'metres_per_pixel':1.2/768,'unobserved_opposite_side':'AI inference constrained by approved identity, not new observed ground truth','template_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(B/'data/left_camera_template_contract.json').write_text(json.dumps(j,indent=2)+'\n');print(j)
