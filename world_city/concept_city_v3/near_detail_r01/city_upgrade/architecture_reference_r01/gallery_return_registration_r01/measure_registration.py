"""Bounded image-only FRONT/RIGHT gallery registration. No geometry authoring."""
import os,sys,resource,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(110,110));START=time.monotonic()
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent;A=O.parent;ROOT=next(p for p in O.parents if (p/'voxel_character/common/core.py').exists());P=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01';S=P/'generated_candidate_r03.png';im=np.asarray(Image.open(S).convert('RGB'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def roi_sha(roi):
 x0,y0,x1,y1=roi;return hashlib.sha256(im[y0:y1,x0:x1].tobytes()).hexdigest()
# Manual semantics identify corresponding edges and short search windows.
# The detector chooses the exact row from real RGB, not an authored bar height.
FEATURES=['cap_first_warm_row','cap_shadow_holdout','lower_rail_fascia_seam','fascia_underside_edge']
BANDS={'upper':{'front':[[249,256],[256,260],[288,294],[296,300]],'right':[[243,249],[249,253],[281,287],[289,294]]},'lower':{'front':[[351,358],[358,362],[388,394],[395,400]],'right':[[352,358],[358,362],[388,394],[396,400]]}}
STRIPS={'front':[[154,170],[170,186],[186,202],[170,206]],'right':[[634,648],[648,662],[662,676],[645,679]]}
records=[];primary={}
for level,views in BANDS.items():
 primary[level]={}
 for view,bands in views.items():
  primary[level][view]={}
  for si,(x0,x1) in enumerate(STRIPS[view]):
   for feature,(y0,y1) in zip(FEATURES,bands):
    median_rgb=np.median(im[y0:y1,x0:x1].astype(float),axis=1);lum=median_rgb.mean(1)
    if feature=='cap_first_warm_row':
     eligible=(median_rgb[:,0]-median_rgb[:,1]>40)&(median_rgb[:,1]-median_rgb[:,2]>35)&(lum>110);ii=np.flatnonzero(eligible);assert len(ii);row=int(y0+ii[0]);method='First row with median r-g>40, g-b>35 and RGB mean>110 within semantic cap search band.';scores=eligible.astype(int).tolist();roi=[x0,y0,x1,y1]
    elif feature=='cap_shadow_holdout':
     row=int(y0+np.argmin(lum));method='Minimum row-median RGB mean within independently labelled cap shadow band; holdout, not fitted.';scores=lum.tolist();roi=[x0,y0,x1,y1]
    else:
     ext=np.median(im[y0-1:y1,x0:x1].astype(float),axis=1).mean(1);delta=np.diff(ext);row=int(y0+np.argmin(delta));method='Most negative difference of adjacent row-median RGB means within semantic edge band.';scores=delta.tolist();roi=[x0,y0-1,x1,y1]
    rec={'level':level,'view':view,'feature':feature,'strip_index':si,'primary_strip':si==3,'source_roi_px':roi,'raw_rgb_sha256':roi_sha(roi),'selected_row_px':row,'edge_height_native_m':(496-row)/32,'method':method,'search_row_range_half_open':[y0,y1],'scores':scores,'manual_annotation':'Feature identity, x strip and search band are manually selected. RGB determines exact row.','uncertainty_floor_px':1};records.append(rec)
    if si==3:primary[level][view][feature]=row
fits={};all_front=[];all_right=[]
for level,views in primary.items():
 fit_features=[f for f in FEATURES if f!='cap_shadow_holdout'];ff=np.array([views['front'][f] for f in fit_features],float);rr=np.array([views['right'][f] for f in fit_features],float);shift=float(np.median(ff-rr));all_front.extend(ff.tolist());all_right.extend(rr.tolist())
 rows=[]
 for f in FEATURES:
  a=views['front'][f];b=views['right'][f];sub_f=[q['selected_row_px'] for q in records if q['level']==level and q['view']=='front' and q['feature']==f];sub_r=[q['selected_row_px'] for q in records if q['level']==level and q['view']=='right' and q['feature']==f]
  rows.append({'feature':f,'used_to_fit':f in fit_features,'front_y_px':a,'right_y_px':b,'native_step_right_minus_front_height_m':(a-b)/32,'registered_right_y_px':b+shift,'residual_registered_right_minus_front_px':b+shift-a,'residual_m':-(b+shift-a)/32,'front_substrip_row_range':[min(sub_f),max(sub_f)],'right_substrip_row_range':[min(sub_r),max(sub_r)]})
 fits[level]={'right_to_front_pixel_y_translation_px':shift,'world_y_translation_m':-shift/32,'horizontal_scale':1,'vertical_scale':1,'transformation_applied_to_pixels':False,'scope':'Proposed part-level coordinate mapping, not raster warping or repair of the global sheet.','paired_edges':rows,'fit_rmse_px':float(np.sqrt(np.mean((rr+shift-ff)**2))),'fit_max_abs_px':float(np.max(np.abs(rr+shift-ff))),'holdout_max_abs_px':max(abs(q['residual_registered_right_minus_front_px']) for q in rows if not q['used_to_fit']),'cap_to_fascia_seam_height_px':views['front']['lower_rail_fascia_seam']-views['front']['cap_first_warm_row'],'cap_to_underside_height_px':views['front']['fascia_underside_edge']-views['front']['cap_first_warm_row']}
ff=np.array(all_front);rr=np.array(all_right);global_shift=float(np.mean(ff-rr));coef=np.linalg.lstsq(np.column_stack([rr,np.ones(len(rr))]),ff,rcond=None)[0];pred=rr*coef[0]+coef[1]
# A small same-height shaft section: silhouette evidence in both orthogonal views.
shaft=[]
for view,roi in [('front',[419,222,438,242]),('right',[616,215,638,235])]:
 x0,y0,x1,y1=roi;c=im[y0:y1,x0:x1].astype(float);r,g,b=np.moveaxis(c,-1,0);warm=(r>=90)&(r-g>=12)&(g-b>=12)&(r>=1.3*b)&(c.mean(2)>=80);coverage=warm.mean(0);xx=np.arange(x0,x1);support=xx[coverage>=.8];rows=[]
 for iy,row in enumerate(warm):
  x=xx[row];rows.append({'native_y_px':y0+iy,'registered_y_px':y0+iy+(7 if view=='right' else 0),'positive_x_pixels':x.tolist(),'positive_span_half_open':[int(x.min()),int(x.max()+1)] if len(x) else None})
 shaft.append({'view':view,'roi_px':roi,'raw_rgb_sha256':roi_sha(roi),'predicate':'r>=90; r-g>=12; g-b>=12; r>=1.3*b; RGB mean>=80','column_coverage':[[int(x),float(q)] for x,q in zip(xx,coverage)],'persistent_positive_columns_80pct':support.tolist(),'persistent_span_half_open':[int(support.min()),int(support.max()+1)],'positive_pixels':int(warm.sum()),'rows':rows,'is_lower_bound_positive_wood':True})
sf,sr=shaft;xx=sf['persistent_span_half_open'];zz=sr['persistent_span_half_open'];bounds={'x':[(xx[0]-256)/32,(xx[1]-256)/32],'y':[(496-242)/32,(496-222)/32],'z':[(768-zz[1])/32,(768-zz[0])/32]}
# Register the OLD audit's three selected probes without inventing connector pixels.
old=json.loads((A/'gallery_audit_r01/footprint_checks.json').read_text());registered=[]
for q in old['patches']:
 x0,y0,x1,y1=q['roi_px'];registered.append({'id':q['id'],'owner':q['owner'],'source_roi_px':q['roi_px'],'raw_rgb_sha256':roi_sha(q['roi_px']),'registered_y_roi_px':[y0+7,y1+7],'registered_bounds_m':{'x':None,'y':[(496-y1-7)/32,(496-y0-7)/32],'z':[(768-x1)/32,(768-x0)/32]},'positive_candidate_pixels':q['warm_positive_candidate_pixels'],'thickness_prior_applied':False})
# Existing cap/shadow/fascia bands, measured from primary source edge rows.
U=primary['upper'];bands={'front':{'cap_positive_search':[253,257],'cap_shadow_unresolved':[257,260],'panel_field':[260,291],'fascia':[291,298]},'right_native':{'cap_positive_search':[246,250],'cap_shadow_unresolved':[250,254],'panel_field':[254,284],'fascia':[284,291]},'right_registered':{'cap_positive_search':[253,257],'cap_shadow_unresolved':[257,261],'panel_field':[261,291],'fascia':[291,298]}}
result={'schema':'riverstone.gallery_return.part_registration.v1','source_image':ref(S),'no_geometry_generated':True,'no_raster_warped':True,'original_files_edited':False,'coordinate_convention':'Source ROI half-open [x0,y0,x1,y1]; selected edge row is a pixel-boundary surrogate with at least +/-1px uncertainty. FRONT/RIGHT native y=(496-pixel_y)/32.','manual_annotation_policy':'Semantic feature matches, strip positions and short search windows are explicit human input; exact edge rows, RGB profiles and residuals are machine measurements.','source_edges':records,'primary_landmarks':primary,'local_fits':fits,'global_fit_counterexample':{'single_translation_px':global_shift,'rmse_px':float(np.sqrt(np.mean((rr+global_shift-ff)**2))),'max_abs_residual_px':float(np.max(np.abs(rr+global_shift-ff))),'all_upper_shift_applied_to_lower_residual_px':7,'best_global_affine_y_front_equals_a_y_right_plus_b':coef.tolist(),'affine_rmse_px':float(np.sqrt(np.mean((pred-ff)**2))),'affine_max_abs_residual_px':float(np.max(np.abs(pred-ff))),'affine_not_applied':True,'why_rejected':'A global shift misaligns one storey; the fitted global affine rescales actual panel heights and is not compatible with unchanged native 32px/m shape. Fiducial fit does not authorize an internal nonuniform warp.'},'shaft_two_view_evidence':shaft,'shaft_common_positive_envelope_m':bounds,'shaft_semantic_and_depth_limits':['Cross-view correspondence of the same visible outer shaft is manually selected.','Measured X and Z spans are persistent positive wood lower bounds, not hidden complete cross-section edges.','A filled rectangular prism would still assume a solid hidden interior; no such geometry is generated.','Joining this shaft to cap/deck requires evaluating intervening source masks, not extending its envelope by a box.'],'registered_prior_audit_probes':registered,'semantic_vertical_bands':bands,'unresolved_contact_bands':{'post_probe_to_cap':'Registered old post probe ends at y253, equal to FRONT first cap row; geometric 2D bounds now meet, but material mask contact/occlusion must still be checked.','old_return_probe_to_cap':'Registered old return probe starts at y267; full return requires measuring y257..267, including the unresolved shadow transition.','old_return_probe_to_deck':'Registered return probe ends y295 and registered old deck probe begins y298. These old diagnostic ROIs mis-classify the y291..298 fascia band as return/deck. Repartition by measured bands before any integration.','important_correction':'The 0.4375m/0.09375m old probe gaps were ROI truncations, not real physical gaps. The new cap/fascia measurements replace those box-bound interpretations.'},'inputs':[ref(S),ref(P/'registration_r03.json'),ref(A/'gallery_audit_r01/diagnosis.json'),ref(A/'gallery_audit_r01/footprint_checks.json'),ref(A/'gallery_panel_repair_r01/manifest.json'),ref(A/'gallery_panel_repair_r01/independent_exterior_validation.json')],'elapsed_seconds':time.monotonic()-START,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':{'cpu_seconds':110,'address_space_mib':256,'wall_command_seconds':120}}
(O/'measurements.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'upper_translation_px':fits['upper']['right_to_front_pixel_y_translation_px'],'upper_fit_max_abs_px':fits['upper']['fit_max_abs_px'],'upper_holdout_max_abs_px':fits['upper']['holdout_max_abs_px'],'lower_translation_px':fits['lower']['right_to_front_pixel_y_translation_px'],'global_affine':result['global_fit_counterexample'],'shaft_envelope_m':bounds,'seconds':result['elapsed_seconds'],'rss_kib':result['peak_rss_kib']}))
