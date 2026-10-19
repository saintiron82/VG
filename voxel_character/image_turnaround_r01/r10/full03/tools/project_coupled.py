"""Native-pixel projection of actual selected meshes + coupled 3D field.
No image repair. Pixel-center ray/root approximation is explicitly reported.
"""
from render_field import *
from couple_head_field import with_head,validate

def run():
 start=time.monotonic();m,a,src,q,b=inputs();validate(m,a,src);q=with_head(q);fq=np.load(BASE/'generated/coupled_head_field.npz');field=fq['field'].astype(np.float32);axes=[fq[k]for k in ['x','y','z']]
 vertices=[];faces=[];offset=0
 for p in b['parts']:
  if p['id']=='hair_envelope':continue
  i=p['index'];v=q[f'v{i}'];f=q[f'f{i}'];vertices.extend(v);faces.extend(f+offset);offset+=len(v)
 vertices=np.array(vertices);faces=np.array(faces);metrics={};images=[];stored={}
 for name,vw in C['views'].items():
  theta=math.radians(vw['yaw_degrees']);camera=np.array([math.sin(theta),0,math.cos(theta)]);right=np.array([math.cos(theta),0,-math.sin(theta)]);x0,y0,x1,y1=vw['crop'];md=depth(vertices,faces,vw);hd=np.full(md.shape,-np.inf)
  for row in range(0,y1-y0,48):
   xx,yy=np.meshgrid(np.arange(x1-x0)+x0+.5,np.arange(row,min(row+48,y1-y0))+y0+.5)
   base=(xx-vw['axis_u'])[:,:,None]*SCALE*right; base[:,:,1]=(vw['sole_y']-yy)*SCALE
   dep,_,_,_=rays(field,axes,base,camera,src,a);hd[row:row+len(dep)]=dep
  pred=np.isfinite(md)|np.isfinite(hd);hair_visible=np.isfinite(hd)&(hd>=md);target=a[name+'_foreground']&~a[name+'_guide'];hair=a[name+'_hair_eligible'];stored[name+'_projection']=pred;stored[name+'_visible_hair']=hair_visible
  metrics[name]={'full_target_pixels':int(target.sum()),'model_pixels':int(pred.sum()),'full_target_coverage':float((pred&target).sum()/target.sum()),'full_IoU':float((pred&target).sum()/(pred|target).sum()),'outside_figure_pixels':int((pred&~target).sum()),'missing_figure_pixels':int((target&~pred).sum()),'visible_hair_target_coverage':float((hair_visible&hair).sum()/hair.sum()),'visible_hair_in_observed_skin_pixels':int((hair_visible&(a[name+'_face_skin']|a[name+'_body_exposed_skin'])).sum()),'view_limit':'Held out; rear anatomy/hairstyle depth unobserved' if name=='back' else 'Nominal75deg, uncertain60..90deg, unequal pose' if name=='side' else 'Approved front alignment; semantic labels still uncertain'}
  rgb=src[y0:y1,x0:x1].astype(float);good=pred&target;extra=pred&~target;miss=target&~pred;rgb[good]=rgb[good]*.5+[20,105,40];rgb[extra]=rgb[extra]*.35+[159,25,15];rgb[miss]=rgb[miss]*.45+[20,45,140];im=Image.fromarray(np.clip(rgb,0,255).astype('uint8'));im.thumbnail((500,624));images.append((name,im));print('NATIVE_PROJECTION_READY',name,json.dumps(metrics[name]),flush=True)
 out=Image.new('RGB',(1536,690),'white');d=ImageDraw.Draw(out);d.text((10,10),'FULL03 actual source projection: green agreement / blue missing / red outside. NOT ART OR TOPOLOGY APPROVED',fill='black')
 for j,(name,im) in enumerate(images):out.paste(im,(j*512,40));d.text((j*512+10,665),name,fill='black')
 op=BASE/'generated/coupled_projection_overlay.jpg';out.save(op,quality=86);np.savez_compressed(BASE/'evidence/coupled_projection_masks.npz',**stored)
 result={'status':'SOURCE_DIAGNOSTIC_ONLY_NOT_ART_APPROVED','approved_reference_sha256':A['approved_image_sha256'],'field_sha256':sha(BASE/'generated/coupled_head_field.npz'),'head_sha256':sha(BASE/'generated/head_interval_trial.npz'),'body_costume_sha256':A['fixed_source_sha256'],'projection_script_sha256':sha(__file__),'implicit_ray_script_sha256':sha(Path(__file__).with_name('render_field.py')),'native_pixel_centers':True,'ray_step_m':float(axes[0][1]-axes[0][0])/2,'root_method':'First positive signed-field sample crossing, linear root; thin intervals between ray steps can be missed. Not exact continuous silhouette proof.','mesh_projection':'All triangle pixel-center intersections; frontmost depth for semantic hair visibility','metrics':metrics,'overlay_sha256':sha(op),'common_compile':False,'GPU_rig_socket_art_approved':False,'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence/coupled_projection.json',result);print(json.dumps(result))
if __name__=='__main__':threading.Thread(target=guard,daemon=True).start();run()
