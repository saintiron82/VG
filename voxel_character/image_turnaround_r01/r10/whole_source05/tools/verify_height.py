"""Independent height-matching replay and actual-pixel input causality."""
from height_correspondence import *
from verify_hole_aware import chart_digest
import review_surface as view

def cells_for(m,a,v,f,ch,source,index):
    ma=base.make_master(m,a,v,f[ch==index],ch[ch==index],source)
    co=compile_master(ma,{'pitch':.025},max_candidate_cells=80000,max_output_cells=20000)
    return {tuple(row[:3]) for row in co['cells']},co['candidate_cells']

def run():
    t=time.monotonic();m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v,f,ch,pp,report=build(m,a,SOURCE)
    exact=all(np.array_equal(x,s[k]) for x,k in [(v,'vertices'),(f,'triangles'),(ch,'charts'),(pp,'primary_pixels')]);mm,aa=extract(SOURCE)
    measurement_exact=all(np.array_equal(a[k],aa[k]) for k in a);del mm,aa
    fixtures=[]
    for name,box in [('side_edge64',[766,353,774,361]),('train100',[591,582,601,592]),('face25',[315,185,320,190])]:
        src=SOURCE.copy();x0,y0,x1,y1=box;src[y0:y1,x0:x1]=[255,0,0];mm,aa=extract(src);vv,ff,cc,ppp,rr=build(mm,aa,src)
        direct=[i for i in range(12) if not np.array_equal(a[f'owned_{i}'],aa[f'owned_{i}'])]
        constraints=[i for i in range(10) if not np.array_equal(a[f'height_constraints_{i}'],aa[f'height_constraints_{i}'])]
        paired=[i for i in range(10) if f'chart_{i}_side' in a and not np.array_equal(a[f'chart_{i}_side'],aa[f'chart_{i}_side'])]
        side_changed=not np.array_equal(a['side_support'],aa['side_support']);inner_changed=not np.array_equal(a['side_inner_candidate'],aa['side_inner_candidate'])
        allowed=set(direct+constraints+paired)
        if side_changed:allowed.update([3,4,9,10,11])
        if inner_changed:allowed.update([5,6])
        if any(i<10 for i in allowed):allowed.add(10)
        if any(i<11 for i in allowed):allowed.add(11)
        changed=[i for i in range(12) if chart_digest(v,f,ch,i)!=chart_digest(vv,ff,cc,i)]
        grid=None
        if name in ['side_edge64','train100']:
            index=0 if name=='side_edge64' else 2;before,nb=cells_for(m,a,v,f,ch,SOURCE,index);after,na=cells_for(mm,aa,vv,ff,cc,src,index)
            grid={'chart':index,'before_cells':len(before),'after_cells':len(after),'changed_grid_coordinates':len(before^after),'before_candidates':nb,'after_candidates':na,'same_pitch_m':.025,'same_thickness_m':.025,'same_origin':[0,0,0],'output_repair':False}
        fixtures.append({'fixture':name,'box_xyxy':box,'actual_changed_pixels':int(np.any(src!=SOURCE,2).sum()),'actual_pixel_sha256':rawsha(src),
          'changed_primary_masks':direct,'changed_observed_correspondence_interval_charts':constraints,'changed_side_panel_candidate_masks':paired,'whole_side_mask_changed':side_changed,'inner_side_mask_changed':inner_changed,
          'allowed_dependency_charts':sorted(allowed),'actual_changed_geometry_charts':changed,'outside_dependency_changes':sorted(set(changed)-allowed),'outside_scope_exact':not(set(changed)-allowed),'actual_common_occupancy':grid})
        del mm,aa,vv,ff,cc,ppp,rr
    reject={}
    try:build(None,a,SOURCE)
    except ValueError as e:reject['missing_measurement']=str(e)
    src=SOURCE.copy();src[275:624,655:1050]=[255,0,0]
    try:extract(src)
    except ValueError as e:reject['contradictory_side']=str(e)
    out={'same_source_geometry_bit_exact':exact,'same_source_measurements_bit_exact':measurement_exact,
      'actual_pixel_regressions':fixtures,'required_input_rejections':reject,
      'art_shape_solver_convergence_approval':False,'status':'PROCESS REGRESSION ONLY; incomplete/uncertain depth and solver limits retained',
      'generator_sha256':sha(Path(__file__).with_name('height_correspondence.py')),'verifier_sha256':sha(__file__),
      'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'compiler_sha256':sha(REPO/'voxel_character/common/core.py'),
      'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
    write(BASE/'evidence/verification.json',out);print(json.dumps(out))

if __name__=='__main__':run()
