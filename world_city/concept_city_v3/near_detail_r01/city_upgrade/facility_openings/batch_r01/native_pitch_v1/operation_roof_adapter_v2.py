"""Exact per-component source-hash binding for legacy roof metadata.

A supplied top-level source hash must match; an absent optional top-level hash
requires all component provenance hashes and immutable compressed catalog hash.
"""
from pathlib import Path
import operation_roof_adapter_v1 as operation_adapter
from operation_roof_adapter_v1 import *
json=base.json;resource=base.resource;relative=base.relative

def build(config_path):
    config_path = Path(config_path)
    config = load(config_path)
    roofs = load(ROOT / config['roof_catalog'])
    windows = load(ROOT / config['window_catalog'])
    rmap = {x['asset_key']: x for x in roofs['assets']}
    wmap = {x['asset_key']: x for x in windows['assets']}
    output = HERE / 'generated'
    items, reports = [], []
    input_hashes = {config['roof_catalog']: sha(ROOT / config['roof_catalog']),
                    config['window_catalog']: sha(ROOT / config['window_catalog']),
                    relative(config_path): sha(config_path)}
    for key in config['assets']:
        r, w = rmap[key], wmap[key]
        require(r['source_master_path'] == w['source_master_path'] and r['source_sha256'] == w['source_sha256'],
                'Roof/window source binding differs')
        source = checked_load(ROOT / w['source_master_path'], w['source_sha256'])
        window = checked_load(ROOT / w['emitted_master_path'], w['emitted_master_sha256'])
        roof = checked_load(ROOT / r['emitted_master_path'], r['emitted_master_sha256'])
        require(roof['metadata'].get('source_master_sha256',w['source_sha256']) == w['source_sha256'], 'Supplied roof metadata source hash differs')
        require(all(c['metadata']['provenance'].get('source_master_sha256') == w['source_sha256']
                    for c in roof['components']), 'Roof component provenance source hash differs')
        contract = checked_load(ROOT / w['replacement_contract_path'], w['replacement_contract_sha256'])
        require(contract['source_sha256'] == w['source_sha256'] and contract['authored_master_sha256'] == w['emitted_master_sha256'],
                'Window replacement contract is not bound to selected inputs')
        render = checked_load(ROOT / contract['source_render_path'], contract['source_render_sha256'])
        require(contract['source_render_path'] == r['source_render_path'] and contract['source_render_sha256'] == r['source_render_sha256'],
                'Roof and window source render mismatch')
        combined, proof = compose_master(source, window, roof, config['policy'])
        scope = replacement_scope(source, render, proof, config['policy'])
        binding = {'source_master_path': w['source_master_path'], 'source_master_sha256': w['source_sha256'],
                   'window_master_path': w['emitted_master_path'], 'window_master_sha256': w['emitted_master_sha256'],
                   'roof_master_path': r['emitted_master_path'], 'roof_master_sha256': r['emitted_master_sha256']}
        combined['provenance']['canonical_roof_openings'].update(binding)
        mp = output / (key + '.canonical.master.json.gz')
        write(mp, combined)
        proof.update({'source_hash_binding_scope':{'top_level_hash_present':'source_master_sha256' in roof['metadata'],'every_component_hash_matches_original':True,'compressed_input_hash_matches_catalog':True},'asset_key': key, **binding, 'canonical_master_sha256': sha(mp)})
        pp = output / (key + '.composition_proof.json.gz')
        write(pp, proof)
        contract['authored_master_path'], contract['authored_master_sha256'] = relative(mp), sha(mp)
        contract['roof_replacement_scope'] = scope
        contract['roof_composition'] = {**binding, 'canonical_master_path': relative(mp),
            'canonical_master_sha256': sha(mp), 'composition_proof_path': relative(pp), 'composition_proof_sha256': sha(pp),
            'outside_detailed_roof_exclusion_aabbs': [{'patch_id': p['id'], **p['replacement_volume_master_m']} for p in contract['patches']],
            'native_instances_and_constraints_preserved': True, 'extra_roof_frame_transform': False,
            'roof_operations_inverse_transformed_to_original_component_frame': True,
            'full_compile': False, 'runtime_activation': False}
        cp = output / (key + '.replacement.json.gz')
        write(cp, contract)
        items.append({**w, 'emitted_master_path': relative(mp), 'emitted_master_sha256': sha(mp),
                      'replacement_contract_path': relative(cp), 'replacement_contract_sha256': sha(cp),
                      'composition_proof_path': relative(pp), 'composition_proof_sha256': sha(pp),
                      'roof_master_path': r['emitted_master_path'], 'roof_master_sha256': r['emitted_master_sha256'],
                      'canonical_common_master': True, 'runtime_ready': False})
        reports.append({k: v for k, v in proof.items() if k != 'bindings'})
    write(output / 'catalog.json', {'schema': 'riverstone.canonical_roof_openings.catalog.v1',
          'assets': items, 'input_catalog_and_config_hashes': input_hashes,
          'adapter_sha256': sha(__file__),'operation_adapter_sha256':sha(operation_adapter.__file__),'frozen_packaging_helper_sha256':sha(base.__file__), 'full_compile': False, 'runtime_activation': False})
    write(output / 'composition_report.json', {'status': 'structural_composition_pass', 'assets': reports,
          'full_compile': False, 'compile_calls': 0, 'runtime_activation': False,
          'pending': ['Bounded cell/contact verification', 'Mesh and seam closure', 'Visual review', 'Global constraint evaluation'],
          'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    require(sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()) <= config['max_output_bytes'], 'Output byte budget exceeded')
    print(json.dumps({'status': 'pass', 'assets': len(items), 'roof_operations': sum(r['finished_roof_operation_count'] for r in reports),
                      'output_bytes': sum(p.stat().st_size for p in output.iterdir()),
                      'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'compile_calls': 0}))
    return items

