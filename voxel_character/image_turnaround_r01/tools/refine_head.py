"""Pixel-supported jaw/cheek and rounded skull constraint, with labelled hidden prior."""
import numpy as np

def refine_head(profiles,records,im,mask,p,annotation):
 scale=1.82/(p['front_floor_y']-p['front_scalp_y']);spec=annotation['head'];evidence=[];byid={q['id']:q for q in records};head=profiles['head']
 # The unknown rear cranium is a smooth depth prior, not the visible cheek patch.
 cranium=byid['cranium']['world_section'];base_depth=cranium[4];base_center=cranium[0]
 for index,(row,record) in enumerate(zip(head,[q for q in records if q['id'] in spec['sections']])):
  name=record['id'];rule=spec['sections'][name];y=record['samples'][0]['row_y'];old=list(row);samples=[]
  if name in ['scalp_tip','scalp_upper','cranium']:
   spans=[]
   for v,axis in [('front',p['front_axis_u']),('side',p['side_axis_u'])]:
    lo,hi=rule[v];rgb=im[y-1:y+2,lo:hi].astype(float);take=mask[y-1:y+2,lo:hi]&(rgb.max(2)-rgb.min(2)<spec['hair_chroma_max'])
    if spec['hair_luminance_max']<255:take&=rgb.mean(2)<spec['hair_luminance_max']
    xs=np.where(take.any(0))[0];runs=np.split(xs,np.where(np.diff(xs)>1)[0]+1);runs=[a for a in runs if len(a)>1]
    if runs:
     run=np.concatenate(runs);a,b=int(run.min()+lo),int(run.max()+lo+1)
    else:a,b=lo,hi
    spans.append((a,b));samples.append({'view':v,'row_y':y,'ROI':[lo,hi],'pixel_span':[a,b],'status':'foreground/hair-color outer span; gaps from ornament/highlights retained inside volume; ROI is manual constraint'})
   (a,b),(c,d)=spans;row[0]=(a+b-2*p['front_axis_u'])*scale/2;row[2]=(2*p['side_axis_u']-c-d)*scale/2;row[3]=max(.008,(b-a)*scale*.44);row[4]=max(.008,(d-c)*scale*.435)
   if name=='scalp_tip':row[0]=base_center;row[2]=cranium[2];row[3]=row[4]=.006
   if name=='cranium':base_depth=row[4];base_center=row[0]
  else:
   spans=[]
   for v in ['front','side']:
    lo,hi=rule[v];rgb=im[y-1:y+2,lo:hi].astype(float);take=(rgb[:,:,0]>rgb[:,:,2]+13)&(rgb[:,:,0]>rgb[:,:,1]+6)&(rgb.mean(2)>100);xs=np.where(take.any(0))[0]
    a,b=(int(xs.min()+lo),int(xs.max()+lo+1)) if len(xs)>1 else (lo,hi);spans.append((a,b));samples.append({'view':v,'row_y':y,'ROI':[lo,hi],'pixel_span':[a,b],'status':'warm skin pixels within manually annotated face-only interval; occluded side is not measured'})
   (a,b),(c,d)=spans;row[0]=(a+b-2*p['front_axis_u'])*scale/2;row[3]=max(rule['min_half_width_m'],(b-a)*scale/2*rule['hidden_width_allowance']);front=(p['side_axis_u']-c)*scale;rear=cranium[2]-base_depth*rule['rear_cranium_fraction'];row[2]=(front+rear)/2;row[4]=(front-rear)/2
  record['previous_curved05_world_section']=old;record['world_section']=list(row);record['refinement_evidence']=samples;record['hidden_shape_prior']=rule;evidence.append({'id':name,'samples':samples,'world_section':list(row),'manual_prior':rule})
 return evidence
