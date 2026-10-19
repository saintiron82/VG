"""Read-only consumer/regression certificate. Does not run Godot or parse scene.json.

Run with python -B <this file>. Only this directory receives new result files.
The shared regression suite is executed against the frozen producer module, not
whichever implementation happens to be on the Python path at a later date.
"""
import ast
import copy
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock
import numpy as np

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
O = HERE.parent
N = O.parent
ROOT = N.parents[4]
P = O / 'replay_r01'
RUNTIME = P / 'evidence/runtime_r01'
read = lambda p: json.loads(pathlib.Path(p).read_text())

def sha(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def resolve(path):
    path = pathlib.Path(path)
    return path if path.is_absolute() else ROOT / path

def ref(path):
    path = pathlib.Path(path).resolve()
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

D = read(P / 'prepared_production_r01.json')
BASE = read(P / 'prepared.json')
PROD = read(O / 'production_routes_r01.json')
LEDGER = read(O / 'production_profile_ledger_r01.json')
MANIFEST = read(RUNTIME / 'run_manifest.json')
REPORTS = {kind: read(RUNTIME / (kind + '.json')) for kind in ('capsule', 'cart')}
MODULE_REF = PROD['sources']['module']
assert sha(resolve(MODULE_REF['path'])) == MODULE_REF['sha256']
SUPPORT = load_module('route_support_profile', resolve(MODULE_REF['path']))
EXISTING = load_module('frozen_snapshot_profile_regressions', N / 'test_route_support_profile.py')
POSITIVES = {
    'PORT_SHED_0:FULL_MARKET_CHAIN', 'PORT_SHED_0:FULL_MARKET_CHAIN_REVERSE',
    'PORT_SHED_5:FULL_MARKET_CHAIN', 'PORT_SHED_5:FULL_MARKET_CHAIN_REVERSE',
}
NEGATIVES = {'NEGATIVE_UNBRIDGED_RIVER', 'NEGATIVE_ACTUAL_SOLID_WALL'}
EXPECTED_INDEX_SHA = '89aef5e605d68de7b02907bed0651d7fc85098104001cd43470c3502d2f844bb'

# These inputs are fingerprinted before and after all tests. Other scene source
# references are hashed as byte streams, never loaded as a whole scene object.
FROZEN_PATHS = [P / 'prepared_production_r01.json', P / 'prepared.json',
    O / 'production_routes_r01.json', O / 'production_profile_ledger_r01.json',
    resolve(MODULE_REF['path']), O / 'generate_routes.py',
    P / 'Traversal.gd', P / 'CartClearance.gd', N / 'CartClearance.gd',
    ROOT / 'world_city/concept_city_v3/traversal_r5/Traversal.gd',
    RUNTIME / 'run_manifest.json', RUNTIME / 'capsule.json', RUNTIME / 'cart.json']
BEFORE = {str(path): sha(path) for path in FROZEN_PATHS}

class FinalConsumerTests(unittest.TestCase):
    def test_exact_positive_route_objects_and_order(self):
        actual = [r for r in D['routes'] if r['id'] in POSITIVES]
        self.assertEqual(actual, PROD['routes'])
        self.assertEqual({r['id'] for r in actual}, POSITIVES)
        self.assertEqual(len(actual), 4)
        self.assertEqual(len(D['routes']), 6)

    def test_reverse_arrays_are_exact_reversals(self):
        routes = {r['id']: r for r in PROD['routes']}
        for ident in sorted(POSITIVES):
            if ident.endswith('_REVERSE'):
                continue
            forward, reverse = routes[ident], routes[ident + '_REVERSE']
            self.assertEqual(reverse['points'], forward['points'][::-1])
            expected = copy.deepcopy(forward)
            expected.update(id=ident + '_REVERSE', points=forward['points'][::-1])
            self.assertEqual(reverse, expected)

    def test_original_xz_retained_and_profile_ledger_exact(self):
        base = {r['id']: r for r in BASE['routes']}
        generated = {r['id']: r for r in PROD['routes']}
        self.assertEqual(len(LEDGER['routes']), 2)
        for row in LEDGER['routes']:
            ident = row['id']
            self.assertEqual(row['original_xyz_hint'], base[ident]['points'])
            self.assertEqual(row['generated_points'], generated[ident]['points'])
            self.assertTrue(row['reverse_uses_same_profile'])
            self.assertEqual(len(row['waypoints']), len(generated[ident]['points']))
            changes = 0
            for old, new, proof in zip(base[ident]['points'], generated[ident]['points'], row['waypoints']):
                self.assertEqual([old[0], old[2]], [new[0], new[2]])
                self.assertEqual(proof['original_xyz_hint_m'], old)
                self.assertEqual(proof['generated_xyz_m'], new)
                self.assertEqual(proof['surface']['y_m'], new[1])
                owner = proof['surface']['owner_id']
                self.assertEqual(proof['surface']['source_mesh_sha256'], PROD['surface_sources'][owner]['sha256'])
                changes += abs(new[1] - old[1]) > 1e-8
            self.assertGreater(changes, 0)

    def test_negative_inputs_and_collision_fixture_unchanged(self):
        base = {r['id']: r for r in BASE['routes']}
        consumer = {r['id']: r for r in D['routes']}
        for ident in NEGATIVES:
            self.assertEqual(consumer[ident], base[ident])
        for key in ('assets', 'placements', 'buildings', 'cart_fixture', 'implementation_hashes', 'implementation_snapshots', 'coverage'):
            self.assertEqual(D[key], BASE[key], key)

    def test_production_source_bindings_match_consumer(self):
        expected = {
            'production_routes': O / 'production_routes_r01.json',
            'production_profile_ledger': O / 'production_profile_ledger_r01.json',
            'route_support_module': resolve(MODULE_REF['path']),
            'route_support_producer': O / 'generate_routes.py',
        }
        for key, path in expected.items():
            binding = D['sources'][key]
            self.assertEqual(resolve(binding['path']).resolve(), path.resolve())
            self.assertEqual(binding['sha256'], sha(path))
        self.assertEqual(D['sources']['route_support_module'], PROD['sources']['module'])
        self.assertEqual(D['sources']['route_support_producer'], PROD['sources']['producer'])
        self.assertEqual(PROD['sources']['original_prepared']['sha256'], sha(P / 'prepared.json'))
        self.assertEqual(D['sources']['visual_index']['sha256'], EXPECTED_INDEX_SHA)
        self.assertEqual(sha(resolve(D['sources']['visual_index']['path'])), EXPECTED_INDEX_SHA)

    def test_all_source_hashes_and_owner_placement_bindings(self):
        checked = {}
        refs = list(D['sources'].values()) + list(PROD['sources'].values()) + list(PROD['surface_sources'].values())
        for binding in refs:
            path = resolve(binding['path'])
            if str(path) not in checked:
                checked[str(path)] = sha(path)
            self.assertEqual(checked[str(path)], binding['sha256'], str(path))
        for owner, binding in PROD['surface_sources'].items():
            self.assertEqual(binding['placement'], D['placements'][owner])
            asset = D['assets'][binding['placement']['asset_key']]
            self.assertEqual(asset['render_sha256'], binding['sha256'])
            self.assertEqual(resolve(asset['render_path']).resolve(), resolve(binding['path']).resolve())

    def test_implementation_snapshots_match_originals_and_hash_table(self):
        self.assertEqual(set(D['implementation_hashes']), set(D['implementation_snapshots']))
        for key, digest in D['implementation_hashes'].items():
            snapshot = D['implementation_snapshots'][key]
            self.assertEqual(snapshot['sha256'], digest)
            self.assertEqual(sha(resolve(snapshot['path'])), digest)
            self.assertEqual(sha(ROOT / key), digest)

    def test_original_capsule_cart_loader_bytes_unchanged(self):
        originals = {
            'Traversal.gd': ROOT / 'world_city/concept_city_v3/traversal_r5/Traversal.gd',
            'Traversal.tscn': ROOT / 'world_city/concept_city_v3/traversal_r5/Traversal.tscn',
            'CartClearance.gd': N / 'CartClearance.gd',
            'CartClearance.tscn': N / 'CartClearance.tscn',
            'RenderData.gd': ROOT / 'voxel_character/common/preview/RenderData.gd',
        }
        for name, original in originals.items():
            self.assertEqual((P / name).read_bytes(), original.read_bytes(), name)

    def test_analytical_ledger_is_complete_but_not_runtime_certificate(self):
        self.assertEqual(LEDGER['errors'], [])
        for row in LEDGER['routes']:
            guard = row['analytical_support_input_guard']
            self.assertEqual(guard['status'], 'PASS')
            self.assertEqual(guard['failures'], [])
            self.assertGreater(guard['poses_checked'], 0)
            self.assertEqual(guard['support_queries'], 4 * guard['poses_checked'])
            self.assertGreater(guard['minimum_ray_start_above_owned_surface_m'], 0)
            self.assertIn('not a substitute for engine', guard['scope'])

    def test_runtime_manifest_and_reports_bind_exact_consumer(self):
        prepared = P / 'prepared_production_r01.json'
        digest = sha(prepared)
        self.assertEqual(resolve(MANIFEST['prepared_path']).resolve(), prepared.resolve())
        self.assertEqual(MANIFEST['prepared_sha256'], digest)
        self.assertEqual({run['kind'] for run in MANIFEST['runs']}, {'capsule', 'cart'})
        for run in MANIFEST['runs']:
            kind = run['kind']
            report = REPORTS[kind]
            self.assertEqual(run['exit_code'], 0)
            self.assertEqual(run['status'], 'pass')
            self.assertEqual(run['changed_sources'], [])
            self.assertIn('--prepared=' + str(prepared), run['command'])
            self.assertEqual(resolve(run['report_path']).resolve(), (RUNTIME / (kind + '.json')).resolve())
            self.assertEqual(run['report_sha256'], sha(RUNTIME / (kind + '.json')))
            self.assertEqual(run['log_sha256'], sha(RUNTIME / (kind + '.log')))
            self.assertEqual(report['prepared_sha256'], digest)
            self.assertEqual(resolve(report['prepared_path']).resolve(), prepared.resolve())
            self.assertEqual(report['implementation_hashes'], D['implementation_hashes'])
            self.assertEqual(report.get('source_hashes', report.get('sources')), D['sources'])
            self.assertEqual(report['status'], 'pass')
            self.assertEqual(report['errors'], [])
            self.assertEqual(run['summary'], report['summary'])

    def test_capsule_positive_success_is_separate_from_expected_negative_failure(self):
        rows = {r['id']: r for r in REPORTS['capsule']['routes']}
        self.assertEqual(set(rows), POSITIVES | NEGATIVES)
        for ident in POSITIVES:
            row = rows[ident]
            self.assertTrue(row['pass'])
            self.assertEqual(row['status'], 'reached')
            self.assertEqual(row['waypoints_reached'], row['waypoints_total'])
            self.assertEqual(row['not_on_floor_frames'], 0)
            self.assertEqual(row['within_route_teleports'], 0)
        for ident, failure in [('NEGATIVE_UNBRIDGED_RIVER', 'ground_lost'), ('NEGATIVE_ACTUAL_SOLID_WALL', 'blocked')]:
            row = rows[ident]
            self.assertTrue(row['pass'])
            self.assertEqual(row['kind'], 'negative_control')
            self.assertEqual(row['expected_failure'], failure)
            self.assertEqual(row['status'], failure)
            self.assertLess(row['waypoints_reached'], row['waypoints_total'])
        wall = rows['NEGATIVE_ACTUAL_SOLID_WALL']
        self.assertGreater(wall['obstacle_contact_ids'][wall['expected_contact_id']], 0)

    def test_cart_positive_success_is_separate_from_expected_negative_failure(self):
        rows = {r['id']: r for r in REPORTS['cart']['routes']}
        self.assertEqual(set(rows), POSITIVES | NEGATIVES)
        self.assertEqual(REPORTS['cart']['fixture'], D['cart_fixture'])
        for ident in POSITIVES:
            row = rows[ident]
            self.assertTrue(row['pass'])
            self.assertEqual(row['status'], 'clear_supported')
            self.assertIsNone(row['first_failure'])
            self.assertEqual(row['samples'], row['planned_poses'])
            self.assertGreater(row['samples'], 0)
        gap = rows['NEGATIVE_UNBRIDGED_RIVER']
        self.assertTrue(gap['pass'])
        self.assertEqual(gap['status'], 'expected_gap_support_absence')
        self.assertEqual(gap['control_mode'], 'gap_support')
        self.assertEqual(gap['control_support']['failure'], 'support_missing')
        wall = rows['NEGATIVE_ACTUAL_SOLID_WALL']
        self.assertTrue(wall['pass'])
        self.assertEqual(wall['status'], 'expected_native_wall_collision')
        self.assertEqual(wall['control_mode'], 'wall_overlap')
        self.assertIn(wall['expected_contact_id'], wall['control_contact_ids'])
        self.assertEqual(gap['samples'], 0)
        self.assertEqual(wall['samples'], 0)

    def test_frozen_generation_label_is_not_rewritten_as_runtime_pass(self):
        self.assertEqual(PROD['status'], 'GENERATED_NOT_REPLAYED')
        self.assertEqual(PROD['errors'], [])
        self.assertEqual(read(P / 'evidence/preparation.json')['status'], 'PREPARED_NOT_EXECUTED')
        for report in REPORTS.values():
            self.assertEqual(report['status'], 'pass')
            binding = report.get('source_hashes', report.get('sources'))['production_routes']
            self.assertEqual(binding['sha256'], sha(O / 'production_routes_r01.json'))
        # Demonstrate that relabelling a source after certification invalidates its binding.
        changed = copy.deepcopy(PROD)
        changed['status'] = 'PASS'
        changed_sha = hashlib.sha256((json.dumps(changed, indent=2) + '\n').encode()).hexdigest()
        self.assertNotEqual(changed_sha, D['sources']['production_routes']['sha256'])

    def test_single_test_only_waypoint_mutation_is_detected(self):
        changed = copy.deepcopy(D)
        changed['routes'][0]['points'][0][1] += .001
        exact = [r for r in changed['routes'] if r['id'] in POSITIVES] == PROD['routes']
        self.assertFalse(exact)
        self.assertNotEqual(hashlib.sha256((json.dumps(changed, indent=2) + '\n').encode()).hexdigest(), MANIFEST['prepared_sha256'])

class AdditionalSupportRegressions(unittest.TestCase):
    def test_ray_start_exactly_on_surface_rejected(self):
        with self.assertRaisesRegex(SUPPORT.ProfileError, 'RAY_START_NOT_ABOVE'):
            SUPPORT.guard_support_ray(1, SUPPORT.Hit('a', 0, 1.75, 1, 'hash'))

    def test_surface_below_bounded_ray_end_rejected(self):
        with self.assertRaisesRegex(SUPPORT.ProfileError, 'OUTSIDE_RAY_RANGE'):
            SUPPORT.guard_support_ray(3, SUPPORT.Hit('a', 0, 1, 1, 'hash'))

    def test_unknown_owner_rejected(self):
        sampler = SUPPORT.RouteSupportSampler([])
        with self.assertRaisesRegex(SUPPORT.ProfileError, 'UNKNOWN_OWNER'):
            sampler.select(0, 0, ['missing'], 1)

    def test_upper_roof_outside_observed_floor_band_rejected(self):
        sampler = SUPPORT.RouteSupportSampler([SUPPORT.OwnerSurface('roof', EXISTING.plane(5), 'hash')])
        with self.assertRaisesRegex(SUPPORT.ProfileError, 'OWNED_WALKING_SURFACE_MISSING'):
            sampler.select(.5, .5, ['roof'], 1, .15)

    def test_profile_without_observations_rejected(self):
        with self.assertRaisesRegex(SUPPORT.ProfileError, 'NO_OBSERVATIONS'):
            SUPPORT.generate_waypoint_profile([[0, 1, 0], [1, 1, 0]], [], SUPPORT.RouteSupportSampler([]))

    def test_all_six_previously_bad_contract_rays_still_rejected(self):
        diagnostic = read(N / 'port_full_chain/height_hint_diagnostic.json')
        count = 0
        for row in diagnostic['results']:
            for sample in row['supports']:
                if not sample['ray_starts_below_contract']:
                    continue
                surface = sample['exact_contract_surface']
                hit = SUPPORT.Hit('contract', surface['triangle_index'], surface['y_m'], 1, 'source-bound-in-diagnostic')
                with self.assertRaisesRegex(SUPPORT.ProfileError, 'RAY_START_NOT_ABOVE'):
                    SUPPORT.guard_support_ray(row['original_pose_hint_xyz_m'][1], hit)
                count += 1
        self.assertEqual(count, 6)

class MemoryFile:
    def __init__(self, name, writes):
        self.name, self.writes = name, writes
    def __truediv__(self, child):
        return MemoryFile(self.name + '/' + child, self.writes)
    def __str__(self):
        return self.name
    def write_text(self, text):
        self.writes[self.name] = text
        return len(text)

class GeneratorControlFlowRegressions(unittest.TestCase):
    """Execute the actual producer route loop and emission gate with small stubs.
    No source mesh loading or producer top-level side effects are executed.
    """
    def run_producer_nodes(self, generation_error=None, guard_status='PASS'):
        source = O / 'generate_routes.py'
        tree = ast.parse(source.read_text(), filename=str(source))
        loop = next(node for node in tree.body if isinstance(node, ast.For) and ast.unparse(node.iter) == "d['routes']")
        gate = next(node for node in tree.body if isinstance(node, ast.If) and ast.unparse(node.test) == 'not errors')
        emitted = {}
        points = [[0., 1., 0.], [1., 1., 0.]]
        route = {'id': 'POSITIVE', 'points': points, 'placement_ids': ['OWNER'], 'length_m': 1.}
        generate = Mock(return_value=(points, [{'proof': 'stub'}]), side_effect=generation_error)
        guard = Mock(return_value={'status': guard_status, 'failures': [] if guard_status == 'PASS' else [{'code': 'SENTINEL_SUPPORT_FAILURE'}]})
        namespace = {
            'd': {'routes': [route], 'sources': {}, 'assumptions': []},
            'caps': {'POSITIVE': {'position_samples': [{'support_id': 'OWNER'}]}},
            'surfaces': {'OWNER': object()}, 'surface': lambda owner: None,
            'RouteSupportSampler': lambda surfaces: object(), 'generate_waypoint_profile': generate,
            'guard_cart_input_profile': guard, 'ProfileError': SUPPORT.ProfileError,
            'routes': [], 'ledger': [], 'errors': [], 'copy': copy, 'np': np,
            'O': MemoryFile('PRODUCER', emitted), 'P': MemoryFile('CONSUMER', emitted),
            'module_snapshot': pathlib.Path('snapshot.py'), 'pathlib': pathlib,
            '__file__': str(source), 'sha': lambda path: 'stub-only-hash', 'json': json,
        }
        for node in (loop, gate):
            exec(compile(ast.Module(body=[copy.deepcopy(node)], type_ignores=[]), str(source), 'exec'), namespace)
        return namespace, emitted, generate, guard

    def test_guard_failure_records_error_and_never_emits_consumer(self):
        state, emitted, generate, guard = self.run_producer_nodes(guard_status='FAIL')
        self.assertEqual(state['routes'], [])
        self.assertEqual(state['ledger'], [])
        self.assertEqual(state['errors'][0]['code'], 'SUPPORT_PROFILE_GUARD_FAILED')
        self.assertEqual(state['errors'][0]['details']['status'], 'FAIL')
        self.assertEqual(emitted, {})
        generate.assert_called_once()
        guard.assert_called_once()

    def test_generator_exception_records_error_and_never_emits_consumer(self):
        error = SUPPORT.ProfileError('AMBIGUOUS_WALKING_LAYERS', {'sentinel': True})
        state, emitted, generate, guard = self.run_producer_nodes(generation_error=error)
        self.assertEqual(state['routes'], [])
        self.assertEqual(state['ledger'], [])
        self.assertEqual(state['errors'], [{'route': 'POSITIVE', 'code': error.code, 'details': error.details}])
        self.assertEqual(emitted, {})
        guard.assert_not_called()

    def test_success_control_emits_exact_generated_route_and_reverse(self):
        state, emitted, generate, guard = self.run_producer_nodes()
        self.assertEqual(state['errors'], [])
        self.assertEqual(len(state['routes']), 2)
        self.assertEqual(state['routes'][1]['points'], state['routes'][0]['points'][::-1])
        self.assertEqual(set(emitted), {'CONSUMER/prepared_production_r01.json'})
        consumer = json.loads(next(iter(emitted.values())))
        self.assertEqual(consumer['routes'][0], state['routes'][0])
        self.assertIn('production_routes', consumer['sources'])

class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({'test': test.id(), 'status': 'PASS'})
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({'test': test.id(), 'status': 'FAIL', 'detail': self._exc_info_to_string(err, test)})
    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({'test': test.id(), 'status': 'ERROR', 'detail': self._exc_info_to_string(err, test)})

if __name__ == '__main__':
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    for case in (FinalConsumerTests, AdditionalSupportRegressions, GeneratorControlFlowRegressions, EXISTING.ProfileTests):
        suite.addTests(loader.loadTestsFromTestCase(case))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult).run(suite)
    after = {str(path): sha(path) for path in FROZEN_PATHS}
    drift = [path for path in BEFORE if BEFORE[path] != after[path]]
    status = 'PASS' if result.wasSuccessful() and not drift else 'FAIL'
    binding_keys = ('production_routes', 'production_profile_ledger', 'route_support_module', 'route_support_producer', 'visual_index', 'final_finite_patch')
    certificate = {
        'schema': 'riverstone.final_production_consumer_verification.v1',
        'status': status, 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Independent read-only final route input, hash chain, implementation identity, runtime outcome interpretation, and frozen support/producer branch regressions. No Godot run and no whole-scene parsing or geometric source-audit duplication.',
        'prepared': ref(P / 'prepared_production_r01.json'),
        'consumer_bindings': {key: D['sources'][key] for key in binding_keys},
        'producer_bindings': PROD['sources'],
        'runtime_manifest': ref(RUNTIME / 'run_manifest.json'),
        'runtime_reports': {kind: ref(RUNTIME / (kind + '.json')) for kind in REPORTS},
        'original_controllers': {name: ref(P / name) for name in ('Traversal.gd', 'CartClearance.gd', 'RenderData.gd')},
        'results_by_kind': {kind: {
            'positive_successes': [{'id': row['id'], 'pass': row['pass'], 'status': row['status']} for row in report['routes'] if row['id'] in POSITIVES],
            'expected_negative_failures': [{'id': row['id'], 'test_pass': row['pass'], 'observed_failure_status': row['status']} for row in report['routes'] if row['id'] in NEGATIVES],
            'summary': report['summary'],
        } for kind, report in REPORTS.items()},
        'frozen_source_status': PROD['status'],
        'status_interpretation': 'GENERATED_NOT_REPLAYED remains the immutable generation-time label. Only the separately hash-bound run manifest and capsule/cart reports certify successful runtime replay. A passing negative-control test records the expected blocked or unsupported outcome, never route accessibility.',
        'tests_run': result.testsRun, 'tests': result.records,
        'input_hashes_unchanged_before_after': not drift, 'input_drift': drift,
        'limitations': [
            'Existing pre-final test_production_profile.py hardcodes port_full_chain/prepared_production_r04.json. It is historical coverage, not a final-composite certificate; these final consumer tests address that gap.',
            'Production observation source is the explicitly bound pre-final capsule report. Final geometry has its own bound support meshes and the final prepared input is independently engine-replayed.',
            'Producer analytical pose counts are not engine pose counts. PORT_SHED_5 forward analytical guard records 6259 poses; unchanged engine fixture executes 6260, all clear_supported. Runtime certificate remains authoritative.',
            'Producer failure regression checks the actual AST route loop and consumer emission gate with synthetic inputs and in-memory output, not a rerun of all source-mesh generation.',
            'Rigid-envelope support and clearance only; no NPC operating system, suspension, load, traction, or steering-dynamics certification. Historical named market endpoint and separate market joining certificates retain their existing scope.',
        ],
    }
    (HERE / 'verification_r01.json').write_text(json.dumps(certificate, indent=2) + '\n')
    (HERE / 'tests_r01.log').write_text(stream.getvalue())
    print(stream.getvalue())
    print(json.dumps({'status': status, 'tests_run': result.testsRun, 'changed_inputs': drift, 'report': str(HERE / 'verification_r01.json')}, indent=2))
    sys.exit(0 if status == 'PASS' else 1)
