"""Actual source-raster mutations in memory; input PNG remains byte-identical."""
import hashlib,json,time,resource
import numpy as np
from PIL import Image
import reconstruct as r
start=time.monotonic();before=r.sha(r.P/'generated_candidate_r03.png');source=np.asarray(Image.open(r.P/'generated_candidate_r03.png').convert('RGB'));maps,pal=r.extract(source);_,occ,mats,_=r.reconstruct(maps,pal)

def run_mutation(yy,xx,color):
 image=source.copy();x0=64+int(xx)*4;y0=496-(int(yy)+1)*4;image[y0:y0+4,x0:x0+4]=color;new_maps,new_pal=r.extract(image);_,o,m,_=r.reconstruct(new_maps,new_pal);return [x0,y0,x0+4,y0+4],new_maps,new_pal,o,m,hashlib.sha256(image.tobytes()).hexdigest()
# A visible silhouette edge, not a filled interior hole. Try real source border
# cells until the diagnostic reconstructed geometry is sensitive to that input.
selected=None
for yy in range(20,76):
 xs=np.flatnonzero(maps['front']['silhouette'][yy]&maps['back']['silhouette'][yy])
 if not len(xs):continue
 for xx in (int(xs[0]),int(xs[-1])):
  result=run_mutation(yy,xx,[255,255,255])
  if not np.array_equal(result[3],occ):selected=(yy,xx,result);break
 if selected:break
assert selected is not None,'No tested4x4 silhouette edit changed geometry'
yy,xx,geo=selected;box,gm,gp,go,gt,gh=geo
# Warm, bright lower facade patch: no gallery/blue-pane depth state changes.
choices=np.argwhere(maps['front']['raw'] & (maps['front']['rgb'].mean(axis=2)>180) & (np.arange(112)[:,None]>=8) & (np.arange(112)[:,None]<24));assert len(choices)
color=None
for cy,cx in choices[::max(1,len(choices)//12)]:
 candidate=run_mutation(cy,cx,[228,144,75]);_,cm,cp,co,ct,_=candidate
 if np.array_equal(co,occ):
  oldrgb=pal[mats[occ]];newrgb=cp[ct[occ]]
  if np.any(oldrgb!=newrgb):color=(int(cy),int(cx),candidate);break
assert color is not None,'No color-only raster edit found without geometry change'
cy,cx,(cbox,cm,cp,co,ct,ch)=color;cell_colors_changed=np.any(pal[mats[occ]]!=cp[ct[occ]],axis=1);coords=np.argwhere(occ);affected=coords[cell_colors_changed];inside=(affected[:,0]==cy)&(affected[:,1]==cx)
report={'schema':'riverstone.image_voxel.actual_raster_sensitivity.v1','source_image':r.ref(r.P/'generated_candidate_r03.png'),'script':r.ref(__file__),'pipeline':r.ref(r.HERE/'reconstruct.py'),'original_file_unchanged':r.sha(r.P/'generated_candidate_r03.png')==before,'mutations_persisted_as_images':False,'geometry_mutation':{'input_4x4_roi_px':box,'replacement_rgb':[255,255,255],'mutated_raster_sha256':gh,'changed_front_raw_mask_cells':int(np.count_nonzero(gm['front']['raw']!=maps['front']['raw'])),'changed_front_silhouette_cells':int(np.count_nonzero(gm['front']['silhouette']!=maps['front']['silhouette'])),'changed_output_occupancy_cells':int(np.count_nonzero(go!=occ)),'palette_entries_changed':int(np.count_nonzero(np.any(gp!=pal,axis=1)))},'color_mutation':{'input_4x4_roi_px':cbox,'replacement_rgb':[228,144,75],'mutated_raster_sha256':ch,'changed_front_raw_mask_cells':int(np.count_nonzero(cm['front']['raw']!=maps['front']['raw'])),'changed_output_occupancy_cells':int(np.count_nonzero(co!=occ)),'changed_output_actual_rgb_cells':int(cell_colors_changed.sum()),'affected_cells_outside_edited_projection_column':int(np.count_nonzero(~inside)),'palette_entries_changed':int(np.count_nonzero(np.any(cp!=pal,axis=1))),'global_effect_explanation':'Palette is re-extracted from the entire foreground raster. A tiny image change may shift median-cut palette values and nearest-color assignments elsewhere; reported as such, not local-only stability.'},'all_pass':True,'sampling_calls':0,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':['12-color global median-cut loses fine color variation.','Input shadows, highlights and ambient occlusion can become baked material colors.','This diagnostic palette is not a physically separated albedo/material map.','No runtime palette override or final3-tone physical-unit design is claimed.']};r.write('actual_raster_sensitivity.json',report);print(json.dumps(report),flush=True)
