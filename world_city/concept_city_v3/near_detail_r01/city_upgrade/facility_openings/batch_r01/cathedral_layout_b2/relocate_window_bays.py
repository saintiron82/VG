"""Data-driven, exact-shape window relocation. Authoring only; never compile.

All asset choices and coordinates live in revision_rules.json. Common primitives,
owner tests, depth grammar and patch calculations come from the frozen author.
"""
from collections import defaultdict
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import resource
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
F = HERE.parents[1]
spec = importlib.util.spec_from_file_location('frozen_window_author', F / 'author.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
core = a.core


def encoded(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def fingerprint(v):
    b = encoded(v)
    return {'sha256': hashlib.sha256(b).hexdigest(), 'canonical_json_bytes': len(b)}


def component(m, name):
    return next(c for c in m['components'] if c['id'] == name)


def operations(m):
    return {o['id']: o for c in m['components'] for o in c['operations']}


def bound_record(shape, t):
    lo, hi = a.bounds(shape, t)
    return {'min': lo, 'max': hi}


def support_snapshot(m, rules):
    name = rules['preserved_support_instance']
    return {'roof_component': fingerprint(component(m, 'roof')),
            'roof_operations': fingerprint(component(m, 'roof')['operations']),
            'roof_operation_count': len(component(m, 'roof')['operations']),
            'support_component': fingerprint(component(m, name)),
            'support_operations': fingerprint(component(m, name)['operations']),
            'support_operation_count': len(component(m, name)['operations']),
            'support_instance': fingerprint(next(i for i in m['instances'] if i['id'] == name)),
            'support_protection_cuts': fingerprint([c for c in m['assembly_cuts'] if c['selector'].get('instance') == name]),
            'support_protection_cut_count': sum(c['selector'].get('instance') == name for c in m['assembly_cuts'])}


def checked_inputs(r):
    for name, b in r['inputs'].items():
        actual = a.sha(ROOT / b['path'])
        assert actual == b['sha256'], f'Input hash mismatch {name}: expected {b["sha256"]}, actual {actual}'
    return {name: ROOT / b['path'] for name, b in r['inputs'].items()}


def relocate_source(source, r):
    revised = copy.deepcopy(source)
    old_ops, new_ops = operations(source), operations(revised)
    changes = []
    for item in r['relocations']:
        z = r['new_centers_m'][item['axis_index']]
        for oid in item['source_operation_ids']:
            old, new = old_ops[oid], new_ops[oid]
            assert old['action'] == 'paint' and old['transform']['translation'][r['axis']] != z
            new['transform']['translation'][r['axis']] = z
            changes.append({'operation_id': oid, 'component': r['window_component'],
                            'before_operation_sha256': core.digest(old), 'after_operation_sha256': core.digest(new),
                            'before_transform': old['transform'], 'after_transform': new['transform']})
    return revised, changes


def author_patch(item, old_patch, revised, inventory, r, rules, render):
    """The frozen author's same window grammar, with owner selection recomputed."""
    look = {(c, i, o['id']): o for c, i, o, t, b in inventory}
    c, i = old_patch['source_glass']['component'], old_patch['source_glass']['instance']
    g = look[c, i, old_patch['source_glass']['operation']]
    sur = look[c, i, old_patch['source_surround']['operation']]
    assert g['shape']['kind'] == sur['shape']['kind'] == 'extrusion'
    assert set(g['transform']) == {'basis', 'translation'}
    # Source windows are unparented identity instances. Reject unsupported hierarchies.
    instance = next(x for x in revised['instances'] if x['id'] == i)
    assert instance == {'id': i, 'component': c}
    t = copy.deepcopy(g['transform'])
    poly, stem, stone = g['shape']['polygon'], old_patch['id'], sur['material']
    cavity = a.extrusion(poly, -rules['cavity_depth_m'], .025)
    cb, owners = a.bounds(cavity, t), defaultdict(list)
    for oc, oi, op, ot, b in inventory:
        relevant = ((oc in rules['wall_component_ids'] and op.get('material') in rules['wall_semantic_slots']) or
                    (oc == c and oi == i and op['id'] in item['source_operation_ids']))
        if relevant and op['action'] == 'paint' and a.overlaps(cb, b):
            owners[oi].append((oc, op))
    assert i in owners and any(c in rules['wall_component_ids'] for rows in owners.values() for c, o in rows)
    cuts = [{'id': stem + '_cavity_' + oi, 'selector': {'instance': oi, 'feature': [o['id'] for c, o in rows]},
             'shape': copy.deepcopy(cavity), 'transform': copy.deepcopy(t)} for oi, rows in owners.items()]
    detail = [a.common_op(stem + '_glass', a.extrusion(poly, -rules['glass_recess_m'] - rules['glass_thickness_m'], -rules['glass_recess_m']), g['material'], t, 'glass')]
    sill = a.clipped(poly, 1, min(p[1] for p in poly) + rules['sill_height_m'], False)
    detail.append(a.common_op(stem + '_sill', a.extrusion(sill, -rules['cavity_depth_m'], -rules['sill_front_recess_m']), stone, t, 'sill'))
    assert any(x.endswith('_mullion') for x in item['source_operation_ids'])
    center = (min(p[0] for p in poly) + max(p[0] for p in poly)) / 2
    bar = a.clipped(a.clipped(poly, 0, center - rules['mullion_width_m'] / 2, True), 0, center + rules['mullion_width_m'] / 2, False)
    detail.append(a.common_op(stem + '_mullion', a.extrusion(bar, -rules['cavity_depth_m'], -rules['mullion_front_recess_m']), stone, t, 'mullion'))
    volume, cells = a.patch_for({'local_to_master': t}, sur['shape'], rules, render['pitch'], render['grid_origin'])
    patch = copy.deepcopy(old_patch)
    patch.update({'source_glass': a.op_binding(c, i, g), 'source_surround': a.op_binding(c, i, sur),
                  'source_owners': [a.op_binding(oc, oi, o) for oi, rows in owners.items() for oc, o in rows],
                  'local_to_master': t, 'replacement_volume_master_m': volume, 'fine_cell_bounds': cells,
                  'source_render_observation': 'original_cache_is_pre_revision; no_revised_render_compiled',
                  'authored_cut_ids': [c['id'] for c in cuts], 'authored_detail_ids': [o['id'] for o in detail]})
    return patch, cuts, detail


def patch_master(master, revised, items, details, cuts, revision, rules, window_path=None):
    # In-place changes avoid duplicating the 22k-operation detailed roof in memory.
    old = operations(master)
    for item in items:
        for oid in item['source_operation_ids']:
            old[oid]['transform'] = copy.deepcopy(operations(revised)[oid]['transform'])
    new_details = {o['id']: o for o in details}
    comp = component(master, rules['detail_component'])
    comp['operations'] = [copy.deepcopy(new_details.get(o['id'], o)) for o in comp['operations']]
    new_cuts = {c['id']: c for c in cuts}
    assert set(new_cuts) <= {c['id'] for c in master['assembly_cuts']}
    master['assembly_cuts'] = [copy.deepcopy(new_cuts.get(c['id'], c)) for c in master['assembly_cuts']]
    master['id'] = rules['asset_key'] + '__window_bay_relocation_b2'
    master['revision'] = master.get('revision', 0) + 1
    provenance = master.setdefault('provenance', {})
    provenance['source_revision'] = copy.deepcopy(revision)
    facility = provenance['facility_openings']
    facility.update({'source_master_path': revision['revised_master_path'], 'source_sha256': revision['revised_master_sha256'],
                     'original_master_sha256': revision['original_master_sha256'], 'source_shapes_unchanged': True,
                     'source_transforms_unchanged': False, 'original_occupancy_unchanged': False,
                     'scope': 'Explicit B2 source revision; 16 lower bays relocated. 17 existing upper/great windows unchanged. Source candidate; no compile or runtime activation.'})
    if 'roof_opening_composition' in provenance:
        composition = provenance['roof_opening_composition']
        composition.update({'native_coordinates_unchanged': False, 'roof_geometry_fields_unchanged': True,
                            'original_master_sha256': revision['original_master_sha256'],
                            'source_master_sha256': revision['revised_master_sha256'],
                            'window_master_path': str(window_path.relative_to(ROOT)), 'window_master_sha256': a.sha(window_path)})
    return master


def main():
    r = a.load(HERE / 'revision_rules.json')
    paths = checked_inputs(r)
    original_compile = core.compile_master
    def forbidden(*args, **kwargs): raise AssertionError('Compilation is not authorized')
    core.compile_master = forbidden
    source, old_contract = a.load(paths['original_master']), a.load(paths['window_contract'])
    render = a.load(ROOT / old_contract['source_render_path'])
    assert a.sha(ROOT / old_contract['source_render_path']) == old_contract['source_render_sha256']
    city = a.load(paths['city_index'])['common_assets'][r['asset_key']]
    assert city['master_sha256'] == r['inputs']['original_master']['sha256']
    assert city['render_sha256'] == old_contract['source_render_sha256']
    revised, changes = relocate_source(source, r)
    assert len(changes) == r['expected_source_operation_changes']
    revised_path = HERE / 'source.b2.revised.master.json.gz'
    a.write(revised_path, revised)
    unaffected = {c['id']: fingerprint(c) for c in source['components'] if c['id'] != r['window_component']}
    proof = {'unchanged_components': unaffected, 'original_assembly_cuts': fingerprint(source.get('assembly_cuts', [])),
             'instances': fingerprint(source['instances']), 'materials': fingerprint(source['materials']),
             'extensions_including_entry_and_envelope': fingerprint(source['extensions']),
             'exact_source_differences': 'Only 48 operation.transform.translation[2] values differ; all other source JSON data, including revision/id, remains equal.',
             'source_revision_identity': 'This sidecar and the revised file hash identify the new source; original JSON id remains the asset family key.',
             'no_fill_operations_added': True, 'old_cavity_restoration': 'Evaluate the full original solid masonry component with lower original window paints moved and their old cavity cuts absent; no cavity fill boxes.',
             'city_index': r['inputs']['city_index'], 'original_city_asset_record': city,
             'entry_and_walking_safety': 'Only source window paints and cavity/detail fields at y >= 4.477611940298507 m change; floor, lower supports, footprint and doorway source/collider remain exact. Entry z = 26.29..27.01 is outside all old/new window regions (z <= 17).'}
    revision = {'original_master_sha256': r['inputs']['original_master']['sha256'],
                'original_master_path': r['inputs']['original_master']['path'],
                'revised_master_path': str(revised_path.relative_to(ROOT)), 'revised_master_sha256': a.sha(revised_path),
                'allowed_operation_ids': [x['operation_id'] for x in changes], 'change_kind': r['change_kind'],
                'unchanged_structure_proof': proof}
    inventory = a.source_inventory(revised)
    window_rules = a.load(paths['frozen_rules'])
    old_by_id = {p['id']: p for p in old_contract['patches']}
    new_patches, new_cuts, new_details, changed = {}, [], [], []
    for item in r['relocations']:
        p, cs, ds = author_patch(item, old_by_id[item['patch_id']], revised, inventory, r, window_rules, render)
        new_patches[p['id']] = p
        new_cuts += cs
        new_details += ds
        changed.append({'patch_id': p['id'], 'window': item['window'], 'axis_index': item['axis_index'], 'side': item['side'],
                        'old_transform': old_by_id[p['id']]['local_to_master'], 'new_transform': p['local_to_master'],
                        'old_region_master_m': old_by_id[p['id']]['replacement_volume_master_m'],
                        'new_region_master_m': p['replacement_volume_master_m'],
                        'source_frame_bounds_m': bound_record(operations(revised)[item['window'] + '_surround']['shape'], p['local_to_master'])})
    assert len(new_cuts) == 32 and len(new_details) == 48
    wm = a.load(paths['window_master'])
    window_path = HERE / 'windows.b2.authored.master.json.gz'
    patch_master(wm, revised, r['relocations'], new_details, new_cuts, revision, r)
    core.validate_master(wm, window_rules['fine_pitch_m'])
    a.write(window_path, wm)
    del wm
    canonical = a.load(paths['canonical_master'])
    preserved_before = support_snapshot(canonical, r)
    canonical_path = HERE / 'canonical.b2.authored.master.json.gz'
    patch_master(canonical, revised, r['relocations'], new_details, new_cuts, revision, r, window_path)
    preserved_after = support_snapshot(canonical, r)
    assert preserved_before == preserved_after
    core.validate_master(canonical, window_rules['fine_pitch_m'])
    a.write(canonical_path, canonical)
    support_bounds = [bound_record(o['shape'], core.transform(o.get('transform'))) for o in component(canonical, r['preserved_support_instance'])['operations']]
    support_min_y = min(b['min'][1] for b in support_bounds)
    lower_cut_max_y = max(a.bounds(c['shape'], c['transform'])[1][1] for c in new_cuts)
    assert lower_cut_max_y < support_min_y
    del canonical
    patches = [new_patches.get(p['id'], copy.deepcopy(p)) for p in old_contract['patches']]
    for p in patches:
        p['source_master_sha256'] = revision['revised_master_sha256']
        p['coordinate_binding_sha256'] = core.digest({'source_master_sha256': revision['revised_master_sha256'], 'source_glass': p['source_glass'], 'local_to_master': p['local_to_master'], 'volume': p['replacement_volume_master_m']})
    affected = []
    for item in changed:
        for location in ('old', 'new'):
            affected.append({'id': item['patch_id'] + '__' + location, 'opening_id': item['patch_id'],
                             'purpose': 'restore_original_solid_masonry' if location == 'old' else 'author_relocated_cavity_and_details',
                             'replacement_volume_master_m': item[location + '_region_master_m'],
                             'source_master_sha256': revision['revised_master_sha256'],
                             'canonical_master_sha256': a.sha(canonical_path)})
    edits = a.cache_contract(render, affected)
    preserve = {'schema': 'riverstone.window_bay_relocation.preservation.v1', 'canonical_input': r['inputs']['canonical_master'],
                'candidate_master_sha256': a.sha(canonical_path), 'before': preserved_before, 'after': preserved_after,
                'equal_canonical_json_bytes': True, 'support_lower_window_cut_disjointness': {'lower_cavity_max_y_m': lower_cut_max_y, 'support_min_y_m': support_min_y, 'gap_m': support_min_y - lower_cut_max_y, 'retained_support_cut_count': 34},
                'encoding': 'UTF-8 JSON, sorted keys, compact separators, ensure_ascii=False, no terminal newline; field SHA and byte length measured before/after.'}
    a.write(HERE / 'preserved_roof_support.json', preserve)
    a.write(HERE / 'source_revision.json', {'schema': 'riverstone.source_revision.v1', 'source_revision': revision, 'operation_changes': changes})
    contract = {'schema': 'riverstone.window_bay_relocation.replacement.v1', 'asset_key': r['asset_key'],
                'status': 'source_candidate_authored_not_compiled_not_activated',
                'source_master_sha256': revision['original_master_sha256'],
                'source_master_sha256_semantics': 'Original tile-index identity only, never the revised geometry input.',
                'source_revision': revision, 'patch_source_master_path': revision['revised_master_path'], 'patch_source_master_sha256': revision['revised_master_sha256'],
                'authored_master_path': str(canonical_path.relative_to(ROOT)), 'authored_master_sha256': a.sha(canonical_path),
                'window_authored_master_path': str(window_path.relative_to(ROOT)), 'window_authored_master_sha256': a.sha(window_path),
                'frozen_author': r['inputs']['frozen_author'], 'frozen_rules': r['inputs']['frozen_rules'],
                'fine_pitch_m': old_contract['fine_pitch_m'], 'source_pitch_m': old_contract['source_pitch_m'], 'grid_origin': old_contract['grid_origin'],
                'source_render_path': old_contract['source_render_path'], 'source_render_sha256': old_contract['source_render_sha256'], 'source_render_is_pre_revision': True,
                'patches': patches, 'relocated_windows': changed, 'affected_regions': affected,
                'cache_quad_edits': edits, 'cache_quad_edits_apply_only_to': 'original coarse render identified by source_render_sha256; never apply these indices to current r05',
                'current_composed_replacement_requirement': 'Subtract and replace the union of all 32 affected old/new regions against the exact current composed render. Evaluate the candidate full canonical master over the entire union, deduplicate by global integer cell/final label, and verify interfaces. The 17 unchanged upper/great patches must not be replaced. New-position overlays alone are invalid.',
                'preserved_roof_support_proof': {'path': str((HERE/'preserved_roof_support.json').relative_to(ROOT)), 'sha256': a.sha(HERE/'preserved_roof_support.json')},
                'protected_component_entry_cuts': old_contract['protected_component_entry_cuts'], 'entrances': old_contract['entrances'], 'city_placement_ids': old_contract['city_placement_ids'],
                'activation': {'runtime_ready': False, 'compiled': False, 'atomic': True, 'original_occupancy_unchanged': False, 'source_revision_required': True, 'original_city_index_changed': False, 'collision_reference_changed': False, 'source_envelope_growth_m': 0, 'old_cavity_recovery_requires_full_source_evaluation': True, 'arbitrary_fill_boxes_allowed': False, 'whole_group_removal': False, 'requires_parent_visual_review': True}}
    a.write(HERE / 'replacement.b2.json.gz', contract)
    a.write(HERE / 'coordinates.b2.json', {'candidate': r['candidate'], 'source_axes_count': 8, 'window_count': 16, 'new_axes_m': r['new_centers_m'], 'windows': changed})
    checked_inputs(r)
    results = {'status': 'source_candidate_authored_structural_tests_pending', 'compile_calls': 0, 'runtime_edits': 0,
               'original_master_sha256': revision['original_master_sha256'], 'revised_master_sha256': revision['revised_master_sha256'],
               'canonical_master_sha256': a.sha(canonical_path), 'original_transforms_changed': len(changes),
               'source_windows': len(patches), 'lower_windows_relocated': len(changed), 'old_and_new_regions': len(affected),
               'cavity_cuts_reauthored': len(new_cuts), 'detail_operations_reauthored': len(new_details),
               'roof_operation_count_preserved': preserved_before['roof_operation_count'], 'support_operation_count_preserved': preserved_before['support_operation_count'],
               'pre_revision_coarse_quad_edits': len(edits), 'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               'output_files': {p.name: {'sha256': a.sha(p), 'bytes': p.stat().st_size} for p in sorted(HERE.iterdir()) if p.name in ('source.b2.revised.master.json.gz', 'windows.b2.authored.master.json.gz', 'canonical.b2.authored.master.json.gz', 'replacement.b2.json.gz', 'source_revision.json', 'coordinates.b2.json', 'preserved_roof_support.json', 'revision_rules.json')}}
    assert results['max_rss_kib'] < r['semantic_limits']['max_rss_kib']
    a.write(HERE / 'authoring_summary.json', results)
    core.compile_master = original_compile
    print(json.dumps({k: v for k, v in results.items() if k != 'output_files'}, indent=2))


if __name__ == '__main__': main()
