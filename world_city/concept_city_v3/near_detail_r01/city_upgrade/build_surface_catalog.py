"""Bind reviewed material semantics and common module hashes to the city candidate.

This builds a runtime placement catalog only. No original asset, collision or
source-city tile is modified and no unknown material receives a silent fallback.
"""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CITY=HERE.parents[1]
OUT=CITY/'playable_detail_r01'/'surface_catalog.json'

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    mapping_path=HERE/'surface_mapping/material_surface_map.v1.json'
    mapping=load(mapping_path)
    index_path=CITY/'playable_r01/generated/tile_r01/index.json'
    index=load(index_path)
    module_dir=HERE/'surface_modules/generated_safe'
    manifest=load(module_dir/'manifest.json')
    modules={};by_kind={}
    for record in manifest['modules']:
        rid=record['id'];path=module_dir/(rid+'.render.json');render=load(path)
        assert render['bounds']['min'][2]>=-.037501 and render['bounds']['max'][2]<=1e-6
        modules[rid]={'path':str(path.relative_to(ROOT)),'sha256':sha(path),'quads':render['quad_count'],'master_hash':render['master_hash'],'kind':record['kind'],'seed':record['seed']}
        by_kind.setdefault(record['kind'],[]).append(rid)
    edge_path=HERE/'surface_modules/edge_trims/edge_catalog.v1.json'
    edge=load(edge_path)
    by_kind_trim=edge['by_kind_trim']
    for r in edge['modules']:
        assert sha(ROOT/r['path'])==r['sha256']
        modules[r['id']]={k:r[k] for k in ['path','sha256','quads','master_hash','kind','seed','trim','master_to_render_translation_m']}
    assets={};skipped={}
    for key,record in mapping['assets'].items():
        if not record.get('used',False):continue
        slots={};pending={}
        for slot,rule in record['slots'].items():
            kind=rule.get('runtime_wall_class')
            state=rule.get('wall_candidate_status')
            if kind in ['ashlar','rubble','planks'] and state in ['SUPPORTED_CANDIDATE','CONDITIONAL_MIXED_ROLES']:
                slots[slot]=kind
            else:pending[slot]={'class':kind,'status':state}
        if slots:assets[key]={'source_render_sha256':index['common_assets'][key]['render_sha256'],'slots':slots,'excluded_slots':pending}
        else:skipped[key]=pending
    out={'schema':'riverstone.city.shared_surface_catalog.v1','source_city_index_sha256':sha(index_path),'mapping_path':str(mapping_path.relative_to(ROOT)),'mapping_sha256':sha(mapping_path),'modules':modules,'by_kind':by_kind,'by_kind_trim':by_kind_trim,'edge_catalog_sha256':sha(edge_path),'seed_contract':'v2 instance/kind/material/exact-plane-normal/global-1m-cell; quad-independent','assets':assets,'excluded_assets':skipped,'radius_m':10,'max_modules':180,'max_submitted_quads':85000,'update_seconds':.5,'module_front_offset_m':.0375,'max_collision_visual_difference_m':.0375,'face_contract':'vertical actual exterior quad; quarter-aligned edge trims preserve original whole-tile voxel subset, exact plane retained; unsupported trims fall back only to contained full tiles','coverage':'candidate native vertical relief including certified edge trims; road and roof layers independently tracked','whole_city_upgrade_complete':False}
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'assets':len(assets),'excluded':len(skipped),'modules':len(modules),'output':str(OUT),'bytes':OUT.stat().st_size}))

if __name__=='__main__':main()
