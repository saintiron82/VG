"""Trace measurement-boundary defects and limitations without changing geometry."""
from measured_surface import *

def run():
 m,a=load_measurement();out={'source_sha256':A['source_sha256'],'generator_sha256':sha(Path(__file__).with_name('measured_surface.py')),'approved_appearance_edited':False,'views':{}}
 for name,d in m['views'].items():
  counts={}
  for p in d['measured_contour']:counts[p['status']]=counts.get(p['status'],0)+1
  out['views'][name]={'contour_point_status_counts':counts,'self_crossings':contour_crossings([p['xy_px'] for p in d['measured_contour']]),'four_connected_components':d['domain_components'],'component_sizes':d['component_sizes'],'bbox_xyxy':d['bbox_xyxy'],'root_box_is_blanket_occlusion':False,'root_attachment_identity_uncertainty_is_separate':True}
 bad=gzread(ROOT/'continuous05b/evidence/measurements.json.gz');old=[p['xy_px'] for p in bad['views']['front']['measured_contour']];out['preserved_predecessor']={'measurement_sha256':sha(ROOT/'continuous05b/evidence/measurements.json.gz'),'actual_invalid_front_contour_intersections':contour_crossings(old),'invalid_contour_would_be_rejected_before_geometry':bool(contour_crossings(old)),'cause':'low directional scores below8 were allowed to move uncertain root points; these offsets collided with manual unobserved return. The current extractor leaves those points at their explicit annotation anchors and rejects any crossing.'}
 out['source_change_is_not_mask_or_voxel_cleanup']='No connected-component filter, dilation, erosion, hole filling, component deletion, thickness change or shifted voxel origin exists in the correction. Low-confidence edge interpretation changed, and all masks/geometry were regenerated from approved pixels.'
 out['unimplemented_constraints']=['Visible side lavender/white transition suggests a rolled return. The current single-valued z(x,y) patch cannot represent multiple depths over one front pixel or certify that physical fold.','No exact material-point correspondence is observed between front/side/back. Equal aligned height free-edge correspondence and side yaw75 remain declared hypotheses.','Unknown root contour is an explicit semantic closure prior, not measured hidden sewing or a recovered attachment.','Back candidate has a different projected shape; it is held out and never forced as this patch truth.','Two-sided original material assignment, full costume layering, hair/face/body, rig/socket, GPU and final AI correction are not completed by this experiment.']
 out['fold_color_warning']='White-to-lavender shading is observed in the image. It cannot alone identify an exact crease angle, seam, backface normal or fabric albedo. No measured fold angle is claimed.'
 out['causal_contract']='actual source pixel digest -> manual search/occlusion contract + automatic contours/masks -> bounded sparse depth solve -> fixed normal-thickness triangle primitives -> common compiler/mesh -> exact pixel-center projections'
 out['not_a_completed_reconstruction']=True;write(BASE/'evidence/input_quality_and_limits.json',out);print(json.dumps(out))
if __name__=='__main__':run()
