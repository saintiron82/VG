#!/usr/bin/env python3
"""Independent r02 cell union proof, source masks and finite chimney evidence.
No shape sampler, compiler, mesher or GUI is called. Upper-only, bounded memory.
"""
from validate_exterior import *
import gc,sys
from PIL import Image
sys.path.insert(0,str(ROOT))
from voxel_character.common import core

class CandidateOracle(BaselineOracle):
    def __init__(self,arrays,upper):
        super().__init__(arrays);a=np.load(upper);self.upper=a['materials'];self.origin=a['origin_cell_xyz'];self.names=a['material_names'].tolist()
        assert a['pitch_m']==PITCH and a['join_y_m']==9.5
        assert self.origin.tolist()==[-200,300,-164] and self.upper.shape==(148,400,328)
        self.low=(-200,0,-164);self.high=(200,448,164)
    def values(self,x,y,z):
        x,y,z=np.broadcast_arrays(x,y,z);out=super().values(x,y,z)
        isupper=y>=304;out[isupper]=-1
        ix=x+200;iy=y-300;iz=z+164
        valid=isupper&(ix>=0)&(ix<400)&(iy>=0)&(iy<148)&(iz>=0)&(iz<328)
        out[valid]=self.upper[iy[valid],ix[valid],iz[valid]]
        return out

def source_masks():
    original=ARCH/'reconstruction_proof_r01';base=ARCH/'foundation_repair_r01'
    a=np.load(base/'foundation_arrays.npz');occ=a['occupancy'];mat=a['materials'];src=np.load(original/'image_derived_arrays.npz')
    image=np.asarray(Image.open(ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png').convert('RGB'))
    gray=[];colors=[]
    for box,center,reverse in [([360,60,400,141],256,False),([1136,60,1176,141],1280,True)]:
        mask=np.zeros((112,96),np.bool_);rgb=np.zeros((112,96,3),np.float32)
        for y in range(88,110):
            v0=496-(y+1)*4
            for x in range(74,86):
                u0=center+(x-48)*4 if not reverse else center-(x-47)*4
                if not (box[0]<=u0 and u0+4<=box[2] and box[1]<=v0 and v0+4<=box[3]):continue
                p=image[v0:v0+4,u0:u0+4].reshape(-1,3).astype(float);l=p.mean(1);good=(np.ptp(p,axis=1)<40)&(l>=55)&(l<210)
                if np.count_nonzero(good)>=6:mask[y,x]=True;rgb[y,x]=np.median(p[good],axis=0)
        gray.append(mask);colors.append(rgb)
    measured=read(original/'roof_measurement_r01/measurements.json');slopes=[abs(f['slope_px_per_px']) for v in measured['front_back_gable_profile_fits'].values() for f in v['left_right_upper_tile_envelope_fits']];slope=sum(slopes)/len(slopes)
    y=(np.arange(112)[:,None,None]+.5)*.125;x=(np.arange(96)[None,:,None]-48+.5)*.125;zi=np.arange(80)[None,None,:]
    line=13.875-slope*np.abs(x)
    def red(rgb):return (rgb[:,:,0]>rgb[:,:,1]*1.7)&(rgb[:,:,1]>rgb[:,:,2]*1.2)&(rgb[:,:,0]>80)
    front=red(src['front_rgb'])[:,:,None];back=red(src['back_rgb'])[:,:,None]
    shell=occ&(y>=9.5)&(y>=line-.5)&(y<=line+.1875)&(((zi>=3)&(zi<77))|((zi>=77)&front)|((zi<3)&back))
    artifacts=occ&(y>=9.5)&(y>line+.1875)&(zi>=3)&(zi<77)
    chimney=occ&(gray[0]|gray[1])[:,:,None]&(y>=9.5)
    ridge=occ&(np.abs(x)<.1875)&(y>=13.75)
    removed=(shell|artifacts|chimney)&~ridge;kept=occ&~removed;km=np.where(kept,mat,-1)
    expected={'removed_roof':removed,'roof_shell':shell,'unsupported_upper_extrude':artifacts,'chimney_extrude':chimney,'retained_ridge_cap':ridge,'kept_occupancy':kept,'kept_materials':km,'chimney_front_gray':gray[0],'chimney_back_gray':gray[1],'chimney_supported_intersection':gray[0]&gray[1]}
    return expected,occ,mat,colors,slope

def prove_cells(oracle):
    expected,occ,mat,colors,slope=source_masks();ownership=np.load(R/'ownership_arrays.npz')
    for key,value in expected.items():assert np.array_equal(ownership[key],value),'Source ownership mismatch: '+key
    kept=expected['kept_occupancy'];km=expected['kept_materials'];intersection=expected['chimney_supported_intersection']
    assert not expected['removed_roof'][:76].any() and np.array_equal(km[:76],np.where(occ[:76],mat[:76],-1)),'Lower source changed'
    a=np.load(R/'upper_union_arrays.npz');retained=a['retained_baseline'];assert retained.shape==oracle.upper.shape
    original_fine=0
    for iy in range(148):
        row=np.full((400,328),-1,np.int16);row[8:392,4:324]=km[(iy+300)//4].repeat(4,0).repeat(4,1)
        mask=row>=0
        assert np.array_equal(retained[iy],mask),'Retained mask mismatch'
        assert np.array_equal(oracle.upper[iy][mask],row[mask]),'Retained source material mismatch'
        assert not ((oracle.upper[iy]>=0)&(oracle.upper[iy]<15)&~mask).any(),'Unexpected baseline material outside retained ownership'
        if iy<4:assert np.array_equal(oracle.upper[iy],row),'Join halo mismatch'
        if iy>=4:original_fine+=int(mask.sum())
    del retained;gc.collect()
    master=read(R/'roof_patch.master.json.gz');core.validate_master(master,PITCH);mh=core.digest(master)
    operations={op['id']:op for c in master['components'] for op in c['operations']};ids={n:i for i,n in enumerate(oracle.names)}
    compilation=read(R/'compile.json');patch_total=inserted=blocked=chimney_count=0;feature_counts={};previous=-164
    links={x['operation']:x for x in read(R/'plan.json')['tile_source_links']}
    tiledata=read(ARCH/'roof_repair_r01/tile_measurement_r01/tile_regions.json');tile_regions={x['id']:x for x in tiledata['regions']};coef=tiledata['conditional_mapping']['coefficients']
    visible={k:0 for k in links};top_y=np.full((400,328),-1,np.int16)
    for iy in range(4,148):top_y[oracle.upper[iy]>=0]=iy+300
    top_class=np.where(top_y>=0,1,0).astype(np.uint8)
    tile_cells_checked=0;max_inset_footprint_overstep=0.
    chimney_extent=[[99999]*3,[-99999]*3]
    for record in compilation['chunks']:
        z0,z1=record['owned_z_cells'];assert z0==previous and z0<z1;previous=z1
        path=ROOT/record['compiled']['path'];assert sha(path)==record['compiled']['sha256']
        c=read(path);assert c['valid'] and c['schema']=='riverstone.voxel.compiled.v1' and c['pitch']==PITCH and c['grid_origin']==[0,0,0]
        assert core.digest(c['cells'])==c['payload_hash'] and c['master_hash']==mh,'Compiled provenance mismatch'
        assert len(c['cells'])==record['cells'];seen=np.zeros((148,400,z1-z0),np.bool_)
        for row in c['cells']:
            assert isinstance(row,list) and len(row)==7 and all(type(x)is int for x in row[:3]),'Malformed compiled cell'
            x,y,z,instance,part,material,feature=row;assert feature in operations and material in ids
            op=operations[feature];assert op['action']=='paint' and op['material']==material and op['part']==part,'Compiled feature provenance mismatch'
            assert -200<=x<200 and 304<=y<448 and z0<=z<z1,'Compiled cell outside owned bounds'
            iy,ix,iz=y-300,x+200,z-z0;assert not seen[iy,ix,iz],'Duplicate compiled cell';seen[iy,ix,iz]=True
            cy,cx,cz=y//4,x//4+48,z//4+40
            baseline=km[cy,cx,cz] if 0<=cy<112 and 0<=cx<96 and 0<=cz<80 else -1
            wanted=int(baseline) if baseline>=0 else ids[material]
            assert oracle.upper[iy,ix,z+164]==wanted,'Source-priority union material mismatch'
            if baseline>=0:blocked+=1
            else:inserted+=1
            feature_counts[feature]=feature_counts.get(feature,0)+1
            if baseline<0 and top_y[ix,z+164]==y:top_class[ix,z+164]={'measured_tile_regions':2,'thin_roof_support':3,'finite_chimney_prior':4}[part]
            if part=='measured_tile_regions':
                link=links[feature];tx0,tz0,tx1,tz1=link['horizontal_footprint_xz'];cxworld=(x+.5)*PITCH;czworld=(z+.5)*PITCH
                assert tx0-1e-9<=cxworld<tx1+1e-9 and tz0-1e-9<=czworld<tz1+1e-9,'Compiled tile center outside source separator inset'
                u0,v0,u1,v1=tile_regions[feature]['bbox_px'];raw=[coef['sx']*u0+coef['tx'],coef['sz']*v0+coef['tz'],coef['sx']*u1+coef['tx'],coef['sz']*v1+coef['tz']]
                assert raw[0]-1e-9<=x*PITCH and (x+1)*PITCH<=raw[2]+1e-9 and raw[1]-1e-9<=z*PITCH and (z+1)*PITCH<=raw[3]+1e-9,'Tile voxel solid extends outside original source region'
                max_inset_footprint_overstep=max(max_inset_footprint_overstep,tx0-x*PITCH,(x+1)*PITCH-tx1,tz0-z*PITCH,(z+1)*PITCH-tz1)
                tile_cells_checked+=1
                if baseline<0 and top_y[ix,z+164]==y:visible[feature]+=1
            if part=='finite_chimney_prior':
                chimney_count+=1
                assert intersection[cy,cx] and -130<=z<-98,'Finite chimney outside source silhouette or 1m depth prior'
                for axis,n in enumerate([x,y,z]):chimney_extent[0][axis]=min(chimney_extent[0][axis],n);chimney_extent[1][axis]=max(chimney_extent[1][axis],n+1)
        union=oracle.upper[:,:,z0+164:z1+164]
        assert not ((union>=15)&~seen).any(),'Added upper cell outside compiled roof/chimney union'
        patch_total+=len(c['cells']);del c,seen;gc.collect()
    assert previous==164 and patch_total==compilation['total_occupied_cells']
    assert int(intersection.sum())==125 and chimney_count==125*16*32==64000,'Finite chimney must contain exactly source-supported XY columns at depth 1m'
    assert sum(k.startswith('finite_chimney_') for k in feature_counts)==125
    assert max_inset_footprint_overstep<=PITCH/2+1e-9
    source_u=(((np.arange(400)-200+.5)*PITCH-coef['tx'])/coef['sx'])[:,None]
    source_v=(((np.arange(328)-164+.5)*PITCH-coef['tz'])/coef['sz'])[None,:]
    exclusions=[]
    for exclusion in tiledata['excluded_regions']:
        u0,v0,u1,v1=exclusion['bbox_px'];mask=(source_u>=u0)&(source_u<u1)&(source_v>=v0)&(source_v<v1)
        counts={name:int(np.count_nonzero(mask&(top_class==kind))) for kind,name in enumerate(['empty','retained_baseline','measured_tile','explicit_support_prior','finite_chimney_prior'])}
        assert counts['measured_tile']==0,'Tile first hit within excluded source ROI'
        exclusions.append({'source_bbox_px':exclusion['bbox_px'],'reason':exclusion['reason'],'top_first_hit_cell_counts':counts,'covered_XZ_area_m2':int(mask.sum())*PITCH**2})
    return {'removal_mask_matches_independent_source_rules':True,'all_ownership_submasks_exact':True,'removed_coarse_cells':int(expected['removed_roof'].sum()),'retained_nonroof_coarse_cells':int(kept.sum()),'lower_coarse_occupied_cells_preserved':int(occ[:76].sum()),'upper_original_occupied_fine_cells_preserved':original_fine,'foundation_exact':True,'all_original_retained_materials_exact':True,'upper_join_halo_exact':True,'exact_baseline_priority_union':True,'compiled_patch_cells':patch_total,'inserted_patch_cells':inserted,'blocked_by_retained_source':blocked,'finite_chimney_source_XY_cells':125,'finite_chimney_fine_cells':chimney_count,'finite_chimney_extent_cell_exclusive':chimney_extent,'finite_chimney_depth_m':1.0,'finite_chimney_center_z_m':-3.5625,'chimney_depth_is_declared_prior_not_measurement':True,'source_side_z_disagreement_m':.5,'original_global_registration_accepted':False,'tile_compiled_cells_checked':tile_cells_checked,'tile_centers_within_measured_separator_insets':True,'tile_solid_voxels_within_original_measured_boxes':True,'maximum_voxel_edge_overstep_of_separator_inset_m':max_inset_footprint_overstep,'inset_quantization_tolerance_m':PITCH/2,'top_first_hit_tile_cells_by_region':visible,'regions_with_actual_top_first_hit':sum(v>0 for v in visible.values()),'total_top_first_hit_tile_cells':sum(visible.values()),'top_visibility_area_m2':sum(visible.values())*PITCH**2,'excluded_source_rois_top_first_hit':exclusions}

def run():
    started=time.monotonic();sources=[R/n for n in ['upper_union_arrays.npz','ownership_arrays.npz','roof_patch.master.json.gz','plan.json','compile.json']];before={str(p.relative_to(ROOT)):sha(p) for p in sources}
    plan=read(R/'plan.json')
    for p,h in plan['source_dependencies'].items():assert sha(ROOT/p)==h,('Source dependency changed',p)
    oracle=CandidateOracle(ARCH/'foundation_repair_r01/foundation_arrays.npz',R/'upper_union_arrays.npz');proof=prove_cells(oracle)
    report={'schema':'riverstone.roof_repair_r02.independent_cell_proof.v1','status':'TECHNICAL_PASS','proof':proof,'input_files':before,'inputs_unchanged':all(sha(ROOT/p)==h for p,h in before.items()),'validator':ref(Path(__file__)),'geometry_sampling_calls':0,'mesher_calls':0,'full_house_fine_volume_allocated':False,'address_space_limit_mib':256,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-started}
    save(HERE/'cell_validation.json',report);print(json.dumps(report,sort_keys=True))
if __name__=='__main__':run()
