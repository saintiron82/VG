"""Read-only r02 pixel evidence. No image edits/warps or source construction."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
R=next(p for p in Path(__file__).resolve().parents if (p/'world_city/reference').exists());P=R/'world_city/reference/house_quality_photos_20261019/six_views_r01';OUT=Path(__file__).resolve().parent
A=np.asarray(Image.open(P/'generated_candidate_r02.png').convert('RGB')).astype(float);red,green,blue=A[:,:,0],A[:,:,1],A[:,:,2]
tile=(red>100)&(red>1.42*green)&(green>1.35*blue)
def ref(p):return {'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def bbox(mask,roi):
 x0,y0,x1,y1=roi;ys,xs=np.where(mask[y0:y1,x0:x1]);return [int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0),int(ys.max()+y0)]
def first_sustained_chimney(x0,x1,y0,y1):
 a=A[y0:y1,x0:x1];frac=(((a.max(axis=2)-a.min(axis=2))<35)&(a.mean(axis=2)<155)).mean(axis=1)
 # Reject isolated one-row grid lines. A cap starts a sustained dark neutral region.
 for j in range(len(frac)-3):
  if np.all(frac[j:j+3]>.1):return int(y0+j)
 raise ValueError('No sustained cap')
rows=[]
def row(view,feature,actual,desired,method,roi=None,uncertainty=1):
 y0=1008 if view=='left' else 496
 rows.append({'view':view,'feature':feature,'actual_y_px':actual,'desired_y_px':desired,'delta_px':actual-desired,'height_from_required_zero_m':(y0-actual)/32,'height_error_from_desired_m':(desired-actual)/32,'uncertainty_px':uncertainty,'method':method,'sample_roi_px':roi})
for view,roi,desired in [('front',[245,45,268,70],64),('right',[610,70,865,105],64),('back',[1270,45,1293,70],64),('left',[177,580,412,620],576)]:
 row(view,'outer ridge tile silhouette',bbox(tile,roi)[1],desired,'First actual terracotta-colored pixel inside manually selected roof ridge ROI; excludes chimney.',roi)
for view,x0,x1,y0,y1,desired in [('front',366,395,50,85,48),('right',877,906,50,85,48),('back',1140,1168,50,85,48),('left',139,165,560,590,560)]:
 row(view,'chimney cap top',first_sustained_chimney(x0,x1,y0,y1),desired,'First of3 successive rows with >10% dark neutral pixels; avoids the isolated grid border.',[x0,y0,x1,y1])
# Front/back eave tips are slopes rather than a full-width horizontal band.
# Keep the manually inspected raster span instead of claiming a hidden plane.
bands=[]
def band(view,feature,yrange,desired,xrange,meaning):
 y0=1008 if view=='left' else 496
 bands.append({'view':view,'feature':feature,'observed_y_band_px':yrange,'desired_y_px':desired,'delta_band_px':[v-desired for v in yrange],'height_band_from_required_zero_m':[(y0-v)/32 for v in reversed(yrange)],'x_probe_range_px':xrange,'method':'Direct image inspection plus horizontal RGB profiles; band uncertainty explicitly retained.','scope':meaning})
band('front','visible eave roof/fascia tip',[184,201],192,[52,75],'Visible layered tip; exact structural eave plane obscured by layered tiles/edge boards.')
band('back','visible eave roof/fascia tip',[184,200],192,[1075,1097],'Visible layered tip; exact structural eave plane obscured.')
band('right','lowest full-width terracotta roof course',[162,170],192,[690,860],'Last coherent red tile row, excluding brown timber fascia at181; not a declared structural eave plane.')
band('left','lowest full-width terracotta roof course',[663,672],704,[175,325],'Last coherent red tile row; timber fascia below is a separate feature.')
for view,feature,yrange,desired,xrange in [('front','gallery1 visible lower rail/deck front band',[391,397],384,[83,429]),('front','gallery2 visible lower rail/deck front band',[291,298],288,[83,429]),('right','gallery1 visible lower rail/deck front band',[391,398],384,[624,678]),('right','gallery2 visible lower rail/deck front band',[284,291],288,[624,678]),('left','gallery1 visible lower rail/deck front band',[884,891],896,[344,390]),('left','gallery2 visible lower rail/deck front band',[778,785],800,[344,390])]:band(view,feature,yrange,desired,xrange,'Walking top surface is hidden by balustrade/deck front. Do not replace this visible band by an invented exact floor elevation.')
top=bbox(tile,[580,560,950,980]);reg=json.load(open(P/'registration_r02.json'))
report={'schema':'riverstone.architecture.readonly_image_height_audit.v1','source':ref(P/'generated_candidate_r02.png'),'registration_reference':ref(P/'registration_r02.json'),'template_reference':ref(P/'template.json'),'script':ref(Path(__file__).resolve()),'fixed_zero_rows_px':{'upper':496,'lower':1008},'pixels_per_meter':32,'actual_pixel_rows':rows,'visible_feature_bands':bands,'roof_plan_tile_mask':{'inclusive_pixel_bbox':top,'pixel_center_span':[top[2]-top[0],top[3]-top[1]],'metric_span_if_fixed_grid_applied_m':[(top[2]-top[0])/32,(top[3]-top[1])/32],'desired_planned_envelope_m':[12,10],'warning':'Diagnostic only because the TOP grid is unregistered. These numbers must not be used to resize the source.'},'registered':reg['registration_pass'],'max_fiducial_error_px':reg['max_error_px'],'source_reconstruction_allowed':False,'images_changed':False,'sampler_calls':0,'visual_findings':[{'status':'improved','finding':'TOP front gable/gallery elevation has been removed; BACK galleries are absent; side roof upper/lower lines are approximately horizontal.'},{'status':'failed','finding':'Outer ridge is54px in FRONT/BACK but87px in RIGHT and599px in LEFT: both side silhouettes are33px (1.03125m at planned scale) below the front/back ridge. Cap-vs-structural-line distinction does not explain the complete discrepancy.'},{'status':'failed','finding':'TOP/BOTTOM grid upper edges remain near558px rather than688px. TOP roof tile plan is taller than wide while the planned12x10m footprint is wider than deep.'},{'status':'unresolved','finding':'Visible gallery bands differ across front/right/left; walking surface is partly hidden. No exact deck plane is inferred from the top edge of a railing.'},{'status':'unresolved','finding':'Attic loggia remains a shallow dark band with a short glazing-like opening. No verifiable deck-height access door silhouette is supplied.'},{'status':'unresolved','finding':'BOTTOM depicts underside beams/stone perimeter and an entrance stair projection; it does not identify a physically clear interior/gallery circulation volume or depth.'}],'conclusion':'Keep failed candidate and measurements as evidence. Fiducial correction alone cannot establish a common3D source. No image warping or grid recomposition was performed.'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':str((OUT/'report.json').relative_to(R)),'sha256':hashlib.sha256((OUT/'report.json').read_bytes()).hexdigest(),'ridge_rows':{x['view']:x['actual_y_px'] for x in rows if x['feature']=='outer ridge tile silhouette'},'chimney_rows':{x['view']:x['actual_y_px'] for x in rows if x['feature']=='chimney cap top'},'top_tile_bbox':top}))
