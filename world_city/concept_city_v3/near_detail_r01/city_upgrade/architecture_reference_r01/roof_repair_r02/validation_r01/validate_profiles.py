#!/usr/bin/env python3
"""Independent exact source-to-profile mapping and finite chimney contract.
Shape data is inspected only. No continuous geometry is sampled or compiled.
"""
from validate_exterior import *
from validate_cells import source_masks
import copy,itertools,sys,gc
sys.path.insert(0,str(ROOT))
from voxel_character.common import core

def validate_geometry(master,plan,tiles,colors,intersection,slope):
    core.validate_master(master,PITCH)
    assert master['grid_origin']==[0,0,0] and len(master['components'])==1 and len(master['instances'])==1
    assert master['assembly_cuts']==[] and master['instances'][0].get('transform',{})=={},'Unexpected source transform or assembly cut'
    meta=master['metadata']
    assert meta['brightness_to_height'] is False and meta['original_global_registration_accepted'] is False and meta['chimney_consistency_accepted'] is False
    assert meta['thin_tile_normal_thickness_prior_m']==.0625 and meta['barrel_normal_crest_prior_m']==.0625
    assert meta['continuous_support_vertical_thickness_prior_m']==.125 and meta['seam_separator_prior_px']==1 and meta['local_pitch_m']==PITCH
    assert meta['chimney_depth_prior_m']==1.0 and meta['chimney_center_z_prior_m']==-3.5625 and meta['chimney_z_observation_disagreement_m']==.5
    operations=master['components'][0]['operations'];ops={op['id']:op for op in operations};assert len(ops)==len(operations)
    regions={r['id']:r for r in tiles['regions']};links={r['operation']:r for r in plan['tile_source_links']};assert len(regions)==len(links)==339
    coeff=tiles['conditional_mapping']['coefficients'];sx,sz,tx,tz=[coeff[k] for k in ['sx','sz','tx','tz']]
    checked=set()
    def top(x):return 13.875-slope*abs(x)
    def slab(x0,x1,z0,z1):return {'kind':'extrusion','polygon':[[x0,top(x0)-.1875],[x1,top(x1)-.1875],[x1,top(x1)-.0625],[x0,top(x0)-.0625]],'z_min':z0,'z_max':z1}
    anchors=tiles['conditional_mapping']['anchors'];xl,xh=anchors['target_x_interval_diagnostic_m'];zl,zh=anchors['target_z_interval_diagnostic_m']
    for side,lo,hi in [('left',xl,0.),('right',0.,xh)]:
        count=math.ceil((hi-lo)/.25)
        for i in range(count):
            name=f'support_{side}_{i:02d}';op=ops[name];x0=lo+(hi-lo)*i/count;x1=lo+(hi-lo)*(i+1)/count
            assert op=={'id':name,'part':'thin_roof_support','action':'paint','material':'top_tile_00','shape':slab(x0,x1,zl,zh)},'Support exceeds declared thin envelope'
            checked.add(name)
    for name,r in regions.items():
        link=links[name];assert link['source_bbox_px']==r['bbox_px'] and link['source_color']==r['color'] and link['partial_endpoints']==r['partial_endpoints_left_top_right_bottom'],'Tile source link mismatch'
        u0,v0,u1,v1=r['bbox_px'];x0=sx*(u0+.5)+tx;x1=sx*(u1-.5)+tx;z0=sz*(v0+.5)+tz;z1=sz*(v1-.5)+tz
        assert x0<x1 and z0<z1 and x0*x1>=0
        signed_slope=slope if x1<0 else -slope;c=1/math.sqrt(1+signed_slope**2)
        basis=[[0,-signed_slope*c,c],[0,c,signed_slope*c],[-1,0,0]]
        width=z1-z0;abscissae=[-width/2,-width/4,0,width/4,width/2];heights=[0,.046875,.0625,.046875,0]
        polygon=[[x,y-.0625] for x,y in zip(abscissae,heights)]+[[x,y] for x,y in reversed(list(zip(abscissae,heights)))]
        shape={'kind':'extrusion','polygon':polygon,'z_min':-.125,'z_max':(x1-x0)/c+.125}
        transform={'translation':[x0,top(x0)-.0625,(z0+z1)/2],'basis':basis}
        wanted={'id':name,'part':'measured_tile_regions','action':'paint','material':f'top_tile_{r["color"]["palette_id"]:02d}','shape':shape,'transform':transform}
        assert ops[name]==wanted,'Tile barrel profile, thickness, transform, material or source interval mismatch'
        assert link['horizontal_footprint_xz']==[x0,z0,x1,z1] and link['thin_normal_thickness_prior_m']==.0625 and link['normal_crest_prior_m']==.0625
        low,high=core.shape_bounds(shape);corners=[core.apply(core.transform(transform),p) for p in itertools.product(*zip(low,high))]
        wlo=[min(p[i] for p in corners)-PITCH for i in range(3)];whi=[max(p[i] for p in corners)+PITCH for i in range(3)]
        crops=[]
        for side,left,right in [('left',wlo[0],x0),('right',x1,whi[0])]:
            cid=name+'_crop_'+side;expected={'id':cid,'part':'measured_tile_regions','action':'cut','selector':{'feature':name},'shape':{'kind':'box','min':[left,wlo[1],wlo[2]],'max':[right,whi[1],whi[2]]}}
            assert ops[cid]==expected,'Tile crop is not exact feature-specific horizontal source trim'
            checked.add(cid);crops.append(cid)
        assert link['common_feature_crop_ops']==crops
        assert [op['id'] for op in operations][[op['id'] for op in operations].index(name):][:3]==[name,*crops],'Tile paint/crop operation order changed'
        checked.add(name)
    yyxx=np.argwhere(intersection);assert len(yyxx)==125
    observations=np.array([(colors[0][y,x]+colors[1][y,x])/2 for y,x in yyxx]);order=np.argsort(observations.mean(1));selected=[order[int((len(order)-1)*fraction)] for fraction in [.15,.5,.85]];palette=np.rint(observations[selected]).astype(int)
    expected_materials={f'top_tile_{p["id"]:02d}':''.join(f'{v:02x}' for v in p['rgb']) for p in tiles['palette']}
    expected_materials.update({f'chimney_gray_{i:02d}':''.join(f'{v:02x}' for v in rgb) for i,rgb in enumerate(palette)})
    assert master['materials']==expected_materials,'Invented tile or chimney source color'
    chimney_links={l['operation']:l for l in plan['chimney_source_links']};assert len(chimney_links)==125
    for y,x in yyxx:
        color=(colors[0][y,x]+colors[1][y,x])/2;material=int(np.argmin(((palette-color)**2).sum(1)));name=f'finite_chimney_y{y}_x{x}'
        expected={'id':name,'part':'finite_chimney_prior','action':'paint','material':f'chimney_gray_{material:02d}','shape':{'kind':'box','min':[(int(x)-48)*.125,int(y)*.125,-4.0625],'max':[(int(x)-47)*.125,(int(y)+1)*.125,-3.0625]}}
        assert ops[name]==expected,'Finite chimney violates neutral-pixel XY silhouette or explicit 1m depth prior'
        link=chimney_links[name];assert link['front_back_grid_yx']==[int(y),int(x)] and link['source_rgb_mean']==color.tolist() and link['material_id']==material,'Chimney source color/XY link mismatch'
        checked.add(name)
    assert set(ops)==checked and len(checked)==1192,'Unproven source operation'
    assert operations[-125:]==[ops[name] for name in chimney_links],'Finite chimney must follow roof operations'
    return {'all_master_operations_verified':len(checked),'source_tile_regions':339,'five_point_barrel_profiles':339,'feature_specific_crop_boxes':678,'thin_support_strips':50,'finite_chimney_source_pixel_boxes':125,'source_only_colors':9,'normal_tile_thickness_prior_m':.0625,'normal_barrel_crest_prior_m':.0625,'continuous_support_vertical_thickness_prior_m':.125,'brightness_does_not_drive_geometry':True,'chimney_hidden_depth_is_explicit_prior':True}

def run():
    started=time.monotonic();master=read(R/'roof_patch.master.json.gz');plan=read(R/'plan.json');tiles=read(ARCH/'roof_repair_r01/tile_measurement_r01/tile_regions.json')
    masks,occ,mat,colors,slope=source_masks();intersection=masks['chimney_supported_intersection'];del masks,occ,mat;gc.collect()
    positive=validate_geometry(master,plan,tiles,colors,intersection,slope);tests={};tile=plan['tile_source_links'][0]['operation'];chimney=plan['chimney_source_links'][0]['operation']
    def bad(name,mutate):
        m=copy.deepcopy(master);p=copy.deepcopy(plan);o={op['id']:op for op in m['components'][0]['operations']};mutate(m,p,o)
        try:validate_geometry(m,p,tiles,colors,intersection,slope)
        except (ValueError,AssertionError,KeyError,TypeError,IndexError) as e:tests[name]={'rejected':True,'reason':str(e)}
        else:raise AssertionError('Malformed geometry accepted: '+name)
    bad('barrel_crest_changed',lambda m,p,o:o[tile]['shape']['polygon'][2].__setitem__(1,.125))
    bad('normal_thickness_changed',lambda m,p,o:o[tile]['shape']['polygon'][0].__setitem__(1,-.125))
    bad('tile_source_extent_changed',lambda m,p,o:o[tile]['shape'].__setitem__('z_max',20))
    bad('tile_material_changed',lambda m,p,o:o[tile].__setitem__('material','top_tile_05' if o[tile]['material']!='top_tile_05' else 'top_tile_00'))
    bad('crop_affects_all_features',lambda m,p,o:o[tile+'_crop_left'].__setitem__('selector',{}))
    bad('crop_source_boundary_changed',lambda m,p,o:o[tile+'_crop_right']['shape']['min'].__setitem__(0,0))
    bad('ten_meter_chimney_blade',lambda m,p,o:o[chimney]['shape']['max'].__setitem__(2,5))
    bad('chimney_not_source_XY',lambda m,p,o:o[chimney]['shape']['min'].__setitem__(0,-5))
    bad('chimney_color_invented',lambda m,p,o:m['materials'].__setitem__('chimney_gray_00','ff00ff'))
    bad('source_partial_flags_changed',lambda m,p,o:p['tile_source_links'][0]['partial_endpoints'].__setitem__(0,not p['tile_source_links'][0]['partial_endpoints'][0]))
    bad('brightness_to_height_enabled',lambda m,p,o:m['metadata'].__setitem__('brightness_to_height',True))
    bad('duplicate_master_operation',lambda m,p,o:m['components'][0]['operations'].append(copy.deepcopy(o[tile])))
    report={'schema':'riverstone.roof_repair_r02.independent_profile_proof.v1','status':'TECHNICAL_PASS','positive':positive,'negative_tests':tests,'negative_tests_count':len(tests),'validator':ref(Path(__file__)),'source_master':ref(R/'roof_patch.master.json.gz'),'source_plan':ref(R/'plan.json'),'geometry_sampling_calls':0,'mesher_calls':0,'source_files_mutated':False,'address_space_limit_mib':256,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-started}
    save(HERE/'profile_validation.json',report);print(json.dumps({'status':report['status'],'positive':positive,'negative_tests':len(tests),'peak_rss_kib':report['peak_rss_kib'],'elapsed_seconds':report['elapsed_seconds']}))
if __name__=='__main__':run()
