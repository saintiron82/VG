"""Source-derived, bounded-memory, single-pass emitted polygon window QA.

Prepare: python verify_polygon_windows.py --prepare-only [--asset-key KEY]
Verify:  python verify_polygon_windows.py --asset-key KEY --render FINAL.json.gz
Tests:   python verify_polygon_windows.py --self-test

No compilation, source changes, or asset mesh generation. Preparation uses common
shape predicates at a finite set of 1D fine-grid center samples, retaining no
voxel volume. Verification reads actual quads once and compares finite exact
ray hits (depth, winding, material). It does not claim whole-mesh or visual QA.
"""
from bisect import bisect_left
from collections import Counter, defaultdict
import argparse
import copy
import gc
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import resource
import sys
import tempfile
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
F = HERE.parents[2]
ROOT = F.parents[4]
AUTHOR = F/'author.py'
STREAM = F/'composed_runtime/stream_render.py'
CORE = ROOT/'voxel_character/common/core.py'
FROZEN = {AUTHOR: '3eb0b9b3336ff4bc2000666b21a5691cd604a3f04bde717024e97640a424291a',
          STREAM: '420b60d904701283aa18001592a13ef9dcb6e9a03b182824f1a01b0048c18262',
          CORE: '2a64ed2cdf43c9adb27a821170192f69fef0153c7be98cc85c903e34ff2a407b'}
EPS = 1e-7
MAX_RSS_KIB = 128*1024
MAX_OUTPUT = 1024*1024
MAX_RAYS = 1024
MAX_LINE_CELLS = 20000
LIMITS = ('Finite clear-half orthographic fine-grid witnesses in this canonical asset only. '
          'Source predicates establish sampled whole-assembly exposure, not visibility in a city placement. '
          'No full-area pane, frame, mullion, sill, roof, seam, watertightness, collision, full entry-volume, '
          'GUI/pixel, historical correctness, or runtime-activation claim. Occluded samples are recorded '
          'separately and never counted as exposed pane passes. No geometry is repaired.')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(65536), b''): h.update(b)
    return h.hexdigest()


def load(path):
    p = Path(path)
    with (gzip.open(p, 'rt') if p.suffix == '.gz' else p.open()) as f: return json.load(f)


def ref(path):
    p = Path(path).resolve()
    try: name = str(p.relative_to(ROOT))
    except ValueError: name = str(p)
    return {'path': name, 'sha256': sha(p), 'bytes': p.stat().st_size}


def check_ref(item):
    p = Path(item['path'])
    if not p.is_absolute(): p = ROOT/p
    if sha(p) != item['sha256']: raise ValueError('Changed source dependency: '+str(p))
    return p


def budget():
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > MAX_RSS_KIB:
        raise MemoryError('128 MiB RSS limit exceeded; refusing partial evidence')


def write(path, value):
    path = Path(path).resolve()
    if path.parent != HERE: raise ValueError('Output must remain in the owned emitted_qa directory')
    payload = canonical(value)+b'\n'
    total = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file() and p.resolve() != path)
    if total+len(payload) > MAX_OUTPUT: raise ValueError('1 MiB total output budget exceeded')
    path.write_bytes(payload)


def modules():
    for p, digest in FROZEN.items():
        if sha(p) != digest: raise ValueError('Frozen helper changed: '+str(p))
    out = []
    for name, path in [('polygon_frozen_author', AUTHOR), ('polygon_frozen_stream', STREAM)]:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); out.append(module)
    return out


def close(a, b): return abs(a-b) < EPS


def normal_axis(t):
    column = [t['basis'][a][2] for a in range(3)]
    nonzero = [a for a, n in enumerate(column) if abs(n) > EPS]
    if len(nonzero) != 1 or not close(abs(column[nonzero[0]]), 1):
        raise ValueError('Witnesses require an axis-aligned unit outward normal')
    # Reject non-axis-aligned tangent directions too, rather than silently sample an approximation.
    for j in range(2):
        col = [t['basis'][a][j] for a in range(3)]
        if sum(abs(x) > EPS for x in col) != 1 or not close(sum(abs(x) for x in col), 1):
            raise ValueError('Witnesses require an orthogonal signed-axis transform')
    a = nonzero[0]
    return a, 1 if column[a] > 0 else -1


class Scene:
    """Point oracle preserving common operation order, instance layers and cuts.

    This is not compile_master: no cell volumes, constraints, neighbor mesh,
    mesher, render, or compiler call. Bounds filter candidates conservatively;
    exact common predicates and selector_matches decide every sampled point.
    """
    def __init__(self, master, pitch, author):
        self.core = author.core; self.pitch = pitch
        self.origin = master.get('grid_origin', [0, 0, 0])
        self.layers = []; self.cuts = []; self.paints = []
        components = {c['id']: c for c in master['components']}
        transforms = author.world_transforms(master)
        for inst in master['instances']:
            ops = []
            for op in components[inst['component']]['operations']:
                t = self.core.compose(transforms[inst['id']], self.core.transform(op.get('transform')))
                shape = self.core.prepare_shape(op['shape'], pitch)
                b = author.bounds(shape, t)
                label = {'instance': inst['id'], 'component': inst['component'], 'part': op['part'],
                         'material': op.get('material'), 'feature': op['id']}
                rec = (op['action'], shape, t, b, op.get('selector', {}), label)
                ops.append(rec)
                if op['action'] == 'paint': self.paints.append(rec)
            self.layers.append(ops)
        for op in master.get('assembly_cuts', []):
            t = self.core.transform(op.get('transform')); shape = self.core.prepare_shape(op['shape'], pitch)
            self.cuts.append(('cut', shape, t, author.bounds(shape, t), op.get('selector', {}), None))
        budget()

    def line_context(self, axis, point):
        tangents = [a for a in range(3) if a != axis]
        def relevant(rec):
            return all(rec[3][0][a]-EPS <= point[a] <= rec[3][1][a]+EPS for a in tangents)
        return [[r for r in ops if relevant(r)] for ops in self.layers], [r for r in self.cuts if relevant(r)]

    def at(self, world, context):
        def contains(rec):
            return (all(rec[3][0][a]-EPS <= world[a] <= rec[3][1][a]+EPS for a in range(3)) and
                    self.core.contains(rec[1], self.core.inverse(rec[2], world), epsilon=self.pitch*self.core.EPS))
        layers, cuts = context; result = None
        for operations in layers:
            label = None
            for r in operations:
                if contains(r):
                    if r[0] == 'paint': label = r[5]
                    elif label is not None and self.core.selector_matches(r[4], label): label = None
            if label is not None:
                for r in cuts:
                    if self.core.selector_matches(r[4], label) and contains(r): label = None; break
            if label is not None: result = label
        return result

    def surfaces(self, ray):
        a, sign, tr = ray['axis'], ray['outward_sign'], ray['frame_axis_origin_m']
        point = ray['sample_master_m'][:]; context = self.line_context(a, point)
        bound = [v for layer in context[0] for r in layer if r[0] == 'paint' for v in (r[3][0][a], r[3][1][a])]
        if not bound: return [], 0
        # Include the full outward half-assembly, not just a wall patch or nearest operation.
        inside = tr+sign*ray['minimum_depth_m']
        outside = max(bound)+2*self.pitch if sign > 0 else min(bound)-2*self.pitch
        lo, hi = sorted((inside, outside))
        start = math.floor((lo-self.origin[a])/self.pitch)-2
        end = math.ceil((hi-self.origin[a])/self.pitch)+2
        if end-start > MAX_LINE_CELLS: raise ValueError('Source ray sample cap exceeded')
        previous = None; hits = []
        for n in range(start, end+1):
            point[a] = self.origin[a]+(n+.5)*self.pitch
            current = self.at(point, context)
            if (previous is None) != (current is None):
                plane = self.origin[a]+n*self.pitch
                depth = sign*(plane-tr)
                if depth >= ray['minimum_depth_m']-EPS:
                    label = previous if previous is not None else current
                    hits.append({'depth_m': round(depth, 12), 'normal_outward': sign*(1 if previous else -1),
                                 'material': label['material'], 'owner': label})
            previous = current
        return sorted(hits, key=lambda h: -h['depth_m']), end-start+1


def scanline(poly, y):
    xs = []
    for p, q in zip(poly, poly[1:]+poly[:1]):
        if (p[1] > y) != (q[1] > y): xs.append(p[0]+(y-p[1])*(q[0]-p[0])/(q[1]-p[1]))
    xs.sort()
    if len(xs) != 2 or xs[1]-xs[0] <= EPS:
        raise ValueError('Clear-half selection requires one nonempty polygon scanline interval')
    return xs


def snapped_witness(t, xy, pitch, origin, core):
    a, sign = normal_axis(t)
    point = core.apply(t, [*xy, 0])
    for j in range(3):
        if j != a: point[j] = origin[j]+(math.floor((point[j]-origin[j])/pitch)+.5)*pitch
    return a, sign, point, core.inverse(t, point)


def compare_hits(actual, expected):
    a = sorted(actual, key=lambda h: (-h['depth_m'], h['normal_outward'], str(h['material'])))
    e = sorted(expected, key=lambda h: (-h['depth_m'], h['normal_outward'], str(h['material'])))
    return (len(a) == len(e) and all(close(x['depth_m'], y['depth_m']) and
            x['normal_outward'] == y['normal_outward'] and x['material'] == y['material'] for x, y in zip(a, e)))


def classify(ray, canonical_hits, source_hits, source_binding):
    front = ray['pane_front_depth_m']
    canonical_first = canonical_hits[0] if canonical_hits else None
    if (canonical_first and close(canonical_first['depth_m'], front) and
        canonical_first['normal_outward'] == 1 and canonical_first['material'] == ray['pane_material'] and
        canonical_first['owner']['feature'] == ray['pane_feature']):
        return 'exposed', None
    # A canonical blocker must also exist in original source with the same ownership/material/depth.
    occluders = [h for h in canonical_hits if h['depth_m'] > front+EPS and h['normal_outward'] == 1]
    for h in occluders:
        label = h['owner']
        is_structure = not (label['instance'] == source_binding['instance'] and
                            label['component'] == source_binding['component'])
        if is_structure and any(close(s['depth_m'], h['depth_m']) and s['owner'] == label and
                                s['normal_outward'] == h['normal_outward'] for s in source_hits):
            return 'preexisting_source_structural_occlusion', h
    return 'unexplained_canonical_pane_failure', canonical_first


def snapped_depth(t, depth, pitch, origin, core):
    a, sign = normal_axis(t); x = core.apply(t, [0, 0, depth])[a]
    scaled = (x-origin[a])/pitch
    if close(scaled-math.floor(scaled), .5):
        raise ValueError('Half-cell tied boundary requires a separately declared witness policy')
    return round(sign*(origin[a]+math.floor(scaled+.5)*pitch-t['translation'][a]), 12)


def prepare_asset(asset, catalog_path, rules_path, author):
    start = time.monotonic(); key = asset['asset_key']; rules = load(rules_path)
    inputs = {name: ref(ROOT/asset[field]) for name, field in
              [('source_master', 'source_master_path'), ('canonical_master', 'emitted_master_path'),
               ('replacement_contract', 'replacement_contract_path')]}
    for name, field in [('source_master', 'source_sha256'), ('canonical_master', 'emitted_master_sha256'),
                        ('replacement_contract', 'replacement_contract_sha256')]:
        if inputs[name]['sha256'] != asset[field]: raise ValueError('Catalog SHA mismatch: '+name)
    contract = load(ROOT/asset['replacement_contract_path'])
    source = load(ROOT/asset['source_master_path']); master = load(ROOT/asset['emitted_master_path'])
    if contract['authored_master_sha256'] != inputs['canonical_master']['sha256']:
        raise ValueError('Contract canonical SHA mismatch')
    if len(contract['patches']) != asset['window_count']: raise ValueError('Window count mismatch')
    pitch = contract['fine_pitch_m']; origin = contract['grid_origin']
    if not close(pitch, rules['fine_pitch_m']) or origin != master.get('grid_origin', [0, 0, 0]):
        raise ValueError('Sampling grid mismatch')
    source_scene = Scene(source, pitch, author); candidate_scene = Scene(master, pitch, author)
    source_lookup = {(c, i, o['id']): (o, t) for c, i, o, t, _ in author.source_inventory(source)}
    new_ops = {o['id']: o for c in master['components'] if c['id'] == 'opening_details' for o in c['operations']}
    rays = []; windows = []; sampled = 0; failures = []
    for patch in contract['patches']:
        b = patch['source_glass']; pane, t = source_lookup[b['component'], b['instance'], b['operation']]
        if author.core.digest(pane) != b['operation_sha256']: raise ValueError('Source pane operation hash mismatch')
        poly = pane['shape']['polygon']
        if poly != patch['source_profile_polygon'] or t != patch['local_to_master']:
            raise ValueError('Source profile/transform differs from replacement contract')
        pid = patch['id']; glass = new_ops[pid+'_glass']; sill = new_ops[pid+'_sill']; mullion = new_ops.get(pid+'_mullion')
        expected_shape = author.extrusion(poly, -rules['glass_recess_m']-rules['glass_thickness_m'], -rules['glass_recess_m'])
        if glass['shape'] != expected_shape or glass.get('transform') != t or glass['material'] != pane['material']:
            raise ValueError('Canonical pane differs from frozen rule construction')
        if patch['cavity_shape_local'] != author.extrusion(poly, -rules['cavity_depth_m'], .025):
            raise ValueError('Canonical cavity differs from frozen rules')
        ymin, ymax = min(p[1] for p in poly), max(p[1] for p in poly)
        center = (min(p[0] for p in poly)+max(p[0] for p in poly))/2
        halfbar = rules['mullion_width_m']/2 if mullion else 0
        window_rays = []
        for yi, fraction in enumerate((.25, .5, .75)):
            y = ymin+(ymax-ymin)*fraction
            left, right = scanline(poly, y)
            for half, x in [('left', (left+center-halfbar)/2), ('right', (center+halfbar+right)/2)]:
                a, sign, point, local = snapped_witness(t, [x, y], pitch, origin, author.core)
                midpoint = [local[0], local[1], -(rules['glass_recess_m']+rules['glass_thickness_m']/2)]
                if not author.core.contains(author.core.prepare_shape(glass['shape'], pitch), midpoint):
                    raise ValueError('Snapped clear-half point lies outside glass')
                if author.core.contains(author.core.prepare_shape(sill['shape'], pitch), midpoint) or (mullion and
                   author.core.contains(author.core.prepare_shape(mullion['shape'], pitch), midpoint)):
                    raise ValueError('Snapped clear-half point intersects sill/mullion')
                ray = {'id': pid+'__'+str(yi)+'__'+half, 'kind': 'pane', 'patch_id': pid, 'half': half,
                       'height_fraction': fraction, 'axis': a, 'outward_sign': sign,
                       'frame_axis_origin_m': t['translation'][a], 'sample_master_m': point,
                       'requested_local_xy_m': [x, y], 'snapped_local_xy_m': local[:2],
                       'minimum_depth_m': -rules['cavity_depth_m']-pitch,
                       'pane_front_depth_m': snapped_depth(t, glass['shape']['z_max'], pitch, origin, author.core),
                       'pane_back_depth_m': snapped_depth(t, glass['shape']['z_min'], pitch, origin, author.core),
                       'pane_material': glass['material'], 'pane_feature': glass['id']}
                hits, n = candidate_scene.surfaces(ray); sampled += n
                old_hits, n = source_scene.surfaces(ray); sampled += n
                classification, blocker = classify(ray, hits, old_hits, b)
                ray.update(exposure=classification, expected_hits=hits, original_source_hits=old_hits,
                           preexisting_occluder=blocker if classification.startswith('preexisting') else None)
                # Independently require a 0.05 m pane, rear air and cavity backing at source depth.
                if classification == 'exposed':
                    expected_front = {'depth_m': ray['pane_front_depth_m'], 'normal_outward': 1, 'material': glass['material']}
                    expected_back = {'depth_m': ray['pane_back_depth_m'], 'normal_outward': -1, 'material': glass['material']}
                    backing_depth = snapped_depth(t, -rules['cavity_depth_m'], pitch, origin, author.core)
                    if (len(hits) < 3 or not compare_hits(hits[:2], [expected_front, expected_back]) or
                        not close(hits[2]['depth_m'], backing_depth) or hits[2]['normal_outward'] != 1 or
                        not close(ray['pane_front_depth_m']-ray['pane_back_depth_m'], rules['glass_thickness_m'])):
                        failures.append({'id': ray['id'], 'problem': 'source_pane_rear_air_or_backing_profile'})
                elif classification == 'unexplained_canonical_pane_failure':
                    failures.append({'id': ray['id'], 'problem': classification})
                rays.append(ray); window_rays.append(ray['id'])
        windows.append({'patch_id': pid, 'source_glass': b, 'profile_polygon': poly, 'local_to_master': t,
                        'source_surround': patch['source_surround'], 'ray_ids': window_rays})
    # Original functional cuts must remain exact, and protected component cuts remain exact.
    original_cuts = source.get('assembly_cuts', [])
    canonical_cuts = {c['id']: c for c in master.get('assembly_cuts', [])}
    preserved = all(canonical_cuts.get(c['id']) == c for c in original_cuts)
    protected = all(canonical_cuts.get(c['id']) == c for c in contract['protected_component_entry_cuts'])
    if not preserved or not protected: failures.append({'problem': 'original_or_protected_entry_cut_changed'})
    entry_cuts = [c for c in original_cuts if any(word in c['id'].lower() for word in ('entry', 'passage', 'portal', 'door'))]
    for cut in entry_cuts:
        shape = cut['shape']; t = author.core.transform(cut.get('transform'))
        if shape['kind'] != 'box': raise ValueError('Entry witness requires an explicitly supported box cut')
        a, sign = normal_axis(t)
        for yi, fy in enumerate((.25, .5, .75)):
            for xi, fx in enumerate((.25, .5, .75)):
                x = shape['min'][0]+fx*(shape['max'][0]-shape['min'][0])
                y = shape['min'][1]+fy*(shape['max'][1]-shape['min'][1])
                _, _, point, _ = snapped_witness(t, [x, y], pitch, origin, author.core)
                depths = sorted((shape['min'][2], shape['max'][2]))
                ray = {'id': cut['id']+'__'+str(yi)+'_'+str(xi), 'kind': 'protected_entry', 'axis': a,
                       'outward_sign': sign, 'frame_axis_origin_m': t['translation'][a],
                       'sample_master_m': point, 'minimum_depth_m': depths[0]-pitch,
                       'maximum_depth_m': depths[1]+pitch, 'exposure': 'protected_entry', 'expected_hits': []}
                context = candidate_scene.line_context(a, point); blockers = []
                low, high = sorted((t['translation'][a]+sign*ray['minimum_depth_m'],
                                    t['translation'][a]+sign*ray['maximum_depth_m']))
                n0 = math.ceil((low-origin[a])/pitch-.5); n1 = math.floor((high-origin[a])/pitch-.5)
                for n in range(n0, n1+1):
                    p = point[:]; p[a] = origin[a]+(n+.5)*pitch
                    label = candidate_scene.at(p, context); sampled += 1
                    if label: blockers.append(label)
                if blockers: failures.append({'id': ray['id'], 'problem': 'protected_entry_source_occupied'})
                rays.append(ray)
    if len(rays) > MAX_RAYS: raise ValueError('Witness ray cap exceeded')
    counts = Counter(r['exposure'] for r in rays)
    for kind in ('exposed', 'preexisting_source_structural_occlusion', 'unexplained_canonical_pane_failure', 'protected_entry'):
        counts.setdefault(kind, 0)
    result = {'schema': 'riverstone.polygon_windows.source_witnesses.v1', 'asset_key': key,
              'all_pass': None, 'source_witnesses_pass': not failures,
              'status': 'source_witnesses_ready_actual_render_not_tested' if not failures else 'source_witness_failure',
              'actual_render_tested': False, 'render_sha256': None, 'quad_count': None,
              'ordered_material_quad_digest': None, 'tested_exposure_count': 0,
              'source_witness_sha256': None, 'window_count': len(windows), 'pitch_m': pitch, 'grid_origin': origin,
              'source_references': {**inputs, 'catalog': ref(catalog_path), 'rules': ref(rules_path),
                                    'frozen_author': ref(AUTHOR), 'frozen_predicates': ref(CORE), 'stream_reader': ref(STREAM),
                                    'witness_verifier': ref(__file__)},
              'source_exposure_counts': dict(counts), 'windows': windows, 'rays': rays,
              'entry_preservation': {'original_assembly_cuts_exact_value_preserved': preserved,
                                     'protected_component_cuts_exact_value_preserved': protected,
                                     'entry_metadata': contract['entrances'], 'finite_entry_rays': counts['protected_entry']},
              'source_line_point_evaluations': sampled, 'failures': failures,
              'compile_calls': 0, 'geometry_edits': 0, 'runtime_edits': 0,
              'limitation_scope': LIMITS, 'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'elapsed_seconds': round(time.monotonic()-start, 3)}
    budget(); write(HERE/(key+'.source_witnesses.json'), result)
    return {k: result[k] for k in ('asset_key', 'status', 'window_count', 'source_exposure_counts', 'source_witnesses_pass', 'max_rss_kib', 'elapsed_seconds')}


class Collector:
    def __init__(self, witnesses, stream):
        self.rays = copy.deepcopy(witnesses['rays']); self.stream = stream
        self.pitch = witnesses['pitch_m']; self.origin = witnesses['grid_origin']
        self.count = self.touched = 0
        self.by_axis = defaultdict(lambda: defaultdict(list)); self.keys = {}
        for r in self.rays:
            r['hits'] = []; a = r['axis']; u, v = (a+1)%3, (a+2)%3
            r['_u'] = (r['sample_master_m'][u]-self.origin[u])/self.pitch
            r['_v'] = (r['sample_master_m'][v]-self.origin[v])/self.pitch
            self.by_axis[a][r['_u']].append(r)
        for a, by_u in self.by_axis.items(): self.keys[a] = sorted(by_u)

    def consume(self, gi, qi, material, quad):
        # Validate every emitted quad, not only likely witness planes. This rejects
        # nonfinite, bow-tie, nonrectangular, degenerate and off-grid geometry.
        a, plane, sign, u0, v0, u1, v1, _ = self.stream.grid_rectangle(quad, self.pitch, self.origin)
        self.count += 1; touched = False
        keys = self.keys.get(a, [])
        for U in keys[bisect_left(keys, u0):bisect_left(keys, u1)]:
            for r in self.by_axis[a][U]:
                if not v0 <= r['_v'] < v1: continue
                depth = r['outward_sign']*(self.origin[a]+plane*self.pitch-r['frame_axis_origin_m'])
                if depth < r['minimum_depth_m']-EPS or depth > r.get('maximum_depth_m', math.inf)+EPS: continue
                r['hits'].append({'depth_m': round(depth, 12), 'normal_outward': sign*r['outward_sign'],
                                  'material': material, 'group_index': gi, 'quad_index': qi})
                if len(r['hits']) > 64: raise ValueError('Witness ray exceeds 64 hits: '+r['id'])
                touched = True
        self.touched += touched


def validate_ray(ray):
    hits = sorted(ray['hits'], key=lambda h: (-h['depth_m'], h['normal_outward'], str(h['material'])))
    problems = []
    if not compare_hits(hits, ray['expected_hits']): problems.append('depth_winding_material_or_hit_count_mismatch')
    if ray['kind'] == 'pane' and ray['exposure'] == 'exposed':
        if (not hits or not close(hits[0]['depth_m'], ray['pane_front_depth_m']) or
            hits[0]['normal_outward'] != 1 or hits[0]['material'] != ray['pane_material']):
            problems.append('exposed_pane_front_missing_or_occluded')
    if ray['exposure'] == 'unexplained_canonical_pane_failure': problems.append('unexplained_source_failure')
    return {'id': ray['id'], 'kind': ray['kind'], 'exposure': ray['exposure'], 'pass': not problems,
            'problems': problems, 'ordered_hits': hits,
            'counted_as_exposed_pane_test': ray['kind'] == 'pane' and ray['exposure'] == 'exposed'}


def verify(witness_path, render_path, stream, save_report=True):
    start = time.monotonic(); w = load(witness_path)
    if not w.get('source_witnesses_pass'): raise ValueError('Source witnesses did not pass; no emitted PASS allowed')
    for item in w['source_references'].values(): check_ref(item)
    if not Path(render_path).is_file(): raise FileNotFoundError('Final render unavailable; no actual geometry test ran')
    before = (render_path.stat().st_size, render_path.stat().st_mtime_ns)
    render_ref = ref(render_path); collector = Collector(w, stream); digest = hashlib.sha256()
    for gi, qi, material, q in stream.iter_indexed_quads(render_path):
        digest.update(canonical([material, q])); collector.consume(gi, qi, material, q)
        if collector.count%10000 == 0: budget()
    if before != (render_path.stat().st_size, render_path.stat().st_mtime_ns): raise ValueError('Render changed during scan')
    results = [validate_ray(r) for r in collector.rays]; failures = [r for r in results if not r['pass']]
    if not collector.count: raise ValueError('Empty render cannot pass geometry QA')
    counts = {kind: {'total': sum(r['exposure'] == kind for r in results),
                     'passed': sum(r['exposure'] == kind and r['pass'] for r in results)}
              for kind in sorted({r['exposure'] for r in results})}
    result = {'schema': 'riverstone.polygon_windows.emitted_geometry_qa.v1', 'asset_key': w['asset_key'],
              'all_pass': not failures, 'status': 'pass_emitted_witnesses' if not failures else 'fail_emitted_witnesses',
              'actual_render_tested': True, 'render_sha256': render_ref['sha256'], 'quad_count': collector.count,
              'ordered_material_quad_digest': digest.hexdigest(), 'source_witness_sha256': sha(witness_path),
              'tested_exposure_count': counts.get('exposed', {}).get('total', 0),
              'passed_exposure_count': counts.get('exposed', {}).get('passed', 0),
              'preexisting_occluded_sample_count': counts.get('preexisting_source_structural_occlusion', {}).get('total', 0),
              'summary_counts': counts, 'ray_results': results, 'failure_count': len(failures),
              'render_reference': render_ref, 'source_witness_reference': ref(witness_path), 'verifier': ref(__file__),
              'window_count': w['window_count'], 'geometry_iterator_passes': 1, 'quads_touching_witnesses': collector.touched,
              'compile_calls': 0, 'geometry_edits': 0, 'runtime_edits': 0, 'visual_review_pass': False,
              'limitation_scope': LIMITS, 'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'elapsed_seconds': round(time.monotonic()-start, 3)}
    budget()
    if save_report: write(HERE/(w['asset_key']+'.emitted_geometry_qa.json'), result)
    return result


def self_test(author, stream):
    checks = []
    def check(name, condition):
        if not condition: raise AssertionError(name)
        checks.append(name)
    base = {'id': 'test', 'kind': 'pane', 'exposure': 'exposed', 'axis': 2, 'outward_sign': 1,
            'frame_axis_origin_m': 0, 'sample_master_m': [.025, .025, 0], 'minimum_depth_m': -.35,
            'pane_front_depth_m': -.2, 'pane_material': 'glass',
            'expected_hits': [{'depth_m': d, 'normal_outward': s, 'material': 'glass'} for d, s in [(-.2, 1), (-.25, -1), (-.3, 1)]]}
    def q(z, sign=1):
        quad = [[0, 0, z], [.05, 0, z], [.05, .05, z], [0, .05, z]]
        return quad if sign == 1 else quad[::-1]
    w = {'rays': [base], 'pitch_m': .05, 'grid_origin': [0, 0, 0]}
    c = Collector(w, stream)
    for i, (d, s) in enumerate([(-.2, 1), (-.25, -1), (-.3, 1)]): c.consume(0, i, 'glass', q(d, s))
    check('correct_depth_winding_material', validate_ray(c.rays[0])['pass'])
    for name, change in [('missing_face_rejected', lambda h: h.pop()),
                         ('duplicate_face_rejected', lambda h: h.append(dict(h[0]))),
                         ('wrong_winding_rejected', lambda h: h[0].update(normal_outward=-1)),
                         ('wrong_depth_rejected', lambda h: h[0].update(depth_m=-.15)),
                         ('wrong_material_rejected', lambda h: h[0].update(material='stone')),
                         ('front_occluder_rejected', lambda h: h.append({'depth_m': .1, 'normal_outward': 1, 'material': 'stone'}))]:
        r = copy.deepcopy(c.rays[0]); change(r['hits']); check(name, not validate_ray(r)['pass'])
    malformed = [('nan', [[math.nan, 0, 0]]*4), ('inf', [[math.inf, 0, 0]]*4),
                 ('bow_tie', [q(0)[i] for i in [0, 2, 1, 3]]), ('degenerate', [[0, 0, 0]]*4),
                 ('off_grid', [[0, 0, .001], [.05, 0, .001], [.05, .05, .001], [0, .05, .001]]),
                 ('nonrectangle', [[0, 0, 0], [.1, 0, 0], [.05, .05, 0], [0, .05, 0]])]
    for name, quad in malformed:
        try: Collector(w, stream).consume(0, 0, 'glass', quad)
        except (ValueError, TypeError): check(name+'_rejected', True)
        else: check(name+'_rejected', False)
    mirror = copy.deepcopy(base); mirror['outward_sign'] = -1
    cm = Collector({**w, 'rays': [mirror]}, stream)
    for i, (d, s) in enumerate([(-.2, 1), (-.25, -1), (-.3, 1)]): cm.consume(0, i, 'glass', q(-d, -s))
    check('mirrored_depth_and_winding', validate_ray(cm.rays[0])['pass'])
    # End-to-end gzip streaming fixture, with a material-after-quads group.
    with tempfile.TemporaryDirectory() as folder:
        p = Path(folder)/'r.json.gz'
        with gzip.open(p, 'wt') as f: json.dump({'groups': [{'quads': [q(-.2)], 'material': 'glass'},
            {'material': 'glass', 'quads': [q(-.25, -1), q(-.3)]}]}, f)
        cc = Collector(w, stream)
        for args in stream.iter_indexed_quads(p): cc.consume(*args)
        check('gzip_actual_quad_reader', cc.count == 3 and validate_ray(cc.rays[0])['pass'])
        wp = Path(folder)/'witness.json'
        wp.write_bytes(canonical({**w, 'asset_key': 'synthetic_fixture_only', 'source_witnesses_pass': True,
                                 'source_references': {'stream_reader': ref(STREAM)}, 'window_count': 1}))
        verified = verify(wp, p, stream, save_report=False)
        required = {'all_pass', 'asset_key', 'render_sha256', 'quad_count', 'ordered_material_quad_digest',
                    'source_witness_sha256', 'tested_exposure_count', 'limitation_scope'}
        check('end_to_end_report_contract', required <= set(verified) and verified['all_pass'] and
              verified['quad_count'] == 3 and verified['tested_exposure_count'] == 1 and
              verified['source_witness_sha256'] == sha(wp) and verified['render_sha256'] == sha(p))
        with gzip.open(p, 'wt') as f: json.dump({'groups': [{'material': 'stone', 'quads': [q(-.2), q(-.25, -1), q(-.3)]}]}, f)
        check('end_to_end_wrong_material_fails', not verify(wp, p, stream, save_report=False)['all_pass'])
        with gzip.open(p, 'wt') as f: f.write('{"groups": [{"material": "glass", "quads": [')
        try: verify(wp, p, stream, save_report=False)
        except ValueError: check('truncated_document_rejected', True)
        else: check('truncated_document_rejected', False)
    # Pure source-point tests: layer-local cuts, selector-targeted assembly cuts,
    # and re-exposure of an earlier layer after a later layer is cut.
    def op(name, material):
        return {'id': name, 'action': 'paint', 'part': 'solid', 'material': material,
                'shape': {'kind': 'box', 'min': [0, 0, 0], 'max': [1, 1, 1]}}
    master = {'components': [{'id': 'a', 'operations': [op('base', 'stone')]},
                            {'id': 'b', 'operations': [op('cover', 'glass')]}],
              'instances': [{'id': 'a', 'component': 'a'}, {'id': 'b', 'component': 'b'}], 'assembly_cuts': []}
    point = [.025]*3; scene = Scene(master, .05, author)
    check('instance_layer_priority', scene.at(point, scene.line_context(2, point))['material'] == 'glass')
    master['assembly_cuts'] = [{'id': 'target', 'shape': op('', '')['shape'], 'selector': {'instance': 'b'}}]
    scene = Scene(master, .05, author)
    check('target_cut_reveals_lower_layer', scene.at(point, scene.line_context(2, point))['material'] == 'stone')
    master['assembly_cuts'][0]['selector'] = {}; scene = Scene(master, .05, author)
    check('functional_global_cut_empty', scene.at(point, scene.line_context(2, point)) is None)
    owner = {'instance': 'wall', 'component': 'masonry', 'feature': 'buttress', 'material': 'stone', 'part': 'solid'}
    blocker = {'depth_m': .2, 'normal_outward': 1, 'material': 'stone', 'owner': owner}
    cr = {**base, 'pane_feature': 'new'}; binding = {'instance': 'windows', 'component': 'windows'}
    check('preexisting_occlusion_classified', classify(cr, [blocker], [blocker], binding)[0] == 'preexisting_source_structural_occlusion')
    check('new_occlusion_not_excused', classify(cr, [blocker], [], binding)[0] == 'unexplained_canonical_pane_failure')
    hidden = {**base, 'exposure': 'preexisting_source_structural_occlusion', 'expected_hits': [blocker], 'hits': [blocker]}
    check('occluded_not_counted_as_exposed', validate_ray(hidden)['pass'] and not validate_ray(hidden)['counted_as_exposed_pane_test'])
    # A preserved entry forbids real cross-ray surfaces, including cut boundaries.
    entry = {**base, 'kind': 'protected_entry', 'exposure': 'protected_entry',
             'minimum_depth_m': -1.05, 'maximum_depth_m': 1.05, 'expected_hits': []}
    ce = Collector({**w, 'rays': [entry]}, stream)
    check('empty_entry_ray_passes', validate_ray(ce.rays[0])['pass'])
    ce.consume(0, 0, 'stone', q(1.0))
    check('entry_boundary_blockage_rejected', not validate_ray(ce.rays[0])['pass'])
    bad_source = copy.deepcopy(master)
    bad_source['assembly_cuts'][0]['selector'] = {'instance': 'absent'}
    scene = Scene(bad_source, .05, author)
    check('incorrect_entry_cut_selector_remains_occupied', scene.at(point, scene.line_context(2, point)) is not None)
    local_master = copy.deepcopy(master); local_master['assembly_cuts'] = []
    local_master['components'][1]['operations'].append({'id': 'local_cut', 'part': 'solid', 'action': 'cut',
        'shape': op('', '')['shape'], 'selector': {'feature': 'cover'}})
    scene = Scene(local_master, .05, author)
    check('component_cut_cannot_erase_lower_instance', scene.at(point, scene.line_context(2, point))['material'] == 'stone')
    return {'status': 'pass', 'test_count': len(checks), 'tests': checks, 'actual_asset_render_tested': False,
            'compile_calls': 0, 'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', type=Path, default=HERE.parent/'canonical/catalog.json')
    p.add_argument('--rules', type=Path, default=HERE.parent/'rules.v1.json')
    p.add_argument('--asset-key'); p.add_argument('--render', type=Path); p.add_argument('--witness', type=Path)
    p.add_argument('--prepare-only', action='store_true'); p.add_argument('--self-test', action='store_true')
    args = p.parse_args(); author, stream = modules()
    if args.self_test:
        result = self_test(author, stream); write(HERE/'self_test.json', result); print(json.dumps(result, indent=2)); return 0
    if args.prepare_only:
        if args.render: p.error('--prepare-only does not test a render; omit --render')
        selected = [a for a in load(args.catalog)['assets'] if not args.asset_key or a['asset_key'] == args.asset_key]
        if not selected: p.error('asset key is absent from catalog')
        results = []
        for a in selected:
            results.append(prepare_asset(a, args.catalog, args.rules, author)); gc.collect()
        print(json.dumps(results, indent=2)); return 0 if all(r['source_witnesses_pass'] for r in results) else 1
    if not args.asset_key or not args.render: p.error('verification requires --asset-key and --render')
    witness = args.witness or HERE/(args.asset_key+'.source_witnesses.json')
    if load(witness)['asset_key'] != args.asset_key: raise ValueError('Witness asset key mismatch')
    result = verify(witness, args.render, stream)
    print(json.dumps({k: result[k] for k in ('all_pass', 'asset_key', 'quad_count', 'render_sha256',
        'tested_exposure_count', 'preexisting_occluded_sample_count', 'failure_count', 'max_rss_kib', 'elapsed_seconds')}, indent=2))
    return 0 if result['all_pass'] else 1


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, FileNotFoundError, MemoryError, AssertionError, KeyError) as exc:
        print(json.dumps({'all_pass': False, 'status': 'verification_not_completed', 'error': str(exc),
                          'actual_render_tested': False, 'visual_review_pass': False}), file=sys.stderr)
        sys.exit(2)
