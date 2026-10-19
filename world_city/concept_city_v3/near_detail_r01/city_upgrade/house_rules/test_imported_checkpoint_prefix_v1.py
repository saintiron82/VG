"""Tiny synthetic artifact tests; never import a sampler or run a compiler."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import checkpoint_store as checkpoint
from connected_constraints import ConnectedAccumulator
import imported_checkpoint_prefix_v1 as imported


class ImportedPrefixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='import-prefix-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = self.root / 'old'; self.delta = self.root / 'new'
        self.lows = [[0, 0, 0], [2, 0, 0], [4, 0, 0], [6, 0, 0]]
        self.rules = {'fine_pitch_m': .05, 'core_pitch_m': .1, 'chunk_edge_fine_cells': 2,
                      'halo_fine_cells': 2, 'protected_parts': ['door'], 'memory_limit_bytes': 10}
        self.master = {'id': 'fixture', 'revision': 1, 'grid_origin': [0, 0, 0],
                       'materials': {'stone': 'ffffff'}, 'constraints': [
                           {'id': 'present', 'kind': 'nonempty', 'selector': {}},
                           {'id': 'joined', 'kind': 'connected', 'selector': {}}],
                       'assembly_cuts': [{'id': 'untouched-cut'}]}
        def write(name, value):
            path = self.root / name; path.write_text(json.dumps(value)); return hashlib.sha256(path.read_bytes()).hexdigest()
        self.header = {k: 'fixed' for k in imported.HEADER_FIELDS}
        self.header.update(asset_key='fixture', source_id='fixture', source_revision=1,
                           master_hash=checkpoint._sha(checkpoint._encode(self.master, checkpoint.MAX_STATE_BYTES)),
                           authored_master_sha256=write('master.json', self.master),
                           source_master_sha256=write('source.json', {'source': 'fixed'}),
                           input_catalog_sha256=write('catalog.json', {'assets': []}),
                           layer_rules_sha256=write('rules.json', self.rules),
                           layer_engine_sha256='a' * 64,
                           compiler_source_sha256='1' * 64, connectivity_source_sha256='2' * 64,
                           polygon_guard_source_sha256='3' * 64, chunk_enumeration_sha256='4' * 64,
                           authoring_seed=1, fine_pitch_m=.05, coarse_pitch_m=.1, grid_origin=[0, 0, 0],
                           chunk_edge_fine_cells=2, halo_fine_cells=2, materials=self.master['materials'],
                           source_constraints=self.master['constraints'], chunks=4, chunk_enumeration={'scheduled_chunks': 4},
                           cell_row_layout=['x', 'y', 'z', 'instance', 'part', 'material', 'feature'],
                           replay_dependency_hashes={k: '5' * 64 for k in imported.SHARED_DEPENDENCIES})
        self.identity = {'header': self.header, 'owned_lows': self.lows,
                         'source_paths': {k: v + '.json' for k, v in
                                          [('master', 'master'), ('source', 'source'), ('rules', 'rules'), ('catalog', 'catalog')]}}
        self.original = checkpoint.Store(self.old, self.identity)
        self.accumulator = ConnectedAccumulator()
        self.totals = imported._empty_totals()
        self.records = []; self.states = []
        for n in range(4):
            record = self.record(n); self.records.append(record)
            imported._add_summary(self.totals, record['chunk_stats'])
            lo = self.lows[n]; self.accumulator.add_chunk([tuple(lo)], lo, [x + 2 for x in lo])
            count, xor, total = self.totals['occupancy']
            state = {'all_fingerprint': {'count': count, 'xor256': f'{xor:064x}', 'sum256': f'{total:064x}'},
                     'face_fingerprint': {'count': 0, 'xor256': '0' * 64, 'sum256': '0' * 64},
                     'total_fine': n + 1, 'total_core': 0, 'candidate_total': 2 * (n + 1),
                     'constraints': {'present': n + 1, 'joined': n + 1},
                     'connected': {'joined': checkpoint.serialize_connected(self.accumulator)},
                     'mins': [0, 0, 0], 'maxs': [2 * n + 1, 1, 1],
                     'sessions_started': 1 if n < 2 else 2, 'elapsed_seconds': n + 1.}
            self.states.append(state)
            if n < 2: self.original.append(n, record, state)
        self.files = imported.file_inventory(self.old)
        self.new_identity = copy.deepcopy(self.identity)
        self.new_identity['header']['layer_engine_sha256'] = 'b' * 64
        self.new_identity['header']['sampling_backend'] = {'sampler_id': 'fixture_v3'}
        self.compatibility = {'header': imported.compatibility_header(self.new_identity['header']),
                              'geometry_rules': imported.geometry_rules(self.rules)}

    def record(self, n):
        fp = {'count': 1, 'xor256': f'{n + 1:064x}', 'sum256': f'{n + 1:064x}'}
        return {'chunk_stats': {'chunk': [n, 0, 0], 'owned_bounds_fine': [self.lows[n], [x + 2 for x in self.lows[n]]],
                               'reference_owned_fine_cells': 1, 'stored_fine_cells': 1, 'stored_core_cells': 0,
                               'near_candidate_cells': 1, 'core_candidate_cells': 1, 'visible_unit_faces': 0,
                               'quads': 0, 'full_fine_fingerprint': fp, 'expanded_fingerprint': copy.deepcopy(fp),
                               'seam_and_overlap_check': True}, 'quads': []}

    def open(self, **changes):
        options = {'original_directory': self.old, 'original_identity': self.identity,
                   'original_files': self.files, 'delta_directory': self.delta,
                   'delta_identity': self.new_identity, 'expected_owned_lows': self.lows,
                   'expected_compatibility': self.compatibility, 'original_count': 2, 'repository_root': self.root}
        options.update(changes)
        return imported.ImportedPrefixStore(**options)

    def test_reference_prefix_append_reopen_and_complete(self):
        snapshot = {p.name: p.read_bytes() for p in self.old.iterdir()}
        s = self.open(); self.assertEqual(s.completed_count, 2)
        self.assertEqual(list(s.load_records()), self.records[:2]); self.assertEqual(s.load_state(), self.states[1])
        self.assertEqual(list(self.delta.glob('chunk-*.gz')), [])
        s.append(2, self.records[2], self.states[2]); self.assertEqual(s.completed_count, 3)
        self.assertEqual(s.delta.manifest['entries'][0]['sequence'], 0)
        s = self.open(); self.assertEqual(s.load_state(), self.states[2])
        s.append(3, self.records[3], self.states[3]); self.assertEqual(list(s.load_records()), self.records)
        stats = self.root / 'stats.json'; stats.write_text('{}')
        s.mark_complete(stats, hashlib.sha256(stats.read_bytes()).hexdigest()); self.assertTrue(self.open().complete)
        self.assertEqual(snapshot, {p.name: p.read_bytes() for p in self.old.iterdir()})
        self.assertEqual(s.producer_metadata['original']['engine_sha256'], 'a' * 64)
        self.assertEqual(s.producer_metadata['new']['engine_sha256'], 'b' * 64)
        self.assertIn('import_prefix', s.delta.identity)

    def test_original_store_never_constructed_or_opened_for_writing(self):
        original_init = checkpoint.Store.__init__; original_open = Path.open
        def init(instance, directory, identity):
            self.assertNotEqual(Path(directory).resolve(), self.old.resolve()); return original_init(instance, directory, identity)
        def open_path(path, mode='r', *args, **kwargs):
            if self.old in path.parents:
                self.assertFalse(any(x in mode for x in ('w', 'a', '+', 'x')))
            return original_open(path, mode, *args, **kwargs)
        with mock.patch.object(checkpoint.Store, '__init__', init), mock.patch.object(Path, 'open', open_path):
            s = self.open(); s.load_state(); list(s.load_records()); s.append(2, self.records[2], self.states[2])

    def test_every_original_file_is_pinned_even_inactive_state_and_lock(self):
        for name in self.files:
            path = self.old / name; raw = path.read_bytes(); path.write_bytes(raw + b'x')
            try:
                with self.subTest(name=name), self.assertRaises(checkpoint.CheckpointError): self.open()
            finally: path.write_bytes(raw)
        (self.old / 'extra.tmp').write_text('unexpected')
        with self.assertRaises(checkpoint.CheckpointError): self.open()
        self.assertFalse(self.delta.exists())

    def test_live_original_tamper_blocks_delta_append(self):
        s = self.open(); path = self.old / 'state-1.json.gz'; raw = path.read_bytes(); path.write_bytes(raw + b'x')
        with self.assertRaises(checkpoint.CheckpointError): s.append(2, self.records[2], self.states[2])
        self.assertEqual(s.delta.completed_count, 0)

    def test_changed_source_cuts_grid_materials_and_core_rejected(self):
        for field, changed in [('grid_origin', [1, 0, 0]), ('materials', {'stone': '000000'}),
                               ('compiler_source_sha256', '9' * 64), ('source_constraints', []),
                               ('source_master_sha256', '9' * 64), ('halo_fine_cells', 4)]:
            identity = copy.deepcopy(self.new_identity); identity['header'][field] = changed
            with self.subTest(field=field), self.assertRaises(checkpoint.CheckpointError): self.open(delta_identity=identity)
        path = self.root / 'master.json'; master = copy.deepcopy(self.master); master['assembly_cuts'] = []; path.write_text(json.dumps(master))
        with self.assertRaises(checkpoint.CheckpointError): self.open()
        self.assertFalse(self.delta.exists())

    def test_resource_changes_allowed_geometry_changes_blocked(self):
        changed = copy.deepcopy(self.rules); changed.update(memory_limit_bytes=20, shared_output_reservation={'limit': 10},
                                                       imported_checkpoint_prefix={'path': 'contract.json', 'sha256': '1' * 64})
        self.assertEqual(imported.geometry_rules(changed), imported.geometry_rules(self.rules))
        compatibility = copy.deepcopy(self.compatibility); compatibility['geometry_rules']['protected_parts'] = []
        with self.assertRaises(checkpoint.CheckpointError): self.open(expected_compatibility=compatibility)
        unknown = copy.deepcopy(self.rules); unknown['unreviewed_geometry_mode'] = True
        compatibility['geometry_rules'] = imported.geometry_rules(unknown)
        with self.assertRaises(checkpoint.CheckpointError): self.open(expected_compatibility=compatibility)

    def test_gap_duplicate_wrong_global_append_and_full_coverage_gate(self):
        for plan in ([self.lows[0]] * 4, self.lows[::-1], self.lows[:3], self.lows[1:] + [[8, 0, 0]]):
            with self.subTest(plan=plan), self.assertRaises(checkpoint.CheckpointError): self.open(expected_owned_lows=plan)
        s = self.open()
        for n in (0, 1, 3, -1, True):
            with self.subTest(n=n), self.assertRaises(checkpoint.CheckpointError): s.append(n, self.records[2], self.states[2])
        bad = copy.deepcopy(self.records[2]); bad['chunk_stats']['owned_bounds_fine'][0] = [8, 0, 0]
        with self.assertRaises(checkpoint.CheckpointError): s.append(2, bad, self.states[2])
        with self.assertRaises(checkpoint.CheckpointError): s.mark_complete('absent.json', '1' * 64)
        self.assertEqual(s.delta.completed_count, 0)

    def test_bad_aggregate_and_boundary_cannot_commit(self):
        s = self.open()
        for key in ('total_fine', 'candidate_total'):
            state = copy.deepcopy(self.states[2]); state[key] += 1
            with self.subTest(key=key), self.assertRaises(checkpoint.CheckpointError): s.append(2, self.records[2], state)
        state = copy.deepcopy(self.states[2]); state['connected']['joined']['boundary'][-1][:3] = [8, 0, 0]
        with self.assertRaises(checkpoint.CheckpointError): s.append(2, self.records[2], state)
        self.assertEqual(s.delta.completed_count, 0)

    def test_delta_identity_tamper_and_overlap_rejected(self):
        s = self.open(); changed = copy.deepcopy(self.new_identity); changed['header']['layer_engine_sha256'] = 'c' * 64
        with self.assertRaises(checkpoint.CheckpointError): self.open(delta_identity=changed)
        for path in (self.old, self.old / 'delta', self.root):
            with self.subTest(path=path), self.assertRaises(checkpoint.CheckpointError): self.open(delta_directory=path)
        alias = self.root / 'alias'; alias.symlink_to(self.old, target_is_directory=True)
        with self.assertRaises(checkpoint.CheckpointError): self.open(original_directory=alias)

    def test_same_budget_callback_blocks_writes(self):
        def stop(_): raise RuntimeError('budget stop')
        with self.assertRaisesRegex(RuntimeError, 'budget stop'): self.open(budget_check=stop)
        self.assertFalse(self.delta.exists())
        s = self.open()
        with self.assertRaisesRegex(RuntimeError, 'budget stop'): s.append(2, self.records[2], self.states[2], budget_check=stop)
        self.assertEqual(s.delta.completed_count, 0); self.assertEqual(list(self.delta.glob('chunk-*.gz')), [])

    def test_rehashed_broken_chain_still_rejected(self):
        path = self.old / 'manifest.json'; manifest = json.loads(path.read_text())
        manifest['entries'][0]['chain_sha256'] = 'e' * 64
        clean = {k: v for k, v in manifest.items() if k != 'manifest_sha256'}
        manifest['manifest_sha256'] = checkpoint._sha(checkpoint._encode(clean, checkpoint.MAX_MANIFEST_BYTES))
        path.write_bytes(checkpoint._encode(manifest, checkpoint.MAX_MANIFEST_BYTES))
        with self.assertRaises(checkpoint.CheckpointError): self.open(original_files=imported.file_inventory(self.old))
        self.assertFalse(self.delta.exists())

    def test_valid_store_with_nonprefix_records_still_rejected(self):
        other = self.root / 'nonprefix'; writer = checkpoint.Store(other, self.identity)
        writer.append(0, self.records[1], self.states[0]); writer.append(1, self.records[0], self.states[1])
        with self.assertRaises(checkpoint.CheckpointError):
            self.open(original_directory=other, original_files=imported.file_inventory(other))
        self.assertFalse(self.delta.exists())

    def test_delta_crash_preserves_original_and_reports_orphan(self):
        snapshot = imported.file_inventory(self.old); s = self.open()
        with mock.patch.object(s.delta, '_commit', side_effect=OSError('fixture crash')):
            with self.assertRaises(OSError): s.append(2, self.records[2], self.states[2])
        self.assertEqual(imported.file_inventory(self.old), snapshot)
        with self.assertRaises(checkpoint.OrphanedCheckpointError): self.open()

    def test_connected_state_exact_round_trip(self):
        s = self.open(); state = s.load_state()
        restored = checkpoint.restore_connected(state['connected']['joined'])
        self.assertEqual(checkpoint.serialize_connected(restored), self.states[1]['connected']['joined'])
        restored.add_chunk([tuple(self.lows[2])], self.lows[2], [x + 2 for x in self.lows[2]])
        self.assertEqual(checkpoint.serialize_connected(restored), self.states[2]['connected']['joined'])


if __name__ == '__main__': unittest.main()
