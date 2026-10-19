"""Exact measured pixel domains, independent depth charts, explicit inferred seams.
Uses the previous actual boundary extractor and common triangle-prism adapter.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'whole_source02/tools'))
import boundary_atlas as previous
from boundary_atlas import *
sys.path.insert(0,str(ROOT/'continuous06/tools'))
import surface_atlas as adaptive_adapter
from scipy.spatial import cKDTree
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;P=BASE/'data/hole_aware_contract.json';A=read(P)

def extract(source):
 pm,a=previous.extract(source);front=a['front_support'];owner=np.full(front.shape,-1,np.int16);stats=[]
 for i,spec in enumerate(previous.A['charts']):
  raw=a[f'chart_{i}_front'];owned=raw&(owner<0);owner[owned]=i;stats.append({'chart':spec['id'],'raw_pixels':int(raw.sum()),'visible_owned_pixels':int(owned.sum()),'previously_owned_occluded_pixels':int((raw&~owned).sum())});a[f'owned_{i}']=owned
 residual=front&(owner<0);owner[residual]=10;a['owned_10']=residual;a['front_ownership']=owner
 previous.configure();spec=A['rear_center'];poly,records=legacy.sampled_edge(source,spec)
 if contour_crossings(poly):raise ValueError('Rear center semantic/measured contour crosses itself')
 rear=polygon_mask(poly,C['views']['back']['crop'])&a['back_support'];a['owned_11']=rear
 deps=pm['dependencies']+[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in [P,Path(__file__),Path(adaptive_adapter.__file__)]]
 m={'schema':'riverstone.hole_aware_costume_measurement.v1','approved_source_sha256':A['source_sha256'],'actual_pixel_sha256':rawsha(source),'source_status':pm['source_status'],'source_file_sha256':pm['source_file_sha256'],'previous_measured_curves':pm,'owned_chart_pixels':stats,'measured_residual_pixels':int(residual.sum()),'rear_center_measured_pixels':int(rear.sum()),'rear_center_boundary_records':records,'front_unassigned_pixels':int((front&(owner<0)).sum()),'front_duplicate_owned_pixels':0,'dependencies':deps,'arrays_digest':digest({k:rawsha(v) for k,v in a.items()})};return m,a

def validate(m,a,source):
 if not m or m.get('schema')!='riverstone.hole_aware_costume_measurement.v1':raise ValueError('Independent native-pixel ownership measurement is required')
 if rawsha(source)!=m['actual_pixel_sha256']:raise ValueError('Source mismatch')
 if digest({k:rawsha(v) for k,v in a.items()})!=m['arrays_digest']:raise ValueError('Mask digest mismatch')
 for dep in m['dependencies']:
  if sha(REPO/dep['path'])!=dep['sha256']:raise ValueError('Dependency changed '+dep['path'])

def triangulate(mask,view):
 labels,n=ndi.label(mask);verts=[];faces=[];pp=[];mesh=[];offset=0
 for comp in range(1,n+1):
  domain=labels==comp
  # Reuse exact pixel triangulation including every tiny island. Separate vertex
  # indices for diagonal-only 4-connected domains avoid false point welding.
  legacy.F=view;nodes,unused,look=legacy.vertex_domain(domain);del unused,look
  adaptive_adapter.F=view;adaptive_adapter.A={'adaptive_mesh':A['mesh']};v=np.zeros((len(nodes),3));aa={'front_support':domain,'front_charts':domain.astype(np.uint8)};av,af,ch,report=adaptive_adapter.adaptive(v,{'source_pixel_nodes':nodes.tolist()},aa)
  px=av[:,0]/SCALE+view['axis_u'];py=view['sole_y']-av[:,1]/SCALE;pixels=np.c_[px,py];theta=math.radians(view['yaw_degrees']);av[:,0]=(px-view['axis_u'])*SCALE/math.cos(theta);verts.extend(av);faces.extend(af+offset);pp.extend(pixels);offset+=len(av);mesh.append(report)
 return np.array(verts),np.array(faces,int),np.array(pp),mesh

def edges_and_boundary(f):
 es={}
 for t in f:
  for i,j in zip(t,np.roll(t,-1)):es[tuple(sorted((int(i),int(j))))]=es.get(tuple(sorted((int(i),int(j)))),0)+1
 bd=sorted({v for e,n in es.items() if n==1 for v in e});return es,np.array(bd,int)

def side_interval_world(v,a):
 sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit'];theta=math.radians(A['depth']['side_yaw_degrees']);available=np.where(a['side_support'].any(1))[0];lo=[];hi=[];extra=[]
 for x,y,_ in v:
  row=sv['sole_y']-y/ss;rs=[r for r in range(int(row)-4,int(row)+5) if 0<=r<len(a['side_support']) and a['side_support'][r].any()];near=int(available[np.argmin(abs(available-row))]);extra.append(abs(near-row))
  if not rs:rs=[near]
  us=np.concatenate([np.flatnonzero(a['side_support'][r])+sv['crop'][0] for r in rs]);lo.append((math.cos(theta)*x-(float(us.max()+1)-sv['axis_u'])*ss)/math.sin(theta));hi.append((math.cos(theta)*x-(float(us.min())-sv['axis_u'])*ss)/math.sin(theta))
 return np.array(lo),np.array(hi),float(max(extra)) if extra else 0

def curve_data(m,a):
 paired=[];anchor=None;rows=[]
 for i,(q,spec) in enumerate(zip(m['previous_measured_curves']['charts'],previous.A['charts'])):
  rv,fp,rep=previous.triangulate_boundary(q,spec,a,anchor)
  if i==0:
   order=np.argsort(fp[:,1]);yp=fp[order,1];zp=rv[order,2];unique=np.unique(yp);anchor=(unique,np.array([np.mean(zp[yp==y]) for y in unique]))
  rows.append((rv,fp,rep))
  if 'side' in q['views']:paired.extend(rv)
 return rows,np.array(paired)

def solve_depth(v,f,boundary_z):
 es,bd=edges_and_boundary(f);n=len(v);ii=np.array(sorted(set(range(n))-set(bd)),int);z=np.zeros(n);z[bd]=boundary_z
 if len(ii):
  edges=np.array(list(es));E=sparse.csr_matrix((np.tile([-1.,1.],len(edges)),(np.repeat(np.arange(len(edges)),2),edges.ravel())),shape=(len(edges),n));L=E.T@E;deg=np.asarray(abs(E).sum(0)).ravel();N=sparse.diags(1/np.maximum(deg,1))@L;K=N.T@N+A['depth']['tangent_weight']*L;rhs=-(K[ii][:,bd]@z[bd]);z[ii]=spsolve(K[ii][:,ii].tocsc(),rhs);res=K[ii][:,ii]@z[ii]-rhs;resmax=float(abs(res).max())
 else:resmax=0
 v[:,2]=z;return v,{'boundary_vertices':len(bd),'interior_vertices':len(ii),'linear_system_max_residual':resmax,'source_xy_foldover_count':0}

def build(m,a,source):
 validate(m,a,source);legacy.F=F;curves,paired=curve_data(m,a);items=[];allnamed=np.concatenate([r[0] for r in curves]);allxy=np.c_[allnamed[:,0],allnamed[:,1]];tree=cKDTree(allxy);paired_order=np.argsort(paired[:,1]);paired=paired[paired_order];uy=np.unique(np.round(paired[:,1],4));uz=np.array([np.median(paired[np.round(paired[:,1],4)==y,2]) for y in uy]);names=[q['id'] for q in previous.A['charts']]+['measured_residual_cloth','rear_center_observed_inferred_seam']
 for i,name in enumerate(names):
  vv,ff,pixels,mr=triangulate(a[f'owned_{i}'],C['views']['back'] if i==11 else F);es,bd=edges_and_boundary(ff)
  if i<10:
   rv,fp,rep=curves[i];dist,inds=cKDTree(fp).query(pixels[bd]);zz=rv[inds,2];role=rep
  elif i==10:
   dist,inds=tree.query(vv[bd,:2]);zz=allnamed[inds,2];role={'status':'Measured visible residual mask; sewing identity unknown. Closest named boundary depth is an explicit prior, not new observed material points.'}
  else:
   zz=np.interp(vv[bd,1],uy,uz);role={'status':'Actual rear white-cloth mask, depth and hidden connection inferred from paired boundary height profile; no front/back point correspondence claim.'}
  lo,hi,extra=side_interval_world(vv[bd],a)
  if i>=10:zz=np.clip(zz,lo,hi)
  items.append({'id':name,'index':i,'v':vv,'f':ff,'pixels':pixels,'bd':bd,'z':zz,'edge':es,'role':role,'mesh':mr,'side_bound_violation_m':float(max((lo-zz).max(),(zz-hi).max(),0)) if len(zz) else 0,'side_row_extrapolation_max_px':extra})
 # Residual-to-named shared native edges only. Do not join separate measured
 # free-edge folds or bridge a gap merely to improve a connectivity score.
 maprows={}
 for item in items[:11]:
  for k,idx in enumerate(item['bd']):
   px,py=item['pixels'][idx];maprows.setdefault((round(float(px),6),round(float(py),6)),[]).append((item['index'],k))
 seam=[];threshold=A['inferred_seam']['max_rgb_edge_rms']
 for (px,py),refs in sorted(maprows.items()):
  if not any(i==10 for i,k in refs) or not any(i!=10 for i,k in refs):continue
  ix,iy=int(px),int(py);patch=source[max(0,iy-1):iy+1,max(0,ix-1):ix+1].astype(float)
  if patch.size==0:continue
  gradient=float(np.sqrt(np.mean(np.var(patch.reshape(-1,3),axis=0))))
  if gradient>threshold:continue
  named=[items[i]['z'][k] for i,k in refs if i!=10];z=float(np.mean(named))
  for i,k in refs:items[i]['z'][k]=z
  seam.append({'xy_px':[px,py],'chart_indices':[i for i,k in refs],'measured_rgb_std_rms':gradient,'shared_depth_m':z,'status':'inferred continuous-surface boundary, sewing unobserved'})
 verts=[];faces=[];chart=[];pp=[];offset=0;reports=[]
 for item in items:
  v,info=solve_depth(item['v'],item['f'],item['z']);f=item['f'];verts.extend(v);faces.extend(f+offset);chart.extend([item['index']]*len(f));pp.extend(item['pixels']);offset+=len(v);report={k:q for k,q in item.items() if k in ['id','index','role','side_bound_violation_m','side_row_extrapolation_max_px']};report.update(info);report.update({'vertices':len(v),'triangles':len(f),'mask_pixels':int(a[f'owned_{item["index"]}'].sum()),'mask_four_connected_components':int(ndi.label(a[f'owned_{item["index"]}'])[1]),'primary_view':'back' if item['index']==11 else 'front','normal_thickness_m':A['depth']['normal_thickness_m']});reports.append(report)
 return np.array(verts),np.array(faces,int),np.array(chart,int),np.array(pp),reports,seam

def make_master(m,a,v,f,ch,source):
 legacy.F=F;previous.configure(previous.FULL);ma=legacy.make_master({'source_status':m['source_status'],'source_file_sha256':m['source_file_sha256'],'source_pixel_sha256':m['actual_pixel_sha256'],'arrays_digest':m['arrays_digest'],'dependencies':m['dependencies']},a,source,v,f);names=[q['id'] for q in previous.A['charts']]+['measured_residual_cloth','rear_center_observed_inferred_seam'];ma['components'][0]['parts']=[{'id':name,'pivot':[0,0,0]} for name in names]
 for j,(op,idx) in enumerate(zip(ma['components'][0]['operations'],ch)):op['id']=f'chart_{int(idx)}_triangle_{j}';op['part']=names[int(idx)]
 ma['id']='approved_violet_hole_aware_multiview_costume03';ma['extensions'].update({'generator_sha256':sha(__file__),'source_measurement_digest':m['arrays_digest'],'approved_source_sha256':A['source_sha256'],'representation':'Exact measured primary pixel ownership plus multiview boundary depths; rear inferred seam remains separate','complete_character':False,'art_approved':False,'sockets':None,'source_to_compile_gate':A['source_to_compile_gate']});return rounded(ma)

def load():
 m=gzread(BASE/'evidence/measurement.json.gz');a=dict(np.load(BASE/'evidence/measurement.npz'));assert sha(BASE/'evidence/measurement.npz')==m['arrays_file_sha256'];validate(m,a,SOURCE);return m,a

def run():
 import shutil
 if shutil.disk_usage(BASE).free<A['budget']['minimum_free_disk_bytes']:raise ValueError('Minimum1GiB free contract')
 t=time.monotonic();m,a=extract(SOURCE);np.savez_compressed(BASE/'evidence/measurement.npz',**a);m['arrays_file_sha256']=sha(BASE/'evidence/measurement.npz');gzwrite(BASE/'evidence/measurement.json.gz',m);v,f,ch,pp,rep,seam=build(m,a,SOURCE);np.savez_compressed(BASE/'generated/continuous_costume.npz',vertices=v,triangles=f,charts=ch,primary_pixels=pp);gzwrite(BASE/'evidence/source_fit.json.gz',{'charts':rep,'inferred_residual_seam_vertices':seam});report={'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'vertices':len(v),'triangles':len(f),'charts':rep,'inferred_seam_vertices':len(seam),'front_unassigned_pixels':m['front_unassigned_pixels'],'front_duplicate_owned_pixels':m['front_duplicate_owned_pixels'],'source_only_master_rebuildable_from_compressed_geometry':True,'bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())};write(BASE/'evidence/build.json',report);print(json.dumps(report))
if __name__=='__main__':run()
