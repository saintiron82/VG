"""One data-driven window source revision; no compiler or runtime mutations.

Applies the same window operation geometry to near and canonical masters. All
original non-window operations, cuts, structure, roof and assembly remain exact.
Render composition/far silhouette/voxel proof are explicitly pending.
"""
import argparse,copy,gzip,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import adapter as a

def load(path):
    path=Path(path)
    with (gzip.open(path,'rt',encoding='utf-8') if path.suffix=='.gz' else path.open(encoding='utf-8')) as f:return json.load(f)

def digest(value):return a.core.digest(value)
def need(value,reason):
    if not value:raise ValueError(reason)
def is_window(op,r):return op.get('part')==r['selectors']['window_part'] and op['action']=='paint'
def rect(op):
    need(op['shape']['kind']=='box' and not op.get('transform'),'Unrecognized window shape/transform must remain pending')
    return op['shape']['min'],op['shape']['max']
def set_box(op,lo,hi):
    need(all(hi[k]>lo[k] for k in range(3)),'Nonpositive revised window box')
    op['shape']={**op['shape'],'min':[round(v,9) for v in lo],'max':[round(v,9) for v in hi]}

def classify_axis(op,base):
    suffix=op['id'][len(base):]
    if suffix in ('_left','_right') or suffix=='__near_mullion':return [0,1,0],'vertical_frame_or_mullion'
    if suffix in ('_sill','_lintel') or suffix in ('__near_transom','__near_sill_top','__near_sill_bottom'):return [1,0,0],'horizontal_frame_or_sill'
    if '__near_shutter_' in suffix and '_strap_' not in suffix:return [0,1,0],'shutter_vertical_plank'
    return None,None

def revise_component(component,r,state):
    c=copy.deepcopy(component);ops=c['operations'];lookup={o['id']:o for o in ops};sel=r['selectors'];windows=[];axes=[];owned=set()
    apertures=[o for o in ops if o['action']=='cut' and re.fullmatch(sel['aperture_id_regex'],o['id'])]
    if not apertures:return c,windows,axes
    need(sel['panel_id'] in lookup,'Missing semantic wall panel')
    wall=lookup[sel['panel_id']];walllo,wallhi=rect(wall);surface=wallhi[2]
    for ap in apertures:
        base=ap['id'][:-len('_aperture')];lo,hi=rect(ap);x0,y0=lo[:2];x1,y1=hi[:2];xm=(x0+x1)/2;ym=(y0+y1)/2
        required=[base+sel['glass_suffix']]+[base+s for s in sel['frame_suffixes']]
        need(all(k in lookup for k in required),'Incomplete frame/glass semantic association '+base)
        ids=[o['id'] for o in ops if is_window(o,r) and (o['id'] in required or o['id'].startswith(base+'__near_'))]
        need(not(owned&set(ids)),'Overlapping window ownership');owned.update(ids)
        original={k:copy.deepcopy(lookup[k]) for k in ids};outside=r['frame_width_m']-r['frame_inside_aperture_m'];inside=r['frame_inside_aperture_m'];z0=surface+r['frame_back_from_wall_m'];z1=surface+r['frame_front_from_wall_m']
        clear=[x1-x0-2*inside,y1-y0-2*inside];need(min(clear)>=r['minimum_clear_span_m'],'Window too small for rule contract')
        frames={'_left':([x0-outside,y0-outside,z0],[x0+inside,y1+outside,z1]),'_right':([x1-inside,y0-outside,z0],[x1+outside,y1+outside,z1]),'_sill':([x0-outside,y0-outside,z0],[x1+outside,y0+inside,z1]),'_lintel':([x0-outside,y1-inside,z0],[x1+outside,y1+outside,z1])}
        for suffix,bounds in frames.items():set_box(lookup[base+suffix],*bounds)
        set_box(lookup[base+'_glass'],[x0,y0,surface-r['glass_recess_m']-r['glass_thickness_m']],[x1,y1,surface-r['glass_recess_m']])
        half=r['mullion_width_m']/2
        for suffix,bounds in {'__near_mullion':([xm-half,y0+inside,surface+r['mullion_back_from_wall_m']],[xm+half,y1-inside,surface+r['mullion_front_from_wall_m']]),'__near_transom':([x0+inside,ym-half,surface+r['mullion_back_from_wall_m']],[x1-inside,ym+half,surface+r['mullion_front_from_wall_m']])}.items():
            need(base+suffix in lookup,'Missing detail crosspiece '+base+suffix);set_box(lookup[base+suffix],*bounds)
        for suffix,ya,yb,front in [('__near_sill_bottom',r['sill_lower_y_m'],r['sill_step_y_m'],.12),('__near_sill_top',r['sill_step_y_m'],r['sill_top_y_m'],r['sill_front_m'])]:
            need(base+suffix in lookup,'Missing stepped sill');set_box(lookup[base+suffix],[max(walllo[0],x0-r['sill_side_extension_m']),y0+ya,surface-.10],[min(wallhi[0],x1+r['sill_side_extension_m']),y0+yb,surface+front])
        shutters=[]
        for side in (-1,1):
            prefix=base+'__near_shutter_'+str(side);group=[lookup[k] for k in ids if k==prefix or k.startswith(prefix+'_')]
            if not group:
                shutters.append({'side':side,'status':'PENDING_NO_EXISTING_SHUTTER_CLEARANCE'});continue
            oldlo,oldhi=rect(original[prefix]);width=oldhi[0]-oldlo[0]
            if state=='glazed_closed_shutters_open':
                targetlo=x0-outside-r['open_shutter_clearance_m']-width if side<0 else x1+outside+r['open_shutter_clearance_m'];scale=1.
            else:
                targetlo=x0 if side<0 else xm;scale=((x1-x0)/2)/width
            for op in group:
                olda,oldb=rect(original[op['id']]);newa=list(olda);newb=list(oldb);newa[0]=targetlo+(olda[0]-oldlo[0])*scale;newb[0]=targetlo+(oldb[0]-oldlo[0])*scale
                set_box(op,newa,newb)
            shutters.append({'side':side,'state':state,'new_x_range':rect(lookup[prefix])[0:2]})
        oldleft,oldright=rect(original[base+'_left']),rect(original[base+'_right']);oldbottom,oldtop=rect(original[base+'_sill']),rect(original[base+'_lintel'])
        oldclear=[oldright[0][0]-oldleft[1][0],oldtop[0][1]-oldbottom[1][1]];oldouter=[oldright[1][0]-oldleft[0][0],oldtop[1][1]-oldbottom[0][1]];newouter=[x1-x0+2*outside,y1-y0+2*outside]
        changed=[k for k in ids if original[k]!=lookup[k]]
        roi_lo=[min(rect(original[k])[0][j] for k in ids) for j in range(3)];roi_hi=[max(rect(original[k])[1][j] for k in ids) for j in range(3)]
        for k in ids:
            for j in range(3):roi_lo[j]=min(roi_lo[j],rect(lookup[k])[0][j]);roi_hi[j]=max(roi_hi[j],rect(lookup[k])[1][j])
            axis,role=classify_axis(lookup[k],base)
            if axis:axes.append({'component_id':c['id'],'operation_id':k,'part_id':lookup[k]['part'],'material':lookup[k]['material'],'role':role,'grain_axis_component_local':axis})
        windows.append({'component_id':c['id'],'aperture_operation_id':ap['id'],'window_base':base,'state':state,'aperture_m':[x1-x0,y1-y0],'old_frame_width_m':oldleft[1][0]-oldleft[0][0],'old_clear_span_m':oldclear,'old_outer_span_m':oldouter,'new_frame_width_m':r['frame_width_m'],'new_clear_span_m':clear,'new_outer_span_m':newouter,'new_mullion_width_m':r['mullion_width_m'],'old_visible_glass_ratio_with_near_cross':max(0,oldclear[0]-.075)*max(0,oldclear[1]-.075)/(oldouter[0]*oldouter[1]),'new_visible_glass_ratio_with_near_cross':max(0,clear[0]-r['mullion_width_m'])*max(0,clear[1]-r['mullion_width_m'])/(newouter[0]*newouter[1]) if state=='glazed_closed_shutters_open' else 0,'area_method':'Analytic frontal projection of rectangular frame/cross only; structural occlusion and voxel phase require ROI verification','changed_operations':changed,'local_roi':{'min':roi_lo,'max':roi_hi},'shutters':shutters})
    # Ambiguous windows must not silently retain their old proportions.
    need(all(not is_window(o,r) or o['id'] in owned for o in ops),'Unmatched window operation in component '+c['id'])
    return c,windows,axes

def revise(source,near,r,state,provenance):
    need(state in r['explicit_states'],'Unsupported explicit shutter/casement state')
    candidate=copy.deepcopy(near);canonical=copy.deepcopy(source);windows=[];axes=[]
    need([c['id'] for c in source['components']]==[c['id'] for c in near['components']],'Component associations changed')
    for index,c in enumerate(near['components']):
        changed,rows,grain=revise_component(c,r,state);candidate['components'][index]=changed;windows.extend(rows);axes.extend(grain)
        if not rows:continue
        newwin={o['id']:o for o in changed['operations'] if is_window(o,r)};original=source['components'][index];seen=set();canonops=[]
        for op in original['operations']:
            if is_window(op,r):
                if op['id'] in newwin:canonops.append(copy.deepcopy(newwin[op['id']]));seen.add(op['id'])
            else:canonops.append(copy.deepcopy(op))
        canonops.extend(copy.deepcopy(o) for o in changed['operations'] if is_window(o,r) and o['id'] not in seen)
        canonical['components'][index]['operations']=canonops
    need(windows,'No supported windows found')
    for old,new in [(source,canonical),(near,candidate)]:
        for field in ('instances','materials','assembly_cuts','constraints'):need(old.get(field)==new.get(field),'Assembly/material/constraint mutated '+field)
        for oc,nc in zip(old['components'],new['components']):
            need([o for o in oc['operations'] if not is_window(o,r)]==[o for o in nc['operations'] if not is_window(o,r)],'Nonwindow operation changed '+oc['id'])
        new['revision']=old['revision']+1
        new.setdefault('provenance',{})['window_proportion_revision']={**provenance,'rules_sha256':digest(r),'engine_sha256':a.sha(__file__),'state':state,'source_revision_id':r['revision_id'],'compile_status':'NOT_COMPILED','runtime_activation':False,'near_far_window_operation_identity':True}
        a.core.validate_master(new,.05)
    for nc,cc in zip(candidate['components'],canonical['components']):need({o['id']:o for o in nc['operations'] if is_window(o,r)}=={o['id']:o for o in cc['operations'] if is_window(o,r)},'Near/far source window design differs')
    return canonical,candidate,windows,axes

def save_gz(path,value):
    need(not path.exists(),'Existing candidate preserved')
    data=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(gzip.compress(data,mtime=0));return {'path':str(path.relative_to(a.ROOT)),'sha256':a.sha(path),'bytes':path.stat().st_size}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--asset',required=True);p.add_argument('--rules',type=Path,default=HERE/'window_rules.v1.json');p.add_argument('--state',default='glazed_closed_shutters_open');p.add_argument('--output',type=Path,required=True);x=p.parse_args();r=load(x.rules);record=next(row for row in load(x.catalog)['assets'] if row['asset_key']==x.asset)
    for field,d in [('source_master_path','source_sha256'),('emitted_master_path','emitted_master_sha256')]:need(a.sha(a.ROOT/record[field])==record[d],'Input SHA mismatch')
    source=load(a.ROOT/record['source_master_path']);near=load(a.ROOT/record['emitted_master_path']);provenance={'asset_key':x.asset,'original_source_path':record['source_master_path'],'original_source_sha256':record['source_sha256'],'previous_near_path':record['emitted_master_path'],'previous_near_sha256':record['emitted_master_sha256'],'rules_file_sha256':a.sha(x.rules)}
    canonical,candidate,windows,axes=revise(source,near,r,x.state,provenance);out=x.output.resolve();out.mkdir(parents=True,exist_ok=True)
    files={'canonical':save_gz(out/(x.asset+'.canonical.master.json.gz'),canonical),'near':save_gz(out/(x.asset+'.near.master.json.gz'),candidate)}
    report={'schema':'riverstone.window_proportion_revision.candidate.v1','asset_key':x.asset,'status':'SOURCE_STRUCTURAL_PASS_RENDER_PENDING','state':x.state,'files':files,'inputs':provenance,'window_count':len(windows),'windows':windows,'all_nonwindow_operations_and_original_cuts_unchanged':True,'component_instances_materials_constraints_unchanged':True,'near_far_window_source_operations_identical':True,'full_compile_run':False,'roi_compile_run':False,'runtime_activation':False,'collision_change':False,'wood_axes_path':str((out/(x.asset+'.grain_axes.json')).relative_to(a.ROOT)),'pending':['Source structural columns can occlude clear view; ROI rays still required','Far mesh must preserve revised silhouette rather than rely on .5m voxel disappearance','Finite old/new window ROI replacement and seam proof required','Hinged open casement is an explicit unsupported state, not a closed-pane fallback']}
    a.write(out/(x.asset+'.candidate.json'),report);a.write(out/(x.asset+'.grain_axes.json'),{'schema':'riverstone.window_grain_axes.v1','source_master_sha256':files['canonical']['sha256'],'authored_master_sha256':files['near']['sha256'],'operations':axes})
    print(json.dumps({'asset':x.asset,'status':report['status'],'windows':len(windows),'files':files}))
