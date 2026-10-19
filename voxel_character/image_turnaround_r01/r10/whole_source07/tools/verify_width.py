"""Source dependency checks for split lining observations and common occupancy."""
from fit_width import *
from verify_hole_aware import chart_digest
from verify_height import cells_for

def potential_whole_bound_charts(v,f,ch,rows):
    # The actual conservative bound samples a +/-4 side-row neighborhood.
    # This is a declared uncertainty dependency, not a same-panel observation.
    out=[];sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit']
    for i in range(12):
        y=sv['sole_y']-v[np.unique(f[ch==i]),1]/ss
        if any(np.any(abs(y-r)<=5) for r in rows):out.append(i)
    return out

def run():
    t=time.monotonic();m,a=load();saved=np.load(BASE/'generated/continuous_costume.npz');v,f,ch,pp,report=build(m,a,SOURCE)
    exact=all(np.array_equal(x,saved[k]) for x,k in [(v,'vertices'),(f,'triangles'),(ch,'charts'),(pp,'primary_pixels')]);mm,aa=extract(SOURCE);measured=all(np.array_equal(a[k],aa[k]) for k in a);del mm,aa
    fixtures=[]
    for name,box in [('lining_edge64',[674,515,682,523]),('train100',[591,582,601,592]),('face25',[315,185,320,190])]:
        src=SOURCE.copy();x0,y0,x1,y1=box;src[y0:y1,x0:x1]=[255,0,0];mm,aa=extract(src);vv,ff,cc,ppp,rr=build(mm,aa,src)
        direct=[i for i in range(12) if not np.array_equal(a[f'owned_{i}'],aa[f'owned_{i}'])]
        paired=[i for i in range(10) if f'chart_{i}_side' in a and not np.array_equal(a[f'chart_{i}_side'],aa[f'chart_{i}_side'])]
        intervals=[i for i in range(10) if not np.array_equal(a[f'height_constraints_{i}'],aa[f'height_constraints_{i}'])]
        lining=[i for i in [5,6] if not np.array_equal(a[f'lining_{i}_side_candidate'],aa[f'lining_{i}_side_candidate'])]
        widths=[i for i in A['width_correspondence']['charts'] if not np.array_equal(a[f'width_sections_{i}'],aa[f'width_sections_{i}'])]
        changed_rows=np.flatnonzero((a['side_support']!=aa['side_support']).any(axis=1));whole=potential_whole_bound_charts(v,f,ch,changed_rows)
        allowed=set(direct+paired+intervals+lining+whole+widths)
        if any(i<10 for i in allowed):allowed.add(10)
        if any(i<11 for i in allowed):allowed.add(11)
        actual=[i for i in range(12) if chart_digest(v,f,ch,i)!=chart_digest(vv,ff,cc,i)]
        grid=None
        if name!='face25':
            index=5 if name=='lining_edge64' else 2;before,nb=cells_for(m,a,v,f,ch,SOURCE,index);after,na=cells_for(mm,aa,vv,ff,cc,src,index)
            grid={'chart':index,'before_cells':len(before),'after_cells':len(after),'changed_grid_coordinates':len(before^after),'before_candidates':nb,'after_candidates':na,'pitch_m':.025,'normal_thickness_m':.025,'origin':[0,0,0],'output_repair':False}
        fixtures.append({'fixture':name,'actual_changed_pixels':int(np.any(src!=SOURCE,2).sum()),'pixel_box_xyxy':box,'actual_pixel_sha256':rawsha(src),
          'changed_primary_masks':direct,'changed_lining_candidate_masks':lining,'changed_lining5_mask_pixels':int((a['lining_5_side_candidate']!=aa['lining_5_side_candidate']).sum()),
          'changed_full_width_section_charts':widths,'changed_height_correspondence_charts':intervals,'changed_side_panel_candidates':paired,'changed_whole_side_rows':changed_rows.tolist(),
          'potential_whole_side_bound_dependency_charts':whole,'allowed_dependency_charts':sorted(allowed),'actual_changed_geometry_charts':actual,
          'outside_dependency_changes':sorted(set(actual)-allowed),'outside_scope_exact':not(set(actual)-allowed),'actual_common_occupancy':grid,
          'limitation':'Whole silhouette bounds/gauges create explicit same-height uncertainty dependencies in unpaired charts; do not claim strict same-panel-only locality.'})
        del mm,aa,vv,ff,cc,ppp,rr
    rejects={}
    try:build(None,a,SOURCE)
    except ValueError as e:rejects['missing_measurement']=str(e)
    src=SOURCE.copy();src[275:624,655:1050]=[255,0,0]
    try:extract(src)
    except ValueError as e:rejects['contradictory_side']=str(e)
    out={'same_source_arrays_bit_exact':exact,'same_measured_input_bit_exact':measured,'actual_pixel_regressions':fixtures,'required_input_rejections':rejects,
      'input_region_coverage':m['previous_measurement']['coverage'],'fitter_sha256':sha(Path(__file__).with_name('fit_width.py')),'verifier_sha256':sha(__file__),
      'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'compiler_sha256':sha(REPO/'voxel_character/common/core.py'),
      'art_shape_complete_character_approval':False,'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
    write(BASE/'evidence/verification.json',out);print(json.dumps(out))

if __name__=='__main__':run()
