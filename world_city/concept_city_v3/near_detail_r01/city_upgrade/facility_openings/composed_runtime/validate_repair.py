"""Independent render-domain checks for the finite canonical-source repair."""
import hashlib,json,resource,time
from collections import defaultdict
import compose as c
a=c.a;HERE=c.HERE;KEY='registered_port_long_loading_shed'

def main():
    start=time.monotonic();path=HERE/f'{KEY}.r03.manifest.json';m=a.load(path);render=a.load(a.ROOT/m['render_path']);assert a.sha(a.ROOT/m['render_path'])==m['render_sha256'];source=a.load(a.ROOT/m['collision_reference_path']);regions=m['surface_exclusion_regions'];patches=[{'id':r['id'],'replacement_volume_master_m':r} for r in regions];edits=a.cache_contract(source,patches);lookup={(e['group_index'],e['quad_index']):e for e in edits};roof_materials={'slate','slate_dark'}
    kept=defaultdict(list);unchanged=0;area_ok=True;tokens=hashlib.sha256()
    # Exact quad identity proof is separate from face coverage: unmodified
    # source records remain byte-for-byte canonical-equal, not reconstructed.
    indexed={g['material']:{a.core.digest(q) for q in g['quads']} for g in render['groups']}
    for gi,g in enumerate(source['groups']):
        if g['material'] in roof_materials:continue
        for qi,q in enumerate(g['quads']):
            e=lookup.get((gi,qi))
            if e:
                area_ok &= abs(e['original_area_m2']-e['removed_area_m2']-sum(a.rect_area(a.quad_info(f)[4]) for f in e['retained_quads']))<1e-7
                kept[g['material']]+=e['retained_quads']
            else:
                assert a.core.digest(q) in indexed[g['material']],(gi,qi,'untouched source quad missing');unchanged+=1;kept[g['material']].append(q);tokens.update(json.dumps([gi,qi,q],separators=(',',':')).encode())
    del indexed
    outside=sum(any(v[j]<source['bounds']['min'][j]-1e-7 or v[j]>source['bounds']['max'][j]+1e-7 for j in range(3)) for g in render['groups'] for q in g['quads'] for v in q)
    faces=c.plane_audit(render['groups']);edges=c.edge_audit(render['groups'])
    retained=HERE/f'{KEY}.r03.outside_retained_sourcequads.json.gz';a.write(retained,{'schema':'riverstone.facility_openings.outside_source_quads.v1','asset_key':KEY,'groups':[{'material':k,'quads':v} for k,v in sorted(kept.items())],'world_local_aabbs':regions,'source_render_sha256':m['source_render_sha256'],'surface_module_rule':'Only these retained original wall faces may generate coarse surface modules when this composed asset is active. All window and interface replacement regions are excluded.','collision_input_unchanged':True})
    report={'schema':'riverstone.facility.composed_render.structural_qa.v1','asset_key':KEY,'input_render_sha256':m['render_sha256'],'source_master_sha256':m['source_master_sha256'],'source_render_sha256':m['source_render_sha256'],'untouched_original_quads':unchanged,'untouched_original_quads_exact':True,'untouched_original_quad_fingerprint':tokens.hexdigest(),'finite_edits_area_conserved':area_ok,'vertex_count_outside_original_bounds':outside,'face_audit':faces,'edge_audit':edges,'raw_edge_count_is_not_external_leak_count':True,'outside_retained_sourcequads':{'path':str(retained.relative_to(a.ROOT)),'sha256':a.sha(retained)},'external_leak_qa':'independent_interface_qa.json required before all_pass','max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-start}
    a.write(HERE/f'{KEY}.r03.structural_qa.json',report);print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
