"""Finite phase-02 productive ground, bound to the corrected frozen R6 scene.

This helper never compiles native geometry, exports a scene, or activates a
holding. Run --self-test without the scene. Run --build only after the parent
has accepted the current design/native inputs. Native footing cuts require an
explicit --native-geometry file; source-design rectangles are never footings.
An explicitly supplied finite private collar is the sole height exception;
its two side closures are split at exact frozen-plane breakpoints.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
OUT = HERE / 'ground_patch_outputs'
sys.path.insert(0, str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import frozen_r6 as f

a = f.a
geo = a.geo
AREA_TOL = 1e-6
TOTAL_AREA_TOL = 1e-4
PLANE_TOL = 1e-8
EXPECTED_SOURCE_AREA = 5379.25


def load(path):
    return json.loads(Path(path).read_bytes())


def reference(path):
    path = Path(path).resolve()
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def write(name, value):
    """Only this helper's dedicated output directory may receive artifacts."""
    path = OUT / name
    if path.parent.resolve() != OUT.resolve():
        raise ValueError('Output must be a direct child of ground_patch_outputs')
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return reference(path)


def verify_reference(ref):
    path = ROOT / ref['path']
    if reference(path) != ref:
        raise ValueError('Changed source reference: ' + ref['path'])
    return path


def area(polygons):
    return sum(geo.polygon_area(p) for p in polygons)


def xz(triangle):
    return [[v[0], v[2]] for v in triangle]


def triangles(polygon, plane):
    # All generated upward geometry passes through the sealed winding helper.
    return list(f.fan_upward(f.lift(polygon, plane)))


def partition(polygon, masks):
    """Return exact union-intersection pieces and the unclaimed complement."""
    remain = [polygon]
    hits = []
    for mask in masks:
        following = []
        for piece in remain:
            hit = a.clean(geo.convex_intersection(piece, mask))
            if hit:
                hits.append(hit)
                following.extend(a.subtract([piece], [mask]))
            else:
                following.append(piece)
        remain = following
        if not remain:
            break
    return hits, remain


class Regions:
    def __init__(self, records):
        self.records = list(records)
        self.index = geo._SpatialIndex(8)
        for i, record in enumerate(self.records):
            if not a.clean(record['polygon_xz_m']):
                raise ValueError('Degenerate region')
            self.index.add(i, record['polygon_xz_m'])

    def candidates(self, polygon, holding_id=None):
        for i in sorted(self.index.candidates(polygon)):
            row = self.records[i]
            if holding_id is None or row.get('holding_id') == holding_id:
                yield row

    def subtract(self, polygon):
        return a.subtract([polygon], [r['polygon_xz_m'] for r in self.candidates(polygon)])


def validate_inputs(plan_path, native_path=None, expected_plan_sha=None, collar_path=None):
    refs = {'design_plan': reference(plan_path), 'helper': reference(Path(__file__))}
    if expected_plan_sha and refs['design_plan']['sha256'] != expected_plan_sha:
        raise ValueError('Design plan changed after coordination')
    plan = load(plan_path)
    if plan['base_scene']['sha256'] != f.SCENE_SHA256:
        raise ValueError('Plan does not name the sealed R6 scene')
    if plan['base_scene']['path'] != str(f.SCENE_PATH.relative_to(ROOT)):
        raise ValueError('Wrong base scene path')
    pre = load(verify_reference(plan['source_holdings']))
    study = load(verify_reference(plan['baseline_study']))
    if study['base_scene'] != plan['base_scene']:
        raise ValueError('Baseline study is not bound to this R6 scene')
    refs.update(source_holdings=plan['source_holdings'], baseline_study=plan['baseline_study'])
    original = {h['id']: h for h in pre['holdings']}
    if set(original) != {h['id'] for h in plan['holdings']}:
        raise ValueError('The two original source holdings changed')
    for h in plan['holdings']:
        if h['polygon_parts_xz_m'] != original[h['id']]['polygon_parts_xz_m']:
            raise ValueError('Source-domain geometry changed: ' + h['id'])
        if abs(area(h['polygon_parts_xz_m']) - h['area_m2']) > AREA_TOL:
            raise ValueError('Holding source area mismatch')
    if abs(sum(h['area_m2'] for h in plan['holdings']) - EXPECTED_SOURCE_AREA) > AREA_TOL:
        raise ValueError('Expected exactly 5379.25 square metres of source holdings')
    native = None
    if native_path:
        native = load(native_path)
        refs['native_geometry'] = reference(native_path)
        if native['base_scene'] != plan['base_scene']:
            raise ValueError('Native geometry is not bound to the same frozen R6')
        if native['sources'] != plan['sources']:
            raise ValueError('Native geometry is stale relative to the current design sources')
        for spec in native['sources']:
            verify_reference(spec['source'])
        for asset in native['assets']:
            verify_reference(asset['cache'])
        placements = {p['id']: p for p in native['placements']}
        if len(placements) < len(plan['sources']):
            raise ValueError('Native source/placement count mismatch')
        for placement, spec in zip(native['placements'], plan['sources']):
            for key in ('source', 'position_m', 'yaw_rad', 'role'):
                if placement[key] != spec[key]:
                    raise ValueError('Native placement differs from current source: ' + key)
        for placement in native['placements']:
            verify_reference(placement['source'])
            verify_reference(placement['cache'])
            if placement.get('scale', [1, 1, 1]) != [1, 1, 1]:
                raise ValueError('Native bearing pack contains an unapproved scaled placement')
        for bearing in native['actual_bearing_footprints']:
            if bearing['placement_id'] not in placements or 'bottom_y_m' not in bearing:
                raise ValueError('Bearing lacks current native owner or exact bottom')
    collar = None
    if collar_path:
        collar = load(collar_path)
        refs['collar_design'] = reference(collar_path)
        if collar['base_scene'] != plan['base_scene']:
            raise ValueError('Collar is not bound to the same frozen R6')
    return plan, native, refs, collar


def make_program(plan):
    fields = []
    paths = []
    plots = []
    for h in plan['holdings']:
        program = h['ground_program']
        for p in h['polygon_parts_xz_m']:
            fields.append({'holding_id': h['id'], 'polygon_xz_m': p,
                           'material': program['default_material']})
        for p in program['service_ribbon_polygons_xz_m']:
            paths.append({'holding_id': h['id'], 'polygon_xz_m': p,
                          'material': program['service_material']})
        for p in program['productive_regions_xz_m']:
            plots.append({'holding_id': h['id'], 'polygon_xz_m': p,
                          'material': program['productive_material']})
    field_index = Regions(fields)
    # The exact source partition must be disjoint, including between holdings.
    overlap = 0.0
    for i, row in enumerate(fields):
        for j in sorted(field_index.index.candidates(row['polygon_xz_m'])):
            if j <= i:
                continue
            overlap += geo.intersection_area(row['polygon_xz_m'], fields[j]['polygon_xz_m'])
    if overlap > AREA_TOL:
        raise ValueError('Source holdings overlap by ' + str(overlap))
    return field_index, Regions(paths), Regions(plots), overlap


def verify_application(scene, patch):
    """Apply only in memory and check every unedited numeric triangle in order."""
    applied = f.apply_edits(scene, patch)
    by_material = collections.defaultdict(dict)
    for edit in patch['surface_edits']:
        by_material[edit['material']][edit['triangle_index']] = edit
    ledger = []
    all_equal = True
    for material, original in scene['surfaces'].items():
        edits = by_material[material]
        result = applied['surfaces'][material]
        cursor = 0
        unchanged_count = 0
        original_hash = hashlib.sha256()
        applied_hash = hashlib.sha256()
        for offset in range(0, len(original), 3):
            tri_index = offset // 3
            source = original[offset:offset + 3]
            if tri_index in edits:
                replacement = edits[tri_index]['replacement_triangles_xyz_m']
                count = 3 * len(replacement)
                expected = [v for t in replacement for v in t]
                if result[cursor:cursor + count] != expected:
                    raise AssertionError('Edited application differs from patch')
                cursor += count
            else:
                actual = result[cursor:cursor + 3]
                all_equal = all_equal and source == actual
                original_hash.update(json.dumps(source, separators=(',', ':'), allow_nan=False).encode() + b'\n')
                applied_hash.update(json.dumps(actual, separators=(',', ':'), allow_nan=False).encode() + b'\n')
                unchanged_count += 1
                cursor += 3
        if result[cursor:] != patch['appended_surfaces'].get(material, []):
            raise AssertionError('Append suffix differs from patch')
        ledger.append({'material': material, 'untouched_triangles': unchanged_count,
                       'ordered_source_sha256': original_hash.hexdigest(),
                       'ordered_applied_sha256': applied_hash.hexdigest(),
                       'numeric_triangle_equality_and_order': original_hash.digest() == applied_hash.digest()})
    for material, values in patch['appended_surfaces'].items():
        if material not in scene['surfaces'] and applied['surfaces'][material] != values:
            raise AssertionError('New material append array differs from patch')
    for key in scene:
        if key != 'surfaces' and applied[key] != scene[key]:
            raise AssertionError('Non-terrain scene content changed: ' + key)
    for material in ('water', 'bank'):
        if applied['surfaces'].get(material) != scene['surfaces'].get(material):
            raise AssertionError('Protected water/bank array changed')
    if not all_equal or not all(r['numeric_triangle_equality_and_order'] for r in ledger):
        raise AssertionError('Untouched source triangles changed')
    return ledger


def segment_interval(start, end, polygon):
    """Exact parameter interval where a straight edge crosses a convex polygon."""
    orientation = 1 if geo.signed_polygon_area(polygon) > 0 else -1
    lo, hi = 0.0, 1.0
    direction = [end[k] - start[k] for k in (0, 1)]
    for p, q in zip(polygon, polygon[1:] + polygon[:1]):
        edge = [q[k] - p[k] for k in (0, 1)]
        c = orientation * (edge[0]*(start[1]-p[1]) - edge[1]*(start[0]-p[0]))
        d = orientation * (edge[0]*direction[1] - edge[1]*direction[0])
        if abs(d) < 1e-12 * max(1.0, math.hypot(*edge)*math.hypot(*direction)):
            if c < -1e-8:
                return None
        elif d > 0:
            lo = max(lo, -c/d)
        else:
            hi = min(hi, -c/d)
        if hi < lo - 1e-10:
            return None
    return (max(0.0, lo), min(1.0, hi)) if hi-lo > 1e-10 else None


def road_union_audit(collar_polygon):
    """Match R01 corridor widths and its <=1 cm circumscribed rounded joins."""
    road_path = ROOT / 'world_city/concept_city_v3/registered_source/plan.json'
    roads = load(road_path)['roads']
    output = []
    for road in roads:
        for kind, width in [('traffic', road['width_m']), ('traffic_plus_shoulders', road['width_m']+4)]:
            masks = []
            metadata = []
            points = road['polyline_xz_m']
            for i, (start, end) in enumerate(zip(points, points[1:])):
                masks.append(geo.road_ribbon(start, end, width))
                metadata.append({'kind': 'segment', 'index': i})
            radius = width/2
            count = max(16, math.ceil(math.pi/math.acos(radius/(radius+.01))))
            r = radius/math.cos(math.pi/count)
            for i, center in enumerate(points):
                masks.append([[center[0]+r*math.cos(2*math.pi*j/count),
                               center[1]+r*math.sin(2*math.pi*j/count)] for j in range(count)])
                metadata.append({'kind': 'round_join_or_cap', 'index': i})
            hits = []
            local_masks = []
            for mask, description in zip(masks, metadata):
                hit = a.clean(geo.convex_intersection(collar_polygon, mask))
                if hit:
                    hits.append(dict(description, area_m2=geo.polygon_area(hit)))
                    local_masks.append(mask)
            overlap = geo.polygon_area(collar_polygon) - area(a.subtract([collar_polygon], local_masks))
            if hits or road['id'] == 'NORTH_BACK_LANE':
                output.append({'road_id': road['id'], 'kind': kind, 'width_m': width,
                               'positive_area_union_intersection_m2': overlap,
                               'component_intersections': hits})
    return {'source_plan': reference(road_path),
            'corridor_method_source': reference(ROOT/'world_city/concept_city_v3/registered_topography/revisions/r01_ownership/author.py'),
            'roads': output,
            'traffic_intersection_m2': sum(r['positive_area_union_intersection_m2'] for r in output if r['kind'] == 'traffic'),
            'traffic_plus_shoulder_intersection_m2': sum(r['positive_area_union_intersection_m2'] for r in output if r['kind'] == 'traffic_plus_shoulders')}


def prepare_collar(idx, collar, plan, fields, bearings):
    polygon = collar['polygon_xz_m']
    if len(polygon) != 4:
        raise ValueError('Collar contract expects road edge 0-1, stair edge 2-3, and two side edges')
    supplied = [f.upward(row['triangle_xyz_m']) for row in collar['triangles']]
    polys = [xz(t) for t in supplied]
    if any(f.normal_y(t) <= 0 for t in supplied):
        raise ValueError('Collar contains a non-upward top')
    if abs(area(polys) - geo.polygon_area(polygon)) > AREA_TOL:
        raise ValueError('Collar supplied area differs from domain')
    if area(a.subtract([polygon], polys)) > AREA_TOL:
        raise ValueError('Collar triangles do not cover their exact domain')
    if any(area(a.subtract([p], [polygon])) > AREA_TOL for p in polys):
        raise ValueError('Collar triangle leaves accepted finite domain')
    if sum(geo.intersection_area(p, q) for i, p in enumerate(polys) for q in polys[i+1:]) > AREA_TOL:
        raise ValueError('Collar supplied tops overlap')
    planes = [a.plane(t) for t in supplied]
    grades = [math.hypot(p[0], p[1]) for p in planes]
    if max(grades) > .12 + 1e-9:
        raise ValueError('Collar exceeds the requested 12 percent full-plane grade')
    cover = idx.cover(polygon)
    old_polys = [r['intersection_polygon_xz_m'] for r in cover]
    if area(a.subtract([polygon], old_polys)) > AREA_TOL or abs(area(old_polys) - geo.polygon_area(polygon)) > AREA_TOL:
        raise ValueError('Collar lacks exact single-layer frozen terrain coverage')
    contacts = []
    for label, rows in [('existing_native', plan.get('native_reservations', [])), ('new_native', bearings)]:
        for row in rows:
            ar = geo.intersection_area(polygon, row['polygon_xz_m'])
            if ar > AREA_TOL:
                contacts.append({'kind': label, 'id': row['id'], 'area_m2': ar})
    if contacts:
        raise ValueError('Finite collar overlaps native reservations: ' + json.dumps(contacts))
    road_audit = road_union_audit(polygon) if 'base_scene' in plan else None
    if road_audit and road_audit['traffic_intersection_m2'] > AREA_TOL:
        write('collar_rejected_road_audit.json', road_audit)
        raise ValueError('Collar changes protected public traffic; see collar_rejected_road_audit.json')
    sides = []
    closures = []
    road_seam_max_error = 0.0
    max_change = 0.0
    for edge_i in (0, 1, 3):  # Never close the native-stair edge 2->3.
        start, end = polygon[edge_i], polygon[(edge_i+1) % 4]
        delta = [end[k]-start[k] for k in (0, 1)]
        cuts = [0.0, 1.0]
        nearby = [idx.records[i] for i in sorted(idx.index.candidates([start, end]))]
        for row in nearby:
            hit = segment_interval(start, end, row['polygon_xz_m'])
            if hit:
                cuts.extend(hit)
        for p in polys:
            hit = segment_interval(start, end, p)
            if hit:
                cuts.extend(hit)
        cuts.sort()
        breaks = []
        for t in cuts:
            if not breaks or t-breaks[-1] > 1e-9:
                breaks.append(t)
        for lo, hi in zip(breaks, breaks[1:]):
            mid = [start[k]+delta[k]*(lo+hi)/2 for k in (0, 1)]
            old = [r for r in nearby if geo.point_in_convex_polygon(mid, r['polygon_xz_m'], 1e-8)]
            new_ids = [i for i, p in enumerate(polys) if geo.point_in_convex_polygon(mid, p, 1e-8)]
            if not old or not new_ids:
                raise ValueError('Collar edge has a frozen-plane coverage gap')
            if edge_i == 0 and 'base_scene' in plan:
                old = [r for r in old if r['material'] == 'road']
                if not old:
                    raise ValueError('Collar road seam has no actual road-triangle coverage')
            old_values = [a.height(r['plane_y_xz_m'], mid) for r in old]
            if max(old_values)-min(old_values) > PLANE_TOL:
                raise ValueError('Ambiguous discontinuous frozen ground along collar edge: ' + json.dumps({'edge': edge_i, 'interval': [lo, hi], 'midpoint': mid, 'sources': [{'material': r['material'], 'triangle_index': r['triangle_index'], 'height': y} for r,y in zip(old, old_values)]}))
            source = old[0]
            old_plane = source['plane_y_xz_m']
            new_plane = planes[new_ids[0]]
            point = lambda t: [start[k]+delta[k]*t for k in (0, 1)]
            difference = lambda t: a.height(new_plane, point(t))-a.height(old_plane, point(t))
            d0, d1 = difference(lo), difference(hi)
            max_change = max(max_change, abs(d0), abs(d1))
            if edge_i == 0:
                road_seam_max_error = max(road_seam_max_error, abs(d0), abs(d1))
                continue
            parameters = [lo, hi]
            if d0*d1 < 0:
                parameters.insert(1, lo+(hi-lo)*(-d0)/(d1-d0))
            for t0, t1 in zip(parameters, parameters[1:]):
                p0, p1 = point(t0), point(t1)
                old0, old1 = a.height(old_plane, p0), a.height(old_plane, p1)
                new0, new1 = a.height(new_plane, p0), a.height(new_plane, p1)
                if max(abs(new0-old0), abs(new1-old1)) <= PLANE_TOL:
                    continue
                quad = [[p0[0], old0, p0[1]], [p1[0], old1, p1[1]],
                        [p1[0], new1, p1[1]], [p0[0], new0, p0[1]]]
                orientation = 1 if geo.signed_polygon_area(polygon) > 0 else -1
                outward = [orientation*delta[1], -orientation*delta[0]]
                sign = 1 if difference((t0+t1)/2) > 0 else -1
                desired = [v*sign for v in outward]
                emitted = []
                for tri in ([quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]):
                    u, v = [[tri[j][k]-tri[0][k] for k in range(3)] for j in (1, 2)]
                    normal = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                    if math.sqrt(sum(n*n for n in normal)) <= 1e-10:
                        continue
                    if abs(normal[1]) > 1e-8:
                        raise AssertionError('Collar side closure is not vertical')
                    if normal[0]*desired[0]+normal[2]*desired[1] < 0:
                        tri = [tri[0], tri[2], tri[1]]
                    closures.extend(tri)
                    emitted.append(tri)
                sides.append({'edge_index': edge_i, 'parameter_interval': [t0, t1],
                              'source_material': source['material'], 'source_triangle_index': source['triangle_index'],
                              'old_plane_y_xz_m': old_plane, 'new_plane_y_xz_m': new_plane,
                              'old_height_endpoints_m': [old0, old1], 'new_height_endpoints_m': [new0, new1],
                              'triangles_xyz_m': emitted})
    if road_seam_max_error > PLANE_TOL:
        raise ValueError('Collar does not meet exact frozen road edge: ' + str(road_seam_max_error))
    audit = {'area_m2': geo.polygon_area(polygon), 'maximum_grade': max(grades),
             'original_plane_source_count': len(cover), 'road_seam_maximum_error_m': road_seam_max_error,
             'side_closure_count': len(closures)//3, 'side_closure_segments': sides,
             'closed_edges': [1, 3], 'open_edges': [0, 2], 'native_contacts': contacts,
             'maximum_side_height_change_m': max_change, 'road_union_audit': road_audit,
             'ownership_policy': 'Explicit finite shoulder-to-pedestrian collar transfer; full traffic ribbon and round-join union remain protected.',
             'original_water_and_bank_faces_retained': True,
             'closure_material': 'ground_earth', 'closure_orientation': 'Into cut / outward from fill'}
    return {'appended_surfaces': {'ground_stone': [v for t in supplied for v in t], 'ground_earth': closures},
            'outside_holdings_m2': area(fields.subtract(polygon)), 'audit': audit}


def build_patch(scene, plan, native=None, collar=None):
    fields, paths, plots, domain_overlap = make_program(plan)
    windows = [f.bounds([v for p in h['polygon_parts_xz_m'] for v in p]) for h in plan['holdings']]
    if collar is not None:
        windows.append(f.bounds(collar['polygon_xz_m']))
    idx = f.SurfaceIndex(scene, windows=windows, margin=0)
    bearings = [] if native is None else native['actual_bearing_footprints']
    native_index = Regions(bearings)
    bearing_checks = []
    for bearing in bearings:
        p = bearing['polygon_xz_m']
        outside = area(fields.subtract(p))
        coverage = idx.cover(p)
        covered_polygons = [r['intersection_polygon_xz_m'] for r in coverage]
        missing = area(a.subtract([p], covered_polygons))
        double = area(covered_polygons) - (geo.polygon_area(p) - missing)
        values = [a.height(r['plane_y_xz_m'], v) for r in coverage for v in r['intersection_polygon_xz_m']]
        embed = min(values) - bearing['bottom_y_m'] if values else None
        row = {'bearing_id': bearing['id'], 'area_m2': geo.polygon_area(p),
               'outside_source_holdings_m2': outside, 'missing_frozen_ground_m2': missing,
               'overlapping_frozen_ground_m2': double, 'minimum_embed_m': embed}
        bearing_checks.append(row)
        if outside > AREA_TOL or missing > AREA_TOL or abs(double) > AREA_TOL or embed is None or embed < -PLANE_TOL:
            raise ValueError('Invalid current native soil bearing: ' + json.dumps(row))
    collar_data = prepare_collar(idx, collar, plan, fields, bearings) if collar is not None else None
    edits = []
    appended = collections.defaultdict(list)
    lineage = []
    per_source = []
    totals = collections.defaultdict(float)
    holding_totals = {h['id']: collections.defaultdict(float) for h in plan['holdings']}
    height_ranges = {h['id']: [math.inf, -math.inf] for h in plan['holdings']}
    max_plane_error = 0.0
    max_containment_error = 0.0

    def emit(poly, source, material, holding_id, kind, local):
        nonlocal max_plane_error, max_containment_error
        plane = source['plane_y_xz_m']
        ts = triangles(poly, plane)
        emitted_area = area([xz(t) for t in ts])
        if abs(emitted_area - geo.polygon_area(poly)) > AREA_TOL:
            raise AssertionError('Fan triangulation lost area')
        start = len(appended[material]) // 3
        for t in ts:
            if f.normal_y(t) <= 0:
                raise AssertionError('Non-upward generated triangle')
            max_plane_error = max(max_plane_error, *(abs(v[1] - a.height(plane, [v[0], v[2]])) for v in t))
            max_containment_error = max(max_containment_error, area(a.subtract([xz(t)], [source['polygon_xz_m']])))
            appended[material].extend(t)
        lineage.append({'source_material': source['material'], 'source_triangle_index': source['triangle_index'],
                        'source_triangle_sha256': source['source_triangle_sha256'],
                        'source_plane_y_xz_m': plane, 'appended_material': material,
                        'appended_triangle_start': start, 'appended_triangle_count': len(ts),
                        'holding_id': holding_id, 'kind': kind, 'area_m2': emitted_area})
        totals[kind + '_area_m2'] += emitted_area
        holding_totals[holding_id][kind + '_area_m2'] += emitted_area
        local['appended_area_m2'] += emitted_area

    for source in idx.records:
        p = source['polygon_xz_m']
        candidate_fields = list(fields.candidates(p))
        collar_hit = a.clean(geo.convex_intersection(p, collar['polygon_xz_m'])) if collar is not None else None
        remain = a.subtract([p], [collar['polygon_xz_m']]) if collar_hit else [p]
        if collar_hit:
            totals['collar_replaced_source_area_m2'] += geo.polygon_area(collar_hit)
            for field in candidate_fields:
                shared = a.clean(geo.convex_intersection(collar_hit, field['polygon_xz_m']))
                if shared:
                    shared_area = geo.polygon_area(shared)
                    holding_totals[field['holding_id']]['collar_replaced_source_area_m2'] += shared_area
                    holding_totals[field['holding_id']]['actual_source_ground_area_m2'] += shared_area
                    totals['actual_source_ground_area_m2'] += shared_area
        field_parts = []
        for field in candidate_fields:
            following = []
            for part in remain:
                hit = a.clean(geo.convex_intersection(part, field['polygon_xz_m']))
                if hit:
                    field_parts.append((hit, field))
                    following.extend(a.subtract([part], [field['polygon_xz_m']]))
                else:
                    following.append(part)
            remain = following
        if not field_parts and not collar_hit:
            continue
        plane = source['plane_y_xz_m']
        replacement = [t for part in remain for t in triangles(part, plane)]
        local = {'material': source['material'], 'triangle_index': source['triangle_index'],
                 'original_area_m2': geo.polygon_area(p), 'outside_preserved_area_m2': area(remain),
                 'field_intersection_area_m2': 0.0, 'native_cut_area_m2': 0.0, 'appended_area_m2': 0.0,
                 'collar_replaced_area_m2': geo.polygon_area(collar_hit) if collar_hit else 0.0}
        for t in replacement:
            if f.normal_y(t) <= 0:
                raise AssertionError('Non-upward outside replacement')
            max_plane_error = max(max_plane_error, *(abs(v[1] - a.height(plane, [v[0], v[2]])) for v in t))
        for hit, field in field_parts:
            hid = field['holding_id']
            hit_area = geo.polygon_area(hit)
            local['field_intersection_area_m2'] += hit_area
            totals['actual_source_ground_area_m2'] += hit_area
            holding_totals[hid]['actual_source_ground_area_m2'] += hit_area
            yy = [a.height(plane, v) for v in hit]
            height_ranges[hid][0] = min(height_ranges[hid][0], *yy)
            height_ranges[hid][1] = max(height_ranges[hid][1], *yy)
            clear = native_index.subtract(hit)
            cut_area = hit_area - area(clear)
            local['native_cut_area_m2'] += cut_area
            totals['native_soil_bearing_cut_area_m2'] += cut_area
            holding_totals[hid]['native_soil_bearing_cut_area_m2'] += cut_area
            for piece in clear:
                ground = [piece]
                for route in paths.candidates(piece, hid):
                    following = []
                    for part in ground:
                        route_hits, other = partition(part, [route['polygon_xz_m']])
                        for q in route_hits:
                            emit(q, source, route['material'], hid, 'service_path', local)
                        following.extend(other)
                    ground = following
                if math.hypot(plane[0], plane[1]) > 1e-8:
                    for part in ground:
                        emit(part, source, 'ground_grass', hid, 'retained_working_bank', local)
                    continue
                for plot in plots.candidates(piece, hid):
                    following = []
                    for part in ground:
                        plot_hits, other = partition(part, [plot['polygon_xz_m']])
                        for q in plot_hits:
                            emit(q, source, plot['material'], hid, 'productive_plot', local)
                        following.extend(other)
                    ground = following
                for part in ground:
                    emit(part, source, field['material'], hid, 'productive_ground', local)
        local['partition_area_error_m2'] = abs(local['original_area_m2'] - local['outside_preserved_area_m2'] - local['field_intersection_area_m2'] - local['collar_replaced_area_m2'])
        local['conservation_error_m2'] = abs(local['original_area_m2'] - local['outside_preserved_area_m2'] - local['native_cut_area_m2'] - local['appended_area_m2'] - local['collar_replaced_area_m2'])
        if local['partition_area_error_m2'] > AREA_TOL or local['conservation_error_m2'] > AREA_TOL:
            raise AssertionError('Source-triangle area was not conserved: ' + json.dumps(local))
        per_source.append(local)
        edits.append({'material': source['material'], 'triangle_index': source['triangle_index'],
                      'source_triangle_sha256': source['source_triangle_sha256'],
                      'replacement_triangles_xyz_m': replacement})

    coverage_checks = []
    for field in fields.records:
        p = field['polygon_xz_m']
        coverage = idx.cover(p)
        pieces = [r['intersection_polygon_xz_m'] for r in coverage]
        missing = area(a.subtract([p], pieces))
        overlap = area(pieces) - (geo.polygon_area(p) - missing)
        if abs(overlap) > AREA_TOL:
            raise AssertionError('Overlapping upward frozen terrain within holding')
        holding_totals[field['holding_id']]['existing_uncovered_source_area_m2'] += missing
        coverage_checks.append({'holding_id': field['holding_id'], 'source_area_m2': geo.polygon_area(p),
                                'existing_uncovered_source_area_m2': missing, 'coverage_overlap_m2': overlap})
    for h in plan['holdings']:
        stats = holding_totals[h['id']]
        stats['source_holding_area_m2'] = h['area_m2']
        error = abs(h['area_m2'] - stats['actual_source_ground_area_m2'] - stats['existing_uncovered_source_area_m2'])
        stats['source_domain_conservation_error_m2'] = error
        if error > TOTAL_AREA_TOL:
            raise AssertionError('Source-domain coverage did not conserve area')
    if max_plane_error > PLANE_TOL or max_containment_error > AREA_TOL:
        raise AssertionError('A generated triangle left its original plane/domain')
    union_bearings = a.disjoint_union([r['polygon_xz_m'] for r in bearings])
    if abs(totals['native_soil_bearing_cut_area_m2'] - area(union_bearings)) > TOTAL_AREA_TOL:
        raise AssertionError('The native cut does not exactly equal the new soil-bearing union')
    if collar_data is not None:
        for material, rows in collar_data['appended_surfaces'].items():
            start = len(appended[material]) // 3
            appended[material].extend(rows)
            lineage.append({'source_material': None, 'source_triangle_index': None,
                            'appended_material': material, 'appended_triangle_start': start,
                            'appended_triangle_count': len(rows)//3, 'holding_id': None,
                            'kind': 'finite_private_collar' if material == 'ground_stone' else 'finite_collar_side_closure',
                            'source_refs_in_collar_audit': True})
        totals['collar_outside_holding_area_m2'] = collar_data['outside_holdings_m2']
    total_conservation_error = abs(totals['actual_source_ground_area_m2'] + totals['collar_outside_holding_area_m2'] - totals['native_soil_bearing_cut_area_m2'] - sum(geo.polygon_area(xz(vs[j:j+3])) for vs in appended.values() for j in range(0, len(vs), 3)))
    if total_conservation_error > TOTAL_AREA_TOL:
        raise AssertionError('Global patch area conservation failed')
    summary = dict(totals)
    summary.update(source_holdings_m2=sum(h['area_m2'] for h in plan['holdings']),
                   edited_original_triangles=len(edits), edited_vertical_triangles=0,
                   appended_triangles=sum(len(vs) // 3 for vs in appended.values()),
                   exact_new_native_bearings=len(bearings), exact_native_union_area_m2=area(union_bearings),
                   holding_areas={k: dict(v) for k, v in holding_totals.items()},
                   frozen_height_ranges_m=height_ranges, terrain_heights_changed=collar is not None,
                   water_changed=False, bank_changed=False,
                   native_cut_status='CURRENT_EXACT_NATIVE_GEOMETRY' if native is not None else 'PENDING_NO_NATIVE_GEOMETRY_SUPPLIED',
                   private_stair_collar_status='EXACT_FINITE_COLLAR_WITH_SIDE_CLOSURES' if collar is not None else 'PENDING_SEPARATE_FINITE_HEIGHT_PATCH',
                   collar_audit=collar_data['audit'] if collar_data else None,
                   activation=False, whole_scene_exported=False)
    patch = {'schema': 'riverstone.frozen_scene.local_surface_patch.v1',
             'id': 'productive_ground_phase02_frozen_r6',
             'status': 'INACTIVE_FINITE_MATERIAL_AND_EXACT_BEARING_PATCH_COLLAR_AND_ACCESS_PENDING',
             'base_scene_sha256': f.SCENE_SHA256,
             'source_surface_hashes': {m: f.canonical_sha(scene['surfaces'][m]) for m in sorted({e['material'] for e in edits})},
             'surface_edits': edits, 'appended_surfaces': dict(appended),
             'removed_foundation_proxy_ids': [], 'summary': summary,
             'limits': ['Private stair collar is the only height override when explicitly supplied; otherwise pending.',
                        'All material fragments inherit their exact original R6 triangle plane.',
                        'Existing missing ground/native holes, water, bank and non-upward triangles stay unchanged.',
                        'No scene activation, whole-city export, native compile, GUI or route/controller acceptance.',
                        'Shared original indices require geometric composition; patches must not be applied sequentially.']}
    untouched = verify_application(scene, patch)
    tests = {'status': 'PASS_FINITE_GROUND_INVARIANTS', 'base_scene_sha256': f.SCENE_SHA256,
             'source_domain_overlap_m2': domain_overlap,
             'maximum_source_partition_error_m2': max([r['partition_area_error_m2'] for r in per_source] or [0]),
             'maximum_source_conservation_error_m2': max([r['conservation_error_m2'] for r in per_source] or [0]),
             'total_ground_conservation_error_m2': total_conservation_error,
             'maximum_original_plane_error_m': max_plane_error,
             'maximum_new_triangle_outside_original_domain_m2': max_containment_error,
             'all_new_upward_triangles_positive_normal_y': True,
             'all_original_terrain_heights_preserved': collar is None,
             'all_original_terrain_heights_outside_finite_collar_preserved': True,
             'untouched_triangles_equal_and_ordered': True,
             'water_bank_and_all_nonterrain_scene_content_unchanged': True,
             'existing_holes_not_filled': True, 'new_native_holes_equal_exact_bearing_union': True,
             'private_collar_included': collar is not None,
             'collar_audit': collar_data['audit'] if collar_data else None, 'native_geometry_supplied': native is not None,
             'native_bearing_checks': bearing_checks, 'source_triangle_checks': per_source,
             'source_domain_coverage_checks': coverage_checks, 'summary': summary,
             'application_in_memory_only': True}
    composition = {'base_scene_sha256': f.SCENE_SHA256,
                   'policy': 'Compose shared original indices on the frozen source triangle, never concatenate edit rows or apply by shifted indices. Intersect preserved outside polygons. Reject overlapping reprogrammed domains until one semantic owner is chosen. Native holes take precedence over appended top surfaces. Any later finite collar replaces only its accepted domain and must clip this patch\'s appended geometry there.',
                   'ownership_domains': fields.records,
                   'exact_native_cut_domains': bearings,
                   'appended_triangle_lineage': lineage,
                   'source_triangle_partition_checks': per_source,
                   'private_collar_status': 'EXACT_FINITE_OVERRIDE' if collar is not None else 'PENDING_NO_HEIGHT_OVERRIDE',
                   'private_collar_domain': collar['polygon_xz_m'] if collar else None}
    return patch, tests, untouched, composition


def self_test():
    def tri(x0, z0, x1, z1, slope=0):
        points = [[x0, 2 + slope*x0, z0], [x1, 2 + slope*x1, z0],
                  [x1, 2 + slope*x1, z1], [x0, 2 + slope*x0, z1]]
        return [v for t in f.fan_upward(points) for v in t]
    holding = {'id': 'TEST', 'area_m2': 16.0,
               'polygon_parts_xz_m': [[[0, 0], [4, 0], [4, 4], [0, 4]]],
               'ground_program': {'default_material': 'ground_grass', 'productive_material': 'ground_earth',
                                  'service_material': 'ground_stone',
                                  'productive_regions_xz_m': [[[0, 0], [1, 0], [1, 4], [0, 4]]],
                                  'service_ribbon_polygons_xz_m': [[[1, 0], [3, 0], [3, 4], [1, 4]],
                                                                 [[2, 0], [4, 0], [4, 4], [2, 4]]]}}
    # A 1 m² preexisting hole is retained; one sloped half and one untouched tri
    # exercise plane inheritance, working banks, material overlap and winding.
    ground = tri(0, 0, 2, 4, .1) + tri(2, 0, 4, 3) + tri(3, 3, 4, 4) + tri(8, 0, 9, 1)
    vertical = [[0, 0, 0], [0, 2, 0], [0, 2, 4]]
    scene = {'surfaces': {'land': ground + vertical, 'water': tri(20, 20, 21, 21),
                          'bank': vertical}, 'common_instances': [{'id': 'retained'}]}
    native = {'actual_bearing_footprints': [{'id': 'soil', 'placement_id': 'test',
               'polygon_xz_m': [[.5, .5], [1.5, .5], [1.5, 1.5], [.5, 1.5]], 'bottom_y_m': 1.0}]}
    patch, tests, untouched, composition = build_patch(scene, {'holdings': [holding]}, native)
    stats = patch['summary']
    assert abs(stats['native_soil_bearing_cut_area_m2'] - 1) < AREA_TOL
    assert abs(stats['holding_areas']['TEST']['existing_uncovered_source_area_m2'] - 1) < AREA_TOL
    assert stats['edited_vertical_triangles'] == 0
    assert stats['retained_working_bank_area_m2'] > 0
    assert stats['service_path_area_m2'] > 0
    assert len(composition['appended_triangle_lineage']) > 0
    patch_no_native, *_ = build_patch(scene, {'holdings': [holding]})
    assert patch_no_native['summary']['native_soil_bearing_cut_area_m2'] == 0
    failed = False
    invalid = {'actual_bearing_footprints': [{**native['actual_bearing_footprints'][0],
               'polygon_xz_m': [[3.5, 3.5], [4.5, 3.5], [4.5, 4.5], [3.5, 4.5]]}]}
    try:
        build_patch(scene, {'holdings': [holding]}, invalid)
    except ValueError:
        failed = True
    assert failed, 'Outside-source native bearing must fail closed'
    collar_polygon = [[0, 0], [1, 0], [1, 2], [0, 2]]
    collar_test = {'polygon_xz_m': collar_polygon, 'triangles': [
        {'triangle_xyz_m': t} for t in triangles(collar_polygon, [.1, .05, 2])]}
    with_collar, collar_tests, *_ = build_patch(scene, {'holdings': [holding]}, collar=collar_test)
    assert with_collar['summary']['collar_audit']['side_closure_count'] > 0
    assert collar_tests['collar_audit']['road_seam_maximum_error_m'] < PLANE_TOL
    assert collar_tests['all_original_terrain_heights_outside_finite_collar_preserved']
    # Source-index safety rejects duplicate rows before any application.
    duplicate = dict(patch, surface_edits=patch['surface_edits'] + patch['surface_edits'][:1])
    failed = False
    try:
        f.apply_edits(scene, duplicate)
    except ValueError:
        failed = True
    assert failed, 'Duplicate original indices must be composed geometrically'
    return {'status': 'PASS_SYNTHETIC_SELF_TESTS', 'uses_frozen_scene': False,
            'tests': ['upward fan winding', 'nonzero original slope preserved',
                      'overlapping service masks partitioned once', 'existing hole retained',
                      'exact new bearing cut', 'no-native mode cuts nothing',
                      'outside-domain bearing rejected', 'duplicate source index rejected',
                      'untouched triangle equality and order', 'water and bank preservation',
                      'finite collar priority and exact road seam', 'side-only cut/fill closure'],
            'maximum_plane_error_m': tests['maximum_original_plane_error_m'],
            'maximum_source_area_error_m2': tests['maximum_source_conservation_error_m2'],
            'helper': reference(Path(__file__))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--self-test', action='store_true')
    action.add_argument('--build', action='store_true')
    parser.add_argument('--plan', type=Path, default=HERE / 'design_plan.json')
    parser.add_argument('--native-geometry', type=Path, help='Explicit current exact native geometry; no automatic fallback')
    parser.add_argument('--expected-plan-sha256')
    parser.add_argument('--collar-design', type=Path, help='Explicit finite private collar; exact supplied triangles plus side closures')
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
        print(json.dumps(write('self_test_results.json', result)))
        return
    started = time.monotonic()
    plan, native, refs, collar = validate_inputs(args.plan, args.native_geometry, args.expected_plan_sha256, args.collar_design)
    scene = f.load_scene()
    patch, tests, untouched, composition = build_patch(scene, plan, native, collar)
    # Fail closed if another worker revised a consumed source while we ran.
    for name, ref in refs.items():
        verify_reference(ref)
    patch['source_refs'] = refs
    patch['base_scene'] = plan['base_scene']
    tests.update(source_refs=refs, total_seconds=time.monotonic() - started,
                 peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    patch_ref = write('surface_patch.json', patch)
    tests['patch'] = patch_ref
    write('ground_tests.json', tests)
    write('index_ledger.json', {'patch': patch_ref, 'base_scene_sha256': f.SCENE_SHA256,
                               'changed_indices_by_material': {m: sorted(e['triangle_index'] for e in patch['surface_edits'] if e['material'] == m) for m in patch['source_surface_hashes']},
                               'untouched_triangle_ledger': untouched})
    composition['patch'] = patch_ref
    write('composition_ledger.json', composition)
    print(json.dumps({'patch': patch_ref, 'summary': patch['summary'], 'seconds': tests['total_seconds']}))


if __name__ == '__main__':
    main()
