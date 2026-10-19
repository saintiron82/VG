"""Same actual pixel masks/triangulation; physical-space curvature and explicit
rear depth ordering. All assumptions live in JSON. No image or occupancy repair.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'whole_source03/tools'))
import hole_aware_atlas as base
from hole_aware_atlas import *
from verify_hole_aware import depth_image
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;P=BASE/'data/depth_contract.json';A=read(P)

def extract(source):
 bm,a=base.extract(source);keys=list(a);previous.configure();poly,rec=legacy.sampled_edge(source,A['side_inner_candidate'])
 if contour_crossings(poly):raise ValueError('Side inner semantic corridor self-crossing')
 a['side_inner_candidate']=polygon_mask(poly,C['views']['side']['crop'])&a['side_support']
 if not a['side_inner_candidate'].any():raise ValueError('Missing actual side inner-cloth candidate support')
 m={'schema':'riverstone.physical_curvature_measured.v1','actual_pixel_sha256':rawsha(source),'source_file_sha256':bm['source_file_sha256'],'source_status':bm['source_status'],'base_measurement':bm,'base_array_keys':keys,'side_inner_candidate_boundary':rec,'side_inner_candidate_pixels':int(a['side_inner_candidate'].sum()),'dependencies':bm['dependencies']+[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in [P,Path(__file__)]],'arrays_digest':digest({k:rawsha(v) for k,v in a.items()})};return m,a

def validate(m,a,source):
 if not m or m.get('schema')!='riverstone.physical_curvature_measured.v1':raise ValueError('Independent physical-curvature measured input required')
 if m['actual_pixel_sha256']!=rawsha(source):raise ValueError('Wrong source pixels')
 if digest({k:rawsha(v) for k,v in a.items()})!=m['arrays_digest']:raise ValueError('Changed measured arrays')
 for dep in m['dependencies']:
  if sha(REPO/dep['path'])!=dep['sha256']:raise ValueError('Changed dependency '+dep['path'])

def segment_depth(query,fp,rv):
 p=fp;q=np.roll(fp,-1,axis=0);d=q-p;norm=(d*d).sum(1);delta=query[:,None,:]-p[None,:,:];t=np.clip(np.einsum('nkd,kd->nk',delta,d)/norm[None,:],0,1);closest=p[None,:,:]+t[:,:,None]*d[None,:,:];dist2=((query[:,None,:]-closest)**2).sum(2);idx=dist2.argmin(1);tt=t[np.arange(len(query)),idx];z=(1-tt)*rv[idx,2]+tt*np.roll(rv,-1,axis=0)[idx,2];return z,np.sqrt(dist2[np.arange(len(query)),idx])

def physical_operator(v,f):
 n=len(v);rows=[];cols=[];values=[];mass=np.zeros(n)
 for tri in f:
  xy=v[tri,:2];area=abs(np.cross(xy[1]-xy[0],xy[2]-xy[0]))/2
  if area<=1e-16:raise ValueError('Degenerate actual primary triangle')
  for i in tri:mass[i]+=area/3
  for k in range(3):
   i,j,h=tri[k],tri[(k+1)%3],tri[(k+2)%3];cot=float(np.dot(v[i,:2]-v[h,:2],v[j,:2]-v[h,:2])/(2*area)/2);rows.extend([i,j,i,j]);cols.extend([i,j,j,i]);values.extend([cot,cot,-cot,-cot])
 L=sparse.csr_matrix((values,(rows,cols)),shape=(n,n));K=(L.T@sparse.diags(1/np.maximum(mass,1e-16))@L).tocsr();scale=float(np.mean(K.diagonal()));K=K/scale+A['depth']['tangent_weight']*L/max(float(np.mean(L.diagonal())),1e-12);return K,{'curvature_normalization':scale,'physical_lumped_area_m2':float(mass.sum())}

def solve(K,prior,ids,targets,weights):
 n=len(prior);w=np.full(n,1e-5);b=1e-5*prior;np.add.at(w,ids,weights);np.add.at(b,ids,weights*targets);H=K+sparse.diags(w);z=spsolve(H.tocsc(),b);return z,{'linear_residual_max':float(abs(H@z-b).max()),'anchor_error_rms_m':float(np.sqrt(np.mean((z[ids]-targets)**2))) if len(ids) else None,'anchor_error_max_m':float(abs(z[ids]-targets).max()) if len(ids) else None}

def overlap_operator(v,f,zfront):
 x0,y0,x1,y1=F['crop'];rows=[];cols=[];vals=[];targets=[];coords=[]
 for tri in f:
  p=v[tri];t=np.c_[F['axis_u']+p[:,0]/SCALE-x0,F['sole_y']-p[:,1]/SCALE];lo=np.maximum(np.floor(t.min(0)).astype(int),0);hi=np.minimum(np.ceil(t.max(0)).astype(int),[x1-x0,y1-y0])
  if np.any(hi<=lo):continue
  xx,yy=np.meshgrid(np.arange(lo[0],hi[0])+.5,np.arange(lo[1],hi[1])+.5);aa,bb,cc=t;den=(bb[1]-cc[1])*(aa[0]-cc[0])+(cc[0]-bb[0])*(aa[1]-cc[1]);wa=((bb[1]-cc[1])*(xx-cc[0])+(cc[0]-bb[0])*(yy-cc[1]))/den;wb=((cc[1]-aa[1])*(xx-cc[0])+(aa[0]-cc[0])*(yy-cc[1]))/den;wc=1-wa-wb;zf=zfront[lo[1]:hi[1],lo[0]:hi[0]];inside=(wa>=-1e-9)&(wb>=-1e-9)&(wc>=-1e-9)&np.isfinite(zf)
  for py,px in zip(*np.where(inside)):
   row=len(targets);rows.extend([row]*3);cols.extend(tri.tolist());vals.extend([float(wa[py,px]),float(wb[py,px]),float(wc[py,px])]);targets.append(float(zf[py,px]-A['depth_correction']['rear_separation_m']));coords.append([int(px+lo[0]+x0),int(py+lo[1])])
 return sparse.csr_matrix((vals,(rows,cols)),shape=(len(targets),len(v))),np.array(targets),coords

def build(m,a,source):
 validate(m,a,source);legacy.F=F;curves,paired=base.curve_data(m['base_measurement'],a);items=[];names=[q['id'] for q in previous.A['charts']]+['measured_residual_cloth','rear_center_observed_inferred_seam'];allnamed=np.concatenate([r[0] for r in curves]);allpixels=np.c_[allnamed[:,0]/SCALE+F['axis_u'],F['sole_y']-allnamed[:,1]/SCALE];tree=cKDTree(allpixels)
 for i,name in enumerate(names):
  v,f,pixels,mr=base.triangulate(a[f'owned_{i}'],C['views']['back'] if i==11 else F);edges,bd=base.edges_and_boundary(f);K,physical=physical_operator(v,f)
  if i<10:
   rv,fp,report=curves[i];prior,dist=segment_depth(pixels,fp,rv);targets=prior[bd];weights=np.where(dist[bd]<=A['depth_correction']['minimum_distance_to_matched_curve_px'],10000.,.001)
   if i in A['side_inner_candidate']['front_chart_indices']:
    aa={**a,'side_support':a['side_inner_candidate']};lo,hi,extra=base.side_interval_world(v,aa);prior=(lo+hi)/2;targets=prior[bd];weights=np.full(len(bd),.1);report={'status':'Unpaired inner drape: actual restricted side candidate interval midpoint gauge, curvature prior. No same-point observation.','side_height_extrapolation_px':extra}
  elif i==10:
   dist,idx=tree.query(pixels);prior=allnamed[idx,2];targets=prior[bd];weights=np.full(len(bd),.001);report={'status':'Measured residual visible cloth. Weak nearest boundary gauge; inferred shared native boundary anchors below.'}
  else:
   yy=np.round(paired[:,1],4);uy=np.unique(yy);uz=np.array([np.median(paired[yy==y,2]) for y in uy]);prior=np.interp(v[:,1],uy,uz);targets=prior[bd];weights=np.full(len(bd),.001);report={'status':'Measured rear center. Unobserved depth uses minimum deformation plus explicit nonpenetration ordering; body/bouquet occlusion unknown.'}
  items.append({'i':i,'id':name,'v':v,'f':f,'pixels':pixels,'bd':bd,'K':K,'physical':physical,'prior':prior,'targets':targets.copy(),'weights':weights,'report':report})
 # Shared depth constraints are recomputed from measured adjacency; no gap fill.
 look={}
 for item in items[:11]:
  for k,idx in enumerate(item['bd']):look.setdefault(tuple(np.round(item['pixels'][idx],6)),[]).append((item['i'],k))
 seams=[]
 for (px,py),refs in sorted(look.items()):
  if not any(i==10 for i,k in refs) or not any(i<10 for i,k in refs):continue
  ix,iy=int(px),int(py);patch=source[max(0,iy-1):iy+1,max(0,ix-1):ix+1].astype(float);gradient=float(np.sqrt(np.mean(np.var(patch.reshape(-1,3),axis=0))))
  if gradient>A['inferred_seam']['max_rgb_edge_rms']:continue
  z=float(np.mean([items[i]['targets'][k] for i,k in refs if i<10]))
  for i,k in refs:items[i]['targets'][k]=z;items[i]['weights'][k]=A['depth_correction']['seam_constraint_weight']
  seams.append([float(px),float(py),z,[i for i,k in refs]])
 verts=[];faces=[];charts=[];pixels=[];reports=[];offset=0;frontv=[];frontf=[]
 for item in items:
  i=item['i'];v=item['v'];f=item['f'];K=item['K'];prior=item['prior'];bd=item['bd'];target=item['targets'];weights=item['weights']
  if i<11:
   z,fit=solve(K,prior,bd,target,weights);v[:,2]=z;frontv.extend(v);frontf.extend(f+len(verts))
  else:
   fv=np.array(frontv);ff=np.array(frontf,int);zf=depth_image(fv,ff);S,upper,coord=overlap_operator(v,f,zf);lo,hi,extra=base.side_interval_world(v,a);w=A['depth_correction']['rear_soft_constraint_weight'];gauge=.01;z0=np.clip(prior,lo,hi)
   def fun(z):
    diff=z-prior;r=K@z;pen=np.maximum(S@z-upper,0);return float(z@r+gauge*(diff@diff)+w*(pen@pen)),2*r+2*gauge*diff+2*w*(S.T@pen)
   result=minimize(fun,z0,jac=True,bounds=list(zip(lo,hi)),method='L-BFGS-B',options={'maxiter':A['depth_correction']['max_solver_iterations'],'ftol':1e-13,'gtol':1e-7,'maxcor':8});z=result.x;v[:,2]=z;pen=np.maximum(S@z-upper,0);impossible=np.maximum(S@lo-upper,0);fit={'solver_success':bool(result.success),'message':str(result.message),'iterations':int(result.nit),'ordering_constraint_pixel_samples':len(upper),'violating_separation_over_1mm_samples':int((pen>.001).sum()),'maximum_separation_constraint_violation_m':float(pen.max()) if len(pen) else 0,'side_interval_proves_infeasible_samples':int((impossible>1e-6).sum()),'max_proven_infeasibility_m':float(impossible.max()) if len(impossible) else 0,'side_row_extrapolation_max_px':extra,'actual_positive_rear_ahead_over_1mm_samples':int((pen>A['depth_correction']['rear_separation_m']+.001).sum()),'separation_prior_m':A['depth_correction']['rear_separation_m']}
  verts.extend(v);faces.extend(f+offset);charts.extend([i]*len(f));pixels.extend(item['pixels']);offset+=len(v);reports.append({'chart':i,'id':item['id'],'measurement_or_prior':item['report'],'physical_curvature':item['physical'],'fit':fit,'z_extent_m':[float(z.min()),float(z.max())],'vertices':len(v),'triangles':len(f)})
 return np.array(verts),np.array(faces,int),np.array(charts,int),np.array(pixels),reports,seams

def load():
 m=gzread(BASE/'evidence/measurement.json.gz');a=dict(np.load(BASE/'evidence/measurement.npz'));assert m['arrays_file_sha256']==sha(BASE/'evidence/measurement.npz');validate(m,a,SOURCE);return m,a

def run():
 t=time.monotonic();m,a=extract(SOURCE);np.savez_compressed(BASE/'evidence/measurement.npz',**a);m['arrays_file_sha256']=sha(BASE/'evidence/measurement.npz');gzwrite(BASE/'evidence/measurement.json.gz',m);v,f,ch,pp,rep,seams=build(m,a,SOURCE);np.savez_compressed(BASE/'generated/continuous_costume.npz',vertices=v,triangles=f,charts=ch,primary_pixels=pp);gzwrite(BASE/'evidence/source_fit.json.gz',{'charts':rep,'inferred_seam_vertices':seams});out={'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'triangles':len(f),'side_inner_candidate_pixels':m['side_inner_candidate_pixels'],'rear_fit':rep[-1]['fit'],'bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()),'new_depth_assumptions_in_data_contract':True};write(BASE/'evidence/build.json',out);print(json.dumps(out))
if __name__=='__main__':run()
