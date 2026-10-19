"""Opt-in, bounded gzip JSON materialization. Not wired into any compiler.

The encoding is exactly the final-render encoding in
layered_compile_frontier_v4_r01.py: GzipFile(filename='', mtime=0, level=5),
TextIOWrapper(encoding='utf-8'), compact json.dump(ensure_ascii=False), newline.
In particular, insertion order and json.dump's default allow_nan=True are kept.

The caller must already own an active output_reservations_v3 writer lease. This
module never reserves/releases a lease, rewrites the ledger, creates directories,
removes failed files, or overwrites a destination. The one book.check() reserves
all new compressed bytes plus explicit headroom before any output is created.
Both temporary and destination paths must belong to that reservation. A Linux
renameat2(RENAME_NOREPLACE) commits one inode atomically, without a second copy.

Use retained_limit_bytes to enforce an additional legacy total-output limit
against the SAME tracked-root inventory returned by book.check(). The caller
must ensure that book.roots includes every directory in that legacy limit.
No production integration, source changes, or timing-speedup claim is implied.
"""
from dataclasses import dataclass
import ctypes
import errno
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time

from output_reservations_v3 import ReservationError


class CompressedBufferLimitError(ValueError):
    """A compressed write was rejected before touching or enlarging storage."""


class MaterializationError(OSError):
    """Output failed; any created temporary/destination is retained as evidence."""


class BoundedCompressedBuffer:
    """Fixed-capacity storage; write checks happen before changing its contents.

    There is no BytesIO/bytearray growth or capacity over-allocation on write.
    The backing bytearray is allocated once at exactly cap_bytes logical bytes.
    Python object overhead, zlib's working memory, TextIO buffering, individual
    JSON token allocations, and the caller-owned JSON object are outside this
    compressed-payload cap. This is not a whole-process memory limiter.
    """
    def __init__(self, cap_bytes):
        if type(cap_bytes) is not int or cap_bytes <= 0:
            raise ValueError('compressed_cap_bytes must be a positive integer')
        self.cap_bytes = cap_bytes
        self._storage = bytearray(cap_bytes)
        self._used = 0
        self._sealed = False

    def write(self, data):
        if self._sealed:
            raise ValueError('Compressed buffer is sealed')
        with memoryview(data) as source:
            if source.ndim != 1 or source.itemsize != 1 or not source.contiguous:
                raise TypeError('Compressed writes must be contiguous byte data')
            count = source.nbytes
            end = self._used + count
            if end > self.cap_bytes:
                raise CompressedBufferLimitError(
                    f'Compressed buffer cap {self.cap_bytes} would be exceeded '
                    f'by write ending at {end}')
            # Equal-size slice assignment through memoryview cannot resize.
            with memoryview(self._storage) as target:
                target[self._used:end] = source
            self._used = end
            return count

    def tell(self):
        return self._used

    def flush(self):
        return None

    def seal(self):
        self._sealed = True
        return self

    def view(self):
        if not self._sealed:
            raise ValueError('Seal the compressed buffer before reading it')
        return memoryview(self._storage)[:self._used].toreadonly()


def encode_json_gzip(value, *, compressed_cap_bytes):
    """Encode in RAM only, preserving the existing final-render byte contract."""
    buffer = BoundedCompressedBuffer(compressed_cap_bytes)
    with gzip.GzipFile(filename='', mode='wb', fileobj=buffer,
                       mtime=0, compresslevel=5) as compressed:
        with io.TextIOWrapper(compressed, encoding='utf-8') as stream:
            json.dump(value, stream, separators=(',', ':'), ensure_ascii=False)
            stream.write('\n')
    return buffer.seal()


@dataclass(frozen=True)
class MaterializationResult:
    destination: str
    temporary_path: str
    compressed_bytes: int
    compressed_sha256: str
    compressed_cap_bytes: int
    additional_prechecked_bytes: int
    budget_precheck_count: int
    gzip_seconds: float
    write_commit_seconds: float


def _assert_writer_lease(book, key):
    # ReservationBook v3 has no public lease-inspection method. Check the same
    # PID-bound token its check() uses, and reject an externally closed handle.
    entry = book._writers.get(key)
    if entry is None or entry[1] != os.getpid() or entry[0].closed:
        raise ReservationError('Materialization requires the caller-held writer lease')


def _owned(path, root, scopes):
    for scope in scopes:
        directory = root / scope['directory']
        if path.is_relative_to(directory):
            parts = path.relative_to(directory).parts
            if parts and (not scope['prefix'] or parts[0].startswith(scope['prefix'])):
                return True
    return False


def _absolute_without_symlinks(path):
    absolute = Path(os.path.abspath(os.fspath(path)))
    # Includes the basename: even a broken pre-existing symlink is rejected.
    if absolute.resolve() != absolute or any(p.is_symlink() for p in [absolute, *absolute.parents]):
        raise ReservationError('Symlink paths are not valid materialization evidence')
    return absolute


def _rename_function():
    if not sys.platform.startswith('linux'):
        raise NotImplementedError('No-clobber atomic materialization requires Linux renameat2')
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, 'renameat2', None)
    if function is None:
        raise NotImplementedError('libc renameat2 is required; no clobbering fallback is allowed')
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                        ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    return function


def _rename_noreplace(function, directory_fd, temporary_name, destination_name):
    if function(directory_fd, os.fsencode(temporary_name), directory_fd,
                os.fsencode(destination_name), 1) != 0:  # RENAME_NOREPLACE
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), destination_name)


def materialize_json_gzip(value, destination, *, compressed_cap_bytes,
                          book, reservation_key, headroom_bytes=65536,
                          retained_limit_bytes=None, temporary_path=None):
    """Atomically create a new gzip JSON file under an existing writer lease.

    The default temp is destination.name + '.tmp', in the same directory and
    reservation scope. Existing files (including symlinks and failed temps) are
    rejected, never cleaned. Short writes are failures, not hidden retries; their
    partial file is retained. A failed final directory fsync leaves the complete
    destination in place and raises, so callers must inspect rather than retry.

    One budget precheck charges compressed_size + headroom_bytes. Existing
    partial/temp files already appear in the book's retained inventory. Atomic
    no-replace rename adds zero bytes, so no 2x hard-link/copy staging is needed.
    This synchronous call assumes the caller does not release its lease or mutate
    its reservation/path tree concurrently. Noncooperating external file writers
    are outside ReservationBook's concurrency contract.
    """
    if type(headroom_bytes) is not int or headroom_bytes < 0:
        raise ValueError('headroom_bytes must be a nonnegative integer')
    if retained_limit_bytes is not None and (type(retained_limit_bytes) is not int or retained_limit_bytes <= 0):
        raise ValueError('retained_limit_bytes must be a positive integer')
    _assert_writer_lease(book, reservation_key)
    record = book.record(reservation_key)
    if record is None or record['state'] != 'ACTIVE' or record['enforcement'] != 'prewrite_required':
        raise ReservationError('An active, enforcing output reservation is required')
    destination = _absolute_without_symlinks(destination)
    temporary = _absolute_without_symlinks(
        temporary_path if temporary_path is not None else destination.with_name(destination.name + '.tmp'))
    if destination == temporary or destination.parent != temporary.parent:
        raise ReservationError('A distinct temporary must be in the destination directory')
    if not destination.parent.is_dir():
        raise FileNotFoundError(errno.ENOENT, 'Destination directory must already exist', str(destination.parent))
    if not all(_owned(p, book.root, record['scopes']) for p in (destination, temporary)):
        raise ReservationError('Destination and temporary must both be inside the owned output scopes')
    if not all(any(p.is_relative_to(Path(r)) for r in book.roots) for p in (destination, temporary)):
        raise ReservationError('Destination and temporary must both be in tracked retained roots')
    for path in (destination, temporary):
        if os.path.lexists(path):
            raise FileExistsError(errno.EEXIST, 'Existing output/failure evidence is preserved', str(path))
    rename_function = _rename_function()  # No output before platform capability check.
    started = time.perf_counter()
    buffer = encode_json_gzip(value, compressed_cap_bytes=compressed_cap_bytes)
    gzip_seconds = time.perf_counter() - started
    with buffer.view() as payload:
        size = len(payload)
        sha256 = hashlib.sha256(payload).hexdigest()
        additional = size + headroom_bytes
        _assert_writer_lease(book, reservation_key)
        summary = book.check(reservation_key, additional)  # Exactly one full inventory.
        if retained_limit_bytes is not None and summary['retained_bytes'] + additional > retained_limit_bytes:
            raise ReservationError('Legacy retained limit exhausted before output creation')
        _assert_writer_lease(book, reservation_key)
        started = time.perf_counter()
        directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            # Detect a destination created during compression/precheck; the final
            # RENAME_NOREPLACE also protects the later race after this inspection.
            try:
                os.stat(destination.name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError(errno.EEXIST, 'Destination appeared; preserved', str(destination))
            descriptor = os.open(temporary.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=directory_fd)
            try:
                written = os.write(descriptor, payload)  # Unbuffered, one exact-size write.
                if written != size:
                    raise MaterializationError(errno.EIO,
                        f'Short write: {written} of {size} bytes; temporary retained', str(temporary))
                if os.fstat(descriptor).st_size != size:
                    raise MaterializationError(errno.EIO, 'Unexpected temporary size; retained', str(temporary))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            _rename_noreplace(rename_function, directory_fd, temporary.name, destination.name)
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        write_seconds = time.perf_counter() - started
    return MaterializationResult(str(destination), str(temporary), size, sha256,
        compressed_cap_bytes, additional, 1, gzip_seconds, write_seconds)
