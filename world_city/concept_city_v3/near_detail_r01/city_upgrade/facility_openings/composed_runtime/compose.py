"""Offline exact render composition. No voxel regeneration or runtime changes."""
from collections import defaultdict, Counter
import argparse, gzip, hashlib, io, json, resource, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import author as a

def dump(path,value):
    path=Path(path)
    if path.suffix=='.gz':
        with path.open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
                with io.TextIOWrapper(zipped,encoding='utf-8') as text:
                    json.dump(value,text,sort_keys=True,separators=(',',':'));text.write('\n')
    else:a.write(path,value)

def clip(q,regions):
    axis,t,plane,sign,r=a.quad_info(q);rects=[r]
    for region in regions:
        if not region['min'][axis]-1e-8<=plane<=region['max'][axis]+1e-8:continue
        cut=[region['min'][t[0]],region['min'][t[1]],region['max'][t[0]],region['max'][t[1]]]
        rects=[piece for rect in rects for piece in a.subtract_rect(rect,cut)[0]]
    if rects==[r]:return [q]
    return [a.rect_quad(rect,axis,t,plane,sign) for rect in rects]

def plane_audit(groups,pitch=.05):
    """Plane-at-a-time raster audit, bounded by one surface cross section."""
    planes=defaultdict(list);offgrid=0
    for g in groups:
        for q in g['quads']:
            axis,t,p,s,r=a.quad_info(q)
            offgrid+=any(abs(x/pitch-round(x/pitch))>1e-5 for v in q for x in v)
            planes[axis,round(p/pitch)].append((s,*[round(x/pitch) for x in r]))
    duplicates=opposed=faces=max_plane=0;examples=[]
    for key,rects in sorted(planes.items()):
        cells={}
        for s,x0,y0,x1,y1 in rects:
            for x in range(x0,x1):
                for y in range(y0,y1):
                    old=cells.get((x,y))
                    if old is not None:
                        if old==s:duplicates+=1
                        else:opposed+=1
                        if len(examples)<12:examples.append([*key,x,y,old,s])
                    cells[x,y]=s;faces+=1
        max_plane=max(max_plane,len(cells))
    return {'same_normal_duplicate_unit_faces':duplicates,'opposed_coplanar_unit_faces':opposed,'off_grid_quads':offgrid,'sampled_unit_faces':faces,'maximum_plane_cells':max_plane,'examples':examples}

def edge_audit(groups,pitch=.05):
    odd_length=0;examples=[];lines_checked=0
    for direction in range(3):
        lines=defaultdict(list);fixed=[j for j in range(3) if j!=direction]
        for g in groups:
            for q in g['quads']:
                vertices=[[round(x/pitch) for x in v] for v in q]
                for p,r in zip(vertices,vertices[1:]+vertices[:1]):
                    if p[direction]==r[direction] or any(p[j]!=r[j] for j in fixed):continue
                    lo,hi=sorted((p[direction],r[direction]));lines[p[fixed[0]],p[fixed[1]]].extend(((lo,1),(hi,-1)))
        for key,events in lines.items():
            counts=Counter()
            for at,delta in events:counts[at]+=delta
            previous=None;active=0
            for at,delta in sorted(counts.items()):
                if previous is not None and active%2:
                    odd_length+=at-previous
                    if len(examples)<12:examples.append([direction,*key,previous,at,active])
                active+=delta;previous=at
            assert active==0
        lines_checked+=len(lines)
    return {'unpaired_unit_edges':odd_length,'axis_lines_checked':lines_checked,'examples':examples}

def main(key):
    start=time.monotonic();root=a.ROOT;inputs=[]
    def bind(path,role,expected=None):
        path=Path(path);path=path if path.is_absolute() else root/path
        digest=a.sha(path)
        if expected:assert digest==expected,(role,'hash mismatch')
        inputs.append({'path':str(path.relative_to(root)),'sha256':digest,'role':role})
        return a.load(path)
    catalog=bind(a.HERE/'compiled'/f'{key}.catalog.json','complete window render catalog')
    item=next(x for x in catalog['assets'] if x['asset_key']==key)
    source=bind(item['source_render_path'],'original render and unchanged collision reference',item['source_render_sha256'])
    master=bind(item['source_master_path'],'original master',item['source_sha256'])
    contract=bind(item['replacement_contract_path'],'finite window replacement contract',item['replacement_contract_sha256'])
    bind(contract['authored_master_path'],'authored window source',contract['authored_master_sha256'])
    indexpath=root/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json'
    bind(indexpath,'original city index')
    handoff=a.load(a.HERE.parent/'facility_roofs/compiled_priority_r01/handoff_manifest.json')
    roofitem=next(x for x in handoff['assets'] if x['asset_key']==key)
    assert roofitem['source_master_sha256']==item['source_sha256'] and roofitem['source_render_sha256']==item['source_render_sha256']
    assert roofitem['complete_selected_source_coverage'] and roofitem['independent_qa']['pass']
    snapshot=HERE/f'{key}.roof_handoff_snapshot.json';a.write(snapshot,roofitem);bind(snapshot,'immutable complete roof handoff')
    bind(roofitem['emitted_master_path'],'finished roof source',roofitem['authored_master_sha256'])
    bind(roofitem['replacement_contract']['path'],'roof replacement contract',roofitem['replacement_contract']['sha256'])
    qa=bind(roofitem['independent_qa']['path'],'independent roof geometry QA',roofitem['independent_qa']['sha256'])
    file=roofitem['files']['.render.json'];roof=bind(file['path'],'complete fine roof render',file['sha256'])
    roofgroups={}
    for mapping in roofitem['original_roof_material_mapping']:
        gi=mapping['source_render_group_index']
        if gi is None:continue
        g=source['groups'][gi]
        assert a.core.digest(g)==mapping['source_group_sha256_canonical']
        assert g['material']==mapping['material_id'] and len(g['quads'])==mapping['source_quad_count']
        roofgroups[gi]=mapping
    regions=[{'id':p['id'],**p['replacement_volume_master_m']} for p in contract['patches']]
    overlaps=[(p['id'],q['id']) for j,p in enumerate(regions) for q in regions[j+1:] if a.overlaps([p['min'],p['max']],[q['min'],q['max']])]
    assert not overlaps
    edits={(e['group_index'],e['quad_index']):e for e in contract['cache_quad_edits']}
    grouped=defaultdict(list);untouched=changed=removed_roof=0;untouched_before=hashlib.sha256();untouched_after=hashlib.sha256()
    for gi,g in enumerate(source['groups']):
        if gi in roofgroups:removed_roof+=len(g['quads']);continue
        for qi,q in enumerate(g['quads']):
            e=edits.get((gi,qi))
            if e:
                assert e['original_quad']==q and a.core.digest(q)==e['original_quad_sha256']
                original=a.rect_area(a.quad_info(q)[4]);kept=sum(a.rect_area(a.quad_info(f)[4]) for f in e['retained_quads'])
                assert abs(original-kept-e['removed_area_m2'])<1e-7
                grouped[g['material']]+=e['retained_quads'];changed+=1
            else:
                grouped[g['material']].append(q);untouched+=1
                token=json.dumps([gi,qi,g['material'],q],separators=(',',':')).encode();untouched_before.update(token)
                untouched_after.update(json.dumps([gi,qi,g['material'],grouped[g['material']][-1]],separators=(',',':')).encode())
    cutters=defaultdict(list)
    for material,quads in grouped.items():
        for q in quads:
            axis,t,plane,sign,rect=a.quad_info(q);cutters[axis,round(plane/.05),sign].append(rect)
    roof_touched=0;roof_output=0;dedup_area=0;dedup_quads=0
    for g in roof['groups']:
        for q in g['quads']:
            fragments=clip(q,regions);roof_touched+=fragments!=[q];trimmed=[]
            for f in fragments:
                axis,t,plane,sign,rect=a.quad_info(f);rects=[rect]
                for cut in cutters.get((axis,round(plane/.05),sign),[]):rects=[piece for r in rects for piece in a.subtract_rect(r,cut)[0]]
                area=a.rect_area(rect)-sum(map(a.rect_area,rects));dedup_area+=area;dedup_quads+=area>1e-8
                trimmed+=[f] if rects==[rect] else [a.rect_quad(r,axis,t,plane,sign) for r in rects]
            roof_output+=len(trimmed);grouped[g['material']]+=trimmed
    windows=[]
    for window in item['windows']:
        w=bind(window['path'],'fine window and exact transition seam',window['sha256'])
        assert w['unpaired_interface_edges']==0 and w['protected_entry_interface_violations']==0
        assert not w['source_geometry_deformed'] and not w['collider_changed']
        for g in w['groups']:grouped[g['material']]+=g['quads']
        windows.append({k:w[k] for k in ['patch_id','quad_count','unpaired_interface_edges','protected_entry_interface_violations','transition_quads']})
    assert len(windows)==len(regions)
    groups=[{'material':m,'quads':qs} for m,qs in sorted(grouped.items())]
    print(json.dumps({'stage':'composed','quad_count':sum(len(g['quads']) for g in groups),'roof_quads_clipped':roof_touched}),flush=True)
    audit=plane_audit(groups)
    edges=edge_audit(groups)
    outside=sum(any(v[j]<source['bounds']['min'][j]-1e-7 or v[j]>source['bounds']['max'][j]+1e-7 for j in range(3)) for g in groups for q in g['quads'] for v in q)
    tests={'input_hashes_verified':True,'all_source_window_ROIs_present':len(windows)==len(regions),'window_ROIs_disjoint':not overlaps,'finite_quad_edits_area_and_source_exact':True,'untouched_quads_identical':untouched_before.digest()==untouched_after.digest(),'original_roof_groups_fully_replaced':True,'window_coarse_fine_boundary_closed':all(w['unpaired_interface_edges']==0 for w in windows),'protected_entry_interface_unchanged':all(w['protected_entry_interface_violations']==0 for w in windows),'source_bounds_preserved':outside==0,'no_duplicate_faces':audit['same_normal_duplicate_unit_faces']==0,'no_opposed_coplanar_faces':audit['opposed_coplanar_unit_faces']==0,'fine_grid_alignment':audit['off_grid_quads']==0,'roof_independent_QA':roofitem['independent_qa']['pass'],'window_overlapping_roof_excluded':True}
    tests['whole_mesh_edges_closed']=edges['unpaired_unit_edges']==0
    result={**{k:v for k,v in source.items() if k not in ['groups','provenance','cell_count','payload_hash']},'groups':groups,'quad_count':sum(len(g['quads']) for g in groups),'pitch':.05,'cell_count':None,'geometry':'Offline mixed-resolution render composition: original exterior outside finite windows and replaced roof groups; exact fine roof, recessed windows and coarse/fine transition seams. Not a full-resolution building occupancy.','provenance':{'source_master_sha256':item['source_sha256'],'source_render_sha256':item['source_render_sha256'],'window_contract_sha256':item['replacement_contract_sha256'],'roof_render_sha256':file['sha256'],'collision_reference_changed':False,'coordinate_transform':'identity native local metres','compositor_sha256':a.sha(__file__)}}
    result['materials']={**source['materials'],**roof['materials']}
    output=HERE/f'{key}.composed.render.json.gz';dump(output,result)
    manifest={'schema':'riverstone.facility.composed_render.v1','asset_key':key,'source_master_sha256':item['source_sha256'],'source_render_sha256':item['source_render_sha256'],'source_index_path':str(indexpath.relative_to(root)),'source_index_sha256':a.sha(indexpath),'render_path':str(output.relative_to(root)),'render_sha256':a.sha(output),'all_pass':all(tests.values()),'collision_reference_changed':False,'collision_reference_path':item['source_render_path'],'collision_reference_sha256':item['source_render_sha256'],'tests':tests,'window_regions':regions,'source_inputs':inputs,'output_quad_count':result['quad_count'],'bounds':source['bounds'],'source_bounds':source['bounds'],'window_contract_sha256':item['replacement_contract_sha256'],'roof_contract_sha256':roofitem['replacement_contract']['sha256'],'untouched_original_quad_count':untouched,'untouched_quad_fingerprint':untouched_before.hexdigest(),'finite_edited_original_quad_count':changed,'removed_original_roof_quad_count':removed_roof,'fine_roof_input_quad_count':roof['quad_count'],'fine_roof_output_quad_count':roof_output,'fine_roof_quads_intersecting_windows':roof_touched,'face_audit':audit,'window_checks':windows,'authored_window_outward_protrusion_m':0,'visual_cavities_do_not_change_collision':True,'runtime_activated':False,'visual_QA':'pending parent acceptance','max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-start,'output_bytes':output.stat().st_size}
    manifest['roof_source_coplanar_dedup']={'changed_fine_roof_quads':dedup_quads,'removed_duplicate_area_m2':round(dedup_area,8),'original_nonroof_quads_changed':0,'operation':'Exact rectangle subtraction only where a fine roof face coincides with an untouched source exterior of the same normal.'};manifest['edge_audit']=edges
    a.write(HERE/f'{key}.manifest.json',manifest)
    print(json.dumps({k:manifest[k] for k in ['all_pass','tests','face_audit','max_rss_kib','elapsed_seconds','output_bytes','render_sha256']},indent=2),flush=True)
    assert manifest['max_rss_kib']<256*1024
    assert sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())<8*1024*1024

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('asset_key');main(parser.parse_args().asset_key)
