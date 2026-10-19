"""Read-only source/cache opening inventory. No compilation or source edits.

Only output files in this directory are written. Material semantics come from
source-bound mapping; no RGB color inference. Render records have no op ownership.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import gzip,hashlib,itertools,json,math,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
sys.path.insert(0,str(ROOT))
from voxel_character.common import core
UPGRADE=HERE.parents[1]
INDEX=ROOT/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json'
CATALOG=UPGRADE/'facility_roofs/catalog.json'
MAP=UPGRADE/'surface_mapping/material_surface_map.v1.json'

def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    (HERE/name).write_text(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n')
def pack(name,rows):
    with (HERE/name).open('wb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as g:
            for row in rows:g.write((json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode())
def bounds(op):return core.shape_bounds(core.prepare_shape(op['shape'],.05))
def extent(lo,hi):return [round(b-a,8) for a,b in zip(lo,hi)]
def tidy(v):
    if isinstance(v,float):return round(v,8)
    if isinstance(v,list):return [tidy(x) for x in v]
    if isinstance(v,dict):return {k:tidy(x) for k,x in v.items()}
    return v

def transforms(master):
    inst={i['id']:i for i in master['instances']};known={}
    def world(key):
        if key not in known:
            i=inst[key];t=core.transform(i.get('transform'))
            known[key]=core.compose(world(i['parent']),t) if i.get('parent') else t
        return known[key]
    for key in inst:world(key)
    return known

def world_bounds(op,t):
    lo,hi=bounds(op);pts=[core.apply(t,p) for p in itertools.product(*zip(lo,hi))]
    return [min(p[j] for p in pts) for j in range(3)],[max(p[j] for p in pts) for j in range(3)]

def signed_axis(t,axis=2,sign=1):
    v=[row[axis]*sign for row in t['basis']];major=max(range(3),key=lambda j:abs(v[j]))
    return (major,1 if v[major]>0 else -1) if abs(abs(v[major])-1)<1e-6 and sum(abs(v[j]) for j in range(3) if j!=major)<1e-6 else None

def render_index(render):
    result=defaultdict(list)
    for g in render['groups']:
        for q in g['quads']:
            lo=[min(p[j] for p in q) for j in range(3)];hi=[max(p[j] for p in q) for j in range(3)]
            axes=[j for j in range(3) if hi[j]-lo[j]<1e-8]
            if len(axes)!=1:continue
            axis=axes[0];u=[q[1][j]-q[0][j] for j in range(3)];v=[q[2][j]-q[1][j] for j in range(3)]
            cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            result[(g['material'],axis,1 if cross[axis]>0 else -1)].append((lo,hi))
    return result

def cache_observation(op,t,normal_sign,index,render):
    lo,hi=world_bounds(op,t);axis=signed_axis(t,2,normal_sign);pitch=render['pitch'];origin=render.get('grid_origin',[0,0,0])
    # Only a zero AABB-axis lattice count is used as a sufficient no-sample proof.
    # Nonzero counts are not treated as proof of occupied/exposed source cells.
    eps=pitch*core.EPS+1e-9
    lattice=[max(0,math.floor((hi[j]+eps-origin[j])/pitch-.5)-math.ceil((lo[j]-eps-origin[j])/pitch-.5)+1) for j in range(3)]
    if axis is None:return {'status':'arbitrary_rigid_face_cache_correspondence_pending','aabb_lattice_counts':lattice}
    axis,sign=axis;face=hi[axis] if sign>0 else lo[axis];count=0;area=0.0
    tangents=[j for j in range(3) if j!=axis]
    for qlo,qhi in index.get((op['material'],axis,sign),[]):
        if abs(qlo[axis]-face)>pitch/2+1e-6:continue
        overlap=[min(hi[j],qhi[j])-max(lo[j],qlo[j]) for j in tangents]
        if min(overlap)>1e-8:count+=1;area+=math.prod(overlap)
    if count and 0 in lattice:status='source_unsampled_nearby_same_material_geometry_ambiguous'
    elif count:status='same_material_exterior_patch_detected_not_exact_op_ownership'
    elif 0 in lattice:status='source_present_cache_absent_zero_axis_sample'
    else:status='source_present_cache_no_patch_occlusion_or_sampling_unresolved'
    return {'status':status,'candidate_quad_count':count,'candidate_overlap_aabb_area_m2':round(area,6),'aabb_lattice_counts':lattice,'axis':axis,'sign':sign,'source_face_m':round(face,8)}

def role(op,glass_slots):
    name=op['id'].lower();part=op.get('part','')
    if op['action']=='cut':
        if re.search(r'window|shop_opening|work_bay',name):return 'window_aperture_cut'
        if re.search(r'door|entry|entrance|loading_bay|portal|passage|gate_opening',name):return 'entrance_cut'
        return None
    if op.get('material') in glass_slots:return 'glass'
    if 'shutter' in name:return 'shutter'
    if 'mullion' in name:return 'mullion'
    if 'transom' in name:return 'transom'
    if part=='door' or ('leaf' in name and 'door_frame' not in name):return 'door_leaf'
    if 'door_frame' in name:return 'door_frame'
    if 'window' in name or 'surround' in name or 'shop_opening' in name or 'work_bay' in name:
        if any(x in name for x in ['surround','_left','_right','_lintel','_sill','frame']):return 'window_frame_sill'
    return None

def associations(component,glass):
    name=glass['id'];lookup={o['id']:o for o in component['operations']}
    if name.endswith('_glass'):
        prefix=name[:-6];kind='rectangular_cut_bay';ap=lookup.get(prefix+'_aperture')
        related=[lookup[x] for x in [prefix+s for s in ('_left','_right','_sill','_lintel','_mullion','_transom','_shutter')] if x in lookup]
        panel=next((o for o in component['operations'] if o['id'].split('__')[-1]=='wall_panel'),None)
        surface=bounds(panel)[1][2] if panel else None;sign=1
    elif name.endswith('_pane'):
        prefix=name[:-5];kind='landmark_polygon_painted_panel';ap=lookup.get(prefix+'_aperture')
        related=[lookup[x] for x in [prefix+s for s in ('_surround','_mullion','_transom','_shutter','_sill')] if x in lookup]
        surround=lookup.get(prefix+'_surround');surface=bounds(surround)[1][2] if surround else None;sign=1
    elif 'window_pane_' in name:
        kind='recovered_flat_painted_panel';frame_name=name.replace('window_pane_','window_surround_');related=[lookup[frame_name]] if frame_name in lookup else []
        ap=None;match=re.search(r'window_pane_(-?1)_',name);sign=int(match.group(1)) if match else 1
        surround=lookup.get(frame_name);surface=bounds(surround)[1 if sign>0 else 0][2] if surround else None
    else:kind='unbound_glazing';ap=None;related=[];surface=None;sign=1
    return kind,ap,related,surface,sign

def family(key,master):
    if 'castle' in key:return 'castle'
    if 'cathedral' in key or 'clergy' in key:return 'cathedral_and_clergy'
    if 'monastery' in key or 'abbey' in key:return 'monastery_and_abbey'
    if 'port' in key:return 'port_loading_shed'
    if key.startswith('c3_property_') or master.get('metadata',{}).get('assembly_class') in ('older_stone_manor','merchant_palazzo','timber_courtyard_house'):return 'manor_and_property_modules'
    return 'other_facilities'

def feature_record(op,r,t,render,idx,sign=1):
    lo,hi=bounds(op)
    return {'id':op['id'],'role':r,'material':op.get('material'),'kind':op['shape']['kind'],'bounds_m':tidy([lo,hi]),'dimensions_m':extent(lo,hi),'operation_sha256':core.digest(op),
            'subpitch_axes':[j for j,n in enumerate(extent(lo,hi)) if n<render['pitch']-1e-8],
            'cache':cache_observation(op,t,sign,idx,render) if op['action']=='paint' else None}

def audit():
    cat=load(CATALOG);index=load(INDEX);mapping=load(MAP);keys={r['asset_key'] for r in cat['assets']};usages=defaultdict(dict)
    for tile in index['tiles'].values():
        path=ROOT/tile['instances_path'];assert sha(path)==tile['instances_sha256']
        for row in load(path)['common_instances']:
            if row['asset_key'] in keys:usages[row['asset_key']][row['id']]=row
    assets=[];windows=[];other=[];families=defaultdict(Counter);slot_totals=Counter()
    for entry in cat['assets']:
        key=entry['asset_key'];asset=index['common_assets'][key];mp=ROOT/asset['master_path'];rp=ROOT/asset['render_path'];assert sha(mp)==asset['master_sha256'] and sha(rp)==asset['render_sha256']
        master=load(mp);render=load(rp);sem=mapping['assets'][key];assert sem['master_sha256']==asset['master_sha256']
        glass_slots={k for k,v in sem['slots'].items() if v['semantic_class']=='glass'}
        idx=render_index(render);trans=transforms(master);instances=defaultdict(list)
        for inst in master['instances']:instances[inst['component']].append(inst)
        roles=Counter();counts=Counter();modes=Counter();states=Counter();normal_ranges=[];repeat=Counter();role_materials=defaultdict(set);row_ids=[]
        for comp in master['components']:
            for op in comp['operations']:
                r=role(op,glass_slots)
                if r:roles[r]+=len(instances[comp['id']]);role_materials[r].add(op.get('material','cut'))
                if r!='glass':
                    if r in ('door_leaf','door_frame','entrance_cut'):
                        for inst in instances[comp['id']]:
                            t=core.compose(trans[inst['id']],core.transform(op.get('transform')))
                            entry_feature=feature_record(op,r,t,render,idx)
                            if entry_feature['cache']:
                                entry_feature['cache']['normal_interpretation']='operation_local_plus_z_unverified_for_entry_features'
                            other.append({'asset_key':key,'component':comp['id'],'instance':inst['id'],'feature':entry_feature,'local_to_master':tidy(t)})
                    continue
                kind,ap,related,surface,sign=associations(comp,op);glo,ghi=bounds(op)
                front=ghi[2] if sign>0 else glo[2]
                recess=sign*(surface-front) if surface is not None else None
                if recess is not None:normal_ranges.append(recess)
                # Source-defined ordinary aperture is a shape contract candidate;
                # it does not establish render-patch ownership or city clearance.
                if ap and ap['action']=='cut' and kind=='rectangular_cut_bay':
                    alo,ahi=bounds(ap);cavity=ahi[2]>=surface and alo[2]<=surface-.22
                    mode='existing_aperture_local_swap_candidate' if cavity else 'insufficient_aperture_depth_needs_local_wall_cavity'
                elif kind in ('landmark_polygon_painted_panel','recovered_flat_painted_panel'):
                    cavity=False;mode='solid_wall_and_surround_cavity_patch_required'
                else:cavity=False;mode='opening_geometry_binding_pending'
                for inst in instances[comp['id']]:
                    t=core.compose(trans[inst['id']],core.transform(op.get('transform')))
                    if signed_axis(t) is None:mode='arbitrary_rigid_partition_required'
                    observed=cache_observation(op,t,sign,idx,render);states[observed['status']]+=1;modes[mode]+=1
                    feats=[]
                    for p in related:
                        pt=core.compose(trans[inst['id']],core.transform(p.get('transform')))
                        rr=role(p,glass_slots) or 'window_frame_sill'
                        feature=feature_record(p,rr,pt,render,idx,sign)
                        pl,ph=bounds(p)
                        feature['front_recess_from_surface_m']=tidy(sign*(surface-(ph[2] if sign>0 else pl[2]))) if surface is not None and p.get('transform')==op.get('transform') else None
                        feats.append(feature)
                    present={r['role'] for r in feats};missing=sorted({'window_frame_sill','mullion','transom','shutter'}-present)
                    # Exact repeated local profile, ignoring translation/operation id.
                    signature=core.digest(tidy({'glass_kind':op['shape']['kind'],'glass_dimensions':extent(glo,ghi),'polygon':[[x-glo[0],y-glo[1]] for x,y in op['shape'].get('polygon',[])],'related_shapes':[(p['shape']['kind'],[[v-glo[j] for j,v in enumerate(b)] for b in bounds(p)],role(p,glass_slots)) for p in related],'normal_sign':sign}))[:16]
                    repeat[signature]+=1
                    record={'asset_key':key,'component':comp['id'],'instance':inst['id'],'glass':feature_record(op,'glass',t,render,idx,sign),'local_to_master':tidy(t),
                            'source_profile':kind,'source_profile_polygon':op['shape'].get('polygon'),'source_polygon_vertices':len(op['shape'].get('polygon',[])),'source_surface_coordinate_m':surface,'local_outward_sign':sign,'source_glass_recess_m':tidy(recess),
                            'associated_aperture':{'id':ap['id'],'shape':ap['shape'],'operation_sha256':core.digest(ap)} if ap else None,
                            'associated_features':feats,'source_frame_is_filled_panel':kind in ('landmark_polygon_painted_panel','recovered_flat_painted_panel'),'source_absent_roles':missing,'upgrade_route':mode,'source_cavity_depth_sufficient_for_015m_glass':cavity,
                            'coarse_patch_swap_required':True,'profile_signature':signature,'source_defined_component_instance_count':len(instances[comp['id']]),
                            'city_asset_placement_count':len(usages[key]),'new_shutters_design_gate':kind!='rectangular_cut_bay'}
                    windows.append(tidy(record));row_ids.append(len(windows)-1);counts['glass_faces']+=1
        for cut in master.get('assembly_cuts',[]):
            if re.search(r'door|entry|entrance|loading_bay|portal|passage|gate_opening',cut['id'],re.I):
                roles['assembly_entrance_cut']+=1;other.append({'asset_key':key,'scope':'assembly','role':'assembly_entrance_cut','operation':cut,'operation_sha256':core.digest(cut)})
        ext=master.get('extensions',{});meta=master.get('metadata',{});f=family(key,master)
        family_row=families[f];family_row['assets']+=1;family_row['city_placements']+=len(usages[key]);family_row.update(roles)
        family_row.update({'route:'+k:v for k,v in modes.items()});family_row.update({'cache:'+k:v for k,v in states.items()})
        item={'asset_key':key,'family':f,'source_master_path':asset['master_path'],'source_sha256':asset['master_sha256'],'render_path':asset['render_path'],'render_sha256':asset['render_sha256'],
              'cache_pitch_m':render['pitch'],'source_master_metadata_kind':meta.get('assembly_class') or ext.get('landmark_kind'),'city_placements':len(usages[key]),'placement_ids':sorted(usages[key]),
              'source_roles':dict(roles),'role_material_slots':{k:sorted(v) for k,v in role_materials.items()},'window_routes':dict(modes),'window_cache_states':dict(states),
              'glass_recess_range_m':tidy([min(normal_ranges),max(normal_ranges)]) if normal_ranges else None,
              'source_components':len(master['components']),'source_instances':len(master['instances']),'shared_component_instance_counts':{k:len(v) for k,v in instances.items() if len(v)>1},
              'profile_repetition':dict(repeat),'glass_face_row_span':[row_ids[0],row_ids[-1]+1] if row_ids else None,
              'entrance_metadata':ext.get('entrances',[]) or ([meta['entrance']] if meta.get('entrance') else []),
              'entrance_policy':'Keep authored passage/door state; absent door leaves do not authorize closing an open portal.',
              'no_glass_policy':'No authored glazing is evidence of source absence, not proof this open shelter/tower needs new windows.' if not roles['glass'] else None}
        assets.append(item);slot_totals.update(roles)
        print(key,'glass',roles['glass'],'routes',dict(modes),flush=True)
    pack('window_faces.jsonl.gz',windows);pack('door_and_entry_features.jsonl.gz',other)
    write('asset_audit.json',{'schema':'riverstone.facility_openings.audit.v1','scope_asset_count':len(assets),'catalog_path':str(CATALOG.relative_to(ROOT)),'catalog_sha256':sha(CATALOG),
          'index_path':str(INDEX.relative_to(ROOT)),'index_sha256':sha(INDEX),'mapping_path':str(MAP.relative_to(ROOT)),'mapping_sha256':sha(MAP),'assets':assets})
    summary={'schema':'riverstone.facility_openings.summary.v1','asset_count':len(assets),'city_placements':sum(x['city_placements'] for x in assets),'glass_face_count':len(windows),
             'door_entry_feature_records':len(other),'cache_pitch_counts':dict(Counter(str(r['cache_pitch_m']) for r in assets)),'source_absent_window_role_counts':dict(Counter(role for r in windows for role in r['source_absent_roles'])),'source_profile_counts':dict(Counter(r['source_profile'] for r in windows)),'landmark_polygon_vertex_counts':dict(Counter(r['source_polygon_vertices'] for r in windows if r['source_profile']=='landmark_polygon_painted_panel')),'source_feature_zero_sample_counts':dict(Counter(f['role'] for r in windows for f in r['associated_features'] if 0 in f['cache']['aabb_lattice_counts'])),'role_counts':dict(slot_totals),'families':{k:dict(v) for k,v in families.items()},
             'source_unchanged':all(sha(ROOT/x['source_master_path'])==x['source_sha256'] and sha(ROOT/x['render_path'])==x['render_sha256'] for x in assets),
             'compile_count':0,'manufactured_modules':0,'runtime_edits':0,
             'methods':{'source_roles':'Exact operation ids/parts/material semantics and associated source stems; not RGB.',
                        'cache':'Same-material axis/normal-aligned render quad AABB overlap within half a cache pitch of source pane face; spatial candidate evidence only.',
                        'absence':'Zero lattice count on any conservatively epsilon-expanded inclusive AABB axis proves no possible source sample. Nonzero count cannot prove occupied cells, exposure or ownership.',
                        'dimension':'Exact continuous primitive AABB; extrusion width/height are envelope dimensions, not rectangular aperture claims.',
                        'families':'Explicit asset naming and assembly class, not blindly reused extensions.landmark_kind.'},
             'limitations':['No compilation, occupied-cell reconstruction or visual review.','Render groups lack component/operation provenance; matching quads do not prove exact frame ownership.','Existing source aperture enables a candidate route, not a ready runtime suppression contract.','A 0.5m cache can hide subpitch detail; no-source-feature cases must be authored rather than recolored.']}
    write('summary.json',summary)
    files=[p for p in HERE.rglob('*') if p.is_file()]
    size=sum(p.stat().st_size for p in files);assert size<1024*1024,(size,'1MiB audit budget exceeded')
    print(json.dumps({'assets':len(assets),'glass_faces':len(windows),'door_entries':len(other),'output_directory_bytes':size,'compile_count':0}))
    return summary

if __name__=='__main__':audit()
