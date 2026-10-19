"""Small runtime projection; full ownership evidence stays separately hash-bound."""
from pathlib import Path
import copy,hashlib,json
H=Path(__file__).resolve().parent; R=H.parents[4]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text())
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n')
def main():
    pairs=[(H/'expansion_r04/combined_ground/source_plan.json',H/'expansion_r04/combined_ground/module_catalog.json')]
    for n in ['first_e7_e1','remaining_e2_e3_e4_e5_e6']:
        p=H/'expansion_r05'/n/'compact_candidate';pairs.append((p/'source_plan.json',p/'modules.json'))
    assets=[];modules={};proofs={};inputs=[]
    keys=['asset_key','source_master_path','source_master_sha256','source_render_path','source_render_sha256','existing_collision_unchanged','rule']
    placement_keys=['bounds_uv_m','collision_changed','module_key','source_face_ref','source_face_sha256','source_plane_y_m','transform']
    for pp,cp in pairs:
        p=read(pp);c=read(cp);assert c['source_plan_sha256']==sha(pp)
        inputs += [ref(pp),ref(cp)]
        for a in p['assets']:
            assert a['asset_key'] not in {x['asset_key']for x in assets}
            b={k:copy.deepcopy(a[k])for k in keys if k in a}
            b['placements']=[{k:copy.deepcopy(row[k])for k in placement_keys if k in row}for row in a['placements']]
            for old,new in zip(a['placements'],b['placements']):
                assert all(old[k]==new[k] for k in ['collision_changed','module_key','transform'])
            proof=copy.deepcopy(a.get('full_source_proof',dict(ref(pp),asset_key=a['asset_key'])))
            assert proof['asset_key']==a['asset_key'] and sha(R/proof['path'])==proof['sha256']
            b['full_source_proof']=proof;proofs[proof['path']]=proof['sha256'];assets.append(b)
        for m in c['modules']:
            if m['id']in modules:assert modules[m['id']]==m
            else:modules[m['id']]=copy.deepcopy(m)
            for k in ['master','render']:assert sha(R/m[k+'_path'])==m[k+'_sha256']
    assert len(assets)==16 and sum(len(a['placements'])for a in assets)==4583
    assert all(p['module_key']in modules for a in assets for p in a['placements'])
    cfg_path=R/'world_city/concept_city_v3/playable_detail_r01/native_access_catalog.json';cfg=read(cfg_path)
    assert cfg['source_plan_sha256']==sha(pairs[0][0])
    out=H/'runtime_projection_r01';pp=out/'source_plan.json';cp=out/'modules.json'
    d={'schema':'riverstone.native_access_detail.plan.v1','revision':'runtime_projection_r01_16types','source_city_index_sha256':cfg['source_city_index_sha256'],'runtime_projection':True,'projection_contract':'Consumed fields and placement order copied exactly. Original source ownership/cut evidence remains hash-bound in full_source_proof. No new geometry.','assets':assets,'maximum_additional_visual_offset_from_source_m':.0375,'whole_city_upgrade_complete':False,'provenance':{'inputs':inputs,'projector':ref(Path(__file__))}}
    save(pp,d)
    save(cp,{'schema':'riverstone.native_access_detail.module_catalog.v1','source_plan_sha256':sha(pp),'original_collision_unchanged':True,'modules':list(modules.values()),'source_dependencies':{x['path']:x['sha256']for x in inputs},'runtime_activation':False})
    before=out/'previous_runtime_catalog.json';assert not before.exists();save(before,cfg)
    cfg.update(source_plan_path=str(pp.relative_to(R)),source_plan_sha256=sha(pp),module_catalog_path=str(cp.relative_to(R)),module_catalog_sha256=sha(cp),binding_revision='r05_compact_sixteen_native_access_types')
    assert cfg['maximum_active_modules']==120 and cfg['maximum_mesh_bytes']==24000000
    save(out/'runtime_catalog_candidate.json',cfg)
    report={'all_pass':True,'assets':16,'placements':4583,'modules':len(modules),'new_geometry_files':0,'runtime_projection_bytes':pp.stat().st_size,'full_proofs_preserved':proofs,'input_runtime_fields_exact':True,'same_collision':True,'pending':'Runtime hash-bound source proof, cap, near/far/owner unload and actual-scene review','plan':ref(pp),'modules_catalog':ref(cp)}
    save(out/'projection_validation.json',report);print(json.dumps(report))
if __name__=='__main__':main()
