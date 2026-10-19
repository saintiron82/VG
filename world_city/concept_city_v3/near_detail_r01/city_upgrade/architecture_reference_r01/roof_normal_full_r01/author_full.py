#!/usr/bin/env python3
"""Author the approved full-source normal sidecar without changing frozen geometry.

Reuse the existing SourceTile classifier and deterministic coplanar partition.
Only one render quad and its labels/pieces are expanded at once. Patch/split
sections are compressed while authoring, then streamed into one deterministic
gzip member. No uncompressed sidecar is written or built as a complete object.
"""
import os
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

from pathlib import Path
import collections
import gc
import gzip
import hashlib
import json
import math
import resource
import time
import traceback

OUT = Path(__file__).resolve().parent
A = OUT.parent
R2, R3, R4 = (A / ('roof_repair_r0' + str(i)) for i in (2, 3, 4))
sys.path.insert(0, str(R3 / 'normal_split_diagnostic_r01'))
from build_split_diagnostic import SourceTile, JsonStream, read, sha, stream_quads, qspec, rect, faces, np

resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 ** 2,) * 2)
resource.setrlimit(resource.RLIMIT_CPU, (45,) * 2)
ROOT = next(p for p in OUT.parents if (p / 'voxel_character/common/core.py').exists())
P = .03125
PIN = '45e9b206d2b126df7dd2ce878f70ada312a122a49c9a958098d08ae1406cb4d5'
SCHEMA = 'riverstone.roof.normal_split_sidecar.v1'
OUTPUT = OUT / 'normal_split_sidecar.json.gz'


def encode(obj):
    return json.dumps(obj, separators=(',', ':'), allow_nan=False).encode('utf-8')


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


class Section:
    """An array's comma-separated contents, stored only in a gzip temporary."""
    def __init__(self, name):
        self.path = OUT / ('.' + name + '.json.gz.part')
        self.raw = self.path.open('wb')
        self.gz = gzip.GzipFile(filename='', mode='wb', compresslevel=9,
                                fileobj=self.raw, mtime=0)
        self.count = self.bytes = 0

    def add(self, obj):
        data = encode(obj)
        if self.count:
            self.gz.write(b',')
            self.bytes += 1
        self.gz.write(data)
        self.count += 1
        self.bytes += len(data)
        return len(data)

    def close(self):
        self.gz.close()
        self.raw.close()


def unit_outward(n, axis, sign):
    assert len(n) == 3 and all(type(x) in (int, float) and math.isfinite(x) for x in n)
    assert abs(sum(x * x for x in n) - 1) < 1e-9
    assert n[axis] * sign > 0


def roundtrip(path, expected_meta, expected_counts, raw_sha, raw_bytes):
    """Read every decompressed byte, then parse all items without a full JSON load."""
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, 'rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            digest.update(block)
            count += len(block)
    assert digest.hexdigest() == raw_sha and count == raw_bytes, 'gzip_roundtrip'
    seen = set()
    actual = collections.Counter()
    meta = {}
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        p = JsonStream(f)
        p.eat('{')
        while p.peek() != '}':
            key = p.value()
            p.eat(':')
            if key in ('patches', 'splits'):
                p.eat('[')
                while p.peek() != ']':
                    item = p.value()
                    target = (item['group_index'], item['quad_index'])
                    assert target not in seen, 'duplicate_or_overlapping_patch_split_target'
                    seen.add(target)
                    actual[key] += 1
                    if key == 'patches':
                        assert item['classification'] == 'analytic_top_staircase'
                        assert len(item['normals']) == 4
                    else:
                        assert item['material'].startswith('top_tile_')
                        assert item['quads']
                        actual['subquads'] += len(item['quads'])
                        for piece in item['quads']:
                            assert piece['classification'] in ('analytic_top_staircase', 'preserved_cardinal')
                            assert len(piece['normals']) == len(piece['corners']) == 4
                    if p.peek() == ',':
                        p.eat(',')
                    else:
                        break
                p.eat(']')
            else:
                assert key not in meta, 'duplicate_metadata'
                meta[key] = p.value()
            if p.peek() == ',':
                p.eat(',')
            else:
                break
        p.eat('}')
        assert p.peek() == '', 'trailing_data'
    assert meta == expected_meta, 'roundtrip_metadata'
    assert dict(actual) == expected_counts, (actual, expected_counts)
    return {'decompressed_sha256': digest.hexdigest(), 'decompressed_bytes': count,
            'parsed_patch_count': actual['patches'], 'parsed_split_count': actual['splits'],
            'parsed_subquad_count': actual['subquads'], 'duplicate_targets': 0}


def main():
    start, cpu = time.monotonic(), time.process_time()
    assert not OUTPUT.exists(), 'Refusing to overwrite a fixed authored payload'
    render = R4 / 'roof_repaired.render.json.gz'
    assert sha(render) == PIN
    audit_path = A / 'roof_normal_extent_r01/counts.json'
    audit = read(audit_path)
    assert audit['status'] == 'EXACT_COUNT_ONLY_NO_SIDECAR_WRITTEN'
    assert audit['render_sha256'] == PIN
    plans = [read(R2 / 'plan.json'), read(R3 / 'plan.json')]
    masters = [read(R2 / 'roof_patch.master.json.gz'), read(R3 / 'roof_patch.master.json.gz')]
    boxes_path = A / 'roof_repair_r01/tile_measurement_r01/tile_regions.json'
    boxes = {r['id']: r['bbox_px'] for r in read(boxes_path)['regions']}
    source, kind = {}, {}
    features = ['unknown_current_union_owner']
    fid_index = {features[0]: 0}

    def idx(fid):
        if fid not in fid_index:
            fid_index[fid] = len(features)
            features.append(fid)
        return fid_index[fid]

    for k, (plan, master) in enumerate(zip(plans, masters)):
        ops = {op['id']: op for comp in master['components'] for op in comp['operations']}
        for link in plan['tile_source_links']:
            fid = link['operation']
            assert fid not in kind, 'duplicate_source_id'
            source[idx(fid)] = SourceTile(ops[fid], link)
            kind[fid] = 'old_measured' if k == 0 else 'recovered_interval'
            if k == 0:
                assert link['source_bbox_px'] == boxes[fid]
            else:
                b, exclusion = link['source']['bbox_px'], [868, 795, 908, 849]
                assert b[2] <= exclusion[0] or b[0] >= exclusion[2] or b[3] <= exclusion[1] or b[1] >= exclusion[3]
    assert collections.Counter(kind.values()) == {'old_measured': 339, 'recovered_interval': 15}

    union = np.load(R4 / 'upper_union_arrays.npz')
    mat, origin = union['materials'], union['origin_cell_xyz'].tolist()
    mids = {name: i for i, name in enumerate(union['material_names'].tolist())}
    delta = np.load(R3 / 'delta_ownership_arrays.npz')['delta_class']
    owners = np.zeros(mat.shape, np.uint16)
    input_paths = [render, R4 / 'upper_union_arrays.npz', R3 / 'delta_ownership_arrays.npz',
                   R2 / 'plan.json', R3 / 'plan.json', R2 / 'roof_patch.master.json.gz',
                   R3 / 'roof_patch.master.json.gz', R2 / 'compile.json', R3 / 'compile.json',
                   R4 / 'compile.json', boxes_path, audit_path,
                   A / 'roof_normal_extent_r01/count_extent.py',
                   R3 / 'normal_split_diagnostic_r01/build_split_diagnostic.py',
                   R3 / 'normal_diagnostic_r01/derive_normal_diagnostic.py']
    pins = {str(p.relative_to(ROOT)): sha(p) for p in input_paths}
    assigned = collections.Counter()
    all_compiled = r4_changed_cells = 0
    r4_owner_ids = set()

    for rec in read(R2 / 'compile.json')['chunks']:
        path = ROOT / rec['compiled']['path']
        assert sha(path) == rec['compiled']['sha256']
        pins[str(path.relative_to(ROOT))] = sha(path)
        data = read(path)
        for x, y, z, inst, part, material, fid in data['cells']:
            iy, ix, iz = y - origin[1], x - origin[0], z - origin[2]
            if delta[iy, ix, iz] == 0 and mat[iy, ix, iz] == mids[material]:
                owners[iy, ix, iz] = idx(fid)
                assigned[kind.get(fid, 'other')] += 1
        all_compiled += len(data['cells'])
        del data
        gc.collect()
    for revision in (R3, R4):
        rec = read(revision / 'compile.json')['delta']
        path = ROOT / rec['path']
        assert sha(path) == rec['sha256']
        pins[str(path.relative_to(ROOT))] = sha(path)
        data = read(path)
        for x, y, z, inst, part, material, fid in data['cells']:
            iy, ix, iz = y - origin[1], x - origin[0], z - origin[2]
            if mat[iy, ix, iz] != mids[material]:
                continue
            if revision == R3 and not ((part == 'observed_shadow_tile_extensions' and delta[iy, ix, iz] == 3)
                                       or (part == 'foreground_resampled_gable_edge' and delta[iy, ix, iz] == 2)):
                continue
            owners[iy, ix, iz] = idx(fid)
            assigned[kind.get(fid, 'other')] += 1
            if revision == R4:
                r4_owner_ids.add(idx(fid))
                r4_changed_cells += 1
                assert idx(fid) not in source
        all_compiled += len(data['cells'])
        del data
        gc.collect()
    assert r4_changed_cells == 2609
    assert all_compiled == audit['cached_compiled_rows_scanned']
    assert dict(assigned) == audit['ownership_assigned_counts']
    del delta
    gc.collect()
    ownership_seconds = time.monotonic() - start

    def cell_index(c):
        return c[1] - origin[1], c[0] - origin[0], c[2] - origin[2]

    patches, splits = Section('patches'), Section('splits')
    total = collections.Counter()
    per = collections.defaultdict(collections.Counter)
    skips, groupcounts = collections.Counter(), collections.Counter()
    cardinal_reasons, unsupported_owners = collections.Counter(), collections.Counter()
    meta, emitted = {}, set()
    previous_key = None
    for gi, qi, material, q in stream_quads(render, meta):
        key = gi, qi
        assert previous_key is None or previous_key < key
        previous_key = key
        total['all_render_quads'] += 1
        if not material.startswith('top_tile_'):
            continue
        total['top_material_quads'] += 1
        sp = qspec(q)
        lo, hi, axis, sign, u, v = sp
        assert sum(lo[i] == hi[i] for i in range(3)) == 1
        assert all(abs(value / P - round(value / P)) < 1e-10 for point in q for value in point)
        fs = list(faces(sp))
        oset = {int(owners[cell_index(c)]) for a, b, c in fs}
        total['top_material_unit_faces'] += len(fs)
        total['R4_changed_owner_exterior_unit_faces'] += sum(int(owners[cell_index(c)]) in r4_owner_ids for a, b, c in fs)
        if not oset.intersection(source):
            continue
        total['source_owned_candidate_quads'] += 1
        total['source_candidate_quad_unit_faces'] += len(fs)
        for a, b, c in fs:
            oid = int(owners[cell_index(c)])
            fid = features[oid]
            if oid in source:
                per[fid]['candidate_unit_faces'] += 1
                groupcounts[kind[fid] + '_candidate_unit_faces'] += 1
            nc = list(c)
            nc[axis] += sign
            assert mat[cell_index(c)] == mids[material] and mat[cell_index(nc)] < 0
        total['classified_candidate_quads'] += 1
        total['classified_candidate_quad_unit_faces'] += len(fs)
        if len(oset) == 1:
            oid = next(iter(oset))
            result, why = source[oid].classify(q, [c for a, b, c in fs], axis, sign)
            if result:
                n, segment = result
                unit_outward(n, axis, sign)
                fid = features[oid]
                assert oid not in r4_owner_ids
                normal = [round(t, 10) for t in n]
                unit_outward(normal, axis, sign)
                patch = {'group_index': gi, 'quad_index': qi, 'normals': [normal[:] for _ in range(4)],
                         'source_tile_id': fid, 'classification': 'analytic_top_staircase'}
                assert key not in emitted
                emitted.add(key)
                total['patch_payload_bytes'] += patches.add(patch)
                total['complete_quad_patches'] += 1
                total['complete_patch_unit_faces'] += len(fs)
                per[fid]['treated_unit_faces'] += len(fs)
                per[fid]['patches'] += 1
                continue
        else:
            why = 'mixed_or_unproven_tile_ownership'
        labels, safe = {}, 0
        cardinal = [0, 0, 0]
        cardinal[axis] = sign
        for a, b, c in fs:
            oid = int(owners[cell_index(c)])
            fid = features[oid]
            result, reason = None, 'non_source_owner'
            if oid in source:
                result, reason = source[oid].classify(rect(q, sp, a, b, a + 1, b + 1), [c], axis, sign)
            if result is None:
                label = fid, 'preserved_cardinal', tuple(cardinal)
                cardinal_reasons[reason] += 1
                if oid not in source:
                    unsupported_owners['R4_recolor_box' if oid in r4_owner_ids else
                                       ('backing_support' if fid.startswith('support_') else 'other_or_unknown')] += 1
            else:
                assert oid not in r4_owner_ids
                n, segment = result
                label = fid, 'analytic_top_staircase', tuple(round(t, 10) for t in n)
                safe += 1
                per[fid]['treated_unit_faces'] += 1
            labels[a, b] = label
        if not safe:
            total['untouched_source_candidate_quads'] += 1
            skips[why] += 1
            continue
        used, pieces, safe_rects = set(), [], 0
        for a, b, c in fs:
            if (a, b) in used:
                continue
            label = labels[a, b]
            b1 = b + 1
            while b1 < hi[v] and (a, b1) not in used and labels[a, b1] == label:
                b1 += 1
            a1 = a + 1
            while a1 < hi[u] and all((a1, x) not in used and labels[a1, x] == label for x in range(b, b1)):
                a1 += 1
            footprint = {(x, y) for x in range(a, a1) for y in range(b, b1)}
            assert footprint and not used.intersection(footprint)
            assert all(labels[uv] == label for uv in footprint)
            used.update(footprint)
            fid, classification, normal = label
            unit_outward(normal, axis, sign)
            if classification == 'preserved_cardinal':
                assert normal == tuple(cardinal)
            else:
                assert fid in kind and fid_index[fid] not in r4_owner_ids
            corners = rect(q, sp, a, b, a1, b1)
            ps = qspec(corners)
            assert ps[2:] == sp[2:] and ps[0][axis] == lo[axis]
            assert ps[0][u] == a and ps[1][u] == a1 and ps[0][v] == b and ps[1][v] == b1
            assert all(lo[i] <= ps[0][i] <= ps[1][i] <= hi[i] for i in range(3))
            assert corners == rect(q, sp, ps[0][u], ps[0][v], ps[1][u], ps[1][v])
            pieces.append({'corners': corners, 'normals': [list(normal) for _ in range(4)],
                           'source_tile_id': fid, 'classification': classification})
            safe_rects += classification == 'analytic_top_staircase'
        assert used == set(labels), 'split_not_exact_disjoint_cover'
        assert key not in emitted
        emitted.add(key)
        split = {'group_index': gi, 'quad_index': qi, 'material': material, 'quads': pieces}
        total['split_payload_bytes'] += splits.add(split)
        total['split_original_quads'] += 1
        total['new_subquads'] += len(pieces)
        total['new_analytic_subquads'] += safe_rects
        total['new_preserved_cardinal_subquads'] += len(pieces) - safe_rects
        total['newly_treated_unit_faces'] += safe
        total['preserved_unit_faces_inside_splits'] += len(fs) - safe
    patches.close()
    splits.close()
    total['total_treated_unit_faces'] = total['complete_patch_unit_faces'] + total['newly_treated_unit_faces']
    total['quad_delta'] = total['new_subquads'] - total['split_original_quads']
    total['unindexed_triangle_vertex_delta'] = total['quad_delta'] * 6
    total['arraymesh_position_normal_float32_extra_bytes'] = total['unindexed_triangle_vertex_delta'] * 24
    total['arraymesh_position_normal_color_float32_extra_bytes'] = total['unindexed_triangle_vertex_delta'] * 40
    assert total['all_render_quads'] == meta['quad_count']
    assert all(value == audit['totals'][key] for key, value in total.items()), 'count_audit_mismatch'
    assert dict(per) == audit['per_source'], 'per_source_audit_mismatch'
    assert dict(skips) == audit['skip_counts_quad_level']
    assert dict(cardinal_reasons) == audit['preserved_candidate_unit_face_reasons']
    assert dict(unsupported_owners) == audit['preserved_non_source_unit_face_owners_inside_candidate_quads']
    assert sum(cardinal_reasons.values()) == total['source_candidate_quad_unit_faces'] - total['total_treated_unit_faces']
    assert len(per) == 354 and all(per[features[i]]['treated_unit_faces'] > 0 for i in source)
    assert len(emitted) == patches.count + splits.count == 59538
    del emitted

    fixed = {'schema': SCHEMA, 'render_sha256': PIN, 'diagnostic_only': True,
             'production_gate_open': False,
             'geometry_invariant': 'exact coplanar area-preserving lattice partition; vertex/index representation changes; no displacement',
             'unchanged_materials_sha256': hashlib.sha256(json.dumps(meta['materials'], sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
             'grid_pitch': P}
    temporary = OUT / '.normal_split_sidecar.json.gz.part'
    digest, raw_bytes = hashlib.sha256(), 0
    with temporary.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', compresslevel=9, fileobj=raw, mtime=0) as final:
            def emit(block):
                nonlocal raw_bytes
                digest.update(block)
                raw_bytes += len(block)
                final.write(block)
            emit(b'{"schema":' + encode(SCHEMA) + b',"render_sha256":' + encode(PIN) + b',"patches":[')
            for index, section in enumerate((patches, splits)):
                if index:
                    emit(b'],"splits":[')
                with gzip.open(section.path, 'rb') as stream:
                    for block in iter(lambda: stream.read(65536), b''):
                        emit(block)
            emit(b']')
            for key, value in fixed.items():
                if key not in ('schema', 'render_sha256'):
                    emit(b',' + encode(key) + b':' + encode(value))
            emit(b'}\n')
    assert raw_bytes == audit['totals']['prospective_compact_sidecar_bytes'] == 25228219
    check = roundtrip(temporary, fixed,
                      {'patches': 43207, 'splits': 16331, 'subquads': 37633}, digest.hexdigest(), raw_bytes)
    assert all(sha(ROOT / path) == expected for path, expected in pins.items()), 'frozen_input_changed'
    temporary.rename(OUTPUT)
    for section in (patches, splits):
        section.path.unlink()
    payload_pin = {'path': str(OUTPUT.relative_to(ROOT)), 'gzip_sha256': sha(OUTPUT),
                   'gzip_bytes': OUTPUT.stat().st_size, 'decompressed_sha256': digest.hexdigest(),
                   'decompressed_bytes': raw_bytes}
    # This flush is deliberately before report/doc creation so consumers can use
    # the fixed, validated payload immediately.
    print(json.dumps({'status': 'PAYLOAD_FIXED_AND_ROUNDTRIPPED', **payload_pin}), flush=True)

    report = {'status': 'PASS_FULL_SOURCE_NORMAL_SIDECAR_AUTHORING', 'payload': payload_pin,
              'render_sha256': PIN, 'schema': SCHEMA, 'grid_pitch': P,
              'source_counts': dict(collections.Counter(kind.values())),
              'features_with_treated_faces': 354, 'cached_compiled_rows_scanned': all_compiled,
              'ownership_assigned_counts': dict(assigned), 'totals': dict(total),
              'group_candidate_counts': dict(groupcounts),
              'group_treated_counts': {k: sum(p['treated_unit_faces'] for fid, p in per.items() if kind[fid] == k)
                                       for k in ('old_measured', 'recovered_interval')},
              'per_source': dict(per), 'skip_counts_quad_level': dict(skips),
              'preserved_candidate_unit_face_reasons': dict(cardinal_reasons),
              'preserved_non_source_unit_face_owners_inside_candidate_quads': dict(unsupported_owners),
              'R4_recolor_cells_proven_non_source': r4_changed_cells,
              'R4_recolor_cells_admitted_to_tile_source_set': 0,
              'roundtrip': check, 'all_recorded_source_pins_unchanged': True,
              'actual_checks': {'all_authoring_counts_equal_exact_count_audit': True,
                                'all_354_sources_have_positive_treated_exterior_area': True,
                                'all_candidate_unit_faces_match_current_owner_material_and_exterior': True,
                                'all_splits_exact_disjoint_complete_lattice_cover': True,
                                'all_subquads_same_original_cardinal_plane_winding_and_material': True,
                                'all_patch_and_piece_normals_finite_unit_outward': True,
                                'all_preserved_cardinal_normals_exact_original_cardinal': True,
                                'patch_and_split_target_sets_disjoint_and_unique': True,
                                'compressed_and_decompressed_hashes_pinned': True,
                                'gzip_roundtrip_bytes_and_streaming_JSON_parse': True,
                                'independent_validation_run_by_this_script': False,
                                'adapter_load_exercised_by_this_script': False,
                                'visual_or_production_acceptance': False},
              'geometry_semantics': fixed['geometry_invariant'],
              'classification_support_caveat': 'Conditional source-appearance intervals plus unchanged explicit barrel-profile/height prior; not observed 3D normals or globally registered geometry.',
              'limits': {'address_space_mib': 256, 'CPU_hard_seconds': 45},
              'ownership_elapsed_seconds': ownership_seconds, 'elapsed_seconds': time.monotonic() - start,
              'CPU_seconds': time.process_time() - cpu,
              'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'sampler_calls': 0, 'compiler_calls': 0, 'mesher_calls': 0, 'GUI_calls': 0,
              'render_file_writes': 0, 'full_render_JSON_expanded': False,
              'complete_sidecar_JSON_object_constructed': False, 'uncompressed_sidecar_files_written': 0,
              'temporary_sections_removed': True, 'production_gate_open': False}
    save('sourcepins.json', {'inputs': pins, 'producer': {str(Path(__file__).relative_to(ROOT)): sha(__file__)},
                            'payload': payload_pin, 'all_inputs_unchanged_at_authoring_end': True})
    save('report.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'elapsed_seconds', 'CPU_seconds', 'peak_rss_kib')}
                     | {'payload': payload_pin}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        save('failure.json', {'status': 'FAILED_NO_LIMIT_ESCALATION', 'exception': repr(exc),
                              'traceback': traceback.format_exc(),
                              'CPU_seconds': time.process_time(),
                              'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
        raise
