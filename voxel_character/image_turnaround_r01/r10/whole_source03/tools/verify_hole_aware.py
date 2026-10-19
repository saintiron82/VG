"""Exact replay/locality plus explicit rear-depth order and pixel topology checks."""
from hole_aware_atlas import *
from review_hole_aware import mats
import review_surface as view
view.C=C;view.F=F;view.A=previous.A;view.SOURCE=SOURCE

def depth_image(v,f):
 x0,y0,x1,y1=F['crop'];zbuf=np.full((y1-y0,x1-x0),-np.inf)
 for tri in f:
  p=v[tri];t=np.c_[F['axis_u']+p[:,0]/SCALE-x0,F['sole_y']-p[:,1]/SCALE-y0];lo=np.maximum(np.floor(t.min(0)).astype(int),0);hi=np.minimum(np.ceil(t.max(0)).astype(int),[x1-x0,y1-y0])
  if np.any(hi<=lo):continue
  xx,yy=np.meshgrid(np.arange(lo[0],hi[0])+.5,np.arange(lo[1],hi[1])+.5);aa,bb,cc=t;den=(bb[1]-cc[1])*(aa[0]-cc[0])+(cc[0]-bb[0])*(aa[1]-cc[1])
  if abs(den)<1e-13:continue
  wa=((bb[1]-cc[1])*(xx-cc[0])+(cc[0]-bb[0])*(yy-cc[1]))/den;wb=((cc[1]-aa[1])*(xx-cc[0])+(aa[0]-cc[0])*(yy-cc[1]))/den;wc=1-wa-wb;inside=(wa>=-1e-9)&(wb>=-1e-9)&(wc>=-1e-9);z=wa*p[0,2]+wb*p[1,2]+wc*p[2,2];cut=zbuf[lo[1]:hi[1],lo[0]:hi[0]];cut[inside]=np.maximum(cut[inside],z[inside])
 return zbuf

def chart_digest(v,f,ch,i):
 t=v[f[ch==i]];return rawsha(np.round(t,10))

def run():
 t=time.monotonic();m,a=load();saved=np.load(BASE/'generated/continuous_costume.npz');v,f,ch,pp,rep,seam=build(m,a,SOURCE);same={'all_source_arrays_exact':all(np.array_equal(x,saved[k]) for x,k in [(v,'vertices'),(f,'triangles'),(ch,'charts'),(pp,'primary_pixels')])};mm,aa=extract(SOURCE);same['independent_measurement_arrays_exact']=all(np.array_equal(a[k],aa[k]) for k in a);same['measured_curves_exact']=m['previous_measured_curves']['charts']==mm['previous_measured_curves']['charts'];del mm,aa
 # Finite faces retain the exact native primary pixel union; no mask-island repair.
 coverage=[]
 for i in range(12):
  view0=C['views']['back'] if i==11 else F;pred=view.project_exact(view.source_render(v,f[ch==i],mats()),view0);target=a[f'owned_{i}'];p=v[f[ch==i]];area=np.cross(p[:,1,:2]-p[:,0,:2],p[:,2,:2]-p[:,0,:2]);coverage.append({'chart':i,'primary_pixel_exact':bool(np.array_equal(pred,target)),'missing_pixels':int((target&~pred).sum()),'outside_pixels':int((pred&~target).sum()),'projected_area_sign_counts':[int((area<0).sum()),int((area>0).sum()),int((abs(area)<1e-14).sum())],'xy_foldovers':bool((area>1e-14).any() and (area<-1e-14).any()),'input_components_4_connected':int(ndi.label(target)[1])})
 front=depth_image(v,f[ch!=11]);rear=depth_image(v,f[ch==11]);overlap=np.isfinite(front)&np.isfinite(rear);diff=np.zeros_like(front);diff[overlap]=rear[overlap]-front[overlap];ahead=overlap&(diff>1e-6);behind=overlap&(diff<-1e-6);touch=overlap&(abs(diff)<=1e-6);crossx=overlap[:,:-1]&overlap[:,1:]&(diff[:,:-1]*diff[:,1:]<0);crossy=overlap[:-1]&overlap[1:]&(diff[:-1]*diff[1:]<0);coords=np.argwhere(ahead);depth={'overlap_pixel_centers':int(overlap.sum()),'rear_in_front_of_observed_front_cloth_pixels':int(ahead.sum()),'rear_behind_pixels':int(behind.sum()),'within_1micrometer_pixels':int(touch.sum()),'rear_front_depth_order_sign_change_neighbor_pairs':int(crossx.sum()+crossy.sum()),'maximum_rear_ahead_m':float(diff[ahead].max()) if ahead.any() else 0,'example_ahead_global_xy_px':[[int(x+F['crop'][0]),int(y)] for y,x in coords[::max(1,len(coords)//20)][:20]],'interpretation':'Depth-order failure indicates potential interpenetration between independently inferred rear and front surfaces. Pixel-center sign changes are evidence, not a full triangle collision proof. No offset/fill repair applied.'}
 fixtures=[]
 for name,box in [('train100',[591,582,601,592]),('face25',[315,185,320,190])]:
  src=SOURCE.copy();x0,y0,x1,y1=box;src[y0:y1,x0:x1]=[255,0,0];mm,aa=extract(src);vv,ff,cc,ppp,rr,ss=build(mm,aa,src);direct=[i for i in range(12) if not np.array_equal(a[f'owned_{i}'],aa[f'owned_{i}'])];changed=[i for i in range(12) if chart_digest(v,f,ch,i)!=chart_digest(vv,ff,cc,i)];boundary_changed=[i for i in range(10) if m['previous_measured_curves']['charts'][i]!=mm['previous_measured_curves']['charts'][i]];declared=set(direct)|set(boundary_changed)
  # Residual/rear inference is a recorded dependency of any paired boundary change.
  if boundary_changed:declared.update([10,11])
  if 0 in boundary_changed:declared.update(i for i,q in enumerate(previous.A['charts']) if 'side' not in q['views'])
  fixtures.append({'fixture':name,'actual_changed_pixels':int(np.any(src!=SOURCE,2).sum()),'directly_changed_owned_charts':direct,'boundary_changed_charts':boundary_changed,'declared_dependency_charts':sorted(declared),'actual_changed_chart_geometry':changed,'outside_scope_geometry_change':sorted(set(changed)-declared),'outside_scope_exact':not(set(changed)-declared)});del mm,aa,vv,ff,cc,ppp,rr,ss
 reject={}
 try:build(None,a,SOURCE)
 except ValueError as e:reject['missing_measurement']=str(e)
 src=SOURCE.copy();src[275:624,655:1050]=[255,0,0]
 try:extract(src)
 except ValueError as e:reject['contradictory_side']=str(e)
 out={'status':'SOURCE ONLY; actual multiview/attachment gate required','reproducibility':same,'owned_primary_pixel_projection':coverage,'front_measured_ownership_missing_pixels':m['front_unassigned_pixels'],'front_measured_ownership_duplicate_pixels':m['front_duplicate_owned_pixels'],'actual_pixel_regressions':fixtures,'missing_or_contradictory_input_rejection':reject,'rear_order_diagnostic':depth,'source_dependency_sockets':None,'source_gate_contract':A['source_to_compile_gate'],'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'generator_sha256':sha(Path(__file__).with_name('hole_aware_atlas.py')),'verifier_sha256':sha(__file__),'source_sha256':sha(BASE/'generated/continuous_costume.npz')};write(BASE/'evidence/verification.json',out);print(json.dumps(out))
if __name__=='__main__':run()
