"""Measured image-bound charts -> shared fold surface -> adaptive common grammar.
Search corridors/correspondence and curvature are explicitly annotated priors.
The source image is measured, never pasted on a plane or used as a texture.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'continuous05c/tools'))
import measured_surface as legacy
legacy.BASE=BASE;legacy.P=BASE/'data/surface_atlas.json';legacy.A=legacy.read(legacy.P)
from measured_surface import *
from scipy.spatial import cKDTree
# Reuse the frozen measurement functions with an independent data preset.
P=BASE/'data/surface_atlas.json';A=read(P)

def fold_edge(source,spec):
 cfg=A['fold_search'];poly=np.array(spec['polyline'],float);offset=np.arange(-cfg['search_radius_px'],cfg['search_radius_px']+.01,.5);rows=[];nom=[];norm=[]
 for p,q in zip(poly[:-1],poly[1:]):
  d=q-p;dist=np.linalg.norm(d);n=np.array([-d[1],d[0]])/dist;k=max(2,int(np.ceil(dist/cfg['sample_spacing_px'])));nom.extend(p+np.arange(k)[:,None]/k*d);norm.extend([n]*k)
 nom=np.array(nom);norm=np.array(norm);candidate=nom[:,None,:]+offset[None,:,None]*norm[:,None,:];r=cfg['normal_difference_radius_px'];before=candidate-r*norm[:,None,:];after=candidate+r*norm[:,None,:]
 aa=np.stack([ndi.map_coordinates(source[:,:,k].astype(float),[before[:,:,1],before[:,:,0]],order=1,mode='nearest') for k in range(3)],2);bb=np.stack([ndi.map_coordinates(source[:,:,k].astype(float),[after[:,:,1],after[:,:,0]],order=1,mode='nearest') for k in range(3)],2)
 # Positive normal is the visually darker return. Reject saturated pink ribbon as fold evidence.
 pink=(aa[:,:,0]-aa[:,:,1]>25)|(bb[:,:,0]-bb[:,:,1]>25)
 score=np.where(pink,-100,aa.mean(2)-bb.mean(2));cost=-score+cfg['normal_displacement_penalty']*offset[None,:]**2;total=cost[0].copy();backs=[]
 for row in cost[1:]:
  cand=total[:,None]+cfg['neighbor_offset_penalty']*(offset[:,None]-offset[None,:])**2;prev=cand.argmin(0);backs.append(prev);total=row+cand[prev,np.arange(len(offset))]
 chosen=[int(total.argmin())]
 for row in backs[::-1]:chosen.append(int(row[chosen[-1]]))
 for i,j in enumerate(chosen[::-1]):
  measured=score[i,j]>=cfg['minimum_contrast'];xy=candidate[i,j] if measured else nom[i];rows.append({'xy_px':xy.tolist(),'contrast':float(score[i,j]),'status':'measured_color_edge' if measured else 'manual_unobserved_search_anchor','offset_px':float(offset[j]) if measured else 0})
 return rows

def extract(source):
 m,a=legacy.extract(source);m['schema']='riverstone.measured_surface_atlas.v1';m['folds']={}
 for name in ['front','side']:
  rows=fold_edge(source,A['fold_search'][name]);pts=np.array([p['xy_px'] for p in rows]);order=np.argsort(pts[:,0]);pts=pts[order];x0,y0,x1,y1=C['views'][name]['crop'];xx=np.arange(x0,x1)+.5;fy=np.interp(xx,pts[:,0],pts[:,1]);yy=np.arange(y0,y1)[:,None]+.5;labels=np.where(yy<fy,1,2).astype(np.uint8)*a[name+'_support'];a[name+'_charts']=labels
  m['folds'][name]={'points':rows,'interpretation':'Observed white-to-lavender color boundary. Not an observed dihedral angle or sewing seam.','chart_pixels':{str(i):int((labels==i).sum()) for i in [1,2]}}
 m['dependencies'].append({'role':'atlas_extractor_solver_adapter','path':str(Path(__file__).resolve().relative_to(REPO)),'sha256':sha(__file__)})
 m['arrays_digest']=digest({k:rawsha(v) for k,v in a.items()});return m,a

def validate(m,a,source):
 if not m or m.get('schema')!='riverstone.measured_surface_atlas.v1':raise ValueError('Independent atlas measurement required')
 old=copy.deepcopy(m);old['schema']='riverstone.measured_visible_surface.v1';legacy.validate(old,a,source)

def load_measurement():
 p=BASE/'evidence/measurements.json.gz'
 if not p.is_file():raise ValueError('Independent measured input required')
 m=gzread(p);assert sha(BASE/'evidence/measurements.npz')==m['arrays_file_sha256'];a=dict(np.load(BASE/'evidence/measurements.npz'));validate(m,a,SOURCE);return m,a

def arclength_resample(points,t):
 p=np.array(points,float);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];s/=s[-1];return np.c_[np.interp(t,s,p[:,0]),np.interp(t,s,p[:,1])]

def solve(m,a,yaw=75):
 mask=a['front_support'];nodes,faces,lookup=vertex_domain(mask);sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit'];theta=math.radians(yaw);xx=(nodes[:,0]-F['axis_u'])*SCALE;yy=(F['sole_y']-nodes[:,1])*SCALE;bounds=[];missing=[];root_priors=[]
 for x,y in zip(xx,yy):
  sy=sv['sole_y']-y/ss;rr={int(math.floor(sy)),int(math.ceil(sy))-1};spans=[]
  for row in rr:
   if 0<=row<a['side_support'].shape[0]:spans+=runs(a['side_support'][row])
  if not spans:
   prior=A['surface_prior']['unknown_root_depth_prior'];px=x/SCALE+F['axis_u'];py=F['sole_y']-y/SCALE;rx0,ry0,rx1,ry1=prior['front_pixel_box'];available=np.where(a['side_support'].any(1))[0];near=int(available[np.argmin(abs(available-sy))]) if len(available) else -1000
   if rx0<=px<=rx1 and ry0<=py<=ry1 and abs(near-sy)<=prior['max_vertical_distance_px']+1e-8:
    spans=runs(a['side_support'][near]);root_priors.append({'front_xy_px':[float(px),float(py)],'aligned_side_y_px':float(sy),'borrowed_measured_row':near,'vertical_extrapolation_px':float(abs(near-sy)),'status':'explicit unknown-root depth prior, not measured support'})
   else:missing.append(sy);bounds.append([np.nan,np.nan]);continue
  u0=min(q[0] for q in spans)+sv['crop'][0];u1=max(q[1] for q in spans)+sv['crop'][0];bounds.append([(math.cos(theta)*x-(u1-sv['axis_u'])*ss)/math.sin(theta),(math.cos(theta)*x-(u0-sv['axis_u'])*ss)/math.sin(theta)])
 if missing:raise ValueError('Corresponding side region has no measured support for '+str(len(missing))+' source vertices; no whole-skirt fallback')
 bounds=np.array(bounds);n=len(nodes);labels=a['front_charts'];edge_sets={1:set(),2:set()}
 for y,x in zip(*np.where(mask)):
  chart=int(labels[y,x]);x+=F['crop'][0];y+=F['crop'][1];q=[lookup[(x+dx,y+dy)] for dx,dy in [(0,0),(1,0),(1,1),(0,1)]]
  for i,j in zip(q,q[1:]+q[:1]):edge_sets[chart].add(tuple(sorted((i,j))))
 operators=[]
 for chart,es in edge_sets.items():
  es=sorted(es);ec=np.array(es).ravel();E=sparse.csr_matrix((np.tile([-1.,1.],len(es)),(np.repeat(np.arange(len(es)),2),ec)),shape=(len(es),n));L=E.T@E;deg=np.asarray(abs(E).sum(0)).ravel();N=sparse.diags(1/np.maximum(deg,1))@L;operators.append((E,N))
 fp=[p['xy_px'] for p in m['folds']['front']['points']];sp=[p['xy_px'] for p in m['folds']['side']['points']];t=np.linspace(0,1,len(fp));fp=arclength_resample(fp,t);sp=arclength_resample(sp,t);tree=cKDTree(nodes);dist,ids=tree.query(fp);guide=np.zeros(n);weight=np.zeros(n);records=[]
 for fi,si,d,i in zip(fp,sp,dist,ids):
  xf=(fi[0]-F['axis_u'])*SCALE;yf=(F['sole_y']-fi[1])*SCALE;ys=(sv['sole_y']-si[1])*ss;target=(math.cos(theta)*xf-(si[0]-sv['axis_u'])*ss)/math.sin(theta)
  if d<=1.5:guide[i]+=target;weight[i]+=1
  records.append({'front_xy_px':fi.tolist(),'side_xy_px':si.tolist(),'aligned_y_residual_m':float(yf-ys),'depth_prior_m':float(target),'constraint_status':'manual normalized measured arc-length correspondence prior'})
 nz=weight>0;guide[nz]/=weight[nz];weight[nz]=A['surface_prior']['fold_correspondence_weight'];target=bounds.mean(1);cfg=A['surface_prior']
 def fun(z):
  delta=z-target;g=z-guide;v=cfg['data_weight']*(delta@delta)+np.dot(weight,g*g);grad=2*(cfg['data_weight']*delta+weight*g)
  for E,N in operators:
   d=E@z;c=N@z;v+=cfg['tangent_weight']*(d@d)+cfg['curvature_weight']*(c@c);grad+=2*(cfg['tangent_weight']*(E.T@d)+cfg['curvature_weight']*(N.T@c))
  return float(v),np.asarray(grad)
 fit=minimize(fun,target,jac=True,bounds=bounds,method='L-BFGS-B',options={'maxiter':cfg['max_solver_iterations'],'ftol':1e-13,'gtol':1e-6,'maxls':40,'maxcor':8});z=fit.x;v=np.c_[xx,yy,z]
 return v,faces,{'success':bool(fit.success),'message':str(fit.message),'iterations':int(fit.nit),'objective':float(fit.fun),'source_nodes':len(nodes),'source_triangles':len(faces),'source_pixel_nodes':nodes.tolist(),'bound_intervals_m':bounds.tolist(),'depth_extent_m':[float(z.min()),float(z.max())],'fold_correspondence':records,'fold_y_residual_rms_m':float(np.sqrt(np.mean([q['aligned_y_residual_m']**2 for q in records]))),'fold_y_residual_max_m':float(max(abs(q['aligned_y_residual_m']) for q in records)),'active_fold_prior_vertices':int(nz.sum()),'unknown_root_depth_prior_vertices':root_priors,'side_bound_violation_m':float(max((bounds[:,0]-z).max(),(z-bounds[:,1]).max(),0))}

def adaptive(v,fit,a):
 nodes=np.array(fit['source_pixel_nodes'],int);z={tuple(p):q[2] for p,q in zip(nodes,v)};mask=a['front_support'];lab=a['front_charts'];ys,xs=np.where(mask);x0=int(xs.min()+F['crop'][0]);y0=int(ys.min());size=1
 while size<max(xs.max()-xs.min()+1,ys.max()-ys.min()+1):size*=2
 leaves=[];tol=A['adaptive_mesh']['max_depth_interpolation_error_m'];maxw=A['adaptive_mesh']['max_leaf_width_px']
 def recurse(x,y,w):
  a0=max(x-F['crop'][0],0);a1=min(x+w-F['crop'][0],mask.shape[1]);b0=max(y,0);b1=min(y+w,mask.shape[0]);cut=mask[b0:b1,a0:a1]
  if not cut.any():return
  full=cut.shape==(w,w) and cut.all();charts=lab[b0:b1,a0:a1];corn=[(x,y),(x+w,y),(x+w,y+w),(x,y+w)];err=None
  if full and np.all(charts==charts[0,0]) and w<=maxw:
   zz=np.array([[z[(xx,yy)] for xx in range(x,x+w+1)] for yy in range(y,y+w+1)]);t=np.arange(w+1)/w;bl=(1-t[:,None])*((1-t[None,:])*zz[0,0]+t[None,:]*zz[0,-1])+t[:,None]*((1-t[None,:])*zz[-1,0]+t[None,:]*zz[-1,-1]);err=float(np.max(abs(zz-bl)))
   if err<=tol:leaves.append((x,y,w,int(charts[0,0]),err));return
  if w==1:leaves.append((x,y,w,int(charts[0,0]),0));return
  h=w//2
  for dx,dy in [(0,0),(h,0),(0,h),(h,h)]:recurse(x+dx,y+dy,h)
 recurse(x0,y0,size)
 corners=set()
 for x,y,w,_,_ in leaves:corners.update([(x,y),(x+w,y),(x+w,y+w),(x,y+w)])
 byx={};byy={}
 for x,y in corners:byx.setdefault(x,[]).append(y);byy.setdefault(y,[]).append(x)
 for v0 in byx.values():v0.sort()
 for v0 in byy.values():v0.sort()
 verts=[];index={};faces=[];charts=[]
 def vertex(p):
  if p not in index:
   x,y=p;zz=z.get(p)
   if zz is None:
    xa,ya=int(math.floor(x)),int(math.floor(y));tx,ty=x-xa,y-ya;zz=sum(z[(xa+dx,ya+dy)]*(tx if dx else 1-tx)*(ty if dy else 1-ty) for dx,dy in [(0,0),(1,0),(0,1),(1,1)])
   index[p]=len(verts);verts.append([(x-F['axis_u'])*SCALE,(F['sole_y']-y)*SCALE,zz])
  return index[p]
 for x,y,w,chart,err in leaves:
  ring=[(xx,y) for xx in byy[y] if x<=xx<x+w]+[(x+w,yy) for yy in byx[x+w] if y<=yy<y+w]+[(xx,y+w) for xx in reversed(byy[y+w]) if x<xx<=x+w]+[(x,yy) for yy in reversed(byx[x]) if y<yy<=y+w];ids=[vertex(p) for p in ring]
  if len(ids)==4:faces.extend([[ids[0],ids[1],ids[2]],[ids[0],ids[2],ids[3]]]);charts.extend([chart]*2)
  else:
   c=vertex((x+w/2,y+w/2))
   for aa,bb in zip(ids,ids[1:]+ids[:1]):faces.append([aa,bb,c]);charts.append(chart)
 vv=np.array(verts);ff=np.array(faces,int)
 return vv,ff,np.array(charts,int),{'leaf_count':len(leaves),'vertices':len(vv),'triangles':len(ff),'native_triangles':len(v)*0+int(mask.sum())*2,'maximum_leaf_bilinear_depth_error_m':max(q[4] for q in leaves),'measured_pixel_domain_area':int(mask.sum()),'t_junction_policy':'Every neighboring leaf corner splits both incident edges; identical shared coordinate/depth. No output pixel repair.'}

def master(m,a,source,v,f,charts):
 ma=legacy.make_master(m,a,source,v,f)
 for i,(o,chart) in enumerate(zip(ma['components'][0]['operations'],charts)):
  o['id']='atlas_triangle_'+str(i);o['part']=A['region_id']+('_outer_chart' if chart==1 else '_return_chart')
 ma['components'][0]['parts']=[{'id':A['region_id']+suffix,'pivot':[0,0,0]} for suffix in ['_outer_chart','_return_chart']];ma['id']='measured_large_lobe_atlas06';ma['extensions']['generator_sha256']=sha(__file__);ma['extensions']['chart_identity']='visible surface charts, sewn panel identity unknown';return rounded(ma)

def build(m,a,source,yaw=75):
 validate(m,a,source);v,f,fit=solve(m,a,yaw);av,af,charts,mesh=adaptive(v,fit,a);ma=master(m,a,source,av,af,charts);return ma,av,af,fit,mesh,charts

def run():
 t=time.monotonic();m,a=extract(SOURCE);save_measurement(m,a);ma,v,f,fit,mesh,charts=build(m,a,SOURCE);gzwrite(BASE/'generated/panel_master.json.gz',ma);np.savez_compressed(BASE/'generated/continuous_surface.npz',vertices=v,triangles=f,charts=charts);gzwrite(BASE/'evidence/surface_fit.json.gz',fit);write(BASE/'evidence/adaptive_mesh.json',mesh);write(BASE/'evidence/build_resources.json',{'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'geometry_complete':False,'measured_source_components':int(ndi.label(a['front_support'])[1]),'operations':len(f),'solver':{k:v for k,v in fit.items() if k not in ['source_pixel_nodes','bound_intervals_m','fold_correspondence']}});print(json.dumps({'mesh':mesh,'fit':{k:v for k,v in fit.items() if k not in ['source_pixel_nodes','bound_intervals_m','fold_correspondence']},'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}))
if __name__=='__main__':run()
