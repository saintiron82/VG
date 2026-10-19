"""Opt-in frontier engine integration evidence, with original queue/compile leases.

Default invocation runs pure/static contracts only. --run-engine-fixtures must be
explicitly authorized at a safe queue boundary. It takes the existing queue.lock;
engines take their existing compile.lock, and independent core QA takes that same
compile lock. No production checkpoint is opened, rewritten, or resampled.
"""
import argparse
import ast
from collections import Counter
from contextlib import contextmanager, redirect_stdout
import copy
import fcntl
import gzip
import io
import itertools
import json
from pathlib import Path
import resource
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

import adapter as a
import checkpoint_store as checkpoint
import connected_frontier_v4 as frontier
from connected_constraints import ConnectedAccumulator
import imported_checkpoint_prefix_v1 as imports
import layered_compile as original
import layered_compile_frontier_v4_r01 as native
import layered_compile_import_frontier_v4_r01 as imported
import layered_qa as qa
import replay_certificate_qa as replay
import verify_imported_prefix_replay_v1 as prefix_replay
from test_bounded_surface_export import source

HERE = Path(__file__).resolve().parent
MEMORY_LIMIT = 268435456
EVIDENCE = {}
RUN_ENGINES = False
FROZEN = {
    Path(a.core.__file__): '2a64ed2cdf43c9adb27a821170192f69fef0153c7be98cc85c903e34ff2a407b',
    HERE / 'layered_compile.py': '5e567fb48a2a5f67bae674adbe8bec990e4d6fa0c8123ec916d1b0a5decc4b33',
    HERE / 'layered_compile_v3_r02.py': '19a749f8336c6b0993a7f8a674d218d82f0301af1477186147886057fd951c98',
    HERE / 'layered_compile_import_v3_r01.py': '9eaf7d8db55778d3647376649ab73cde4941d30daa7d55c4fcb977aedfd72ed2',
    HERE / 'connected_frontier_v4.py': 'fd7315101bd659707e672fc1112bef61439be4690b72cfe7f8352dbc86bfc163',
    HERE / 'connected_constraints.py': 'd6413a71f43b1ad32ba866c878c912db66bca4bf0f8aac846626cc10d940c5a3',
    HERE / 'imported_checkpoint_prefix_v1.py': '0d345f36fe91cf9cb0428ccb63805c3e28a56f48e70ce3c5d0c3aa01a3e72340',
    HERE / 'checkpoint_store.py': '5be4b9508623bee4a11fc097bdb02757a0f01b142b66d5df517730623244233c',
    HERE / 'layered_compile_frontier_v4_r01.py': '5d859e625eaa9dec68d184beeff7dd30e0a990f36533b6ba37f623d517487f17',
    HERE / 'layered_compile_import_frontier_v4_r01.py': 'c2324428f584084a7aa7dc6090f3b3a26912f10a32a85cacdf06ba708d118665',
}


def digest_rows(rows):
    fp = qa.Fingerprint()
    for row in rows:
        fp.add(list(row))
    return fp.as_dict()


def constraints_like_core(checks):
    result = []
    for check in checks:
        row = {key: check[key] for key in ('id', 'kind', 'pass')}
        row['occupied_cells'] = check.get('occupied_cells', check.get('occupied_fine_reference_cells'))
        if check['kind'] == 'connected':
            row['unreached_cells'] = check['unreached_cells']
        result.append(row)
    return result


def all_faces(rows):
    cells = {tuple(row[:3]): row for row in rows}
    result = set()
    for point, row in cells.items():
        for axis in range(3):
            for sign in (-1, 1):
                neighbor = list(point)
                neighbor[axis] += sign
                if tuple(neighbor) not in cells:
                    result.add((axis, sign, point[axis] + (sign > 0),
                                point[(axis + 1) % 3], point[(axis + 2) % 3], row[5]))
    return result


def render_faces(render):
    result = []
    for group in render['groups']:
        for quad in group['quads']:
            axis, sign, plane, u0, u1, v0, v1 = qa._quad_rectangle(quad, render['grid_origin'], .05)
            result.extend((axis, sign, plane, u, v, group['material'])
                          for u in range(u0, u1) for v in range(v0, v1))
    return result


@contextmanager
def compile_lease():
    with (HERE / 'compile.lock').open('a') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lease, fcntl.LOCK_UN)


class PureIntegrationContracts(unittest.TestCase):
    def test_frozen_originals_and_helpers(self):
        for path, expected in FROZEN.items():
            self.assertEqual(a.sha(path), expected, str(path))

    def test_both_engines_preserve_sampling_calls_and_pin_frontier(self):
        for module in (native, imported):
            text = Path(module.__file__).read_text()
            tree = ast.parse(text)
            calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
            self.assertEqual(calls.count('prepared_sampling_v3.compile_prepared'), 2)
            self.assertEqual(calls.count('prepared_sampling_v3.prepare_master'), 2)
            self.assertNotIn('a.core.compile_master', calls)
            self.assertNotIn('connected_constraints.ConnectedAccumulator', calls)
            self.assertIn('connected_frontier_v4.plan_digest(owned_lows, edge)', ast.unparse(tree))
            self.assertIn("'connected_frontier_v4': connected_frontier_v4.__file__", ast.unparse(tree))
            self.assertIn("connected[c['id']].result()", ast.unparse(tree))
            self.assertNotIn("connected[c['id']].accumulator.result()", ast.unparse(tree))
            self.assertIn('checkpoint_store.serialize_connected(value.accumulator)', ast.unparse(tree))
            self.assertIn("'connected_frontier': {key: value.metadata()", ast.unparse(tree))

    def test_native_restore_and_import_adoption_have_distinct_contracts(self):
        normal = ast.unparse(ast.parse(Path(native.__file__).read_text()))
        mixed = ast.unparse(ast.parse(Path(imported.__file__).read_text()))
        self.assertIn('ConnectedFrontierV4.restore_projection', normal)
        self.assertIn("saved['connected_frontier'][key], owned_lows, edge, owned_lows[:resume_start]", normal)
        self.assertIn('frontier_checkpoint_metadata_missing', normal)
        self.assertIn('ConnectedFrontierV4.from_accumulator', mixed)
        self.assertIn("'connected_frontier' not in saved", mixed)
        self.assertIn('import_has_only_one_remaining_historical_session', mixed)
        self.assertIn('a.fail(not resume_checkpoint', mixed)

    def test_legacy_adoption_separate_projection_and_closed_components(self):
        lows = [(0, 0, 0), (4, 0, 0), (8, 0, 0), (12, 0, 0)]
        chunks = [[(1, 1, 1)], [(7, 1, 1)], [(8, 1, 1)], []]
        original_accumulator = ConnectedAccumulator()
        for low, points in zip(lows[:2], chunks[:2]):
            original_accumulator.add_chunk(points, low, [x + 4 for x in low])
        immutable = checkpoint.serialize_connected(original_accumulator)
        result = frontier.ConnectedFrontierV4.from_accumulator(
            original_accumulator, lows, 4, lows[:2], expected_plan_sha256=frontier.plan_digest(lows, 4))
        self.assertEqual(checkpoint.serialize_connected(original_accumulator), immutable)
        self.assertEqual(result.accumulator.sizes, original_accumulator.sizes)
        projection = checkpoint.serialize_connected(result.accumulator)
        metadata = result.metadata()
        self.assertNotIn('connected', metadata)
        restored = frontier.ConnectedFrontierV4.restore_projection(
            projection, metadata, lows, 4, lows[:2], expected_plan_sha256=frontier.plan_digest(lows, 4))
        self.assertEqual(restored.snapshot(), result.snapshot())
        for low, points in zip(lows[2:], chunks[2:]):
            restored.add_chunk(points, low)
            original_accumulator.add_chunk(points, low, [x + 4 for x in low])
        expected = original_accumulator.result()
        expected['retained_boundary_cells'] = 0
        self.assertEqual(restored.result(), expected)
        self.assertEqual(restored.result()['connected_components'], 2)
        self.assertEqual(restored.result()['unreached_cells'], 2)
        self.assertEqual(checkpoint.serialize_connected(original_accumulator)['total'], 3)

    def test_truncated_and_tampered_coverage_fail_closed(self):
        lows = [(0, 0, 0), (4, 0, 0)]
        digest = frontier.plan_digest(lows, 4)
        result = frontier.ConnectedFrontierV4(lows, 4, expected_plan_sha256=digest)
        result.add_chunk([(1, 1, 1)], lows[0])
        self.assertTrue(result.progress()['selected_prefix_connected'])
        self.assertNotIn('pass', result.progress())
        with self.assertRaisesRegex(frontier.FrontierError, 'Incomplete ownership coverage'):
            result.result()
        projection = checkpoint.serialize_connected(result.accumulator)
        for field, replacement in [('owned_lows', [[0, 0, 0]]), ('completed_lows', [list(x) for x in lows]),
                                   ('plan_sha256', '0' * 64), ('edge', 8), ('schema', 'wrong')]:
            metadata = result.metadata()
            metadata[field] = replacement
            with self.subTest(field=field), self.assertRaises(frontier.FrontierError):
                frontier.ConnectedFrontierV4.restore_projection(
                    projection, metadata, lows, 4, lows[:1], expected_plan_sha256=digest)
        with self.assertRaises(frontier.FrontierError):
            frontier.ConnectedFrontierV4.restore_projection(projection, {}, lows, 4, lows[:1], expected_plan_sha256=digest)
        result.add_chunk([], lows[1])
        self.assertTrue(result.result()['pass'])
        self.assertEqual(result.metadata()['completed_lows'], [list(x) for x in lows])


class RealEngineIntegration(unittest.TestCase):
    def setUp(self):
        if not RUN_ENGINES:
            self.skipTest('Real sampling requires explicit safe-boundary authorization')
        self.temporary = tempfile.TemporaryDirectory(prefix='frontier_engine_integration.fixture.', dir=HERE / 'generated')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'outputs'
        self.output.mkdir()
        self.master = source(True)
        self.master['constraints'].append({'id': 'connected_body', 'kind': 'connected', 'selector': {}})
        self.master['constraints'].append({'id': 'connected_window', 'kind': 'connected', 'selector': {'material': 'glass'}})
        self.key = 'frontier_integration_fixture'
        self.source_path = self.root / 'source.json'
        self.catalog = self.root / 'catalog.json'
        self.rules = a.load(HERE / 'layer_rules.v1.json')
        self.rules.update(chunk_edge_fine_cells=4, memory_limit_bytes=MEMORY_LIMIT)
        self.rules['shared_output_reservation'] = {
            'book_path': str((self.root / 'book.json').relative_to(a.ROOT)),
            'retained_roots': [str(self.output.relative_to(a.ROOT)), str((HERE / 'replay_code').relative_to(a.ROOT))],
            'limit_bytes': 10000000, 'asset_cap_bytes': 1000000, 'min_free_disk_bytes': 1073741824}
        self.rules_path = self.root / 'rules.json'
        a.write(self.rules_path, self.rules)
        self.write_source()

    def write_source(self):
        a.write(self.source_path, self.master)
        a.write(self.catalog, {'assets': [{'asset_key': self.key,
            'source_master_path': str(self.source_path.relative_to(a.ROOT)), 'source_sha256': a.sha(self.source_path),
            'emitted_master_path': str(self.source_path.relative_to(a.ROOT)), 'emitted_master_sha256': a.sha(self.source_path)}]})

    def policy(self, name, stop=None):
        data = {'enabled_asset_keys': [self.key], 'max_sessions': 2,
                'per_session_wall_seconds': 900, 'soft_stop_seconds': 840}
        if stop:
            data['fixture_stop_after_chunks'] = stop
        path = self.root / (name + '.json')
        a.write(path, data)
        return path

    def reference(self):
        with compile_lease():
            return a.core.compile_master(self.master, {'pitch': .05})

    def run_capture(self, engine, output, rules=None, policy=None, resume=False):
        actual = engine.prepared_sampling_v3.compile_prepared
        captured = []
        def sample(plan, **kwargs):
            result = actual(plan, **kwargs)
            captured.append({'pitch': plan.pitch, 'bounds': copy.deepcopy(kwargs['cell_bounds']),
                             'rows': copy.deepcopy(result['cells'])})
            return result
        with patch.object(engine.prepared_sampling_v3, 'compile_prepared', side_effect=sample):
            stats = engine.run(self.key, output, rules or self.rules_path, self.catalog, True, policy, resume)
        return stats, captured

    def capture_owned_rows(self, captured):
        rows = []
        for sample in captured:
            if sample['pitch'] != .05:
                continue
            low = [v + 2 for v in sample['bounds']['min']]
            high = [v - 2 for v in sample['bounds']['max']]
            rows.extend(row for row in sample['rows'] if all(low[j] <= row[j] < high[j] for j in range(3)))
        return rows

    def check_final(self, stats, reference, captures, expected_x_lows):
        rows = self.capture_owned_rows(captures)
        actual_lows = [sample['bounds']['min'][0] + 2 for sample in captures if sample['pitch'] == .05]
        self.assertEqual(actual_lows, expected_x_lows)
        expected_rows = [row for row in reference['cells'] if row[0] // 4 * 4 in expected_x_lows]
        self.assertEqual(sorted(rows), sorted(expected_rows))
        expected_faces = all_faces(reference['cells'])
        self.assertEqual(qa._fingerprint(stats['full_fine_fingerprint']), digest_rows(reference['cells']))
        self.assertEqual(qa._fingerprint(stats['fine_face_fingerprint']), digest_rows(expected_faces))
        self.assertEqual(constraints_like_core(stats['constraints']), reference['constraints'])
        self.assertEqual(stats['reference_full_fine_cells'], 80)
        self.assertEqual(len(stats['chunks']), 5)
        self.assertEqual(stats['memory_limit_bytes'], MEMORY_LIMIT)
        with gzip.open(a.ROOT / stats['files']['.render.json']['path'], 'rt') as stream:
            render = json.load(stream)
        faces = render_faces(render)
        self.assertEqual(len(faces), len(set(faces)))
        self.assertEqual(set(faces), expected_faces)
        self.assertEqual(render['materials'], reference['materials'])
        expected_bounds = {'min': [round(min(row[j] for row in reference['cells']) * .05, 8) for j in range(3)],
                           'max': [round((max(row[j] for row in reference['cells']) + 1) * .05, 8) for j in range(3)]}
        self.assertEqual(render['bounds'], expected_bounds)
        self.assertEqual(render['cell_count'], len(reference['cells']))
        lows = [chunk['owned_bounds_fine'][0] for chunk in stats['chunks']]
        for constraint in self.master['constraints']:
            if constraint['kind'] != 'connected':
                continue
            legacy = ConnectedAccumulator()
            for low in lows:
                selected = [tuple(row[:3]) for row in reference['cells']
                            if all(low[j] <= row[j] < low[j] + 4 for j in range(3))
                            and a.core.selector_matches(constraint.get('selector', {}),
                                dict(instance=row[3], component='wall', part=row[4], material=row[5], feature=row[6]))]
                legacy.add_chunk(selected, low, [v + 4 for v in low])
            expected = {'id': constraint['id'], 'kind': 'connected', **legacy.result()}
            expected['retained_boundary_cells'] = 0
            actual = next(row for row in stats['constraints'] if row['id'] == constraint['id'])
            self.assertEqual(actual, expected)
            metadata = stats['connected_frontier']['final'][constraint['id']]
            self.assertEqual(metadata['owned_lows'], lows)
            self.assertEqual(metadata['completed_lows'], lows)
            self.assertEqual(metadata['plan_sha256'], frontier.plan_digest(lows, 4))
            self.assertEqual(metadata['retired_boundary_cells'], len(legacy.boundary))
        self.assertEqual(stats['compiled_header']['connected_frontier']['implementation_sha256'], a.sha(frontier.__file__))
        self.assertIn('connected_frontier_v4', stats['replay_contract']['code_snapshots'])
        phases = stats['phase_measurements']
        self.assertEqual(phases['sampled_chunk_count_with_phase_observations'],
                         3 if 'imported_checkpoint_prefix' in stats else 5)
        self.assertTrue(all(value >= 0 for value in phases['chunk_phase_seconds'].values()))
        self.assertGreaterEqual(phases['final_render_materialization_seconds'], 0)
        self.assertIn('checkpoint', phases['unattributed_scope'])
        with compile_lease(), patch.object(native.prepared_sampling_v3, 'compile_prepared', side_effect=AssertionError('Replay must use original core')):
            replay_report = replay.verify(a.ROOT / stats['files']['.render.json']['path'].replace('.render.json.gz', '.stats.json'), limit=5)
        self.assertTrue(replay_report['pass'])
        self.assertTrue(replay_report['all_chunks_independently_replayed'])
        total_bytes = sum(path.stat().st_size for path in self.root.rglob('*') if path.is_file())
        self.assertLess(total_bytes, 1000000)
        return {'pass': True, 'fixture_source': self.master, 'fixture_source_sha256': a.sha(self.source_path),
                'fine_cells': len(reference['cells']), 'material_cells': dict(Counter(row[5] for row in reference['cells'])),
                'full_semantic_rows_exact': True, 'full_fine_fingerprint': stats['full_fine_fingerprint'],
                'material_exterior_faces_exact': True, 'visible_unit_faces': len(expected_faces),
                'fine_face_fingerprint': stats['fine_face_fingerprint'], 'final_constraints_exact': True,
                'constraints': stats['constraints'], 'frontier_final': stats['connected_frontier']['final'],
                'sampled_new_owned_x_lows': actual_lows, 'independent_replay_all_5_chunks': True,
                'independent_replay_seconds': replay_report['elapsed_seconds'],
                'fixture_retained_bytes': total_bytes, 'memory_limit_bytes': stats['memory_limit_bytes'],
                'phase_measurements': stats.get('phase_measurements')}

    def test_native_soft_stop_projection_resume_exact(self):
        policy = self.policy('native_policy', 3)
        out = self.output / 'native'
        stopped, prefix = self.run_capture(native, out, policy=policy)
        self.assertEqual(stopped['status'], 'PENDING_RESUMABLE_CHECKPOINT')
        self.assertEqual(stopped['completed_chunks'], 3)
        cp = out / (self.key + '.layered.checkpoint')
        manifest = a.load(cp / 'manifest.json')
        saved = checkpoint.Store(cp, manifest['identity']).load_state()
        self.assertEqual(set(saved['connected_frontier']), {'connected_body', 'connected_window'})
        lows = manifest['identity']['owned_lows']
        for key in saved['connected']:
            restored = frontier.ConnectedFrontierV4.restore_projection(saved['connected'][key], saved['connected_frontier'][key],
                lows, 4, lows[:3], expected_plan_sha256=frontier.plan_digest(lows, 4))
            with self.assertRaises(frontier.FrontierError):
                restored.result()
        stats, suffix = self.run_capture(native, out, policy=policy, resume=True)
        self.assertEqual(stats['checkpoint']['resumed_chunks'], 3)
        self.assertEqual(stats['checkpoint']['sessions_started'], 2)
        self.assertEqual([x['bounds']['min'][0] + 2 for x in suffix if x['pitch'] == .05], [12, 16])
        evidence = self.check_final(stats, self.reference(), prefix + suffix, [0, 4, 8, 12, 16])
        evidence.update(native_restore_projection_exercised=True, sessions_started=2,
                        resumed_without_resampling_x_lows=[12, 16], final_stats_sha256=a.sha(out / (self.key + '.layered.stats.json')))
        EVIDENCE['native_resume'] = evidence

    def test_original_prefix_immutable_import_exact(self):
        old_policy = self.policy('old_policy', 2)
        stopped = original.run(self.key, self.output / 'old', self.rules_path, self.catalog, True, old_policy)
        self.assertEqual(stopped['completed_chunks'], 2)
        cp = self.output / 'old' / (self.key + '.layered.checkpoint')
        manifest = a.load(cp / 'manifest.json')
        ledger = self.output / 'old' / (self.key + '.layered.checkpoint_sessions.json')
        pins = imports.file_inventory(cp)
        original_ledger_sha = a.sha(ledger)
        contract = {'original_directory': str(cp.relative_to(a.ROOT)), 'original_identity': manifest['identity'],
            'original_files': pins, 'original_count': 2, 'expected_owned_lows': manifest['identity']['owned_lows'],
            'original_session_ledger': {'path': str(ledger.relative_to(a.ROOT)), 'sha256': original_ledger_sha}}
        contract_path = self.root / 'import.json'
        a.write(contract_path, contract)
        proof = self.root / 'prefix_replay.json'
        with compile_lease():
            self.assertEqual(prefix_replay.verify(contract_path, proof), 0)
        signal.alarm(0)
        rules = copy.deepcopy(self.rules)
        rules['imported_checkpoint_prefix'] = {'path': str(contract_path.relative_to(a.ROOT)), 'sha256': a.sha(contract_path),
            'independent_prefix_replay': {'path': str(proof.relative_to(a.ROOT)), 'sha256': a.sha(proof)}}
        rules_path = self.root / 'import_rules.json'
        a.write(rules_path, rules)
        policy = self.policy('import_policy')
        out = self.output / 'imported'
        stats, captures = self.run_capture(imported, out, rules_path, policy)
        self.assertEqual(len(captures), 6)
        self.assertEqual(imports.file_inventory(cp), pins)
        self.assertEqual(a.sha(ledger), original_ledger_sha)
        self.assertEqual(stats['checkpoint']['imported_complete_chunks'], 2)
        self.assertEqual(stats['checkpoint']['new_delta_chunks'], 3)
        self.assertEqual(stats['checkpoint']['sessions_started'], 2)
        self.assertEqual([row['producer']['producer_id'] for row in stats['chunks']],
                         ['imported_reference_core'] * 2 + ['new_prepared_v3'] * 3)
        with self.assertRaisesRegex(a.UnsupportedSurface, 'import_has_only_one_remaining_historical_session'):
            imported.run(self.key, out, rules_path, self.catalog, True, policy, True)
        evidence = self.check_final(stats, self.reference(), captures, [8, 12, 16])
        evidence.update(original_inventory_unchanged=True, original_ledger_unchanged=True,
                        imported_chunks_resampled=0, original_prefix_files=pins, historical_sessions=2,
                        import_resume_rejected=True, original_ledger_sha256=original_ledger_sha,
                        final_stats_sha256=a.sha(out / (self.key + '.layered.stats.json')))
        EVIDENCE['immutable_import'] = evidence

    def test_incomplete_global_coverage_never_publishes_pass(self):
        actual_add = frontier.ConnectedFrontierV4.add_chunk
        def omit_last(self, points, lo, hi=None):
            if lo[0] == 16:
                return
            return actual_add(self, points, lo, hi)
        out = self.output / 'missing_coverage'
        with patch.object(frontier.ConnectedFrontierV4, 'add_chunk', omit_last):
            with self.assertRaisesRegex(frontier.FrontierError, 'Incomplete ownership coverage'):
                native.run(self.key, out, self.rules_path, self.catalog, True)
        blocked = a.load(out / (self.key + '.layered.blocked.json'))
        self.assertEqual(blocked['completed_chunks'], 5)
        self.assertFalse((out / (self.key + '.layered.stats.json')).exists())
        self.assertFalse((out / (self.key + '.layered.render.json.gz')).exists())
        EVIDENCE['missing_coverage'] = {'pass': True, 'fault': 'Test-only omission of final connectivity add; sampling remains complete',
            'reason': blocked['reason'], 'sampled_chunks': 5, 'final_stats_or_render_published': False}

    def test_missing_nonempty_constraint_never_publishes_pass(self):
        self.master = source(False)
        self.master['constraints'].append({'id': 'connected_body', 'kind': 'connected', 'selector': {}})
        self.write_source()
        out = self.output / 'missing_window'
        with self.assertRaisesRegex(a.UnsupportedSurface, 'layer_global_constraints_failed'):
            native.run(self.key, out, self.rules_path, self.catalog, True)
        blocked = a.load(out / (self.key + '.layered.blocked.json'))
        reference = self.reference()
        self.assertFalse(reference['valid'])
        checks = blocked['details']['details']['checks']
        self.assertEqual(constraints_like_core(checks), reference['constraints'])
        self.assertEqual(blocked['completed_chunks'], 5)
        self.assertFalse((out / (self.key + '.layered.stats.json')).exists())
        self.assertFalse((out / (self.key + '.layered.render.json.gz')).exists())
        EVIDENCE['missing_window'] = {'pass': True, 'reason': blocked['reason'], 'global_checks_match_original_core': True,
                                    'checks': checks, 'sampled_chunks': 5, 'final_stats_or_render_published': False}


def main():
    global RUN_ENGINES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-engine-fixtures', action='store_true')
    parser.add_argument('--proof', type=Path, default=HERE / 'generated/frontier_engine_integration.pure.r01.json')
    args = parser.parse_args()
    RUN_ENGINES = args.run_engine_fixtures
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    suite = unittest.TestLoader().loadTestsFromTestCase(PureIntegrationContracts)
    if RUN_ENGINES:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(RealEngineIntegration))
    start = time.perf_counter()
    stream = io.StringIO()
    with redirect_stdout(stream):
        if RUN_ENGINES:
            with (HERE / 'queue.lock').open('a') as queue:
                fcntl.flock(queue, fcntl.LOCK_EX)
                try:
                    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
                finally:
                    fcntl.flock(queue, fcntl.LOCK_UN)
        else:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {'schema': 'riverstone.frontier_engine_integration.r01', 'pass': result.wasSuccessful(),
              'phase': 'real_engine_and_pure' if RUN_ENGINES else 'pure_static_no_sampling',
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'engine_sampling_performed': RUN_ENGINES, 'production_sampling_performed': False,
              'queue_and_compile_locks_bypassed': False, 'address_space_limit_bytes': MEMORY_LIMIT,
              'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'elapsed_seconds': time.perf_counter() - start,
              'hashes': {str(path.relative_to(a.ROOT)): a.sha(path) for path in
                         [*FROZEN, Path(native.__file__), Path(imported.__file__), Path(__file__)]},
              'evidence': EVIDENCE, 'test_output': stream.getvalue()}
    encoded = json.dumps(report, indent=2) + '\n'
    if len(encoded.encode()) >= 1000000:
        raise ValueError('Integration proof exceeds one megabyte')
    args.proof.write_text(encoded)
    print(json.dumps({key: report[key] for key in ('pass', 'phase', 'tests_run', 'failures', 'errors', 'elapsed_seconds', 'max_rss_kib')}))
    if not result.wasSuccessful():
        print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
