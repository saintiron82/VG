"""Read-only profile of one completed v3 chunk, checked against retained render.

This separate diagnostic never edits a production engine, source, or output.
Preparation is measured separately; cProfile overhead is not production timing.
"""
import argparse
import cProfile
import io
import itertools
import json
from pathlib import Path
import pstats
import resource
import time

import layered_compile_v3_r02 as layer
import layered_qa as qa
from replay_certificate_qa import quad_owner


def run(stats_path, output, index):
    if output.exists():
        raise ValueError('Existing diagnostic evidence preserved')
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = min(268435456, hard) if hard != resource.RLIM_INFINITY else 268435456
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    stats = layer.a.load(stats_path)
    header = stats['compiled_header']
    contract = stats['replay_contract']
    for record in contract['inputs'].values():
        if layer.a.sha(layer.a.ROOT / record['path']) != record['sha256']:
            raise ValueError('Changed source input')
    if layer.a.sha(layer.__file__) != header['layer_engine_sha256']:
        raise ValueError('Profile requires the exact committed engine')
    for record in contract['code_snapshots'].values():
        if layer.a.sha(layer.a.ROOT / record['snapshot_path']) != record['sha256']:
            raise ValueError('Changed immutable code snapshot')
    master = layer.load_master(layer.a.ROOT / contract['inputs']['authored_master']['path'])
    rules = layer.a.load(layer.a.ROOT / contract['inputs']['layer_rules']['path'])
    summary = stats['chunks'][index]
    low, high = summary['owned_bounds_fine']
    edge = header['chunk_edge_fine_cells']
    halo = header['halo_fine_cells']
    origin = header['grid_origin']
    render_record = stats['files']['.render.json']
    render_path = layer.a.ROOT / render_record['path']
    if layer.a.sha(render_path) != render_record['sha256']:
        raise ValueError('Changed retained render')
    render = layer.load_master(render_path)
    expected_quads = [(g['material'], q) for g in render['groups'] for q in g['quads']
                      if quad_owner(qa._quad_rectangle(q, origin, .05), edge) == tuple(summary['chunk'])]
    del render
    phases = {}

    def timed(name, fn):
        wall = time.perf_counter()
        cpu = time.process_time()
        value = fn()
        phases[name] = {'wall_seconds': time.perf_counter() - wall,
                        'cpu_seconds': time.process_time() - cpu}
        return value

    fine_plan, coarse_plan = timed('prepare_full_source_plans_once', lambda: tuple(
        layer.prepared_sampling_v3.prepare_master(master, {'pitch': pitch},
            max_plan_bytes=rules['max_prepared_plan_bytes_per_pitch']) for pitch in (.05, .1)))
    for name, plan in (('fine', fine_plan), ('core', coarse_plan)):
        if plan.plan_key != stats['prepared_plans'][name]['plan_key']:
            raise ValueError('Prepared plan identity changed')
    bounds = {'min': [v-halo for v in low], 'max': [v+halo for v in high]}
    coarse_bounds = {k: [v//2 for v in values] for k, values in bounds.items()}
    budget = {'max_candidate_cells': rules['max_chunk_candidate_cells'],
              'max_output_cells': rules['max_chunk_output_cells']}
    prof = cProfile.Profile()
    wall = time.perf_counter()
    cpu = time.process_time()
    prof.enable()
    fine = timed('prepared_fine_sample', lambda: layer.prepared_sampling_v3.compile_prepared(
        fine_plan, cell_bounds=bounds, **budget))
    coarse = timed('prepared_core_sample', lambda: layer.prepared_sampling_v3.compile_prepared(
        coarse_plan, cell_bounds=coarse_bounds, **budget))
    own, near, core, cells = timed('lossless_layer_split', lambda: layer.split_cells(fine, coarse, low, high, rules))

    def fingerprint(rows):
        fp = layer.Fingerprint()
        for row in rows:
            fp.add(row)
        return fp.value()

    occupancy = timed('owned_occupancy_hash', lambda: fingerprint(own))
    expected_faces = timed('expected_exterior_faces', lambda: layer.expected_faces(own, cells))
    quads, actual = timed('common_mesh_owned_face_extraction', lambda: layer.owned_quads(
        layer.bounded_surface_export_v1.make_bounded_render_data(fine), low, high, rules))
    timed('exterior_hash', lambda: fingerprint([list(face) for face in actual]))

    def expanded():
        yield from near
        for row in core:
            for delta in itertools.product((0, 1), repeat=3):
                yield [*(2*row[j]+delta[j] for j in range(3)), *row[3:]]

    expansion = timed('reconstruction_hash', lambda: fingerprint(expanded()))
    prof.disable()
    elapsed = time.perf_counter() - wall
    cpu_seconds = time.process_time() - cpu
    normalize = lambda rows: sorted(json.dumps(row, sort_keys=True, separators=(',', ':')) for row in rows)
    checks = {
        'owned_occupancy_semantics_exact': occupancy == summary['full_fine_fingerprint'],
        'lossless_reconstruction_exact': expansion == occupancy,
        'directed_exterior_set_exact': expected_faces == actual,
        'exterior_count_exact': len(actual) == summary['visible_unit_faces'],
        'layer_cell_counts_exact': len(near) == summary['stored_fine_cells'] and len(core) == summary['stored_core_cells'],
        'retained_material_quad_payload_exact': normalize(quads) == normalize(expected_quads),
        'candidate_counts_exact': fine['candidate_cells'] == summary['near_candidate_cells'] and coarse['candidate_cells'] == summary['core_candidate_cells'],
        'bounded_constraints_not_global_claim': fine['global_constraints_evaluated'] is False,
    }
    text = io.StringIO()
    pstats.Stats(prof, stream=text).sort_stats('cumulative').print_stats(35)
    report = {
        'schema': 'riverstone.layered_detail.v3_one_chunk_profile.v1',
        'pass': all(checks.values()), 'checks': checks, 'asset_key': stats['asset_key'],
        'chunk_index': index, 'chunk': summary['chunk'], 'owned_cells': len(own), 'quads': len(quads),
        'production_chunk_seconds': summary['seconds'], 'phases': phases,
        'profiled_chunk_wall_seconds': elapsed, 'profiled_chunk_cpu_seconds': cpu_seconds,
        'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'memory_limit_bytes': limit,
        'stats_path': str(stats_path.relative_to(layer.a.ROOT)), 'stats_sha256': layer.a.sha(stats_path),
        'render': render_record, 'layer_engine_sha256': header['layer_engine_sha256'],
        'prepared_plans': stats['prepared_plans'], 'sampling_backend': stats['sampling_backend'],
        'diagnostic_sha256': layer.a.sha(__file__), 'cprofile': text.getvalue(),
        'scope': 'One actual retained chunk only. Full plan preparation measured separately. Profiling adds instrumentation overhead. Global constraint accumulation, checkpoint/reservation I/O and final serialization excluded. No production geometry changed.',
    }
    layer.a.write(output, report)
    print(json.dumps({k: report[k] for k in ('pass', 'asset_key', 'chunk_index', 'profiled_chunk_wall_seconds', 'max_rss_kib', 'phases')}))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stats', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--chunk-index', type=int, required=True)
    x = p.parse_args()
    raise SystemExit(run(x.stats.resolve(), x.output.resolve(), x.chunk_index))
