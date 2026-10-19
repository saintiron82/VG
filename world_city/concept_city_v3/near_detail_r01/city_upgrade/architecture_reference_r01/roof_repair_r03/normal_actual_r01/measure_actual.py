"""Read-only pixel analysis of actual paired captures; geometry projection is diagnostic ROI, not occlusion truth."""
from pathlib import Path
import json,hashlib,gzip
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
P=Path(__file__).resolve().parent
c=json.loads((P/'capture_report.json').read_text()); assert len(c['records'])==8 and all(x['save_error']==0 for x in c['records'])
s=json.loads(Path(c['normal_validation']['sidecar_path']).read_text());r=json.loads(gzip.decompress(Path(c['source_render_path']).read_bytes()))
assert c['source_render_sha256']==s['render_sha256']; rows={x['view']:x for x in c['records']}
metrics=[]
for stem in ['oblique','roof_close']:
 for suffix in ['','_noshadow']:
  a=stem+'_before'+suffix;b=stem+'_after'+suffix
  x=np.asarray(Image.open(P/(a+'.png')).convert('RGB'));y=np.asarray(Image.open(P/(b+'.png')).convert('RGB'))
  src=rows[a]['world_to_pixel_anchors'];X=np.array([k['world']+[1] for k in src]);Y=np.array([k['pixel'] for k in src]);proj=np.linalg.lstsq(X,Y,rcond=None)[0]
  err=float(np.abs(X@proj-Y).max()); assert err<.01
  mask=Image.new('L',(x.shape[1],x.shape[0]));dr=ImageDraw.Draw(mask)
  for patch in s['patches']:
   q=r['groups'][patch['group_index']]['quads'][patch['quad_index']];uv=np.c_[np.array(q),np.ones(4)]@proj
   dr.polygon([tuple(z) for z in uv],fill=255)
  m=np.asarray(mask.filter(ImageFilter.MaxFilter(5)))>0;m[:70]=False
  changed=np.any(x!=y,axis=2);changed[:70]=False
  # Neighbor energy in explicitly projected diagnostic ROI. This is not a semantic z-buffer.
  energy={}
  for label,im in [('before',x),('after',y)]:
   lum=(im/255.)@np.array([.2126,.7152,.0722]);mx=m[:,:-1]&m[:,1:];my=m[:-1,:]&m[1:,:]
   v=np.r_[np.abs(np.diff(lum,axis=1))[mx],np.abs(np.diff(lum,axis=0))[my]]
   energy[label]=float(v.mean())
  metrics.append({'pair':[a,b],'affine_anchor_max_error_px':err,'changed_pixels':int(changed.sum()),'changed_outside_projected_patches_with_2px_margin':int((changed&~m).sum()),'projected_roi_pixels':int(m.sum()),'neighbor_luma_delta':energy,'roi_limit':'projected quad union, no independent occlusion solver'})
report={'schema':'riverstone.roof.normal.actual_comparison.v1','status':'DIAGNOSTIC_SUCCESS_ART_UNRESOLVED','source_geometry_color_preservation':c['normal_validation'],'metrics':metrics,'review':['Twelve source-bound tile patches are visibly altered with unchanged positions/materials. Their broad color/curvature is more discernible, but substantial fine steps remain within and around patches.','Shadow-off views retain microgrid: cast shadows alone are not the cause. Normal substitution reduces part of the grid; neither isolated action completes tile readability.','No whole-roof smoothing, unshaded final material, cell reduction or geometry deletion was performed.','Actual baseline gable gaps and blank backing remain because this diagnostic uses frozen r02 geometry. r03 geometry is separate.'],'six_view_gate_substitute':False,'files':[{'path':str(P/(name+'.png')),'sha256':hashlib.sha256((P/(name+'.png')).read_bytes()).hexdigest()} for name in rows]}
(P/'actual_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(metrics,indent=2))
