from field_source import *
from scipy.optimize import minimize
from audit_loft_winding import fixed

def run():
 start=time.monotonic();m,a,src,q,b=inputs();hp=BASE/'data/head_interval_contract.json';h=read(hp);old=read(ROOT/'full01/data/volume_annotations_v03.json')['parts'][0];faces={name:polygons_mask(a[name+'_face_skin'].shape,C['views'][name]['crop'],[h['visible_face_search_polygons'][name]])&a[name+'_face_skin']for name in ['front','side']};fy=np.arange(54,239,h['source_step_px']);fy=np.r_[fy,239.];N=len(fy);D=np.diff(np.eye(N),n=2,axis=0);profiles={};report=[]
 for name in ['front','side']:
  vw=C['views'][name];box=old[name];mask=(a[name+'_hair_eligible']|a[name+'_face_skin'])&boxes_mask(a[name+'_face_skin'].shape,vw['crop'],[box]);py=vw['sole_y']-(C['views']['front']['sole_y']-fy);bounds=[];observed=[]
  for row in py:
   rr=int(np.clip(round(row),0,mask.shape[0]-1));xs=np.flatnonzero(mask[rr])+vw['crop'][0]
   if not len(xs):
    avail=np.flatnonzero(mask.any(1));rr=int(avail[np.argmin(abs(avail-row))]);xs=np.flatnonzero(mask[rr])+vw['crop'][0]
   lo,hi=float(xs.min()),float(xs.max()+1);skin=np.flatnonzero(faces[name][rr])+vw['crop'][0];center=(lo+hi)/2
   if len(skin):innerlo,innerhi=float(skin.min()),float(skin.max()+1)
   else:innerlo=innerhi=center
   bounds.append([[lo,min(hi,innerlo)],[max(lo,innerhi),hi]]);observed.append({'requested_y_px':float(row),'actual_y_px':rr,'outer_pixels':[lo,hi],'visible_face_pixels':[innerlo,innerhi] if len(skin) else None})
  bounds=np.array(bounds);result=[]
  for k in range(2):
   low,high=bounds[:,k,0],bounds[:,k,1];target=(low+high)/2;chin=h['landmarks_manual_observed'][name+'_chin'][0];low[-1]=high[-1]=target[-1]=chin
   # Crown upper outer contour is observed; hidden cap stays inside that bound.
   target[0]=low[0] if k==0 else high[0]
   def fun(x):
    delta=x-target;dd=D@x;return float(dd@dd+h['gauge_weight']*(delta@delta)),2*D.T@dd+2*h['gauge_weight']*delta
   res=minimize(fun,np.clip(target,low,high),jac=True,bounds=list(zip(low,high)),method='L-BFGS-B',options={'maxiter':1000,'ftol':1e-12,'gtol':1e-8});result.append(res.x);report.append({'view':name,'support':k,'success':bool(res.success),'iterations':int(res.nit),'bounds_violation_px':float(max((low-res.x).max(),(res.x-high).max(),0)),'second_difference_rms_px':float(np.sqrt(np.mean((D@res.x)**2)))})
  profiles[name]={'rows':observed,'supports':np.array(result).T.tolist()}
 fit=volume.support_solver(24,h['side_yaw_deg']);sections=[]
 for j,y in enumerate(fy[:-1]):
  fs=profiles['front']['supports'][j];ss=profiles['side']['supports'][j];xl,xh=[(x-C['views']['front']['axis_u'])*SCALE for x in fs];ul,uh=[(u-C['views']['side']['axis_u'])*SCALE for u in ss];poly,center,minimum=fit(xl,xh,ul,uh);ym=(C['views']['front']['sole_y']-y)*SCALE;sections.append({'polygon_xz_m':poly,'center_xz_m':center,'world_y_range':[ym-.001,ym+.001],'source_y_px':float(y)})
 # A tiny cross-section approaching observed chin closes the inferred skull.
 x=(h['landmarks_manual_observed']['front_chin'][0]-C['views']['front']['axis_u'])*SCALE;u=(h['landmarks_manual_observed']['side_chin'][0]-C['views']['side']['axis_u'])*SCALE;z=(math.cos(math.radians(75))*x-u)/math.sin(math.radians(75));eps=.0001;poly=[[x-eps,z-eps],[x+eps,z-eps],[x+eps,z+eps],[x-eps,z+eps]];y=(C['views']['front']['sole_y']-239)*SCALE;sections.append({'polygon_xz_m':poly,'center_xz_m':[x,z],'world_y_range':[y-.0001,y+.0001],'source_y_px':239})
 profile={'id':'head_cap_closed','sections':sections};v,f=fixed(profile);rgb=before.surface_rgb(v,f,src,a,'head_cap_closed');np.savez_compressed(BASE/'generated/head_interval_trial.npz',v0=v,f0=f,c0=rgb);gzwrite(BASE/'evidence/head_interval_measurement.json.gz',{'contract_sha256':sha(hp),'profiles':profiles,'sections':sections,'optimization':report,'manual_search_polygons':h['visible_face_search_polygons']});out={'status':'HEAD_TRIAL_ONLY_NOT_FULL_MASTER_APPROVED','source_sha256':sha(BASE/'generated/head_interval_trial.npz'),'input_measurement_sha256':sha(BASE/'evidence/head_interval_measurement.json.gz'),'script_sha256':sha(__file__),'vertices':len(v),'triangles':len(f),'optimization':report,'unchanged_body_cloth_hair_geometry':True,'hair_field_occlusion_prior_uses_old_head':'Must re-evaluate if new head is selected; no claim of same new whole-master dependency','seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence/head_interval_trial.json',out);print(json.dumps(out))
if __name__=='__main__':run()
