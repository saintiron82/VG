"""Pinned read-only checkpoint prefix plus a separate append-only delta.

No compiler imports, sampling, payload copying, repair, deletion or old writes.
The caller owns invocation/session accounting and the reviewed new producer.
"""
from __future__ import annotations
import copy
import gzip
import hashlib
import json
from pathlib import Path
import stat

import checkpoint_store as checkpoint

SCHEMA = 'riverstone.house_detail.imported_checkpoint_prefix.v1'
HEADER_FIELDS = (
    'asset_key', 'source_id', 'source_revision', 'master_hash',
    'source_master_sha256', 'authored_master_sha256', 'compiler_source_sha256',
    'connectivity_source_sha256', 'polygon_guard_source_sha256',
    'chunk_enumeration_sha256', 'input_catalog_sha256', 'authoring_seed',
    'fine_pitch_m', 'coarse_pitch_m', 'grid_origin', 'chunk_edge_fine_cells',
    'halo_fine_cells', 'materials', 'source_constraints', 'core_policy',
    'cell_row_layout', 'sampling_contract', 'storage_mode', 'chunks', 'chunk_enumeration',
)
SHARED_DEPENDENCIES = ('core', 'adapter', 'mesh', 'render_data',
                       'connected_constraints', 'polygon_crop_guard',
                       'retention', 'chunk_enumeration')
RESOURCE_RULE_FIELDS = frozenset((
    'memory_limit_bytes', 'total_output_budget_bytes', 'wall_time_limit_seconds',
    'max_prepared_plan_bytes_per_pitch', 'shared_output_reservation',
    'imported_checkpoint_prefix',  # Pinned identity/I/O metadata, not geometry.
))
SOURCE_HASH_FIELDS = {'master': 'authored_master_sha256',
                      'source': 'source_master_sha256',
                      'catalog': 'input_catalog_sha256', 'rules': 'layer_rules_sha256'}


def _fail(condition, reason):
    checkpoint._fail(condition, 'Imported prefix: ' + reason)


def _clone(value):
    return copy.deepcopy(value)


def compatibility_header(header):
    """Exact semantic contract; a new producer is deliberately not an old one."""
    _fail(type(header) is dict and all(k in header for k in HEADER_FIELDS),
          'missing semantic header field')
    deps = header.get('replay_dependency_hashes', {})
    _fail(all(k in deps for k in SHARED_DEPENDENCIES), 'missing shared dependency hash')
    return {**{k: _clone(header[k]) for k in HEADER_FIELDS},
            'shared_dependencies': {k: deps[k] for k in SHARED_DEPENDENCIES}}


def geometry_rules(rules):
    """Fail closed on unknown semantic fields; only explicit resource/identity-I/O keys differ."""
    _fail(type(rules) is dict and bool(rules), 'missing geometry rules')
    return {k: _clone(v) for k, v in rules.items() if k not in RESOURCE_RULE_FIELDS}


def file_inventory(directory):
    """For review/contract creation only; production must use a previously pinned map."""
    directory = Path(directory)
    _fail(directory.is_dir() and not directory.is_symlink(), 'invalid original directory')
    result = {}
    for path in sorted(directory.iterdir()):
        _fail(stat.S_ISREG(path.lstat().st_mode), 'nonregular original file')
        raw = checkpoint._read_bytes(path, checkpoint.MAX_STATE_BYTES)
        result[path.name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return result


class _ReadOnlyStore:
    """Use the existing format validators without its writable constructor/lock."""
    def __init__(self, directory, identity, files):
        self.directory = Path(directory)
        self.files = _clone(files)
        self.check_pins()
        reader = checkpoint.Store.__new__(checkpoint.Store)
        reader.directory = self.directory
        reader.identity_bytes = checkpoint._identity(identity)
        reader.identity = _clone(identity)
        reader.identity_sha = checkpoint._sha(reader.identity_bytes)
        reader.identity_digest = reader.identity_sha
        reader.manifest_path = self.directory / 'manifest.json'
        reader._load_manifest()
        reader._check_files()
        self.reader = reader

    def check_pins(self):
        _fail(type(self.files) is dict and 'manifest.json' in self.files, 'missing original file pins')
        for name, pin in self.files.items():
            _fail(type(name) is str and name == Path(name).name and name not in ('.', '..'),
                  'unsafe original file name')
            _fail(type(pin) is dict and set(pin) == {'sha256', 'bytes'}, 'invalid original file pin')
            checkpoint._hash(pin['sha256']); checkpoint._integer(pin['bytes'])
        _fail(file_inventory(self.directory) == self.files, 'original file set, size or SHA changed')


def _fingerprint(value):
    _fail(type(value) is dict and set(value) == {'count', 'xor256', 'sum256'}, 'invalid fingerprint')
    checkpoint._integer(value['count']); checkpoint._hash(value['xor256']); checkpoint._hash(value['sum256'])
    return value['count'], int(value['xor256'], 16), int(value['sum256'], 16)


def _empty_totals():
    return {'occupancy': [0, 0, 0], 'total_fine': 0, 'total_core': 0,
            'candidate_total': 0, 'faces': 0, 'quads': 0}


def _add_summary(totals, summary):
    count, xor, total = _fingerprint(summary['full_fine_fingerprint'])
    _fail(summary.get('expanded_fingerprint') == summary['full_fine_fingerprint'], 'expanded fingerprint mismatch')
    for key in ('reference_owned_fine_cells', 'stored_fine_cells', 'stored_core_cells',
                'near_candidate_cells', 'core_candidate_cells', 'visible_unit_faces', 'quads'):
        checkpoint._integer(summary[key])
    _fail(count == summary['reference_owned_fine_cells'] ==
          summary['stored_fine_cells'] + 8 * summary['stored_core_cells'], 'fine reconstruction count mismatch')
    _fail(summary.get('seam_and_overlap_check') is True, 'unverified chunk seam')
    totals['occupancy'][0] += count; totals['occupancy'][1] ^= xor
    totals['occupancy'][2] = (totals['occupancy'][2] + total) % (1 << 256)
    totals['total_fine'] += summary['stored_fine_cells']; totals['total_core'] += summary['stored_core_cells']
    totals['candidate_total'] += summary['near_candidate_cells'] + summary['core_candidate_cells']
    totals['faces'] += summary['visible_unit_faces']; totals['quads'] += summary['quads']


class ImportedPrefixStore:
    """Store-compatible global view; delta filenames and envelopes stay local."""
    def __init__(self, original_directory, original_identity, original_files,
                 delta_directory, delta_identity, *, expected_owned_lows,
                 expected_compatibility, original_count=99, repository_root=None,
                 budget_check=None):
        self.original_count = checkpoint._integer(original_count, 1)
        self._root = Path(repository_root or Path(__file__).resolve().parent.parents[4]).resolve()
        original = Path(original_directory)
        delta = Path(delta_directory)
        _fail(not original.is_symlink() and not delta.is_symlink(), 'symlink checkpoint directory')
        original = original.resolve(); delta = delta.resolve()
        _fail(original != delta and original not in delta.parents and delta not in original.parents,
              'delta must be a separate nonoverlapping directory')
        self._original = _ReadOnlyStore(original, original_identity, original_files)
        old = self._original.reader
        _fail(old.completed_count == original_count and not old.complete, 'original must be the exact incomplete prefix')
        self._old_identity = _clone(original_identity)
        self._header = self._old_identity['header']
        self._lows = _clone(expected_owned_lows)
        self._compatibility = _clone(expected_compatibility)
        _fail(type(self._compatibility) is dict and set(self._compatibility) == {'header', 'geometry_rules'},
              'invalid semantic compatibility contract')
        _fail(compatibility_header(self._header) == self._compatibility['header'], 'semantic header changed')
        self._edge = checkpoint._integer(self._header['chunk_edge_fine_cells'], 1)
        _fail(self._edge % 2 == 0, 'odd chunk edge')
        _fail(type(self._lows) is list and len(self._lows) == self._header['chunks'] > original_count,
              'invalid total chunk count')
        for point in self._lows:
            checkpoint._point(point)
            _fail(all(x % self._edge == 0 for x in point), 'unaligned chunk ownership')
        _fail(self._lows == sorted(self._lows) and len({tuple(p) for p in self._lows}) == len(self._lows),
              'duplicate or noncanonical chunk plan')
        _fail(self._lows == original_identity['owned_lows'], 'chunk ownership plan changed')
        self._source_pins = self._verify_sources()
        _fail('import_prefix' not in delta_identity, 'caller must not replace import contract')
        _fail(compatibility_header(delta_identity['header']) == self._compatibility['header'],
              'new producer semantic header changed')
        _fail(delta_identity.get('owned_lows') == self._lows, 'new producer ownership plan changed')
        self._producer_metadata = {
            'sampling_mode': 'mixed_original_prefix_and_new_suffix',
            'original': {'global_sequence_start': 0, 'global_sequence_end_exclusive': original_count,
                         'engine_sha256': self._header['layer_engine_sha256'],
                         'sampling_backend': _clone(self._header.get('sampling_backend'))},
            'new': {'global_sequence_start': original_count, 'global_sequence_end_exclusive': len(self._lows),
                    'engine_sha256': delta_identity['header']['layer_engine_sha256'],
                    'sampling_backend': _clone(delta_identity['header'].get('sampling_backend'))},
            'original_payload_copied': False, 'original_chunks_resampled': False,
        }
        for producer in ('original', 'new'):
            checkpoint._hash(self._producer_metadata[producer]['engine_sha256'])
        self._contract = {
            'schema': SCHEMA, 'original_directory': str(original.relative_to(self._root)),
            'original_count': original_count, 'total_chunks': len(self._lows),
            'original_identity': _clone(original_identity),
            'original_identity_sha256': old.identity_sha,
            'original_manifest_file_sha256': original_files['manifest.json']['sha256'],
            'original_last_chain_sha256': old.manifest['entries'][-1]['chain_sha256'],
            'original_files': _clone(original_files), 'source_files': _clone(self._source_pins),
            'compatibility': _clone(self._compatibility),
            'producer_metadata': _clone(self._producer_metadata),
            'delta_local_to_global_offset': original_count,
        }
        self._totals = _empty_totals()
        for sequence, record in enumerate(old.load_records()):
            self._check_record(sequence, record)
            _add_summary(self._totals, record['chunk_stats'])
        old_state = old.load_state()
        self._validate_state(old_state, self._totals, original_count)
        self._original_state = _clone(old_state)
        identity = {**_clone(delta_identity), 'import_prefix': _clone(self._contract)}
        if not (delta / 'manifest.json').exists() and budget_check is not None:
            budget_check(len(checkpoint._encode(identity, checkpoint.MAX_MANIFEST_BYTES // 2)) + 16384)
        # No writable action occurs before every original/compatibility check passes.
        self.delta = checkpoint.Store(delta, identity)
        _fail(self.delta.completed_count <= len(self._lows) - original_count, 'delta exceeds chunk plan')
        for local, record in enumerate(self.delta.load_records()):
            self._check_record(original_count + local, record)
            _add_summary(self._totals, record['chunk_stats'])
        if self.delta.completed_count:
            self._validate_state(self.delta.load_state(), self._totals, self.completed_count)
        _fail(not self.delta.complete or self.completed_count == len(self._lows), 'partial delta marked complete')
        self.directory = delta
        self.manifest_path = self.delta.manifest_path
        self.identity_digest = self.delta.identity_digest
        self.identity_sha = self.delta.identity_sha
        self.identity = _clone(self.delta.identity)

    def _verify_sources(self):
        pins = {}
        for role, field in SOURCE_HASH_FIELDS.items():
            relative = self._old_identity['source_paths'][role]
            path = self._root / relative
            _fail(not Path(relative).is_absolute() and self._root in path.resolve().parents,
                  'unsafe original source path')
            raw = checkpoint._read_bytes(path, checkpoint.MAX_STATE_BYTES)
            _fail(hashlib.sha256(raw).hexdigest() == self._header[field], 'original ' + role + ' hash changed')
            pins[role] = {'path': relative, 'sha256': self._header[field], 'bytes': len(raw)}
            if role == 'rules':
                rules = checkpoint._decode(raw, checkpoint.MAX_STATE_BYTES)
                _fail(geometry_rules(rules) == self._compatibility['geometry_rules'], 'geometry rules changed')
            elif role == 'master':
                payload = gzip.decompress(raw) if path.suffix == '.gz' else raw
                master = checkpoint._decode(payload, checkpoint.MAX_STATE_BYTES)
                _fail(checkpoint._sha(checkpoint._encode(master, checkpoint.MAX_STATE_BYTES)) == self._header['master_hash'],
                      'authored master canonical hash changed')
                _fail(master['id'] == self._header['source_id'] and master['revision'] == self._header['source_revision'] and
                      master.get('grid_origin', [0, 0, 0]) == self._header['grid_origin'] and
                      master['materials'] == self._header['materials'] and
                      master.get('constraints', []) == self._header['source_constraints'], 'master/header semantic mismatch')
        return pins

    def _check_record(self, sequence, record):
        checkpoint._integer(sequence, 0, len(self._lows) - 1)
        checkpoint._record(record)
        _fail(type(record.get('chunk_stats')) is dict and type(record.get('quads')) is list, 'invalid chunk record')
        summary = record['chunk_stats']; lo = self._lows[sequence]; hi = [x + self._edge for x in lo]
        _fail(summary.get('owned_bounds_fine') == [lo, hi] and
              summary.get('chunk') == [x // self._edge for x in lo], 'non-prefix or mismatched chunk ownership')
        _fail(summary.get('quads') == len(record['quads']), 'quad count mismatch')
        for item in record['quads']:
            _fail(type(item) is list and len(item) == 2 and item[0] in self._header['materials'] and
                  type(item[1]) is list and len(item[1]) == 4, 'invalid quad/material')
            for point in item[1]: checkpoint._point(point, integral=False)

    def _validate_state(self, saved, totals, count):
        _fail(type(saved) is dict, 'missing aggregate state')
        checkpoint._record(saved)
        _fail(list(_fingerprint(saved['all_fingerprint'])) == totals['occupancy'], 'aggregate occupancy mismatch')
        _fail(_fingerprint(saved['face_fingerprint'])[0] == totals['faces'], 'aggregate face count mismatch')
        for key in ('total_fine', 'total_core', 'candidate_total'):
            _fail(type(saved[key]) is int and saved[key] == totals[key], 'aggregate ' + key + ' mismatch')
        constraints = {c['id']: c for c in self._header['source_constraints']}
        _fail(type(saved.get('constraints')) is dict and set(saved['constraints']) <= set(constraints),
              'constraint names mismatch')
        for number in saved['constraints'].values(): checkpoint._integer(number)
        expected_connected = {k for k, c in constraints.items() if c['kind'] == 'connected'}
        _fail(type(saved.get('connected')) is dict and set(saved['connected']) == expected_connected,
              'connected constraint names mismatch')
        owners = {tuple(p) for p in self._lows[:count]}
        for key, value in saved['connected'].items():
            # checkpoint._record above already validates/restores the exact DSU.
            _fail(value['total'] == saved['constraints'].get(key, 0), 'connected constraint total mismatch')
            for row in value['boundary']:
                point = row[:3]; lo = tuple((x // self._edge) * self._edge for x in point)
                _fail(lo in owners and any(point[j] in (lo[j], lo[j] + self._edge - 1) for j in range(3)),
                      'connected boundary outside completed ownership')
        checkpoint._integer(saved['sessions_started'], 1)
        _fail(type(saved['elapsed_seconds']) in (float, int) and saved['elapsed_seconds'] >= 0,
              'invalid elapsed time')

    def _check_original(self):
        self._original.check_pins()
        _fail(self._verify_sources() == self._source_pins, 'original source file metadata changed')

    @property
    def completed_count(self): return self.original_count + self.delta.completed_count

    @property
    def complete(self): return self.delta.complete

    @property
    def manifest(self): return self.delta.manifest

    @property
    def import_contract(self): return _clone(self._contract)

    @property
    def producer_metadata(self): return _clone(self._producer_metadata)

    def load_records(self):
        self._check_original()
        yield from self._original.reader.load_records()
        yield from self.delta.load_records()

    def load_state(self):
        self._check_original()
        saved = self.delta.load_state() if self.delta.completed_count else _clone(self._original_state)
        self._validate_state(saved, self._totals, self.completed_count)
        return saved

    def append(self, sequence, chunk_record, state_record, budget_check=None):
        checkpoint._integer(sequence, 0, len(self._lows) - 1)
        _fail(sequence == self.completed_count, 'global append must be sequential')
        self._check_original(); self._check_record(sequence, chunk_record)
        totals = _clone(self._totals); _add_summary(totals, chunk_record['chunk_stats'])
        self._validate_state(state_record, totals, sequence + 1)
        self.delta.append(sequence - self.original_count, chunk_record, state_record, budget_check=budget_check)
        self._totals = totals

    def mark_complete(self, final_stats_path, final_stats_sha, budget_check=None):
        self._check_original()
        _fail(self.completed_count == len(self._lows), 'cannot complete before full global coverage')
        self.delta.mark_complete(final_stats_path, final_stats_sha, budget_check=budget_check)
