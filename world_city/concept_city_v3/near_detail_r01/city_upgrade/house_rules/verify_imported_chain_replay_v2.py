"""Independent original-core samples and full stored-face certificate of an import.

Only four imported owned chunks are sampled as QA. Production chunk files are
never regenerated or changed. No imported sampling claim is attributed to v3.
"""
import argparse
import collections
import json
from pathlib import Path
import resource
import signal
import time

import adapter as a
import checkpoint_store
import imported_checkpoint_chain_v2 as imports
import layered_qa as qa
from replay_certificate_qa import quad_owner


def verify(contract_path, output):
    if output.exists():
        raise ValueError('Preserve existing import replay evidence')
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    signal.alarm(600)
    start = time.perf_counter()
    spec = a.load(contract_path)
    readonly=imports._ReadOnlyStore(a.ROOT/spec['original_directory'],spec['original_identity'],spec['original_files'],repository_root=a.ROOT)
    original=readonly.reader
    if imports.producer_segments(original)!=spec['producer_segments']:
        raise ValueError('Pinned actual producer chain changed')
    header = spec['original_identity']['header']
    if original.completed_count != spec['original_count']:
        raise ValueError('Original prefix count changed')
    state = original.load_state()
    summaries = []
    for record in original.load_records():
        summaries.append(record['chunk_stats'])
    first_new=spec['producer_segments'][-1]['first']
    ancestors=[];identity=spec['original_identity']
    while 'import_prefix' in identity:
        info=identity['header']['imported_checkpoint_prefix']['independent_prefix_replay']
        proof_path=a.ROOT/info['path']
        if a.sha(proof_path)!=info['sha256'] or a.load(proof_path).get('pass') is not True:
            raise ValueError('Earlier independently replayed prefix proof changed')
        ancestors.append(info);identity=identity['import_prefix']['original_identity']
    indices = sorted(set([first_new, len(summaries)-1, first_new+(len(summaries)-first_new)//2,
                          max(range(first_new,len(summaries)), key=lambda i: summaries[i]['reference_owned_fine_cells'])]))
    selected = {tuple(summaries[i]['chunk']): i for i in indices}
    surface = {key: qa.Fingerprint() for key in selected}
    all_surface = qa.Fingerprint()
    occupancy = qa.Fingerprint()
    edge = header['chunk_edge_fine_cells']
    halo = header['halo_fine_cells']
    origin = header['grid_origin']
    quads = collections.Counter()
    for index, record in enumerate(original.load_records()):
        summary = summaries[index]
        expected_chunk = tuple(summary['chunk'])
        if summary['owned_bounds_fine'][0] != spec['expected_owned_lows'][index]:
            raise ValueError('Original ownership order changed')
        if len(record['quads']) != summary['quads']:
            raise ValueError('Original quad count changed')
        for material, quad in record['quads']:
            rect = qa._quad_rectangle(quad, origin, .05)
            owner = quad_owner(rect, edge)
            if owner != expected_chunk:
                raise ValueError('Imported quad crosses ownership boundary')
            quads[owner] += 1
            axis, sign, plane, u0, u1, v0, v1 = rect
            for u in range(u0, u1):
                for v in range(v0, v1):
                    face = [axis, sign, plane, u, v, material]
                    all_surface.add(face)
                    if owner in surface:
                        surface[owner].add(face)
    if all_surface.as_dict() != qa._fingerprint(state['face_fingerprint']):
        raise ValueError('Complete imported exterior certificate mismatch')
    from layered_compile_v3_r02 import load_master
    paths = spec['original_identity']['source_paths']
    master_path = a.ROOT / paths['master']
    if a.sha(master_path) != header['authored_master_sha256'] or a.sha(a.core.__file__) != header['compiler_source_sha256']:
        raise ValueError('Original source/reference core mismatch')
    master = load_master(master_path)
    reports = []
    for key, index in selected.items():
        tick = time.perf_counter()
        summary = summaries[index]
        low, high = summary['owned_bounds_fine']
        bounds = {'min': [v-halo for v in low], 'max': [v+halo for v in high]}
        result = a.core.compile_master(master, {'pitch': .05}, cell_bounds=bounds,
                                       max_candidate_cells=5000000, max_output_cells=600000)
        cells = {tuple(row[:3]): row for row in result['cells']}
        occupied = qa.Fingerprint()
        exterior = qa.Fingerprint()
        for row in result['cells']:
            if not all(low[j] <= row[j] < high[j] for j in range(3)):
                continue
            occupied.add(row)
            for axis in range(3):
                for sign in (-1, 1):
                    neighbor = list(row[:3])
                    neighbor[axis] += sign
                    if tuple(neighbor) not in cells:
                        exterior.add([axis, sign, row[axis]+(sign>0), row[(axis+1)%3], row[(axis+2)%3], row[5]])
        checks = {'occupancy_and_semantics_exact': occupied.as_dict() == qa._fingerprint(summary['full_fine_fingerprint']),
                  'material_directed_exterior_exact': exterior.as_dict() == surface[key].as_dict(),
                  'exterior_count_exact': exterior.count == summary['visible_unit_faces'],
                  'quad_count_exact': quads[key] == summary['quads'],
                  'global_constraints_not_claimed': result.get('global_constraints_evaluated') is False}
        reports.append({'chunk_index': index, 'chunk': list(key), 'checks': checks, 'pass': all(checks.values()),
                        'seconds': time.perf_counter()-tick})
        del cells, result
    readonly.check_pins()
    report = {'schema': 'riverstone.imported_prefix.original_reference_replay.v1',
              'pass': all(r['pass'] for r in reports), 'import_contract_path': str(contract_path.relative_to(a.ROOT)),
              'import_contract_sha256': a.sha(contract_path), 'original_files_unchanged': True,
              'imported_chunks': original.completed_count, 'all_imported_quad_ownership_valid': True,
              'all_imported_exterior_fingerprint_exact': True, 'reports': reports,
              'sampled_imported_chunks': len(reports), 'production_chunk_files_regenerated': 0,
              'global_constraint_pass_inferred': False, 'reference_core_sha256': a.sha(a.core.__file__),
              'verifier_sha256': a.sha(__file__), 'elapsed_seconds': time.perf_counter()-start,
              'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'producer_segments':spec['producer_segments'],'earlier_prefix_replay_proofs_preserved':ancestors,'newly_replayed_segment_start':first_new, 'scope': 'All stored imported quads checked against exact ownership and aggregate exterior certificate; four original-core owned samples independently replayed. Remaining imported occupancy relies on its original full-source native compiler certificates.'}
    a.write(output, report)
    print(json.dumps({k: report[k] for k in ('pass', 'imported_chunks', 'sampled_imported_chunks', 'elapsed_seconds', 'max_rss_kib')}), flush=True)
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    x = p.parse_args()
    raise SystemExit(verify(x.contract.resolve(), x.output.resolve()))
