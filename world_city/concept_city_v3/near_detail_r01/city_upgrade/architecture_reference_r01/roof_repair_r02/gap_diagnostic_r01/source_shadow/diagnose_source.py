#!/usr/bin/env python3
"""Read-only source/capture audit; outputs only this small diagnostic directory."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import csv, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'voxel_character/common/core.py').exists())
A=HERE.parents[2]
SRC=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
TILE=A/'roof_repair_r01/tile_measurement_r01/tile_regions.json'
CON=A/'reconstruction_proof_r01/roof_measurement_r01/measurement_contract.json'
CAP=A/'roof_repair_r02/actual_godot_r01/after'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def area(b):return (b[2]-b[0])*(b[3]-b[1])
def intersection(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def crop(b):return im[b[1]:b[3],b[0]:b[2]]
def chroma(a):
 a=a.astype(float);return (a[...,0]>a[...,1]*1.45)&(a[...,1]>a[...,2]*1.15)
def peaks(profile,distance,prominence):
 # Exact peak-selection algorithm from frozen r01 measure_tiles.py, copied not modified.
 v=-np.asarray(profile);candidates=[];i=1
 while i<len(v)-1:
  if v[i]>v[i-1]:
   j=i
   while j+1<len(v) and v[j+1]==v[i]:j+=1
   if j+1<len(v) and v[j]>v[j+1]:candidates.append((i+j)//2)
   i=j+1
  else:i+=1
 accepted=[]
 for i in sorted(candidates,key=lambda i:(-v[i],i)):
  if any(abs(i-j)<distance for j in accepted):continue
  lo=hi=float(v[i])
  for j in range(i-1,-1,-1):
   if v[j]>v[i]:break
   lo=min(lo,float(v[j]))
  for j in range(i+1,len(v)):
   if v[j]>v[i]:break
   hi=min(hi,float(v[j]))
  if float(v[i])-max(lo,hi)>=prominence:accepted.append(i)
 return [(i,float(np.asarray(profile)[max(0,i-3):min(len(v),i+4)].max()-profile[i])) for i in sorted(accepted)]
inputs=[SRC,TILE,CON,CAP/'top.png',CAP/'right.png']
before={str(p.relative_to(ROOT)):sha(p) for p in inputs}
t=json.loads(TILE.read_text());contract=json.loads(CON.read_text())
im=np.array(Image.open(SRC).convert('RGB'));assert im.shape==(1024,1536,3)
E=[865,795,925,879];P=[783,791,919,974];C=[868,795,908,849];shadow_test=[870,849,903,879]
s=contract['conditional_local_registration']['coefficients'];factor=s['sx']*s['sz']
strips=[x for x in t['strips'] if x['side']=='right' and intersection([*x['u_interval_px'][:1],791,x['u_interval_px'][1],974],E)]
# Original rejects are recorded before accepting any extension candidate.
rejected=[r for r in t['rejected_regions'] if r['reason']=='Intersects excluded ridge/chimney/shadow ROI' and intersection(r['bbox_px'],E)]
assert len(rejected)>0
safe=[r for r in rejected if not intersection(r['bbox_px'],C) and 5<=r['bbox_px'][3]-r['bbox_px'][1]<=21]
profiles=[];boundaries=[]
for strip in strips:
 u0,u1=strip['u_interval_px'];u=(u0+u1)//2;box=strip['local_v_profile_roi_px'];p=crop(box).mean(axis=(1,2));pk=peaks(p,6,10)
 assert [box[1]+v for v,q in pk]==strip['local_v_troughs_px']
 for v,q in pk:
  vv=box[1]+v
  if 849<=vv<889:
   window=p[max(0,v-3):min(len(p),v+4)];vvhi=box[1]+max(0,v-3)+int(window.argmax())
   boundaries.append({'strip_id':strip['id'],'source_trough_px':[u,vv],'source_trough_rgb':im[vv,u].tolist(),'three_column_mean_rgb_at_trough':round(float(p[v]),6),'local_contrast_mean_rgb':round(q,6),'nearby_high_px':[u,vvhi],'nearby_high_rgb':im[vvhi,u].tolist(),'profile_roi_px':box,'within_expanded_exclusion':E[0]<=u<E[2] and E[1]<=vv<E[3]})
 for k,val in enumerate(p):profiles.append([strip['id'],u,box[1]+k,round(float(val),6),*im[box[1]+k,u].tolist()])
regions=[]
for r in safe:
 b=r['bbox_px'];strip=next(s for s in strips if s['id']==r['strip']);u0,v0,u1,v1=b;ib=[u0+2,v0+1,u1-2,v1-1];a=crop(ib);f=a.reshape(-1,3).astype(float);good=chroma(a).reshape(-1)&(f[:,0]>90);ids=np.flatnonzero(good)
 if len(ids)<3:continue
 med=np.median(f[ids],axis=0);k=int(ids[np.argmin(((f[ids]-med)**2).sum(1))]);w=ib[2]-ib[0]
 q={v:q for v,q in zip(strip['local_v_troughs_px'],strip['local_v_strength'])}
 regions.append({'id':f"shadow_extension_{len(regions):02d}",'original_rejected_strip':r['strip'],'bbox_px':b,'u_boundary_support_roi_px':strip['u_profile_roi_px'],'u_boundary_strength_from_clear_roi':strip['u_edge_strength'],'v_boundary_strength': [q.get(v0,0),q.get(v1,0)],'all_endpoints_already_detected':v0 in q and v1 in q,'interior_bbox_px':ib,'terracotta_support_pixels':int(len(ids)),'interior_pixels':len(f),'median_rgb':med.tolist(),'actual_sample_px':[ib[0]+k%w,ib[1]+k//w],'actual_sample_rgb':f[k].astype(int).tolist(),'conditional_diagnostic_xz_bbox':[s['sx']*u0+s['tx'],s['sz']*v0+s['tz'],s['sx']*u1+s['tx'],s['sz']*v1+s['tz']],'use':'Appearance region candidate only; no observed relief or fully traced tile outline.'})
# Neutral-colored stone and opening are observed source content, not a physical footprint.
a=crop(C).astype(float);gray=(a.max(2)-a.min(2)<30)&(a[...,0]<a[...,1]*1.3);ys,xs=np.where(gray)
core_bbox=[int(xs.min()+C[0]),int(ys.min()+C[1]),int(xs.max()+C[0]+1),int(ys.max()+C[1]+1)]
gray_sensitivity={str(k):int(((a.max(2)-a.min(2)<k)&(a[...,0]<a[...,1]*1.3)).sum()) for k in [20,25,30,35,40]}
clipped=[max(E[0],P[0]),max(E[1],P[1]),min(E[2],P[2]),min(E[3],P[3])]
output={'schema':'riverstone.source_shadow_gap_diagnostic.v1','source_dependencies':before,'coordinate_convention':'Original unwarped source raster boxes [u0,v0,u1,v1). X/Z quantities are conditional planned-template coordinates, never physical survey or sloped surface area.','status':'SOURCE_APPEARANCE_EXTENSION_CANDIDATES_ONLY','original_global_registration_accepted':False,'brightness_to_height':False,'geometry_created':False,'compiler_invoked':False,'scope':{'expanded_exclusion_bbox_px':E,'safe_right_plane_bbox_px':P,'conservative_chimney_rim_face_box_px':C,'neutral_stone_opening_core_bbox_px':core_bbox,'explicit_shadow_test_bbox_px':shadow_test},'area_accounting':{'expanded_rectangle_pixels':area(E),'expanded_rectangle_conditional_xz_area':area(E)*factor,'within_safe_right_plane_pixels':area(clipped),'within_safe_right_plane_percent':100*area(clipped)/area(P),'within_safe_right_plane_conditional_xz_area':area(clipped)*factor,'conservative_chimney_box_pixels':area(C),'conservative_chimney_box_conditional_xz_area':area(C)*factor,'neutral_stone_opening_core_pixels':int(gray.sum()),'neutral_core_is_color_support_not_exact_semantic_silhouette':True,'remaining_within_plane_outside_conservative_chimney_box_pixels':area(clipped)-area(C),'whole_rejected_regions_count':len(rejected),'whole_rejected_regions_union_pixels':sum(area(r['bbox_px']) for r in rejected),'whole_rejected_regions_union_conditional_xz_area':sum(area(r['bbox_px']) for r in rejected)*factor,'rejected_region_pixels_inside_exclusion':sum(intersection(r['bbox_px'],E) for r in rejected),'extra_region_pixels_rejected_outside_exclusion':sum(area(r['bbox_px'])-intersection(r['bbox_px'],E) for r in rejected),'candidate_regions_count':len(regions),'candidate_regions_pixels':sum(area(r['bbox_px']) for r in regions),'candidate_region_pixels_within_exclusion':sum(intersection(r['bbox_px'],E) for r in regions),'candidate_regions_percent_of_safe_right_plane':100*sum(area(r['bbox_px']) for r in regions)/area(P),'candidate_regions_conditional_xz_area':sum(area(r['bbox_px']) for r in regions)*factor},'pixel_classification':{'neutral_stone_opening_threshold':'Within conservative box: max(R,G,B)-min(R,G,B)<30 and R<1.3G','neutral_threshold_sensitivity_counts':gray_sensitivity,'terracotta_chroma_threshold':'R>1.45G and G>1.15B; no brightness cutoff for chroma counts','expanded_exclusion_within_plane_terracotta_chroma_pixels':int(chroma(crop(clipped)).sum()),'shadow_test_pixels':area(shadow_test),'shadow_test_terracotta_chroma_pixels':int(chroma(crop(shadow_test)).sum()),'classification_caution':'Color support does not establish semantic correctness or exact occluder contour. The conservative box remains held out.'},'boundary_observations':boundaries,'minimal_extension_candidates':regions,'interpretation':{'observed':'Local V troughs and terracotta interiors remain detectable below the source chimney face and within the excluded shadow area. Reuse only source-supported intervals; do not invent regular rows.','conditional_u_edges':'Candidate U boundaries retain the r01 shared-strip assumption from clear v=884..963. They are not independently traced at every shadowed row.','occluded':'Roof appearance behind stone, dark chimney opening and apparent vertical face is not observed. Any concealed tile continuation requires an explicit continuity prior; TOP chimney placement remains a failed held-out metric correspondence.','global_flatness':'The exclusion clips 18.225 percent of the safe right source plane. It can explain a localized withheld patch, not by itself all broad flat right-roof appearance in frozen TOP and RIGHT captures. This report does not establish a renderer/capture pixel correspondence.','no_depth':'Shadow brightness, dark seams and the black opening never supply height or occupancy.','minimal_next_measurement_change':'Keep the conservative chimney/rim/face holdout [868,795,908,849), consider these 15 already-detected non-overlapping rejected regions after independent visual review, retain original U-strip approximation and source colors, and label any fill under the occluder as continuity prior rather than observation.'}}
assert len(regions)==15
assert all(not intersection(r['bbox_px'],C) for r in regions)
assert all(not intersection(a['bbox_px'],b['bbox_px']) for i,a in enumerate(regions) for b in regions[i+1:])
assert all(im[r['actual_sample_px'][1],r['actual_sample_px'][0]].tolist()==r['actual_sample_rgb'] for r in regions)
assert before=={str(p.relative_to(ROOT)):sha(p) for p in inputs}
output['validation']={'original_inputs_unchanged':True,'original_profile_troughs_reproduced':True,'candidate_regions_nonoverlapping':True,'candidate_occluder_box_intersections':0,'sample_colors_match_source_pixels':True,'frozen_capture_inputs_only':True}
(HERE/'diagnostic.json').write_text(json.dumps(output,indent=2)+'\n')
with (HERE/'source_profiles.csv').open('w') as f:
 writer=csv.writer(f);writer.writerow(['strip_id','source_u','source_v','three_column_mean_rgb','center_R','center_G','center_B']);writer.writerows(profiles)
assert sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())<1024*1024
print(json.dumps({'area_accounting':output['area_accounting'],'pixel_classification':output['pixel_classification'],'candidate_boxes':[r['bbox_px'] for r in regions],'validation':output['validation']},indent=2))
