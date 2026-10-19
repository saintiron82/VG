"""Record observed actual-engine images and a bounded same-eye background-color comparison."""
import json,hashlib
from pathlib import Path
from PIL import Image
import numpy as np
from scipy.ndimage import label,find_objects
from .build_corridors import H,ROOT,ref

def main():
 e=ROOT/'world_city/concept_city_v3/evidence';records=[]
 for side in ['west','east']:
  row={'side':side.upper(),'images':{},'sky_color_pixel_count_in_side_rois':{}}
  for rev in ['r03','r04']:
   path=e/f'r10_functional_{rev}'/f'r9_{side}_gate_eye.png';a=np.asarray(Image.open(path).convert('RGB'));color=a[400,720];mask=(a==color).all(2);roi=np.zeros(mask.shape,bool);roi[630:960,:505]=True;roi[630:960,1065:]=True;mask&=roi;lab,count=label(mask);boxes=[]
   for i,s in enumerate(find_objects(lab)):boxes.append({'pixel_count':int((lab[s]==i+1).sum()),'pixel_bbox_xyxy_exclusive':[s[1].start,s[0].start,s[1].stop,s[0].stop]})
   row['images'][rev]=ref(path);row['sky_color_pixel_count_in_side_rois'][rev]=int(mask.sum())
   if rev=='r04':row['remaining_background_color_components']=boxes;row['sampled_sky_rgb']=color.tolist()
  records.append(row)
 caps=[]
 for rev in ['r03','r04']:
  runtime=json.load(open(e/f'r10_functional_{rev}'/'runtime.json'));caps.append({r['view']:{k:r[k]for k in ['width','height','lighting']}for r in runtime['captures']if r['view']in ['r9_west_gate_eye','r9_east_gate_eye']})
 report={'schema':'riverstone.actual_visual_review.v1','status':'REVIEWED_MAJOR_FORECOURT_TEARS_CLOSED_WITH_RECORDED_OUTER_EDGE_RESIDUAL','candidate':ref(H/'candidate_r10/FROZEN.json'),'actual_composition':{'index':ref(ROOT/'world_city/concept_city_v3/registered_integration/r10_functional_audit/integration_r04/index.json'),'finite_patch':ref(ROOT/'world_city/concept_city_v3/registered_integration/r10_functional_audit/integration_r04/surface_patch.json')},'actual_runtime_binding':ref(e/'r10_functional_r04/runtime_source_binding.json'),'image_review':{'directly_viewed':['r9_west_gate_eye.png','r9_east_gate_eye.png','registered.png'],'registered_overview':ref(e/'r10_functional_r04/registered.png'),'findings':['Repeated large triangular side tears visible in r03 no longer appear in r04; the repaired sides read as connected retaining faces beneath narrow grass setbacks.','The public approach top and gate opening remain visually continuous in both unchanged eye views.','The registered whole-city view retains the approved city outline and southern port/bridge arrangement; the view is not a detailed inspection of every city edge.','A residual sequence of tiny sky-colored dashes remains at the far lower-right outer boundary in the east view. It is recorded below and is not declared sealed or proven harmless from pixels alone.']},'same_resolution_and_lighting':caps[0]==caps[1],'camera_pose_policy':'Parent reused the original named r9 gate-eye camera definitions; no reframing requested by the producer.','pixel_diagnostic':{'method':'Exact RGB equality to the visible sky sample at pixel [720,400]. Side ROIs are x[0,505) or x[1065,1536), y[630,960). This quantifies the observed same-eye background-colored exposure; it is not a geometric proof of watertightness.','records':records},'limits':['No claim that the whole city or all unchanged outer shoulders are gap-free.','East residual has 42 background-colored pixels in 17 connected components, mostly one-pixel-high outer-edge dashes; no source change was made to hide them.','Retaining walls are explicit geometry up to 3.8385 m high; their sides are not pedestrian/cart routes.','The visual judgement is bounded to these actual captures. Full runtime evidence separately passes 26 capsule and 26 rigid-cart cases.']}
 (H/'candidate_r10/visual_review.json').write_text(json.dumps(report,indent=2)+'\n')
 print(report['status'])
if __name__=='__main__':main()
