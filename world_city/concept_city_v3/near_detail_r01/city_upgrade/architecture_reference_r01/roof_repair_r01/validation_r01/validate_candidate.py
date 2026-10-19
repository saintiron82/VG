#!/usr/bin/env python3
"""Independent roof-only candidate proof: exact source priority and every face."""
from validate_exterior import *
import copy,gc,sys
sys.path.insert(0,str(ROOT))
from voxel_character.common import core

class CandidateOracle(BaselineOracle):
    def __init__(self,arrays,upper):
        super().__init__(arrays)
        a=np.load(upper);self.upper=a['materials'];self.origin=a['origin_cell_xyz'];self.names=a['material_names'].tolist()
        assert a['pitch_m']==PITCH and a['join_y_m']==9.5
        self.low=(-100,0,-82);self.high=(100,224,82)
    def values(self,x,y,z):
        x,y,z=np.broadcast_arrays(x,y,z)
        out=super().values(x,y,z)
        isupper=y>=152;out[isupper]=-1
        ix=x-self.origin[0];iy=y-self.origin[1];iz=z-self.origin[2]
        valid=isupper&(ix>=0)&(ix<self.upper.shape[1])&(iy>=0)&(iy<self.upper.shape[0])&(iz>=0)&(iz<self.upper.shape[2])
        out[valid]=self.upper[iy[valid],ix[valid],iz[valid]]
        return out

def prove_occupancy(oracle):
    base=ARCH/'foundation_repair_r01';original=ARCH/'reconstruction_proof_r01'
    a=np.load(base/'foundation_arrays.npz');occ=a['occupancy'];mat=a['materials']
    ownership=np.load(R/'ownership_arrays.npz');removed=ownership['removed_roof'];kept=ownership['kept_occupancy'];km=ownership['kept_materials']
    measured=read(original/'roof_measurement_r01/measurements.json')
    slopes=[abs(f['slope_px_per_px']) for v in measured['front_back_gable_profile_fits'].values() for f in v['left_right_upper_tile_envelope_fits']]
    slope=sum(slopes)/len(slopes)
    y=(np.arange(112)[:,None,None]+.5)*.125;x=(np.arange(96)[None,:,None]-48+.5)*.125;z=np.arange(80)[None,None,:]
    height=13.875-slope*np.abs(x)
    allowed_band=(y>=9.5)&(y>=height-.5)&(y<=height+.1875)&(np.abs(x)>=.1875)
    source=np.load(original/'image_derived_arrays.npz')
    def strict_red(rgb):return (rgb[:,:,0]>rgb[:,:,1]*1.7)&(rgb[:,:,1]>rgb[:,:,2]*1.2)&(rgb[:,:,0]>80)
    redfront=strict_red(source['front_rgb'])[:,:,None];redback=strict_red(source['back_rgb'])[:,:,None]
    expected_removed=occ&allowed_band&(((z>=3)&(z<77))|((z>=77)&redfront)|((z<3)&redback))
    assert np.array_equal(removed,expected_removed),'Removal mask differs from explicitly measured roof ownership rule'
    assert np.array_equal(kept,occ&~removed),'Kept occupancy differs outside roof ownership'
    assert np.array_equal(km,np.where(kept,mat,-1)),'Kept source material changed'
    assert not removed[:76].any(),'Lower source removal'
    assert np.array_equal(km[:76],np.where(occ[:76],mat[:76],-1)),'Lower source material changed'
    aa=np.load(R/'upper_union_arrays.npz');retained=aa['retained_baseline']
    expected=np.full_like(oracle.upper,-1);unchanged_upper=0
    for iy in range(expected.shape[0]):
        cy=(iy+150)//2
        row=np.where(kept[cy],mat[cy],-1).repeat(2,axis=0).repeat(2,axis=1)
        expected[iy,4:196,2:162]=row
        if iy>=2:unchanged_upper+=int((row>=0).sum())
    assert np.array_equal(retained,expected>=0),'Retained upper-baseline provenance mask mismatch'
    assert np.array_equal(oracle.upper[retained],expected[retained]),'Original upper occupied materials changed'
    patch=read(R/'roof_patch.compiled.json.gz');master=read(R/'roof_patch.master.json.gz')
    core.validate_master(master,PITCH)
    assert patch['schema']=='riverstone.voxel.compiled.v1' and patch['valid'] is True
    assert patch['pitch']==PITCH and patch['grid_origin']==[0,0,0]
    assert core.digest(patch['cells'])==patch['payload_hash'],'Compiled cell payload mismatch'
    assert core.digest(master)==patch['master_hash'],'Compiled master provenance mismatch'
    operations={op['id']:op for c in master['components'] for op in c['operations']}
    ids={n:i for i,n in enumerate(oracle.names)};seen=np.zeros_like(expected,dtype=np.bool_)
    inserted=blocked=0
    for row in patch['cells']:
        assert isinstance(row,list) and len(row)==7 and all(type(v)is int for v in row[:3]),'Malformed compiled cell'
        x,y,z,instance,part,material,feature=row
        assert material in ids and feature in operations and operations[feature]['material']==material and operations[feature]['part']==part,'Compiled cell source feature/material mismatch'
        assert y>=152,'New roof enters preserved lower section'
        ix=x+100;iy=y-150;iz=z+82
        assert 0<=iy<expected.shape[0] and 0<=ix<expected.shape[1] and 0<=iz<expected.shape[2],'Compiled cell outside bounded upper'
        assert not seen[iy,ix,iz],'Duplicate patch cell'
        seen[iy,ix,iz]=True
        if expected[iy,ix,iz]<0:expected[iy,ix,iz]=ids[material];inserted+=1
        else:blocked+=1
    assert np.array_equal(expected,oracle.upper),'Actual upper differs from exact baseline-first + compiled roof cell union'
    assert np.array_equal(oracle.upper[:2],expected[:2]),'Join halo differs'
    owned_count=int(removed.sum());lower_count=int(occ[:76].sum());patch_count=len(patch['cells'])
    del patch,master,seen,expected;gc.collect()
    return {'removed_roof_cells':owned_count,'removal_mask_matches_source_semantic_rule':True,'nonroof_coarse_occupied_cells_preserved':int(kept.sum()),'lower_coarse_occupied_cells_preserved':lower_count,'upper_original_occupied_fine_cells_preserved':unchanged_upper,'original_materials_preserved':True,'foundation_exact':bool(np.array_equal(km[:10],np.where(occ[:10],mat[:10],-1))),'exact_baseline_priority_union':True,'upper_halo_exact':True,'all_other_upper_empty_cells_unchanged':True,'new_roof_inserted_fine_cells':inserted,'new_roof_overlap_blocked_cells':blocked,'compiled_patch_cells':patch_count,'bounded_compiled_payload_and_master_hash_valid':True}

def provenance():
    plan=read(R/'plan.json');pin=read(R/'input_pin_revision_r02.json');tiles=read(R/'tile_measurement_r01/tile_regions.json')
    for p,h in pin['current_source_dependencies'].items():assert sha(ROOT/p)==h,('Pinned dependency drift',p)
    for k in ('original_plan','original_compilation'):
        x=pin[k];assert sha(ROOT/x['path'])==x['sha256']
    regions={r['id']:r for r in tiles['regions']}
    assert len(plan['source_links'])==len(regions)==339
    for link in plan['source_links']:
        r=regions[link['operation']]
        assert link['source_bbox_px']==r['bbox_px'] and link['source_color']==r['color'] and link['partial_endpoints']==r['partial_endpoints_left_top_right_bottom']
    master=read(R/'roof_patch.master.json.gz')
    core.validate_master(master,PITCH)
    expected_materials={f'top_tile_{p["id"]:02d}':''.join(f'{v:02x}' for v in p['rgb']) for p in tiles['palette']}
    assert master['materials']==expected_materials,'Master palette differs from source-pixel palette'
    assert master['grid_origin']==[0,0,0] and len(master['components'])==1 and len(master['instances'])==1
    assert master['assembly_cuts']==[] and master['instances'][0].get('transform',{})=={},'Unexpected source transform/cut'
    ops={op['id']:op for op in master['components'][0]['operations']}
    slope=plan['measured_gable_average_slope'];coef=plan['conditional_top_mapping']
    def expected_shape(x0,x1,z0,z1,bottom,top):
        ys=[13.875-slope*abs(x) for x in [x0,x1]]
        return {'kind':'extrusion','polygon':[[x0,ys[0]+bottom],[x1,ys[1]+bottom],[x1,ys[1]+top],[x0,ys[0]+top]],'z_min':z0,'z_max':z1}
    checked=set()
    for identity,r in regions.items():
        op=ops[identity];u0,v0,u1,v1=r['bbox_px'];x0=coef['sx']*(u0+.5)+coef['tx'];x1=coef['sx']*(u1-.5)+coef['tx'];z0=coef['sz']*(v0+.5)+coef['tz'];z1=coef['sz']*(v1-.5)+coef['tz']
        shape=expected_shape(x0,x1,z0,z1,-.0625,0.)
        assert op['shape']==shape and op['material']==f'top_tile_{r["color"]["palette_id"]:02d}' and op['part']=='measured_tile_regions' and op['action']=='paint','Master tile is not the measured source region and declared prior'
        assert op.get('transform',{})=={} and op.get('selector',{})=={},'Unexpected tile transformation or selector'
        checked.add(identity)
    anchors=tiles['conditional_mapping']['anchors'];xl,xh=anchors['target_x_interval_diagnostic_m'];zl,zh=anchors['target_z_interval_diagnostic_m']
    for side,lo,hi in [('left',xl,0.),('right',0.,xh)]:
        count=math.ceil((hi-lo)/.25)
        for i in range(count):
            identity=f'support_{side}_{i:02d}';op=ops[identity];x0=lo+(hi-lo)*i/count;x1=lo+(hi-lo)*(i+1)/count
            assert op['shape']==expected_shape(x0,x1,zl,zh,-.25,-.0625) and op['material']=='top_tile_00' and op['part']=='thin_roof_support' and op['action']=='paint','Master support differs from declared bounded prior'
            assert op.get('transform',{})=={} and op.get('selector',{})=={},'Unexpected support transformation or selector'
            checked.add(identity)
    assert checked==set(ops),'Unproven source operation present'
    assert plan['thickness_prior_m']==.0625 and plan['support_prior_m']==.1875 and plan['seam_separator_prior_px']==1.
    changed=[p for p,h in plan['source_dependencies'].items() if sha(ROOT/p)!=h]
    assert changed==pin['changed_dependencies']
    return {'current_pinned_dependencies_exact':True,'source_region_links_exact':339,'all_master_operations_match_source_regions_or_declared_support_prior':len(checked),'original_plan_changed_dependencies':changed,'pin_revision':ref(R/'input_pin_revision_r02.json')}

def lower_face_identity(render):
    baseline=read(ARCH/'foundation_repair_r01/foundation_repaired.render.json.gz')
    def lower(r):
        ans=[]
        for g in r['groups']:
            for q in g['quads']:
                n=cross(sub(q[1],q[0]),sub(q[2],q[0]));ys=[p[1] for p in q]
                owner_below=(ys[0]<9.5 or (ys[0]==9.5 and n[1]>0)) if min(ys)==max(ys) else max(ys)<=9.5
                if owner_below:ans.append((g['material'],tuple(tuple(v) for v in q)))
        return sorted(ans)
    old=lower(baseline);new=lower(render)
    assert old==new,'Lower retained render quads changed'
    return {'identical_lower_original_quads':len(old),'lower_original_quads_exact_ordered_vertex_and_material_match':True}

def run():
    started=time.monotonic();frozen_files=[R/n for n in ['roof_repaired.render.json.gz','upper_union_arrays.npz','ownership_arrays.npz','roof_patch.compiled.json.gz','roof_patch.master.json.gz','plan.json','compile.json','composition.json','input_pin_revision_r02.json']]
    before={str(p.relative_to(ROOT)):sha(p) for p in frozen_files}
    assert before[str((R/'roof_repaired.render.json.gz').relative_to(ROOT))]=='933130b0a37e35644b8a9b6178c19bb3fc16c46ac072252b7c9ff27504482e1e'
    oracle=CandidateOracle(ARCH/'foundation_repair_r01/foundation_arrays.npz',R/'upper_union_arrays.npz')
    cellproof=prove_occupancy(oracle);prov=provenance();render=read(R/'roof_repaired.render.json.gz')
    lower=lower_face_identity(render);adapter,order=adapter_order()
    faceproof=audit_render(render,oracle,{n:i for i,n in enumerate(oracle.names)},order,extra_interfaces={(2,z) for z in [-82,-50,-18,14,46,78,82]})
    report={'schema':'riverstone.roof_repair.independent_candidate_validation.v1','status':'PASS' if faceproof['outward_CCW_matches_actual_solid_exterior'] else 'FAIL','candidate_render':ref(R/'roof_repaired.render.json.gz'),'validator':ref(Path(__file__)),'face_validator':ref(HERE/'validate_exterior.py'),'godot_adapter':ref(adapter),'occupancy_and_material':cellproof,'lower_render_identity':lower,'source_provenance':prov,'exterior_face_audit':faceproof,'input_files':before,'inputs_unchanged_during_validation':all(sha(ROOT/p)==h for p,h in before.items()),'sampling_calls':0,'mesher_calls':0,'full_house_fine_volume_allocated':False,'address_space_limit_mib':256,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-started}
    save(HERE/'candidate_validation.json',report)
    print(json.dumps({k:report[k] for k in ['status','occupancy_and_material','lower_render_identity','exterior_face_audit','inputs_unchanged_during_validation','peak_rss_kib','elapsed_seconds']},sort_keys=True))
    assert report['status']=='PASS' and report['inputs_unchanged_during_validation']
if __name__=='__main__':run()
