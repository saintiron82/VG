"""Actual three-view pixel measurements, with explicit human ROI boundaries."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def measure(a):
 p=(ROOT/'data'/a['sheet']).resolve();assert sha(p)==a['sheet_sha256'];im=np.asarray(Image.open(p).convert('RGB'));h,w=im.shape[:2];gray=im.mean(2);sat=im.max(2).astype(int)-im.min(2).astype(int)
 scores=((gray<175)&(sat<20)).sum(1);start=h-100;end=h-30;floor=int(start+np.argmax(scores[start:end]))
 # Row-local background estimate uses known outside margins, not model colours.
 bg=np.median(np.concatenate([im[:,:8],im[:,-8:]],axis=1),axis=1);diff=np.linalg.norm(im.astype(float)-bg[:,None,:],axis=2)
 raw=(diff>20)|(sat>17);raw[floor-1:]=False;labels,n=ndi.label(raw);sizes=np.bincount(labels.ravel());raw &= sizes[labels]>=12
 mask=ndi.binary_closing(raw,structure=np.ones((2,2)));holes=ndi.binary_fill_holes(mask)&~mask;labs,n=ndi.label(holes);sizes=np.bincount(labs.ravel());mask|=holes&(sizes[labs]<120)
 out=ROOT/'measurements'/a['id'];out.mkdir(exist_ok=True);overlay=Image.fromarray(im.copy());draw=ImageDraw.Draw(overlay);draw.line((0,floor,w,floor),fill=(230,20,20),width=2);views=[]
 for view in a['views']:
  x0,y0,x1,y1=view['crop'];local=mask[y0:y1,x0:x1];yy,xx=np.where(local);bbox=[int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0+1),int(yy.max()+y0+1)];hx0,hy0,hx1,hy1=view['head_roi'];hy,hx=np.where(mask[hy0:hy1,hx0:hx1]);scalp=int(hy.min()+hy0);scale=a['scalp_to_floor_m']/(floor-scalp)
  rows=[]
  for y in range(max(0,scalp),floor,8):
   xs=np.where(mask[max(0,y-1):min(h,y+2),x0:x1].any(0))[0]
   if len(xs):rows.append({'y_pixel':y,'world_y_m':(floor-y)*scale,'min_u':int(xs.min()+x0),'max_u':int(xs.max()+x0),'width_pixels':int(xs.max()-xs.min()+1)})
  viewrecord={**view,'foreground_bbox':bbox,'foreground_pixels':int(local.sum()),'floor_y_pixel':floor,'floor_status':'long horizontal low-saturation dark-line maximum','scalp_y_pixel':scalp,'scalp_status':'foreground minimum within manually supplied head ROI','meters_per_pixel':scale,'row_silhouette':rows,'alignment_status':'Source-derived floor and scalp scale; human semantic lateral axis; not post-fitted to mesh'};views.append(viewrecord)
  edge=local&~ndi.binary_erosion(local);arr=np.asarray(overlay).copy();ys,xs=np.where(edge);arr[ys+y0,xs+x0]=[255,0,180];overlay=Image.fromarray(arr);draw=ImageDraw.Draw(overlay);draw.line((view['manual_axis_u'],scalp,view['manual_axis_u'],floor),fill=(0,180,70),width=1);draw.rectangle(view['head_roi'],outline=(240,140,0),width=1)
  Image.fromarray(local.astype(np.uint8)*255).save(out/(view['name']+'_silhouette.png'))
 hsv=np.asarray(Image.fromarray(im).convert('HSV')).astype(float)/255;eyes=[]
 for i,(x0,y0,x1,y1) in enumerate(a['eye_rois']):
  q=hsv[y0:y1,x0:x1];selected=(q[:,:,0]>=a['eye_hue_range'][0])&(q[:,:,0]<=a['eye_hue_range'][1])&(q[:,:,1]>.24)&(q[:,:,2]>.45);yy,xx=np.where(selected)
  if len(xx):eyes.append({'id':'visible_eye_'+str(i),'pixel':[float(xx.mean()+x0),float(yy.mean()+y0)],'method':'HSV source pixels within human ROI','count':len(xx)})
 overlay.save(out/'source_measurement_overlay.png');np.savez_compressed(out/'pixels.npz',mask=mask,rgb=im)
 result={'schema':'riverstone.turnaround.measurements.v1','id':a['id'],'sheet_sha256':a['sheet_sha256'],'original_sha256':a['original_sha256'],'prompt_sha256':sha(ROOT.parent/'reference_turnarounds_r01/prompts.json'),'annotation_sha256':sha(ROOT/'data/measurement_annotations.json'),'extractor_sha256':sha(Path(__file__)),'views':views,'visible_eyes':eyes,'status':'AI-generated view silhouettes, not original-observed side/back ground truth','observed_disagreements':a['observed_disagreements'],'mask_uncertainty':'Low-contrast gray hair/cloth versus gray background and small filled holes are ambiguous; no independent ground-truth masks.'}
 (out/'measurements.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'id':a['id'],'floor':floor,'views':[{k:v[k] for k in ['name','scalp_y_pixel','meters_per_pixel','foreground_bbox']} for v in views],'eyes':eyes}))
if __name__=='__main__':
 for a in json.loads((ROOT/'data/measurement_annotations.json').read_text())['assets']:measure(a)
