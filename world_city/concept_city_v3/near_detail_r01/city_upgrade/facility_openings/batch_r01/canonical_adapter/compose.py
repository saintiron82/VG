"""Fail-closed, JSON-driven native roof/opening common-master composition.

No voxel compile, primitive clipping, runtime change, or frozen-helper edits.
Only a uniquely instanced, whole paint-only roof component can be substituted.
"""
from __future__ import annotations
from collections import Counter
import argparse
import copy
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import resource
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
sys.path.insert(0, str(ROOT))
from voxel_character.common import core


class UnsupportedContract(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise UnsupportedContract(message)


def load(path):
    p = Path(path)
    with (gzip.open(p, 'rt') if p.suffix == '.gz' else p.open()) as f:
        return json.load(f)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode()
    if p.suffix == '.gz':
        with p.open('wb') as f:
            with gzip.GzipFile(filename='', fileobj=f, mode='wb', mtime=0) as z:
                z.write(data)
    else:
        p.write_bytes(data)


def relative(p):
    return str(Path(p).resolve().relative_to(ROOT))


def transforms(master):
    instances = core.indexed(master['instances'], 'instance')
    resolved, visiting = {}, set()
    def resolve(key):
        if key in resolved:
            return resolved[key]
        require(key not in visiting, 'Instance hierarchy cycle')
        visiting.add(key)
        instance = instances[key]
        t = core.transform(instance.get('transform'))
        if instance.get('parent'):
            t = core.compose(resolve(instance['parent']), t)
        visiting.remove(key)
        resolved[key] = t
        return t
    for key in instances:
        resolve(key)
    return resolved


def inverse_transform(t):
    basis = core.transpose(t['basis'])
    return {'basis': basis, 'translation': core.mv(basis, [-v for v in t['translation']])}


def affine_error(a, b):
    return max(abs(x-y) for x, y in zip(
        sum(a['basis'], []) + a['translation'], sum(b['basis'], []) + b['translation']))


def geometry_error(shape, a, b, pitch):
    lo, hi = core.shape_bounds(core.prepare_shape(shape, pitch))
    return max(abs(x-y) for point in itertools.product(*zip(lo, hi))
               for x, y in zip(core.apply(a, point), core.apply(b, point)))


def labels_for(component, instance):
    return [{'instance': instance, 'component': component['id'], 'part': op['part'],
             'material': op['material'], 'feature': op['id']}
            for op in component['operations'] if op['action'] == 'paint']


def compose_master(source, window, roof, policy):
    """Return common master and exact proof inventory without sampling voxels."""
    pitch = policy['fine_pitch_m']
    for m in (source, window, roof):
        core.validate_master(m, pitch)
    require(roof.get('metadata', {}).get('roof_only') is True, 'Selected master must be roof-only')
    require(roof.get('assembly_cuts', []) == [], 'Roof assembly cuts need an explicit scoped conversion contract')
    require(roof.get('constraints', []) == [], 'Roof-only constraints require an explicit selector mapping contract')
    for key in ('axes', 'grid_origin', 'materials'):
        require(source.get(key) == window.get(key) == roof.get(key), 'Source/window/roof mismatch: ' + key)
    require(source['instances'] == window['instances'], 'Window input must retain original ordered native instances')
    require(source.get('constraints', []) == window.get('constraints', []), 'Window input changed source constraints')
    sc = core.indexed(source['components'], 'component')
    wc = core.indexed(window['components'], 'component')
    rc = core.indexed(roof['components'], 'component')
    require(list(sc) == list(wc), 'Window input must retain original component identities/order')
    si = core.indexed(source['instances'], 'instance')
    st, rt = transforms(source), transforms(roof)
    use_counts = Counter(i['component'] for i in source['instances'])
    roof_uses = Counter(i['component'] for i in roof['instances'])
    require(set(roof_uses) == set(rc) and all(n == 1 for n in roof_uses.values()),
            'Every finished roof component must have exactly one instance')
    grouped, covered, bindings, run_order, max_error = {}, {}, [], [], 0.0
    source_hash = core.digest(source)
    for ri in roof['instances']:
        c = rc[ri['component']]
        metadata = c.get('metadata', {})
        provenance = metadata.get('provenance', {})
        identity = metadata.get('shared_row_source', {}).get('instance_metadata', {}).get('source_identity', {})
        cid, iid = provenance.get('source_component'), identity.get('instance')
        require(cid in sc and iid in si and si[iid]['component'] == cid and identity.get('component') == cid,
                'Missing or inconsistent source component/instance identity')
        require(use_counts[cid] == 1, 'Shared original roof components need a distinct-instance conversion contract')
        require(sc[cid] == wc[cid], 'Window input already modified a selected roof component')
        require(all(o['action'] == 'paint' for o in sc[cid]['operations']),
                'Original roof component cuts cannot be flattened')
        require(all(o['action'] == 'paint' and not o.get('selector') for o in c['operations']),
                'Finished roof component cuts/selectors cannot be flattened')
        require(all(p.get('metadata', {}).get('source_category') in policy['roof_part_categories']
                    for p in sc[cid]['parts']), 'Selected component contains a nonroof/unclassified part')
        require(affine_error(core.transform(identity.get('transform')), st[iid]) <= policy['transform_tolerance_m'],
                'Source identity does not match the resolved original instance transform')
        originals = core.indexed(sc[cid]['operations'], 'source operation')
        ids = provenance.get('source_operations')
        require(isinstance(ids, list) and ids and len(set(ids)) == len(ids) and set(ids) <= set(originals),
                'Finished component has missing/unknown source operation provenance')
        require(all(originals[k]['part'] == identity.get('part') and
                    originals[k]['material'] == identity.get('material') for k in ids),
                'Source operation part/material identity mismatch')
        require(all(o['part'] == identity.get('part') and o['material'] == identity.get('material')
                    for o in c['operations']), 'Finished geometry changes source part/material semantics')
        require(identity['material'] in policy['roof_materials'], 'Nonroof source operation material')
        if not run_order or run_order[-1] != iid:
            run_order.append(iid)
        grouped.setdefault(cid, [])
        covered.setdefault(cid, set()).update(ids)
        op_bindings = []
        for o in c['operations']:
            world = core.compose(rt[ri['id']], core.transform(o.get('transform')))
            local = core.compose(inverse_transform(st[iid]), world)
            recovered = core.compose(st[iid], local)
            error = max(affine_error(world, recovered), geometry_error(o['shape'], world, recovered, pitch))
            require(error <= policy['transform_tolerance_m'], 'Inverse transform changes world operation geometry')
            max_error = max(max_error, error)
            new = copy.deepcopy(o)
            new['id'] = ri['id'] + '__' + o['id']
            new['transform'] = local
            grouped[cid].append(new)
            op_bindings.append({'roof_operation': o['id'], 'canonical_operation': new['id'],
                                'shape_sha256': core.digest(o['shape']), 'source_roof_operation_sha256': core.digest(o),
                                'canonical_operation_sha256': core.digest(new), 'world_transform': world})
        bindings.append({'source_component': cid, 'source_instance': iid, 'source_operations': ids,
                         'roof_component': c['id'], 'roof_instance': ri['id'],
                         'operation_bindings': op_bindings})
    require(grouped, 'No roof operations found')
    expected_order = [i['id'] for i in source['instances'] if i['component'] in grouped]
    require(run_order == expected_order, 'Finished roof order interleaves/reorders source roof instances')
    for cid in grouped:
        require(covered[cid] == {o['id'] for o in sc[cid]['operations']},
                'Roof replacement must cover every original operation and no nonroof subset')
    selected_labels = [label for i in source['instances'] if i['component'] in grouped
                       for label in labels_for(sc[i['component']], i['id'])]
    # Instance/component/part/material labels survive. Feature IDs do not; an
    # active feature-scoped selector would require a separately verified remap.
    selectors = []
    for cut in window.get('assembly_cuts', []):
        selectors.append((cut['id'], cut.get('selector', {})))
    for constraint in window.get('constraints', []):
        for name in ('selector', 'a', 'b'):
            if name in constraint:
                selectors.append((constraint['id'], constraint[name]))
    for name, selector in selectors:
        nonfeature_scope = {k: v for k, v in selector.items() if k != 'feature'}
        require(not ('feature' in selector and any(core.selector_matches(nonfeature_scope, label) for label in selected_labels)),
                'Feature-scoped roof selector needs an explicit semantic remap: ' + name)
    combined = copy.deepcopy(window)
    for c in combined['components']:
        if c['id'] in grouped:
            c['operations'] = grouped[c['id']]
    combined['id'] = source['id'] + '__canonical_roof_openings_r01'
    combined.setdefault('provenance', {})['canonical_roof_openings'] = {
        'adapter_schema': 'riverstone.canonical_roof_openings.v1',
        'source_semantic_sha256': source_hash,
        'contract': 'Whole unique original roof components; paint-only; inverse proper-rigid transforms; stable source instance order.',
        'source_instance_part_component_labels_preserved': True,
        'source_constraints_preserved': True, 'feature_selector_remap': None,
        'full_compile': False, 'runtime_activation': False}
    core.validate_master(combined, pitch)
    proof = {'source_roof_components': list(grouped), 'source_roof_instances': expected_order,
             'source_roof_operation_count': sum(len(sc[k]['operations']) for k in grouped),
             'finished_roof_component_count': len(roof['components']),
             'finished_roof_operation_count': sum(len(x) for x in grouped.values()),
             'max_world_geometry_error_m': max_error, 'bindings': bindings,
             'native_instances_sha256': core.digest(window['instances']),
             'constraints_sha256': core.digest(window.get('constraints', [])),
             'scoped_assembly_cuts_sha256': core.digest(window.get('assembly_cuts', [])),
             'nonroof_components_sha256': core.digest([c for c in window['components'] if c['id'] not in grouped]),
             'parts_metadata_and_component_order_preserved': True,
             'source_and_finished_roof_paint_precedence_preserved': True,
             'constraint_semantics_preserved_global_constraints_not_evaluated': True}
    return combined, proof


def replacement_scope(source, render, proof, policy):
    """Bind removals to exact operations and exact group indices, never substrings."""
    selected = set(proof['source_roof_components'])
    sc = {c['id']: c for c in source['components']}
    st = transforms(source)
    operations = []
    for i in source['instances']:
        if i['component'] in selected:
            for o in sc[i['component']]['operations']:
                operations.append({'component': i['component'], 'instance': i['id'], 'operation': o['id'],
                                   'material': o['material'], 'part': o['part'],
                                   'original_operation': copy.deepcopy(o), 'operation_sha256': core.digest(o),
                                   'world_transform': core.compose(st[i['id']], core.transform(o.get('transform')))})
    materials = {o['material'] for o in operations}
    nonroof_materials = {o['material'] for c in source['components'] if c['id'] not in selected
                         for o in c['operations'] if o['action'] == 'paint'}
    require(not (materials & nonroof_materials), 'Roof cache material is shared with nonroof geometry; exact labeled extraction required')
    require(materials <= set(policy['roof_materials']), 'Unexpected roof semantic material')
    groups, inventory = [], []
    for n, g in enumerate(render['groups']):
        item = {'group_index': n, 'material': g['material'], 'quad_count': len(g['quads']),
                'original_group_sha256': core.digest(g)}
        inventory.append(item)
        if g['material'] in materials:
            groups.append({**item, 'original_group': copy.deepcopy(g)})
    require(groups, 'No exact roof source cache group was found')
    return {'schema': 'riverstone.canonical_roof_replacement_scope.v1',
            'source_roof_operations': operations, 'source_roof_materials': sorted(materials),
            'exclusive_source_material_ownership_verified': True,
            'exact_source_roof_groups': groups, 'ordered_source_group_inventory': inventory,
            'source_material_bindings': copy.deepcopy(source['materials']),
            'removal_rule': 'Only exact hash-bound source groups listed here, only for this asset, and only when the complete roof replacement is active. Never substring- or city-wide material removal.',
            'window_overlap_rule': 'Window ROIs own the canonical composed surface inside each exact AABB. Outside detailed roof faces must be clipped by those same AABBs. Coarse roof groups must not be reintroduced.',
            'runtime_ready': False}


def checked_load(path, digest):
    require(sha(path) == digest, 'Input byte hash mismatch: ' + str(path))
    return load(path)


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
        require(roof['metadata'].get('source_master_sha256') == w['source_sha256'], 'Roof metadata source hash differs')
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
        proof.update({'asset_key': key, **binding, 'canonical_master_sha256': sha(mp)})
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
          'adapter_sha256': sha(__file__), 'full_compile': False, 'runtime_activation': False})
    write(output / 'composition_report.json', {'status': 'structural_composition_pass', 'assets': reports,
          'full_compile': False, 'compile_calls': 0, 'runtime_activation': False,
          'pending': ['Bounded cell/contact verification', 'Mesh and seam closure', 'Visual review', 'Global constraint evaluation'],
          'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    require(sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()) <= config['max_output_bytes'], 'Output byte budget exceeded')
    print(json.dumps({'status': 'pass', 'assets': len(items), 'roof_operations': sum(r['finished_roof_operation_count'] for r in reports),
                      'output_bytes': sum(p.stat().st_size for p in output.iterdir()),
                      'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'compile_calls': 0}))
    return items


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=HERE / 'rules.v1.json')
    args = parser.parse_args()
    build(args.config)
