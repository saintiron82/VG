"""Requested review layout: original + whole AI turnaround + actual final views.

Only composition/resize of preserved inputs. No image or geometry retouch.
"""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'r07';CLOSE=OUT/'closure'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(size):
 path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
 return ImageFont.truetype(str(path),size) if path.exists() else ImageFont.load_default()
def paste_fit(canvas,path,box):
 im=Image.open(path).convert('RGB');x,y,w,h=box;im.thumbnail((w,h));canvas.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2));return {'path':str(path.relative_to(ROOT.parent.parent)),'sha256':sha(path),'source_size_px':Image.open(path).size,'display_box_px':box,'crop':None}
def make(aid,original):
 d=OUT/'generated'/(aid+'_r07c');orig=ROOT.parent/'image_characters_r01/reference'/original;sheet=ROOT.parent/'reference_turnarounds_r01'/(aid+'_turnaround.png');canvas=Image.new('RGB',(1600,1240),'white');draw=ImageDraw.Draw(canvas);large=font(22);small=font(17);title=font(25);draw.text((20,12),aid.upper()+' | Reference to r07c cloth correction',font=title,fill='#151515');draw.text((20,51),'Original supplied illustration',font=small,fill='#222222');draw.text((420,51),'AI three-view reference: front redesigned; side/back inferred',font=small,fill='#222222');inputs=[paste_fit(canvas,orig,(10,80,390,535)),paste_fit(canvas,sheet,(410,80,1180,535))]
 draw.line((15,630,1585,630),fill='#bbbbbb',width=2);draw.text((20,650),'Actual common voxel | front',font=large,fill='#222222');draw.text((555,650),'Actual common voxel | three-quarter',font=large,fill='#222222');inputs += [paste_fit(canvas,d/'voxel_front.png',(10,685,530,530)),paste_fit(canvas,d/'voxel_three_quarter.png',(545,685,530,530))]
 x,y=1100,700
 labels=['TECHNICAL APPROXIMATION','', 'Same 25mm voxel grid.', 'Cloth outer/lining materials corrected.', 'Head/hair source unchanged.', '', '75mm cloth shell is a coarse-grid', 'display thickness, not measured fabric.', '', 'Remaining: coarse face and hair,', 'simplified large garment forms,', 'step shading and small hem conflicts.', '', 'Original wind pose differs from', 'the AI neutral-pose redesign.', '', 'Likeness/art approval: pending.', 'GPU visual review: pending.', 'Rig/socket validation: not done.']
 for line in labels:draw.text((x,y),line,font=small,fill='#222222');y+=25
 out=CLOSE/(aid+'_reference_to_final_r07c.jpg');canvas.save(out,quality=88,optimize=True)
 record={'asset':aid,'output':str(out.relative_to(OUT)),'output_sha256':sha(out),'source_inputs':inputs,'layout_code_sha256':sha(Path(__file__)),'operation':'Unaltered input images composed and resized only; same 25mm CPU geometry rasterizer before/after','limits':['AI front neutral-pose redesign; side/back inference','Appearance not approved','GPU visual review pending','Rig/socket validation not done','Cloth 75mm coarse-grid display thickness'],'render_records_sha256':sha(d/'voxel_render_provenance.json'),'render_gzip_sha256':sha(d/'character.render.json.gz'),'master_gzip_sha256':sha(d/'master.json.gz')};(CLOSE/(aid+'_comparison_provenance.json')).write_text(json.dumps(record,indent=2)+'\n');return record
if __name__=='__main__':
 for aid,name in [('violet','1000041593.webp'),('cyan','1000041592.webp')]:print(json.dumps(make(aid,name)))
