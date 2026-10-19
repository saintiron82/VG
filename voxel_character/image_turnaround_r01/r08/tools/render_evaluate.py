"""Actual common-mesh CPU views and source-frame projection errors.
No generated beauty image, fitted image warp or texture plane is used.
"""
import math,json,sys,numpy as np
from pathlib import Path
from PIL import Image,ImageDraw
from measured_cloth import ROOT,sha,read,write,gzread,budget

def raster(r,yaw,pitch,center,span,size=480):
 camera=np.array([math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch)]);right=np.cross([0,1,0],camera);right/=np.linalg.norm(right);up=np.cross(camera,right);basis=np.stack([right,up,camera],1);scale=size/span
 rgb=np.full((size,size,3),245,np.uint8);zbuf=np.full((size,size),-np.inf);light=np.array([-.4,.7,.6]);light/=np.linalg.norm(light)
 for group in r['groups']:
  hx=r['materials'][group['material']]['color'];color=np.array([int(hx[i:i+2],16) for i in (1,3,5)])
  for quad in group['quads']:
   q=np.array(quad);n=np.cross(q[1]-q[0],q[2]-q[0]);n/=np.linalg.norm(n)
   if n@camera<=0:continue
   shaded=np.clip(color*(.55+.45*max(0,n@light)),0,255).astype(np.uint8);p=(q-center)@basis;p[:,0]=size/2+p[:,0]*scale;p[:,1]=size/2-p[:,1]*scale
   for tri in ((0,1,2),(0,2,3)):
    t=p[list(tri)];lo=np.maximum(np.floor(t[:,:2].min(0)).astype(int),0);hi=np.minimum(np.ceil(t[:,:2].max(0)).astype(int)+1,size)
    if np.any(hi<=lo):continue
    x,y=np.meshgrid(np.arange(lo[0],hi[0])+.5,np.arange(lo[1],hi[1])+.5);a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-10:continue
    wa=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;wb=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;wc=1-wa-wb;z=wa*a[2]+wb*b[2]+wc*c[2];zz=zbuf[lo[1]:hi[1],lo[0]:hi[0]];valid=(wa>=-1e-7)&(wb>=-1e-7)&(wc>=-1e-7)&(z>zz);zz[valid]=z[valid];rgb[lo[1]:hi[1],lo[0]:hi[0]][valid]=shaded
 return Image.fromarray(rgb)

def projection_mask(render,view,scale):
 x0,y0,x1,y1=view['crop'];im=Image.new('1',(x1-x0,y1-y0));d=ImageDraw.Draw(im);name=view['name'];axis=view['axis_u']-x0
 for group in render['groups']:
  for quad in group['quads']:
   points=[]
   for x,y,z in quad:
    u=axis+(x if name=='front' else -x if name=='back' else -z)/scale;v=view['floor_y']-y/scale;points.append((u,v))
   d.polygon(points,fill=1)
 return np.array(im,dtype=bool)

def run(tag="region",measured="measured"):
 out=ROOT/"generated"/tag;r=gzread(out/"region.render.json.gz");measurement_path=ROOT/"generated"/measured/"measurements.json";m=read(measurement_path);c=read(m['contract_path']);s=c['alignment']['metres_per_pixel'];source=Image.open(m['source']['sheet_path']).convert('RGB');maskfile=np.load(m['mask_path']);metrics={};panels=[];views=[]
 for name,view in m['views'].items():
  v={**view,'name':name};pred=projection_mask(r,v,s);ref=maskfile[name];x0,y0,x1,y1=view['crop'];h,w=ref.shape;yy,xx=np.indices((h,w));world_y=(view['floor_y']-yy)*s;band=(world_y>=c['region']['world_y_min'])&(world_y<=c['region']['world_y_max']);target=np.zeros_like(ref)
  for py in np.where(band[:,0])[0]:
   xs=np.where(ref[py])[0]
   if len(xs)==0:continue
   axis=view['axis_u']-x0
   if name=='front':limit=(xs.min()+axis)/2;target[py]=ref[py]&(np.arange(w)<=limit)
   elif name=='back':limit=(xs.max()+axis)/2;target[py]=ref[py]&(np.arange(w)>=limit)
   else:target[py]=ref[py]
  overlap=pred&target;union=pred|target;inside=pred&ref;fp=pred&~target;fn=target&~pred
  errors=[]
  for section in m['sections']:
   py=section['samples'][name]['row_y'];xs=np.where(pred[py])[0]+x0
   if len(xs)==0:continue
   observed=section['samples'][name]['pixel_span']
   if name=='front':errors.append(abs(xs.min()-observed[0]))
   elif name=='back':errors.append(abs(xs.max()-observed[1]))
  metrics[name]={'projected_pixels':int(pred.sum()),'target_pixels':int(target.sum()),'intersection_pixels':int(overlap.sum()),'diagnostic_region_IoU':float(overlap.sum()/union.sum()),'projected_pixels_inside_observed_clothing_ratio':float(inside.sum()/pred.sum()),'outside_selected_target_pixels':int(fp.sum()),'missed_target_pixels':int(fn.sum()),'boundary_mean_abs_error_px':float(np.mean(errors)) if errors else None,'boundary_max_abs_error_px':int(max(errors)) if errors else None,'target_status':('front/back selected outer half of thresholded clothing; annotation-based test ROI, not sewing panel ground truth' if name!='side' else 'complete skirt envelope in selected band; this panel cannot be semantically isolated from side image, so IoU is diagnostic only')}
  arr=np.array(source.crop(view['crop'])).astype(float);arr[overlap]=arr[overlap]*.45+np.array([40,210,80])*.55;arr[fp]=arr[fp]*.35+np.array([245,45,30])*.65;arr[fn]=arr[fn]*.45+np.array([40,105,240])*.55
  img=Image.fromarray(arr.astype(np.uint8));draw=ImageDraw.Draw(img);draw.text((8,510),name+' | green match / red model extra / blue target missed',fill='black')
  ymin=int(view['floor_y']-c['region']['world_y_max']/s)-25;ymax=int(view['floor_y']-c['region']['world_y_min']/s)+25;crop=img.crop((0,ymin,w,ymax));crop.thumbnail((510,280));panels.append((name,crop));img.save(out/f'{name}_projection_overlay.png')
 for name,yaw,pitch in [('front',0,0),('three_quarter',-45,12),('side',-90,0),('back',180,0)]:
  im=raster(r,math.radians(yaw),math.radians(pitch),np.array([-.45,.43,-.18]),1.15);dr=ImageDraw.Draw(im);dr.rectangle((0,0,480,29),fill='white');dr.text((10,8),name+' | actual common voxel surface, CPU',fill='black');im.save(out/f'cpu_{name}.png');views.append({'view':name,'yaw_degrees':yaw,'pitch_degrees':pitch,'center_m':[-.45,.43,-.18],'span_m':1.15,'output_sha256':sha(out/f'cpu_{name}.png')})
 sheet=Image.new('RGB',(1600,1220),'white');d=ImageDraw.Draw(sheet);d.text((25,15),'r08 MEASURED CLOTH REGION | pipeline proof, not a finished character',fill='black');d.text((25,40),'Source AI three views -> masks/47 sections -> curved sector prior -> common voxel -> actual overlays',fill='black')
 for i,(name,im) in enumerate(panels):sheet.paste(im,(20+i*525,80));d.text((20+i*525,375),name+' | IoU %.3f | source-mask coverage %.3f'%(metrics[name]['diagnostic_region_IoU'],metrics[name]['projected_pixels_inside_observed_clothing_ratio']),fill='black')
 for i,name in enumerate(['front','three_quarter','side','back']):
  im=Image.open(out/f'cpu_{name}.png');im.thumbnail((390,390));sheet.paste(im,(20+i*395,430))
 lines=['Measured: thresholded cloth pixels, automatic ground landmark and per-row outer boundaries.',
        'Annotated priors: view crops/axes, scale, 60 degree sector, elliptical sections, %.0f mm display thickness.'%(c['region']['thickness_m']*1000),
        'Front/back folds disagree; side depth is the whole skirt envelope and does not identify this left panel.',
        ('First 25 mm shell: 12 components. 50 mm thickness-only test: '+str(read(ROOT/'evidence/thickness_prior_test.json')['new_50mm_topology']['six_connected_components'])+' components. Likeness/cloth reconstruction NOT APPROVED.'),
        '416 changed input pixels -> only 4 measured sections and 5 adjacent surface strips change; see exact per-build cell deltas.',
        'Other rows and other-view measurements stay exact. Missing measurement rejects generation.',
        'Original and r07 are preserved. No face/hair revision was created. CPU evidence only; GPU/rig not tested.']
 for i,t in enumerate(lines):d.text((25,860+i*34),t,fill='black')
 sheet.save(out/'measurement_pipeline_comparison.jpg',quality=88)
 write(out/'projection_metrics.json',{'source_sha256':m['source']['sheet_sha256'],'measurements_sha256':sha(measurement_path),'render_sha256':sha(out/'region.render.json.gz'),'evaluator_sha256':sha(__file__),'views':metrics,'front_back_measured_boundary_conflict_m_mean':float(np.mean([v['front_back_boundary_conflict_m'] for v in m['sections']])),'front_back_measured_boundary_conflict_m_max':float(max(v['front_back_boundary_conflict_m'] for v in m['sections'])),'interpretation':'Errors diagnose an intentionally limited ellipse-family sector; no claim of panel reconstruction or art pass.'})
 write(out/'cpu_render_provenance.json',{'renderer':'deterministic CPU triangle z-buffer over unchanged common mesh quads; not Godot screenshot','renderer_sha256':sha(__file__),'render_input_sha256':sha(out/'region.render.json.gz'),'views':views,'comparison_sha256':sha(out/'measurement_pipeline_comparison.jpg')});print(json.dumps(metrics));budget()
if __name__=='__main__':run(*sys.argv[1:])
