"""Read-only raster measurements and uncertainty masks. Never authors geometry.
The semantic ROIs are declared annotations; pixel thresholds measure evidence
inside them, not hidden depth. No image warp, image generation or compiler.
"""
from pathlib import Path
import csv,hashlib,json,math,os,resource,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
def find_peaks(values,distance=1,prominence=0):
 # Bounded scalar profile analysis only. Same local-maximum/contour-prominence
 # definition; avoids importing the large SciPy stack into the AS256MiB job.
 values=np.asarray(values);candidates=[];i=1
 while i<len(values)-1:
  if values[i]>values[i-1]:
   end=i
   while end+1<len(values)and values[end+1]==values[i]:end+=1
   if end+1<len(values)and values[end]>values[end+1]:candidates.append((i+end)//2)
   i=end+1
  else:i+=1
 accepted=[]
 for i in sorted(candidates,key=lambda i:(values[i],i),reverse=True):
  if all(abs(i-j)>=distance for j in accepted):accepted.append(i)
 peaks=[];proms=[]
 for i in sorted(accepted):
  lowleft=lowright=float(values[i])
  for j in range(i-1,-1,-1):
   if values[j]>values[i]:break
   lowleft=min(lowleft,float(values[j]))
  for j in range(i+1,len(values)):
   if values[j]>values[i]:break
   lowright=min(lowright,float(values[j]))
  value=float(values[i])-max(lowleft,lowright)
  if value>=prominence:peaks.append(i);proms.append(value)
 return np.asarray(peaks,dtype=int),{'prominences':np.asarray(proms)}
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if(p/'voxel_character/common/core.py').exists());P=R/'world_city/reference/house_quality_photos_20261019/six_views_r01';Q=H.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def save(name,data):
 p=H/name;assert not p.exists();p.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n')
def bbox(mask,origin):
 ys,xs=np.where(mask);assert len(xs);return [int(xs.min()+origin[0]),int(ys.min()+origin[1]),int(xs.max()+origin[0]+1),int(ys.max()+origin[1]+1)]
def rle(mask):
 runs=[]
 for y,row in enumerate(mask):
  transitions=np.diff(np.r_[False,row,False].astype(np.int8));starts=np.flatnonzero(transitions==1);ends=np.flatnonzero(transitions==-1);runs.extend([[int(y),int(x),int(z)]for x,z in zip(starts,ends)])
 return {'true_pixels':int(mask.sum()),'runs_y_x0_x1':runs}

def measure():
 started=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(45,)*2)
 inputs=[P/'generated_candidate_r03.png',P/'registration_r03.json',P/'template.json',Q/'reconstruct.py',Q/'reprojection_limits.json'];deps={str(p.relative_to(R)):sha(p)for p in inputs};im=np.asarray(Image.open(inputs[0]).convert('RGB'),dtype=np.uint8);registration=json.loads(inputs[1].read_bytes());template=json.loads(inputs[2].read_bytes());assert im.shape==(1024,1536,3)
 rois={'top':[604,770,931,983],'front':[48,50,464,190],'back':[1074,50,1485,190],'right':[600,85,934,176],'left':[90,595,424,679]}
 chimney_rois={'top':[868,795,908,849],'front':[360,60,400,141],'back':[1136,60,1176,141],'right':[868,60,910,137],'left':[128,564,174,642]}
 def crop(box):x,y,z,w=box;return im[y:w,x:z]
 def red(box,ratio=1.7):a=crop(box);r,g,b=a.transpose(2,0,1);return (r>g*ratio)&(g>b*1.2)&(r>80)
 roof={}
 for view,box in rois.items():
  masks=[red(box,t)for t in [1.45,1.6,1.8]];bounds=[bbox(m,box[:2])for m in masks];roof[view]={'semantic_roi_px':box,'red_envelope_bbox_px':bbox(red(box),box[:2]),'threshold_ratio_sensitivity':{'ratios':[1.45,1.6,1.8],'bounds_px':bounds},'box_is_color_evidence_not_closed_surface':True}
 # Separate slope-sheet ends from the extended ridge cap. Quantiles describe
 # actual foreground per-column/row evidence, not a repaired template grid.
 topbox=rois['top'];tm=red(topbox);xo,yo=topbox[:2];top_ends=[];bottom_ends=[]
 for left,right in [(620,750),(785,860)]:
  for x in range(left,right):
   ys=np.flatnonzero(tm[:,x-xo]);top_ends.append(int(ys.min()+yo));bottom_ends.append(int(ys.max()+yo+1))
 left_ends=[];right_ends=[]
 for y in range(800,968):
  xs=np.flatnonzero(tm[y-yo]);left_ends.append(int(xs.min()+xo));right_ends.append(int(xs.max()+xo+1))
 rect=[float(np.median(left_ends)),float(np.median(top_ends)),float(np.median(right_ends)),float(np.median(bottom_ends))];ends={'left':left_ends,'back':top_ends,'right':right_ends,'front':bottom_ends};roof['top']['slope_outer_rectangle_median_px']=rect;roof['top']['edge_evidence_quantiles_px']={k:np.percentile(v,[0,10,50,90,100]).tolist()for k,v in ends.items()};roof['top']['ridge_cap_full_red_envelope_differs_from_slope_ends']=True
 grid_samples=[('top_rows',[586,778,606,990],1),('top_columns',[586,774,750,784],0),('front_rows',[67,55,80,140],1),('front_columns',[70,50,230,61],0)];grids={}
 for name,box,axis in grid_samples:
  profile=255-crop(box).mean(2).mean(axis=axis);peaks,properties=find_peaks(profile,distance=2,prominence=1.5);major=peaks[properties['prominences']>=25];offset=box[1]if axis else box[0];gaps=np.diff(major);minor=np.diff(peaks)
  grids[name]={'background_only_roi_px':box,'major_line_positions_px':(major+offset).tolist(),'major_intervals_px':gaps.tolist(),'mean_major_interval_px':float(gaps.mean())if len(gaps)else None,'median_minor_peak_interval_px':float(np.median(minor)),'detected_peaks':len(peaks),'criterion':'Mean RGB darkness profile; local peaks prominence>=25 for major lines, >=1.5 for minor evidence; no building pixels in annotated strips.'}
 fits=registration['diagnostic_affine_fits']['top'];affine=np.asarray(fits['template_to_output_affine']);a=affine[:2].T;t=affine[2];inv=np.linalg.inv(a)
 # Dimensions use the original elevation grid's planned32px/m convention.
 # They are diagnostic template units, not physical-photo survey metres.
 fb=roof['front']['red_envelope_bbox_px'];bb=roof['back']['red_envelope_bbox_px'];rb=roof['right']['red_envelope_bbox_px'];lb=roof['left']['red_envelope_bbox_px']
 front_x=[(fb[0]-256)/32,(fb[2]-256)/32];back_x=[(1280-bb[2])/32,(1280-bb[0])/32];right_z=[(768-rb[2])/32,(768-rb[0])/32];left_z=[(lb[0]-256)/32,(lb[2]-256)/32]
 target_x=np.mean([front_x,back_x],axis=0);target_z=np.mean([right_z,left_z],axis=0);sx=(target_x[1]-target_x[0])/(rect[2]-rect[0]);sz=(target_z[1]-target_z[0])/(rect[3]-rect[1]);tx=target_x[0]-sx*rect[0];tz=target_z[0]-sz*rect[1]
 def registered(u,v):return [sx*u+tx,sz*v+tz]
 corners=np.array([[rect[0],rect[1]],[rect[2],rect[3]]]);unwarped=(corners-t)@inv.T
 fit={'status':'CONDITIONAL_SEMANTIC_ROOF_RECTANGLE_ONLY_NOT_GLOBAL_REGISTRATION','free_parameters':4,'mapping':'diagnostic X=sx*pixel_u+tx; diagnostic Z=sz*pixel_v+tz','coefficients':{'sx':sx,'tx':tx,'sz':sz,'tz':tz},'anchors':{'front_tile_x_interval_diagnostic_m':front_x,'back_tile_x_interval_diagnostic_m':back_x,'right_tile_z_interval_diagnostic_m':right_z,'left_tile_z_interval_diagnostic_m':left_z,'target_x_interval_diagnostic_m':target_x.tolist(),'target_z_interval_diagnostic_m':target_z.tolist(),'top_slope_rectangle_px':rect},'fitted_target_dimensions_diagnostic_m':[(target_x[1]-target_x[0]),(target_z[1]-target_z[0])],'top_naive32px_dimensions_diagnostic_m':[(rect[2]-rect[0])/32,(rect[3]-rect[1])/32],'top_marker_inverse_only_dimensions_diagnostic_m':((unwarped[1]-unwarped[0])/32).tolist(),'pixel_scale_to_elevation_pixel_scale':[sx*32,sz*32],'front_back_width_disagreement_m':abs((front_x[1]-front_x[0])-(back_x[1]-back_x[0])),'left_right_depth_disagreement_m':abs((right_z[1]-right_z[0])-(left_z[1]-left_z[0])),'absolute_scale_is_planned_not_measured':True,'image_warp_performed':False,'fit_anchors_not_counted_as_independent_validation':True,'boundary_uncertainty_px':3}
 chimneys={}
 for view,box in chimney_rois.items():
  a0=crop(box);lum=a0.mean(2);chroma=np.ptp(a0,axis=2);rows=[]
  for threshold in [25,35,45]:
   mask=(chroma<threshold)&(lum>70)&(lum<205);ys,xs=np.where(mask);rows.append({'chroma_max':threshold,'bbox_px':bbox(mask,box[:2]),'x_percentiles_2_50_98_px':np.percentile(xs+box[0],[2,50,98]).tolist(),'y_percentiles_2_50_98_px':np.percentile(ys+box[1],[2,50,98]).tolist()})
  chimneys[view]={'roi_px':box,'threshold_sensitivity':rows,'representative_center_px':[rows[1]['x_percentiles_2_50_98_px'][1],rows[1]['y_percentiles_2_50_98_px'][1]],'gray_bbox_includes_visible_rim_sides_and_shadow_uncertainty':True}
 cf=chimneys['front']['representative_center_px'];cb=chimneys['back']['representative_center_px'];cr=chimneys['right']['representative_center_px'];cl=chimneys['left']['representative_center_px'];ct=chimneys['top']['representative_center_px'];chimney_x=[(cf[0]-256)/32,(1280-cb[0])/32];chimney_z=[(768-cr[0])/32,(cl[0]-256)/32];top_chimney=registered(*ct)
 chimney_check={'top_registered_observed_stone_center_diagnostic_xz_m':top_chimney,'front_back_center_x_diagnostic_m':chimney_x,'right_left_center_z_diagnostic_m':chimney_z,'front_back_x_disagreement_m':abs(chimney_x[0]-chimney_x[1]),'right_left_z_disagreement_m':abs(chimney_z[0]-chimney_z[1]),'top_x_residual_from_front_back_mean_m':top_chimney[0]-float(np.mean(chimney_x)),'top_z_residual_from_sides_mean_m':top_chimney[1]-float(np.mean(chimney_z)),'top_registered_bbox_size_m':[(chimneys['top']['threshold_sensitivity'][1]['bbox_px'][2]-chimneys['top']['threshold_sensitivity'][1]['bbox_px'][0])*sx,(chimneys['top']['threshold_sensitivity'][1]['bbox_px'][3]-chimneys['top']['threshold_sensitivity'][1]['bbox_px'][1])*sz],'pass_as_same_metric_chimney':False,'reason':'Held-out X offset exceeds the3px edge uncertainty by several times; side depths disagree and TOP stone lower edge may be a rendered vertical face or shadow. Do not turn these dark areas into depth.'}
 # Red gable upper silhouettes: retain tile scallops as residual rather than
 # flattening or claiming a unique analytic roof surface.
 gables={}
 for name,origin in [('front',0),('back',1024)]:
  box=rois[name];mask=red(box);lines=[]
  for low,high in [(70+origin,240+origin),(274+origin,440+origin)]:
   points=[]
   for x in range(low,high):
    ys=np.flatnonzero(mask[:,x-box[0]])
    if len(ys):points.append([x,float(ys[0]+box[1])])
   values=np.array(points);coef=np.polyfit(values[:,0],values[:,1],1);res=values[:,1]-np.polyval(coef,values[:,0]);lines.append({'fit_pixels_x_range':[low,high],'slope_px_per_px':float(coef[0]),'intercept_px':float(coef[1]),'residual_rms_px':float(np.sqrt(np.mean(res*res))),'max_residual_px':float(abs(res).max())})
  u=(lines[1]['intercept_px']-lines[0]['intercept_px'])/(lines[0]['slope_px_per_px']-lines[1]['slope_px_per_px']);v=lines[0]['slope_px_per_px']*u+lines[0]['intercept_px'];gables[name]={'left_right_upper_tile_envelope_fits':lines,'intersection_px':[u,v],'observed_red_ridge_min_y_px':roof[name]['red_envelope_bbox_px'][1]}
 ridge_band=[766,772];ridge_x_interval=[registered(x,rect[1])[0]for x in ridge_band];front_ridge_x=(gables['front']['intersection_px'][0]-256)/32;back_ridge_x=(1280-gables['back']['intersection_px'][0])/32
 ridge={'top_axis_pixel_u_band':ridge_band,'top_cap_strip_roi_px':[756,772,783,982],'registered_axis_x_interval_diagnostic_m':ridge_x_interval,'front_back_fitted_axis_x_m':[front_ridge_x,back_ridge_x],'front_back_red_ridge_y_px':[roof['front']['red_envelope_bbox_px'][1],roof['back']['red_envelope_bbox_px'][1]],'side_red_roof_top_y_px_front_origin':[roof['right']['red_envelope_bbox_px'][1],roof['left']['red_envelope_bbox_px'][1]-512],'side_vs_front_top_height_difference_px':[roof['right']['red_envelope_bbox_px'][1]-roof['front']['red_envelope_bbox_px'][1],roof['left']['red_envelope_bbox_px'][1]-512-roof['front']['red_envelope_bbox_px'][1]],'use':'axis orientation/central split is supported; cap width/height/end projection remains ambiguous','side_upper_height_not_accepted':True}
 tile_samples=[('left_plane_u',[620,860,748,953],0),('right_plane_u',[787,860,914,953],0),('left_plane_v',[640,800,742,968],1),('right_plane_v',[794,860,853,968],1),('right_side_v',[650,96,845,169],1)]
 tile_evidence={}
 for name,box,axis in tile_samples:
  profile=crop(box).mean(2).mean(axis=axis);peaks,properties=find_peaks(-profile,distance=4,prominence=3);offset=box[1]if axis else box[0];d=np.diff(peaks)
  tile_evidence[name]={'appearance_roi_px':box,'profile_axis':'v'if axis else'u','candidate_trough_positions_px':(peaks+offset).tolist(),'trough_prominences_rgb_units':properties['prominences'].tolist(),'intervals_px':d.tolist(),'median_interval_px':float(np.median(d)),'interval_coefficient_of_variation':float(np.std(d)/np.mean(d)),'interpretation':'appearance seam candidates, not per-tile3D boundaries or height samples'}
 # Six local examples use narrow columns; curved seams and threshold changes
 # prevent these raster intervals from becoming authoritative closed solids.
 tile_examples=[]
 for center in [637,671,704,809,843,889]:
  box=[center-1,860,center+2,955];profile=crop(box).mean(axis=(1,2));peaks,properties=find_peaks(-profile,distance=5,prominence=10);pairs=list(zip(peaks[:-1],peaks[1:]));pair=min(pairs,key=lambda pair:abs((pair[0]+pair[1])/2-35))if pairs else None
  if pair:tile_examples.append({'column_center_u_px':center,'profile_strip_px':box,'adjacent_seam_v_px':[int(pair[0]+860),int(pair[1]+860)],'local_tile_interval_observable':True,'closed_2d_tile_outline_proven':False,'3d_height_from_darkness_allowed':False})
 # Raw-coordinate overlapping masks, encoded as rows. No bitmap is generated.
 yy,xx=np.indices(tm.shape);xx+=xo;yy+=yo
 outer=(xx>=rect[0])&(xx<rect[2])&(yy>=rect[1])&(yy<rect[3]);inner=(xx>=rect[0]+3)&(xx<rect[2]-3)&(yy>=rect[1]+3)&(yy<rect[3]-3);ridge_mask=(xx>=756)&(xx<783)&(yy>=772)&(yy<982);chimney=(xx>=868)&(xx<908)&(yy>=795)&(yy<849);shadow_roi=(xx>=865)&(xx<925)&(yy>=795)&(yy<879);lum=crop(topbox).mean(2);dark=lum<85;opening=(xx>=878)&(xx<900)&(yy>=804)&(yy<832)&dark
 masks={'tile_color_appearance_only':inner&tm&~ridge_mask&~shadow_roi,'outer_edge_or_endcap_uncertain':(outer&~inner)|(tm&~outer),'ridge_axis_cap_geometry_uncertain':ridge_mask,'chimney_rim_footprint_and_vertical_face_ambiguous':chimney,'shadow_or_occlusion_no_depth':shadow_roi&dark,'dark_chimney_opening_no_depth':opening,'background_grid_excluded':~outer&~tm,'dark_seam_or_shadow_within_roof_no_depth':outer&dark}
 mask_report={'schema':'riverstone.raster_uncertainty_masks.v1','source_image':ref(inputs[0]),'roi_px':topbox,'encoding':'For each named overlapping boolean mask: [local_y,local_x0,local_x1), source coordinates add roi origin','masks':{k:rle(v)for k,v in masks.items()},'geometry_permission':'None. Color/seam masks are appearance evidence. Uncertain/shadow/opening masks may not generate occupied depth. Conditional outer/axis measurements are a separate contract.','source_image_modified':False}
 save('uncertainty_masks.json',mask_report)
 measured_y=grids['top_rows']['mean_major_interval_px'];predicted_y=32*float(affine[1,1]);gridtest={'global_marker_affine_is_valid_raster_inverse':False,'marker_predicted_vertical_major_period_px':predicted_y,'measured_vertical_major_period_px':measured_y,'difference_px':measured_y-predicted_y,'marker_vertical_scale':float(affine[1,1]),'actual_grid_vertical_scale_from_major_lines':measured_y/32,'explanation':'Top vertical fiducial span shrank, but internal horizontal grid lines retain near32px spacing. A single whole-raster affine cannot explain both. Grid redraw/crop/layout and building-content resize must remain separate hypotheses.'}
 report={'schema':'riverstone.reference_roof_measurement.audit.v1','status':'PARTIAL_ROOF_TOPOLOGY_SUPPORTED_METRIC_TOP_NOT_ACCEPTED','source_image':ref(inputs[0]),'author':ref(Path(__file__)),'source_dependencies':deps,'original_registration_pass':registration['registration_pass'],'original_registration_max_error_px':registration['max_error_px'],'original_top_fiducial_anisotropy':fits['anisotropy'],'semantic_roi_annotations':rois,'roof_envelope_measurements':roof,'internal_grid_measurements':grids,'global_affine_hypothesis_test':gridtest,'conditional_local_roof_registration':fit,'ridge_and_height_consistency':ridge,'front_back_gable_profile_fits':gables,'chimney_observations':chimneys,'heldout_chimney_consistency':chimney_check,'tile_appearance_evidence':tile_evidence,'local_tile_examples':tile_examples,'uncertainty_masks':ref(H/'uncertainty_masks.json'),'whole_roof_metric_registration_pass':False,'per_tile_3d_reconstruction_supported':False,'geometry_or_compiler_invoked':False,'image_warp_or_generation_performed':False,'production_changes':False,'absolute_real_world_measurement_claim':False,'source_dependencies_unchanged':all(sha(R/f)==s for f,s in deps.items()),'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 assert report['source_dependencies_unchanged']and not registration['registration_pass']and gridtest['difference_px']>5 and abs(chimney_check['top_x_residual_from_front_back_mean_m'])>.5
 save('measurements.json',report)
 table=[['feature','view','observation','diagnostic_metric_or_residual','status'],['roof_tile_envelope_width','front/back',str([fb,bb]),str(fit['fitted_target_dimensions_diagnostic_m'][0]),'planned32px units; gutter not included'],['roof_tile_depth','right/left',str([rb,lb]),str(fit['fitted_target_dimensions_diagnostic_m'][1]),'horizontal interval only; upper height contradictory'],['top_slope_rectangle','top',str(rect),str(fit['top_naive32px_dimensions_diagnostic_m']),'raw scale rejected'],['top_marker_inverse','top','corner-affine diagnostic',str(fit['top_marker_inverse_only_dimensions_diagnostic_m']),'whole-raster inverse rejected by internal grid'],['ridge_axis','top vs front/back',str(ridge_band),str([ridge_x_interval,front_ridge_x,back_ridge_x]),'conditional local-axis support'],['ridge_height','sides vs front/back',str(ridge['side_vs_front_top_height_difference_px']),str([v/32 for v in ridge['side_vs_front_top_height_difference_px']]),'contradiction preserved'],['chimney_center_X','top vs front/back',str(ct),str(chimney_check['top_x_residual_from_front_back_mean_m']),'held-out registration FAIL'],['chimney_center_Z','right vs left',str([cr,cl]),str(chimney_check['right_left_z_disagreement_m']),'uncertain finite depth envelope only'],['tile_seam_U','top two planes','median approximately11px',str([tile_evidence[n]['interval_coefficient_of_variation']for n in ['left_plane_u','right_plane_u']]),'appearance strip boundaries supported'],['tile_seam_V','top two planes','irregular/phase-shifted shaded troughs',str([tile_evidence[n]['interval_coefficient_of_variation']for n in ['left_plane_v','right_plane_v']]),'individual closed tiles and height unsupported']]
 with(H/'correspondence.csv').open('x',newline='')as f:csv.writer(f).writerows(table)
 print(json.dumps({'status':report['status'],'outer_fit':fit,'ridge':ridge,'chimney':chimney_check,'grid':gridtest,'elapsed_seconds':report['elapsed_seconds'],'peak_rss_kib':report['peak_rss_kib']}))

if __name__=='__main__':measure()
