"""Seal a finite-region composition after emitted geometry and input closure QA."""
import argparse,collections,hashlib,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'composed_runtime')]
import author as a
import stream_render as sr

def rays(render,contract,key):
    qa_path=HERE/'aperture_rules/generated/structural_qa.json';qa=next(x for x in a.load(qa_path)['assets'] if x['asset_key']==key)
    windows={p['id']:p for p in contract['patches']};records=[]
    for w in qa['continuous_pane_witnesses']:
        p=windows[w['patch_id']];tr=a.core.transform(p['local_to_master']);x,y=w['local_xy_m'];start=a.core.apply(tr,[x,y,.3]);direction=[tr['basis'][j][2] for j in range(3)];axis=next(j for j,v in enumerate(direction) if abs(v)>.9);sign=direction[axis];t=[j for j in range(3) if j!=axis]
        records.append({'patch_id':p['id'],'origin_world':start,'normal_axis':axis,'outward_sign':sign,'source_exposure':w['exposure_status'],'expected_exposed':w['whole_master_recess_exposed_witness'],'expected_glass_front_world':a.core.apply(tr,[x,y,-.15])[axis],'hits':[]})
    digest=hashlib.sha256();vertices=0;lo=[float('inf')]*3;hi=[float('-inf')]*3
    for m,q in sr.iter_quads(render):
        digest.update(json.dumps([m,q],separators=(',',':')).encode());axis,t,plane,s,r=a.quad_info(q)
        for v in q:
            vertices+=1
            for j in range(3):lo[j]=min(lo[j],v[j]);hi[j]=max(hi[j],v[j])
        for w in records:
            if axis!=w['normal_axis']:continue
            p=w['origin_world'];distance=(p[axis]-plane)*w['outward_sign']
            if distance<-.00001 or distance>1.5:continue
            if r[0]<=p[t[0]]<r[2] and r[1]<=p[t[1]]<r[3]:w['hits'].append({'distance_m':round(distance,8),'material':m,'plane':plane,'normal_sign':s})
    for w in records:
        w['hits'].sort(key=lambda h:h['distance_m']);w['first_hit']=w['hits'][0] if w['hits'] else None
        w['fine_glass_front_matches_source_recess']=bool(w['first_hit'] and w['first_hit']['material']=='glass' and abs(w['first_hit']['plane']-w['expected_glass_front_world'])<1e-6)
        if w['expected_exposed']:assert w['fine_glass_front_matches_source_recess'],w
    return {'schema':'riverstone.facility.emitted_window_ray_qa.v1','asset_key':key,'render_sha256':a.sha(render),'source_structural_qa_path':str(qa_path.relative_to(a.ROOT)),'source_structural_qa_sha256':a.sha(qa_path),'windows':records,'expected_exposed_count':sum(w['expected_exposed'] for w in records),'visible_exact_recess_count':sum(w['fine_glass_front_matches_source_recess'] for w in records),'ordered_material_quad_digest':digest.hexdigest(),'vertices':vertices,'bounds':{'min':lo,'max':hi},'scope':'One clear-pane local source witness per opening projected onto actual emitted quads. Blocked original shared-wall panes stay blocked and are recorded separately.'}

def run(key):
    start=time.monotonic();out=HERE/'composed'/key;pre=a.load(out/'preflight.json');assert pre['asset_key']==key;render=a.ROOT/pre['render_path'];assert a.sha(render)==pre['render_sha256'];cat_path=HERE/'compiled'/key/'catalog.json';cat=a.load(cat_path);contract=a.load(a.ROOT/cat['window_contract_path']);master=a.load(a.ROOT/cat['canonical_master_path']);source=a.load(a.ROOT/cat['source_master_path']);source_render=a.load(a.ROOT/cat['source_render_path'])
    qr=rays(render,contract,key);qp=out/'emitted_window_ray_qa.json';a.write(qp,qr)
    assert qr['vertices']==pre['summary']['quad_count']*4 and qr['bounds']==pre['summary']['bounds']
    analytic=[bb for c,i,o,t,bb in a.source_inventory(master) if o['action']=='paint'];bounds={'min':[min(bb[0][j] for bb in analytic) for j in range(3)],'max':[max(bb[1][j] for bb in analytic) for j in range(3)]}
    outside=0
    for m,q in sr.iter_quads(render):
        outside+=sum(any(v[j]<bounds['min'][j]-1e-6 or v[j]>bounds['max'][j]+1e-6 for j in range(3)) for v in q)
    assert outside==0,('outside canonical analytic AABB',outside)
    tests={'same_normal_duplicate_unit_faces_zero':pre['face_audit']['same_normal_duplicate_unit_faces']==0,'opposed_coplanar_unit_faces_zero':pre['face_audit']['opposed_coplanar_unit_faces']==0,'offgrid_quads_zero':pre['face_audit']['off_grid_quads']==0,'whole_render_unpaired_unit_edges_zero':pre.get('edge_audit',{}).get('unpaired_unit_edges')==0,'original_render_unpaired_unit_edges_zero':pre.get('original_edge_audit',{}).get('unpaired_unit_edges')==0,'source_clear_pane_rays_recessed_exactly':all(w['fine_glass_front_matches_source_recess'] for w in qr['windows'] if w['expected_exposed']),'all_vertices_inside_canonical_analytic_aabb':outside==0,'runtime_96mib_cap':pre['summary']['runtime_cap_96mib_pass'],'source_contact_new_occupancy_none':not cat['source_contact_occupancy_authored'],'source_shapes_uncropped':not cat['source_shapes_cropped'],'all_roi_chunks_complete':cat['complete']}
    assert all(tests.values()),tests
    inputs=list(pre['source_inputs']);extra=[(cat_path,'complete region catalog'),(out/'preflight.json','exact emitted face and boundary QA'),(qp,'actual emitted window ray QA'),(out/'outside_retained_sourcequads.json.gz','surface-overlay retained source quads'),(out/'finite_source_quad_edits.json.gz','finite cache quad ownership'),(HERE/'canonical_adapter/generated/structural_qa.json','canonical transform and selector tests'),(HERE/'canonical_adapter/generated/composition_report.json','source preservation proof'),(HERE/'aperture_rules/generated/structural_qa.json','existing aperture source witness QA'),(HERE/'aperture_rules/generated/determinism_qa.json','source adapter determinism'),(Path(__file__),'final emitted geometry verifier')]
    plan=a.load(a.ROOT/cat['plan_path']);now_catalog=a.ROOT/plan['canonical_catalog_path'];revision=None
    if a.sha(now_catalog)!=plan['canonical_catalog_sha256']:
        snapshot=HERE/'contact_plan/canonical_catalog_at_plan.json';assert a.sha(snapshot)==plan['canonical_catalog_sha256'];old=a.load(snapshot);now=a.load(now_catalog);assert old['assets']==now['assets'];difference={k for k in old.keys()|now.keys() if old.get(k)!=now.get(k)};assert difference=={'adapter_sha256'}
        revision={'original_catalog_path':plan['canonical_catalog_path'],'original_catalog_sha256':plan['canonical_catalog_sha256'],'immutable_snapshot_path':str(snapshot.relative_to(a.ROOT)),'current_catalog_sha256':a.sha(now_catalog),'changed_fields':['adapter_sha256'],'all_asset_geometry_rows_byte_equivalent':True,'reason':'Source-authoring guard tests strengthened after planning. Masters, scoped contracts and all per-asset rows unchanged; captured pre-change catalog resolves the immutable planned hash.'};extra.append((snapshot,'immutable exact planned catalog snapshot'))
    extra.append((now_catalog,'current canonical source catalog with unchanged per-asset rows'))
    for p,role in extra:inputs.append({'path':str(p.resolve().relative_to(a.ROOT)),'sha256':a.sha(p),'role':role})
    unique={}
    for i in inputs:
        assert a.sha(a.ROOT/i['path'])==i['sha256'],i
        if i['path'] in unique:assert unique[i['path']]['sha256']==i['sha256']
        unique[i['path']]=i
    inputs=list(unique.values());source_index=next(i for i in inputs if i['role']=='unchanged original city index')
    manifest={'schema':'riverstone.facility.composed_render.v1','asset_key':key,'roof_variant_asset_key':key,'source_master_sha256':cat['source_sha256'],'source_render_sha256':cat['source_render_sha256'],'source_index_sha256':source_index['sha256'],'render_path':pre['render_path'],'render_sha256':pre['render_sha256'],'all_pass':True,'collision_reference_changed':False,'tests':tests,'window_regions':[{'id':p['id'],**p['replacement_volume_master_m']} for p in contract['patches']],'contact_regions':[r for r in cat['ordered_regions'] if r['kind']=='source_contact'],'source_inputs':inputs,'output_quad_count':pre['summary']['quad_count'],'vertex_normal_material_bytes':pre['summary']['vertex_normal_material_bytes'],'ordered_material_quad_digest':qr['ordered_material_quad_digest'],'bounds':pre['summary']['bounds'],'bounds_contract':{'source_master_sha256':cat['source_sha256'],'coarse_render_bounds':source_render['bounds'],'composed_render_bounds':pre['summary']['bounds'],'analytic_source_bounds':bounds,'outside_analytic_aabb_vertices':0,'reason':'Selected detailed roof and finite canonical window/contact evaluation restore native source detail. Original coarse cache/index bounds remain unchanged.','proof_scope':'Every emitted vertex tested against final canonical authored source AABB; this is not whole-solid containment.'},'authoring_revision':{'original_master_path':cat['source_master_path'],'original_sha256':cat['source_sha256'],'canonical_master_path':cat['canonical_master_path'],'canonical_master_sha256':cat['canonical_master_sha256'],'glass_revision':'Existing glass slab reduced by exact instance+feature scoped front/rear cuts; source aperture/frame/sill/mullion/shutter operations unchanged.','source_contact_new_occupancy':False,'original_occupancy_unchanged':False,'source_shapes_cropped':False},'outside_retained_sourcequads_path':str((out/'outside_retained_sourcequads.json.gz').relative_to(a.ROOT)),'outside_retained_sourcequads_sha256':a.sha(out/'outside_retained_sourcequads.json.gz'),'finite_source_quad_edits_path':str((out/'finite_source_quad_edits.json.gz').relative_to(a.ROOT)),'finite_source_quad_edits_sha256':a.sha(out/'finite_source_quad_edits.json.gz'),'untouched_original_quads':pre['source_untouched_quads'],'untouched_original_quad_digest':pre['source_untouched_sha256'],'finite_edited_original_quads':pre['source_finite_edited_quads'],'catalog_revision_resolution':revision,'global_constraint_scope':'Original full-source constraints retained exactly; bounded ROI compiler does not reevaluate full-building constraints. Complete selected roof QA verifies its own nonempty domain; source nonroof changes are only glass-feature scoped cuts.','runtime_activated':False,'visual_qa':'Parent native-cache and real scene review pending.','elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    target=out/(key+'.manifest.json');a.write(target,manifest);files=inputs+[{'path':pre['render_path'],'sha256':pre['render_sha256'],'role':'composed render output'},{'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target),'role':'sealed bounded composition manifest'}];closure=out/'file_closure.json';a.write(closure,{'schema':'riverstone.facility.composition_file_closure.v1','asset_key':key,'files':files,'file_count':len(files),'hash_mismatches':0,'catalog_revision_resolution':revision});print(json.dumps({'manifest':str(target.relative_to(a.ROOT)),'sha256':a.sha(target),'closure':str(closure.relative_to(a.ROOT)),'file_count':len(files),'quads':manifest['output_quad_count'],'all_pass':True,'window_rays':qr['visible_exact_recess_count'],'bounds':manifest['bounds'],'seconds':manifest['elapsed_seconds'],'rss_kib':manifest['max_rss_kib']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('asset');run(p.parse_args().asset)
