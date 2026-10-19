"""Generic pixel classification under explicit, separately stored semantics."""
from measured_panels import *
def classify(rgb,rule):
 a=rgb.astype(float);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2];values={'r':r,'g':g,'b':b,'mean':a.mean(2),'chroma':a.max(2)-a.min(2),'r_minus_g':r-g,'r_minus_b':r-b,'b_minus_r':b-r,'b_minus_g':b-g,'g_minus_b':g-b};mask=np.ones(a.shape[:2],bool)
 for key,v in rule.items():
  base,op=key.rsplit('_',1)
  if base not in values or op not in ('min','max'):raise ValueError('Unknown color rule '+key)
  mask&=(values[base]>=v) if op=='min' else (values[base]<=v)
 return mask

def measure_semantics(contract_path,annotation_path,out):
 c=read(contract_path);ann=read(annotation_path);sp=REPO/c['source'];assert sha(sp)==ann['source_sha256']==c['source_sha256'];source=np.array(Image.open(sp).convert('RGB'));base,arrays=extract(contract_path);out=Path(out);out.mkdir(parents=True,exist_ok=False);result={'source_sha256':sha(sp),'source_path':str(sp),'contract_sha256':sha(contract_path),'annotation_sha256':sha(annotation_path),'extractor_sha256':sha(__file__),'manual_automatic_boundary':ann['annotation_status'],'views':{},'landmarks':[]};allmasks={};images=[]
 for name,v in c['views'].items():
  x0,y0,x1,y1=v['crop'];rgb=source[y0:y1,x0:x1];fg=arrays[name+'_foreground'];counts=np.zeros(fg.shape,np.uint8);uncertain=np.zeros(fg.shape,bool);overlay=rgb.astype(float);vr={}
  def boxmask(boxes):
   m=np.zeros(fg.shape,bool)
   for xa,ya,xb,yb in boxes:m[max(0,ya-y0):min(y1-y0,yb-y0),max(0,xa-x0):min(x1-x0,xb-x0)]=True
   return m
  for cl in ann['classes']:
   roi=boxmask(cl['boxes'].get(name,[]));excluded=boxmask(cl.get('exclude_boxes',{}).get(name,[]));mask=fg&roi&~excluded&classify(rgb,cl['color']);counts+=mask;uncertain|=fg&excluded;allmasks[name+'_'+cl['id']]=mask;cc,n=ndi.label(mask);rows=[{'y_px':int(y+y0),'intervals_px':[[a+x0,b+x0] for a,b in runs(mask[y])]} for y in np.where(mask.any(1))[0]];pix=rgb[mask];vr[cl['id']]={'pixels':int(mask.sum()),'four_connected_components':int(n),'apparent_rgb_median':np.median(pix,0).tolist() if len(pix) else None,'measured_row_intervals':rows,'geometry_limit':cl['geometry_limit']};overlay[mask]=rgb[mask]*.4+np.array(cl['display_rgb'])*.6
  unknown=fg&(counts==0);ambiguous=counts>1;allmasks[name+'_unassigned']=unknown;allmasks[name+'_ambiguous']=ambiguous;allmasks[name+'_semantic_occlusion_envelopes']=uncertain;overlay[unknown]=rgb[unknown]*.6+[90,55,0];overlay[ambiguous]=rgb[ambiguous]*.3+[165,20,20];result['views'][name]={'crop':v['crop'],'classes':vr,'foreground_pixels':int(fg.sum()),'unassigned_pixels':int(unknown.sum()),'ambiguous_pixels':int(ambiguous.sum()),'semantic_occlusion_envelope_pixels':int(uncertain.sum()),'notes':'Multiple components can be genuine visible fragments; this step does not delete any. Excluded semantic boxes are uncertainty envelopes, not final geometry cuts.'};im=Image.fromarray(np.clip(overlay,0,255).astype('uint8'));im.save(out/f'{name}_semantic_overlay.png');im.thumbnail((500,624));images.append((name,im))
 for lm in ann['landmark_searches']:
  xa,ya,xb,yb=lm['box'];rgb=source[ya:yb,xa:xb];mask=classify(rgb,lm['color']);ys,xs=np.where(mask);result['landmarks'].append({'id':lm['id'],'view':lm['view'],'manual_search_box':lm['box'],'color_rule':lm['color'],'matching_pixels':len(xs),'centroid_xy_px':[float(xs.mean()+xa),float(ys.mean()+ya)] if len(xs) else None,'bbox_xyxy_px':[int(xs.min()+xa),int(ys.min()+ya),int(xs.max()+xa+1),int(ys.max()+ya+1)] if len(xs) else None,'status':'computed color-pixel centroid under manually annotated semantic search; not fully automatic anatomical landmark'})
 np.savez_compressed(out/'semantic_masks.npz',**allmasks);result['masks_sha256']=sha(out/'semantic_masks.npz');gzwrite(out/'full_measurements.json.gz',result);sheet=Image.new('RGB',(1536,710),'white');d=ImageDraw.Draw(sheet);d.text((15,12),ann['asset_id']+' / actual pixel classes under explicit semantic annotations',fill='black');d.text((15,35),'Amber: unassigned. Red: overlapping classes. Hidden anatomy and panel correspondence remain unknown.',fill='black')
 for i,(name,im) in enumerate(images):sheet.paste(im,(10+i*510,65));d.text((15+i*510,680),name+' / no geometry generated',fill='black')
 sheet.save(out/'full_semantic_measurement_review.jpg',quality=89);write(out/'summary.json',{'source_sha256':result['source_sha256'],'measurement_sha256':sha(out/'full_measurements.json.gz'),'annotation_sha256':result['annotation_sha256'],'views':{k:{a:b for a,b in v.items() if a!='classes'} for k,v in result['views'].items()},'landmarks':result['landmarks'],'comparison_sha256':sha(out/'full_semantic_measurement_review.jpg'),'geometry_generated':False});print(json.dumps({'views':{k:{cl:v0['pixels'] for cl,v0 in v['classes'].items()} for k,v in result['views'].items()},'landmarks':result['landmarks'],'disk_bytes':budget()}));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--annotations',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();measure_semantics(a.contract,a.annotations,a.output)
