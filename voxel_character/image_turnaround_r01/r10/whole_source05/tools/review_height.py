"""Actual CPU source and native pixel projection; fixed04 comparison camera."""
from height_correspondence import *
from review_physical import normal_stats
from review_hole_aware import mats
from PIL import ImageDraw
import review_surface as view
view.A=previous.A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def fixed_views(r,label):
    camera=read(ROOT/'whole_source04/evidence/source_review.json')['camera'];center=np.array(camera['center_m']);span=camera['span_m']
    im=Image.new('RGB',(1536,440),'white');d=ImageDraw.Draw(im);d.text((10,8),label,fill='black')
    for i,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side90',90,0),('back',180,0)]):
        tile=view.raster(r,math.radians(yaw),math.radians(tilt),center,span,size=370);im.paste(tile,(384*i,35));d.text((384*i+10,411),name,fill='black')
    return im,camera

def run():
    start=time.monotonic();m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v,f,ch=s['vertices'],s['triangles'],s['charts'];r=view.source_render(v,f,mats())
    im,camera=fixed_views(r,'HEIGHT MATCH05 | observed edge intervals + explicit unknown depth prior | fixed04 camera; no added thickness');im.resize((1152,330)).save(BASE/'generated/costume_source_four_views.jpg',quality=82)
    stat,pred=view.metrics(r,a)
    stat['side']['correspondence_status']='whole costume candidate; only55 major drape front observations have height-consistent conditional side candidates'
    view.overlays(a,pred,'ACTUAL source05; measured masks fixed, conditional intervals and unknown depths').resize((1152,390)).save(BASE/'generated/costume_source_overlay.jpg',quality=80)
    primary=[]
    for i in range(12):
        p=view.project_exact(view.source_render(v,f[ch==i],mats()),C['views']['back'] if i==11 else F);target=a[f'owned_{i}'];primary.append({'chart':i,'exact':bool(np.array_equal(p,target)),'missing':int((target&~p).sum()),'outside':int((p&~target).sum())})
    zf=pd.depth_image(v,f[ch!=11]);zb=pd.depth_image(v,f[ch==11]);both=np.isfinite(zf)&np.isfinite(zb);gap=zf[both]-zb[both]
    out={'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'actual_CPU_renderer_sha256':sha(CPU_SOURCE),'projection_evaluator_sha256':sha(view.__file__),
      'camera_fixed_to_source04':camera,'projection':stat,'primary_projection':primary,'normals':normal_stats(v,f,ch),
      'rear_front_overlap_px':int(both.sum()),'minimum_front_rear_mid_surface_gap_m':float(gap.min()),'rear_ahead_over1mm_px':int((gap<-.001).sum()),
      'solver_reports':'evidence/source_fit.json; iteration limits remain failures, not hidden',
      'common_compile':False,'art_or_complete_character_approved':False,'hidden_body_attachment':None,'GPU_rig_sockets':False,
      'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'script_sha256':sha(__file__)}
    write(BASE/'evidence/source_review.json',out);print(json.dumps({k:v for k,v in out.items() if k not in ['normals','primary_projection']}))

if __name__=='__main__':run()
