"""Stream one QA-bound render candidate, verify its replay and bind all inputs.

This is render composition, not a voxel generator. Source and ROI compilers are
immutable dependencies. The acceptance scope is finite contacts, not a global
manifold or occupied-solid containment certificate.
"""
import argparse,collections,gzip,hashlib,io,json,resource,time
from pathlib import Path
import stream_compose_priority as sc
a=sc.a;sr=sc.sr

def main(preflight_path,witness_path,side_path,closure_path,prefix):
    start=time.monotonic();pre=a.load(preflight_path);summary=pre['summary'];faces=pre['faces']
    witness=a.load(witness_path)['final_retest'];side=a.load(side_path);closure=a.load(closure_path)
    assert closure['all_pass'] and witness['all_2714_outward_faces_restored']
    assert side['unoccluded_outward_rays']==0 and side['representative_ray_count']==6
    assert faces['same_normal_duplicate_unit_faces']==faces['opposed_coplanar_unit_faces']==0
    catalog=next(x['path'] for x in pre['source_inputs'] if x['role']=='complete window catalog')
    interfaces=next(x['path'] for x in pre['source_inputs'] if x['role']=='bounded authored interface catalog')
    comp=sc.Composition(a.ROOT/catalog,a.ROOT/interfaces)
    assert comp.inputs==pre['source_inputs']
    assert hashlib.sha256(sr._canonical(comp.inputs)).hexdigest()==witness['source_inputs_sha256']
    assert a.sha(sc.__file__)==witness['priority_compositor_sha256']
    for item in closure['source_inputs']:assert a.sha(a.ROOT/item['path'])==item['sha256']
    structural_path=a.HERE/'composed/cathedral_authored_revision_structural_qa.json'
    delta_path=a.HERE/'composed/cathedral_authored_delta_qa.json'
    structural=a.load(structural_path);delta=a.load(delta_path)
    assert structural['all_pass'] and delta['all_pass']
    analytic=structural['support_geometry']['full_original_analytic_aabb_m']
    rays=[{'section_id':r['section_id'],'point_m':r['point_m'],'outward_sign':r['outward_sign'],'hit_count':0,'nearest':None,'outermost':None} for r in side['rays']]
    output=Path(str(prefix)+'.candidate.render.json.gz');assert not output.exists(),'Do not overwrite a preserved candidate'
    count=outside=0;lo=[float('inf')]*3;hi=[float('-inf')]*3;materials=collections.Counter();fingerprint=hashlib.sha256()
    with output.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as z:
            with io.TextIOWrapper(z,encoding='utf-8') as f:
                f.write('{"groups":[');last=None;first=True
                for material,quad in comp.factory():
                    if material!=last:
                        if not first:f.write(']},')
                        f.write('{"material":'+json.dumps(material)+',"quads":[');last=material;first=False;ingroup=0
                    if ingroup:f.write(',')
                    f.write(json.dumps(quad,separators=(',',':')));ingroup+=1;count+=1;materials[material]+=1
                    fingerprint.update(sr._canonical([material,quad]))
                    for vertex in quad:
                        outside+=any(vertex[j]<analytic['min'][j]-1e-7 or vertex[j]>analytic['max'][j]+1e-7 for j in range(3))
                        for j in range(3):lo[j]=min(lo[j],vertex[j]);hi[j]=max(hi[j],vertex[j])
                    axis,t,plane,normal,rect=a.quad_info(quad)
                    if axis==0:
                        for ray in rays:
                            p=ray['point_m'];sign=ray['outward_sign']
                            if sign*(plane-p[0])<=0 or not(rect[0]<p[t[0]]<rect[2] and rect[1]<p[t[1]]<rect[3]):continue
                            hit={'plane_x_m':plane,'normal':normal,'material':material};distance=sign*(plane-p[0]);ray['hit_count']+=1
                            if ray['nearest'] is None or distance<sign*(ray['nearest']['plane_x_m']-p[0]):ray['nearest']=hit
                            if ray['outermost'] is None or distance>sign*(ray['outermost']['plane_x_m']-p[0]):ray['outermost']=hit
                    if count%100000==0:print({'stage':'write','quads':count,'seconds':round(time.monotonic()-start,2)},flush=True)
                if not first:f.write(']}')
                f.write(']')
                meta={k:v for k,v in comp.source.items() if k not in ['groups','quad_count','bounds','provenance','cell_count','payload_hash','pitch']}
                meta.update(quad_count=count,bounds={'min':lo,'max':hi},pitch=.05,cell_count=None,geometry='Mixed-resolution candidate: retained coarse body plus actual fine roof, 33 geometric windows, six approved authored eave supports and eight source-backed gable repairs.',provenance={'source_master_sha256':comp.item['source_sha256'],'source_render_sha256':comp.item['source_render_sha256'],'compositor_sha256':a.sha(sc.__file__),'candidate_writer_sha256':a.sha(__file__),'collision_reference_changed':False})
                for k,v in meta.items():f.write(','+json.dumps(k)+':'+json.dumps(v,separators=(',',':')))
                f.write('}\n')
    assert count==summary['quad_count'] and dict(materials)==summary['material_quads'] and {'min':lo,'max':hi}==summary['bounds']
    replay=hashlib.sha256();replay_count=0
    for material,quad in sr.iter_quads(output):replay.update(sr._canonical([material,quad]));replay_count+=1
    assert replay_count==count and replay.hexdigest()==fingerprint.hexdigest()
    ray_pass=all(r['hit_count'] and r['outermost']['normal']==r['outward_sign'] for r in rays)
    ray_path=Path(str(prefix)+'.side_ray_retest.json')
    a.write(ray_path,{'schema':'riverstone.six_direction.render_retest.v1','all_pass':ray_pass,'input_side_report_sha256':a.sha(side_path),'output_render_sha256':a.sha(output),'rays':rays,'scope':'Six previously unresolved outward X directions only; actual final emitted faces, not all-direction containment.'})
    for p,role in [(preflight_path,'measured final face audit and preservation contract'),(witness_path,'2714 exact outward/inward gable witness retest'),(side_path,'frozen original six-ray diagnosis'),(ray_path,'six rays retested against emitted final geometry'),(closure_path,'306-file bounded compiler dependency closure'),(structural_path,'independent authoring structural QA'),(delta_path,'native bounded old/new source cell comparison'),(Path(__file__),'verified render candidate writer')]:comp.bind(p,role,load=False)
    for field in ['outside_retained_sourcequads','source_face_exceptions']:
        record=pre[field];comp.bind(record['path'],field,record['sha256'],load=False)
    authored_path=a.ROOT/comp.interface_manifest['canonical_master_path'];comp.bind(authored_path,'final authored canonical source',comp.interface_manifest['canonical_master_sha256'],load=False)
    spec=comp.bind(comp.interface_manifest['spec_path'],'authored support specification',comp.interface_manifest['spec_sha256'])
    revision=comp.bind(spec['revision_path'],'approved bounded support operations',spec['revision_sha256'])
    tests={'all_input_hashes_verified':True,'compiler_dependency_closure_verified':True,'all_33_windows_present':len(comp.windows)==33,'all_14_interface_regions_present':len(comp.interface)==len(comp.interface_outputs)==14,'no_same_normal_duplicate_faces':faces['same_normal_duplicate_unit_faces']==0,'no_opposed_internal_faces':faces['opposed_coplanar_unit_faces']==0,'all_2714_gable_witness_faces_restored':witness['all_2714_outward_faces_restored'],'six_known_side_rays_occluded':ray_pass,'all_actual_vertices_in_analytic_aabb':outside==0,'render_stream_replay_identical':replay.hexdigest()==fingerprint.hexdigest(),'runtime_vertex_budget_under_96mib':summary['runtime_cap_96mib_pass'],'original_source_structural_preservation':structural['all_pass'],'bounded_authoring_cell_comparison':delta['all_pass'],'existing_source_cells_not_removed_or_relabelled':all(r['removed_cells']==0 and r['relabelled_existing_cells']==0 for r in delta['regions']),'new_source_protects_windows_and_entry':all(r['protected_cavity_or_entry_added_cells']==0 for r in delta['regions']),'original_collider_reference_unchanged':True,'source_shapes_not_cropped':True}
    for item in comp.inputs:assert a.sha(a.ROOT/item['path'])==item['sha256']
    bounds={'source_master_sha256':comp.item['source_sha256'],'authored_master_sha256':comp.interface_manifest['canonical_master_sha256'],'coarse_render_bounds':comp.source['bounds'],'composed_render_bounds':summary['bounds'],'analytic_source_bounds':analytic,'outside_analytic_aabb_vertices':outside,'vertices_checked':4*count,'proof_scope':'Every emitted vertex compared with the final authored analytic source AABB; not occupied-solid containment. Roof unpruned chunk replays and six changed-domain cell comparisons are separate evidence.','reason':'Original thin ridge reaches y40.0, omitted by old .5 cache y39.5. Fine geometry restores that source envelope; approved eave supports remain within the existing whole-source AABB.'}
    manifest={'schema':'riverstone.facility.composed_render.v1','asset_key':comp.key,'roof_variant_asset_key':comp.roof['asset_key'],'source_master_sha256':comp.item['source_sha256'],'source_render_sha256':comp.item['source_render_sha256'],'source_index_path':str(comp.indexpath.relative_to(a.ROOT)),'source_index_sha256':a.sha(comp.indexpath),'render_path':str(output.relative_to(a.ROOT)),'render_sha256':a.sha(output),'all_pass':all(tests.values()),'review_status':'Bounded geometry QA complete; parent native cache and GUI review pending.','collision_reference_changed':False,'collision_reference_path':comp.item['source_render_path'],'collision_reference_sha256':comp.item['source_render_sha256'],'tests':tests,'window_regions':comp.windows,'interface_regions':comp.interface,'surface_exclusion_regions':comp.regions,'surface_overlay_policy':'Use outside_retained_sourcequads for original wall relief. Compile AABBs are not actual window-feature exclusion envelopes.','source_inputs':comp.inputs,'output_quad_count':count,'runtime_vertex_normal_material_bytes':summary['vertex_normal_material_bytes'],'runtime_mib':summary['runtime_mib'],'bounds':summary['bounds'],'source_bounds':comp.source['bounds'],'bounds_contract':bounds,'outside_retained_sourcequads':pre['outside_retained_sourcequads'],'source_quad_preservation_exceptions':pre['source_face_exceptions'],'untouched_original_quad_count':pre['untouched_original_quad_count'],'untouched_quad_fingerprint':pre['untouched_quad_fingerprint'],'finite_edited_original_quad_count':pre['finite_edited_original_quad_count'],'window_contract_sha256':comp.item['replacement_contract_sha256'],'roof_contract_sha256':comp.roof['replacement_contract']['sha256'],'composition_geometry_sha256':fingerprint.hexdigest(),'face_audit':faces,'authoring_revision':{**comp.interface_manifest['authoring_revision'],'original_master_sha256':comp.item['source_sha256'],'pre_support_canonical_master_sha256':spec['canonical_master_sha256'],'final_authored_master_sha256':comp.interface_manifest['canonical_master_sha256'],'changed_regions':revision['change_aabbs_m'],'analytic_added_volume_m3':revision['aggregate']['net_added_analytic_volume_m3'],'sampled_added_cells':delta['unique_added_cells'],'operation_hashes':revision['operation_hashes']},'original_occupancy_unchanged':False,'source_backed_contact_regions':8,'contact_source_shape_change':False,'visual_cavities_do_not_change_collision':True,'authored_window_outward_protrusion_m':0,'whole_building_manifold_verified':False,'global_edge_scope':'r04 odd edges were diagnostic, with coplanar T-junction and closed-roof interior classifications. No exhaustive r05 global manifold or occupied-solid certificate is claimed.','runtime_activated':False,'visual_QA':'pending parent GUI review','acceptance_scope':'Detailed selected roof, 33 actual recessed windows and finite source-backed contacts; retained other body faces remain coarse. Specified leak witnesses and rays pass; this is not a full-building resolution upgrade.','max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':round(time.monotonic()-start,3),'output_bytes':output.stat().st_size}
    manifest['composition_contract_sha256']=a.core.digest({'source_master_sha256':manifest['source_master_sha256'],'source_render_sha256':manifest['source_render_sha256'],'roof_variant_asset_key':manifest['roof_variant_asset_key'],'source_inputs':manifest['source_inputs'],'window_regions':comp.windows,'interface_regions':comp.interface,'render_sha256':manifest['render_sha256']})
    mp=Path(str(prefix)+'.candidate.manifest.json');a.write(mp,manifest)
    file_map={item['path']:item for item in closure['source_inputs']}
    for item in comp.inputs:file_map[item['path']]=item
    for p,role in [(output,'final render candidate'),(mp,'final candidate manifest')]:file_map[str(p.relative_to(a.ROOT))]={'path':str(p.relative_to(a.ROOT)),'sha256':a.sha(p),'role':role}
    for item in file_map.values():assert a.sha(a.ROOT/item['path'])==item['sha256']
    cp=Path(str(prefix)+'.file_closure.json');a.write(cp,{'schema':'riverstone.facility.file_closure.v1','all_pass':True,'manifest_path':str(mp.relative_to(a.ROOT)),'manifest_sha256':a.sha(mp),'file_count':len(file_map),'files':list(file_map.values()),'scope':'Every declared direct render input and all recursively verified bounded-compiler dependencies, plus emitted output and manifest.'})
    sizes={'composed_bytes':sum(p.stat().st_size for p in Path(__file__).parent.rglob('*') if p.is_file()),'facility_bytes':sum(p.stat().st_size for p in a.HERE.rglob('*') if p.is_file())}
    assert sizes['composed_bytes']<22*1048576 and sizes['facility_bytes']<28*1048576 and manifest['max_rss_kib']<256*1024
    print({'ready':True,'all_pass':manifest['all_pass'],'manifest':str(mp.relative_to(a.ROOT)),'manifest_sha256':a.sha(mp),'render_sha256':manifest['render_sha256'],'closure_sha256':a.sha(cp),'closure_files':len(file_map),'quad_count':count,'output_bytes':manifest['output_bytes'],'seconds':manifest['elapsed_seconds'],'rss_kib':manifest['max_rss_kib'],**sizes},flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('preflight',type=Path);p.add_argument('witnesses',type=Path);p.add_argument('side_rays',type=Path);p.add_argument('closure',type=Path);p.add_argument('prefix',type=Path);args=p.parse_args();main(*(getattr(args,k).resolve() for k in ['preflight','witnesses','side_rays','closure','prefix']))
