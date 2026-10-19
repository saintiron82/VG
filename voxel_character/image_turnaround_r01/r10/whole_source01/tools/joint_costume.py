"""Approved pixels -> whole visible costume ownership -> joint bounded-depth atlas.
Known patch and whole-envelope semantic priors remain explicit data. No body,
hair, skin, socket, hidden connector or post-voxel repair is created here.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'continuous06/tools'))
import surface_atlas as atlas
from surface_atlas import *
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;P=BASE/'data/joint_costume.json';A=read(P)
def configure(config,path,base):
 legacy.A=config;legacy.P=path;legacy.BASE=base

def extract(source):
 ap=ROOT/'continuous05c/data/panel_correspondence.json';configure(read(ap),ap,ap.parent.parent);mu,au=legacy.extract(source)
 ap=ROOT/'continuous06/data/surface_atlas.json';atlas.A=read(ap);atlas.P=ap;atlas.BASE=ap.parent.parent;configure(atlas.A,ap,atlas.BASE);ml,al=atlas.extract(source)
 configure(A,P,BASE);m,a=legacy.extract(source);m['schema']='riverstone.whole_visible_costume_measurement.v1';m['known_patch_measurements']={'upper':mu,'lobe':ml};m['ownership']={}
 for name in ['front','side','back']:
  x0,y0,x1,y1=C['views'][name]['crop'];oc=np.zeros_like(a[name+'_support'])
  for poly in A['occluder_semantic_polygons'][name]:oc|=polygon_mask(poly,C['views'][name]['crop'])
  visible=a[name+'_visible']&~oc;known=au[name+'_support']|al[name+'_support'];remaining=visible&~known;labels=np.zeros_like(remaining,np.uint8);labels[au[name+'_support']]=1
  if name in ['front','side']:
   labels[al[name+'_support']&(al[name+'_charts']==1)]=2;labels[al[name+'_support']&(al[name+'_charts']==2)]=3
  else:labels[al[name+'_support']]=2
  overlap=au[name+'_support']&al[name+'_support'];labels[remaining]=4
  # A known cross-patch source pixel overlap is retained as an explicit ambiguity;
  # no generic priority converts it to a confirmed same-material point.
  a.update({name+'_charts':labels,name+'_support':labels>0,name+'_visible':visible|au[name+'_visible']|al[name+'_visible'],name+'_occluded_unknown':(au[name+'_occluded_unknown']|al[name+'_occluded_unknown']),name+'_unmodeled_occluder':oc&a[name+'_visible'],name+'_known_patch_overlap':overlap,name+'_remaining_visible':remaining,name+'_upper_candidate':au[name+'_support'],name+'_lobe_candidate':al[name+'_support']})
  m['ownership'][name]={'whole_rgb_eligible_visible_pixels':int(visible.sum()),'known_upper_pixels':int(au[name+'_support'].sum()),'known_lobe_pixels':int(al[name+'_support'].sum()),'remaining_visible_pixels':int(remaining.sum()),'known_patch_overlap_ambiguity_pixels':int(overlap.sum()),'omitted_under_occluder_eligible_pixels':int((oc&a[name+'_visible']).sum()),'source_domain_components':int(ndi.label(labels>0)[1]),'remaining_component_sizes':sorted(np.bincount(ndi.label(remaining)[0].ravel())[1:].tolist(),reverse=True),'ownership_remainder_overlap_pixels':int((remaining&known).sum()),'new_hidden_cloth_fill_pixels':0}
 if not a['side_support'].any():raise ValueError('No measured side costume support, cannot infer depth')
 m['dependencies'] += [{'role':'known_upper_semantics','path':str((ROOT/'continuous05c/data/panel_correspondence.json').relative_to(REPO)),'sha256':sha(ROOT/'continuous05c/data/panel_correspondence.json')},{'role':'known_lobe_semantics','path':str((ROOT/'continuous06/data/surface_atlas.json').relative_to(REPO)),'sha256':sha(ROOT/'continuous06/data/surface_atlas.json')},{'role':'atlas_shared_implementation','path':str(Path(atlas.__file__).relative_to(REPO)),'sha256':sha(atlas.__file__)},{'role':'joint_costume_adapter','path':str(Path(__file__).resolve().relative_to(REPO)),'sha256':sha(__file__)}]
 m['arrays_digest']=digest({k:rawsha(v) for k,v in a.items()});return m,a

def validate(m,a,source):
 if not m or m.get('schema')!='riverstone.whole_visible_costume_measurement.v1':raise ValueError('Independent whole measurement required')
 old=copy.deepcopy(m);old['schema']='riverstone.measured_visible_surface.v1';legacy.validate(old,a,source)
def load_measurement():
 m=gzread(BASE/'evidence/measurements.json.gz');a=dict(np.load(BASE/'evidence/measurements.npz'));assert sha(BASE/'evidence/measurements.npz')==m['arrays_file_sha256'];validate(m,a,SOURCE);return m,a

def solve(m,a):
 nodes,faces,lookup=vertex_domain(a['front_support']);n=len(nodes)
 if n>A['budget']['max_source_nodes']:raise ValueError('Source-node budget exceeded before solver')
 cfg=A['joint_depth'];owners={i:set() for i in range(1,5)};edge_sets={i:set() for i in range(1,5)};native_owner=np.zeros(len(faces),np.uint8)
 for pi,(py,px) in enumerate(zip(*np.where(a['front_support']))):
  own=int(a['front_charts'][py,px]);x=px+F['crop'][0];y=py+F['crop'][1];q=[lookup[(x+dx,y+dy)] for dx,dy in [(0,0),(1,0),(1,1),(0,1)]];owners[own].update(q);native_owner[2*pi:2*pi+2]=own
  for i,j in zip(q,q[1:]+q[:1]):edge_sets[own].add(tuple(sorted((i,j))))
 shared={}
 for i in range(1,5):
  for j in range(i+1,5):shared[f'{i}_{j}']={'shared_edge_count':len(edge_sets[i]&edge_sets[j]),'shared_vertex_count':len(owners[i]&owners[j]),'interpretation':'joint geometric boundary prior only; sewing identity unknown'}
 theta=math.radians(cfg['side_yaw_deg']);sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit'];xworld=(nodes[:,0]-F['axis_u'])*SCALE;yworld=(F['sole_y']-nodes[:,1])*SCALE;rowradius=cfg['vertical_alignment_uncertainty_px'];bound_ids=[];lower=[];upper=[];record=[];missing=[]
 for own in range(1,5):
  sidemask=a['side_upper_candidate'] if own==1 else a['side_lobe_candidate'] if own in [2,3] else a['side_support'];row_intervals={y:(int(np.flatnonzero(sidemask[y])[0]+sv['crop'][0]),int(np.flatnonzero(sidemask[y])[-1]+sv['crop'][0]+1)) for y in np.where(sidemask.any(1))[0]}
  for i in sorted(owners[own]):
   sy=sv['sole_y']-yworld[i]/ss;rows=[r for r in range(int(math.floor(sy))-rowradius,int(math.ceil(sy))+rowradius+1) if r in row_intervals]
   if not rows:missing.append([own,i,float(sy)]);continue
   ulo=min(row_intervals[r][0] for r in rows);uhi=max(row_intervals[r][1] for r in rows);lo=(math.cos(theta)*xworld[i]-(uhi-sv['axis_u'])*ss)/math.sin(theta);hi=(math.cos(theta)*xworld[i]-(ulo-sv['axis_u'])*ss)/math.sin(theta);bound_ids.append(i);lower.append(lo);upper.append(hi);record.append([own,i,float(sy),ulo,uhi,min(rows),max(rows)])
 ids=np.array(bound_ids);lower=np.array(lower);upper=np.array(upper);sums=np.zeros(n);counts=np.zeros(n);np.add.at(sums,ids,(lower+upper)/2);np.add.at(counts,ids,1);target=sums/np.maximum(counts,1);unknown=counts==0
 # Unmeasured vertices have no fake depth observation. A constant gauge merely
 # initializes the regularized solve; its count and affected source pixels remain explicit.
 target[unknown]=float(np.median(target[~unknown]));loint=np.full(n,-np.inf);hiint=np.full(n,np.inf);np.maximum.at(loint,ids,lower);np.minimum.at(hiint,ids,upper);conflicts=np.flatnonzero(loint>hiint);operators=[]
 for own,es in edge_sets.items():
  es=sorted(es)
  if not es:continue
  ec=np.array(es).ravel();E=sparse.csr_matrix((np.tile([-1.,1.],len(es)),(np.repeat(np.arange(len(es)),2),ec)),shape=(len(es),n));L=E.T@E;deg=np.asarray(abs(E).sum(0)).ravel();N=sparse.diags(1/np.maximum(deg,1))@L;operators.append((own,E,N))
 guide=np.zeros(n);weight=np.zeros(n);ml=m['known_patch_measurements']['lobe'];fp=[q['xy_px'] for q in ml['folds']['front']['points']];sp=[q['xy_px'] for q in ml['folds']['side']['points']];t=np.linspace(0,1,len(fp));fp=atlas.arclength_resample(fp,t);sp=atlas.arclength_resample(sp,t);dist,idx=cKDTree(nodes).query(fp)
 for f0,s0,d,i in zip(fp,sp,dist,idx):
  if d<=1.5:guide[i]+=(math.cos(theta)*(f0[0]-F['axis_u'])*SCALE-(s0[0]-sv['axis_u'])*ss)/math.sin(theta);weight[i]+=1
 present=weight>0;guide[present]/=weight[present];weight[present]=.2
 def fun(z):
  d=z-target;v=cfg['midpoint_gauge_weight']*(d@d);g=2*cfg['midpoint_gauge_weight']*d;below=np.minimum(z[ids]-lower,0);above=np.maximum(z[ids]-upper,0);v+=cfg['bound_weight']*(below@below+above@above);np.add.at(g,ids,2*cfg['bound_weight']*(below+above));q=z-guide;v+=np.dot(weight,q*q);g+=2*weight*q
  for own,E,N in operators:
   t=E@z;c=N@z;v+=cfg['tangent_weight']*(t@t)+cfg['curvature_weight']*(c@c);g+=2*(cfg['tangent_weight']*(E.T@t)+cfg['curvature_weight']*(N.T@c))
  return float(v),g
 fit=minimize(fun,target,jac=True,method='L-BFGS-B',options={'maxiter':cfg['max_iterations'],'ftol':1e-12,'gtol':1e-6,'maxls':30,'maxcor':6});z=fit.x;viol=np.maximum.reduce([lower-z[ids],z[ids]-upper,np.zeros(len(ids))]);vertices=np.c_[xworld,yworld,z]
 out={'success':bool(fit.success),'message':str(fit.message),'iterations':int(fit.nit),'objective':float(fit.fun),'source_nodes':n,'source_triangles':len(faces),'source_pixel_nodes':nodes.tolist(),'source_components_four_connected':int(ndi.label(a['front_support'])[1]),'shared_chart_boundaries':shared,'same_node_incompatible_depth_interval_count':len(conflicts),'incompatible_interval_max_gap_m':float(np.max(loint[conflicts]-hiint[conflicts])) if len(conflicts) else 0,'side_bound_count':len(ids),'maximum_actual_bound_violation_m':float(viol.max()),'rms_actual_bound_violation_m':float(np.sqrt(np.mean(viol**2))),'bound_violation_over_1mm_count':int((viol>.001).sum()),'unmeasured_depth_vertex_count':int(unknown.sum()),'unmeasured_depth_records':missing,'depth_extent_m':[float(z.min()),float(z.max())],'fold_correspondence':'same explicit normalized measured arc-length prior as06, not an observed material point','side_correspondence':'Known patches use their own candidate region; unpaired remaining cloth uses whole costume only as conservative support. Not a target panel silhouette.'}
 return vertices,faces,out

def build(m,a,source):
 validate(m,a,source);v,f,fit=solve(m,a);atlas.A=A;atlas.BASE=BASE;atlas.P=P;av,af,charts,mesh=atlas.adaptive(v,fit,a);configure(A,P,BASE);ma=legacy.make_master(m,a,source,av,af);names={1:'upper_known_patch',2:'lobe_outer_known_patch',3:'lobe_return_known_patch',4:'remaining_visible_costume'}
 for i,(op,ch) in enumerate(zip(ma['components'][0]['operations'],charts)):op['id']='visible_costume_triangle_'+str(i);op['part']=names[int(ch)]
 ma['components'][0]['parts']=[{'id':name,'pivot':[0,0,0]} for name in names.values()];ma['id']='approved_violet_whole_visible_costume_source01';ma['extensions'].update({'generator_sha256':sha(__file__),'whole_visible_costume_candidate':True,'whole_character_complete':False,'hidden_roots_or_socket_geometry_generated':False,'joint_depth_constraints_consistent':fit['same_node_incompatible_depth_interval_count']==0,'solver_converged':fit['success']});return rounded(ma),av,af,charts,fit,mesh

def run():
 t=time.monotonic();m,a=extract(SOURCE);configure(A,P,BASE);legacy.save_measurement(m,a);write(BASE/'evidence/ownership_preflight.json',{'ownership':m['ownership'],'front_source_pixels':int(a['front_support'].sum()),'geometry_not_yet_verified':True});ma,v,f,ch,fit,mesh=build(m,a,SOURCE);payload=gzip.compress(canonical(ma),mtime=0);existing=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file());
 if existing+len(payload)>A['budget']['new_bytes_ceiling']:raise ValueError('New3MB budget before master write exceeded')
 (BASE/'generated/costume_master.json.gz').write_bytes(payload);np.savez_compressed(BASE/'generated/continuous_costume.npz',vertices=v,triangles=f,charts=ch);gzwrite(BASE/'evidence/joint_fit.json.gz',fit);write(BASE/'evidence/adaptive_mesh.json',mesh);write(BASE/'evidence/build_resources.json',{'elapsed_seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'operations':len(f),'master_compressed_bytes':len(payload),'source_only_no_compile':True});print(json.dumps({'ownership':m['ownership'],'fit':{k:v for k,v in fit.items() if k not in ['source_pixel_nodes','unmeasured_depth_records']},'mesh':mesh,'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}))
if __name__=='__main__':run()
