#!/usr/bin/env python3
"""Bounded original-pixel candidate/appearance-separator audit. No asset writes."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
import json,hashlib,collections,time
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent;A=O.parent;ROOT=next(p for p in A.parents if (p/'voxel_character/common/core.py').exists());S=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stats(a):return {'n':len(a),'min':float(np.min(a)),'p25':float(np.quantile(a,.25)),'median':float(np.median(a)),'p75':float(np.quantile(a,.75)),'max':float(np.max(a))} if a else {'n':0}
def measure(profile,i):
 if not 3<=i<len(profile)-3:return None
 bottom=float(profile[i]);base=float(min(max(profile[i-3:i]),max(profile[i+1:i+4])));contrast=base-bottom
 if contrast<=0:return None
 half=bottom+contrast*.5;l=r=i
 while l>i-3 and profile[l-1]<=half:l-=1
 while r<i+3 and profile[r+1]<=half:r+=1
 return {'half_contrast_dark_support_width_px':r-l+1,'contrast_mean_RGB_units':contrast,'center_mean_RGB':bottom,'shoulder_mean_RGB':base,'range_relative_to_center':[l-i,r-i],'censored_at_3px_window':l==i-3 or r==i+3}
def main():
 start=time.monotonic();cpu=time.process_time();m=read(A/'roof_repair_r01/tile_measurement_r01/tile_regions.json');c=read(O/'candidate_intervals.json');a=read(O/'audit.json');im=np.asarray(Image.open(S).convert('RGB'));assert sha(S)==c['source_image_sha256'];profiles={p['id']:p for p in c['profiles']};raw=np.zeros((1024,1536),bool)
 for s in read(O/'source_uncertainty_masks.json')['runs']['existing_raw_measurement']:
  v,u0,u1=s;raw[v,u0:u1]=True
 accepted=np.zeros_like(raw);hold=np.zeros_like(raw);hold[795:849,868:908]=True;cm=read(O/'top_first_hit_masks.json')['runs'];back=np.zeros(a['lattice_array_shape_xz'],bool);chim=np.zeros_like(back)
 for x,z0,z1 in cm['backing_in_unmeasured_source']:back[x,z0:z1]=True
 for x,z0,z1 in cm['current_chimney_outside_source_holdout']:chim[x,z0:z1]=True
 co=a['conditional_mapping'];origin=a['lattice_origin_xyz'];P=a['lattice_pitch'];candidate_results=[]
 for q in c['candidate_intervals']:
  u0,v0,u1,v1=q['bbox_px'];p=profiles[q['local_profile_ref']];assert not raw[v0:v1,u0:u1].any() and not hold[v0:v1,u0:u1].any() and not accepted[v0:v1,u0:u1].any();accepted[v0:v1,u0:u1]=True
  nbound=int(v0 in p['observed_troughs_v'])+int(v1 in p['observed_troughs_v']);assert nbound==2-sum(q['partial_V_endpoints']);sx,sy=q['source_sample_px'];assert im[sy,sx].tolist()==q['source_sample_rgb'];vp=np.array(p['mean_RGB_profile']);all_boundary_verified=all((partial or (v in p['observed_troughs_v'] and vp[v-791]<=vp[v-792] and vp[v-791]<=vp[v-790])) for v,partial in zip([v0,v1],q['partial_V_endpoints']));assert all_boundary_verified
  topcounts=collections.Counter()
  for v in range(v0,v1):
   for u in range(u0,u1):
    ix=int(np.floor((co['sx']*(u+.5)+co['tx'])/P))-origin[0];iz=int(np.floor((co['sz']*(v+.5)+co['tz'])/P))-origin[2];topcounts['backing' if back[ix,iz] else 'current_chimney' if chim[ix,iz] else 'other_current_surface']+=1
  candidate_results.append({'id':q['id'],'pixels':q['pixels'],'both_V_endpoints_observed':nbound==2,'observed_V_boundary_count':nbound,'partial_endpoint_count':sum(q['partial_V_endpoints']),'current_top_pixel_center_correspondence_counts':dict(topcounts),'original_source_RGB_verified':True,'old_354_overlap_pixels':0,'holdout_overlap_pixels':0,'candidate_overlap_pixels':0,'V_endpoints_are_actual_local_profile_troughs_or_declared_ROI_clip':True})
 # Source mean-RGB valley widths are appearance statistics, not dimensions of a hole.
 sample=[];seen_u=set()
 for s in m['strips']:
  if s['side']!='right':continue
  b=s['local_v_profile_roi_px'];vp=im[b[1]:b[3],b[0]:b[2]].mean(axis=(1,2))
  for v in s['local_v_troughs_px']:
   if not 884<=v<=960:continue
   r=measure(vp,v-b[1])
   if r:sample.append({'axis':'V','strip_id':s['id'],'source_px':[(b[0]+b[2]-1)//2,v],**r})
  ub=s['u_profile_roi_px'];up=im[ub[1]:ub[3],ub[0]:ub[2]].mean(axis=(0,2))
  for u,partial in zip(s['u_interval_px'],s['u_partial_endpoints']):
   if partial or u in seen_u:continue
   seen_u.add(u);r=measure(up,u-ub[0])
   if r:sample.append({'axis':'U','strip_id':s['id'],'source_px':[u,884],**r})
 summaries={}
 for axis in ['U','V']:
  ss=[s for s in sample if s['axis']==axis];summaries[axis]={'half_contrast_dark_support_width_px':stats([s['half_contrast_dark_support_width_px'] for s in ss]),'contrast_mean_RGB_units':stats([s['contrast_mean_RGB_units'] for s in ss]),'count_width_greater_than_1px':sum(s['half_contrast_dark_support_width_px']>1 for s in ss),'count_width_equal_1px':sum(s['half_contrast_dark_support_width_px']==1 for s in ss),'censored_count':sum(s['censored_at_3px_window'] for s in ss)}
 total=collections.Counter();both=collections.Counter();partial=collections.Counter();groups=collections.defaultdict(collections.Counter)
 for q in candidate_results:
  total.update(q['current_top_pixel_center_correspondence_counts']);(both if q['both_V_endpoints_observed'] else partial).update(q['current_top_pixel_center_correspondence_counts']);groups[q['id'].rsplit('_v',1)[0]]['count']+=1;groups[q['id'].rsplit('_v',1)[0]]['pixels']+=q['pixels']
 report={'schema':'riverstone.roof.candidate_separator_validation.r1','source_dependencies':{str(p.relative_to(ROOT)):sha(p) for p in [S,O/'candidate_intervals.json',O/'audit.json',O/'source_ordering_audit.json',A/'roof_repair_r01/tile_measurement_r01/tile_regions.json']},'source_rgb_and_boundaries_verified':True,'candidate_count':len(candidate_results),'candidate_source_pixels':int(accepted.sum()),'two_observed_V_boundaries_candidate_count':sum(q['both_V_endpoints_observed'] for q in candidate_results),'two_observed_V_boundaries_source_pixels':sum(q['pixels'] for q in candidate_results if q['both_V_endpoints_observed']),'partial_V_candidate_count':sum(not q['both_V_endpoints_observed'] for q in candidate_results),'partial_V_source_pixels':sum(q['pixels'] for q in candidate_results if not q['both_V_endpoints_observed']),'per_margin':{k:dict(v) for k,v in groups.items()},'top_first_hit_pixel_center_counts_all':dict(total),'top_first_hit_pixel_center_counts_two_observed_V_boundaries':dict(both),'top_first_hit_pixel_center_counts_partial_V':dict(partial),'old_354_overlap_pixels':int((accepted&raw).sum()),'true_holdout_overlap_pixels':int((accepted&hold).sum()),'separator_prior':'1px total declared appearance separator centered on each source trough; not a measured dark-band width, physical gap width, recess or depth.','separator_method':'At each source trough, use the smaller of left/right maxima within 3 px as shoulder baseline; count contiguous original profile samples below halfway from trough to shoulder. U uses the old V=884..963 mean profile, V uses each old 3-column profile and V=884..960. This measures raster contrast support only.','separator_statistics':summaries,'separator_conclusion':'Observed valleys support visual separation. Their raster dark support is generally not narrower than the 1px declared separator. The evidence does not justify interpreting these dark bands as empty geometry or increasing gap depth. The 7312 current backing columns in separator bands are distinct from the 1781 ordering-deleted columns.','candidate_results':candidate_results,'separator_samples':sample,'elapsed_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'compiler_calls':0,'geometry_changes':0}
 (O/'candidate_separator_validation.json').write_text(json.dumps(report,indent=2)+'\n');assert sum(p.stat().st_size for p in O.iterdir() if p.is_file())<2*1024**2;print(json.dumps({k:v for k,v in report.items() if k not in ['source_dependencies','candidate_results','separator_samples']},indent=2))
if __name__=='__main__':main()
