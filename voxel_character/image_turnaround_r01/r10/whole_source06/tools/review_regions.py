"""Compare actual source06 four views and per-lining projection to measured input."""
from fit_regions import *
from review_height import fixed_views
from review_physical import normal_stats
from review_hole_aware import mats
import review_surface as view
view.A=previous.A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def run():
    start=time.monotonic();m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v,f,ch=s['vertices'],s['triangles'],s['charts'];r=view.source_render(v,f,mats())
    im,camera=fixed_views(r,'REGION06 | separate measured lining candidates, unknown depth | fixed04 camera; same25mm representation');im.resize((1152,330)).save(BASE/'generated/costume_source_four_views.jpg',quality=82)
    stat,pred=view.metrics(r,a);stat['side']['correspondence_status']='Measured whole costume; lining5/6 separate visible candidates, identity still provisional'
    view.overlays(a,pred,'ACTUAL source06; explicit visibility-specific measurements; body occlusion unknown').resize((1152,390)).save(BASE/'generated/costume_source_overlay.jpg',quality=80)
    primary=[];lining=[]
    for i in range(12):
        cr=view.source_render(v,f[ch==i],mats());p=view.project_exact(cr,C['views']['back'] if i==11 else F);target=a[f'owned_{i}'];primary.append({'chart':i,'exact':bool(np.array_equal(p,target)),'missing':int((target&~p).sum()),'outside':int((p&~target).sum())})
        if i in [5,6]:
            side=view.project_exact(cr,C['views']['side']);q=a[f'lining_{i}_side_candidate'];lining.append({'chart':i,'measured_visible_candidate_pixels':int(q.sum()),'projection_pixels':int(side.sum()),'candidate_coverage':float((side&q).sum()/q.sum()),'projection_outside_candidate_pixels':int((side&~q).sum()),'limit':'Some outside candidate projection may be hidden by other cloth/body; no calibrated same-material-point or body depth proof.'})
    zf=pd.depth_image(v,f[ch!=11]);zb=pd.depth_image(v,f[ch==11]);both=np.isfinite(zf)&np.isfinite(zb);gap=zf[both]-zb[both]
    out={'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'renderer_sha256':sha(CPU_SOURCE),'projection_evaluator_sha256':sha(view.__file__),'script_sha256':sha(__file__),
      'camera_fixed_to04':camera,'projection':stat,'primary_projection':primary,'lining_side_projection':lining,'normals':normal_stats(v,f,ch),
      'rear_overlap_px':int(both.sum()),'minimum_front_rear_mid_surface_gap_m':float(gap.min()),'rear_ahead_over1mm_px':int((gap<-.001).sum()),
      'body_face_hair_complete':False,'art_shape_approved':False,'common_compile':False,'GPU_rig_sockets':False,'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
    write(BASE/'evidence/source_review.json',out);print(json.dumps({k:v for k,v in out.items() if k not in ['normals','primary_projection']}))

if __name__=='__main__':run()
