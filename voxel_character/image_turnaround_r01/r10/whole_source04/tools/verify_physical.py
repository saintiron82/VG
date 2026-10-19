"""Replay actual pixels -> measurements -> curvature surface -> common cells.

Fixtures are held in memory. No baseline geometry, masks, or cells are repaired.
"""
from physical_depth import *
from verify_hole_aware import chart_digest
from review_hole_aware import mats
import review_surface as view
view.A=previous.A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def curve_coords(m):
    return [{name:[q['xy_px'] for q in val['boundary']]
             for name,val in chart['views'].items()}
            for chart in m['base_measurement']['previous_measured_curves']['charts']]

def chart_cells(m,a,v,f,ch,source,i):
    ma=base.make_master(m,a,v,f[ch==i],ch[ch==i],source)
    co=compile_master(ma,{'pitch':.025},max_candidate_cells=80000,max_output_cells=20000)
    return {tuple(row[:3]) for row in co['cells']},co['candidate_cells']

def run():
    start=time.monotonic();m,a=load();saved=np.load(BASE/'generated/continuous_costume.npz')
    v,f,ch,pp,rep,seams=build(m,a,SOURCE)
    same={'all_source_arrays_bit_exact':all(np.array_equal(x,saved[k]) for x,k in
          [(v,'vertices'),(f,'triangles'),(ch,'charts'),(pp,'primary_pixels')])}
    mm,aa=extract(SOURCE)
    same.update({'independent_measurement_arrays_bit_exact':all(np.array_equal(a[k],aa[k]) for k in a),
                 'independent_measured_boundary_coordinates_exact':curve_coords(m)==curve_coords(mm)})
    del mm,aa
    primary=[]
    for i in range(12):
        pred=view.project_exact(view.source_render(v,f[ch==i],mats()),C['views']['back'] if i==11 else F)
        target=a[f'owned_{i}'];p=v[f[ch==i]];area=np.cross(p[:,1,:2]-p[:,0,:2],p[:,2,:2]-p[:,0,:2])
        primary.append({'chart':i,'primary_mask_exact':bool(np.array_equal(pred,target)),
          'missing_px':int((target&~pred).sum()),'outside_px':int((pred&~target).sum()),
          'parameter_foldover':bool((area>1e-14).any() and (area<-1e-14).any()),
          'measured_mask_components':int(ndi.label(target)[1])})
    fixtures=[]
    for name,box in [('train100',[591,582,601,592]),('face25',[315,185,320,190])]:
        src=SOURCE.copy();x0,y0,x1,y1=box;src[y0:y1,x0:x1]=[255,0,0]
        mm,aa=extract(src);vv,ff,cc,ppp,rr,ss=build(mm,aa,src)
        direct=[i for i in range(12) if not np.array_equal(a[f'owned_{i}'],aa[f'owned_{i}'])]
        c0,c1=curve_coords(m),curve_coords(mm);boundary=[i for i in range(10) if c0[i]!=c1[i]]
        actual=[i for i in range(12) if chart_digest(v,f,ch,i)!=chart_digest(vv,ff,cc,i)]
        # Explicit dependency graph: changed front domains/depths can constrain
        # rear overlap; named measured curves also supply residual boundary gauges.
        allowed=set(direct)|set(boundary)
        if boundary:allowed.add(10)
        if 0 in boundary:allowed.update([3,4,9])
        if any(i<11 for i in allowed):allowed.add(11)
        cell_result=None
        if name=='train100':
            before,nb=chart_cells(m,a,v,f,ch,SOURCE,2);after,na=chart_cells(mm,aa,vv,ff,cc,src,2)
            cell_result={'chart':2,'before_cells':len(before),'after_cells':len(after),
              'changed_grid_positions':len(before^after),'before_candidates':nb,'after_candidates':na,
              'pitch_m':.025,'origin':[0,0,0],'normal_thickness_m':.025,
              'coordinates_changed':sorted([list(q) for q in before^after]),
              'output_repair':False,'source_change_reaches_actual_common_occupancy':bool(before^after)}
        fixtures.append({'fixture':name,'pixel_box_xyxy':box,'source_rgb':[255,0,0],
          'actual_changed_pixel_count':int(np.any(src!=SOURCE,2).sum()),'source_pixel_sha256':rawsha(src),
          'directly_changed_owned_charts':direct,'actual_boundary_coordinate_changed_charts':boundary,
          'allowed_dependency_charts':sorted(allowed),'actual_changed_geometry_charts':actual,
          'outside_declared_dependency_changes':sorted(set(actual)-allowed),
          'outside_scope_exact':not(set(actual)-allowed),'actual_common_grid_regression':cell_result})
        del mm,aa,vv,ff,cc,ppp,rr,ss
    rejects={}
    try:build(None,a,SOURCE)
    except ValueError as e:rejects['missing_measurement']=str(e)
    src=SOURCE.copy();src[275:624,655:1050]=[255,0,0]
    try:extract(src)
    except ValueError as e:rejects['contradictory_side']=str(e)
    source_pass=all(same.values()) and all(q['primary_mask_exact'] and not q['parameter_foldover'] for q in primary)
    causal_pass=all(q['outside_scope_exact'] for q in fixtures) and fixtures[0]['actual_common_grid_regression']['source_change_reaches_actual_common_occupancy'] and not fixtures[1]['actual_changed_geometry_charts']
    out={'status':'REPRODUCIBLE MEASUREMENT PROCESS ONLY; ART/CONNECTIVITY FAILURE RETAINED',
      'same_input':same,'primary_masks':primary,'actual_pixel_regressions':fixtures,
      'required_input_rejections':rejects,'source_replay_and_primary_masks_pass':source_pass,
      'pixel_causality_and_dependency_scope_pass':causal_pass,
      'rear_fit_remains':rep[-1]['fit'],'source_sha256':sha(BASE/'generated/continuous_costume.npz'),
      'generator_sha256':sha(Path(__file__).with_name('physical_depth.py')),
      'verifier_sha256':sha(__file__),'compiler_sha256':sha(REPO/'voxel_character/common/core.py'),
      'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
    write(BASE/'evidence/verification.json',out);print(json.dumps(out))

if __name__=='__main__':run()
