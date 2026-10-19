"""Actual output pixels/registration, explicit semantic annotations, honest gates."""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json,hashlib,sys
B=Path(__file__).resolve().parents[1];R=B.parents[2];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(rev='r01'):
 annotation=B/f'data/{rev}_measurement_annotations.json';a=json.loads(annotation.read_text());path=B/a['image'];im=Image.open(path).convert('RGB');rgb=np.array(im);h,w=rgb.shape[:2];template=json.loads((B/'data/template_contract.json').read_text());sy=h/template['canvas'][1];sx=w/template['canvas'][0];pairs=[];missing=[]
 for p in template['panels']:
  for x,y in p['markers_centers']:
   tx,ty=x*sx,y*sy;ix,iy=int(round(tx)),int(round(ty));x0=max(0,ix-5);y0=max(0,iy-5);cut=rgb[y0:iy+6,x0:ix+6];white=np.all(cut>=225,axis=2);yy,xx=np.where(white)
   if len(xx):pairs.append(([x,y,1],[float(xx.mean()+x0),float(yy.mean()+y0)]))
   else:missing.append([x,y])
 matrix=None;error=None
 if len(pairs)>=3:
  original=np.array([p[0]for p in pairs]);actual=np.array([p[1]for p in pairs]);matrix=np.linalg.lstsq(original,actual,rcond=None)[0];err=np.linalg.norm(original@matrix-actual,axis=1);error={'rms_px':float(np.sqrt(np.mean(err**2))),'max_px':float(err.max())}
 ratios={}
 for name,lm in a['landmarks'].items():
  c,k,s=lm['visible_hair_crown_y'],lm['chin_y'],lm['sole_y'];u=lm['uncertainty_px'];ratio=(s-c)/(k-c);ratios[name]={'crown_chin_sole_px':[c,k,s],'ratio':ratio,'manual_uncertainty_px':u,'conservative_ratio_range':[(s-c-2*u)/(k-c+2*u),(s-c+2*u)/(k-c-2*u)],'within3_plusminus0_12':abs(ratio-3)<=.12}
 ref=np.array(Image.open(R/template['approved_source_path']).convert('RGB'));refboxes={'face':[375,211,384,219],'upper_arm':[429,277,437,287],'thigh':[408,423,416,432]};skins={}
 def stats(arr,box):
  x,y,x1,y1=box;p=arr[y:y1,x:x1].reshape(-1,3);return {'box_xyxy':box,'count':len(p),'median_rgb':np.median(p,0).tolist(),'min_rgb':p.min(0).tolist(),'max_rgb':p.max(0).tolist(),'p10_rgb':np.percentile(p,10,axis=0).tolist(),'p90_rgb':np.percentile(p,90,axis=0).tolist()}
 for name,box in a['skin_roi_xyxy'].items():
  new=stats(rgb,box);old=stats(ref,refboxes[name]);skins[name]={'approved':old,'new':new,'median_delta_rgb':(np.array(new['median_rgb'])-old['median_rgb']).tolist(),'uncertainty':'Observed apparent illustration color, unmatched lighting/patch context, not albedo or a perceptual metric'}
 # Fixed empty inter-panel strip, outside all character rectangles/labels/markers.
 margin=rgb[int(110*sy):int(610*sy),int(670*sx):int(695*sx)].reshape(-1,3);colors,counts=np.unique(margin,axis=0,return_counts=True);dom=colors[counts.argmax()];green=(rgb[:,:,0]<=40)&(rgb[:,:,2]<=40)&(rgb[:,:,1]>=90);uncertain=(rgb[:,:,1].astype(int)-rgb[:,:,0]>80)&(rgb[:,:,1].astype(int)-rgb[:,:,2]>80)&~green
 out={'schema':'riverstone.chroma_image_validation.v1','status':'FAIL_REFERENCE_CORRECTION_REQUIRED','image_sha256':sha(path),'approved_source_sha256':template['source_sha256'],'template_sha256':template['template_sha256'],'annotation_sha256':sha(annotation),'validator_sha256':sha(Path(__file__)),'actual_size':[w,h],'requested_size':template['canvas'],'registration':{'detected_marker_count':len(pairs),'missing':missing,'template_to_actual_affine':matrix.tolist()if matrix is not None else None,'residual':error,'global_scale_is_not_exact_output_coordinate_compliance':True},'ratios':ratios,'skin_samples':skins,'background':{'guard_strip_dominant_rgb':dom.tolist(),'dominant_fraction':float(counts.max()/len(margin)),'green_family_pixels':int(green.sum()),'green_spill_or_key_collision_uncertain_pixels':int(uncertain.sum()),'note':'Grid and key share saturated green family. Plant leaves/edge blends require ownership review; do not erase full grid lines through objects.'},'manual_visual_review':a['visual_review'],'actual_six_orthographic_3D_render_gate':False,'top_bottom_reference_status':'design_section_only; original references missing, current generated view angles also fail','ready_for_measurement_voxel':False}
 out['background'].update({'guard_strip_p01_rgb':np.percentile(margin,1,axis=0).tolist(),'guard_strip_p99_rgb':np.percentile(margin,99,axis=0).tolist(),'exact_0_255_0_fraction':float(np.all(margin==[0,255,0],axis=1).mean()),'exact_flat_background_pass':bool(np.all(margin==[0,255,0])),'not_chroma_corrected':True})
 canvas=im.copy();d=ImageDraw.Draw(canvas)
 for name,lm in a['landmarks'].items():
  p=next(v for v in template['panels']if v['id']==name);x0,y0,x1,y1=p['box'];left=int(x0*sx);right=int(x1*sx)
  for y in [lm['visible_hair_crown_y'],lm['chin_y'],lm['sole_y']]:d.line((left,y,right,y),fill=(255,0,0),width=1)
  d.text((left+4,int(y0*sy)+3),f'Measured {ratios[name]["ratio"]:.3f} heads: FAIL',fill=(255,0,0))
 for n,box in a['skin_roi_xyxy'].items():d.rectangle(box,outline=(255,255,0),width=1)
 canvas.save(B/f'evidence/validation_overlay_{rev}.jpg',quality=86);(B/f'evidence/image_validation_{rev}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'registration':out['registration'],'ratios':ratios,'skin_delta':{k:v['median_delta_rgb']for k,v in skins.items()},'background':out['background']}))
if __name__=='__main__':run(sys.argv[1]if len(sys.argv)>1 else'r01')
