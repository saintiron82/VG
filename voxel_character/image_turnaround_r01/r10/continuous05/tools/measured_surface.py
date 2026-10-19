"""Generic annotated-correspondence -> measured pixel boundaries -> thin surface.
The image is never a render texture. All geometry uses measured domain vertices.
Hidden depth is a bounded, explicitly regularized inference, not recovered truth.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'tools'))
from measured_panels import *
from verify_and_render import raster,CPU_SOURCE,components,project
from scipy import sparse
from scipy.optimize import minimize
P=BASE/'data/panel_correspondence.json';A=read(P);C=read(REPO/A['alignment_contract']);F=C['views']['front'];HEIGHT=C['alignment']['character_height_m_for_test'];SCALE=HEIGHT/F['scale_px_per_unit'];SOURCE=np.array(Image.open(REPO/A['source']).convert('RGB'));assert sha(REPO/A['source'])==A['source_sha256']

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def rawsha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def rounded(v):
 if isinstance(v,dict):return {k:rounded(x) for k,x in v.items()}
 if isinstance(v,list):return [rounded(x) for x in v]
 if isinstance(v,(float,np.floating)):return round(float(v),10)
 if isinstance(v,np.integer):return int(v)
 return v

def polygon_mask(poly,crop):
 x0,y0,x1,y1=crop;xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5);inside=np.zeros(xx.shape,bool)
 for p,q in zip(poly,poly[1:]+poly[:1]):
  if abs(q[1]-p[1])<1e-12:continue
  inside^=((p[1]>yy)!=(q[1]>yy))&(xx<(q[0]-p[0])*(yy-p[1])/(q[1]-p[1])+p[0])
 return inside

def sampled_edge(source,spec):
 cfg=A['extractor'];poly=spec['contour_search_vertices'];pts=[];records=[];radius=cfg['normal_search_radius_px'];offsets=np.arange(-radius,radius+.01,.5);prior=cfg['normal_displacement_penalty']
 for seg,(p,q) in enumerate(zip(poly,poly[1:]+poly[:1])):
  p,q=np.array(p,float),np.array(q,float);d=q-p;length=np.linalg.norm(d);n=np.array([-d[1],d[0]])/length;count=max(2,int(math.ceil(length/cfg['boundary_sample_spacing_px'])));samples=p+np.arange(count)[:,None]/count*d
  uncertain=seg in spec['uncertain_segments'];allxy=samples[:,None,:]+offsets[None,:,None]*n
  r=cfg['color_difference_radius_px'];before=allxy-r*n;after=allxy+r*n
  aa=np.stack([ndi.map_coordinates(source[:,:,k].astype(float),[before[:,:,1],before[:,:,0]],order=1,mode='nearest') for k in range(3)],2);bb=np.stack([ndi.map_coordinates(source[:,:,k].astype(float),[after[:,:,1],after[:,:,0]],order=1,mode='nearest') for k in range(3)],2)
  strength=np.linalg.norm(aa-bb,axis=2)/math.sqrt(3);cost=-strength+prior*offsets[None,:]**2
  # Explicitly hidden segment is a semantic uncertainty boundary, not a fake measured gradient.
  if uncertain:chosen=np.full(count,int(np.argmin(abs(offsets))))
  else:
   back=[];total=cost[0].copy()
   for row in cost[1:]:
    candidates=total[:,None]+cfg['neighbor_offset_penalty']*(offsets[:,None]-offsets[None,:])**2;prev=candidates.argmin(0);back.append(prev);total=row+candidates[prev,np.arange(len(offsets))]
   chosen=[int(total.argmin())]
   for row in back[::-1]:chosen.append(int(row[chosen[-1]]))
   chosen=np.array(chosen[::-1])
  for i,j in enumerate(chosen):
   xy=allxy[i,j].tolist();s=float(strength[i,j]);pts.append(xy);records.append({'xy_px':xy,'segment':seg,'offset_px':float(offsets[j]),'edge_strength':s,'status':'manual_occluded_continuation' if uncertain else 'measured_edge' if s>=cfg['minimum_observed_edge_strength'] else 'low_gradient_uncertain'})
 return pts,records

def extract(source):
 if source.shape!=SOURCE.shape:raise ValueError('Source dimensions differ')
 arrays={};views={};cfg=A['extractor']
 for name,spec in A['views'].items():
  crop=C['views'][name]['crop'];x0,y0,x1,y1=crop;rgb=source[y0:y1,x0:x1].astype(float);poly,edges=sampled_edge(source,spec);domain=polygon_mask(poly,crop);chroma=rgb.max(2)-rgb.min(2)
  cloth=(rgb.mean(2)>=cfg['cloth_min_mean'])&(chroma<=cfg['cloth_max_chroma'])&(rgb[:,:,2]-rgb[:,:,0]>=cfg['cloth_blue_minus_red_min'])
  ribbon=(rgb[:,:,0]-rgb[:,:,1]>=cfg['ribbon_r_minus_g_min'])&(rgb[:,:,2]-rgb[:,:,1]>=cfg['ribbon_b_minus_g_min'])&(rgb[:,:,0]>=125)&(rgb[:,:,2]>=125)
  guide=(rgb[:,:,2]>=245)&(rgb[:,:,2]-rgb[:,:,0]>=25)&(rgb[:,:,2]-rgb[:,:,1]>=15)&(rgb[:,:,1]-rgb[:,:,0]>=6)
  oc=cfg['outline_rule'];outline=(rgb[:,:,0]>=oc['r_min'])&(rgb[:,:,1]>=oc['g_min'])&(rgb[:,:,2]-rgb[:,:,0]>=oc['blue_minus_red_min'])&(chroma<=oc['max_chroma'])
  rx0,ry0,rx1,ry1=spec['root_search_box'];root_unknown=np.zeros_like(domain);root_unknown[max(0,ry0-y0):ry1-y0,max(0,rx0-x0):rx1-x0]=True;root_unknown&=domain
  visible=domain&(cloth|outline)&~ribbon&~guide&~root_unknown;unknown=domain&(ribbon|guide|root_unknown);unsupported=domain&~(visible|unknown)
  white=(rgb.min(2)>=243)&(chroma<=12);seeds=np.zeros_like(white);seeds[0]=white[0];seeds[-1]=white[-1];seeds[:,0]=white[:,0];seeds[:,-1]=white[:,-1];exterior=ndi.binary_propagation(seeds,mask=white)
  arrays.update({name+'_domain':domain,name+'_visible':visible,name+'_outline':domain&outline&~cloth,name+'_occluded_unknown':unknown,name+'_root_unknown':root_unknown,name+'_unsupported_color':unsupported,name+'_support':visible|unknown,name+'_foreground':~exterior})
  labels,n=ndi.label(visible|unknown);ys,xs=np.where(visible|unknown)
  views[name]={'measured_contour':edges,'visible_pixels':int(visible.sum()),'occluded_unknown_pixels':int(unknown.sum()),'manual_root_unknown_pixels':int(root_unknown.sum()),'unsupported_color_pixels':int(unsupported.sum()),'domain_pixels':int(domain.sum()),'domain_components':int(n),'component_sizes':sorted(np.bincount(labels.ravel())[1:].tolist(),reverse=True),'bbox_xyxy':([int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0+1),int(ys.max()+y0+1)] if len(xs) else None),'row_intervals':[{'y':int(y+y0),'runs':[[aa+x0,b+x0] for aa,b in runs((visible|unknown)[y])]} for y in np.where((visible|unknown).any(1))[0]]}
 deps=[{'role':k,'path':str(p.relative_to(REPO)),'sha256':sha(p)} for k,p in [('semantic_correspondence_and_priors',P),('alignment',REPO/A['alignment_contract']),('extractor_surface_adapter',Path(__file__))]]
 m={'schema':'riverstone.measured_visible_surface.v1','source_pixel_sha256':rawsha(source),'source_status':'approved_original' if np.array_equal(source,SOURCE) else 'TEST_ONLY_pixel_mutation','source_file_sha256':A['source_sha256'] if np.array_equal(source,SOURCE) else None,'approved_parent_sha256':A['source_sha256'],'dependencies':deps,'views':views,'arrays_digest':digest({k:rawsha(v) for k,v in arrays.items()})}
 return m,arrays

def save_measurement(m,arrays):
 np.savez_compressed(BASE/'evidence/measurements.npz',**arrays);m['arrays_file_sha256']=sha(BASE/'evidence/measurements.npz');gzwrite(BASE/'evidence/measurements.json.gz',m)

def load_measurement():
 if not (BASE/'evidence/measurements.json.gz').is_file():raise ValueError('Measured input is mandatory')
 m=gzread(BASE/'evidence/measurements.json.gz');assert sha(BASE/'evidence/measurements.npz')==m['arrays_file_sha256'];arrays={k:v for k,v in np.load(BASE/'evidence/measurements.npz').items()};validate(m,arrays,SOURCE);return m,arrays

def validate(m,a,source):
 if not m or m.get('schema')!='riverstone.measured_visible_surface.v1':raise ValueError('Independent measurement required')
 if rawsha(source)!=m['source_pixel_sha256']:raise ValueError('Wrong source pixels')
 if digest({k:rawsha(v) for k,v in a.items()})!=m['arrays_digest']:raise ValueError('Measured arrays changed')
 for dep in m['dependencies']:
  if sha(REPO/dep['path'])!=dep['sha256']:raise ValueError('Stale measured dependency '+dep['role'])

def vertex_domain(mask):
 ys,xs=np.where(mask);vertex=set()
 for y,x in zip(ys,xs):
  for dx,dy in ((0,0),(1,0),(1,1),(0,1)):vertex.add((int(x+F['crop'][0]+dx),int(y+F['crop'][1]+dy)))
 nodes=sorted(vertex,key=lambda p:(p[1],p[0]));lookup={p:i for i,p in enumerate(nodes)};faces=[]
 for y,x in zip(ys,xs):
  x+=F['crop'][0];y+=F['crop'][1];q=[lookup[(x+dx,y+dy)] for dx,dy in ((0,0),(1,0),(1,1),(0,1))];faces.extend([(q[0],q[1],q[2]),(q[0],q[2],q[3])])
 return np.array(nodes,float),np.array(faces,int),lookup

def solve_surface(m,a,yaw=75):
 mask=a['front_support'];nodes,faces,lookup=vertex_domain(mask)
 if not len(nodes):raise ValueError('Empty measured front domain')
 sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit'];angle=math.radians(yaw);xx=(nodes[:,0]-F['axis_u'])*SCALE;yy=(F['sole_y']-nodes[:,1])*SCALE;bounds=[];row_records=[];missing=[]
 # Bounds on vertices come from adjacent native side pixel rows; these are measurement uncertainty cells, not enlarged garment thickness.
 for x,y in zip(xx,yy):
  sy=sv['sole_y']-y/ss;rr=[i for i in {int(math.floor(sy)),int(math.ceil(sy))-1} if 0<=i<a['side_support'].shape[0]];spans=[]
  for py in rr:spans.extend(runs(a['side_support'][py]))
  if not spans:missing.append(float(sy));bounds.append([np.nan,np.nan]);continue
  u0=min(p[0] for p in spans)+sv['crop'][0];u1=max(p[1] for p in spans)+sv['crop'][0];lo=(math.cos(angle)*x-(u1-sv['axis_u'])*ss)/math.sin(angle);hi=(math.cos(angle)*x-(u0-sv['axis_u'])*ss)/math.sin(angle);bounds.append([lo,hi]);row_records.append([float(sy),float(u0),float(u1)])
 if missing:raise ValueError('Candidate corresponding side flap has no support for '+str(len(missing))+' vertices; no fallback to whole skirt')
 bounds=np.array(bounds);n=len(nodes);edges=set()
 for tri in faces:
  for i,j in zip(tri,np.roll(tri,-1)):
   # Native horizontal/vertical edges only; triangulation direction must not bias the depth prior.
   if np.sum(abs(nodes[i]-nodes[j]))==1:edges.add(tuple(sorted((int(i),int(j)))))
 edges=sorted(edges);er=np.repeat(np.arange(len(edges)),2);ec=np.array(edges).ravel();E=sparse.csr_matrix((np.tile([-1.,1.],len(edges)),(er,ec)),shape=(len(edges),n));L=E.T@E;deg=np.asarray(abs(E).sum(0)).ravel();N=sparse.diags(1/np.maximum(deg,1))@L
 cfg=A['surface_prior'];target=bounds.mean(1);guide=np.zeros(n);gw=np.zeros(n)
 # Identifiable upper free-edge segments 0..2 only. This optional boundary-to-boundary match is explicitly a correspondence PRIOR, not a point observation.
 for e in m['views']['front']['measured_contour']:
  if e['segment']>2 or e['status']!='measured_edge':continue
  x,y=e['xy_px'];dist=(nodes[:,0]-x)**2+(nodes[:,1]-y)**2;i=int(dist.argmin())
  if dist[i]<=3:guide[i]=bounds[i,0];gw[i]=cfg['outer_edge_correspondence_weight']
 wd,wt,wc=cfg['data_weight'],cfg['tangent_weight'],cfg['curvature_weight']
 def fun(z):
  d=z-target;t=E@z;c=N@z;g=z-guide;val=wd*(d@d)+wt*(t@t)+wc*(c@c)+np.dot(gw,g*g);grad=2*(wd*d+wt*(E.T@t)+wc*(N.T@c)+gw*g);return float(val),np.asarray(grad)
 fit=minimize(fun,target,jac=True,bounds=bounds,method='L-BFGS-B',options={'maxiter':cfg['max_solver_iterations'],'ftol':1e-13,'gtol':1e-6,'maxls':40,'maxcor':8});z=fit.x;vertices=np.stack([xx,yy,z],1)
 zz=z[faces];slope=[]
 for i,j in edges:slope.append(abs(z[i]-z[j])/SCALE)
 return vertices,faces,{'yaw_degrees_hypothesis':yaw,'solver_success':bool(fit.success),'solver_message':str(fit.message),'iterations':int(fit.nit),'objective':float(fit.fun),'maximum_side_bound_violation_m':float(max(np.max(bounds[:,0]-z),np.max(z-bounds[:,1]),0)),'depth_extent_m':[float(z.min()),float(z.max())],'depth_bounds_digest':digest(rounded(bounds.tolist())),'max_neighbor_depth_slope':float(max(slope)),'rms_neighbor_depth_slope':float(np.sqrt(np.mean(np.array(slope)**2))),'source_vertices':len(nodes),'source_triangles':len(faces),'source_four_connected_components':int(ndi.label(mask)[1]),'missing_support_vertices':0,'source_pixel_nodes':nodes.astype(int).tolist(),'solved_vertex_z_m':rounded(z.tolist()),'bound_intervals_m':rounded(bounds.tolist()),'outer_edge_prior_vertex_count':int((gw>0).sum()),'surface_is_visible_patch_not_complete_panel':True}

def triangle_prism(p,ident,material,thick):
 p=np.array(p);u=p[1]-p[0];u/=np.linalg.norm(u);n=np.cross(p[1]-p[0],p[2]-p[0]);n/=np.linalg.norm(n);v=np.cross(n,u)
 return {'id':ident,'part':A['region_id'],'action':'paint','material':material,'shape':{'kind':'extrusion','polygon':[[float((q-p[0])@u),float((q-p[0])@v)] for q in p],'z_min':-thick/2,'z_max':thick/2,'minimum_cells':0},'transform':{'translation':p[0].tolist(),'basis':np.stack([u,v,n],1).tolist()}}

def make_master(m,a,source,vertices,faces):
 cfg=A['color'];mats={}
 for name,key in [('outer','front_white_roi'),('underside','front_underside_roi')]:
  x0,y0,x1,y1=cfg[key];rgb=np.median(source[y0:y1,x0:x1].reshape(-1,3),0).round().astype(int);mats[name]={'color':'#'+''.join(f'{v:02x}' for v in rgb)}
 # Keep one coherent outer surface material. The underside sample is recorded,
 # not splattered into common cells according to a single-view shading map.
 ops=[]
 for i,tri in enumerate(faces):
  px=int(round(vertices[tri,0].min()/SCALE+F['axis_u']));py=int(round(F['sole_y']-vertices[tri,1].max()/SCALE));ops.append(triangle_prism(vertices[tri],f'pixel_x{px}_y{py}_t{i%2}','outer',A['surface_prior']['normal_representation_thickness_m']))
 return rounded({'schema':'riverstone.voxel.master.v1','id':'measured_corresponding_flap05','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':mats,'components':[{'id':'flap','parts':[{'id':A['region_id'],'pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'asset','component':'flap'}],'constraints':[{'id':'nonempty','kind':'nonempty','minimum_cells':1}],'extensions':{'source_status':m['source_status'],'source_sha256':m['source_file_sha256'],'actual_source_pixels_sha256':m['source_pixel_sha256'],'approved_parent_sha256':A['source_sha256'],'measurement_arrays_digest':m['arrays_digest'],'measurement_dependencies_digest':digest(m['dependencies']),'generator_sha256':sha(__file__),'correspondence_and_priors_sha256':sha(P),'art_approved':False,'complete_panel':False}})

def build(m,a,source,yaw=75):
 validate(m,a,source);v,f,fit=solve_surface(m,a,yaw);ma=make_master(m,a,source,v,f);ma['extensions']['active_side_yaw_hypothesis_deg']=yaw;return ma,v,f,fit

def run():
 start=time.monotonic();m,a=extract(SOURCE);save_measurement(m,a);ma,v,f,fit=build(m,a,SOURCE);gzwrite(BASE/'generated/panel_master.json.gz',ma);np.savez_compressed(BASE/'generated/continuous_surface.npz',vertices=v,triangles=f);gzwrite(BASE/'evidence/surface_fit.json.gz',fit)
 write(BASE/'evidence/build_resources.json',{'operations':len(ma['components'][0]['operations']),'runtime_seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'surface_components':fit['source_four_connected_components'],'status':'partial source surface, common compile not yet checked'})
 print(json.dumps({k:fit[k] for k in fit if k not in ['source_pixel_nodes','solved_vertex_z_m','bound_intervals_m']}));print('bytes',sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
if __name__=='__main__':run()
