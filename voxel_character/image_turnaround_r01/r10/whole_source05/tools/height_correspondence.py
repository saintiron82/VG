"""Actual edge observations with height-consistent, semantic-segment intervals.

The sheet has no calibrated material-point matches. Matching and curvature are
explicit conditional priors. All measured pixel domains/holes remain unchanged.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'whole_source04/tools'))
import physical_depth as pd
from physical_depth import *
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;P=BASE/'data/correspondence_contract.json';A=read(P)

def phase_of(segment,spec):
    corners=spec['phase_corner_indices'];n=len(spec['contour_search_vertices'])
    for k,start in enumerate(corners):
        end=corners[(k+1)%len(corners)];end=end if end>start else end+n
        if any(j%n==segment for j in range(start,end)):return k
    raise ValueError('Missing semantic segment phase')

def pair_constraints(q,spec):
    if 'side' not in q['views']:return np.empty((0,10)),{'status':'UNKNOWN: no same-panel side boundary','observed_front_points':q['views']['front']['observed_gradient_points'],'matched_front_observations':0}
    obs=[r for r in q['views']['front']['boundary'] if r['status']=='measured_edge']
    side=[r for r in q['views']['side']['boundary'] if r['status']=='measured_edge']
    sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit'];match=A['matching'];out=[];unknown=0
    for index,r in enumerate(obs):
        px,py=r['xy_px'];x=(px-F['axis_u'])*SCALE;y=(F['sole_y']-py)*SCALE
        sy=sv['sole_y']-y/ss;phase=phase_of(r['segment'],spec['views']['front'])
        eligible=[s for s in side if phase_of(s['segment'],spec['views']['side'])==phase and abs(s['xy_px'][1]-sy)<=match['aligned_height_tolerance_px']]
        if not eligible:unknown+=1;continue
        us=np.array([s['xy_px'][0] for s in eligible]);dy=np.array([s['xy_px'][1]-sy for s in eligible]);err=match['edge_localization_uncertainty_px'];theta=math.radians(match['nominal_side_yaw_deg'])
        nominal=(math.cos(theta)*x-(us-sv['axis_u'])*ss)/math.sin(theta)
        lo=(math.cos(theta)*x-(us.max()+err-sv['axis_u'])*ss)/math.sin(theta)
        hi=(math.cos(theta)*x-(us.min()-err-sv['axis_u'])*ss)/math.sin(theta)
        uncertain=[]
        for yaw in [*match['side_yaw_uncertainty_deg'],match['nominal_side_yaw_deg']]:
            t=math.radians(yaw)
            for u in [us.min()-err,us.max()+err]:uncertain.append((math.cos(t)*x-(u-sv['axis_u'])*ss)/math.sin(t))
        out.append([px,py,lo,hi,float(np.median(nominal)),min(uncertain),max(uncertain),float(np.max(abs(dy))),phase,len(eligible)])
    result=np.array(out,float).reshape((-1,10))
    return result,{'status':'CONDITIONAL observed edges + manual semantic phase identity; no exact material-point correspondence',
      'observed_front_points':len(obs),'observed_side_points':len(side),'matched_front_observations':len(result),
      'unmatched_observed_front_points_unknown':unknown,'manual_front_points_excluded':q['views']['front']['manual_unobserved_points'],
      'manual_side_points_excluded':q['views']['side']['manual_unobserved_points'],
      'height_disagreement_max_px':float(result[:,7].max()) if len(result) else None,
      'nominal_depth_interval_width_p50_max_mm':(np.percentile(result[:,3]-result[:,2],[50,100])*1000).tolist() if len(result) else None,
      'camera_uncertainty_interval_width_p50_max_mm':(np.percentile(result[:,6]-result[:,5],[50,100])*1000).tolist() if len(result) else None}

def extract(source):
    pm,a=pd.extract(source);curves=pm['base_measurement']['previous_measured_curves']['charts'];reports=[]
    for i,(q,spec) in enumerate(zip(curves,previous.A['charts'])):
        a[f'height_constraints_{i}'],report=pair_constraints(q,spec);reports.append({'chart':i,'id':q['id'],**report})
    return {'schema':'riverstone.height_interval_measurement.v1','actual_pixel_sha256':rawsha(source),'source_file_sha256':pm['source_file_sha256'],
      'source_status':pm['source_status'],'previous_measurement':pm,'matching':reports,
      'arrays_digest':digest({k:rawsha(v) for k,v in a.items()}),
      'dependencies':pm['dependencies']+[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in [P,Path(__file__)]]},a

def validate(m,a,source):
    if not m or m.get('schema')!='riverstone.height_interval_measurement.v1':raise ValueError('Independent actual height-correspondence measurements required')
    if m['actual_pixel_sha256']!=rawsha(source):raise ValueError('Wrong source pixels')
    if m['arrays_digest']!=digest({k:rawsha(v) for k,v in a.items()}):raise ValueError('Changed measured arrays')
    for dep in m['dependencies']:
        if sha(REPO/dep['path'])!=dep['sha256']:raise ValueError('Changed dependency '+dep['path'])

def fit_depth(v,f,pixels,i,a,shared,zfront,source):
    K,physical=pd.physical_operator(v,f);reg=A['regularization'];prior_label='whole-side conservative admissible interval, unknown same-panel identity'
    aa=a
    if i in [5,6]:aa={**a,'side_support':a['side_inner_candidate']};prior_label='restricted side inner-cloth region, identity unknown'
    elif i<10 and f'chart_{i}_side' in a:aa={**a,'side_support':a[f'chart_{i}_side']};prior_label='provisional same-panel actual side candidate'
    lo,hi,extra=base.side_interval_world(v,aa);prior=(lo+hi)/2;ids=[];low=[];high=[];mid=[]
    bd=base.edges_and_boundary(f)[1];observed=a.get(f'height_constraints_{i}',np.empty((0,10)))
    if len(observed):
        distance,near=cKDTree(observed[:,:2]).query(pixels[bd]);keep=distance<=A['matching']['front_vertex_to_observed_edge_radius_px'];ids=bd[keep];rows=observed[near[keep]];low,high,mid=rows[:,2],rows[:,3],rows[:,4]
    ids=np.array(ids,int);low=np.array(low);high=np.array(high);mid=np.array(mid)
    seam_ids=[];seam_z=[]
    if i==10:
        for index in bd:
            key=tuple(np.round(pixels[index],6))
            if key not in shared:continue
            px,py=map(int,key);patch=source[max(0,py-1):py+1,max(0,px-1):px+1].astype(float)
            if float(np.sqrt(np.mean(np.var(patch.reshape(-1,3),axis=0))))<=pd.A['inferred_seam']['max_rgb_edge_rms']:
                seam_ids.append(index);seam_z.append(float(np.mean(shared[key])))
    seam_ids=np.array(seam_ids,int);seam_z=np.array(seam_z)
    S=None;upper=None
    if i==11:S,upper,coords=pd.overlap_operator(v,f,zfront)
    def fun(z):
        d=z-prior;kz=K@z;value=float(z@kz+reg['gauge_weight']*(d@d));grad=2*kz+2*reg['gauge_weight']*d
        if len(ids):
            za=z[ids];under=np.minimum(za-low,0);over=np.maximum(za-high,0);md=za-mid;w=reg['observed_interval_violation_weight'];mw=reg['observed_interval_midpoint_prior_weight'];value+=w*(under@under+over@over)+mw*(md@md);np.add.at(grad,ids,2*w*(under+over)+2*mw*md)
        if len(seam_ids):
            d=z[seam_ids]-seam_z;w=reg['shared_native_boundary_prior_weight'];value+=w*(d@d);np.add.at(grad,seam_ids,2*w*d)
        if S is not None:
            pen=np.maximum(S@z-upper,0);w=pd.A['depth_correction']['rear_soft_constraint_weight'];value+=w*(pen@pen);grad+=2*w*(S.T@pen)
        return float(value),grad
    result=minimize(fun,prior,jac=True,bounds=list(zip(lo,hi)),method='L-BFGS-B',options={'maxiter':reg['max_solver_iterations'],'ftol':reg['ftol'],'gtol':reg['gtol'],'maxcor':8});z=result.x
    fit={'chart':i,'solver_success':bool(result.success),'message':str(result.message),'iterations':int(result.nit),
      'side_bound_identity':prior_label,'side_row_extrapolation_max_px':extra,'observed_boundary_interval_constraints':len(ids),
      'inferred_shared_boundary_constraints':len(seam_ids),'all_vertex_side_bound_max_violation_m':float(max((lo-z).max(),(z-hi).max(),0)),
      'observed_interval_max_violation_m':float(np.maximum(low-z[ids],z[ids]-high).clip(0).max()) if len(ids) else None,
      'z_extent_m':[float(z.min()),float(z.max())],'physical_curvature':physical}
    if S is not None:
        impossible=np.maximum(S@lo-upper,0);pen=np.maximum(S@z-upper,0);fit.update({'ordering_samples':len(upper),'infeasible_separation_samples':int((impossible>1e-6).sum()),'violating_separation_over1mm':int((pen>.001).sum()),'maximum_separation_violation_m':float(pen.max()),'rear_ahead_over1mm_samples':int((pen>.026).sum())})
    v[:,2]=z;return v,fit,bd

def build(m,a,source):
    validate(m,a,source);verts=[];faces=[];charts=[];pixels=[];reports=[];offset=0;shared={};zf=None
    for i in range(12):
        v,f,pp,mesh=base.triangulate(a[f'owned_{i}'],C['views']['back'] if i==11 else F)
        if i==11:zf=pd.depth_image(np.array(verts),np.array(faces,int))
        v,fit,bd=fit_depth(v,f,pp,i,a,shared,zf,source)
        if i<10:
            for index in bd:shared.setdefault(tuple(np.round(pp[index],6)),[]).append(float(v[index,2]))
        verts.extend(v);faces.extend(f+offset);charts.extend([i]*len(f));pixels.extend(pp);offset+=len(v);reports.append(fit)
    return np.array(verts),np.array(faces,int),np.array(charts,int),np.array(pixels),reports

def load():
    m=gzread(BASE/'evidence/measurement.json.gz');a=dict(np.load(BASE/'evidence/measurement.npz'));assert sha(BASE/'evidence/measurement.npz')==m['arrays_file_sha256'];validate(m,a,SOURCE);return m,a

def run():
    start=time.monotonic();m,a=extract(SOURCE);np.savez_compressed(BASE/'evidence/measurement.npz',**a);m['arrays_file_sha256']=sha(BASE/'evidence/measurement.npz');gzwrite(BASE/'evidence/measurement.json.gz',m)
    v,f,ch,pp,report=build(m,a,SOURCE);np.savez_compressed(BASE/'generated/continuous_costume.npz',vertices=v,triangles=f,charts=ch,primary_pixels=pp);write(BASE/'evidence/source_fit.json',report)
    out={'status':'SOURCE ONLY, correspondence/curvature assumptions explicit; not art approved','matching':m['matching'],'triangles':len(f),'vertices':len(v),'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence/build.json',out);print(json.dumps(out))

if __name__=='__main__':run()
