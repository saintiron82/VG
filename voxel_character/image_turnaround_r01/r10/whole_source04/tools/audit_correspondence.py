"""Read actual masks/curves and source, separating observations from priors."""
from physical_depth import *
from collections import Counter,deque
from PIL import ImageDraw
import review_surface as view
from review_hole_aware import mats
view.A=previous.A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def run():
    m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v,f,ch=s['vertices'],s['triangles'],s['charts']
    curves=m['base_measurement']['previous_measured_curves']['charts'];fit=gzread(BASE/'evidence/source_fit.json.gz')['charts']
    records=[]
    for i,q in enumerate(curves):
        seen={}
        for name,vr in q['views'].items():
            count=Counter(r['status'] for r in vr['boundary']);seen[name]={'status_counts':dict(count),
              'gradient_edge_observation_fraction':count['measured_edge']/len(vr['boundary']),
              'same_material_point_observed':False}
        z=v[np.unique(f[ch==i]),2];r=fit[i]['measurement_or_prior']
        records.append({'chart':i,'id':q['id'],'boundary_evidence':seen,'same_panel_identity':q['cross_view_identity'],
          'observed_same_material_point_count':0,'paired_correspondence_method':'MANUAL normalized phase/arclength' if 'side' in q['views'] else None,
          'boundary_height_rms_mm':r.get('boundary_y_disagreement_rms_m',0)*1000 if 'side' in q['views'] else None,
          'boundary_height_max_mm':r.get('boundary_y_disagreement_max_m',0)*1000 if 'side' in q['views'] else None,
          'depth_extent_mm':[float(z.min()*1000),float(z.max()*1000)],
          'depth_span_mm':float(np.ptp(z)*1000),
          'depth_is_observed_exact':False,'hidden_sewn_root':None})
    rear=view.project_exact(view.source_render(v,f[ch==11],mats()),F)
    foreground=a['front_foreground'];cloth=a['front_support'];oc=np.zeros_like(cloth)
    for poly in previous.FULL['occluder_semantic_polygons']['front']:oc|=polygon_mask(poly,F['crop'])
    zf=depth_image(v,f[ch!=11]);zr=depth_image(v,f[ch==11]);over=np.isfinite(zf)&np.isfinite(zr)
    occlusion={'rear_projected_pixels':int(rear.sum()),'rear_over_actual_front_cloth_pixels':int((rear&cloth).sum()),
      'rear_over_explicit_bouquet_occlusion_polygon_not_cloth_px':int((rear&oc&foreground&~cloth).sum()),
      'rear_over_other_front_foreground_not_cloth_px':int((rear&foreground&~cloth&~oc).sum()),
      'rear_outside_conservative_figure_foreground_px':int((rear&~foreground).sum()),
      'rear_ahead_front_cloth_over_1mm_px':int((over&(zr>zf+.001)).sum()),
      'interpretation':'Only the last exterior quantity diagnoses outline protrusion. Non-cloth foreground includes visible legs, bouquet, gloves or hair; body depth is absent, so actual occlusion remains unknown. Front cloth is z-buffer tested separately. This is not a body z-buffer or completed semantic segmentation.'}
    co=gzread(BASE/'generated/common25.cells.json.gz');lookup={tuple(r[:3]):r for r in co['cells']};todo=set(lookup);components=[]
    while todo:
        start=min(todo);todo.remove(start);queue=[start];cells=[]
        while queue:
            p=queue.pop();cells.append(p)
            for k in range(3):
                for d in [-1,1]:
                    q=tuple(p[j]+(d if j==k else 0) for j in range(3))
                    if q in todo:todo.remove(q);queue.append(q)
        components.append({'cells':len(cells),'paint_part_counts':dict(Counter(lookup[p][4] for p in cells))})
    components.sort(key=lambda x:-x['cells'])
    out={'approved_pixel_sha256':sha(REPO/previous.A['source']),'measurement_sha256':sha(BASE/'evidence/measurement.json.gz'),
      'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'charts':records,
      'occlusion_partition':occlusion,'common25_components_part_attribution':components,
      'diagnosis':['Measured gradient locations do not establish cross-view point identity; most declared boundary samples are explicit manual/unknown anchors.',
        'Chart4 inherits an upper-fold height gauge and has only about25mm depth variation. Its flatness is a prior outcome, not measured panel thickness.',
        'Rear center is back-mask observed but its depth/sewing identity is unknown. Height-profile gauge, conflicting ordering bounds and unconverged solve remain potential band causes.',
        'Source03->04 fixes winding/nearest-anchor/physical-curvature issues, but does not make manually phase-paired boundaries physically calibrated.'],
      'next_measured_method':'Use actually observed garment edge/free-hem extrema or cloth-skin boundaries for height-consistent segment-restricted correspondence. Record camera and matching intervals; absent corresponding edge means unknown. Keep front native masks, separate charts and explicit curvature priors; no thickness increase.',
      'legacy_contract_text_errata':{'depth.interior':'Superseded by depth_correction.curvature: physical cotangent/lumped-area operator with soft observations, not old hard graph-Laplacian wording.',
        'legacy_projection_labels':'Side is whole costume provisional region; the inherited phrase same-flap is not a claim that all panels have known correspondence.'},
      'audit_script_sha256':sha(__file__)}
    write(BASE/'evidence/correspondence_occlusion_audit.json',out)
    # This is an evidence sheet from original pixels plus actual renders, not an edited reference.
    canvas=Image.new('RGB',(1152,940),'white');d=ImageDraw.Draw(canvas)
    d.text((12,8),'APPROVED PIXELS / CONTINUOUS SOURCE / ACTUAL COMMON25 | costume-only process draft',fill='black')
    src=Image.fromarray(SOURCE).crop((60,270,1536,624));src.thumbnail((1130,280));canvas.paste(src,((1152-src.width)//2,32))
    for name,y in [('costume_source_four_views.jpg',314),('common25_four_views.jpg',612)]:
        im=Image.open(BASE/'generated'/name);im.thumbnail((1152,296));canvas.paste(im,(0,y))
    d.text((12,918),'38 common components; rear207 incompatible samples; correspondence uncertain; no body / head / hair / rig / GPU approval',fill='black')
    canvas.save(BASE/'generated/approved_source_common_comparison.jpg',quality=83)
    print(json.dumps({'occlusion':occlusion,'chart4':records[4],'comparison_sha256':sha(BASE/'generated/approved_source_common_comparison.jpg')}))

if __name__=='__main__':run()
