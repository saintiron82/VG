"""Approved pixels -> independent measured curves/masks -> multiview boundary
triangulation -> minimum-curvature disk charts -> shared common extrusion grammar.
No source image texture, manual 3D dimensions, hidden socket, island deletion.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'continuous05c/tools'))
import measured_surface as legacy
from measured_surface import *
from scipy.sparse.linalg import spsolve
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
P=BASE/'data/multiview_charts.json';A=read(P);FULL=read(REPO/A['full_envelope_contract'])
SOURCE=np.array(Image.open(REPO/A['source']).convert('RGB'));assert sha(REPO/A['source'])==A['source_sha256']
C=read(REPO/A['alignment_contract']);F=C['views']['front'];SCALE=HEIGHT/F['scale_px_per_unit']

def configure(cfg=A):legacy.A=cfg;legacy.P=P;legacy.BASE=BASE

def extract(source):
 configure(FULL);m,a=legacy.extract(source);views={};charts=[]
 for name in ['front','side','back']:
  raw=a[name+'_support'].copy();oc=np.zeros_like(raw)
  for poly in FULL['occluder_semantic_polygons'][name]:oc|=polygon_mask(poly,C['views'][name]['crop'])
  fg=a[name+'_foreground'];a[name+'_visible']&=fg&~oc;a[name+'_occluded_unknown']&=fg&~oc;a[name+'_support']=a[name+'_visible']|a[name+'_occluded_unknown']
  views[name]={'raw_exterior_white_conflict_pixels':int((raw&~fg).sum()),'post_gate_exterior_conflict_pixels':int((a[name+'_support']&~fg).sum()),'visible_pixels':int(a[name+'_visible'].sum()),'unknown_occlusion_pixels':int(a[name+'_occluded_unknown'].sum()),'unmodeled_occluder_eligible_pixels':int((raw&oc).sum())}
 if not a['side_support'].any():raise ValueError('No actual measured side costume support')
 configure()
 for i,spec in enumerate(A['charts']):
  q={'id':spec['id'],'views':{},'cross_view_identity':spec['secondary_identity']}
  for name,vs in spec['views'].items():
   poly,records=legacy.sampled_edge(source,vs)
   # Search segments meet at manual semantic corner anchors. Independent normal searches
   # cannot define a crossing corner; retain a small explicitly unobserved corner collar.
   for k,r in enumerate(records):
    seg=r['segment'];p0=np.array(vs['contour_search_vertices'][seg],float);p1=np.array(vs['contour_search_vertices'][(seg+1)%len(vs['contour_search_vertices'])],float);d=p1-p0;t=float(np.dot(np.array(r['xy_px'])-p0,d)/np.dot(d,d));nom=p0+np.clip(t,0,1)*d
    if min(np.linalg.norm(nom-p0),np.linalg.norm(nom-p1))<A['corner_anchor_uncertainty_px']:
     r['unregularized_measurement']=copy.deepcopy(r);r['xy_px']=nom.tolist();r['status']='manual_corner_anchor_uncertainty';poly[k]=nom.tolist()
   cross=contour_crossings(poly)
   if cross:raise ValueError('Self-crossing annotated/measured boundary '+spec['id']+'/'+name+': '+str(cross[:4]))
   domain=polygon_mask(poly,C['views'][name]['crop']);support=domain&a[name+'_support'];key=f'chart_{i}_{name}';a[key]=support;q['views'][name]={'boundary':records,'visible_mask_array':key,'observed_gradient_points':sum(r['status']=='measured_edge' for r in records),'manual_unobserved_points':sum(r['status']!='measured_edge' for r in records),'measured_support_pixels':int(support.sum())}
  charts.append(q)
 dep=[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in [P,Path(__file__),Path(legacy.__file__),REPO/A['alignment_contract'],REPO/A['full_envelope_contract']]]
 out={'schema':'riverstone.boundary_atlas_measurement.v1','source_file_sha256':A['source_sha256'] if np.array_equal(source,SOURCE) else None,'actual_pixel_sha256':rawsha(source),'approved_parent_sha256':A['source_sha256'],'source_status':'APPROVED_REFERENCE' if np.array_equal(source,SOURCE) else 'TEST_ONLY_PIXEL_MUTATION','views':views,'charts':charts,'dependencies':dep,'arrays_digest':digest({k:rawsha(v) for k,v in a.items()})}
 return out,a

def validate(m,a,source):
 if not m or m.get('schema')!='riverstone.boundary_atlas_measurement.v1':raise ValueError('Independent measured curves and masks required')
 if m['actual_pixel_sha256']!=rawsha(source):raise ValueError('Wrong source pixel digest')
 if digest({k:rawsha(v) for k,v in a.items()})!=m['arrays_digest']:raise ValueError('Changed measured masks')
 for p in m['dependencies']:
  if sha(REPO/p['path'])!=p['sha256']:raise ValueError('Stale dependency '+p['path'])

def boundary(records,spec,sectors):
 phases=spec['phase_corner_indices'];nseg=len(spec['contour_search_vertices']);allpts=[]
 for j,start in enumerate(phases):
  end=phases[(j+1)%len(phases)];segments=list(range(start,end if end>start else end+nseg));rec=[r['xy_px'] for k in segments for r in records if r['segment']==k%nseg];rec.append(next(r['xy_px'] for r in records if r['segment']==end));p=np.array(rec,float);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];s/=s[-1];ts=(np.arange(sectors)/sectors*len(phases)-j);active=(ts>=0)&(ts<1);allpts.append((active,np.c_[np.interp(ts[active],s,p[:,0]),np.interp(ts[active],s,p[:,1])]))
 result=np.zeros((sectors,2))
 for active,p in allpts:result[active]=p
 return result

def template():
 nr=A['surface_prior']['rings'];ns=A['surface_prior']['sectors'];uv=[[0.,0.]]
 for r in range(1,nr+1):uv.extend([[r/nr*math.cos(t),r/nr*math.sin(t)] for t in np.arange(ns)*2*math.pi/ns])
 ff=[]
 for k in range(ns):ff.append([0,1+k,1+(k+1)%ns])
 for r in range(1,nr):
  for k in range(ns):
   a=1+(r-1)*ns+k;b=1+(r-1)*ns+(k+1)%ns;c=1+r*ns+(k+1)%ns;d=1+r*ns+k;ff.extend([[a,b,c],[a,c,d]])
 uv=np.array(uv);ff=np.array(ff);n=len(uv);edges=set()
 for tri in ff:
  for i,j in zip(tri,np.roll(tri,-1)):edges.add(tuple(sorted([int(i),int(j)])))
 # Intrinsic 2D disk cotangent Laplacian; each chart solved independently.
 L=sparse.lil_matrix((n,n));area=np.zeros(n)
 for tri in ff:
  pp=uv[tri];ar=abs(np.cross(pp[1]-pp[0],pp[2]-pp[0]))/2
  for i in tri:area[i]+=ar/3
  for k in range(3):
   i,j,h=tri[k],tri[(k+1)%3],tri[(k+2)%3];cot=np.dot(uv[i]-uv[h],uv[j]-uv[h])/(2*ar)/2;L[i,i]+=cot;L[j,j]+=cot;L[i,j]-=cot;L[j,i]-=cot
 L=L.tocsr();K=L.T@sparse.diags(1/np.maximum(area,1e-12))@L+A['surface_prior']['tension']*L;nb=ns;inter=np.arange(n-nb);rim=np.arange(n-nb,n);T=-spsolve(K[inter][:,inter].tocsc(),K[inter][:,rim].toarray());return uv,ff,inter,rim,T

def extend(rim,inter,ids,T):
 v=np.empty((len(inter)+len(ids),rim.shape[1]));v[ids]=rim;v[inter]=T@rim;return v

def side_bounds(front,a):
 view=C['views']['side'];s=HEIGHT/view['scale_px_per_unit'];theta=math.radians(A['camera']['side_yaw_degrees']);ys=np.where(a['side_support'].any(1))[0];lo=[];hi=[];rec=[]
 for px,py in front:
  x=(px-F['axis_u'])*SCALE;y=(F['sole_y']-py)*SCALE;sy=view['sole_y']-y/s;near=int(ys[np.argmin(abs(ys-sy))]);rr=[r for r in range(int(sy)-4,int(sy)+5) if 0<=r<a['side_support'].shape[0] and a['side_support'][r].any()]
  if not rr:rr=[near]
  inds=np.concatenate([np.flatnonzero(a['side_support'][r])+view['crop'][0] for r in rr]);u0=float(inds.min());u1=float(inds.max()+1);lo.append((math.cos(theta)*x-(u1-view['axis_u'])*s)/math.sin(theta));hi.append((math.cos(theta)*x-(u0-view['axis_u'])*s)/math.sin(theta));rec.append(abs(near-sy))
 return np.array(lo),np.array(hi),rec

def triangulate_boundary(q,spec,a,anchor=None,yaw=None):
 ns=A['surface_prior']['sectors'];fp=boundary(q['views']['front']['boundary'],spec['views']['front'],ns);x=(fp[:,0]-F['axis_u'])*SCALE;yf=(F['sole_y']-fp[:,1])*SCALE;report={};theta=math.radians(yaw or A['camera']['side_yaw_degrees']);sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit']
 if 'side' in q['views']:
  sp=boundary(q['views']['side']['boundary'],spec['views']['side'],ns);ys=(sv['sole_y']-sp[:,1])*ss;z=(math.cos(theta)*x-(sp[:,0]-sv['axis_u'])*ss)/math.sin(theta);y=(2*yf+ys)/3;report={'depth_observation':'Boundary two-view triangulation conditioned on manual phase/arclength correspondence and 75-degree camera hypothesis','boundary_y_disagreement_rms_m':float(np.sqrt(np.mean((yf-ys)**2))),'boundary_y_disagreement_max_m':float(abs(yf-ys).max()),'secondary_boundary_px':sp.tolist()}
 else:
  lo,hi,dist=side_bounds(fp,a);gauge=np.interp(fp[:,1],anchor[0],anchor[1]);n=len(fp);D=np.eye(n)-np.roll(np.eye(n),1,axis=1);B=D.T@D
  if spec['hidden_depth_prior']=='backmost_measured_side_bound':gauge=lo.copy()
  def fun(z):
   d=z-gauge;t=D@z;c=B@z;return .1*(d@d)+(t@t)+8*(c@c),.2*d+2*(D.T@t)+16*(B.T@c)
  fit=minimize(fun,np.clip(gauge,lo,hi),jac=True,bounds=list(zip(lo,hi)),method='L-BFGS-B',options={'maxiter':600,'ftol':1e-13,'gtol':1e-8});z=fit.x;y=yf;report={'depth_observation':'UNKNOWN; bounded minimum-curvature prior, no fabricated side material points','depth_prior':spec['hidden_depth_prior'],'gauge_dependency':'measured upper-fold boundary only' if spec['hidden_depth_prior']=='nearest_paired' else 'actual whole-side far support bound, explicit rear-layer ordering assumption','solver_success':bool(fit.success),'nearest_side_height_extrapolation_max_px':float(max(dist)),'depth_bound_violation_m':float(max((lo-z).max(),(z-hi).max(),0))}
 return np.c_[x,y,z],fp,report

def build(m,a,source,yaw=None):
 validate(m,a,source);uv,ff,inter,rim,T=template();ns=len(rim);allv=[];allf=[];allchart=[];allprimary=[];reports=[];offset=0;anchor=None;configure(FULL)
 # Fixed dependency: unknown charts inherit only the first known upper-fold gauge.
 for i,(q,spec) in enumerate(zip(m['charts'],A['charts'])):
  rv,fp,report=triangulate_boundary(q,spec,a,anchor,yaw)
  if i==0:
   order=np.argsort(fp[:,1]);yp=fp[order,1];zp=rv[order,2];unique=np.unique(yp);anchor=(unique,np.array([np.mean(zp[yp==y]) for y in unique]))
  v=extend(rv,inter,rim,T);primary=extend(fp,inter,rim,T);mask=a[q['views']['front']['visible_mask_array']];tri=primary[ff];bary=np.array([[1/3]*3,[.6,.2,.2],[.2,.6,.2],[.2,.2,.6],[.49,.49,.02],[.49,.02,.49],[.02,.49,.49]]);pts=np.einsum('sk,tkd->tsd',bary,tri);px=np.floor(pts[:,:,0]).astype(int)-F['crop'][0];py=np.floor(pts[:,:,1]).astype(int);ok=(px>=0)&(px<mask.shape[1])&(py>=0)&(py<mask.shape[0]);hit=np.zeros_like(ok);hit[ok]=mask[py[ok],px[ok]];fraction=hit.mean(1);keep=fraction>=A['surface_prior']['minimum_triangle_primary_support_fraction'];selected=ff[keep]
  normals=np.cross(v[selected[:,1]]-v[selected[:,0]],v[selected[:,2]]-v[selected[:,0]]);area=np.linalg.norm(normals,axis=1)/2;flat2=np.cross(primary[ff[:,1]]-primary[ff[:,0]],primary[ff[:,2]]-primary[ff[:,0]]);report.update({'id':spec['id'],'chart_index':i,'source_vertices':len(v),'retained_source_triangles':len(selected),'input_classification_rejected_facets':int((~keep).sum()),'degenerate_triangles':int((area<1e-12).sum()),'parameter_map_orientation_positive_triangles':int((flat2>0).sum()),'parameter_map_orientation_negative_triangles':int((flat2<0).sum()),'primary_domain_mapping_foldovers':bool((flat2>1e-8).any() and (flat2<-1e-8).any()),'boundary_world_m':rv.tolist(),'boundary_primary_px':fp.tolist(),'depth_extent_m':[float(v[:,2].min()),float(v[:,2].max())],'hidden_root_socket':None})
  allv.extend(v);allprimary.extend(primary);allf.extend(selected+offset);allchart.extend([i]*len(selected));offset+=len(v);reports.append(report)
 v=np.array(allv);f=np.array(allf);ch=np.array(allchart);primary=np.array(allprimary)
 if len(f)>A['budget']['max_triangles']:raise ValueError('Triangle budget exceeded')
 configure(FULL);ma=legacy.make_master({'source_status':m['source_status'],'source_file_sha256':m['source_file_sha256'],'source_pixel_sha256':m['actual_pixel_sha256'],'arrays_digest':m['arrays_digest'],'dependencies':m['dependencies']},a,source,v,f);ma['id']='approved_violet_multiview_boundary_costume02';ma['components'][0]['parts']=[{'id':s['id'],'pivot':[0,0,0]} for s in A['charts']]
 for j,(op,idx) in enumerate(zip(ma['components'][0]['operations'],ch)):
  op['id']=f'chart_{int(idx)}_triangle_{j}';op['part']=A['charts'][int(idx)]['id']
 ma['extensions'].update({'generator_sha256':sha(__file__),'representation':'multi-view boundary triangulation plus independent minimum-curvature disk charts','complete_character':False,'hidden_socket_positions':None,'boundary_correspondence_observed':False,'back_same_panel_identity':'unknown; conservative held-out support only','normal_thickness_m':A['surface_prior']['normal_thickness_m'],'geometry_has_not_been_visually_approved':True});return rounded(ma),v,f,ch,primary,reports

def load():
 m=gzread(BASE/'evidence/measurement.json.gz');a=dict(np.load(BASE/'evidence/measurement.npz'));assert sha(BASE/'evidence/measurement.npz')==m['arrays_file_sha256'];validate(m,a,SOURCE);return m,a

def run():
 t=time.monotonic();m,a=extract(SOURCE);np.savez_compressed(BASE/'evidence/measurement.npz',**a);m['arrays_file_sha256']=sha(BASE/'evidence/measurement.npz');gzwrite(BASE/'evidence/measurement.json.gz',m);ma,v,f,ch,primary,rep=build(m,a,SOURCE);gzwrite(BASE/'generated/costume_master.json.gz',ma);np.savez_compressed(BASE/'generated/continuous_costume.npz',vertices=v,triangles=f,charts=ch,primary_pixels=primary);gzwrite(BASE/'evidence/boundary_fit.json.gz',rep);report={'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'vertices':len(v),'triangles':len(f),'bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()),'source_only':True,'charts':[ {k:v for k,v in q.items() if k not in ['boundary_world_m','boundary_primary_px','secondary_boundary_px']} for q in rep],'background_gate':m['views']};write(BASE/'evidence/build.json',report);print(json.dumps(report))
if __name__=='__main__':run()
