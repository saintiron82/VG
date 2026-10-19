"""Project actual common-compiled cubes into each fixed source-sheet camera."""
from pathlib import Path
import argparse,gzip,hashlib,json,math
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(tag):
 budget=read(ROOT/'data/output_budget.json')['approved_MiB']*1024**2;used=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
 if used+2500000>budget:raise RuntimeError('Projection overlays paused pending expanded disk budget')
 aid=tag.split('_')[0];a=next(x for x in read(ROOT/'data/measurement_annotations.json')['assets'] if x['id']==aid);p=read(ROOT/'data'/(aid+'_preset.json'));d=ROOT/'generated'/tag;c=json.loads(gzip.decompress((d/'compiled.cells.json.gz').read_bytes()));source=np.asarray(Image.open((ROOT/'data'/a['sheet']).resolve()).convert('RGB'));mask=np.load(ROOT/'measurements'/aid/'pixels.npz')['mask'];pitch=c['pitch'];scale=1.82/(p['front_floor_y']-p['front_scalp_y']);reports=[];panels=[]
 for view in a['views']:
  x0,y0,x1,y1=view['crop'];h,w=y1-y0,x1-x0;axis=view['manual_axis_u'];frame=np.full((h,w,3),245,np.uint8);zb=np.full((h,w),-np.inf);pred=np.zeros((h,w),bool)
  for row in c['cells']:
   xyz=np.array(row[:3])*pitch
   if view['name']=='front':horizontal=[xyz[0],xyz[0]+pitch];depth=xyz[2]+pitch
   elif view['name']=='right':horizontal=[-xyz[2]-pitch,-xyz[2]];depth=xyz[0]+pitch
   else:horizontal=[-xyz[0]-pitch,-xyz[0]];depth=-xyz[2]
   left=max(0,math.ceil(axis+horizontal[0]/scale-x0-.5));right=min(w,math.ceil(axis+horizontal[1]/scale-x0-.5));top=max(0,math.ceil(p['front_floor_y']-(xyz[1]+pitch)/scale-y0-.5));bottom=min(h,math.ceil(p['front_floor_y']-xyz[1]/scale-y0-.5))
   if right<=left or bottom<=top:continue
   update=depth>zb[top:bottom,left:right];hx=c['materials'][row[5]]['color'];color=[int(hx[i:i+2],16) for i in [1,3,5]];zb[top:bottom,left:right][update]=depth;frame[top:bottom,left:right][update]=color;pred[top:bottom,left:right][update]=True
  target=mask[y0:y1,x0:x1];inter=(target&pred).sum();union=(target|pred).sum();te=target&~ndi.binary_erosion(target);pe=pred&~ndi.binary_erosion(pred);chamfer=(ndi.distance_transform_edt(~te)[pe].mean()+ndi.distance_transform_edt(~pe)[te].mean())/2
  overlay=(source[y0:y1,x0:x1]*.5+frame*.5).astype(np.uint8);overlay[te]=[255,0,160];overlay[pe]=[0,180,255];Image.fromarray(frame).save(d/('projected_'+view['name']+'.png'));Image.fromarray(overlay).save(d/('overlay_'+view['name']+'.png'))
  panel=Image.fromarray(overlay);panel.thumbnail((480,650));canvas=Image.new('RGB',(490,685),'white');canvas.paste(panel,((490-panel.width)//2,30));ImageDraw.Draw(canvas).text((10,8),view['name']+' | source / actual compiled voxel contour',fill='black');panels.append(canvas)
  reports.append({'view':view['name'],'silhouette_iou':float(inter/union),'boundary_chamfer_pixels':float(chamfer),'fixed_axis_pixel':axis,'fixed_floor_pixel':p['front_floor_y'],'meters_per_pixel':scale,'source_view_status':'AI generated design inference; source front is also a neutral-pose redesign','camera_fit_to_render':False})
 sheet=Image.new('RGB',(490*3,710),'white')
 for i,panel in enumerate(panels):sheet.paste(panel,(i*490,0))
 ImageDraw.Draw(sheet).text((10,690),'Magenta = extracted AI sheet contour. Cyan = compiled volume contour. This is not original hidden-view ground truth.',fill='black');sheet.save(d/'three_view_constraint_overlay.png')
 result={'views':reports,'compiled_payload_hash':c['payload_hash'],'source_sheet_sha256':a['sheet_sha256'],'projection_code_sha256':sha(Path(__file__)),'quality_boundary':'These are alignment diagnostics, not a pass threshold for likeness, topology or inferred depth accuracy.'};(d/'three_view_projection_metrics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('tag');run(a.parse_args().tag)
