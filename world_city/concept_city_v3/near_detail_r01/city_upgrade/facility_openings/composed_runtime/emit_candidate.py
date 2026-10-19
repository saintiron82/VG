"""Emit the parent-requested review candidate without claiming final join approval."""
import gzip,io,json,resource,time
from pathlib import Path
import stream_compose as sc
a=sc.a

def main():
    start=time.monotonic();key='registered_cathedral_nave_aisles_transept';here=Path(__file__).parent
    preflight=a.load(here/(key+'.r04.preflight.json'));summary=preflight['summary'];witness=a.load(a.HERE/'composed/cathedral_gable_witness_retest.json');delta=a.load(a.HERE/'composed/cathedral_authored_delta_qa.json');assert witness['all_pass'] and delta['all_pass']
    assert preflight['faces']['same_normal_duplicate_unit_faces']==preflight['faces']['opposed_coplanar_unit_faces']==0
    comp=sc.Composition(a.HERE/'compiled_active_r02'/f'{key}.catalog.json',here/'cathedral_gable_contacts_r02/catalog.json')
    expected={x['path']:x['sha256'] for x in preflight['source_inputs']}
    for item in comp.inputs:assert expected.get(item['path'])==item['sha256'],'Candidate source changed after measured preflight'
    output=here/(key+'.r04.candidate.render.json.gz');n=0
    with output.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as zipped:
            with io.TextIOWrapper(zipped,encoding='utf-8') as f:
                f.write('{"groups":[');last=None;first=True
                for material,q in comp.factory():
                    if material!=last:
                        if not first:f.write(']},')
                        f.write('{"material":'+json.dumps(material)+',"quads":[');last=material;first=False;ingroup=0
                    if ingroup:f.write(',')
                    f.write(json.dumps(q,separators=(',',':')));ingroup+=1;n+=1
                if not first:f.write(']}')
                f.write(']');assert n==summary['quad_count']
                meta={k:v for k,v in comp.source.items() if k not in ['groups','quad_count','bounds','provenance','cell_count','payload_hash','pitch']};meta.update(quad_count=n,bounds=summary['bounds'],pitch=.05,cell_count=None,geometry='Mixed-resolution review candidate: actual detailed roof, 33 geometric windows, six authored eave contacts and four unchanged-source gable repairs. Further join classification pending.',provenance={'source_master_sha256':comp.item['source_sha256'],'source_render_sha256':comp.item['source_render_sha256'],'compositor_sha256':a.sha(sc.__file__),'candidate_writer_sha256':a.sha(__file__),'collision_reference_changed':False})
                for k,v in meta.items():f.write(','+json.dumps(k)+':'+json.dumps(v,separators=(',',':')))
                f.write('}\n')
    for path,role in [(a.HERE/'composed/cathedral_gable_witness_retest.json','same failed gable witness retest'),(a.HERE/'composed/cathedral_authored_delta_qa.json','bounded original/new source cell comparison'),(a.HERE/'composed/cathedral_compilation_input_closure.json','252 verified compiler dependencies'),(here/(key+'.r04.preflight.json'),'measured face and edge diagnostic'),(Path(__file__),'review candidate writer')]:comp.bind(path,role,load=False)
    structural=a.load(a.HERE/'composed/cathedral_authored_revision_structural_qa.json');analytic=structural['support_geometry']['full_original_analytic_aabb_m'];bounds={'source_master_sha256':comp.item['source_sha256'],'authored_master_sha256':comp.interface_manifest['canonical_master_sha256'],'coarse_render_bounds':comp.source['bounds'],'composed_render_bounds':summary['bounds'],'analytic_source_bounds':analytic,'outside_analytic_aabb_vertices':0 if all(summary['bounds']['min'][j]>=analytic['min'][j] and summary['bounds']['max'][j]<=analytic['max'][j] for j in range(3)) else None,'proof_scope':'All final vertices contributed to measured composition extrema, which lie inside the analytic whole-source AABB. This is not occupied-solid containment.','reason':'Restore original thin ridge source y40.0 omitted by old .5 cache y39.5; eave authoring revision stays within existing analytic source bounds.'}
    manifest={'schema':'riverstone.facility.composed_render.v1','asset_key':key,'roof_variant_asset_key':comp.roof['asset_key'],'source_master_sha256':comp.item['source_sha256'],'source_render_sha256':comp.item['source_render_sha256'],'source_index_path':str(comp.indexpath.relative_to(a.ROOT)),'source_index_sha256':a.sha(comp.indexpath),'render_path':str(output.relative_to(a.ROOT)),'render_sha256':a.sha(output),'all_pass':False,'review_status':'CANDIDATE: additional join classification pending; parent may inspect actual geometry, not final activation approval.','collision_reference_changed':False,'collision_reference_path':comp.item['source_render_path'],'collision_reference_sha256':comp.item['source_render_sha256'],'tests':{'input_hashes_match_measured_preflight':True,'same_and_opposed_duplicate_faces_zero':True,'failed_four_gable_witnesses_restored':True,'protected_window_and_entry_added_cells_zero':True,'runtime_96mib_budget_pass':summary['runtime_cap_96mib_pass'],'additional_join_review_complete':False},'window_regions':comp.windows,'interface_regions':comp.interface,'source_inputs':comp.inputs,'output_quad_count':n,'runtime_vertex_normal_material_bytes':summary['vertex_normal_material_bytes'],'runtime_mib':summary['runtime_mib'],'bounds':summary['bounds'],'bounds_contract':bounds,'authoring_revision':comp.interface_manifest['authoring_revision'],'original_occupancy_unchanged':False,'face_audit':preflight['faces'],'edge_audit':preflight['edges'],'source_shape_crop':False,'runtime_activated':False,'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'output_bytes':output.stat().st_size}
    manifest['composition_contract_sha256']=a.core.digest({'inputs':manifest['source_inputs'],'render_sha256':manifest['render_sha256'],'window_regions':comp.windows,'interface_regions':comp.interface,'source_master_sha256':manifest['source_master_sha256']});mp=here/(key+'.r04.candidate.manifest.json');a.write(mp,manifest)
    sizes={'composed_bytes':sum(p.stat().st_size for p in here.rglob('*') if p.is_file()),'folder_bytes':sum(p.stat().st_size for p in a.HERE.rglob('*') if p.is_file())};assert sizes['composed_bytes']<13*1048576 and sizes['folder_bytes']<20*1048576
    print({'candidate_ready':True,'manifest':str(mp.relative_to(a.ROOT)),'manifest_sha256':a.sha(mp),'render_sha256':manifest['render_sha256'],'quads':n,'bytes':manifest['output_bytes'],'seconds':manifest['elapsed_seconds'],'rss_kib':manifest['max_rss_kib'],**sizes},flush=True)

if __name__=='__main__':main()
