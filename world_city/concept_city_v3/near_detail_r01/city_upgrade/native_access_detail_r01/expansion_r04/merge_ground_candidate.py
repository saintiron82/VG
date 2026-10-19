"""Append sealed ground deltas, reusing identical meshes. No live catalog write."""
from pathlib import Path
import copy, hashlib, json
H = Path(__file__).resolve().parent
R = H.parents[5]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n')
def verified(ref):
    p=R/ref['path']; assert sha(p)==ref['sha256'], str(p)
    return read(p)
def ref(p): return {'path':str(p.relative_to(R)), 'sha256':sha(p)}
def main():
    hand=read(H/'ground_candidate_handoff.json')
    assert hand['sealed'] and hand['all_geometry_and_shared_mesh_tests_pass']
    plans=[verified(r) for r in hand['plans']]
    cats=[verified(r) for r in hand['module_catalogs']]
    for r in hand['review_manifests']: verified(r)
    assets=[]; modules={}; demand={}; deps={}; duplicate=0
    index_hash=plans[0]['source_city_index_sha256']
    for i,(p,c) in enumerate(zip(plans,cats)):
        assert p['source_city_index_sha256']==index_hash
        assert c['source_plan_sha256']==hand['plans'][i]['sha256']
        assert c['original_collision_unchanged']
        for a in p['assets']:
            assert a['asset_key'] not in {v['asset_key'] for v in assets}
            assert a['existing_collision_unchanged']; assets.append(copy.deepcopy(a))
        for m in c['modules']:
            if m['id'] in modules:
                assert modules[m['id']]==m, 'Changed duplicate mesh module'
                duplicate+=1
            else: modules[m['id']]=copy.deepcopy(m)
            for k in ['master','render']:
                assert sha(R/m[k+'_path'])==m[k+'_sha256']
        for d in p['module_demand']:
            if d['id'] in demand: assert demand[d['id']]==d
            demand[d['id']]=copy.deepcopy(d)
        for path,digest in c.get('source_dependencies',{}).items():
            if path in deps: assert deps[path]==digest
            deps[path]=digest
    assert len(assets)==hand['prospective_asset_count']==9
    assert len(modules)==hand['prospective_module_count']==169
    assert sum(len(a['placements']) for a in assets)==hand['prospective_placement_count']==2167
    assert duplicate==hand['exact_duplicate_module_rows_verified']==24
    assert assets[:6]==plans[0]['assets']
    assert list(modules.values())[:145]==cats[0]['modules']
    assert all(p['module_key'] in modules for a in assets for p in a['placements'])
    out=H/'combined_ground'; pp=out/'source_plan.json'; cp=out/'module_catalog.json'
    plan=copy.deepcopy(plans[0]); plan.update(revision='r04_ground_9_candidate',assets=assets,module_demand=list(demand.values()),runtime_activation=False)
    plan['merge_provenance']={'handoff':ref(H/'ground_candidate_handoff.json'),'plans':hand['plans'],'module_catalogs':hand['module_catalogs'],'script':ref(Path(__file__)),'existing_six_asset_rows_exact':True,'geometry_files_duplicated':0}
    save(pp,plan)
    cat=copy.deepcopy(cats[0]); cat.update(revision='r04_ground_9_candidate',modules=list(modules.values()),source_plan_sha256=sha(pp),source_dependencies=deps,runtime_activation=False)
    save(cp,cat)
    live=R/'world_city/concept_city_v3/playable_detail_r01/native_access_catalog.json'
    cfg=read(live); assert cfg['source_plan_sha256']==hand['plans'][0]['sha256']
    assert cfg['maximum_active_modules']==120 and cfg['maximum_mesh_bytes']==24000000
    cfg.update(source_plan_path=str(pp.relative_to(R)),source_plan_sha256=sha(pp),module_catalog_path=str(cp.relative_to(R)),module_catalog_sha256=sha(cp),binding_revision='candidate_r04_nine_native_access_types')
    save(out/'runtime_catalog_candidate.json',cfg)
    report={'all_pass':True,'assets':9,'placements':2167,'modules':169,'duplicate_modules_reused':duplicate,'new_geometry_files':0,'existing_six_asset_rows_exact':True,'existing_145_module_rows_exact':True,'production_catalog_unchanged':ref(live),'source_plan':ref(pp),'module_catalog':ref(cp),'runtime_candidate':ref(out/'runtime_catalog_candidate.json'),'pending':['Actual runtime near/far/cap/collider identity','Actual original-coordinate render'],'whole_city_upgrade_complete':False}
    save(out/'merge_validation.json',report)
    print(json.dumps(report))
if __name__=='__main__':main()
