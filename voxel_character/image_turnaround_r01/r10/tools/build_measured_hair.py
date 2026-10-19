"""Measured view-local hair intervals -> small independent common extrusion ops.

No cap, asset dispatch, manually authored 3D curve, voxel compilation or repair.
Cross-view correspondence and hidden depth remain explicit hypotheses.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,time
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[2];FULL=ROOT/'full01'
BASIS=[[1,0,0],[0,0,1],[0,-1,0]]

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
    p=Path(path);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())
def gzsave(path,value):Path(path).write_bytes(gzip.compress(canonical(value),mtime=0))
def rounded(v):return round(float(v),9)
def array_digest(arrays):
    h=hashlib.sha256()
    for k in sorted(arrays):
        a=np.ascontiguousarray(arrays[k]);h.update(k.encode());h.update(str(a.shape).encode());h.update(str(a.dtype).encode());h.update(a.tobytes())
    return h.hexdigest()
def intervals(row):
    d=np.diff(np.r_[False,row,False].astype(np.int8));return np.column_stack((np.where(d==1)[0],np.where(d==-1)[0])).tolist()
def intersect_sets(left,right):
    out=[]
    for a,b in left:
        for c,d in right:
            lo,hi=max(a,c),min(b,d)
            if lo<=hi+1e-12:out.append([lo,max(lo,hi)])
    return sorted(out)
def combine_runs(rows,start_y,step):
    """Group exact same X run across consecutive native rows, at most step rows.
    A changing endpoint, a split, a gap or an isolated run is never discarded.
    """
    chunks=[];active={}
    for row in rows:
        y=row['y_px']
        if y<start_y:continue
        new={}
        for a,b in row['intervals_px']:
            key=(a,b,y//step)
            old=active.get(key)
            if old is not None and old['source_y_range'][1]==y:
                old['source_y_range'][1]=y+1;new[key]=old
            else:
                item={'source_y_range':[y,y+1],'source_interval_px':[a,b],'source_band_id':y//step};chunks.append(item);new[key]=item
        active=new
    return chunks

def polygon_overlap(a,b):
    # Strict positive-area overlap of convex sections. Touching is not overlap.
    for poly in (a,b):
        for p,q in zip(poly,poly[1:]+poly[:1]):
            n=[-(q[1]-p[1]),q[0]-p[0]]
            pa=[v[0]*n[0]+v[1]*n[1] for v in a];pb=[v[0]*n[0]+v[1]*n[1] for v in b]
            if min(max(pa),max(pb))-max(min(pa),min(pb))<=1e-12:return False
    return True

def build_hair(contract,branch_measurements,branch_masks,source,priors=None):
    priors=load(FULL/'data/hair_depth_priors.json') if priors is None else priors
    assert priors['schema']=='riverstone.measured_hair_depth_priors.v1'
    assert branch_measurements['schema']=='riverstone.measured_surface_branches.v1'
    assert contract['source_sha256']==branch_measurements['source_sha256']==priors['source_sha256']
    original=REPO/contract['source'];assert sha(original)==contract['source_sha256']
    rgb=np.asarray(Image.open(source).convert('RGB')) if isinstance(source,(str,Path)) else np.asarray(source)
    assert np.array_equal(rgb,np.asarray(Image.open(original).convert('RGB'))),'Source pixel array differs from approved image'
    assert array_digest(branch_masks)==priors['branch_arrays_sha256'],'Branch arrays changed'
    measured_gzip_sha=hashlib.sha256(gzip.compress(canonical(branch_measurements),mtime=0)).hexdigest()
    assert measured_gzip_sha==priors['branch_measurement_sha256'],'Branch measurement changed'
    height=contract['alignment']['character_height_m_for_test'];views=contract['views'];fv=views['front'];sv=views['side']
    fs=height/fv['scale_px_per_unit'];ss=height/sv['scale_px_per_unit'];yaw=sv['yaw_degrees'];angle=math.radians(yaw)
    assert 0<yaw<180
    side_mask=np.asarray(branch_masks['side__eligible__hair_visible'],bool)
    source_iris_bottom=priors['long_hair_start']['measured_front_gold_iris_bbox_bottom_y_px']
    cap_bottom=priors['long_hair_start']['head_master_front_bottom_y_px']
    mats={};parts=[];ops=[];records=[];unresolved=[];ownership=[];branch_accounting=[]
    subband_splits=0
    def side_support(xc,r,ylo,yhi):
        # Every source row represented by a sub-band contributes its real side row.
        side_rows=sorted(set(int(math.floor(sv['sole_y']-y/ss)) for y in np.arange(ylo+fs*.5,yhi+fs*.1,fs)))
        if not side_rows:side_rows=[int(math.floor(sv['sole_y']-(ylo+yhi)*.5/ss))]
        rows=[];full=None;center=None
        for sy in side_rows:
            ly=sy-sv['crop'][1]
            raw=intervals(side_mask[ly]) if 0<=ly<len(side_mask) else []
            raw=[[a+sv['crop'][0],b+sv['crop'][0]] for a,b in raw]
            fc=[];cc=[]
            for a,b in raw:
                ul,uh=(a-sv['axis_u'])*ss,(b-sv['axis_u'])*ss
                cc.append([(math.cos(angle)*xc-uh)/math.sin(angle),(math.cos(angle)*xc-ul)/math.sin(angle)])
                if uh-ul>=2*r-1e-12:
                    fc.append([(math.cos(angle)*xc-(uh-r))/math.sin(angle),(math.cos(angle)*xc-(ul+r))/math.sin(angle)])
            center=cc if center is None else intersect_sets(center,cc)
            full=fc if full is None else intersect_sets(full,fc)
            rows.append({'side_y_px':sy,'intervals_px':raw})
        return full or [],center or [],rows
    for view in ('front','back'):
        v=views[view];scale=height/v['scale_px_per_unit'];sign=priors['source_x_sign'][view]
        candidates=[b for b in branch_measurements['views'][view]['branches'] if b['source_class']=='hair_visible']
        unknown=branch_measurements['views'][view]['unknown_by_class']['hair_visible']
        candidates.append(dict(unknown,id='hair_unknown',role='hair_unknown',source_class='hair_visible'))
        for branch in candidates:
            front_threshold=cap_bottom if branch['role']=='hair_cap' else source_iris_bottom
            threshold=int(math.ceil(v['sole_y']-(fv['sole_y']-front_threshold)*fs/scale))
            key=view+'__'+branch['id'] if branch['id']!='hair_unknown' else view+'__unknown__hair_visible'
            m=np.asarray(branch_masks[key],bool)
            actual=[{'y_px':int(y+v['crop'][1]),'intervals_px':[[a+v['crop'][0],b+v['crop'][0]] for a,b in intervals(m[y])]} for y in np.where(m.any(1))[0]]
            assert actual==branch['measured_row_intervals'],'Row intervals and corresponding mask differ'
            part='long_hair_'+view+'_'+branch['id'];parts.append({'id':part,'pivot':[0,0,0]})
            chunks=combine_runs(actual,threshold,priors['row_band_source_pixels'])
            expected_pixels=sum((b-a) for row in actual if row['y_px']>=threshold for a,b in row['intervals_px'])
            removed=sum((b-a) for row in actual if row['y_px']<threshold for a,b in row['intervals_px'])
            ownership.append({'part':part,'source_start_y_px':threshold,'pixels_owned_by_head_or_above_eye':removed,'role':branch['role']})
            queue=list(chunks);accounted=0;start_record=len(records);unresolved_pixels=0
            while queue:
                chunk=queue.pop(0);ya,yb=chunk['source_y_range'];a,b=chunk['source_interval_px']
                x0,x1=sorted([sign*(a-v['axis_u'])*scale,sign*(b-v['axis_u'])*scale]);xc=(x0+x1)*.5;r=(x1-x0)*.5
                ylo,yhi=(v['sole_y']-yb)*scale,(v['sole_y']-ya)*scale
                full,center,srows=side_support(xc,r,ylo,yhi)
                if not center and yb-ya>1:
                    queue[0:0]=[dict(chunk,source_y_range=[y,y+1]) for y in range(ya,yb)];subband_splits+=1;continue
                if not center:
                    lost=(yb-ya)*(b-a);unresolved_pixels+=lost
                    unresolved.append({'part':part,**chunk,'pixels':lost,'reason':'No measured side center support at the aligned native row. Data retained; no fabricated depth or fallback geometry.'});continue
                allowed=full if full else center
                selection=allowed[-1] if view=='front' else allowed[0]
                q=priors['depth_order_quantile'][view];zc=selection[0]+q*(selection[1]-selection[0])
                n=priors['section_vertices'];poly=[[rounded(xc+r*math.cos(2*math.pi*k/n)),rounded(zc+r*math.sin(2*math.pi*k/n))] for k in range(n)]
                color=np.median(rgb[ya:yb,a:b,:3].reshape(-1,3),axis=0);color=np.clip(np.round(color/16)*16,0,255).astype(int)
                material='hair_rgb_'+'_'.join(map(str,color));mats[material]={'color':'#'+''.join(f'{c:02x}' for c in color)}
                oid=f'{part}_y{ya}_{yb}_x{a}_{b}'
                ops.append({'id':oid,'part':part,'action':'paint','material':material,'shape':{'kind':'extrusion','polygon':[[x,-z] for x,z in poly],'z_min':rounded(ylo),'z_max':rounded(yhi),'minimum_cells':0},'transform':{'basis':BASIS}})
                sensitivity={}
                for test_yaw in priors['side_yaw_uncertainty_degrees']:
                    ta=math.radians(test_yaw);u=math.cos(ta)*xc-math.sin(ta)*zc
                    center_ok=all(any((lo-sv['axis_u'])*ss-1e-9<=u<=(hi-sv['axis_u'])*ss+1e-9 for lo,hi in row['intervals_px']) for row in srows)
                    sensitivity[str(test_yaw)]={'fixed_center_inside_measured_side':center_ok}
                records.append({'operation':oid,'part':part,'source_view':view,'source_branch':branch['id'],'role':branch['role'],**chunk,'source_pixel_count':(yb-ya)*(b-a),'source_x_sign':sign,'world_y_range':[rounded(ylo),rounded(yhi)],'world_x_range':[rounded(x0),rounded(x1)],'center_xz_m':[rounded(xc),rounded(zc)],'isotropic_radius_m':rounded(r),'polygon_xz_m':poly,'side_support':srows,'allowed_center_z_intervals_m':[[rounded(a0),rounded(b0)] for a0,b0 in center],'full_circle_feasible_center_z_intervals_m':[[rounded(a0),rounded(b0)] for a0,b0 in full],'selected_center_z_interval_m':list(map(rounded,selection)),'depth_selection':'front nearest supported depth branch' if view=='front' else 'back farthest supported depth branch','full_circle_supported':bool(full),'cross_view_correspondence':'unknown','yaw_sensitivity':sensitivity})
                accounted+=(yb-ya)*(b-a)
            assert accounted+unresolved_pixels==expected_pixels
            branch_accounting.append({'part':part,'observed_below_threshold_pixels':expected_pixels,'represented_source_pixels':accounted,'unresolved_source_pixels':unresolved_pixels,'operations':len(records)-start_record,'tiny_or_isolated_runs_deleted':0})
    # Source-adjacent same-branch strips must not quietly be called joined.
    joins=[];adjacent=0;isolated=[];starts={};ends={}
    for i,r in enumerate(records):
        starts.setdefault((r['part'],r['source_y_range'][0]),[]).append(i);ends.setdefault((r['part'],r['source_y_range'][1]),[]).append(i)
    linked=set()
    for i,a in enumerate(records):
        for j in starts.get((a['part'],a['source_y_range'][1]),[]):
            b=records[j];lo=max(a['world_x_range'][0],b['world_x_range'][0]);hi=min(a['world_x_range'][1],b['world_x_range'][1])
            if hi<=lo:continue
            adjacent+=1;linked.update([i,j])
            if not polygon_overlap(a['polygon_xz_m'],b['polygon_xz_m']):joins.append([a['operation'],b['operation']])
    isolated=[r['operation'] for i,r in enumerate(records) if i not in linked]
    # Detect positive continuous section overlap; retain both sources regardless.
    bins={};pairs=set();cross=[];exact=[];ordering=[]
    for i,r in enumerate(records):
        if r['source_view']!='front':continue
        ya,yb=r['world_y_range']
        for row in range(math.floor(ya/fs+1e-7),math.ceil(yb/fs-1e-7)):bins.setdefault(row,[]).append(i)
    for j,b in enumerate(records):
        if b['source_view']!='back':continue
        ya,yb=b['world_y_range'];cand=set(i for row in range(math.floor(ya/fs+1e-7),math.ceil(yb/fs-1e-7)) for i in bins.get(row,[]))
        for i in cand:
            a=records[i]
            if min(a['world_y_range'][1],yb)-max(a['world_y_range'][0],ya)<=1e-10:continue
            if min(a['world_x_range'][1],b['world_x_range'][1])-max(a['world_x_range'][0],b['world_x_range'][0])<=0:continue
            if a['center_xz_m'][1]<=b['center_xz_m'][1]:ordering.append([a['operation'],b['operation']])
            if polygon_overlap(a['polygon_xz_m'],b['polygon_xz_m']):
                cross.append([a['operation'],b['operation']])
                if a['polygon_xz_m']==b['polygon_xz_m'] and a['world_y_range']==b['world_y_range']:exact.append([a['operation'],b['operation']])
    preflight={}
    for pitch in priors['preflight_pitches_m']:
        total=0
        for r in records:
            p=r['polygon_xz_m'];lo=[min(x for x,z in p),r['world_y_range'][0],min(z for x,z in p)];hi=[max(x for x,z in p),r['world_y_range'][1],max(z for x,z in p)]
            total+=math.prod(max(0,math.ceil(b/pitch-1e-9)-math.floor(a/pitch+1e-9)) for a,b in zip(lo,hi))
        preflight[str(pitch)]={'candidate_cells_exact_axis_aligned_operation_bounds':total,'occupied_cells':'not compiled','grid_origin':[0,0,0]}
    provenance={'approved_source_sha256':contract['source_sha256'],'source_pixel_array_sha256':hashlib.sha256(np.ascontiguousarray(rgb).tobytes()).hexdigest(),'branch_measurement_sha256':measured_gzip_sha,'branch_arrays_sha256':array_digest(branch_masks),'assumptions_content_sha256':digest(priors),'adapter_code_sha256':sha(__file__),'operations_content_sha256':digest(ops),'materials_content_sha256':digest(mats)}
    # Refer to exact source support rows once instead of repeating dozens of
    # intervals and the operation polygon inside every evidence record.
    side_table={};compact=[]
    for record in records:
        item=dict(record)
        item['side_support_row_ids']=[]
        for sr in item.pop('side_support'):
            side_table[str(sr['side_y_px'])]=sr['intervals_px'];item['side_support_row_ids'].append(sr['side_y_px'])
        item['allowed_center_interval_count']=len(item.pop('allowed_center_z_intervals_m'))
        item['full_circle_feasible_interval_count']=len(item.pop('full_circle_feasible_center_z_intervals_m'))
        item.pop('polygon_xz_m')
        compact.append(item)
    evidence={'provenance':provenance,'rows':compact,'side_support_rows':side_table,'side_support_reconstruction':'Each listed side row retains every measured interval. Center Z interval = [(cos(yaw)*xc-u_hi)/sin(yaw),(cos(yaw)*xc-u_lo)/sin(yaw)]; intersect row unions. For full-circle support inset each U interval by isotropic radius before mapping. Exact polygons are referenced by operation ID.','full_circle_unsupported_operation_count':sum(not r['full_circle_supported'] for r in records),'unresolved_runs':unresolved,'source_partition_accounting':branch_accounting,'head_ownership':ownership,'subbands_split_for_side_support':subband_splits,'duplicates':{'cross_view_positive_overlap_pair_count':len(cross),'exact_duplicate_section_pair_count':len(exact),'cross_view_positive_overlap_pairs':cross,'exact_duplicate_section_pairs':exact,'action':'reported only; neither source deleted or merged'},'join_conflicts':{'source_adjacent_pair_count':adjacent,'disjoint_cross_section_pair_count':len(joins),'disjoint_pairs':joins,'isolated_operation_count':len(isolated),'isolated_operations':isolated,'front_near_back_far_order_conflict_count':len(ordering),'depth_order_conflict_pairs':ordering,'cap_attachment':'not evaluated; head master owned separately'},'preflight':preflight,'limits':priors['limits'],'compiled':False,'rig_or_socket_complete':False}
    return {'schema':'riverstone.measured_hair_adapter.v1','materials':mats,'parts':parts,'operations':ops,'evidence':evidence}

def disk_adapter(result):
    out={k:v for k,v in result.items() if k!='evidence'}
    out['evidence']={k:result['evidence'][k] for k in ('provenance','preflight','limits','compiled','rig_or_socket_complete')}
    out['evidence']['audit_file']='../evidence/hair_audit.json.gz'
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--priors',type=Path,default=FULL/'data/hair_depth_priors.json');ap.add_argument('--verify',action='store_true');args=ap.parse_args();t=time.perf_counter()
    c=load(ROOT/'data/measurement_contract.json');m=load(ROOT/'full_measurement/violet_branches/branch_measurements.json.gz');masks=np.load(ROOT/'full_measurement/violet_branches/branch_masks.npz',allow_pickle=False)
    r=build_hair(c,m,masks,REPO/c['source'],load(args.priors));out=FULL/'generated/hair_adapter.json.gz';audit=FULL/'evidence/hair_audit.json.gz'
    if args.verify:
        assert canonical(disk_adapter(r))==canonical(load(out));assert canonical(r['evidence'])==canonical(load(audit));report={'independent_process_replay_identical':True,'adapter_file_sha256':sha(out),'operations_content_sha256':r['evidence']['provenance']['operations_content_sha256']};(FULL/'evidence/hair_reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
    else:
        assert not out.exists(),'Refusing to overwrite a generated adapter'
        gzsave(out,disk_adapter(r));gzsave(audit,r['evidence'])
        report={'operations':len(r['operations']),'parts':len(r['parts']),'materials':len(r['materials']),'adapter_file_sha256':sha(out),'provenance':r['evidence']['provenance'],'preflight':r['evidence']['preflight'],'unresolved_runs':len(r['evidence']['unresolved_runs']),'join_conflicts':{k:v for k,v in r['evidence']['join_conflicts'].items() if not isinstance(v,list)},'duplicates':{k:v for k,v in r['evidence']['duplicates'].items() if not isinstance(v,list)}}
        (FULL/'evidence/hair_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    own=[Path(__file__),args.priors,*list((FULL/'evidence').glob('hair_*')),*list((FULL/'generated').glob('hair_*'))]
    size=sum(p.stat().st_size for p in own if p.is_file());assert size<=int(1.2*1048576),f'Hair adapter budget exceeded: {size}'
    print(json.dumps({'seconds':round(time.perf_counter()-t,3),'owned_output_and_code_bytes':size,**report}))
