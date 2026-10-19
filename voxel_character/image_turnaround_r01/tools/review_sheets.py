"""Comparison layouts only; source images and rendered artifacts remain unmodified."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make():
 for aid,orig,crop in [('violet','1000041593.webp',(0,0,660,837)),('cyan','1000041592.webp',(0,0,705,813))]:
  d=ROOT/'generated'/(aid+'_curved06b');source=ROOT.parent/'image_characters_r01/reference'/orig;sheet=ROOT.parent/'reference_turnarounds_r01'/(aid+'_turnaround.png');items=[(source,None,'Original illustration'),(sheet,crop,'AI front redesign / inferred other views'),(d/'continuous_three_quarter.png',None,'Curved master / CPU pre-voxel'),(d/'voxel_three_quarter.png',None,'Actual common voxel / CPU')];canvas=Image.new('RGB',(1440,560),'white');draw=ImageDraw.Draw(canvas);files=[]
  for i,(p,box,label) in enumerate(items):
   im=Image.open(p).convert('RGB');im=im.crop(box) if box else im;im.thumbnail((354,510));canvas.paste(im,(i*360+(360-im.width)//2,32));draw.text((i*360+8,8),label,fill='black');files.append({'path':str(p.relative_to(ROOT.parent)),'sha256':sha(p),'crop':box})
  draw.text((8,542),'Coarse 3D approximation. AI side/back are design hypotheses. Appearance unapproved. GPU review pending.',fill='black');out=d/'source_to_curved_voxel_comparison.jpg';canvas.save(out,quality=83,optimize=True)
  views=Image.new('RGB',(1000,1035),'white')
  for i,name in enumerate(['front','three_quarter','side','rear']):
   im=Image.open(d/('voxel_'+name+'.png'));im.thumbnail((500,500));views.paste(im,((i%2)*500,(i//2)*500));files.append({'path':str((d/('voxel_'+name+'.png')).relative_to(ROOT)),'sha256':sha(d/('voxel_'+name+'.png'))})
  ImageDraw.Draw(views).text((8,1014),'Actual common-compiled quads; deterministic CPU rasterizer. No Godot GPU visual approval.',fill='black');views.save(d/'actual_voxel_four_views.jpg',quality=82,optimize=True)
  (d/'review_sheet_provenance.json').write_text(json.dumps({'script_sha256':sha(Path(__file__)),'inputs':files,'outputs':[{'path':p.name,'sha256':sha(p)} for p in [out,d/'actual_voxel_four_views.jpg']],'operation':'layout/resize only; no geometry/image appearance correction'},indent=2)+'\n')
if __name__=='__main__':make()
