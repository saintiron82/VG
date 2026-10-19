"""CPU z-buffer of actual generated full source, plus native-pixel projection.
No image correction, beauty rendering, texture planes, or output cleanup.
"""
from pipeline import *
from verify_and_render import raster,CPU_SOURCE
import review_surface as view
view.C=C;view.HEIGHT=C['alignment']['character_height_m_for_test']

def render_input(q,parts):
 mats={}
 for part in parts:
  colors=np.unique(q[f'c{part["index"]}'],axis=0)
  for rgb in colors:
   key='rgb_'+'_'.join(map(str,rgb));mats[key]={'color':'#'+''.join(f'{int(c):02x}' for c in rgb)}
 def groups():
  for part in parts:
   i=part['index'];v,f,col=q[f'v{i}'],q[f'f{i}'],q[f'c{i}']
   for start in range(0,len(f),2000):
    fs=f[start:start+2000];colors=col[start:start+2000];tri=v[fs];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);valid=np.linalg.norm(norm,axis=1)>1e-15;tri=tri[valid];colors=colors[valid];palette,labels=np.unique(colors,axis=0,return_inverse=True)
    for k,rgb in enumerate(palette):
     quads=[[t[0].tolist(),t[1].tolist(),t[2].tolist(),t[2].tolist()] for t in tri[labels==k]]
     yield {'material':'rgb_'+'_'.join(map(str,rgb)),'quads':quads}
 return {'materials':mats,'groups':groups()}

def topology(v,f):
 edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);u,count=np.unique(edges,axis=0,return_counts=True);tri=v[f];return {'boundary_edges':int((count==1).sum()),'nonmanifold_edges':int((count>2).sum()),'degenerate_triangles':int((np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)<=1e-15).sum()),'no_deletion_or_repair':True}

def run():
 start=time.monotonic();m,a,source=load();q=np.load(BASE/'generated/full_source.npz');b=read(BASE/'evidence/build.json');r=render_input(q,b['parts']);allv=np.concatenate([q[f'v{p["index"]}'] for p in b['parts']]);center=(allv.min(0)+allv.max(0))/2;span=float(max(allv.max(0)-allv.min(0))*1.12);sheet=Image.new('RGB',(1536,450),'white');d=ImageDraw.Draw(sheet);d.text((10,10),'FULL02 actual measured source | closed lofts + regularized hair envelope + unchanged costume07 | unapproved',fill='black')
 for j,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side90',90,0),('back',180,0)]):
  im=raster(render_input(q,b['parts']),math.radians(yaw),math.radians(tilt),center,span,size=384);im.save(BASE/'generated'/('source_'+name+'.png'));sheet.paste(im,(j*384,40));d.text((j*384+10,425),name,fill='black')
 sheet.save(BASE/'generated/full_source_four_views.jpg',quality=87);print('FOUR_VIEWS_READY',flush=True)
 sheets=[];metrics={};hairpart=next(p for p in b['parts'] if p['id']=='hair_envelope');hr=render_input(q,[hairpart])
 for name,vw in C['views'].items():
  pred=view.project_exact(render_input(q,b['parts']),vw);hp=view.project_exact(render_input(q,[hairpart]),vw);target=a[name+'_foreground']&~a[name+'_guide'];hair=a[name+'_hair_eligible'];occluded=a[name+'_face_skin']|a[name+'_body_exposed_skin']|a[name+'_bodice_gloves'];metrics[name]={'full_target_pixels':int(target.sum()),'model_pixels':int(pred.sum()),'full_target_coverage':float((pred&target).sum()/target.sum()),'full_IoU':float((pred&target).sum()/(pred|target).sum()),'outside_figure_pixels':int((pred&~target).sum()),'missing_figure_pixels':int((target&~pred).sum()),'hair_visible_target_coverage':float((hp&hair).sum()/hair.sum()),'hair_projection_in_nonhair_nonoccluder_pixels':int((hp&~hair&~occluded).sum()),'hair_side_same_material_identity':'unknown','back':'held-out view; not destructive exact silhouette constraint' if name=='back' else 'nominal alignment; side yaw75 with60..90 uncertainty'}
  x0,y0,x1,y1=vw['crop'];rgb=source[y0:y1,x0:x1].astype(float);good=pred&target;extra=pred&~target;miss=target&~pred;rgb[good]=rgb[good]*.5+[20,105,40];rgb[extra]=rgb[extra]*.35+[159,25,15];rgb[miss]=rgb[miss]*.45+[20,45,140];im=Image.fromarray(np.clip(rgb,0,255).astype('uint8'));im.thumbnail((500,624));sheets.append((name,im))
 out=Image.new('RGB',(1536,690),'white');d=ImageDraw.Draw(out);d.text((10,10),'Actual native-pixel projection | green agreement / blue missing / red outside | internal occlusion not silhouette truth',fill='black')
 for j,(name,im) in enumerate(sheets):out.paste(im,(j*512,40));d.text((j*512+10,665),name,fill='black')
 out.save(BASE/'generated/full_source_projection_overlay.jpg',quality=87)
 ts={p['id']:topology(q[f'v{p["index"]}'],q[f'f{p["index"]}']) for p in b['parts']};report={'source_sha256':sha(BASE/'generated/full_source.npz'),'approved_source_sha256':A['source_sha256'],'CPU_renderer_sha256':sha(CPU_SOURCE),'reviewer_sha256':sha(__file__),'camera':{'center_m':center.tolist(),'span_m':span},'native_projection':metrics,'surface_topology':ts,'common_compile':False,'GPU_rig_socket_approved':False,'art_approved':False,'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence/source_review.json',report);print(json.dumps(report));disk()
if __name__=='__main__':
 import threading
 def guard():
  while True:
   rss=int(Path('/proc/self/status').read_text().split('VmRSS:')[1].split()[0])/1024
   if rss>485:
    write(BASE/'evidence/review_memory_guard.json',{'rss_mib':rss,'stopped':True});os._exit(77)
   time.sleep(.05)
 threading.Thread(target=guard,daemon=True).start();run()

