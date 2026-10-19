"""Isolated tests only. No compiler import, sampling, or production ledger writes.

Run with python -B test_bounded_gzip_materializer_v1.py --report
  generated/bounded_gzip_materializer_v1.report.json --actual-render PATH
The script limits its own address space to 128 MiB before running any tests.
Temporary fixture books/output are confined to an owned TemporaryDirectory.
"""
import argparse
import ast
import errno
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import resource
import random
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import bounded_gzip_materializer_v1 as materializer
from output_reservations_v3 import ReservationBook, ReservationError

HERE = Path(__file__).resolve().parent
EVIDENCE = []


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def existing_writer(value):
    """Execute the actual existing writer class/body extracted via AST, read-only.

    The parent function/engine is never imported or invoked. Its reserve_bytes
    is replaced only in this isolated reference fixture with a counting callback;
    the exact JSON/TextIO/gzip body and BudgetedWriter come from source.
    """
    source = HERE / 'layered_compile_frontier_v4_r01.py'
    tree = ast.parse(source.read_text())
    writer = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.ClassDef) and node.name == 'BudgetedWriter')
    candidates = [node for node in ast.walk(tree) if isinstance(node, ast.With)
                  and 'gzip.GzipFile' in ast.unparse(node.items[0].context_expr)]
    body = next(node for node in candidates if 'BudgetedWriter(raw)' in ast.unparse(node))
    code = ast.fix_missing_locations(ast.Module(body=[writer, body], type_ignores=[]))
    raw = io.BytesIO()
    calls = []
    namespace = dict(gzip=gzip, io=io, json=json, raw=raw, render=value,
                     reserve_bytes=lambda count: calls.append(count))
    started = time.perf_counter()
    exec(compile(code, str(source), 'exec'), namespace)
    return raw.getvalue(), calls, time.perf_counter() - started


class BoundedMaterializerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bounded-gzip-materializer-v1-')
        self.root = Path(self.temp.name)
        (self.root / 'out').mkdir()
        self.book = ReservationBook(self.root / 'fixture-book.json', self.root,
                                    [self.root / 'out'], 2_000_000, 0, 0)
        self.key = 'fixture'
        self.cap = 1_000_000
        self.book.reserve(self.key, [{'directory': 'out', 'prefix': 'asset.'}],
                          self.cap, {'fixture': 'bounded_gzip_materializer_v1'})
        self.destination = self.root / 'out/asset.render.json.gz.partial'
        self.temporary = self.destination.with_name(self.destination.name + '.tmp')
        self.ledger_hash = sha_file(self.book.path)
        self.value = {'schema': 'fixture', '한글': ['λ😀', '\n', 1, -0.0, True, None],
                      'groups': [{'material': 'oak', 'quads': [[1.1, 2, 3, 4]] * 100}]}

    def tearDown(self):
        self.assertEqual(sha_file(self.book.path), self.ledger_hash, 'Helper must not rewrite the reservation ledger')
        for key in list(self.book._writers):
            self.book.release_writer(key)
        self.temp.cleanup()  # Only owned test fixtures are cleaned, never production.

    def write(self, **changes):
        arguments = dict(compressed_cap_bytes=16384, book=self.book,
                         reservation_key=self.key, headroom_bytes=64)
        arguments.update(changes)
        return materializer.materialize_json_gzip(self.value, self.destination, **arguments)

    def test_source_writer_fixture_bytes_and_semantics(self):
        fixtures = [None, {}, self.value, {'z': -0.0, 'a': 'line\n\r\t"\\', 'list': tuple(range(9000))},
                    {'nonfinite': [float('nan'), float('inf'), -float('inf')]},
                    {'multibyte': '한글🌳é' * 5000}]
        for index, value in enumerate(fixtures):
            with self.subTest(index=index):
                baseline, calls, baseline_seconds = existing_writer(value)
                encoded = materializer.encode_json_gzip(value, compressed_cap_bytes=len(baseline))
                with encoded.view() as view:
                    self.assertEqual(view, baseline)
                    decoded = gzip.decompress(view)
                self.assertEqual(decoded, gzip.decompress(baseline))
                expected = json.dumps(value, separators=(',', ':'), ensure_ascii=False) + '\n'
                self.assertEqual(decoded.decode('utf-8'), expected)
                # Exact decoded text equality implies identical JSON semantics;
                # explicit nonfinite fixture also preserves legacy NaN behavior.
                if index == 4:
                    self.assertTrue(math.isnan(json.loads(decoded)['nonfinite'][0]))
                EVIDENCE.append(dict(fixture=index, compressed_bytes=len(baseline),
                    sha256=sha_bytes(baseline), decoded_sha256=sha_bytes(decoded),
                    existing_budget_check_count=len(calls),
                    existing_empty_write_count=calls.count(0),
                    existing_encoding_seconds=baseline_seconds))

    def test_buffer_rejection_occurs_before_storage_change(self):
        buffer = materializer.BoundedCompressedBuffer(4)
        self.assertEqual(buffer.write(b'ab'), 2)
        backing_id = id(buffer._storage)
        with self.assertRaises(materializer.CompressedBufferLimitError):
            buffer.write(b'cde')
        self.assertEqual(buffer.tell(), 2)
        self.assertEqual(bytes(buffer._storage), b'ab\0\0')
        self.assertEqual(id(buffer._storage), backing_id)
        buffer.write(b'cd')
        with buffer.seal().view() as view:
            self.assertEqual(view, b'abcd')
            self.assertTrue(view.readonly)
        with self.assertRaises(ValueError):
            buffer.write(b'')

    def test_invalid_buffer_caps(self):
        for cap in (-1, 0, True, 1.5, None):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                materializer.encode_json_gzip({}, compressed_cap_bytes=cap)

    def test_cap_rejection_creates_no_output_and_no_precheck(self):
        baseline, _, _ = existing_writer(self.value)
        with self.book.writer(self.key), patch.object(self.book, 'check', wraps=self.book.check) as check:
            with self.assertRaises(materializer.CompressedBufferLimitError):
                self.write(compressed_cap_bytes=len(baseline) - 1)
            check.assert_not_called()
        self.assertEqual(list((self.root / 'out').iterdir()), [])

    def test_single_exact_precheck_atomic_file_and_fsync(self):
        baseline, _, _ = existing_writer(self.value)
        with self.book.writer(self.key), patch.object(self.book, 'check', wraps=self.book.check) as check, \
                patch.object(materializer.os, 'fsync', wraps=os.fsync) as fsync:
            result = self.write()
            check.assert_called_once_with(self.key, len(baseline) + 64)
            self.assertEqual(fsync.call_count, 2)
            self.assertIn(self.key, self.book._writers)
        self.assertEqual(self.destination.read_bytes(), baseline)
        self.assertFalse(self.temporary.exists())
        self.assertEqual(self.book.inspect()['assets'][self.key]['owned_bytes'], len(baseline))
        self.assertEqual(result.compressed_sha256, sha_bytes(baseline))
        self.assertEqual(result.additional_prechecked_bytes, len(baseline) + 64)
        self.assertEqual(result.budget_precheck_count, 1)

    def test_large_payload_one_unbuffered_write_and_temporary_inventory(self):
        self.value = {'deterministic_incompressible': random.Random(0).randbytes(300000).hex()}
        baseline, _, _ = existing_writer(self.value)
        self.assertGreater(len(baseline), 250000)
        real_write = os.write
        def write_and_inspect(fd, data):
            self.assertFalse(self.destination.exists())
            written = real_write(fd, data)
            self.assertEqual(self.book.inspect()['assets'][self.key]['owned_bytes'], len(data))
            return written
        with self.book.writer(self.key), patch.object(self.book, 'check', wraps=self.book.check) as check, \
                patch.object(materializer.os, 'write', side_effect=write_and_inspect) as write:
            result = self.write(compressed_cap_bytes=500000)
            check.assert_called_once_with(self.key, len(baseline) + 64)
            self.assertEqual(write.call_count, 1)
        self.assertEqual(self.destination.read_bytes(), baseline)
        self.assertEqual(result.compressed_bytes, len(baseline))
        self.assertFalse(self.temporary.exists())

    def test_full_temporary_headroom_and_existing_partial_are_counted(self):
        baseline, _, _ = existing_writer(self.value)
        prior = self.root / 'out/asset.previous.failure.partial'
        # All new gzip bytes fit, but preserving the 64-byte headroom does not.
        prior.write_bytes(b'x' * (self.cap - len(baseline) - 63))
        old_hash = sha_file(prior)
        with self.book.writer(self.key), self.assertRaises(ReservationError):
            self.write()
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.temporary.exists())
        self.assertEqual(sha_file(prior), old_hash)
        self.assertEqual(self.book.inspect()['assets'][self.key]['owned_bytes'], prior.stat().st_size)

    def test_global_retained_budget_rejection_before_output(self):
        foreign = self.root / 'out/unowned.previous.partial'
        foreign.write_bytes(b'x' * 1_000_001)
        with self.book.writer(self.key), self.assertRaises(ReservationError):
            self.write()
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.temporary.exists())
        self.assertEqual(foreign.stat().st_size, 1_000_001)

    def test_legacy_retained_limit_rejection_before_output(self):
        baseline, _, _ = existing_writer(self.value)
        with self.book.writer(self.key), patch.object(self.book, 'check', wraps=self.book.check) as check:
            with self.assertRaises(ReservationError):
                self.write(retained_limit_bytes=len(baseline) + 63)
            check.assert_called_once()
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.temporary.exists())

    def test_existing_destination_preserved(self):
        self.destination.write_bytes(b'prior successful/failure evidence')
        with self.book.writer(self.key), patch.object(self.book, 'check', wraps=self.book.check) as check:
            with self.assertRaises(FileExistsError):
                self.write()
            check.assert_not_called()
        self.assertEqual(self.destination.read_bytes(), b'prior successful/failure evidence')
        self.assertFalse(self.temporary.exists())

    def test_existing_temporary_preserved(self):
        self.temporary.write_bytes(b'prior partial failure')
        with self.book.writer(self.key), self.assertRaises(FileExistsError):
            self.write()
        self.assertEqual(self.temporary.read_bytes(), b'prior partial failure')
        self.assertFalse(self.destination.exists())

    def test_missing_writer_lease(self):
        with self.assertRaises(ReservationError):
            self.write()
        self.assertEqual(list((self.root / 'out').iterdir()), [])

    def test_inherited_writer_lease_is_rejected(self):
        with self.book.writer(self.key):
            with patch.object(materializer.os, 'getpid', return_value=-99), self.assertRaises(ReservationError):
                self.write()
        self.assertEqual(list((self.root / 'out').iterdir()), [])

    def test_unowned_temporary_is_rejected(self):
        with self.book.writer(self.key), self.assertRaises(ReservationError):
            self.write(temporary_path=self.root / 'out/.hidden-stage')
        self.assertEqual(list((self.root / 'out').iterdir()), [])

    def test_temporary_outside_tracked_roots_is_rejected(self):
        with self.book.writer(self.key), self.assertRaises(ReservationError):
            self.write(temporary_path=self.root / 'hidden.tmp')
        self.assertFalse((self.root / 'hidden.tmp').exists())

    def test_symlink_destination_is_preserved(self):
        self.destination.symlink_to(self.root / 'missing-target')
        with self.book.writer(self.key), self.assertRaises(ReservationError):
            self.write()
        self.assertTrue(self.destination.is_symlink())
        self.assertFalse(self.temporary.exists())

    def test_short_write_retains_counted_partial_and_no_destination(self):
        real_write = os.write
        with self.book.writer(self.key), patch.object(materializer.os, 'write',
                side_effect=lambda fd, data: real_write(fd, data[:11])):
            with self.assertRaises(materializer.MaterializationError):
                self.write()
        self.assertEqual(self.temporary.stat().st_size, 11)
        self.assertEqual(self.book.inspect()['assets'][self.key]['owned_bytes'], 11)
        self.assertFalse(self.destination.exists())
        with self.book.writer(self.key), self.assertRaises(FileExistsError):
            self.write()
        self.assertEqual(self.temporary.stat().st_size, 11)

    def test_write_error_retains_counted_partial(self):
        real_write = os.write
        def failing_write(fd, data):
            real_write(fd, data[:7])
            raise OSError(errno.ENOSPC, 'injected storage failure')
        with self.book.writer(self.key), patch.object(materializer.os, 'write', side_effect=failing_write):
            with self.assertRaises(OSError):
                self.write()
        self.assertEqual(self.temporary.stat().st_size, 7)
        self.assertEqual(self.book.inspect()['retained_bytes'], 7)
        self.assertFalse(self.destination.exists())

    def test_file_fsync_failure_retains_complete_temporary(self):
        baseline, _, _ = existing_writer(self.value)
        with self.book.writer(self.key), patch.object(materializer.os, 'fsync', side_effect=OSError('injected fsync failure')):
            with self.assertRaises(OSError):
                self.write()
        self.assertEqual(self.temporary.read_bytes(), baseline)
        self.assertFalse(self.destination.exists())

    def test_directory_fsync_failure_preserves_committed_destination(self):
        baseline, _, _ = existing_writer(self.value)
        real_fsync = os.fsync
        count = 0
        def failing_directory_fsync(fd):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('injected directory fsync failure')
            return real_fsync(fd)
        with self.book.writer(self.key), patch.object(materializer.os, 'fsync', side_effect=failing_directory_fsync):
            with self.assertRaises(OSError):
                self.write()
        self.assertEqual(self.destination.read_bytes(), baseline)
        self.assertFalse(self.temporary.exists())

    def test_destination_race_does_not_overwrite_either_file(self):
        baseline, _, _ = existing_writer(self.value)
        real_rename = materializer._rename_noreplace
        def race(function, directory_fd, temporary, destination):
            self.destination.write_bytes(b'race evidence')
            return real_rename(function, directory_fd, temporary, destination)
        with self.book.writer(self.key), patch.object(materializer, '_rename_noreplace', side_effect=race):
            with self.assertRaises(FileExistsError):
                self.write()
        self.assertEqual(self.destination.read_bytes(), b'race evidence')
        self.assertEqual(self.temporary.read_bytes(), baseline)
        self.assertEqual(self.book.inspect()['assets'][self.key]['owned_bytes'],
                         len(baseline) + len(b'race evidence'))

    def test_temporary_race_is_preserved_by_exclusive_create(self):
        real_check = self.book.check
        def check_then_race(key, additional):
            result = real_check(key, additional)
            self.temporary.write_bytes(b'racing temporary evidence')
            return result
        with self.book.writer(self.key), patch.object(self.book, 'check', side_effect=check_then_race):
            with self.assertRaises(FileExistsError):
                self.write()
        self.assertEqual(self.temporary.read_bytes(), b'racing temporary evidence')
        self.assertFalse(self.destination.exists())

    def test_zero_byte_write_retains_empty_failure_file(self):
        with self.book.writer(self.key), patch.object(materializer.os, 'write', return_value=0):
            with self.assertRaises(materializer.MaterializationError):
                self.write()
        self.assertTrue(self.temporary.exists())
        self.assertEqual(self.temporary.stat().st_size, 0)
        self.assertFalse(self.destination.exists())

    def test_unsupported_atomic_rename_preserves_complete_temporary(self):
        baseline, _, _ = existing_writer(self.value)
        with self.book.writer(self.key), patch.object(materializer, '_rename_noreplace',
                side_effect=OSError(errno.ENOSYS, 'unsupported renameat2')):
            with self.assertRaises(OSError):
                self.write()
        self.assertEqual(self.temporary.read_bytes(), baseline)
        self.assertFalse(self.destination.exists())

    def test_invalid_headroom_and_retained_limits(self):
        with self.book.writer(self.key):
            for settings in ({'headroom_bytes': -1}, {'headroom_bytes': True},
                             {'retained_limit_bytes': 0}, {'retained_limit_bytes': True}):
                with self.subTest(settings=settings), self.assertRaises(ValueError):
                    self.write(**settings)
        self.assertEqual(list((self.root / 'out').iterdir()), [])

    def test_encoding_error_creates_no_output(self):
        self.value = {'unsupported': object()}
        with self.book.writer(self.key), self.assertRaises(TypeError):
            self.write()
        self.assertEqual(list((self.root / 'out').iterdir()), [])


def compare_actual_render(path):
    """Read a completed render only; bounded AS applies to parsing/reencoding too."""
    path = Path(path)
    before_stat = path.stat()
    before = sha_file(path)
    record = dict(path=str(path), original_bytes=before_stat.st_size,
                  original_sha256=before, status='NOT_RUN')
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            value = json.load(stream)
        baseline, calls, baseline_seconds = existing_writer(value)
        started = time.perf_counter()
        encoded = materializer.encode_json_gzip(value, compressed_cap_bytes=2 * 1024 * 1024)
        duration = time.perf_counter() - started
        with encoded.view() as view:
            candidate_hash = sha_bytes(view)
            assert view == baseline, 'Existing writer and helper differ on actual render'
            assert candidate_hash == before, 'Reencoded render differs from preserved source'
            decoded_hash = sha_bytes(gzip.decompress(view))
        # No second JSON tree: byte-identical decoded JSON is a stronger semantic
        # identity check. The helper input above is an actual json.load result.
        with gzip.open(path, 'rb') as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(65536), b''):
                digest.update(chunk)
        assert decoded_hash == digest.hexdigest()
        record.update(status='PASS', compressed_bytes_equal=True,
                      decoded_json_bytes_equal=True, decoded_semantics_equal=True,
                      candidate_sha256=candidate_hash, decoded_sha256=decoded_hash,
                      existing_budget_check_count=len(calls), existing_empty_write_count=calls.count(0),
                      existing_encoding_no_budget_scan_seconds=baseline_seconds,
                      helper_encoding_seconds=duration, compressed_cap_bytes=encoded.cap_bytes)
    except MemoryError:
        record.update(status='SKIPPED_MEMORY_LIMIT', reason='Actual JSON tree/reencoding exceeded the enforced 128 MiB address-space cap')
    finally:
        record['source_unchanged'] = sha_file(path) == before and path.stat().st_mtime_ns == before_stat.st_mtime_ns
    assert record['source_unchanged']
    return record



def compare_actual_streaming(path):
    """Identity check without building a large JSON tree.

    This uses the helper's fixed compressed buffer and the exact gzip/TextIO
    settings, streaming already-serialized JSON. It does NOT claim to exercise
    encode_json_gzip/json.dump on the full object when that object exceeds RAM.
    """
    path = Path(path)
    original_stat = path.stat()
    original_hash = sha_file(path)
    buffer = materializer.BoundedCompressedBuffer(2 * 1024 * 1024)
    started = time.perf_counter()
    with gzip.open(path, 'rt', encoding='utf-8') as source:
        with gzip.GzipFile(filename='', mode='wb', fileobj=buffer, mtime=0, compresslevel=5) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8') as stream:
                for text in iter(lambda: source.read(16384), ''):
                    stream.write(text)
    with buffer.seal().view() as view:
        candidate_hash = sha_bytes(view)
        assert candidate_hash == original_hash, 'Streaming recompression changed original bytes'
    unchanged = sha_file(path) == original_hash and path.stat().st_mtime_ns == original_stat.st_mtime_ns
    assert unchanged
    return dict(path=str(path), status='PASS', method='stream original JSON text through bounded buffer and exact gzip/TextIO settings',
                compressed_bytes=original_stat.st_size, sha256=candidate_hash,
                compressed_bytes_equal=True, decoded_semantics_equal=True,
                full_object_json_dump_exercised=False, source_unchanged=unchanged,
                compressed_cap_bytes=buffer.cap_bytes, elapsed_seconds=time.perf_counter() - started)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    parser.add_argument('--actual-render', type=Path, action='append', default=[])
    parser.add_argument('--stream-render', type=Path, action='append', default=[])
    args = parser.parse_args()
    hard_limit = 128 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (hard_limit, hard_limit))
    start = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BoundedMaterializerTests))
    report = dict(schema='riverstone.bounded_gzip_materializer_v1.tests.v1',
                  status='PASS' if result.wasSuccessful() else 'FAIL',
                  test_count=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  address_space_limit_bytes=hard_limit, fixtures=EVIDENCE,
                  implementation_sha256=sha_file(HERE / 'bounded_gzip_materializer_v1.py'),
                  tests_sha256=sha_file(__file__),
                  reference_engine_sha256=sha_file(HERE / 'layered_compile_frontier_v4_r01.py'),
                  reservation_helper_sha256=sha_file(HERE / 'output_reservations_v3.py'),
                  production_ledger_read_or_written=False, production_adoption=False, sampling_performed=False,
                  test_temporary_files='Owned isolated fixture roots only; their books account for all output/partial/temp bytes')
    if result.wasSuccessful():
        report['actual_renders'] = [compare_actual_render(path) for path in args.actual_render]
        report['streaming_renders'] = [compare_actual_streaming(path) for path in args.stream_render]
    report.update(elapsed_seconds=time.perf_counter() - start,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if args.report:
        # Reports are new files only; reruns must choose a fresh report name.
        with args.report.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
