from physical_depth import *
import review_hole_aware as shared
import review_surface as view
view.A=previous.A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def normal_stats(v,f,ch):
 out=[]
 for i in sorted(set(ch.tolist())):
  ff=f[ch==i];p=v[ff];norm=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);nz=norm[:,2].copy();norm/=np.linalg.norm(norm,axis=1)[:,None];edges={}
  for j,tri in enumerate(ff):
   for x,y in zip(tri,np.roll(tri,-1)):edges.setdefault(tuple(sorted([int(x),int(y)])),[]).append(j)
  ang=[];slope=[]
  for (x,y),ids in edges.items():
   slope.append(abs(v[x,2]-v[y,2])/np.linalg.norm(v[x,:2]-v[y,:2]))
   if len(ids)==2:ang.append(math.degrees(math.acos(np.clip(norm[ids[0]]@norm[ids[1]],-1,1))))
  out.append({'chart':i,'winding_sign_counts':[int((nz>0).sum()),int((nz<0).sum())],'normal_angle_p50_p95_max_deg':np.percentile(ang,[50,95,100]).tolist() if ang else [],'edge_depth_slope_p50_p95_max':np.percentile(slope,[50,95,100]).tolist(),'adjacent_normal_over45deg_edges':int((np.array(ang)>45).sum())})
 return out

def run():
 t=time.monotonic();m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v,f,ch=s['vertices'],s['triangles'],s['charts'];new=normal_stats(v,f,ch);old=np.load(ROOT/'whole_source03/generated/continuous_costume.npz');before=normal_stats(old['vertices'],old['triangles'],old['charts']);write(BASE/'evidence/normal_comparison.json',{'before_source03_sha256':sha(ROOT/'whole_source03/generated/continuous_costume.npz'),'after_source04_sha256':sha(BASE/'generated/continuous_costume.npz'),'before':before,'after':new,'note':'Same source pixel topology, front XY, resolution and representation thickness. Only explicitly measured side-inner candidate and depth interpolation/physical curvature/order model changed.'})
 r=view.source_render(v,f,shared.mats());im,cam=view.view_sheet(r,'PHYSICAL CURVATURE04 | same measured pixel domains | explicit rear order, 25mm shell limits unresolved');im.resize((1152,330)).save(BASE/'generated/costume_source_four_views.jpg',quality=80)
 stats,preds=view.metrics(r,a);view.overlays(a,preds,'Actual source; body/bouquet occlusion separate from cloth depth ordering').resize((1152,390)).save(BASE/'generated/costume_source_overlay.jpg',quality=78)
 zf=depth_image(v,f[ch!=11]);zb=depth_image(v,f[ch==11]);over=np.isfinite(zf)&np.isfinite(zb);delta=np.zeros_like(zf);delta[over]=zb[over]-zf[over];front_only=np.isfinite(zf)
 report={'status':'SOURCE CANDIDATE; actual visual inspection and shell intersection gate pending','metrics_assembled':stats,'front_owned_pixel_exact':bool(np.array_equal(front_only,a['front_support'])),'rear_front_overlap_pixels':int(over.sum()),'rear_ahead_over1mm_pixels':int((over&(delta>.001)).sum()),'min_front_rear_gap_m':float((-delta[over]).min()),'side_inner_candidate_pixels':m['side_inner_candidate_pixels'],'candidate_estimates_by_chart':{str(p):shared.estimates(v,f,ch,p) for p in [.025,.0125]},'camera':cam,'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'renderer_sha256':sha(CPU_SOURCE),'evaluator_sha256':sha(view.__file__),'review_script_sha256':sha(__file__),'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'common_compile':False,'GPU_rig_sockets':False};write(BASE/'evidence/source_review.json',report);print(json.dumps(report))
if __name__=='__main__':run()
