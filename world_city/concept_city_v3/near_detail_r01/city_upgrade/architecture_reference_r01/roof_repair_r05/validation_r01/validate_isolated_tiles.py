#!/usr/bin/env python3
"""Independent, bounded source-identity and component-local-cut regression tests.

Writes only this validation directory. No production compiler/mesher run, no
source edits, no reconstructed or newly measured geometry. Compilation uses
only tiny integer ROIs and hard candidate/output/plan/process budgets.
"""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import resource
resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 ** 2,) * 2)
resource.setrlimit(resource.RLIMIT_CPU, (45,) * 2)
import copy
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time
from collections import Counter

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
A = OUT.parent.parent
ROOT = next(p for p in A.parents if (p / 'voxel_character/common/core.py').is_file())
sys.path.insert(0, str(ROOT))
from voxel_character.common import core
from voxel_character.common import prepared_sampling_v3 as prepared

PITCH = 1 / 32
REQUEST = {'pitch': PITCH}
TILE_PARTS = {'measured_tile_regions', 'observed_shadow_tile_extensions'}
CAPS = {'max_candidate_cells': 4096, 'max_output_cells': 512}
PLAN_CAP = 32 * 1024 ** 2


def read(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else path.open() as stream:
        return json.load(stream)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def extract_sources():
    masters, tiles, hashes = {}, [], {}
    for rev, expected in [(2, 339), (3, 15)]:
        path = A / f'roof_repair_r{rev:02d}/roof_patch.master.json.gz'
        m = read(path)
        masters[rev] = m
        hashes[rev] = sha(path)
        check(not m.get('assembly_cuts'), 'Frozen source unexpectedly has assembly cuts')
        check(len(m['components']) == len(m['instances']) == 1, 'Frozen source structure changed')
        check(core.transform(m['instances'][0].get('transform')) == core.transform(), 'Frozen placement changed')
        operations = m['components'][0]['operations']
        count = 0
        for index, operation in enumerate(operations):
            if operation['action'] != 'paint' or operation['part'] not in TILE_PARTS:
                continue
            group = operations[index:index + 3]
            feature = operation['id']
            check([o['id'] for o in group] == [feature, feature + '_crop_left', feature + '_crop_right'], 'Source triplet changed')
            check([o['action'] for o in group] == ['paint', 'cut', 'cut'], 'Source triplet action changed')
            check(all(o.get('selector') == {'feature': feature} for o in group[1:]), 'Source cut selector changed')
            tiles.append({'revision': rev, 'feature': feature, 'ops': group})
            count += 1
        check(count == expected, 'Source tile count changed')
    return masters, tiles, hashes


def validate_contract(master, tiles, sources):
    """Stricter r05 authoring contract, not a change to common-core validation."""
    core.validate_master(master, PITCH)
    check(not master.get('assembly_cuts'), 'Global/assembly cuts are forbidden for this repair')
    check(master.get('grid_origin') == [0, 0, 0], 'Sampling origin changed')
    check(len(master['components']) == len(master['instances']) == len(tiles) == 354, 'One component/instance per source tile required')
    expected_materials = {}
    for source in sources.values():
        expected_materials.update(source['materials'])
    check(master['materials'] == expected_materials, 'Source materials changed')
    for component, instance, tile in zip(master['components'], master['instances'], tiles):
        expected_id = 'tile_' + tile['feature']
        check(component['id'] == instance['id'] == instance['component'] == expected_id, 'Source-order or identity mismatch')
        check(instance.get('parent') is None and core.transform(instance.get('transform')) == core.transform(), 'Tile instance placement must be identity')
        check(component['operations'] == tile['ops'], 'Exact original paint and two feature cuts required')
        check(component['parts'] == [{'id': tile['ops'][0]['part'], 'pivot': [0, 0, 0]}], 'Source part identity changed')
        check(len(component['operations']) == 3, 'Tile must be isolated from every other paint')
        for operation in component['operations'][1:]:
            check(operation.get('selector') == {'feature': tile['feature']}, 'Unscoped/foreign cut rejected')
    return True


def prepare_point_operation(operation):
    shape = core.prepare_shape(operation['shape'], PITCH)
    transform = core.transform(operation.get('transform'))
    lo, hi = core.shape_bounds(shape)
    corners = [core.apply(transform, p) for p in itertools.product(*zip(lo, hi))]
    low = [min(p[k] for p in corners) for k in range(3)]
    high = [max(p[k] for p in corners) for k in range(3)]
    return operation, shape, transform, low, high


def contains(prep, point):
    _, shape, placement, low, high = prep
    return (all(low[k] - 1e-10 <= point[k] <= high[k] + 1e-10 for k in range(3))
            and core.contains(shape, core.inverse(placement, point), epsilon=PITCH * core.EPS))


def replay_operations(operations, point, instance='source', component='source'):
    cell = None
    for prep in operations:
        operation = prep[0]
        if not contains(prep, point):
            continue
        if operation['action'] == 'paint':
            cell = {'instance': instance, 'component': component, 'feature': operation['id'],
                    'part': operation['part'], 'material': operation['material']}
        elif cell and core.selector_matches(operation.get('selector', {}), cell):
            cell = None
    return cell


def roi(center, radius=1):
    return {'min': [v - radius for v in center], 'max': [v + radius + 1 for v in center]}


def compare_compilers(master, bounds, plan=None):
    check(math.prod(b - a for a, b in zip(bounds['min'], bounds['max'])) <= 27, 'ROI exceeds 27 cells')
    baseline = core.compile_master(master, REQUEST, cell_bounds=bounds, **CAPS)
    if plan is None:
        plan = prepared.prepare_master(master, REQUEST, max_plan_bytes=PLAN_CAP)
    fast = prepared.compile_prepared(plan, cell_bounds=bounds, **CAPS)
    # Backend identity is intentionally different; every other result field,
    # including cells, ownership, constraints and candidate count, must agree.
    reference_semantics = {k: v for k, v in baseline.items() if k != 'compiler_source_hash'}
    prepared_semantics = {k: v for k, v in fast.items() if k not in ('compiler_source_hash', 'compiler_provenance')}
    check(reference_semantics == prepared_semantics, 'Baseline/prepared semantic mismatch')
    check(baseline['valid_scope'] == 'cell_bounds_only' and baseline['global_constraints_valid'] is None,
          'Bounded test must not claim full-master constraint validity')
    return baseline


def subset(master, features, merged=False, duplicate=False):
    m = copy.deepcopy(master)
    selected = [c for c in m['components'] if c['operations'][0]['id'] in features]
    check(len(selected) == len(features), 'Fixture feature missing')
    if merged:
        selected = [{'id': 'same_component_regression', 'parts': selected[0]['parts'],
                     'operations': [op for c in selected for op in c['operations']]}]
    m['components'] = selected
    m['instances'] = [{'id': c['id'], 'component': c['id']} for c in selected]
    if duplicate:
        check(len(selected) == 1, 'Overlap fixture must have one unchanged tile source')
        m['instances'] = [{'id': label, 'component': selected[0]['id']} for label in ['overlap_first', 'overlap_last']]
    m['id'] = 'bounded_validation_fixture'
    m['constraints'] = []
    return m


def main():
    started, cpu = time.monotonic(), time.process_time()
    source_masters, tiles, source_hashes = extract_sources()
    master_path = A / 'roof_repair_r05/roof_patch.master.json.gz'
    master, plan_meta = read(master_path), read(A / 'roof_repair_r05/plan.json')
    pin_paths = [master_path, A / 'roof_repair_r05/plan.json',
                 A / 'roof_backing_measurement_r01/source_ordering_audit.json',
                 A / 'roof_backing_measurement_r01/source_ordering_witnesses.json',
                 Path(core.__file__), Path(prepared.__file__), Path(__file__)]
    for rev in [2, 3, 4]:
        pin_paths.append(A / f'roof_repair_r{rev:02d}/roof_patch.master.json.gz')
    pins = {str(p.relative_to(ROOT)): sha(p) for p in pin_paths}
    validate_contract(master, tiles, source_masters)
    check(len(plan_meta['source_tile_links']) == 354, 'Plan link count mismatch')
    identities = []
    for tile, link in zip(tiles, plan_meta['source_tile_links']):
        check(link['source_feature'] == tile['feature'] and link['source_revision'] == tile['revision'], 'Plan order mismatch')
        check(link['source_master']['sha256'] == source_hashes[tile['revision']], 'Plan source hash mismatch')
        check(link['operations_sha256'] == core.digest(tile['ops']), 'Plan operation hash mismatch')
        check(link['component'] == link['instance'] == 'tile_' + tile['feature'], 'Plan tile ownership mismatch')
        identities.append({'source_revision': tile['revision'], 'feature': tile['feature'], 'operations_sha256': core.digest(tile['ops'])})

    tile_prepared = {t['feature']: [prepare_point_operation(o) for o in t['ops']] for t in tiles}
    source_prepared = {rev: [prepare_point_operation(o) for o in m['components'][0]['operations']]
                       for rev, m in source_masters.items()}
    witnesses = read(A / 'roof_backing_measurement_r01/source_ordering_witnesses.json')['queries']
    check(len(witnesses) == 1781, 'Expected all 1781 audited witnesses')
    restored, ownership, overlaps, old_bugs = [], Counter(), [], 0
    for witness in witnesses:
        point, feature = witness['world_center'], witness['expected_source_tile']
        rev = 3 if witness['source_revision'].endswith('03') else 2
        check([(v + .5) * PITCH for v in witness['point_grid_xyz']] == point, 'Witness grid mismatch')
        old = replay_operations(source_prepared[rev], point)
        check(old is None and witness['ordered_source_final_feature'] is None, 'Historical ordering bug not reproduced')
        old_bugs += 1
        expected_layer = replay_operations(tile_prepared[feature], point)
        check(expected_layer is not None and expected_layer['feature'] == feature, 'Expected tile is destroyed by its own original cuts')
        surviving = [t['feature'] for t in tiles if replay_operations(tile_prepared[t['feature']], point)]
        check(feature in surviving, 'Expected tile layer not preserved')
        check(surviving, 'Isolated tile union remains empty')
        owner = surviving[-1]
        ownership['expected_tile_final_owner' if owner == feature else 'later_source_tile_final_owner'] += 1
        if len(surviving) > 1:
            overlaps.append({'point_grid_xyz': witness['point_grid_xyz'], 'surviving_layers': surviving, 'final_owner': owner})
        restored.append({'point_grid_xyz': witness['point_grid_xyz'], 'expected_tile': feature, 'final_owner': owner})

    # Representative full-r05 queries retain all 354 components but intersect
    # each operation's integer ranges with only a 3x3x3 ROI (27 cells).
    representatives = [witnesses[0]]
    for predicate in [lambda w: w['source_revision'].endswith('03'),
                      lambda w: w['distance_band'] == '>2P',
                      lambda w: not w['whole_XZ_cell_inside']]:
        w = next(w for w in witnesses if predicate(w))
        if w not in representatives:
            representatives.append(w)
    left = next(t for t in tiles if t['feature'].startswith('left_'))
    paint = left['ops'][0]
    local = [0, PITCH, (paint['shape']['z_min'] + paint['shape']['z_max']) / 2]
    seed = [math.floor(v / PITCH) for v in core.apply(core.transform(paint.get('transform')), local)]
    left_center = next([a + b for a, b in zip(seed, delta)] for delta in itertools.product(range(-1, 2), repeat=3)
                       if replay_operations(tile_prepared[left['feature']],
                                            [(a + b + .5) * PITCH for a, b in zip(seed, delta)]))
    representatives.append({'point_grid_xyz': left_center, 'expected_source_tile': left['feature']})
    first = witnesses[0]
    first_tile = tile_prepared[first['expected_source_tile']]
    next_tile = tile_prepared[first['later_overwriting_feature']]
    gap_low = first_tile[2][0]['shape']['min'][0]
    gap_high = next_tile[1][0]['shape']['max'][0]
    gap_center = list(first['point_grid_xyz'])
    gap_center[0] = math.floor((gap_low + gap_high) / (2 * PITCH))
    check(gap_low < (gap_center[0] + .5) * PITCH < gap_high, 'Source separator has no chosen lattice center')
    check(not any(replay_operations(ops, [(v + .5) * PITCH for v in gap_center]) for ops in tile_prepared.values()),
          'Expected source separator is occupied')
    representatives.append({'point_grid_xyz': gap_center, 'expected_source_tile': None, 'radius': 0,
                            'label': 'authored_x_separator_remains_empty'})
    full_plan = prepared.prepare_master(master, REQUEST, max_plan_bytes=PLAN_CAP)
    compiler_checks, total_candidates, emitted = [], 0, 0
    for witness in representatives:
        bounds = roi(witness['point_grid_xyz'], witness.get('radius', 1))
        result = compare_compilers(master, bounds, full_plan)
        expected_rows = []
        for coordinate in itertools.product(*(range(a, b) for a, b in zip(bounds['min'], bounds['max']))):
            point = [(v + .5) * PITCH for v in coordinate]
            surviving = [t for t in tiles if replay_operations(tile_prepared[t['feature']], point)]
            if not surviving:
                continue
            expected = surviving[-1]
            expected_rows.append([*coordinate, 'tile_' + expected['feature'], expected['ops'][0]['part'],
                                  expected['ops'][0]['material'], expected['feature']])
        check(result['cells'] == expected_rows, 'Compiled ROI occupancy or source ownership mismatch')
        center = next((r for r in result['cells'] if r[:3] == witness['point_grid_xyz']), None)
        check((center is None) == (witness['expected_source_tile'] is None), 'Compiled center occupancy differs from source')
        check(result['candidate_cells'] <= CAPS['max_candidate_cells'], 'Candidate cap broken')
        total_candidates += result['candidate_cells']; emitted += len(result['cells'])
        compiler_checks.append({'source_feature': witness['expected_source_tile'], 'cell_bounds': bounds,
                                'candidate_cells': result['candidate_cells'], 'output_cells': len(result['cells']),
                                'payload_hash': result['payload_hash'], 'center_owner': center[6] if center else None,
                                'label': witness.get('label', 'source_tile_neighborhood'),
                                'all_roi_cells_match_independent_source_oracle': True,
                                'all_semantics_equal_except_backend_identity': True})

    fixtures, negative_results = [], []
    for rev in [2, 3]:
        witness = next(w for w in witnesses if w['source_revision'].endswith(f'{rev:02d}'))
        features = [witness['expected_source_tile'], witness['later_overwriting_feature']]
        isolated = subset(master, features)
        merged = subset(master, features, merged=True)
        bounds = roi(witness['point_grid_xyz'], radius=0)
        good = compare_compilers(isolated, bounds)
        bad = compare_compilers(merged, bounds)
        check(len(good['cells']) == 1 and good['cells'][0][6] == features[0], 'Two-tile local cut regression failed')
        check(bad['cells'] == [], 'Same-component fixture must retain the historical bug')
        fixtures.append({'name': f'R{rev}_exact_two_tile_source', 'bounds': bounds,
                         'isolated_master': isolated, 'same_component_negative_master': merged,
                         'expected_surviving_feature': features[0]})
        negative_results.append({'name': f'R{rev}_same_component_bug_retained', 'pass': True})

    # Exact overlapping instances of one unchanged source triplet prove generic
    # union ownership priority. They are test-only and rejected by r05 contract.
    witness = witnesses[0]
    duplicate = subset(master, [witness['expected_source_tile']], duplicate=True)
    bounds = roi(witness['point_grid_xyz'], radius=0)
    result = compare_compilers(duplicate, bounds)
    check(result['cells'][0][3] == 'overlap_last', 'Later retained instance must own true overlap')
    duplicate['instances'].reverse()
    reverse = compare_compilers(duplicate, bounds)
    check(reverse['cells'][0][3] == 'overlap_first', 'Reversing instance order must reverse overlap ownership')
    check(result['cells'][0][4:] == reverse['cells'][0][4:], 'Overlap ordering changed source semantics')
    fixtures.append({'name': 'unchanged_tile_full_overlap_reverse_order', 'bounds': bounds, 'master': duplicate})

    mutations = [
        ('unscoped_cut', lambda m: m['components'][0]['operations'][1].pop('selector')),
        ('global_assembly_cut', lambda m: m['assembly_cuts'].append(copy.deepcopy(m['components'][0]['operations'][1]))),
        ('foreign_feature_cut', lambda m: m['components'][0]['operations'][1].update(selector={'feature': 'wrong_tile'})),
        ('altered_source_geometry', lambda m: m['components'][0]['operations'][0]['shape'].update(z_max=123)),
        ('reordered_source_ownership', lambda m: m['instances'].reverse()),
        ('repeated_tile_instance', lambda m: m['instances'].append({'id': 'extra_instance', 'component': m['components'][0]['id']})),
        ('moved_tile_instance', lambda m: m['instances'][0].update(transform={'translation': [1, 0, 0]})),
    ]
    for name, mutate in mutations:
        changed = copy.deepcopy(master)
        mutate(changed)
        try:
            validate_contract(changed, tiles, source_masters)
        except (AssertionError, core.InvalidMaster) as error:
            negative_results.append({'name': name, 'pass': True, 'rejected_by': 'r05 validation contract', 'reason': str(error)})
        else:
            raise AssertionError('Negative mutation not rejected: ' + name)
    check(all(sha(ROOT / p) == value for p, value in pins.items()), 'Pinned input changed during validation')
    output_rows = {'schema': 'riverstone.roof.isolated_tile_validation.r1', 'pass': True,
                   'scope': 'Source identity; existing point witnesses; tiny bounded common compiler comparisons only. Not full-roof or merge acceptance.',
                   'source_dependencies': pins, 'source_tiles_by_revision': {'2': 339, '3': 15},
                   'exact_source_triplets': 354, 'exact_source_operations': 1062,
                   'source_geometry_material_transform_changes': 0, 'new_measured_regions': 0,
                   'all_local_cut_selectors_exact': True, 'assembly_cuts': 0,
                   'historical_same_component_null_witnesses_reproduced': old_bugs,
                   'isolated_source_witness_layers_preserved': len(restored),
                   'isolated_union_nonempty_witnesses': len(restored), 'witness_final_ownership': dict(ownership),
                   'witnesses_with_multiple_surviving_tiles': len(overlaps), 'overlap_examples': overlaps[:5],
                   'true_overlap_fixture_last_instance_ownership_verified': True,
                   'bounded_full_r05_checks': compiler_checks,
                   'bounded_baseline_compiler_calls': len(compiler_checks) + 6,
                   'bounded_prepared_compiler_calls': len(compiler_checks) + 6,
                   'full_r05_roi_candidate_cells_total_per_backend': total_candidates,
                   'full_r05_roi_output_cells_total_per_backend': emitted,
                   'maximum_roi_volume_cells': 27, 'compiler_call_caps': CAPS,
                   'plan_cap_bytes': PLAN_CAP, 'prepared_full_master_retained_bytes': full_plan.retained_bytes,
                   'negative_tests': negative_results, 'all_pinned_inputs_unchanged': True,
                   'process_caps': {'address_space_mib': 256, 'cpu_seconds': 45, 'directory_output_max_bytes': 1000000},
                   'elapsed_seconds': time.monotonic() - started, 'cpu_seconds': time.process_time() - cpu,
                   'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   'production_or_large_compiler_calls': 0, 'mesher_calls': 0}
    outputs = {'validation_report.json': output_rows,
               'source_operation_identities.json': {'tiles': identities, 'combined_sha256': core.digest(identities)},
               'point_witness_results.json': {'queries': restored}, 'tiny_regression_fixtures.json': {'fixtures': fixtures}}
    encoded = {name: json.dumps(value, ensure_ascii=False, indent=2 if name == 'validation_report.json' else None) + '\n'
               for name, value in outputs.items()}
    other_bytes = sum(p.stat().st_size for p in OUT.iterdir() if p.is_file() and p.name not in outputs)
    check(other_bytes + sum(len(value.encode()) for value in encoded.values()) <= 1000000, 'Validation outputs exceed 1 MB')
    for name, contents in encoded.items():
        (OUT / name).write_text(contents)
    print(json.dumps({k: output_rows[k] for k in ['pass', 'exact_source_triplets', 'exact_source_operations',
        'historical_same_component_null_witnesses_reproduced', 'isolated_union_nonempty_witnesses',
        'witness_final_ownership', 'bounded_baseline_compiler_calls', 'elapsed_seconds', 'cpu_seconds', 'peak_rss_kib']}))


if __name__ == '__main__':
    main()
