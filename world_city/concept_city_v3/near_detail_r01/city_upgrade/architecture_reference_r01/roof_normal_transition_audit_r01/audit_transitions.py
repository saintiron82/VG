#!/usr/bin/env python3
"""Count-only exact piecewise-top ownership audit. No shading/sidecar construction."""
import os, sys
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
from pathlib import Path
OUT=Path(__file__).resolve().parent; A=OUT.parent
R2,R3,R4=[A/('roof_repair_r0'+str(i)) for i in (2,3,4)]
sys.path.insert(0,str(R3/'normal_split_diagnostic_r01'))
from build_split_diagnostic import SourceTile,read,sha,stream_quads,qspec,rect,faces,np,resource,time,json,collections,gc,math
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(45,)*2)
ROOT=next(p for p in OUT.parents if(p/'voxel_character/common/core.py').exists())
P=.03125; EPS=1e-9
PIN='45e9b206d2b126df7dd2ce878f70ada312a122a49c9a958098d08ae1406cb4d5'
SIDEPIN='65d9d55e80692809bbe5809d212e8d183afdd90e4a3ca6cfa9ec74e5f7135e70'
TARGETS=('profile_crease_crossing','profile_crease_neighbor_ambiguity')


def extrema_points(poly,top):
    """All vertices of a rectangle partitioned by every profile-knot plane.
    With local x = +/- world Z, each cell is a polygon and signed top height
    is affine on that cell. Its extrema occur at these vertices, not samples.
    """
    pts=list(poly)
    for a,b in zip(poly,poly[1:]+poly[:1]):
        for x,y in top[1:-1]:
            if min(a[0],b[0])+1e-12<x<max(a[0],b[0])-1e-12:
                f=(x-a[0])/(b[0]-a[0]); pts.append([a[i]+f*(b[i]-a[i]) for i in range(3)])
    return pts


def signed(t,p):
    s=t.seg(p[0])
    return None if s is None else p[1]-t.height(p[0],s)


def inspect_face(t,q,cell,axis,sign):
    wc=[(v+.5)*P for v in cell]; wn=wc.copy();wn[axis]+=sign*P
    lc,ln=t.local(wc),t.local(wn)
    center_domain=(t.x0+EPS<wc[0]<t.x1-EPS and t.x0+EPS<wn[0]<t.x1-EPS
        and t.top[0][0]+EPS<lc[0]<t.top[-1][0]-EPS and t.top[0][0]+EPS<ln[0]<t.top[-1][0]-EPS
        and t.op['shape']['z_min']+EPS<lc[2]<t.op['shape']['z_max']-EPS
        and t.op['shape']['z_min']+EPS<ln[2]<t.op['shape']['z_max']-EPS)
    sc,sn=signed(t,lc),signed(t,ln)
    center_ok=center_domain and sc is not None and sn is not None and -.0625-EPS<=sc<=EPS and sn>EPS
    base={'owner_center_signed_top':sc,'exterior_center_signed_top':sn,
          'owner_center_segment':t.seg(lc[0]),'exterior_center_segment':t.seg(ln[0]),
          'center_top_pair_proven':center_ok}
    wplanes=[]; lplanes=[]
    for side in (-1,1):
        ps=[]
        for p in q:
            z=p.copy();z[axis]+=side*sign*P/2;ps.append(z)
        wplanes.append(ps);lplanes.append([t.local(p) for p in ps])
    allw=wplanes[0]+wplanes[1];allp=lplanes[0]+lplanes[1]
    margins={'crop':min(min(p[0]-t.x0,t.x1-p[0]) for p in allw),
             'barrel':min(min(p[0]-t.top[0][0],t.top[-1][0]-p[0]) for p in allp),
             'extrusion':min(min(p[2]-t.op['shape']['z_min'],t.op['shape']['z_max']-p[2]) for p in allp),
             'source_footprint_z':min(min(p[2]-t.z0,t.z1-p[2]) for p in allw)}
    base['full_prism_domain_margins']=margins
    for name in ('crop','barrel','extrusion','source_footprint_z'):
        if margins[name]<=EPS:return base,'full_prism_'+name+'_boundary'
    base['full_prism_domain_proven']=True
    plo=min(p[0] for p in allp);phi=max(p[0] for p in allp)
    segs=[i for i,(a,b) in enumerate(zip(t.top,t.top[1:])) if b[0]>=plo-1e-12 and a[0]<=phi+1e-12]
    hemis=[sign*t.normal(i)[axis] for i in segs]
    base['touched_profile_segments']=segs
    base['touched_facet_cardinal_hemisphere']=hemis
    base['all_touched_facet_normals_strictly_outward']=min(hemis)>1e-10
    extrema=[extrema_points(p,t.top) for p in lplanes]
    vals=[[signed(t,p) for p in poly] for poly in extrema]
    assert all(v is not None for vs in vals for v in vs)
    base['owner_plane_signed_top_range']=[min(vals[0]),max(vals[0])]
    base['exterior_plane_signed_top_range']=[min(vals[1]),max(vals[1])]
    base['piecewise_affine_extremum_point_counts']=[len(p) for p in extrema]
    if min(vals[0])<-.0625-EPS:return base,'owner_plane_crosses_authored_bottom'
    if max(vals[0])>EPS:return base,'owner_plane_not_entirely_below_top'
    if min(vals[1])<=EPS:return base,'exterior_plane_not_entirely_above_top'
    base['full_face_continuous_top_ownership_proven']=True
    return base,'proven_continuous_top_same_source'


def main():
    start=time.monotonic();cpu=time.process_time();render=R4/'roof_repaired.render.json.gz'
    side=A/'roof_normal_full_r01/normal_split_sidecar.json.gz'
    assert sha(render)==PIN and sha(side)==SIDEPIN
    source={};features=['unknown_current_union_owner'];fid_index={features[0]:0};kind={};source_structure=[]
    def idx(fid):
        if fid not in fid_index:fid_index[fid]=len(features);features.append(fid)
        return fid_index[fid]
    paths=[render,side,R4/'upper_union_arrays.npz',R3/'delta_ownership_arrays.npz',
        A/'roof_normal_extent_r01/counts.json',A/'roof_normal_extent_r01/count_extent.py',
        R3/'normal_diagnostic_r01/derive_normal_diagnostic.py',R3/'normal_split_diagnostic_r01/build_split_diagnostic.py',
        ROOT/'voxel_character/common/core.py']
    for rev in (R2,R3,R4):paths += [rev/'roof_patch.master.json.gz',rev/'compile.json']
    for rev in (R2,R3):paths.append(rev/'plan.json')
    pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
    for k,rev in enumerate((R2,R3)):
        ma=read(rev/'roof_patch.master.json.gz');pl=read(rev/'plan.json')
        assert not ma['assembly_cuts']
        ops={o['id']:o for comp in ma['components'] for o in comp['operations']}
        cuts=[o for o in ops.values() if o['action']=='cut']
        assert len(cuts)==2*len(pl['tile_source_links'])
        for link in pl['tile_source_links']:
            fid=link['operation'];t=SourceTile(ops[fid],link);source[idx(fid)]=t
            kind[fid]='old_measured' if k==0 else 'recovered_interval'
            assert t.op['action']=='paint' and t.op['shape']['kind']=='extrusion'
            assert abs(t.B[0][0])<1e-12 and abs(t.B[1][0])<1e-12 and abs(abs(t.B[2][0])-1)<1e-12
            bottom=t.op['shape']['polygon'][:5]
            assert all(abs(a[0]-b[0])<1e-12 and abs(a[1]+.0625-b[1])<1e-12 for a,b in zip(bottom,t.top))
            ms=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(t.top,t.top[1:])]
            assert all(ms[i]>ms[i+1] for i in range(3))
            raw=[]
            for x,y in t.op['shape']['polygon']:
                for z in (t.op['shape']['z_min'],t.op['shape']['z_max']):raw.append([sum(r[j]*[x,y,z][j] for j in range(3))+v for r,v in zip(t.B,t.t)])
            low=[min(p[i] for p in raw) for i in range(3)];high=[max(p[i] for p in raw) for i in range(3)]
            assert abs(low[2]-t.z0)<EPS and abs(high[2]-t.z1)<EPS
            exact_cuts=[o for o in cuts if o.get('selector')=={'feature':fid}]
            assert {o['id'] for o in exact_cuts}=={fid+'_crop_left',fid+'_crop_right'}
            for cut in exact_cuts:
                b=cut['shape'];assert b['kind']=='box' and not cut.get('transform')
                assert all(b['min'][j]<=low[j]+EPS and b['max'][j]>=high[j]-EPS for j in (1,2))
                if cut['id'].endswith('_left'):assert b['min'][0]<=low[0]+EPS and abs(b['max'][0]-t.x0)<EPS
                else:assert b['max'][0]>=high[0]-EPS and abs(b['min'][0]-t.x1)<EPS
            source_structure.append({'source_tile_id':fid,'adjacent_facet_turn_degrees':[math.degrees(abs(math.atan(ms[i+1])-math.atan(ms[i]))) for i in range(3)]})
    assert len(source)==354
    tiles=list(source.values());overlaps=[]
    for i,t in enumerate(tiles):
        for k in range(i):
            s=tiles[k]
            if min(t.x1,s.x1)>max(t.x0,s.x0)+1e-10 and min(t.z1,s.z1)>max(t.z0,s.z0)+1e-10:overlaps.append((t.op['id'],s.op['id']))
    assert not overlaps
    m4=read(R4/'roof_patch.master.json.gz');assert not m4['assembly_cuts']
    assert all(o['action']=='paint' and o['shape']['kind']=='box' for comp in m4['components'] for o in comp['operations'])
    u=np.load(R4/'upper_union_arrays.npz');mat=u['materials'];origin=u['origin_cell_xyz'].tolist();names=u['material_names'].tolist();mids={n:i for i,n in enumerate(names)}
    delta=np.load(R3/'delta_ownership_arrays.npz')['delta_class'];owners=np.zeros(mat.shape,np.uint16)
    assigned=collections.Counter();all_compiled=0;r4_owner_ids=set();r4_changed_cells=0
    for rec in read(R2/'compile.json')['chunks']:
        p=ROOT/rec['compiled']['path'];assert sha(p)==rec['compiled']['sha256'];pins[str(p.relative_to(ROOT))]=sha(p);d=read(p)
        for x,y,z,inst,part,m,fid in d['cells']:
            iy,ix,iz=y-origin[1],x-origin[0],z-origin[2]
            if delta[iy,ix,iz]==0 and mat[iy,ix,iz]==mids[m]:owners[iy,ix,iz]=idx(fid);assigned[kind.get(fid,'other')]+=1
        all_compiled+=len(d['cells']);del d;gc.collect()
    for rev in (R3,R4):
        rec=read(rev/'compile.json')['delta'];p=ROOT/rec['path'];assert sha(p)==rec['sha256'];pins[str(p.relative_to(ROOT))]=sha(p);d=read(p)
        for x,y,z,inst,part,m,fid in d['cells']:
            iy,ix,iz=y-origin[1],x-origin[0],z-origin[2]
            if mat[iy,ix,iz]!=mids[m]:continue
            if rev==R3 and not((part=='observed_shadow_tile_extensions' and delta[iy,ix,iz]==3) or(part=='foreground_resampled_gable_edge' and delta[iy,ix,iz]==2)):continue
            owners[iy,ix,iz]=idx(fid);assigned[kind.get(fid,'other')]+=1
            if rev==R4:r4_owner_ids.add(idx(fid));r4_changed_cells+=1;assert idx(fid) not in source
        all_compiled+=len(d['cells']);del d;gc.collect()
    assert r4_changed_cells==2609
    baseline=read(A/'roof_normal_extent_r01/counts.json')
    assert all_compiled==baseline['cached_compiled_rows_scanned'] and dict(assigned)==baseline['ownership_assigned_counts']
    del delta;gc.collect();ownership_seconds=time.monotonic()-start
    def ix(c):return(c[1]-origin[1],c[0]-origin[0],c[2]-origin[2])
    total=collections.Counter();original=collections.Counter();stats={r:collections.Counter() for r in TARGETS}
    rejects={r:collections.Counter() for r in TARGETS};axes={r:collections.Counter() for r in TARGETS}
    per={r:collections.Counter() for r in TARGETS};examples={r:{} for r in TARGETS};meta={};partial=False
    for gi,qi,m,q in stream_quads(render,meta):
        total['all_render_quads']+=1
        if time.process_time()-cpu>40:partial=True;break
        if not m.startswith('top_tile_'):continue
        sp=qspec(q);lo,hi,axis,sign,u,v=sp;fs=list(faces(sp));oset={int(owners[ix(c)]) for a,b,c in fs}
        if not oset.intersection(source):continue
        total['source_candidate_quad_unit_faces']+=len(fs)
        for a,b,c in fs:
            nc=list(c);nc[axis]+=sign;assert mat[ix(c)]==mids[m] and mat[ix(nc)]<0
        if len(oset)==1:
            oid=next(iter(oset));res,why=source[oid].classify(q,[c for a,b,c in fs],axis,sign)
            if res:total['treated_unit_faces']+=len(fs);continue
        for a,b,c in fs:
            oid=int(owners[ix(c)]);reason='non_source_owner';res=None
            if oid in source:
                uq=rect(q,sp,a,b,a+1,b+1);res,reason=source[oid].classify(uq,[c],axis,sign)
            if res:total['treated_unit_faces']+=1;continue
            original[reason]+=1
            if reason not in TARGETS:continue
            t=source[oid];proof,outcome=inspect_face(t,uq,c,axis,sign);s=stats[reason];s['audited_unit_faces']+=1
            s['center_top_pair_proven']+=proof['center_top_pair_proven']
            s['full_prism_domain_proven']+=proof.get('full_prism_domain_proven',False)
            s['full_face_continuous_top_ownership_proven']+=proof.get('full_face_continuous_top_ownership_proven',False)
            eligible=proof.get('full_face_continuous_top_ownership_proven',False) and proof.get('all_touched_facet_normals_strictly_outward',False)
            s['full_face_proven_and_all_facet_normals_outward']+=eligible
            if eligible:per[reason][features[oid]]+=1
            rejects[reason][outcome]+=1;axes[reason][str(axis)+'_'+str(sign)+'_'+outcome]+=1
            key=outcome+('_outward' if eligible else '')
            if key not in examples[reason]:examples[reason][key]=[]
            if len(examples[reason][key])<2:
                examples[reason][key].append({'group_index':gi,'quad_index':qi,'source_tile_id':features[oid],'owner_cell_xyz':c,'axis':axis,'sign':sign,'unit_face_corners':uq,'original_reason':reason,'outcome':outcome,**proof})
    if not partial:
        assert total['all_render_quads']==189901
        assert total['treated_unit_faces']==98060
        assert dict(original)==baseline['preserved_candidate_unit_face_reasons'],(original,baseline['preserved_candidate_unit_face_reasons'])
        assert stats[TARGETS[0]]['audited_unit_faces']==26081 and stats[TARGETS[1]]['audited_unit_faces']==2736
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    report={'schema':'riverstone.roof.transition_ownership_audit.v1','status':'PARTIAL_CPU_CUTOFF' if partial else 'EXACT_COUNT_ONLY_ANALYSIS',
        'render_sha256':PIN,'frozen_full_sidecar_sha256':SIDEPIN,'limits':{'AS_mib':256,'CPU_hard_seconds':45,'CPU_soft_seconds':40,'all_output_bytes_max':1000000},
        'source_structure_proofs':{'source_count':354,'five_point_strictly_concave_connected_top_profiles':354,'uniform_normal_coordinate_thickness':.0625,'profile_coordinate_exactly_signed_world_Z':True,'feature_selected_full_span_endpoint_crop_boxes':708,'interior_groove_cut_operations':0,'source_horizontal_footprint_overlap_pairs':0,'R4_only_paint_boxes_no_cuts':True,'adjacent_facet_turn_degrees_range':[min(v for s in source_structure for v in s['adjacent_facet_turn_degrees']),max(v for s in source_structure for v in s['adjacent_facet_turn_degrees'])]},
        'current_ownership':{'cached_compiled_rows_scanned':all_compiled,'assigned_counts':dict(assigned),'R4_repaint_cells_excluded_from_sources':r4_changed_cells},
        'full_face_proof_definition':'For each unit face Q, use the two entire rectangles Q +/- sign*(pitch/2)*axis. They bound the owner/exterior center-to-center prism. Require the complete prism strictly within the source crop, profile, extrusion and horizontal footprint; all source horizontal footprints have zero pairwise positive-area overlap. Partition each rectangle at every exact authored profile knot. On every partition the signed local top height is affine; evaluate all original corners and every knot/edge intersection. Entire owner rectangle must lie between authored bottom and top; entire exterior rectangle strictly above top. This proves source-specific top crossing across the whole face, conservatively stronger than owner/exterior center tests. It does not manufacture a unique differentiable normal at a crease.',
        'original_preserved_reason_counts':dict(original),'totals':dict(total),'by_original_reason':{r:{'counts':dict(stats[r]),'first_failure_or_success':dict(rejects[r]),'axis_sign_outcome_counts':dict(axes[r]),'per_source_full_face_outward_count':dict(per[r])} for r in TARGETS},
        'proof_examples':examples,'normal_definition':'No normals generated. Authored polyline creases have two distinct facet normals. All-touched-facet outward tests are conservative necessary evidence for a convex adjacent-normal shading prior; interpolation would be a separate explicit authored-profile shading choice, not image-measured geometry.',
        'source_pins':pins,'all_frozen_inputs_unchanged':True,'ownership_elapsed_seconds':ownership_seconds,'elapsed_seconds':time.monotonic()-start,'CPU_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'sampler_calls':0,'compiler_calls':0,'mesher_calls':0,'GUI_calls':0,'sidecars_generated':0,'render_source_geometry_color_shadow_changes':0}
    data=json.dumps(report,indent=2,allow_nan=False)+'\n';assert len(data.encode())+sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())<1000000
    (OUT/'counts_and_proofs.json').write_text(data)
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','proof_examples','by_original_reason')},indent=2))
    print(json.dumps({r:{k:v for k,v in report['by_original_reason'][r].items() if k!='per_source_full_face_outward_count'} for r in TARGETS},indent=2))
if __name__=='__main__':main()
