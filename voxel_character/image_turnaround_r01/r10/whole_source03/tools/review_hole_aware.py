from hole_aware_atlas import *
import review_surface as view
view.A=previous.A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def mats():
 x0,y0,x1,y1=previous.A['color']['front_white_roi'];rgb=np.median(SOURCE[y0:y1,x0:x1].reshape(-1,3),0).round().astype(int);return {'outer':{'color':'#'+''.join(f'{v:02x}' for v in rgb)}}

def estimates(v,f,ch,pitch):
 result={};h=A['depth']['normal_thickness_m']/2
 for i in sorted(set(ch.tolist())):
  t=v[f[ch==i]];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);n/=np.linalg.norm(n,axis=1)[:,None];lo=np.minimum((t+h*n[:,None,:]).min(1),(t-h*n[:,None,:]).min(1));hi=np.maximum((t+h*n[:,None,:]).max(1),(t-h*n[:,None,:]).max(1));count=np.prod(np.maximum(np.ceil(hi/pitch-1e-9)-np.floor(lo/pitch+1e-9),0),axis=1).sum();result[str(i)]=int(count)
 return result

def run():
 t=time.monotonic();m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v=s['vertices'];f=s['triangles'];ch=s['charts'];r=view.source_render(v,f,mats());stats,preds=view.metrics(r,a);rf=view.source_render(v,f[ch!=11],mats());frontpred=view.project_exact(rf,F);front_exact=bool(np.array_equal(frontpred,a['front_support']));im,cam=view.view_sheet(r,'HOLE-AWARE03 | exact visible front charts + separate inferred rear depth | costume-only, attachments uncertain');im.resize((1152,330)).save(BASE/'generated/costume_source_four_views.jpg',quality=78)
 view.overlays(a,preds,'Assembled source; back chart may lie behind unmodeled foreground body/cloth').resize((1152,390)).save(BASE/'generated/costume_source_overlay.jpg',quality=76)
 # Two input ownership classes are explicitly visible, not concealed by a score.
 im=Image.fromarray(SOURCE.copy());rgb=np.array(im).astype(float);crop=F['crop'];cut=rgb[crop[1]:crop[3],crop[0]:crop[2]];res=a['owned_10'];cut[res]=.45*cut[res]+[120,30,0];unknown=a['front_occluded_unknown'];cut[unknown]=.4*cut[unknown]+[120,80,0];cut[a['front_support']&~res&~unknown]=.6*cut[a['front_support']&~res&~unknown]+[0,80,10];im=Image.fromarray(np.clip(rgb,0,255).astype(np.uint8));im.crop((64,275,655,624)).resize((591,349)).save(BASE/'generated/front_ownership_overlay.jpg',quality=76)
 report={'status':'SOURCE ACTUAL FOUR VIEWS; first visual review pending','metrics_assembled_with_inferred_rear':stats,'front_measured_charts_only_pixel_exact':front_exact,'front_measured_only_missing_pixels':int((a['front_support']&~frontpred).sum()),'front_measured_only_outside_support_pixels':int((frontpred&~a['front_support']).sum()),'rear_chart_front_projection_under_noncloth_foreground_pixels':int((preds['front']&~a['front_support']&a['front_foreground']).sum()),'front_unknown_body_occlusion_not_silently_removed_from_metrics':True,'candidate_estimates_by_chart':{str(p):estimates(v,f,ch,p) for p in [.025,.0125]},'source_geometry_sha256':sha(BASE/'generated/continuous_costume.npz'),'generator_sha256':sha(Path(__file__).with_name('hole_aware_atlas.py')),'review_script_sha256':sha(__file__),'CPU_renderer_sha256':sha(CPU_SOURCE),'projection_evaluator_sha256':sha(view.__file__),'camera':cam,'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'body_head_hair_changed':False,'common_compile':False};write(BASE/'evidence/source_review.json',report);print(json.dumps(report))
if __name__=='__main__':run()
