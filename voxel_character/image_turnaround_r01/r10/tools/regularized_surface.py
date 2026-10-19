"""Thin continuous depth hypothesis from measured rows and explicit priors."""
from measured_panels import *
from scipy.optimize import lsq_linear
from verify_and_render import components,project,projections,raster,CPU_SOURCE
SURFACE=ROOT/'surface01';ASSUMPTIONS=SURFACE/'data/surface_assumptions.json'

def fit_surface(m,c):
 a=read(ASSUMPTIONS);sv=m['views']['side'];scale=c['alignment']['character_height_m_for_test']/sv['scale_px_per_unit'];theta=math.radians(sv['yaw_degrees']);bounds=[];observations=[]
 for row in m['sections']:
  spans=row['views']['side']['foreground_intervals_px']
  if not spans:raise ValueError('No side depth interval: surface cannot be generated without a declared constraint relaxation')
  u0,u1=max(spans,key=lambda p:(p[1]-p[0],-p[0]));lo=-(u1-sv['axis_u'])*scale/math.sin(theta);hi=-(u0-sv['axis_u'])*scale/math.sin(theta);bounds.append([lo,hi]);observations.append({'source_front_row':row['source_front_row'],'chosen_side_span_px':[u0,u1],'all_side_spans_px':spans,'f_bounds_m':[lo,hi]})
 bounds=np.array(bounds);mid=bounds.mean(1);n=len(mid);D=np.zeros((n-2,n))
 for i in range(n-2):D[i,i:i+3]=[1,-2,1]
 w=a['objective'];A=np.vstack((np.eye(n)*math.sqrt(w['mid_interval_weight']),D*math.sqrt(w['squared_second_difference_weight'])));b=np.r_[mid*math.sqrt(w['mid_interval_weight']),np.zeros(n-2)]
 result=lsq_linear(A,b,bounds=(bounds[:,0],bounds[:,1]),tol=1e-12,max_iter=200);f=result.x
 if not result.success:raise ValueError('Constrained minimum-bending solver failed: '+result.message)
 boundary=np.r_[f[0],(f[:-1]+f[1:])/2,f[-1]];master,_=geometry(m,c);ops=[];a_x=math.cos(theta)/math.sin(theta);thickness=a['normal_thickness_m'];fv=m['views']['front'];fs=m['metres_per_front_pixel'];traces=[]
 for i,row in enumerate(m['sections']):
  # Measured rows increase downward, so boundary[i] is the upper-Y edge.
  for label,spans in row['patch_intervals_px'].items():
   for k,(left,right) in enumerate(spans):
    xl,xh=(left-fv['axis_u'])*fs,(right-fv['axis_u'])*fs;ylo,yhi=row['y_min_m'],row['y_max_m'];p0=np.array([xl,ylo,a_x*xl+boundary[i+1]]);p1=np.array([xh,ylo,a_x*xh+boundary[i+1]]);p2=np.array([xh,yhi,a_x*xh+boundary[i]]);p3=np.array([xl,yhi,a_x*xl+boundary[i]]);e1=p1-p0;e1/=np.linalg.norm(e1);normal=np.cross(p1-p0,p3-p0);normal/=np.linalg.norm(normal);e2=np.cross(normal,e1);basis=np.stack((e1,e2,normal),axis=1);poly=[[float((p-p0)@e1),float((p-p0)@e2)] for p in (p0,p1,p2,p3)]
    ops.append({'id':f'row{row["source_front_row"]}_p{label}_r{k}','part':'patch_'+label,'action':'paint','material':'patch_'+label,'shape':{'kind':'extrusion','polygon':poly,'z_min':-thickness/2,'z_max':thickness/2,'minimum_cells':0},'transform':{'translation':p0.tolist(),'basis':basis.tolist()}})
 for edge in m['measured_fold_edges']:
  pts=[]
  for p in edge['measured_points']:
   if p['y_px'] is None:continue
   idx=p['y_px']-m['sections'][0]['source_front_row']
   if 0<=idx<len(f):
    x=(p['x_px']-fv['axis_u'])*fs;y=(fv['sole_y']-p['y_px']-.5)*fs;pts.append({'source_uv':[p['x_px'],p['y_px']],'surface_xyz_m':[x,y,a_x*x+float(f[idx])],'depth_status':'regularized inference, not observed fold depth'})
  traces.append({'id':edge['id'],'points':pts,'semantics':a['fold_semantics'].get(edge['id'])})
 master['id']='violet_r10_regularized_thin_surface01';master['components'][0]['operations']=ops;master['extensions'].update({'generator_sha256':sha(__file__),'surface_assumptions_sha256':sha(ASSUMPTIONS),'representation':a,'base_measured_generator_sha256':sha(ROOT/'tools/measured_panels.py'),'complete_garment_reconstruction':False})
 fit={'model':a['depth_model'],'f_row_centers_m':f.tolist(),'f_row_boundaries_m':boundary.tolist(),'side_x_slope':a_x,'solver_success':bool(result.success),'solver_cost':float(result.cost),'second_difference_energy':float(np.sum((D@f)**2)),'bounds_violation_m':float(max(0,np.max(bounds[:,0]-f),np.max(f-bounds[:,1]))),'observations':observations,'lifted_measured_fold_traces':traces,'semantic_limits':a['uncertainty']}
 return master,fit

def run():
 mp=ROOT/'generated/measured/measurements.json.gz';m,c=verify_measurement(mp);a=read(ASSUMPTIONS);master,fit=fit_surface(m,c);pre=preflight(m,c,master);write(SURFACE/'evidence/preflight.json',pre);gzwrite(SURFACE/'generated/master.json.gz',master);gzwrite(SURFACE/'generated/fitted_depth_and_fold_traces.json.gz',fit);print(json.dumps({'preflight':pre,'fit_bounds_violation':fit['bounds_violation_m']}))

if __name__=='__main__':run()
