"""Source image, independently measured charts, continuous and common geometry."""
from surface_atlas import *
import review_surface as view

def source_review():
 m,a=load_measurement();ma=gzread(BASE/'generated/panel_master.json.gz');sf=np.load(BASE/'generated/continuous_surface.npz');r=view.source_render(sf['vertices'],sf['triangles'],ma['materials']);stats,preds=view.metrics(r,a);sheet,cam=view.view_sheet(r,'CONTINUOUS06 | measured larger lobe with shared fold / explicit inferred depth');sheet.save(BASE/'generated/source_four_views.jpg',quality=90);view.overlays(a,preds,'SOURCE: approved pixel boundaries / uncalibrated side / back identity UNKNOWN').save(BASE/'generated/source_overlay.jpg',quality=90)
 im=Image.fromarray(SOURCE.copy());dr=ImageDraw.Draw(im)
 for name in ['front','side','back']:
  for pt in m['views'][name]['measured_contour']:
   x,y=pt['xy_px'];dr.ellipse((x-1,y-1,x+1,y+1),fill='lime' if pt['status']=='measured_edge' else 'orange')
  if name in m['folds']:
   for pt in m['folds'][name]['points']:
    x,y=pt['xy_px'];dr.ellipse((x-1,y-1,x+1,y+1),fill='red' if pt['status']=='measured_color_edge' else 'yellow')
 im.crop((390,375,1285,565)).save(BASE/'generated/measurement_boundary_fold_overlay.png')
 exact=bool(np.array_equal(preds['front'],a['front_support']));est={str(p):view.candidate_count(ma,p) for p in [.025,.0125]};fit=gzread(BASE/'evidence/surface_fit.json.gz');out={'source_projection':stats,'exact_front_pixel_domain_after_adaptive_triangulation':exact,'adaptive_mesh':read(BASE/'evidence/adaptive_mesh.json'),'candidate_estimate':est,'camera':cam,'source_components':int(ndi.label(a['front_support'])[1]),'fold_correspondence_vertical_rms_mm':1000*fit['fold_y_residual_rms_m'],'fold_correspondence_vertical_max_mm':1000*fit['fold_y_residual_max_m'],'root_depth_extrapolated_vertices':len(fit['unknown_root_depth_prior_vertices']),'side_back_are_generated_image_interpretations':True,'body_attachment_complete':False,'source_surface_fit':fit['success'],'master_sha256':sha(BASE/'generated/panel_master.json.gz'),'source_geometry_sha256':sha(BASE/'generated/continuous_surface.npz'),'CPU_renderer_sha256':sha(CPU_SOURCE),'evaluator_sha256':sha(view.__file__),'budget_plan':{'source_operations':len(sf['triangles']),'expected_compile_peak_mib_upper':400,'hard_peak_limit_mib':512,'expected_new_total_bytes_upper':5000000,'total_r10_ceiling_bytes':41943040,'no_full_character_compile':True}}
 write(BASE/'evidence/source_review.json',out);print(json.dumps(out))
if __name__=='__main__':source_review()
