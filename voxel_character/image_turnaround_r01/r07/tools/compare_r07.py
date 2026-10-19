from pathlib import Path
import hashlib,json,sys
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'r07'
for a in sys.argv[1:]:
 before=ROOT/'generated'/(a+'_curved06b');after=OUT/'generated'/(a+'_r07c');canvas=Image.new('RGB',(1200,1235),'white');draw=ImageDraw.Draw(canvas);inputs=[]
 for row,view in enumerate(['front','three_quarter']):
  for col,(folder,label) in enumerate([(before,'BEFORE: thin overlapping material bands'),(after,'AFTER: multilayer shell / 3D material field')]):
   p=folder/('voxel_'+view+'.png');im=Image.open(p);im.thumbnail((600,600));canvas.paste(im,(col*600,row*600));draw.rectangle((col*600,row*600,col*600+600,row*600+24),fill='white');draw.text((col*600+8,row*600+6),label+' | '+view,fill='black');inputs.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 draw.text((8,1214),'Same 25mm grid and renderer. Head/hair source unchanged. Actual common voxel materials, no image retouch.',fill='black');output=after/'cloth_regression_comparison.jpg';canvas.save(output,quality=86,optimize=True);(after/'comparison_provenance.json').write_text(json.dumps({'inputs':inputs,'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'layout_only':True},indent=2)+'\n')
