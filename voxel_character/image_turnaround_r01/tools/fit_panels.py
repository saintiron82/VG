"""Bounded four-parameter fit to three-view lower-cloth pixel envelopes.

The panel correspondence/curves remain an explicit authored hypothesis. This
fits their width/depth envelope; it does not infer unseen folds from pixels.
"""
from pathlib import Path
import argparse,hashlib,json,math
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy.optimize import differential_evolution
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fit(aid):
 r=read(ROOT/'data/shared_rules.json');p=read(ROOT/'data'/(aid+'_preset.json'));ann=next(x for x in read(ROOT/'data/measurement_annotations.json')['assets'] if x['id']==aid);im=np.asarray(Image.open((ROOT/'data'/ann['sheet']).resolve()).convert('RGB')).astype(float);scale=1.82/(p['front_floor_y']-p['front_scalp_y']);heights=[.13,.30,.48,.66,.80];targets=[];records=[]
 for y in heights:
  py=round(p['front_floor_y']-y/scale);intervals=[]
  for view in ann['views']:
   x0,_,x1,_=view['crop'];crop=im[py-2:py+3,x0:x1];bright=crop.mean(2);sat=crop.max(2)-crop.min(2);colored=(np.linalg.norm(crop-np.array([215,215,218]),axis=2)>20)&(bright>165)&(sat<84);xs=np.where(colored.any(0))[0]
   if not len(xs):raise ValueError('empty cloth cross-view sample')
   lo,hi=int(xs.min()+x0),int(xs.max()+x0);axis=view['manual_axis_u'];world=[(lo-axis)*scale,(hi-axis)*scale]
   if view['name'] in ['right','back']:world=[-world[1],-world[0]]
   intervals.append(world);records.append({'view':view['name'],'world_y_m':y,'pixel_row':py,'pixel_span':[lo,hi],'world_span_m':world,'measurement':'bright low-saturation foreground pixels within view crop; lower-cloth heuristic, not semantic ground truth'})
  targets.append([(intervals[0][0]+intervals[2][0])/2,(intervals[0][1]+intervals[2][1])/2,*intervals[1]])
 targets=np.array(targets);samples=[]
 for panel in r['panels']:
  if panel['id']=='front_short_panel':continue
  rows=np.array(panel['profile']);t=np.linspace(0,len(rows)-1,34);u=np.linspace(-1,1,21);prof=np.column_stack([PchipInterpolator(np.arange(len(rows)),rows[:,i])(t) for i in range(3)]);tt=np.arange(len(t))/(len(t)-1);T,U=np.meshgrid(tt,u,indexing='ij');Y=prof[:,0,None]+panel['hem_wave']*T**3*(U**2-.35)+.04*np.sin(T*np.pi*3+U*1.2)*T;R=prof[:,1,None]+panel['bow']*np.sin(np.pi*T)*(1-U**2)+panel['curl']*T**5*np.cos(U*np.pi/2);W=U*prof[:,2,None];samples.append((panel['id'],panel['angle_deg'],Y.ravel(),R.ravel(),W.ravel(),T.ravel()))
 def envelopes(params):
  la,ra,xscale,zscale=params;xyz=[]
  for name,angle,y,rad,width,t in samples:
   if name=='left_petal':angle=-la
   elif name=='right_petal':angle=ra
   angle=math.radians(angle);x=(np.sin(angle)*rad+np.cos(angle)*width)*(1+(xscale-1)*t);z=(np.cos(angle)*rad-np.sin(angle)*width)*(1+(zscale-1)*t);xyz.append(np.column_stack([x,y,z]))
  points=np.concatenate(xyz);result=[]
  for y in heights:
   row=points[np.abs(points[:,1]-y)<.045];result.append([row[:,0].min(),row[:,0].max(),row[:,2].min(),row[:,2].max()])
  return np.array(result)
 def objective(params):
  residual=envelopes(params)-targets
  return float(np.mean(residual**2)+.00015*((params[2]-1)**2+(params[3]-1)**2))
 bounds=[(78,110),(78,110),(.82,1.18),(.70,1.15)];before=[72,69,1,1];result=differential_evolution(objective,bounds,seed=19,maxiter=35,popsize=8,polish=False,tol=.001);p['cloth_fit']={'left_angle_degrees':-float(result.x[0]),'right_angle_degrees':float(result.x[1]),'width_scale':float(result.x[2]),'depth_scale':float(result.x[3]),'method':'bounded fit to actual lower-cloth front+back lateral and side depth envelopes','targets_m':targets.tolist(),'heights_m':heights,'measured_samples':records,'bounds':bounds,'mean_absolute_envelope_error_m_before':float(np.abs(envelopes(before)-targets).mean()),'mean_absolute_envelope_error_m_after':float(np.abs(envelopes(result.x)-targets).mean()),'side_back_status':'AI inferred design views, not observed original geometry','sheet_sha256':ann['sheet_sha256'],'fit_code_sha256':sha(Path(__file__))};(ROOT/'data'/(aid+'_fitted_preset.json')).write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'id':aid,'parameters':result.x.tolist(),'before_m':p['cloth_fit']['mean_absolute_envelope_error_m_before'],'after_m':p['cloth_fit']['mean_absolute_envelope_error_m_after']}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('asset',choices=['violet','cyan']);fit(a.parse_args().asset)
