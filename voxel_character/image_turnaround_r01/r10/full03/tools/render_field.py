"""Actual implicit-source CPU ray intersection + original mesh z-buffer.
Same approved source; no generated beauty image, smoothing image or texture plane.
"""
from field_source import *
import inspect
from verify_and_render import raster,CPU_SOURCE
import review as prior_review
# The existing renderer arithmetic is untouched; expose its existing z-buffer
# for depth-correct composition with a real3D implicit source surface.
code=inspect.getsource(raster).replace('def raster(', 'def mesh_raster(').replace('return Image.fromarray(rgb)','return Image.fromarray(rgb),zbuf')
exec(code,globals())

def rays(field,axes,base,camera,source,masks):
 flat=base.reshape(-1,3);lo=np.array([a[0]for a in axes]);hi=np.array([a[-1]for a in axes]);step=float(axes[0][1]-axes[0][0]);inv=np.where(abs(camera)>1e-10,1/np.where(abs(camera)>1e-10,camera,1),1e20);aa=(lo-flat)*inv;bb=(hi-flat)*inv;tnear=np.minimum(aa,bb).max(1);tfar=np.maximum(aa,bb).min(1);possible=tfar>=tnear;depth=np.full(len(flat),-np.inf);points=np.zeros((len(flat),3));normals=np.zeros((len(flat),3));outcolor=np.zeros((len(flat),3),np.uint8);grads=np.gradient(field.astype(np.float32),step);caststep=step/2
 def sample(p,arr=field):return ndi.map_coordinates(arr,((p-lo)/step).T,order=1,mode='constant',cval=-1)
 active=np.flatnonzero(possible);t=tfar[active]+caststep;prev=np.full(len(active),-1.);prev_t=t.copy();maxsteps=int(math.ceil(np.max(tfar[possible]-tnear[possible])/caststep))+3 if possible.any() else 0
 for k in range(maxsteps):
  if not len(active):break
  t-=caststep;p=flat[active]+t[:,None]*camera;value=sample(p);hit=(value>0)&(prev<=0);ii=active[hit]
  if len(ii):
   fraction=-prev[hit]/np.maximum(value[hit]-prev[hit],1e-12);root=prev_t[hit]+fraction*(t[hit]-prev_t[hit]);depth[ii]=root;points[ii]=flat[ii]+root[:,None]*camera
  keep=~hit&(t>=tnear[active]-caststep);active=active[keep];prev=value[keep];prev_t=t[keep];t=t[keep]
 good=np.where(np.isfinite(depth))[0]
 if len(good):
  n=-np.stack([sample(points[good],g)for g in grads],1);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12);normals[good]=n;names=list(C['views']);cameras=np.array([[math.sin(math.radians(C['views'][name]['yaw_degrees'])),0,math.cos(math.radians(C['views'][name]['yaw_degrees']))]for name in names]);ids=(n@cameras.T).argmax(1)
  for j,name in enumerate(names):
   ii=good[ids==j];p=points[ii];vw=C['views'][name];theta=math.radians(vw['yaw_degrees']);x=np.floor(vw['axis_u']+(math.cos(theta)*p[:,0]-math.sin(theta)*p[:,2])/SCALE).astype(int);y=np.floor(vw['sole_y']-p[:,1]/SCALE).astype(int);x=np.clip(x,vw['crop'][0],vw['crop'][2]-1);y=np.clip(y,vw['crop'][1],vw['crop'][3]-1);rgb=source[y,x].copy();eligible=masks[name+'_hair_eligible'][y-vw['crop'][1],x-vw['crop'][0]];rgb[~eligible]=[76,47,77];outcolor[ii]=rgb
 return depth.reshape(base.shape[:2]),outcolor.reshape((*base.shape[:2],3)),normals.reshape((*base.shape[:2],3)),{'step_m':caststep,'rays':len(flat),'hits':len(good),'maximum_steps':maxsteps}

def run(head_trial=False,coupled=False):
 head_trial=head_trial or coupled
 prefix='coupled_' if coupled else 'head_trial_' if head_trial else 'source_'
 t=time.monotonic();m,a,src,q,build=inputs();
 if head_trial:
  delta=np.load(BASE/'generated/head_interval_trial.npz');original=q
  class Overlay:
   def __getitem__(self,k):return delta[k] if k in delta.files else original[k]
  q=Overlay()
 own=np.load(BASE/'evidence/ownership_masks.npz');a={**a,**{name+'_hair_eligible':own[name+'_hair_confident'] for name in ['front','side']}};field_path=BASE/'generated'/('coupled_head_field.npz' if coupled else 'hair_field.npz');fq=np.load(field_path);field=fq['field'].astype(np.float32);axes=[fq[k]for k in ['x','y','z']];parts=[p for p in build['parts']if p['id']!='hair_envelope'];oldcam=read(ROOT/'full02/evidence/build.json');allv=np.concatenate([q[f'v{p["index"]}']for p in parts]);lo=np.minimum(allv.min(0),[v[0]for v in axes]);hi=np.maximum(allv.max(0),[v[-1]for v in axes]);center=(lo+hi)/2;span=float(max(hi-lo)*1.08);size=384;sheet=Image.new('RGB',(1536,450),'white');draw=ImageDraw.Draw(sheet);draw.text((10,10),'FULL03 actual3D source | observed color / inferred opaque-depth separated | unchanged body/costume | NOT ART APPROVED',fill='black');reports=[]
 for j,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side90',90,0),('back',180,0)]):
  ya,ti=math.radians(yaw),math.radians(tilt);r=prior_review.render_input(q,parts);im,zbuf=mesh_raster(r,ya,ti,center,span,size=size);rgb=np.array(im);camera=np.array([math.sin(ya)*math.cos(ti),math.sin(ti),math.cos(ya)*math.cos(ti)]);right=np.cross([0,1,0],camera);right/=np.linalg.norm(right);up=np.cross(camera,right);light=np.array([-.4,.7,.6]);light/=np.linalg.norm(light);viewstats=[]
  for row in range(0,size,48):
   xx,yy=np.meshgrid(np.arange(size)+.5,np.arange(row,min(row+48,size))+.5);base=center+(xx-size/2)[:,:,None]*(span/size)*right+(size/2-yy)[:,:,None]*(span/size)*up;dep,col,norm,stat=rays(field,axes,base,camera,src,a);shade=.55+.45*np.maximum(0,norm@light);pixels=np.clip(col*shade[:,:,None],0,255).astype('uint8');valid=dep>zbuf[row:row+len(dep)];rgb[row:row+len(dep)][valid]=pixels[valid];viewstats.append(stat)
  im=Image.fromarray(rgb);
  stored_view=(not coupled) or name in ['front','three_quarter']
  if stored_view:im.save(BASE/'generated'/(prefix+name+'.png'))
  sheet.paste(im,(j*384,40));draw.text((j*384+10,425),name,fill='black');reports.append({'view':name,'yaw_deg':yaw,'tilt_deg':tilt,'ray_chunks':viewstats,'sha256':sha(BASE/'generated'/(prefix+name+'.png')) if stored_view else None,'stored_in_four_view_sheet':True,'pixel_rgb_sha256':rawsha(rgb)});print('VIEW_READY',name,flush=True)
 sheet.save(BASE/'generated'/('coupled_source_four_views.jpg' if coupled else 'head_trial_four_views.jpg' if head_trial else 'full_source_four_views.jpg'),quality=87);report={'source_field_sha256':sha(field_path),'body_costume_source_sha256':A['fixed_source_sha256'],'CPU_mesh_renderer_sha256':sha(CPU_SOURCE),'implicit_renderer_sha256':sha(__file__),'mesh_raster_adaptation':'Only returns original z-buffer; source arithmetic unchanged','camera':{'center_m':center.tolist(),'span_m':span},'views':reports,'head_trial_geometry_sha256':sha(BASE/'generated/head_interval_trial.npz') if head_trial else None,'hair_occlusion_uses_original_head_prior':head_trial and not coupled,'selected_head_and_hair_occlusion_dependency_coherent':coupled,'actual_common_compile':False,'no_image_repair':True,'GPU_rig_socket_art_approved':False,'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence'/('coupled_source_render.json' if coupled else 'head_trial_render.json' if head_trial else 'source_render.json'),report);print(json.dumps(report));before.disk()
if __name__=='__main__':threading.Thread(target=guard,daemon=True).start();run('--head-trial' in sys.argv,'--coupled' in sys.argv)
