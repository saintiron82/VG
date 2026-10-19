"""Visibility-specific gauges, conservative whole-side bounds, same thin surface.
No visible side polygon is treated as the full hidden material domain.
"""
from width_measurements import *

def solve_chart(v,f,pixels,i,a,shared,zfront,source):
    K,physical=pd.physical_operator(v,f);reg=prev.A['regularization'];lo,hi,extra=base.side_interval_world(v,a)
    gauge_array=a;gauge_label='whole-side interval midpoint; unknown panel depth'
    if i in [5,6]:gauge_array={**a,'side_support':a[f'lining_{i}_side_candidate']};gauge_label='separate measured visible lining candidate; provisional identity, midpoint prior only'
    elif i<10 and f'chart_{i}_side' in a:gauge_array={**a,'side_support':a[f'chart_{i}_side']};gauge_label='provisional visible side chart midpoint prior, not hidden surface bound'
    gl,gh,gextra=base.side_interval_world(v,gauge_array);prior=np.clip((gl+gh)/2,lo,hi)
    width_ids=np.array([],int);width_target=np.array([]);width_weight=A['width_correspondence']['boundary_width_prior_weight'];width_valid=None
    if i in A['width_correspondence']['charts']:
        width_z,width_edge,width_valid=width_prior(v,pixels,i,a);prior[width_valid]=np.clip(width_z[width_valid],lo[width_valid],hi[width_valid]);width_ids=np.flatnonzero(width_edge);width_target=width_z[width_ids];gauge_label='Measured two-edge projected-width correspondence + explicit monotone interior prior; no constant-side-u midpoint collapse'
    bd=base.edges_and_boundary(f)[1];obs=a.get(f'height_constraints_{i}',np.empty((0,10)));ids=np.array([],int);low=high=mid=np.array([])
    if len(obs):
        distance,near=cKDTree(obs[:,:2]).query(pixels[bd]);keep=distance<=prev.A['matching']['front_vertex_to_observed_edge_radius_px'];ids=bd[keep];rows=obs[near[keep]];low,high,mid=rows[:,2],rows[:,3],rows[:,4]
    seam_ids=[];seam_z=[]
    if i==10:
        for index in bd:
            key=tuple(np.round(pixels[index],6))
            if key not in shared:continue
            px,py=map(int,key);patch=source[max(0,py-1):py+1,max(0,px-1):px+1].astype(float)
            if float(np.sqrt(np.mean(np.var(patch.reshape(-1,3),axis=0))))<=pd.A['inferred_seam']['max_rgb_edge_rms']:
                seam_ids.append(index);seam_z.append(float(np.mean(shared[key])))
    seam_ids=np.array(seam_ids,int);seam_z=np.array(seam_z);S=None;upper=None
    if i==11:S,upper,coord=pd.overlap_operator(v,f,zfront)
    gauge=A['width_correspondence']['interior_gauge_weight'] if i in A['width_correspondence']['charts'] else reg['gauge_weight'];weight=reg['observed_interval_violation_weight'];mw=reg['observed_interval_midpoint_prior_weight'];sw=reg['shared_native_boundary_prior_weight'];rw=pd.A['depth_correction']['rear_soft_constraint_weight']
    diag=2*K.diagonal()+2*gauge
    if len(width_ids):np.add.at(diag,width_ids,2*width_weight)
    if len(ids):np.add.at(diag,ids,2*weight+2*mw)
    if len(seam_ids):np.add.at(diag,seam_ids,2*sw)
    if S is not None:diag+=2*rw*np.asarray(S.multiply(S).sum(axis=0)).ravel()
    scale=np.sqrt(np.maximum(diag,1e-12))
    def fun_scaled(u):
        z=u/scale;diff=z-prior;kz=K@z;value=float(z@kz+gauge*(diff@diff));grad=2*kz+2*gauge*diff
        if len(ids):
            za=z[ids];under=np.minimum(za-low,0);over=np.maximum(za-high,0);md=za-mid;value+=weight*(under@under+over@over)+mw*(md@md);np.add.at(grad,ids,2*weight*(under+over)+2*mw*md)
        if len(width_ids):
            d=z[width_ids]-width_target;value+=width_weight*(d@d);np.add.at(grad,width_ids,2*width_weight*d)
        if len(seam_ids):
            d=z[seam_ids]-seam_z;value+=sw*(d@d);np.add.at(grad,seam_ids,2*sw*d)
        if S is not None:
            pen=np.maximum(S@z-upper,0);value+=rw*(pen@pen);grad+=2*rw*(S.T@pen)
        return float(value),grad/scale
    result=minimize(fun_scaled,prior*scale,jac=True,bounds=list(zip(lo*scale,hi*scale)),method='L-BFGS-B',options={'maxiter':A['geometry_policy']['max_solver_iterations'],'ftol':reg['ftol'],'gtol':reg['gtol'],'maxcor':8});z=result.x/scale
    grad=fun_scaled(result.x)[1]*scale;pg=grad.copy();pg[(z<=lo+1e-10)&(grad>0)]=0;pg[(z>=hi-1e-10)&(grad<0)]=0
    report={'chart':i,'width_boundary_prior_constraints':len(width_ids),'width_correspondence_valid_vertices':int(width_valid.sum()) if width_valid is not None else 0,'width_boundary_prior_max_error_m':float(abs(z[width_ids]-width_target).max()) if len(width_ids) else None,'solver_success':bool(result.success),'message':str(result.message),'iterations':int(result.nit),'preconditioner':'Jacobi diagonal of curvature+constraint upper Hessian; objective unchanged by variable scaling',
      'projected_unscaled_gradient_max':float(abs(pg).max()),'hard_bounds':'whole measured side support only, no same-panel identity claim','gauge':gauge_label,
      'whole_bound_height_extrapolation_max_px':extra,'gauge_height_extrapolation_max_px':gextra,'observed_interval_constraints':len(ids),'inferred_shared_boundary_constraints':len(seam_ids),
      'side_bound_violation_m':float(max((lo-z).max(),(z-hi).max(),0)),
      'observed_interval_max_violation_m':float(np.maximum(low-z[ids],z[ids]-high).clip(0).max()) if len(ids) else None,
      'z_extent_m':[float(z.min()),float(z.max())],'physical_curvature':physical}
    if S is not None:
        impossible=np.maximum(S@lo-upper,0);pen=np.maximum(S@z-upper,0);report.update({'ordering_samples':len(upper),'infeasible_separation_samples':int((impossible>1e-6).sum()),'violating_separation_over1mm':int((pen>.001).sum()),'maximum_separation_violation_m':float(pen.max()),'rear_ahead_over1mm_samples':int((pen>.026).sum())})
    v[:,2]=z;return v,report,bd

def build(m,a,source):
    validate(m,a,source);verts=[];faces=[];charts=[];pixels=[];report=[];shared={};offset=0;zf=None
    for i in range(12):
        v,f,pp,mesh=base.triangulate(a[f'owned_{i}'],C['views']['back'] if i==11 else F)
        if i==11:zf=pd.depth_image(np.array(verts),np.array(faces,int))
        v,q,bd=solve_chart(v,f,pp,i,a,shared,zf,source)
        if i<10:
            for k in bd:shared.setdefault(tuple(np.round(pp[k],6)),[]).append(float(v[k,2]))
        verts.extend(v);faces.extend(f+offset);charts.extend([i]*len(f));pixels.extend(pp);offset+=len(v);report.append(q)
    return np.array(verts),np.array(faces,int),np.array(charts,int),np.array(pixels),report

def run():
    t=time.monotonic();m,a=load();v,f,ch,pp,report=build(m,a,SOURCE);np.savez_compressed(BASE/'generated/continuous_costume.npz',vertices=v,triangles=f,charts=ch,primary_pixels=pp);write(BASE/'evidence/source_fit.json',report)
    out={'status':'SOURCE07 measured full-width sections; hidden curvature and correspondence conditional','vertices':len(v),'triangles':len(f),'source_sha256':sha(BASE/'generated/continuous_costume.npz'),
      'fitter_sha256':sha(__file__),'measurement_sha256':sha(BASE/'evidence/measurement.json.gz'),'contract_sha256':sha(P),
      'solver_success_charts':sum(q['solver_success'] for q in report),'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
      'normal_thickness_m':.025,'new_body_face_hair_or_skin':False,'GPU_rig_socket':False};write(BASE/'evidence/build.json',out);print(json.dumps(out))

if __name__=='__main__':run()
