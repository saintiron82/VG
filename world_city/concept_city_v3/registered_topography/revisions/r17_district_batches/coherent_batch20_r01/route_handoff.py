"""Exact route chains, retaining measured legacy public steps explicitly."""
import json, math
from .screen import HERE, write
from .. import author as a
from ..coherent_batch18_r01.route_interval import interval

def run():
    hand = json.loads((HERE / 'physical_owner_handoff_r02.json').read_bytes())
    layout = json.loads((HERE / 'effective_source_layout_r03.json').read_bytes())
    native = json.loads((HERE / 'native_pack_ready_r02.json').read_bytes())
    public = hand['public_fixed_regions']
    regions = public + hand['physical_earth_owners']
    public_count = len(public)
    index = a.geo._SpatialIndex(2)
    for i, region in enumerate(regions):
        index.add(i, region['polygon_xz_m'])
    entries = []
    selected = set(hand['accepted_holding_ids'])
    for holding in layout['holdings']:
        if holding['id'] not in selected:
            continue
        xyz, errors, inherited, plane_segments = [], [], [], []
        previous_owner = None
        for p, q in zip(holding['external_route'], holding['external_route'][1:]):
            if math.dist(p, q) < 1e-10:
                continue
            spans = [(span, j) for j in sorted(index.candidates([p, q])) if (span := interval(p, q, regions[j]['polygon_xz_m']))]
            knots = sorted({0.0, 1.0} | {t for span, _ in spans for t in span})
            knots = [t for k, t in enumerate(knots) if k == 0 or t - knots[k - 1] > 1e-9]
            for lo, hi in zip(knots, knots[1:]):
                mid = (lo + hi) / 2
                owners = [j for span, j in spans if span[0] - 1e-12 <= mid <= span[1] + 1e-12]
                if not owners:
                    errors.append(dict(kind='uncovered_centerline_interval', a_xz_m=p, b_xz_m=q, parameters=[lo, hi]))
                    continue
                midpoint = [p[k] + mid * (q[k] - p[k]) for k in (0, 1)]
                values = [a.common.height(regions[j]['plane_y_xz_m'], midpoint) for j in owners]
                if max(values) - min(values) > 1e-6:
                    errors.append(dict(kind='positive_interval_owner_disagreement', point_xz_m=midpoint, heights_m=values))
                    continue
                owner = owners[0]
                points = []
                for parameter in (lo, hi):
                    xz = [p[k] + parameter * (q[k] - p[k]) for k in (0, 1)]
                    points.append([xz[0], a.common.height(regions[owner]['plane_y_xz_m'], xz), xz[1]])
                if xyz and math.hypot(xyz[-1][0] - points[0][0], xyz[-1][2] - points[0][2]) < 1e-7:
                    step = abs(xyz[-1][1] - points[0][1])
                    if step > 1e-6:
                        inherited_public = previous_owner is not None and previous_owner < public_count and owner < public_count and all(regions[j].get('source_kind') == 'actual_retained_r04_top' for j in (previous_owner, owner))
                        event = dict(point_xz_m=[points[0][0], points[0][2]], before_y_m=xyz[-1][1], after_y_m=points[0][1], absolute_step_m=step, before_owner_id=regions[previous_owner]['id'] if previous_owner is not None else None, after_owner_id=regions[owner]['id'])
                        if inherited_public:
                            inherited.append(dict(event, classification='UNCHANGED_ACTUAL_R04_PUBLIC_STEP'))
                        else:
                            errors.append(dict(event, kind='new_private_or_public_boundary_height_seam'))
                for point in points:
                    if not xyz or math.dist(point, xyz[-1]) > 1e-8:
                        xyz.append(point)
                previous_owner = owner
                plane_segments.append(dict(owner_id=regions[owner]['id'], endpoints_xyz_m=points, inherited_public=owner < public_count))
        entry = dict(id=holding['id'] + ':PUBLIC_ENTRY', holding_id=holding['id'], public_road_id=holding['public_road_id'], width_m=holding['external_width_m'], polyline_xyz_m=list(reversed(xyz)), public_start_xyz_m=xyz[-1] if xyz else None, court_gate_xyz_m=xyz[0] if xyz else None, source_reserved_polygons_xz_m=holding['external_route_polygons_xz_m'], exact_plane_segments=plane_segments, inherited_public_steps=inherited, maximum_centerline_grade=max([abs(v[1]-u[1])/math.hypot(v[0]-u[0],v[2]-u[2]) for u,v in zip(xyz,xyz[1:]) if math.hypot(v[0]-u[0],v[2]-u[2]) > 1e-8] + [0]), errors=errors, status='SOURCE_BOUND_WITH_DISCLOSED_INHERITED_PUBLIC_STEPS' if not errors and inherited else 'SOURCE_PLANES_BOUND' if not errors else 'HELD_ROUTE_HANDOFF')
        entries.append(entry)
    access = json.loads((HERE / 'atomic_rebind_binding_r01.json').read_bytes())['exact_internal_routes']
    failures = [r['holding_id'] for r in entries if r['errors']]
    result = dict(schema='riverstone.r17.ready_private_routes.v2', status='SOURCE_BOUND_PENDING_COMPOSED_SCENE_REPLAY', terrain_handoff=dict(path=str((HERE / 'physical_owner_handoff_r02.json').relative_to(a.ROOT)), sha256=a.sha(HERE / 'physical_owner_handoff_r02.json')), base_scene_sha256=a.SCENE_SHA256, retained_public_scene_sha256='3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7', accepted_holding_ids=sorted(selected), entries=entries, internal_door_routes=access, actual_doors=native['actual_doors'], failures=failures, summary=dict(entries=len(entries), actual_doors=len(native['actual_doors']), internal_door_routes=len(access), source_profile_holds=len(failures), unchanged_public_step_events=sum(len(r['inherited_public_steps']) for r in entries)), policy='Each XYZ lies on its original source plane. Both heights at inherited public steps are retained; no averaging, public-face rewrite or controller success is claimed.', activation=False)
    write('route_handoff_ready_r02.json', result)
    print(result['summary'], failures, flush=True)

if __name__ == '__main__':
    run()
