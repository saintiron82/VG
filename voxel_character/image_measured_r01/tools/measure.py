"""Measured pixels first. Human semantic ROIs never define the outside contour."""
from pathlib import Path
import hashlib,json,colorsys
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def roi(shape,box):
 m=np.zeros(shape,bool);x0,y0,x1,y1=box;m[y0:y1,x0:x1]=True;return m

def measure(a):
 base_colors=json.loads((ROOT/'data/annotations.json').read_text())['palette_base_colors'];source=(ROOT/'data'/a['source']).resolve();assert sha(source)==a['expected_sha256'];rgb=np.asarray(Image.open(source).convert('RGB'));h,w=rgb.shape[:2];color=rgb.astype(float)/255
 hsv=np.asarray(Image.fromarray(rgb).convert('HSV')).astype(float)/255;hue,sat,val=np.moveaxis(hsv,-1,0)
 # Anti-aliased near-white pixels are ambiguous. The 12-level rule is fixed before voxel fitting.
 raw=(255-rgb.min(axis=2).astype(int))>12
 labels,n=ndi.label(raw);sizes=np.bincount(labels.ravel());raw &= sizes[labels]>=5
 enclosed=ndi.binary_fill_holes(raw)&~raw;holes,n=ndi.label(enclosed);fill=np.zeros_like(raw);decisions=[]
 for i,sl in enumerate(ndi.find_objects(holes),1):
  if sl is None:continue
  y0=max(0,sl[0].start-1);y1=min(h,sl[0].stop+1);x0=max(0,sl[1].start-1);x1=min(w,sl[1].stop+1)
  local=holes[y0:y1,x0:x1]==i;yy,xx=np.where(local);yy=yy+y0;xx=xx+x0
  ring=ndi.binary_dilation(local)&raw[y0:y1,x0:x1];brightness=rgb[y0:y1,x0:x1][ring].mean(axis=1) if ring.any() else np.array([0]);cy=float(yy.mean())
  accepted=(cy>a['hair_fill_exclusion_y'] and np.quantile(brightness,.75)>205) or (len(xx)<35 and cy>a['cloth_start_y'])
  roi_fill=False
  for name in ['head_roi','flower_roi']:
   bx0,by0,bx1,by1=a[name];ratio=np.mean((xx>=bx0)&(xx<bx1)&(yy>=by0)&(yy<by1))
   if ratio>.92 and len(xx)<1600:roi_fill=True
  accepted=accepted or roi_fill
  if accepted:fill[yy,xx]=True
  if len(xx)>=10:decisions.append({'pixels':len(xx),'bbox':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'filled_as_white_surface':bool(accepted),'manual_roi_assisted':roi_fill,'boundary_brightness_q75':float(np.quantile(brightness,.75))})
 mask=raw|fill
 # Semantic labels are depth priors, not silhouette. Actual material colors remain sampled RGB.
 sem=np.full((h,w),0,np.uint8);sem[mask]=1 # cloth/default
 hair=(np.indices((h,w))[0]<a['cloth_start_y'])&mask;sem[hair]=2
 img=Image.new('L',(w,h));ImageDraw.Draw(img).polygon([tuple(p) for p in a['body_clothing_polygon']],fill=1);sem[np.asarray(img).astype(bool)&mask]=8
 for region in a['human_semantic_regions']:
  img=Image.new('L',(w,h));ImageDraw.Draw(img).polygon([tuple(p) for p in region['polygon']],fill=1);inside=np.asarray(img).astype(bool)
  skin_color=((hue<.12)|(hue>.94))&(sat>.025)&(val>.28)
  sem[inside&mask&skin_color]=3
 head=roi((h,w),a['head_roi']);skinface=head&mask&(((hue<.09)|(hue>.94))&(sat>.08))
 sem[skinface]=4
 halo=roi((h,w),a['halo_roi'])&mask&~head;sem[halo]=5
 flower=roi((h,w),a['flower_roi'])&mask;sem[flower]=6
 # Colored airborne ribbons use source saturation/hue, with explicit semantic hue ranges.
 if a['id']=='violet':ribbon=(hue>.75)&(hue<.93)&(sat>.22)&(val>.52)&(np.indices((h,w))[0]>415)
 else:ribbon=(hue>.45)&(hue<.57)&(sat>.30)&(np.indices((h,w))[0]>325)
 sem[ribbon&mask]=7
 # Signature ROI is excluded from all color/landmark metrics; infer its underlying cloth material only.
 excluded=roi((h,w),a['signature_roi'])&mask
 material_rgb=rgb.copy();valid=mask&~excluded
 _,nearest=ndi.distance_transform_edt(~valid,return_indices=True);material_rgb[excluded]=rgb[nearest[0][excluded],nearest[1][excluded]]
 sample=material_rgb[mask];small=Image.fromarray(sample.reshape((-1,1,3))).quantize(colors=base_colors,method=Image.Quantize.MEDIANCUT);palette=np.array(small.getpalette(),dtype=np.uint8).reshape((-1,3))[:base_colors]
 # Palette nearest RGB labels are measured, not preset colors.
 ids=np.zeros((h,w),np.uint8)
 for y in range(0,h,64):
  diff=material_rgb[y:y+64,:,None,:].astype(np.int16)-palette[None,None,:,:].astype(np.int16);ids[y:y+64]=np.argmin(np.sum(diff.astype(np.int32)**2,axis=3),axis=2)
 eye=[]
 for i,box in enumerate(a['eye_rois']):
  candidates=roi((h,w),box)&(hue>=a['eye_hue_range'][0])&(hue<=a['eye_hue_range'][1])&(sat>.24)&(val>.42)
  yy,xx=np.where(candidates);assert len(xx)>0,'Eye color detection empty'
  palette=np.vstack([palette,np.median(rgb[candidates],axis=0).astype(np.uint8)]);ids[candidates]=len(palette)-1
  eye.append({'id':'visible_eye_'+str(i),'pixel':[float(xx.mean()),float(yy.mean())],'method':'source HSV threshold inside manually supplied eye ROI','sample_count':int(len(xx))})
 yy,xx=np.where(mask);bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
 landmarks=[{'id':k,'pixel':v,'method':'manual semantic landmark, not automatically measured','uncertainty_pixels':6} for k,v in a['manual_landmarks'].items()]+eye
 area=[]
 for k,p in enumerate(palette):
  selected=mask&(ids==k)&~excluded;yy,xx=np.where(selected)
  area.append({'id':int(k),'rgb':p.tolist(),'pixel_count':int(selected.sum()),'centroid_pixel':[float(xx.mean()),float(yy.mean())] if len(xx) else None})
 d=ROOT/'measurements'/a['id'];d.mkdir(exist_ok=True)
 Image.fromarray(mask.astype(np.uint8)*255).save(d/'silhouette.png');Image.fromarray(sem).save(d/'semantic_labels.png');Image.fromarray(ids).save(d/'color_labels.png');Image.fromarray(excluded.astype(np.uint8)*255).save(d/'excluded_signature.png')
 np.savez_compressed(d/'pixels.npz',mask=mask,semantic=sem,colors=ids,excluded=excluded,palette=palette)
 contour=mask&~ndi.binary_erosion(mask);overlay=rgb.copy();overlay[contour]=[255,0,180];out=Image.fromarray(overlay);draw=ImageDraw.Draw(out)
 for lm in landmarks:
  x,y=lm['pixel'];col=(0,150,0) if lm['method'].startswith('source') else (255,90,0);draw.line((x-6,y,x+6,y),fill=col,width=2);draw.line((x,y-6,x,y+6),fill=col,width=2)
 out.save(d/'source_measurement_overlay.png')
 labelcolors=np.array([[255,255,255],[200,210,235],[100,80,140],[220,150,135],[255,185,150],[0,200,220],[230,220,100],[220,70,200],[120,190,175]],np.uint8);Image.fromarray(labelcolors[sem]).save(d/'semantic_preview.png')
 measured={'schema':'riverstone.image_measurements.v1','id':a['id'],'source_file':str(source.relative_to(ROOT.parent)),'source_sha256':sha(source),'source_pixels':[w,h],'extraction_code_sha256':sha(Path(__file__)),'annotation_sha256':sha(ROOT/'data/annotations.json'),'palette_base_colors':base_colors,'automatic':{'foreground_pixels':int(mask.sum()),'nonwhite_pixels':int(raw.sum()),'inferred_white_fill_pixels':int(fill.sum()),'foreground_bbox':bounds,'palette':area,'white_hole_decisions':decisions},'landmarks':landmarks,'semantic_labels':{'0':'background','1':'cloth','2':'hair','3':'skin_body','4':'skin_face','5':'halo','6':'bouquet','7':'ribbon','8':'body_clothing'},'manual_boundary':'Semantic ROIs and joint labels are human annotations; white-hole classification is a declared heuristic. No hand-traced outer silhouette.','uncertainty':'White-on-white boundaries, signature coverage and semantic masks require human review. These are extracted targets, not independently annotated ground truth.','files':{p.name:sha(p) for p in d.iterdir() if p.is_file() and p.name!='measurements.json'}}
 dump(d/'measurements.json',measured);print(json.dumps({'id':a['id'],'bbox':bounds,'foreground_pixels':int(mask.sum()),'filled_white_pixels':int(fill.sum()),'automatic_eyes':eye},ensure_ascii=False))
if __name__=='__main__':
 for asset in json.loads((ROOT/'data/annotations.json').read_text())['assets']:measure(asset)
