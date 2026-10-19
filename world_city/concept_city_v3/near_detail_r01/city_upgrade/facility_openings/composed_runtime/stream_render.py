"""Small stdlib-only, bounded-memory render reader and geometry QA.

Public API:
  iter_quads(path) -> (material, quad), in original file order.
  iter_indexed_quads(path) -> (group_index, quad_index, material, quad).
  read_metadata(path, omitted_fields=[]) -> small top-level non-groups values.
  plane_audit(factory), edge_audit(factory): factory() yields (material, quad).

Plain UTF-8 JSON and gzip (detected by magic bytes) are supported. No coordinate
rounding/reordering occurs in either iterator: json.loads decodes one quad at a
time, with the same int/float behavior as json.load. Repeated material groups,
empty groups, arbitrary key order, and unknown nested metadata are supported.
If a group puts material after quads, just that array is reread via a second
seekable stream. This can make gzip with many such groups slow, not unbounded.
Consume an iterator fully to validate its document suffix. Skipped metadata is
structurally scanned, not fully JSON-grammar-validated; this is not a validator
for hostile JSON. Duplicate keys in structural objects are rejected.

Metadata defaults: at most 256 KiB raw JSON per field and 1 MiB total; oversized
fields are skipped, optionally named in omitted_fields. No field-name whitelist.
Depth is capped at 128 and one quad/key/material at 64 KiB. Limits raise rather
than silently truncate geometry. Consumers must not list() a large iterator.

Audits validate axis-aligned rectangles on a 0.05m grid, never hold quad objects,
and use no temporary disk. Plane QA stores five int32 values per rectangle,
then two byte masks on one plane at a time. Edge QA repeats the factory for each
axis, storing int32 interval endpoints grouped by axis line; subdivision is OK.
Explicit record/plane/line/mask caps raise BudgetExceeded, never partial PASS.
Defaults are sized for <64 MiB total RSS with a small standalone Python caller,
including a 631,738-quad input. Caps are algorithmic, not an OS RSS guarantee;
caller allocations and changed limits remain the caller's responsibility.
"""
from array import array
from pathlib import Path
import gzip
import hashlib
import json
import math
import resource
import tempfile
import time


class BudgetExceeded(ValueError):
    """A configured resource cap was reached; no partial PASS is returned."""


def _open(path):
    f = open(path, 'rb')
    magic = f.read(2)
    f.close()
    return gzip.open(path, 'rb') if magic == b'\x1f\x8b' else open(path, 'rb')


class _Reader:
    def __init__(self, stream, chunk_size=65536):
        self.f = stream
        self.buf = b''
        self.pos = 0
        self.offset = stream.tell()
        self.chunk_size = chunk_size

    def _fill(self):
        self.offset += self.pos
        self.buf = self.buf[self.pos:] + self.f.read(self.chunk_size)
        self.pos = 0
        return bool(self.buf)

    def peek(self):
        while True:
            if self.pos == len(self.buf) and not self._fill():
                return None
            c = self.buf[self.pos]
            if c not in b' \r\n\t':
                return c
            self.pos += 1

    def expect(self, char):
        if self.peek() != ord(char):
            raise ValueError('expected %r at byte %d' % (char, self.offset + self.pos))
        self.pos += 1

    def members(self):
        self.expect('{')
        if self.peek() == ord('}'):
            self.pos += 1
            return
        # Bound the key-set too: ordinary objects in this format are small.
        seen = set()
        key_chars = 0
        while True:
            key = self.value()
            if not isinstance(key, str) or key in seen:
                raise ValueError('non-string or duplicate object key')
            seen.add(key)
            key_chars += len(key)
            if len(seen) > 4096 or key_chars > 65536:
                raise BudgetExceeded('structural object key budget exceeded')
            self.expect(':')
            yield key
            if self.peek() == ord('}'):
                self.pos += 1
                return
            self.expect(',')

    def elements(self):
        self.expect('[')
        if self.peek() == ord(']'):
            self.pos += 1
            return
        index = 0
        while True:
            yield index
            index += 1
            if self.peek() == ord(']'):
                self.pos += 1
                return
            self.expect(',')

    def raw(self, limit=0):
        """Consume one value; retain at most limit bytes, or return None."""
        first = self.peek()
        if first is None or first in b',]}':
            raise ValueError('missing JSON value')
        compound = first in b'[{'
        quoted = first == ord('"')
        stack = []
        in_string = escaped = False
        parts = []
        kept = 0
        too_large = limit == 0
        done = False
        while not done:
            start = self.pos
            while self.pos < len(self.buf):
                c = self.buf[self.pos]
                if not compound and not quoted and c in b' \t\r\n,]}':
                    done = True
                    break
                self.pos += 1
                if in_string:
                    if escaped:
                        escaped = False
                    elif c == ord('\\'):
                        escaped = True
                    elif c == ord('"'):
                        in_string = False
                        if quoted and not stack:
                            done = True
                            break
                elif c == ord('"'):
                    in_string = True
                elif c in b'[{':
                    stack.append(c)
                    if len(stack) > 128:
                        raise BudgetExceeded('JSON depth exceeds 128')
                elif c in b']}':
                    if not stack or (stack.pop(), c) not in ((91, 93), (123, 125)):
                        raise ValueError('mismatched JSON brackets')
                    if not stack:
                        done = True
                        break
            size = self.pos - start
            if not too_large:
                kept += size
                if kept > limit:
                    parts.clear()
                    too_large = True
                else:
                    parts.append(self.buf[start:self.pos])
            if not done and not self._fill():
                if compound or quoted:
                    raise ValueError('truncated JSON value')
                done = True
        return None if too_large else b''.join(parts)

    def value(self, limit=65536):
        raw = self.raw(limit)
        if raw is None:
            raise BudgetExceeded('individual JSON value exceeds %d bytes' % limit)
        return json.loads(raw)

    def finish(self):
        if self.peek() is not None:
            raise ValueError('trailing data after render object')


def iter_indexed_quads(path):
    """Yield gi, qi, material, q without collecting any group or quad array."""
    with _open(path) as stream:
        r = _Reader(stream)
        found = False
        for field in r.members():
            if field != 'groups':
                r.raw()
                continue
            found = True
            for gi in r.elements():
                material = None
                have_material = have_quads = False
                delayed_offset = None
                for key in r.members():
                    if key == 'material':
                        material = r.value()
                        if not isinstance(material, (str, int)) or isinstance(material, bool):
                            raise ValueError('material must be a string or integer ID')
                        have_material = True
                    elif key == 'quads':
                        have_quads = True
                        if not have_material:
                            r.peek()
                            delayed_offset = r.offset + r.pos
                            r.raw()
                        else:
                            for qi in r.elements():
                                q = r.value()
                                yield gi, qi, material, q
                    else:
                        r.raw()
                if not have_material or not have_quads:
                    raise ValueError('group needs material and quads')
                if delayed_offset is not None:
                    with _open(path) as secondary:
                        secondary.seek(delayed_offset)
                        rr = _Reader(secondary)
                        for qi in rr.elements():
                            yield gi, qi, material, rr.value()
        r.finish()
        if not found:
            raise ValueError('render has no groups array')


def iter_quads(path):
    for _, _, material, quad in iter_indexed_quads(path):
        yield material, quad


def read_metadata(path, max_field_bytes=262144, max_total_bytes=1048576,
                  omitted_fields=None):
    """Read bounded non-groups top-level fields, wherever they occur in JSON."""
    result = {}
    remaining = max_total_bytes
    with _open(path) as stream:
        r = _Reader(stream)
        for key in r.members():
            if key == 'groups':
                r.raw()
                continue
            raw = r.raw(max(0, min(max_field_bytes, remaining)))
            if raw is None:
                if omitted_fields is not None:
                    omitted_fields.append(key)
            else:
                remaining -= len(raw)
                result[key] = json.loads(raw)
        r.finish()
    return result


def grid_rectangle(q, pitch=.05, origin=(0, 0, 0)):
    """Return axis, plane, sign, u0, v0, u1, v1, integer vertices.

    u/v are cyclic tangential axes, matching existing face fingerprints.
    Only this QA helper snaps after checking tolerance; iterators never snap.
    """
    if not math.isfinite(pitch) or pitch <= 0:
        raise ValueError('pitch must be finite and positive')
    if len(q) != 4 or any(len(v) != 3 for v in q):
        raise ValueError('quad requires four 3D vertices')
    points = []
    for vertex in q:
        p = []
        for axis, x in enumerate(vertex):
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                raise ValueError('non-finite/non-numeric quad coordinate')
            scaled = (x - origin[axis]) / pitch
            n = round(scaled)
            if abs(scaled - n) > 1e-6:
                raise ValueError('off-grid quad coordinate')
            p.append(n)
        points.append(tuple(p))
    fixed = [a for a in range(3) if len({p[a] for p in points}) == 1]
    if len(fixed) != 1 or len(set(points)) != 4:
        raise ValueError('quad is degenerate or not axis-aligned')
    axis = fixed[0]
    u, v = (axis + 1) % 3, (axis + 2) % 3
    u0, u1 = min(p[u] for p in points), max(p[u] for p in points)
    v0, v1 = min(p[v] for p in points), max(p[v] for p in points)
    if {(p[u], p[v]) for p in points} != {(u0, v0), (u0, v1), (u1, v0), (u1, v1)}:
        raise ValueError('nonrectangular quad')
    edges = [tuple(points[(i + 1) % 4][a] - points[i][a] for a in range(3)) for i in range(4)]
    if any(sum(x != 0 for x in e) != 1 for e in edges):
        raise ValueError('crossed/non-axis-aligned quad edge')
    e, f = edges[:2]
    sign = 1 if e[u] * f[v] - e[v] * f[u] > 0 else -1
    return axis, points[0][axis], sign, u0, v0, u1, v1, points


def plane_audit(factory, pitch=.05, origin=(0, 0, 0),
                max_quad_records=1000000, max_planes=8192,
                max_plane_mask_cells=1048576):
    """Exact overlap counts using compact records and one plane's byte masks.

    same_normal_duplicate_unit_faces = sum(max(nplus-1,0)+max(nminus-1,0));
    opposed_coplanar_unit_faces = sum(min(nplus,nminus)), per grid cell.
    Invalid quads, >255 same-sign layers, or exceeded resource caps raise.
    """
    planes = {}
    count = faces = 0
    for _, q in factory():
        a,p,s,x0,y0,x1,y1,_ = grid_rectangle(q,pitch,origin)
        count += 1
        if count > max_quad_records:
            raise BudgetExceeded('plane audit quad-record cap exceeded')
        key = (a,p)
        if key not in planes:
            if len(planes) >= max_planes:
                raise BudgetExceeded('plane audit plane-count cap exceeded')
            planes[key] = array('i')
        planes[key].extend((s,x0,y0,x1,y1))
        faces += (x1-x0)*(y1-y0)
    result = dict(same_normal_duplicate_unit_faces=0, opposed_coplanar_unit_faces=0,
                  sampled_unit_faces=faces, maximum_plane_cells=0,
                  maximum_plane_mask_cells=0, plane_count=len(planes),
                  quad_count=count,off_grid_quads=0,examples=[])
    while planes:
        key,records = planes.popitem()
        xmin = min(records[i] for i in range(1,len(records),5))
        ymin = min(records[i] for i in range(2,len(records),5))
        xmax = max(records[i] for i in range(3,len(records),5))
        ymax = max(records[i] for i in range(4,len(records),5))
        height = ymax-ymin
        cells = (xmax-xmin)*height
        if cells > max_plane_mask_cells:
            raise BudgetExceeded('plane mask cap exceeded: %d cells on %r' % (cells,key))
        positive,negative = bytearray(cells),bytearray(cells)
        unique = 0
        result['maximum_plane_mask_cells'] = max(result['maximum_plane_mask_cells'],cells)
        for i in range(0,len(records),5):
            sign,x0,y0,x1,y1 = records[i:i+5]
            same,other = (positive,negative) if sign > 0 else (negative,positive)
            for x in range(x0,x1):
                base = (x-xmin)*height-ymin
                for y in range(y0,y1):
                    index = base+y
                    old,opposed = same[index],other[index]
                    if old == 255:
                        raise BudgetExceeded('plane overlap multiplicity exceeds 255')
                    result['same_normal_duplicate_unit_faces'] += bool(old)
                    result['opposed_coplanar_unit_faces'] += old < opposed
                    unique += not (old or opposed)
                    if (old or opposed) and len(result['examples']) < 12:
                        result['examples'].append([*key,x,y,sign,old,opposed])
                    same[index] = old+1
        result['maximum_plane_cells'] = max(result['maximum_plane_cells'],unique)
        del positive,negative,same,other,records
    return result


def edge_audit(factory, pitch=.05, origin=(0, 0, 0),
               max_axis_endpoints=4000000,max_axis_lines=32768,
               max_line_endpoints=65536):
    """Three bounded passes; unit-edge parity, not manifoldness/orientation.

    Each interval contributes two toggles. Their sorted positions give parity
    even if neighboring rectangles have different edge subdivision. No disk.
    """
    result = dict(unpaired_unit_edges=0,axis_lines_checked=0,quad_count=0,
                  maximum_axis_endpoints=0,maximum_line_endpoints=0,examples=[])
    for direction in range(3):
        lines = {}
        fixed = [j for j in range(3) if j != direction]
        count = endpoints = 0
        for _,q in factory():
            points = grid_rectangle(q,pitch,origin)[-1]
            count += 1
            for p,r in zip(points,points[1:]+points[:1]):
                if p[direction] == r[direction]:
                    continue
                key = (p[fixed[0]],p[fixed[1]])
                if key not in lines:
                    if len(lines) >= max_axis_lines:
                        raise BudgetExceeded('edge axis-line cap exceeded')
                    lines[key] = array('i')
                line = lines[key]
                if len(line)+2 > max_line_endpoints:
                    raise BudgetExceeded('edge per-line endpoint cap exceeded')
                endpoints += 2
                if endpoints > max_axis_endpoints:
                    raise BudgetExceeded('edge per-axis endpoint cap exceeded')
                line.extend((p[direction],r[direction]))
        if direction and count != result['quad_count']:
            raise ValueError('iterator factory changed quad count across passes')
        result['quad_count'] = count
        result['axis_lines_checked'] += len(lines)
        result['maximum_axis_endpoints'] = max(result['maximum_axis_endpoints'],endpoints)
        while lines:
            key,values = lines.popitem()
            result['maximum_line_endpoints'] = max(result['maximum_line_endpoints'],len(values))
            ordered = sorted(values)  # Capped one line only, never all endpoints.
            # Pairing adjacent sorted endpoints integrates odd parity; tied
            # endpoints have zero length, so no special duplicate handling.
            for j in range(0,len(ordered),2):
                lo,hi = ordered[j],ordered[j+1]
                result['unpaired_unit_edges'] += hi-lo
                if hi > lo and len(result['examples']) < 12:
                    result['examples'].append([direction,*key,lo,hi])
            del values,ordered
    return result


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def _file_sha(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(65536),b''):
            h.update(block)
    return h.hexdigest()


def stream_summary(path, face_fingerprint=False):
    """Digest ordered indexed tuples; optionally compare legacy unit-face QA.

    Per-group summaries are capped at 4096 groups; geometry is never retained.
    Fingerprint is the existing cyclic-axis BLAKE2b-256 multiset convention.
    """
    digest = hashlib.sha256()
    groups = {}
    count = faces = xor = total = 0
    for gi,qi,material,q in iter_indexed_quads(path):
        digest.update(_canonical([gi,qi,material,q]))
        if gi not in groups:
            if len(groups) >= 4096:
                raise BudgetExceeded('summary group cap exceeded')
            groups[gi] = dict(group_index=gi,material=material,quad_count=0)
        groups[gi]['quad_count'] += 1
        count += 1
        if face_fingerprint:
            a,p,s,u0,v0,u1,v1,_ = grid_rectangle(q)
            for u in range(u0,u1):
                for v in range(v0,v1):
                    encoded = _canonical([a,s,p,u,v,material])
                    n = int.from_bytes(hashlib.blake2b(encoded,digest_size=32).digest(),'big')
                    xor ^= n
                    total = (total+n) % (1 << 256)
                    faces += 1
    result = dict(quad_count=count,ordered_indexed_quads_sha256=digest.hexdigest(),
                  nonempty_groups=list(groups.values()))
    if face_fingerprint:
        result['face_fingerprint'] = dict(count=faces,xor256=f'{xor:064x}',sum256=f'{total:064x}')
    return result


def selftest(repo, output):
    """Small synthetic regression suite + bounded actual-source verification."""
    started = time.monotonic()
    repo = Path(repo)
    checks = {}
    q = [[0,0,0],[.1,0,0],[.1,.1,0],[0,.1,0]]
    back = list(reversed(q))
    fixture = {'before':{'text':'quote: " slash: \\ unicode: 한글 []{}'},
               'groups':[{'material':'a','quads':[q,back]},
                         {'quads':[q],'unknown':{'deep':[1,{'x':'y'}]},'material':'a'},
                         {'quads':[],'material':'empty'}],
               'after':[1,True,None,{'x':2.5}]}
    expected = [('a',q),('a',back),('a',q)]
    with tempfile.TemporaryDirectory(prefix='stream-render-test-') as d:
        for indent in (None,2):
            for gz in (False,True):
                p = Path(d)/('fixture.json'+('.gz' if gz else ''))
                raw = json.dumps(fixture,indent=indent,ensure_ascii=False).encode()
                p.write_bytes(gzip.compress(raw,mtime=0) if gz else raw)
                assert list(iter_quads(p)) == expected
                assert read_metadata(p) == {k:v for k,v in fixture.items() if k != 'groups'}
        checks['compact_indented_gzip_unicode_reordered_duplicate_empty_groups'] = True
        p = Path(d)/'big-metadata.json'
        p.write_text('{"huge":"'+'x'*300000+'","groups":[],"later":7}')
        omitted = []
        assert read_metadata(p,omitted_fields=omitted) == {'later':7} and omitted == ['huge']
        assert list(iter_quads(p)) == []
        checks['oversized_unknown_metadata_skipped_without_losing_suffix'] = True
        # Exercise chunks split inside UTF-8, escaped strings and every token.
        for chunk in (1,2,3,7,65536):
            import io
            r = _Reader(io.BytesIO(json.dumps(fixture,ensure_ascii=False).encode()),chunk)
            assert json.loads(r.raw(100000)) == fixture
            r.finish()
        checks['scanner_chunk_boundaries'] = True
        invalid = [b'{"groups":[',b'{"groups":[],"groups":[]}',b'{"groups":[]}x',
                   b'{"groups":[{"quads":[]}]}',b'{"groups":[{"material":"a","quads":null}]}']
        for raw in invalid:
            p.write_bytes(raw)
            try:
                list(iter_quads(p))
            except ValueError:
                pass
            else:
                raise AssertionError('malformed structural JSON accepted')
        checks['malformed_structure_rejected'] = True
        overlap = plane_audit(lambda:iter([('a',q),('b',q),('c',back)]))
        assert overlap['same_normal_duplicate_unit_faces'] == 4
        assert overlap['opposed_coplanar_unit_faces'] == 4
        assert overlap['sampled_unit_faces'] == 12 and overlap['maximum_plane_cells'] == 4
        assert edge_audit(lambda:iter([('a',q)]))['unpaired_unit_edges'] == 8
        assert edge_audit(lambda:iter([('a',q),('b',back)]))['unpaired_unit_edges'] == 0
        split = [[[0,0,0],[.05,0,0],[.05,.1,0],[0,.1,0]],
                 [[.05,0,0],[.1,0,0],[.1,.1,0],[.05,.1,0]]]
        assert edge_audit(lambda:iter([('a',back)]+[('b',x) for x in split]))['unpaired_unit_edges'] == 0
        try:
            plane_audit(lambda:iter([('a',q)]),max_plane_mask_cells=1)
        except BudgetExceeded:
            pass
        else:
            raise AssertionError('plane mask cap not enforced')
        for invalid_quad in ([[[.001,0,0]]*4], [[[0,0,0]]*4]):
            try:
                grid_rectangle(invalid_quad[0])
            except (ValueError,TypeError):
                pass
            else:
                raise AssertionError('invalid quad not rejected')
        checks['overlap_orientation_parity_tjunction_and_budget_tests'] = True
        # Independent unit raster oracle on small, randomized three-axis data.
        import random
        rng = random.Random(41873)
        rows,face_counts,edge_counts = [],{},{}
        for _ in range(150):
            axis,plane = rng.randrange(3),rng.randrange(-2,3)
            u,v = (axis+1)%3,(axis+2)%3
            x0,y0 = rng.randrange(-4,4),rng.randrange(-4,4)
            x1,y1 = x0+rng.randrange(1,5),y0+rng.randrange(1,5)
            sign = rng.choice((-1,1))
            vertices = []
            for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)):
                point = [0,0,0]
                point[axis],point[u],point[v] = plane,x,y
                vertices.append(point)
            if sign < 0:
                vertices.reverse()
            rows.append(('random',[[n*.05 for n in point] for point in vertices]))
            for x in range(x0,x1):
                for y in range(y0,y1):
                    key = axis,plane,x,y
                    counts = face_counts.setdefault(key,[0,0])
                    counts[sign > 0] += 1
            for start,end in zip(vertices,vertices[1:]+vertices[:1]):
                direction = next(a for a in range(3) if start[a] != end[a])
                fixed = [a for a in range(3) if a != direction]
                for at in range(min(start[direction],end[direction]),max(start[direction],end[direction])):
                    key = direction,start[fixed[0]],start[fixed[1]],at
                    edge_counts[key] = edge_counts.get(key,0)+1
        audit = plane_audit(lambda:iter(rows))
        assert audit['same_normal_duplicate_unit_faces'] == sum(max(a-1,0)+max(b-1,0) for a,b in face_counts.values())
        assert audit['opposed_coplanar_unit_faces'] == sum(min(a,b) for a,b in face_counts.values())
        assert audit['sampled_unit_faces'] == sum(a+b for a,b in face_counts.values())
        assert edge_audit(lambda:iter(rows))['unpaired_unit_edges'] == sum(v%2 for v in edge_counts.values())
        checks['randomized_three_axis_overlap_and_edge_unit_raster_oracle'] = True
    root = repo/'world_city/concept_city_v3/near_detail_r01/city_upgrade'
    manifest_path = root/'facility_roofs/compiled_priority_r01/handoff_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    item = next(x for x in manifest['assets'] if x['asset_key'] == 'registered_port_long_loading_shed')
    source = repo/item['source_render_path']
    roof = repo/item['files']['.render.json']['path']
    source_json = json.loads(source.read_bytes())  # Only the 420-quad original.
    source_summary = stream_summary(source)
    h = hashlib.sha256()
    for gi,g in enumerate(source_json['groups']):
        for qi,quad in enumerate(g['quads']):
            h.update(_canonical([gi,qi,g['material'],quad]))
    assert source_summary['quad_count'] == 420
    assert h.hexdigest() == source_summary['ordered_indexed_quads_sha256']
    assert list(iter_quads(source)) == [(g['material'],x) for g in source_json['groups'] for x in g['quads']]
    assert read_metadata(source) == {k:v for k,v in source_json.items() if k != 'groups'}
    source_summary['file_sha256'] = _file_sha(source)
    assert source_summary['file_sha256'] == item['source_render_sha256']
    checks['original_420_quads_equal_json_load_numbers_winding_group_indices_metadata'] = True
    del source_json
    roof_metadata = read_metadata(roof)
    roof_summary = stream_summary(roof,face_fingerprint=True)
    roof_summary['file_sha256'] = _file_sha(roof)
    qa_path = repo/item['independent_qa']['path']
    qa = json.loads(qa_path.read_text())
    assert _file_sha(qa_path) == item['independent_qa']['sha256']
    assert roof_summary['file_sha256'] == item['files']['.render.json']['sha256'] == qa['render_file']['sha256']
    assert roof_summary['quad_count'] == 123002 == item['quads'] == qa['surface']['quad_count']
    assert roof_metadata['quad_count'] == 123002
    assert roof_summary['face_fingerprint'] == qa['surface']['face_fingerprint']
    assert all(roof_metadata[k] == v for k,v in qa['surface']['metadata'].items())
    checks['roof_123002_quads_manifest_file_hash_independent_face_fingerprint_metadata'] = True
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    assert rss < 64*1024, ('RSS exceeds 64 MiB',rss)
    checks['rss_under_64_mib'] = True
    report = dict(schema='riverstone.stream_render.tests.v1',all_pass=all(checks.values()),
                  checks=checks,original=source_summary,roof=roof_summary,
                  max_rss_kib=rss,elapsed_seconds=round(time.monotonic()-started,3),
                  helper_sha256=_file_sha(__file__),independent_qa_sha256=_file_sha(qa_path),
                  fixture_manifest=str(manifest_path.relative_to(repo)),
                  roof_full_document_loaded=False,
                  limits={'quad_bytes':65536,'metadata_field_bytes':262144,
                          'metadata_total_bytes':1048576,'plane_quad_records':1000000,
                          'plane_count':8192,'plane_mask_cells':1048576,
                          'edge_axis_endpoints':4000000,'edge_axis_lines':32768,
                          'edge_line_endpoints':65536},
                  audit_scope='Synthetic overlap/parity/T-junction cases only; no large roof overlap/edge audit benchmark.',
                  notes=['Geometry iterator retains only one quad and a 64 KiB input buffer.',
                         'Roof was independently checked with all 849134 oriented/material unit-face fingerprints.',
                         'Edge parity is necessary for closure, not a full manifold/topology certificate.'])
    Path(output).write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selftest',metavar='REPO')
    ap.add_argument('--output',default=str(Path(__file__).with_name('stream_render_tests.json')))
    args = ap.parse_args()
    if not args.selftest:
        ap.error('--selftest REPO is required; import this module for reader/audit APIs')
    result = selftest(args.selftest,args.output)
    print(json.dumps({k:result[k] for k in ('all_pass','max_rss_kib','elapsed_seconds')}))
