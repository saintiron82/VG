"""Small algebraic/analytic regression suite. compile_master is disabled."""
from __future__ import annotations
import copy
import math
from pathlib import Path
import resource
import tempfile
import compose as c


def fail_compile(*args, **kwargs):
    raise AssertionError('Full or bounded voxel compilation is forbidden in this suite')


def rejected(fn):
    try:
        fn()
    except (c.UnsupportedContract, c.core.InvalidMaster):
        return True
    raise AssertionError('Unsupported input was accepted')


def synthetic(policy):
    angle = .37
    rotation = {'basis': [[math.cos(angle), 0, math.sin(angle)], [0, 1, 0],
                          [-math.sin(angle), 0, math.cos(angle)]], 'translation': [4.25, 3.0, -7.75]}
    box = {'kind': 'box', 'min': [0, 0, 0], 'max': [1, 1, 1]}
    op = {'id': 'plane', 'part': 'solid', 'action': 'paint', 'shape': box, 'material': 'slate'}
    src = {'schema': c.core.SCHEMA, 'id': 'rotated_parent_fixture', 'revision': 1,
           'axes': {'up': '+Y', 'front': '+Z', 'right': '+X'}, 'grid_origin': [0, 0, 0],
           'materials': {'slate': '45676a'},
           'components': [
               {'id': 'parent', 'parts': [{'id': 'solid', 'pivot': [0, 0, 0]}], 'operations': []},
               {'id': 'roof', 'parts': [{'id': 'solid', 'pivot': [0, 0, 0],
                  'metadata': {'source_category': 'uniform_material_pitched_roof'}}], 'operations': [op]}],
           'instances': [{'id': 'parent', 'component': 'parent', 'transform': rotation},
                         {'id': 'roof', 'component': 'roof', 'parent': 'parent',
                          'transform': {'translation': [2.0, .5, 1.0]}}],
           'constraints': [{'id': 'roof', 'kind': 'nonempty', 'selector': {'instance': 'roof'}}],
           'assembly_cuts': []}
    t = c.transforms(src)['roof']
    finished = {'schema': c.core.SCHEMA, 'id': 'finished', 'revision': 1,
                'axes': src['axes'], 'grid_origin': [0, 0, 0], 'materials': src['materials'],
                'metadata': {'roof_only': True}, 'constraints': [], 'assembly_cuts': [],
                'components': [{'id': 'detail', 'parts': [{'id': 'solid', 'pivot': [0, 0, 0]}],
                    'operations': [copy.deepcopy(op)], 'metadata': {
                        'provenance': {'source_component': 'roof', 'source_operations': ['plane']},
                        'shared_row_source': {'instance_metadata': {'source_identity': {
                            'component': 'roof', 'instance': 'roof', 'part': 'solid',
                            'material': 'slate', 'transform': t}}}}}],
                'instances': [{'id': 'detail', 'component': 'detail', 'transform': t}]}
    combined, proof = c.compose_master(src, copy.deepcopy(src), finished, policy)
    assert combined['instances'] == src['instances']
    assert combined['components'][1]['operations'][0]['shape'] == box
    assert proof['max_world_geometry_error_m'] < policy['transform_tolerance_m']
    assert c.affine_error(c.core.transform(combined['components'][1]['operations'][0]['transform']),
                          c.core.transform(None)) < policy['transform_tolerance_m']
    return src, finished, proof


def run():
    c.core.compile_master = fail_compile
    config = c.load(c.HERE / 'rules.v1.json')
    policy = config['policy']
    catalog = c.load(c.HERE / 'generated/catalog.json')
    windows = {a['asset_key']: a for a in c.load(c.ROOT / config['window_catalog'])['assets']}
    assets = []
    for item in catalog['assets']:
        w = windows[item['asset_key']]
        source = c.checked_load(c.ROOT / item['source_master_path'], item['source_sha256'])
        window = c.checked_load(c.ROOT / w['emitted_master_path'], w['emitted_master_sha256'])
        roof = c.checked_load(c.ROOT / item['roof_master_path'], item['roof_master_sha256'])
        actual = c.checked_load(c.ROOT / item['emitted_master_path'], item['emitted_master_sha256'])
        proof = c.checked_load(c.ROOT / item['composition_proof_path'], item['composition_proof_sha256'])
        contract = c.checked_load(c.ROOT / item['replacement_contract_path'], item['replacement_contract_sha256'])
        old_contract = c.checked_load(c.ROOT / w['replacement_contract_path'], w['replacement_contract_sha256'])
        render = c.checked_load(c.ROOT / contract['source_render_path'], contract['source_render_sha256'])
        expected, independently_rebuilt_proof = c.compose_master(source, window, roof, policy)
        for key in ('components', 'instances', 'constraints', 'assembly_cuts', 'materials', 'axes', 'grid_origin'):
            assert actual.get(key) == expected.get(key), key
        for key, value in independently_rebuilt_proof.items():
            assert proof[key] == value, key
        selected = set(proof['source_roof_components'])
        assert [x for x in actual['components'] if x['id'] not in selected] == [x for x in window['components'] if x['id'] not in selected]
        assert actual['instances'] == source['instances']
        assert actual['constraints'] == source['constraints']
        assert actual['assembly_cuts'] == window['assembly_cuts']
        for before, after in zip(window['components'], actual['components']):
            if before['id'] in selected:
                assert {k: v for k, v in before.items() if k != 'operations'} == {k: v for k, v in after.items() if k != 'operations'}
        assert contract['cache_quad_edits'] == old_contract['cache_quad_edits']
        assert contract['patches'] == old_contract['patches']
        assert contract['roof_replacement_scope'] == c.replacement_scope(source, render, proof, policy)
        ccs = {x['id']: x for x in actual['components']}
        rcs = {x['id']: x for x in roof['components']}
        cts, rts = c.transforms(actual), c.transforms(roof)
        verified = 0
        for binding in proof['bindings']:
            new_ops = {o['id']: o for o in ccs[binding['source_component']]['operations']}
            old_ops = {o['id']: o for o in rcs[binding['roof_component']]['operations']}
            for op in binding['operation_bindings']:
                new, old = new_ops[op['canonical_operation']], old_ops[op['roof_operation']]
                assert new['shape'] == old['shape'] and new['part'] == old['part'] and new['material'] == old['material']
                assert c.core.digest(new) == op['canonical_operation_sha256']
                assert c.core.digest(old) == op['source_roof_operation_sha256']
                nt = c.core.compose(cts[binding['source_instance']], c.core.transform(new['transform']))
                ot = c.core.compose(rts[binding['roof_instance']], c.core.transform(old.get('transform')))
                assert c.geometry_error(old['shape'], nt, ot, policy['fine_pitch_m']) <= policy['transform_tolerance_m']
                verified += 1
        assert verified == proof['finished_roof_operation_count']
        assets.append({'asset_key': item['asset_key'], 'world_geometry_operations_verified': verified,
                       'constraints_preserved': len(source['constraints']),
                       'scoped_cuts_preserved': len(window['assembly_cuts']),
                       'exact_source_groups': len(contract['roof_replacement_scope']['exact_source_roof_groups']),
                       'max_world_geometry_error_m': proof['max_world_geometry_error_m'],
                       'nonroof_components_and_source_parts_exact': True,
                       'window_cache_edits_and_patch_scope_exact': True})
    source, roof, rotated_proof = synthetic(policy)
    cases = []
    def negative(name, mutate):
        s, w, r = copy.deepcopy(source), copy.deepcopy(source), copy.deepcopy(roof)
        mutate(s, w, r)
        rejected(lambda: c.compose_master(s, w, r, policy))
        cases.append(name)
    box = {'kind': 'box', 'min': [0, 0, 0], 'max': [1, 1, 1]}
    negative('roof_assembly_cut', lambda s, w, r: r['assembly_cuts'].append({'id': 'cut', 'shape': box}))
    negative('roof_component_cut', lambda s, w, r: r['components'][0]['operations'][0].update(action='cut'))
    negative('source_component_cut', lambda s, w, r: [m['components'][1]['operations'][0].update(action='cut') for m in (s, w)])
    negative('shared_source_component', lambda s, w, r: [m['instances'].append({'id': 'other_roof', 'component': 'roof'}) for m in (s, w)])
    negative('unknown_source_operation', lambda s, w, r: r['components'][0]['metadata']['provenance'].update(source_operations=['unmapped']))
    negative('missing_source_operation', lambda s, w, r: [m['components'][1]['operations'].append({**copy.deepcopy(m['components'][1]['operations'][0]), 'id': 'missing'}) for m in (s, w)])
    negative('nonroof_source_part', lambda s, w, r: [m['components'][1]['parts'][0]['metadata'].update(source_category='wall') for m in (s, w)])
    negative('altered_source_instance', lambda s, w, r: w['instances'][1]['transform'].update(translation=[100, 0, 0]))
    negative('dropped_source_constraints', lambda s, w, r: w.update(constraints=[]))
    negative('preedited_source_roof', lambda s, w, r: w['components'][1]['operations'][0]['shape']['max'].__setitem__(0, 2))
    negative('wrong_source_identity_transform', lambda s, w, r: r['components'][0]['metadata']['shared_row_source']['instance_metadata']['source_identity'].update(transform={}))
    negative('missing_source_identity', lambda s, w, r: r['components'][0]['metadata'].pop('shared_row_source'))
    negative('wrong_source_identity_material', lambda s, w, r: r['components'][0]['metadata']['shared_row_source']['instance_metadata']['source_identity'].update(material='glass'))
    negative('not_roof_only', lambda s, w, r: r['metadata'].update(roof_only=False))
    negative('feature_scoped_roof_cut', lambda s, w, r: w['assembly_cuts'].append({'id': 'target_old_feature', 'shape': box, 'selector': {'instance': 'roof', 'feature': 'plane'}}))
    negative('feature_scoped_roof_constraint', lambda s, w, r: [m['constraints'].append({'id': 'old_feature', 'kind': 'nonempty', 'selector': {'feature': 'plane'}}) for m in (s, w)])
    negative('roof_material_map_changed', lambda s, w, r: r.update(materials={**r['materials'], 'new': 'ffffff'}))
    negative('unmapped_finished_component', lambda s, w, r: r['components'].append({'id': 'unused', 'parts': [], 'operations': []}))
    negative('unsupported_roof_constraint', lambda s, w, r: r['constraints'].append({'id': 'unmapped', 'kind': 'nonempty', 'selector': {}}))
    # Material-only roof suppression is forbidden if any nonroof paint uses it.
    mixed = copy.deepcopy(source)
    mixed['components'][0]['operations'] = [copy.deepcopy(source['components'][1]['operations'][0])]
    rejected(lambda: c.replacement_scope(mixed, {'groups': [{'material': 'slate', 'quads': []}]}, rotated_proof, policy))
    cases.append('mixed_nonroof_material_scope')
    with tempfile.TemporaryDirectory() as temp:
        p = Path(temp) / 'hash.json'
        c.write(p, {'value': 1})
        pinned = c.sha(p)
        c.write(p, {'value': 2})
        rejected(lambda: c.checked_load(p, pinned))
        cases.append('modified_input_bytes')
    result = {'schema': 'riverstone.canonical_roof_openings.structural_qa.v1', 'status': 'pass',
              'assets': assets, 'unsupported_contract_rejections': cases,
              'nested_rotated_parent_transform_fixture': 'pass',
              'nested_fixture_max_error_m': rotated_proof['max_world_geometry_error_m'],
              'compile_calls': 0, 'source_edits': 0, 'runtime_edits': 0,
              'limits': 'Analytic affine equivalence, hash binding, source label/scope/order conservation. Fine occupancy, contact closure and global constraints are not evaluated.',
              'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    c.write(c.HERE / 'generated/structural_qa.json', result)
    print(c.json.dumps({'status': 'pass', 'operations_verified': sum(x['world_geometry_operations_verified'] for x in assets),
                        'negative_cases': len(cases), 'compile_calls': 0, 'max_rss_kib': result['max_rss_kib']}))


if __name__ == '__main__':
    run()
