"""Pure checkpoint serialization tests. Never import or invoke the compiler."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import checkpoint_store as checkpoint
from connected_constraints import ConnectedAccumulator


class StoreContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='checkpoint-contract-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'store'
        self.identity = {'source_sha256': '1' * 64, 'master_sha256': '2' * 64,
                         'core_sha256': '3' * 64, 'engine_sha256': '4' * 64,
                         'rules_sha256': '5' * 64, 'catalog_sha256': '6' * 64,
                         'helper_sha256': '7' * 64,
                         'chunk_plan': [[0, 0, 0], [2, 0, 0], [4, 0, 0]],
                         'fine_pitch_m': .05, 'core_pitch_m': .1}

    def chunk(self, sequence=0):
        low = [2 * sequence, 0, 0]; high = [2 * sequence + 2, 2, 2]
        return {'chunk_stats': {'owned_bounds_fine': [low, high], 'reference_owned_fine_cells': 1,
                                'full_fine_fingerprint': {'count': 1, 'sum': '12'}},
                'quads': [['stone', [[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.]]]]}

    def state(self, sequence=0):
        return {'total_fine': sequence + 1, 'total_core': 0, 'total_candidate': 2 * (sequence + 1),
                'mins': [0, 0, 0], 'maxs': [2 * sequence + 2, 2, 2],
                'constraints': {'present': sequence + 1}, 'connected': {}}

    def create(self, count=1):
        store = checkpoint.Store(self.path, self.identity)
        for sequence in range(count):
            store.append(sequence, self.chunk(sequence), self.state(sequence))
        return store

    def test_empty_and_reopen_then_continue_exact(self):
        store = self.create(0)
        self.assertEqual(store.completed_count, 0)
        self.assertIsNone(store.load_state())
        self.assertEqual(list(store.load_records()), [])
        store.append(0, self.chunk(), self.state())
        restored = checkpoint.Store(self.path, copy.deepcopy(self.identity))
        restored.append(1, self.chunk(1), self.state(1))
        self.assertEqual(restored.completed_count, 2)
        self.assertEqual(list(restored.load_records()), [self.chunk(), self.chunk(1)])
        self.assertEqual(restored.load_state(), self.state(1))
        self.assertEqual(restored.identity_digest, store.identity_digest)
        self.assertEqual(restored.manifest_path, self.path / 'manifest.json')

    def test_rotating_states_and_immutable_chunks(self):
        store = self.create()
        original = (self.path / 'chunk-00000000.json.gz').read_bytes()
        for sequence in range(1, 7):
            store.append(sequence, self.chunk(sequence), self.state(sequence))
            store = checkpoint.Store(self.path, self.identity)
            self.assertEqual(store.load_state(), self.state(sequence))
        self.assertEqual(len(list(self.path.glob('state-*.json.gz'))), 2)
        self.assertEqual(len(list(self.path.glob('chunk-*.json.gz'))), 7)
        self.assertEqual((self.path / 'chunk-00000000.json.gz').read_bytes(), original)
        self.assertEqual(len(list(store.load_records())), 7)

    def test_nonsequential_and_repeated_appends_rejected(self):
        store = self.create()
        for sequence in (-1, 0, 2, True, '1', 100000000):
            with self.subTest(sequence=sequence), self.assertRaises(checkpoint.CheckpointError):
                store.append(sequence, self.chunk(), self.state())
        self.assertEqual(store.completed_count, 1)

    def test_changed_or_malformed_identity_rejected(self):
        self.create()
        for field, value in [('source_sha256', '9' * 64), ('helper_sha256', 'z' * 64),
                             ('fine_pitch_m', .025), ('chunk_plan', [[2, 0, 0]])]:
            changed = copy.deepcopy(self.identity); changed[field] = value
            with self.subTest(field=field), self.assertRaises(checkpoint.CheckpointError):
                checkpoint.Store(self.path, changed)

    def test_chunk_and_state_tamper_rejected(self):
        self.create()
        for filename in ('chunk-00000000.json.gz', 'state-0.json.gz'):
            path = self.path / filename; original = path.read_bytes()
            path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            with self.subTest(filename=filename), self.assertRaises(checkpoint.CheckpointError):
                checkpoint.Store(self.path, self.identity)
            path.write_bytes(original)
        checkpoint.Store(self.path, self.identity)

    def test_manifest_tamper_and_unsafe_filename_rejected(self):
        self.create()
        path = self.path / 'manifest.json'
        manifest = json.loads(path.read_text()); manifest['entries'][0]['file'] = '../escape.gz'
        # Even recomputing the manifest integrity hash cannot permit a traversal.
        del manifest['manifest_sha256']
        manifest['manifest_sha256'] = checkpoint._sha(checkpoint._encode(manifest, checkpoint.MAX_MANIFEST_BYTES))
        path.write_bytes(checkpoint._encode(manifest, checkpoint.MAX_MANIFEST_BYTES))
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.Store(self.path, self.identity)

    def test_crash_after_chunk_before_state_reports_orphan(self):
        store = self.create(2)
        original_atomic = checkpoint._atomic
        def interrupted(path, data, replace=False):
            if path.name == 'state-0.json.gz':
                raise OSError('simulated crash before state publication')
            return original_atomic(path, data, replace)
        with mock.patch.object(checkpoint, '_atomic', side_effect=interrupted):
            with self.assertRaises(OSError):
                store.append(2, self.chunk(2), self.state(2))
        with self.assertRaises(checkpoint.OrphanedCheckpointError) as caught:
            checkpoint.Store(self.path, self.identity)
        self.assertIn('chunk-00000002.json.gz', caught.exception.paths)
        evidence = checkpoint.inspect_orphans(self.path, self.identity)
        self.assertEqual(evidence['completed_count'], 2)
        self.assertIsNone(evidence['next_pair'])
        self.assertEqual(store._state(), self.state(1))

    def test_crash_after_state_before_manifest_has_verified_recovery_evidence(self):
        store = self.create(2)
        committed_chunks = {p.name: p.read_bytes() for p in self.path.glob('chunk-*.json.gz')}
        with mock.patch.object(store, '_commit', side_effect=OSError('simulated crash before manifest')):
            with self.assertRaises(OSError):
                store.append(2, self.chunk(2), self.state(2))
        with self.assertRaises(checkpoint.OrphanedCheckpointError):
            checkpoint.Store(self.path, self.identity)
        evidence = checkpoint.inspect_orphans(self.path, self.identity)
        pair = evidence['next_pair']
        self.assertEqual(evidence['completed_count'], 2)
        self.assertEqual(pair['sequence'], 2)
        self.assertEqual(pair['identity_digest'], store.identity_digest)
        self.assertEqual(pair['entry']['previous_chain_sha256'], store.manifest['entries'][-1]['chain_sha256'])
        self.assertEqual(pair['entry']['sha256'], hashlib.sha256((self.path / pair['entry']['file']).read_bytes()).hexdigest())
        self.assertEqual(pair['state']['sha256'], hashlib.sha256((self.path / pair['state']['file']).read_bytes()).hexdigest())
        self.assertEqual(store._state(), self.state(1))
        for name, contents in committed_chunks.items():
            self.assertEqual((self.path / name).read_bytes(), contents)

    def test_tampered_orphan_pair_is_not_recovery_evidence(self):
        store = self.create(2)
        with mock.patch.object(store, '_commit', side_effect=OSError('crash')):
            with self.assertRaises(OSError):
                store.append(2, self.chunk(2), self.state(2))
        path = self.path / 'state-0.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        record['record']['total_fine'] += 1
        raw, _ = checkpoint._gzip_bytes(record, checkpoint.MAX_STATE_BYTES)
        path.write_bytes(raw)
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.inspect_orphans(self.path, self.identity)

    def test_live_state_tamper_prevents_next_commit(self):
        store = self.create()
        path = self.path / 'state-0.json.gz'
        raw = path.read_bytes(); path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaises(checkpoint.CheckpointError):
            store.append(1, self.chunk(1), self.state(1))
        self.assertFalse((self.path / 'chunk-00000001.json.gz').exists())

    def test_orphan_without_initial_manifest_and_temporary_files_reported(self):
        self.path.mkdir(); (self.path / 'manifest.json.tmp').write_text('{}')
        with self.assertRaises(checkpoint.OrphanedCheckpointError) as caught:
            checkpoint.Store(self.path, self.identity)
        self.assertIn('manifest.json.tmp', caught.exception.paths)

    def test_stale_writer_rejected_without_overwriting(self):
        first = self.create(0); second = checkpoint.Store(self.path, self.identity)
        first.append(0, self.chunk(), self.state())
        with self.assertRaises(checkpoint.CheckpointError):
            second.append(0, self.chunk(4), self.state(4))
        self.assertEqual(checkpoint.Store(self.path, self.identity).load_state(), self.state())

    def test_deterministic_gzip_and_mtime_zero(self):
        self.create(2)
        other = checkpoint.Store(Path(self.temp.name) / 'other', self.identity)
        for sequence in range(2):
            other.append(sequence, self.chunk(sequence), self.state(sequence))
        for path in self.path.glob('*.gz'):
            raw = path.read_bytes()
            self.assertEqual(raw[4:8], b'\0' * 4)
            self.assertEqual(raw, (other.directory / path.name).read_bytes())

    def test_cell_arrays_bad_bounds_and_nonfinite_state_rejected_before_writes(self):
        store = self.create(0)
        chunks = [dict(self.chunk(), fine_cells=[[0, 0, 0, 'i']]),
                  {'owned_bounds_fine': [[0, 0, 0], [0, 2, 2]]},
                  {'owned_bounds_fine': [[0, 0], [1, 2, 3]]},
                  {'bounds': {'min': [0, 0, 0], 'max': [1, 2, float('inf')]}}]
        for chunk in chunks:
            with self.assertRaises(checkpoint.CheckpointError):
                store.append(0, chunk, self.state())
        for state in ({'mins': [0, 0, 0], 'maxs': [0, 1, 1]}, {'seconds': float('nan')}, {'bad': (1, 2, 3)}):
            with self.assertRaises(checkpoint.CheckpointError):
                store.append(0, self.chunk(), state)
        self.assertEqual(list(self.path.glob('*.gz')), [])
        store.append(0, {'quads': [], 'chunk_stats': {}}, {'mins': None, 'maxs': None})

    def test_bounded_size_and_gzip_bomb_rejected(self):
        store = self.create(0)
        with mock.patch.object(checkpoint, 'MAX_STATE_BYTES', 128):
            with self.assertRaises(checkpoint.CheckpointError):
                store.append(0, self.chunk(), {'large': 'x' * 129})
        self.assertEqual(list(self.path.glob('*.gz')), [])
        raw = gzip.compress(b'x' * 4096, mtime=0)
        path = Path(self.temp.name) / 'bomb.gz'; path.write_bytes(raw)
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint._read_gzip(path, {'sha256': hashlib.sha256(raw).hexdigest(),
                                       'content_sha256': '1' * 64}, 1024)

    def test_budget_callback_rejects_without_writes_and_receives_peak_bytes(self):
        store = self.create(2)
        before = {p.name: p.read_bytes() for p in self.path.iterdir()}
        received = []
        def reject(additional_peak_bytes):
            received.append(additional_peak_bytes)
            raise ValueError('shared output budget exceeded')
        with self.assertRaisesRegex(ValueError, 'shared output budget'):
            store.append(2, self.chunk(2), self.state(2), budget_check=reject)
        self.assertGreater(received[0], 0)
        self.assertEqual(store.completed_count, 2)
        self.assertEqual({p.name: p.read_bytes() for p in self.path.iterdir()}, before)
        self.assertEqual(checkpoint.Store(self.path, self.identity).completed_count, 2)
        store.append(2, self.chunk(2), self.state(2), budget_check=received.append)
        exact_peak = sum((self.path / name).stat().st_size for name in
                         ('chunk-00000002.json.gz', 'state-0.json.gz', 'manifest.json'))
        self.assertEqual(received, [exact_peak, exact_peak])

    def test_mark_complete_pins_stats_and_blocks_append(self):
        store = self.create()
        path = Path(self.temp.name) / 'final.stats.json'; path.write_text('{"status":"PASS"}')
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(checkpoint.CheckpointError):
            store.mark_complete(path, '0' * 64)
        store.mark_complete(path, sha)
        restored = checkpoint.Store(self.path, self.identity)
        self.assertTrue(restored.complete)
        restored.mark_complete(path, sha)
        with self.assertRaises(checkpoint.CheckpointError):
            restored.append(1, self.chunk(1), self.state(1))

    def test_completion_budget_callback_reserves_whole_manifest_before_write(self):
        store = self.create(2)
        path = Path(self.temp.name) / 'final.stats.json'; path.write_text('{"status":"PASS"}')
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        before = {p.name: p.read_bytes() for p in self.path.iterdir()}
        received = []
        def reject(additional_peak_bytes):
            received.append(additional_peak_bytes)
            raise ValueError('completion budget exceeded')
        with self.assertRaisesRegex(ValueError, 'completion budget'):
            store.mark_complete(path, sha, budget_check=reject)
        self.assertFalse(store.complete)
        self.assertEqual({p.name: p.read_bytes() for p in self.path.iterdir()}, before)
        self.assertFalse(checkpoint.Store(self.path, self.identity).complete)
        store.mark_complete(path, sha, budget_check=received.append)
        self.assertEqual(received, [store.manifest_path.stat().st_size] * 2)
        self.assertTrue(checkpoint.Store(self.path, self.identity).complete)

    def test_symlink_chunk_rejected(self):
        store = self.create()
        original = self.path / 'chunk-00000000.json.gz'
        moved = Path(self.temp.name) / 'external.gz'; original.rename(moved)
        original.symlink_to(moved)
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.Store(self.path, self.identity)


class ConnectivitySerializationContracts(unittest.TestCase):
    def populated(self):
        accumulator = ConnectedAccumulator()
        accumulator.add_chunk([(0, 0, 0), (1, 0, 0), (0, 2, 0)], [0, 0, 0], [2, 3, 2])
        return accumulator

    def test_empty_roundtrip(self):
        original = ConnectedAccumulator()
        self.assertEqual(checkpoint.restore_connected(checkpoint.serialize_connected(original)).result(), original.result())

    def test_roundtrip_exact_after_adding_adjacent_chunk(self):
        original = self.populated()
        saved = checkpoint.serialize_connected(original)
        restored = checkpoint.restore_connected(json.loads(json.dumps(saved)))
        self.assertEqual(restored.parents, original.parents)
        self.assertEqual(restored.sizes, original.sizes)
        self.assertEqual(restored.boundary, original.boundary)
        points = [(2, 0, 0), (2, 1, 0), (2, 2, 0), (3, 2, 0)]
        for state in (original, restored):
            state.add_chunk(points, [2, 0, 0], [4, 3, 2])
        self.assertEqual(restored.result(), original.result())
        self.assertEqual(checkpoint.serialize_connected(restored), checkpoint.serialize_connected(original))

    def test_roundtrip_union_and_first_node_preserved(self):
        original = ConnectedAccumulator()
        original.add_chunk([(0, 0, 0), (0, 2, 0)], [0, 0, 0], [1, 3, 1])
        original.add_chunk([(1, 0, 0), (1, 1, 0), (1, 2, 0)], [1, 0, 0], [2, 3, 1])
        restored = checkpoint.restore_connected(checkpoint.serialize_connected(original))
        self.assertEqual(restored.result(), original.result())
        self.assertTrue(restored.result()['pass'])

    def test_malformed_dsu_bounds_and_totals_rejected(self):
        good = checkpoint.serialize_connected(self.populated())
        changes = [
            {'parents': [1, 0]}, {'parents': [-1, 1]}, {'parents': [2, 1]},
            {'sizes': [999, 1]}, {'total': good['total'] + 1},
            {'first_point': [0, 0]}, {'first_node': 999}, {'peak_local_cells': 0},
            {'max_boundary_cells': 0}, {'boundary': [[0, 0, 0, 999]]},
            {'boundary': [[0, 0, 0, 0], [0, 0, 0, 0]]},
            {'boundary': [[0, 0, 0, True]]}, {'first_point': [float('nan'), 0, 0]},
        ]
        for change in changes:
            malformed = copy.deepcopy(good); malformed.update(change)
            with self.subTest(change=change), self.assertRaises(checkpoint.CheckpointError):
                checkpoint.restore_connected(malformed)

    def test_serialization_does_not_mutate_live_dsu(self):
        original = self.populated()
        before = copy.deepcopy(original.__dict__)
        checkpoint.serialize_connected(original)
        self.assertEqual(original.__dict__, before)


if __name__ == '__main__':
    unittest.main()
