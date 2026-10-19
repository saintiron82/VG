#!/usr/bin/env python3
"""Independent source-delta, protected-material and exterior-face audit.

Read-only inputs; writes only validation_r01. Does not mesh or compile.
External unit faces are compared explicitly, never inferred from cell retention.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import resource
resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 ** 2,) * 2)
resource.setrlimit(resource.RLIMIT_CPU, (120,) * 2)
import collections
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
A = OUT.parent.parent
ROOT = next(p for p in A.parents if (p / 'voxel_character/common/core.py').exists())
sys.path.insert(0, str(ROOT))
from voxel_character.common import core
P = 1 / 32


def read(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else path.open() as stream:
        return json.load(stream)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def check(value, message):
    if not value:
        raise AssertionError(message)


def external_faces(a, axis, sign):
    occupied_neighbor = np.zeros(a.shape, dtype=bool)
    owner, neighbor = [slice(None)] * 3, [slice(None)] * 3
    owner[axis] = slice(1, None) if sign < 0 else slice(None, -1)
    neighbor[axis] = slice(None, -1) if sign < 0 else slice(1, None)
    occupied_neighbor[tuple(owner)] = a[tuple(neighbor)] >= 0
    np.logical_not(occupied_neighbor, out=occupied_neighbor)
    occupied_neighbor &= a >= 0
    occupied_neighbor[:4] = False
    return occupied_neighbor


def first_hit(a, axis, sign, origin):
    shape = tuple(v for k, v in enumerate(a.shape) if k != axis)
    index = np.full(shape, -32768, dtype=np.int16)
    material = np.full(shape, -1, dtype=np.int16)
    order = range(a.shape[axis]) if sign > 0 else range(a.shape[axis] - 1, -1, -1)
    offset = [origin[1], origin[0], origin[2]][axis]
    for position in order:
        if axis == 0 and position < 4:
            continue
        plane = np.take(a, position, axis=axis)
        mask = plane >= 0
        index[mask] = position + offset
        material[mask] = plane[mask]
    return (index[4:], material[4:]) if axis != 0 else (index, material)


def main():
    started, cpu = time.monotonic(), time.process_time()
    old_path = A / 'roof_repair_r04/upper_union_arrays.npz'
    new_path = A / 'roof_repair_r05/upper_union_arrays.npz'
    delta_path = A / 'roof_repair_r05/delta_cells.json.gz'
    master_path = A / 'roof_repair_r05/roof_patch.master.json.gz'
    labels_path = A / 'roof_repair_r03/delta_ownership_arrays.npz'
    r04_index = A / 'roof_repair_r04/compile.json'
    r04_delta = ROOT / read(r04_index)['delta']['path']
    pin_paths = [old_path, new_path, delta_path, master_path, labels_path, r04_index, r04_delta,
                 A / 'roof_repair_r05/compile.json', A / 'roof_repair_r02/compile.json', Path(core.__file__), Path(__file__)]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in pin_paths}
    old_npz, new_npz = np.load(old_path), np.load(new_path)
    old, new = old_npz['materials'], new_npz['materials']
    origin, names = old_npz['origin_cell_xyz'].tolist(), old_npz['material_names'].tolist()
    check(old.shape == new.shape == (148, 400, 328), 'Union shape mismatch')
    check(origin == new_npz['origin_cell_xyz'].tolist() == [-200, 300, -164], 'Union origin mismatch')
    check(names == new_npz['material_names'].tolist(), 'Material-index mapping changed')
    check(float(old_npz['pitch_m']) == float(new_npz['pitch_m']) == P, 'Pitch changed')
    check(float(old_npz['join_y_m']) == float(new_npz['join_y_m']) == 9.5, 'Join changed')
    lower_equal = np.array_equal(old[:4], new[:4])
    check(lower_equal, 'Lower join halo changed')
    delta = read(delta_path)['cells']
    by_coordinate = {tuple(row[:3]): row for row in delta}
    check(len(by_coordinate) == len(delta), 'Duplicate delta coordinates')
    master = read(master_path)
    tiles = {c['operations'][0]['id']: c['operations'] for c in master['components']}
    prepared_ops = {fid: [(op, core.prepare_shape(op['shape'], P), core.transform(op.get('transform')))
                          for op in ops] for fid, ops in tiles.items()}
    labels = np.load(labels_path)['delta_class']
    protected = {tuple(row[:3]) for row in read(r04_delta)['cells']}
    check(labels.shape == old.shape, 'R3 protection labels shape mismatch')
    mask = np.zeros(old.shape, dtype=bool)
    source_counts, prior_classes = collections.Counter(), collections.Counter()
    source_errors = []
    for x, y, z, prior, after, feature, owner in delta:
        iy, ix, iz = y - origin[1], x - origin[0], z - origin[2]
        check(4 <= iy < old.shape[0] and 0 <= ix < old.shape[1] and 0 <= iz < old.shape[2], 'Delta out of authorized upper bounds')
        check(int(old[iy, ix, iz]) == prior and int(new[iy, ix, iz]) == after, 'Delta differs from actual before/after arrays')
        check(after == names.index(tiles[feature][0]['material']), 'Delta material not copied from exact source tile')
        check((x, y, z) not in protected and int(labels[iy, ix, iz]) not in [1, 2], 'Delta changed a protected R3/R4 source cell')
        check(owner == ('empty' if prior < 0 else 'original_support'), 'Prior-owner class mismatch')
        point = [(x + .5) * P, (y + .5) * P, (z + .5) * P]
        cell = None
        for op, shape, placement in prepared_ops[feature]:
            if core.contains(shape, core.inverse(placement, point), epsilon=P * core.EPS):
                if op['action'] == 'paint':
                    cell = {'feature': op['id'], 'part': op['part'], 'material': op['material']}
                elif cell and core.selector_matches(op.get('selector', {}), cell):
                    cell = None
        check(cell is not None and cell['feature'] == feature, 'Delta cell is not contained by original cropped tile')
        mask[iy, ix, iz] = True
        source_counts[feature] += 1; prior_classes[owner] += 1
    del labels, protected
    changed = old != new
    check(not np.any(changed & ~mask), 'Unexpected change outside exact delta')
    check(int(changed.sum()) == sum(row[3] != row[4] for row in delta), 'Occupancy/material difference count mismatch')
    same_material_transfers = sum(row[3] == row[4] for row in delta)
    change_count = int(changed.sum())
    del changed, mask

    # Authenticate persisted delta feature ownership against the bounded common
    # compiler outputs, and authenticate every replaced support against R2.
    authenticated, authenticated_supports = set(), set()
    for index_path, target in [(A / 'roof_repair_r05/compile.json', 'new'),
                               (A / 'roof_repair_r02/compile.json', 'support')]:
        for record in read(index_path)['chunks']:
            path = ROOT / record['compiled']['path']
            check(sha(path) == record['compiled']['sha256'], 'Compiled chunk pin mismatch')
            pins[str(path.relative_to(ROOT))] = record['compiled']['sha256']
            for row in read(path)['cells']:
                coordinate = tuple(row[:3])
                if coordinate not in by_coordinate:
                    continue
                delta_row = by_coordinate[coordinate]
                if target == 'new':
                    check(row[3] == 'tile_' + delta_row[5] and row[6] == delta_row[5]
                          and names[delta_row[4]] == row[5], 'Persisted compiled source ownership mismatch')
                    authenticated.add(coordinate)
                elif delta_row[6] == 'original_support' and row[4] == 'thin_roof_support':
                    check(names[delta_row[3]] == row[5], 'Prior support material mismatch')
                    authenticated_supports.add(coordinate)
    check(len(authenticated) == len(delta), 'Some delta ownership lacks compiled evidence')
    check(len(authenticated_supports) == prior_classes['original_support'], 'Some replaced support lacks exact source evidence')

    protected_ids = [i for i, name in enumerate(names) if not name.startswith('top_tile_')]
    material_preservation = []
    for index in protected_ids:
        old_mask, new_mask = old == index, new == index
        equal = np.array_equal(old_mask, new_mask)
        check(equal, 'Protected material cell locations changed: ' + names[index])
        material_preservation.append({'material': names[index], 'occupied_cells': int(old_mask.sum()), 'cell_mask_equal': equal})
    del old_mask, new_mask

    faces, witnesses, occluders = [], [], set()
    for axis, dimension in [(0, 'Y'), (1, 'X'), (2, 'Z')]:
        for sign in [-1, 1]:
            before = external_faces(old, axis, sign)
            after = external_faces(new, axis, sign)
            direction = ('-' if sign < 0 else '+') + dimension
            count_before = np.bincount(old[before], minlength=len(names))
            count_after = np.bincount(new[after], minlength=len(names))
            lost_mask, gained_mask = before & ~after, after & ~before
            lost_by_material = np.bincount(old[lost_mask], minlength=len(names))
            gained_by_material = np.bincount(new[gained_mask], minlength=len(names))
            for index in protected_ids:
                lost, gained = int(lost_by_material[index]), int(gained_by_material[index])
                faces.append({'direction': direction, 'material': names[index],
                              'before_unit_faces': int(count_before[index]), 'after_unit_faces': int(count_after[index]),
                              'lost_unit_faces': lost, 'gained_unit_faces': gained, 'exact_face_mask_equal': lost == gained == 0})
                if lost:
                    for iy, ix, iz in np.argwhere(lost_mask & (old == index)):
                        xyz = [int(ix) + origin[0], int(iy) + origin[1], int(iz) + origin[2]]
                        neighbor = list(xyz)
                        neighbor[{'X': 0, 'Y': 1, 'Z': 2}[dimension]] += sign
                        delta_row = by_coordinate.get(tuple(neighbor))
                        check(delta_row is not None and delta_row[3] < 0, 'Lost protected face lacks adjacent added source tile')
                        occluders.add(tuple(neighbor))
                        witnesses.append({'owner_cell_xyz': xyz, 'material': names[index], 'direction': direction,
                                          'adjacent_delta_xyz': neighbor, 'adjacent_source_tile': delta_row[5],
                                          'adjacent_new_material': names[delta_row[4]]})
            del before, after, lost_mask, gained_mask

    views = []
    for label, axis, sign in [('FRONT', 2, 1), ('BACK', 2, -1), ('TOP', 0, 1)]:
        before_position, before_material = first_hit(old, axis, sign, origin)
        after_position, after_material = first_hit(new, axis, sign, origin)
        difference = (before_position != after_position) | (before_material != after_material)
        by_material = []
        for index in protected_ids:
            count = int(np.count_nonzero(difference & ((before_material == index) | (after_material == index))))
            by_material.append({'material': names[index], 'changed_first_hit_columns': count})
        views.append({'view': label, 'axis': ['Y', 'X', 'Z'][axis], 'direction': sign,
                      'changed_first_hit_columns': int(difference.sum()), 'protected_material_first_hits': by_material,
                      'protected_material_first_hits_equal': all(row['changed_first_hit_columns'] == 0 for row in by_material)})

    check(all(sha(ROOT / path) == value for path, value in pins.items()), 'Inputs changed during independent validation')
    coordinates = np.asarray([row[:3] for row in delta], dtype=np.int32)
    lost_faces, gained_faces = sum(row['lost_unit_faces'] for row in faces), sum(row['gained_unit_faces'] for row in faces)
    report = {'schema': 'riverstone.roof.source_delta_independent_validation.r1',
              'status': 'PASS' if lost_faces == gained_faces == 0 else 'BLOCKED_NONROOF_EXTERIOR_PRESERVATION',
              'source_dependencies': pins,
              'scope': 'Frozen R4 versus r05 upper union, exact material cell locations, unit exterior faces and axis first-hit masks; no render or full-asset closure claim.',
              'delta_cells_source_authenticated': len(delta), 'replaced_supports_source_authenticated': len(authenticated_supports),
              'changed_occupancy_or_material_cells': change_count, 'same_material_owner_transfers': same_material_transfers,
              'prior_owner_classes': dict(prior_classes), 'delta_cell_bounds_xyz_inclusive': {'min': coordinates.min(axis=0).tolist(), 'max': coordinates.max(axis=0).tolist()},
              'all_delta_inside_original_cropped_source_tiles': True, 'all_delta_materials_exact_source': True,
              'all_persisted_delta_feature_owners_match_common_compiled_chunks': True,
              'changes_outside_delta': 0, 'protected_R3_R4_cell_overwrites': 0,
              'lower_halo_y_cells': [300, 304], 'lower_halo_material_arrays_exactly_equal': lower_equal,
              'protected_material_cell_masks': material_preservation,
              'exterior_face_convention': 'Occupied owner cell at Y>=304 with empty adjacent union cell. All six directions; lower halo is used as neighbor context; outside union array interpreted empty.',
              'protected_material_unit_faces': faces, 'protected_unit_faces_lost': lost_faces,
              'protected_unit_faces_gained': gained_faces, 'unique_adjacent_added_tile_cells_occluding_protected_faces': len(occluders),
              'all_protected_exterior_face_masks_equal': lost_faces == gained_faces == 0,
              'first_hit_views': views, 'source_tile_delta_counts': dict(source_counts),
              'all_dependency_pins_unchanged': True, 'compiler_calls': 0, 'mesher_calls': 0,
              'process_caps': {'address_space_mib': 384, 'cpu_seconds': 120},
              'elapsed_seconds': time.monotonic() - started, 'cpu_seconds': time.process_time() - cpu,
              'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    outputs = {'source_delta_proof.json': report,
               'protected_external_face_witnesses.json': {'union_sha256': pins[str(new_path.relative_to(ROOT))],
                  'lost_face_witnesses': witnesses, 'occluding_delta_cells_xyz': [list(xyz) for xyz in sorted(occluders)]}}
    encoded = {name: json.dumps(value, ensure_ascii=False, indent=2) + '\n' for name, value in outputs.items()}
    retained = sum(p.stat().st_size for p in OUT.iterdir() if p.is_file() and p.name not in outputs)
    check(retained + sum(len(value.encode()) for value in encoded.values()) <= 1000000, 'Validation directory exceeds 1 MB')
    for name, contents in encoded.items():
        (OUT / name).write_text(contents)
    print(json.dumps({k: report[k] for k in ['status', 'delta_cells_source_authenticated',
        'protected_unit_faces_lost', 'protected_unit_faces_gained',
        'unique_adjacent_added_tile_cells_occluding_protected_faces', 'elapsed_seconds', 'cpu_seconds', 'peak_rss_kib']}))


if __name__ == '__main__':
    main()
