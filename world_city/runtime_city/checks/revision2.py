#!/usr/bin/env python3
"""Independent r2 property, sampled-envelope, fabric and all-row-door audit.

Read-only. Reuses r1 numerical geometry but never edits its checker or source
brief. Access results are bounded 2D clearance proposals, not navmesh/gameplay.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location('r1_placement_geometry', Path(__file__).with_name('placement.py'))
g = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(g)
TOL = g.CAD_TOLERANCE_M
ACCESS_WIDTH_M = 1.4
MAX_FRONTAGE_OFFSET_M = 3.0
MAX_CONNECTOR_LENGTH_M = 80.0


def _resources(asset):
    if 'render_path' in asset:
        return [('default', asset)]
    return [(k, v) for k, v in asset.items() if isinstance(v, dict) and 'render_path' in v]


def union_bounds(bounds):
    return {'min': [min(b['min'][j] for b in bounds) for j in range(3)],
            'max': [max(b['max'][j] for b in bounds) for j in range(3)]}


def mesh_vertex_bounds(render):
    vertices = [p for group in render.get('groups', []) for quad in group.get('quads', []) for p in quad]
    if not vertices or not all(g._vector(p, 3) for p in vertices):
        raise ValueError('No finite compiled quad vertices')
    return {'min': [min(p[j] for p in vertices) for j in range(3)],
            'max': [max(p[j] for p in vertices) for j in range(3)]}


def _same_bounds(a, b):
    return g._valid_bounds(a) and g._valid_bounds(b) and all(abs(a[k][j] - b[k][j]) <= TOL for k in ('min', 'max') for j in range(3))


def _contains_bounds(a, b):
    return g._valid_bounds(a) and g._valid_bounds(b) and all(a['min'][j] - TOL <= b['min'][j] and a['max'][j] + TOL >= b['max'][j] for j in range(3))


def _xz(world):
    return [world[0], world[2]]


def _ribbons(points, width):
    # Closed 16-sided circumscribed turn caps prevent a bend from hiding the
    # outside-corner gap left by two plain segment rectangles.
    polygons = [g.road_ribbon(a, b, width) for a, b in zip(points, points[1:]) if math.dist(a, b) > 1e-8]
    radius = width / 2 / math.cos(math.pi / 16)
    for center in points[1:-1]:
        polygons.append([[center[0] + radius * math.cos(j * math.pi / 8),
                          center[1] + radius * math.sin(j * math.pi / 8)] for j in range(16)])
    return polygons


def _overlap(a, b):
    return g.positive_area_overlap(a, b, TOL)


def frontage_route_proposal(instance, doors, bounds, road_connection, obstacles, index):
    """Try finite, explicitly bounded shared-frontage routes from EVERY door.

    Door-to-front stubs may cross their own roof/threshold envelope only. All
    subsequent frontage/connector ribbons, including turn caps, must avoid that
    envelope too. No other building or blocking fabric gets an exception.
    """
    iid, yaw, pos = instance['id'], instance['yaw_rad'], instance['position_m']
    half = ACCESS_WIDTH_M / 2
    target = g.inverse_transform_point_m(road_connection, pos, yaw)
    min_x, max_x = min(p[0] for p in doors), max(p[0] for p in doors)
    target_x = max(min_x, min(max_x, target[0]))
    joins = list(dict.fromkeys([target_x, (min_x + max_x) / 2, min_x, max_x]))
    best = None

    def world(local):
        return _xz(g.transform_point_m([local[0], 0, local[1]], pos, yaw))

    def collisions(polygons, allow_owner=False):
        found = set()
        for polygon in polygons:
            for key in index.candidates(polygon):
                if allow_owner and key == 'building:' + iid:
                    continue
                if _overlap(polygon, obstacles[key]):
                    found.add(key)
        return sorted(found)

    def caps(local_points):
        return [[world([p[0] - half, p[1] - half]), world([p[0] + half, p[1] - half]),
                 world([p[0] + half, p[1] + half]), world([p[0] - half, p[1] + half])] for p in local_points]

    attempted = 0
    for extra in (0.02, 0.32, 0.82, 1.52, 2.3):
        offset = half + extra
        if offset > MAX_FRONTAGE_OFFSET_M:
            continue
        front_z = bounds['max'][2] + offset
        stubs = [[world([d[0], d[2]]), world([d[0], front_z])] for d in doors]
        stub_polygons = [p for line in stubs for p in _ribbons(line, ACCESS_WIDTH_M)]
        stub_hits = collisions(stub_polygons, allow_owner=True)
        for join_x in joins:
            connector_options = [[[join_x, front_z], [target[0], target[2]]]]
            # A bounded side detour is allowed only around this building's own
            # envelope, not a free-form search through the city or other plots.
            for side_x in (bounds['min'][0] - half - 0.02, bounds['max'][0] + half + 0.02):
                connector_options.append([[join_x, front_z], [side_x, front_z], [side_x, target[2]], [target[0], target[2]]])
            for connector in connector_options:
                length = sum(math.dist(a, b) for a, b in zip(connector, connector[1:]))
                if length > MAX_CONNECTOR_LENGTH_M:
                    continue
                attempted += 1
                frontage = [[min(min_x, join_x), front_z], [max(max_x, join_x), front_z]]
                common_polygons = _ribbons([world(p) for p in frontage], ACCESS_WIDTH_M)
                common_polygons += _ribbons([world(p) for p in connector], ACCESS_WIDTH_M)
                common_polygons += caps(frontage + connector)
                hits = sorted(set(stub_hits + collisions(common_polygons)))
                result = {'instance_id': iid, 'door_count': len(doors), 'passed': not hits,
                          'width_m': ACCESS_WIDTH_M, 'frontage_offset_m': offset,
                          'door_local_positions_m': doors,
                          'door_world_positions_m': [g.transform_point_m(d, pos, yaw) for d in doors],
                          'door_stub_polylines_xz_m': stubs,
                          'shared_frontage_polyline_xz_m': [world(p) for p in frontage],
                          'street_connector_polyline_xz_m': [world(p) for p in connector],
                          'road_id': instance.get('entrance', {}).get('road_id'),
                          'connector_length_m': length, 'blocking_obstacle_ids': hits,
                          'status': 'proposed_2d_clearance_verified_not_navmesh' if not hits else 'blocked_bounded_proposal'}
                if best is None or (len(hits), length) < (len(best['blocking_obstacle_ids']), best['connector_length_m']):
                    best = result
                if not hits:
                    result['candidates_tested'] = attempted
                    return result
    if best is None:
        best = {'instance_id': iid, 'passed': False, 'door_count': len(doors), 'blocking_obstacle_ids': [],
                'status': 'no_connector_within_declared_bounds'}
    best['candidates_tested'] = attempted
    return best


def audit_revision2(scene, fabric, original_plan, repo_root=None):
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    failures, checks, tolerated = [], {}, []
    sampling_outsets, nonblocking_underlays, reserved_access_conflicts = [], [], []

    def check(name, okay, detail=None):
        entry = checks.setdefault(name, {'name': name, 'evaluated': 0, 'failure_count': 0})
        entry['evaluated'] += 1
        if not okay:
            entry['failure_count'] += 1
            failures.append({'check': name, 'detail': detail})

    scene = copy.deepcopy(scene)
    fabric = copy.deepcopy(fabric)
    originals = {b['id']: b for b in original_plan.get('building_plans', [])}
    instances = {i['id']: i for i in scene.get('instances', [])}
    check('unique_scene_instance_ids', len(instances) == len(scene.get('instances', [])))
    overrides = {o['id']: o for o in fabric.get('building_override_specs', [])}
    supersessions = {s['source_building_id']: s for s in fabric.get('source_building_supersessions', [])}
    properties = {p['id']: p for p in fabric.get('properties', [])}
    reservations = fabric.get('access_reservations', [])
    access_by_owner = defaultdict(list)
    for reservation in reservations:
        access_by_owner[reservation.get('owner_id')].append(reservation)
    check('unique_override_ids', len(overrides) == len(fabric.get('building_override_specs', [])))
    check('unique_superseded_sources', len(supersessions) == len(fabric.get('source_building_supersessions', [])))
    check('replacement_mapping_count', len(overrides) == len(supersessions), {'overrides': len(overrides), 'supersessions': len(supersessions)})
    covered_sources = set()
    effective = copy.deepcopy(original_plan)
    effective_buildings = []
    for sid, source in originals.items():
        effective_source = copy.deepcopy(source)
        if sid in supersessions:
            sup = supersessions[sid]
            rid = sup.get('replacement_id')
            override, instance = overrides.get(rid), instances.get(rid)
            valid = override is not None and instance is not None
            check('explicit_replacement_mapping', valid, {'source_id': sid, 'replacement_id': rid})
            if not valid:
                effective_buildings.append(effective_source)
                continue
            covered_sources.add(sid)
            check('replacement_original_provenance',
                  sup.get('source_footprint_xz_m') == source['footprint_xz_m']
                  and override.get('provenance', {}).get('source_footprint_xz_m') == source['footprint_xz_m']
                  and instance.get('original_v2_footprint_xz_m') == source['footprint_xz_m']
                  and sid in override.get('source_building_ids', []), rid)
            check('replacement_new_footprint_matches_manifest', instance.get('source_footprint_xz_m') == override.get('footprint_xz_m'), rid)
            prop = properties.get(override.get('property_id'), {})
            check('replacement_explicit_property_membership', ('building_override_ids' not in prop or rid in prop['building_override_ids'])
                  and sid in prop.get('source_building_ids', []) and bool(prop.get('land_use'))
                  and sup.get('property_id') == override.get('property_id') == instance.get('property_id'), rid)
            footprint = override.get('footprint_xz_m', [])
            property_polygon = prop.get('footprint_xz_m', [])
            check('replacement_inside_reparceled_property', g.is_convex_polygon(footprint)
                  and g.is_convex_polygon(property_polygon) and g.convex_polygon_contains(property_polygon, footprint, TOL), rid)
            expected_position = override.get('position_m', [])
            check('replacement_manifest_transform', g._vector(expected_position, 3)
                  and math.dist(_xz(instance['position_m']), _xz(expected_position)) <= TOL
                  and abs(math.sin(instance['yaw_rad'] - override['yaw_rad'])) <= 1e-7, rid)
            effective_source['footprint_xz_m'] = footprint
            effective_source['id'] = instance.get('source_footprint_id', sid)
            if override.get('entrances'):
                ent = override['entrances'][0]
                effective_source['road_access']['road_id'] = ent['road_id']
                effective_source['road_access']['connection_xz_m'] = ent['road_connection_xz_m']
        else:
            instance = instances.get(sid)
            check('retained_original_source_footprint', instance is not None and instance.get('source_footprint_id') == sid
                  and instance.get('source_footprint_xz_m') == source['footprint_xz_m'], sid)
            if instance is not None:
                covered_sources.add(sid)
        effective_buildings.append(effective_source)
    check('all_original_ids_accounted_for', covered_sources == set(originals), sorted(set(originals) - covered_sources))
    check('no_unmapped_added_or_missing_instances', set(instances) == (set(originals) - set(supersessions)) | {s['replacement_id'] for s in supersessions.values()})
    effective['building_plans'] = effective_buildings

    public_nodes = {n['id']: n['position_m'] for n in original_plan.get('road_nodes', [])}
    public_polys, public_index = {}, g._SpatialIndex()
    for road in original_plan.get('roads', []):
        if road.get('kind') == 'wall_walk' or road.get('route_id') == 'WALL_ACCESS':
            continue
        polygon = g.road_ribbon(_xz(public_nodes[road['from_node']]), _xz(public_nodes[road['to_node']]), road['width_m'])
        public_polys[road['id']] = polygon
        public_index.add(road['id'], polygon)

    def reaches_public_road(reservation):
        points = reservation.get('polyline_xz_m', [])
        if len(points) < 2 or not all(g._vector(p, 2) for p in points):
            return False
        endpoint = points[-1]
        return any(g.point_in_convex_polygon(endpoint, public_polys[rid], TOL)
                   for rid in public_index.candidates([endpoint]))

    plots = {p['id']: p for p in original_plan.get('plots', [])}
    repurposed = set(fabric.get('repurposed_courtyard_plot_ids', []))
    verified_repurposed = set()
    for pid in sorted(repurposed):
        matches = [p for p in properties.values() if pid in p.get('source_plot_ids', p.get('plot_ids', []))]
        valid = pid in plots and bool(plots[pid].get('courtyard_xz_m')) and bool(matches)
        linked = []
        for prop in matches:
            owners = [prop['id']] + prop.get('building_override_ids', [])
            linked.extend(a for owner in owners for a in access_by_owner[owner]
                          if a.get('kind') in {'court_to_public_road', 'property_entrance'})
        valid = valid and all(bool(p.get('land_use')) for p in matches) and any(reaches_public_road(a) for a in linked)
        check('repurposed_court_has_landuse_and_public_access', valid, {'plot_id': pid, 'properties': [p['id'] for p in matches]})
        if valid:
            verified_repurposed.add(pid)
    for plot in effective.get('plots', []):
        if plot['id'] in verified_repurposed:
            plot.pop('courtyard_xz_m', None)
    court_graph_checks = 0
    for owner, owned in access_by_owner.items():
        routes = [a for a in owned if a.get('kind') in {'court_to_public_road', 'cross_courtyard'}]
        if not any(a.get('kind') == 'cross_courtyard' for a in routes):
            continue
        polygons = [_ribbons(a['polyline_xz_m'], a['width_m']) for a in routes]
        reachable = {j for j, a in enumerate(routes) if a.get('kind') == 'court_to_public_road' and reaches_public_road(a)}
        changed = True
        while changed:
            changed = False
            for j in range(len(routes)):
                if j in reachable:
                    continue
                if any(any(_overlap(p, q) for p in polygons[j] for q in polygons[k]) for k in reachable):
                    reachable.add(j)
                    changed = True
        for j, reservation in enumerate(routes):
            if reservation.get('kind') == 'cross_courtyard':
                court_graph_checks += 1
                check('internal_court_reservation_connected_to_public_link', j in reachable,
                      {'owner_id': owner, 'reservation_id': reservation['id']})


    source_roads = {r['id']: r for r in original_plan.get('roads', [])}
    scene_roads = {r['id']: r for r in scene.get('roads', [])}
    check('road_ids_preserved', set(source_roads) == set(scene_roads))
    for rid, road in source_roads.items():
        check('road_geometry_preserved', all(scene_roads.get(rid, {}).get(k) == road.get(k)
                                            for k in ('from_node', 'to_node', 'width_m', 'kind')), rid)
    scene_nodes = {n['id']: n for n in scene.get('road_nodes', [])}
    for node in original_plan.get('road_nodes', []):
        actual = scene_nodes.get(node['id'], {}).get('position_m', [None, None, None])
        check('road_node_xz_preserved', [actual[0], actual[2]] == [node['position_m'][0], node['position_m'][2]], node['id'])

    compiled_reads, master_metadata = 0, {}
    for kind, catalog in (('building', scene.get('assets', {})), ('fabric', fabric.get('assets', {}))):
        for key, asset in catalog.items():
            resources = _resources(asset)
            check('compiled_resources_present', bool(resources), {'kind': kind, 'asset_key': key})
            for lod, resource in resources:
                path = root / resource['render_path']
                try:
                    raw = path.read_bytes()
                    render = json.loads(raw)
                    actual = mesh_vertex_bounds(render)
                    compiled_reads += 1
                    check('compiled_vertex_bounds_match_catalog', _same_bounds(resource.get('bounds'), actual), {'kind': kind, 'asset_key': key, 'lod': lod})
                    check('compiled_vertex_bounds_match_render', _same_bounds(render.get('bounds'), actual), {'kind': kind, 'asset_key': key, 'lod': lod})
                    if resource.get('render_sha256'):
                        check('compiled_render_hash', hashlib.sha256(raw).hexdigest() == resource['render_sha256'], {'asset_key': key, 'lod': lod})
                    resource['bounds'] = actual
                except (OSError, ValueError, TypeError, KeyError) as error:
                    check('compiled_render_readable', False, {'path': str(path.relative_to(root)), 'error': str(error)})
                if kind == 'building' and key not in master_metadata and resource.get('master_path'):
                    try:
                        raw_master = (root / resource['master_path']).read_bytes()
                        master = json.loads(raw_master)
                        master_metadata[key] = master.get('metadata', {})
                        if resource.get('master_sha256'):
                            check('source_master_hash', hashlib.sha256(raw_master).hexdigest() == resource['master_sha256'], key)
                    except (OSError, ValueError, TypeError) as error:
                        check('source_master_readable', False, {'asset_key': key, 'error': str(error)})

    base = g.validate_placements(scene, effective)
    for failure in base['failures']:
        check('building:' + failure['check'], False, failure['detail'])
    check('effective_building_placement_audit', base['passed'], {'failure_count': base['failure_count']})
    obstacles, building_polys, building_bounds, obstacle_index = {}, {}, {}, g._SpatialIndex()
    for iid, instance in instances.items():
        resources = _resources(scene['assets'][instance['asset_key']])
        bounds = union_bounds([instance['local_bounds']] + [r['bounds'] for _, r in resources if g._valid_bounds(r.get('bounds'))])
        polygon = g.transformed_aabb_xz_m(bounds, instance['position_m'], instance['yaw_rad'])
        building_polys[iid], building_bounds[iid] = polygon, bounds
        key = 'building:' + iid
        obstacles[key] = polygon
        obstacle_index.add(key, polygon)

    for reservation in reservations:
        if reservation.get('kind') not in {'court_to_public_road', 'cross_courtyard'}:
            continue
        for segment_index, polygon in enumerate(_ribbons(reservation['polyline_xz_m'], reservation['width_m'])):
            for target in obstacle_index.candidates(polygon):
                if _overlap(polygon, obstacles[target]):
                    conflict = {'reservation_id': reservation['id'], 'reservation_kind': reservation['kind'],
                                'segment_or_turn_cap_index': segment_index, 'obstacle_id': target,
                                'polyline_xz_m': reservation['polyline_xz_m'], 'width_m': reservation['width_m'],
                                'blocker_polygon_xz_m': obstacles[target],
                                'intersection_area_m2': g.intersection_area(polygon, obstacles[target]),
                                'penetration_m': g.convex_penetration_m(polygon, obstacles[target])}
                    reserved_access_conflicts.append(conflict)
                    check('reserved_court_access_routes_clear_of_buildings', False, conflict)

    nodes = {n['id']: n['position_m'] for n in original_plan.get('road_nodes', [])}
    road_polys = {}
    for rid, road in source_roads.items():
        if rid in base['excluded_wall_walk_road_ids'] + base['excluded_stair_to_wall_road_ids']:
            continue
        road_polys[rid] = g.road_ribbon(_xz(nodes[road['from_node']]), _xz(nodes[road['to_node']]), road['width_m'])
    clearance_polys, clearance_index = {}, g._SpatialIndex()
    for rid, polygon in road_polys.items():
        clearance_polys['road:' + rid] = polygon
    for plot in effective.get('plots', []):
        if plot.get('courtyard_xz_m'):
            clearance_polys['courtyard:' + plot['id']] = plot['courtyard_xz_m']
    for reservation in reservations:
        points, width = reservation.get('polyline_xz_m', []), reservation.get('width_m')
        valid = isinstance(points, list) and len(points) >= 2 and all(g._vector(p, 2) for p in points) and g._number(width) and width > 0
        check('access_reservation_geometry', valid, reservation.get('id'))
        if valid:
            for j, polygon in enumerate(_ribbons(points, width)):
                clearance_polys['access:' + reservation['id'] + ':' + str(j)] = polygon
    for key, polygon in clearance_polys.items():
        clearance_index.add(key, polygon)
    fabric_polys, blocking_fabric, fabric_bounds = {}, {}, {}
    ids = set()
    for placement in fabric.get('placements', []):
        fid = placement['id']
        check('unique_fabric_placement_ids', fid not in ids, fid)
        ids.add(fid)
        asset = fabric.get('assets', {}).get(placement['asset_key'])
        if not asset or not g._valid_bounds(asset.get('bounds')):
            check('fabric_compiled_asset_reference', False, fid)
            continue
        bounds = asset['bounds']
        polygon = g.transformed_aabb_xz_m(bounds, placement['position_m'], placement.get('yaw_rad', 0))
        fabric_polys[fid], fabric_bounds[fid] = polygon, bounds
        if not _contains_bounds(placement.get('local_bounds'), bounds):
            sampling_outsets.append({'placement_id': fid, 'continuous_local_bounds': placement.get('local_bounds'),
                                    'actual_compiled_bounds': bounds, 'policy': 'must_fit_explicit_sample_guard_and_actual_clearance'})
        envelope = placement.get('conservative_sample_envelope_xz_m', [])
        check('fabric_sample_guard_encloses_compiled', g.is_convex_polygon(envelope) and g.convex_polygon_contains(envelope, polygon, TOL), fid)
        flush = placement.get('category') == 'flush_work_surface' and placement.get('collision_enabled') is False and bounds['max'][1] <= 0.3
        check('nonblocking_fabric_is_declared_flush_surface', placement.get('collision_enabled') is not False or flush, fid)
        for target in clearance_index.candidates(polygon):
            if flush and target.startswith('access:'):
                continue
            if _overlap(polygon, clearance_polys[target]):
                check('fabric_respects_reserved_clearance', False, {'placement_id': fid, 'reservation': target,
                      'intersection_area_m2': g.intersection_area(polygon, clearance_polys[target])})
        for target in obstacle_index.candidates(polygon):
            if _overlap(polygon, obstacles[target]):
                if flush and target.startswith('fabric:'):
                    nonblocking_underlays.append({'placement_id': fid, 'obstacle_id': target})
                else:
                    check('fabric_does_not_overlap_building_or_prior_blocker', False, {'placement_id': fid, 'obstacle_id': target})
        if not flush:
            blocking_fabric[fid] = polygon
            obstacles['fabric:' + fid] = polygon
            obstacle_index.add('fabric:' + fid, polygon)

    row_routes, row_count, door_count = [], 0, 0
    for iid, instance in instances.items():
        meta = master_metadata.get(instance['asset_key'], {})
        is_row = meta.get('assembly_class') == 'poor_row' or instance.get('assembly_class') == 'poor_row'
        if not is_row:
            continue
        row_count += 1
        entmeta = meta.get('entrance', {})
        doors = entmeta.get('all_positions')
        valid = isinstance(doors, list) and len(doors) >= 1 and all(g._vector(p, 3) for p in doors)
        check('poor_row_all_authored_doors_available', valid and entmeta.get('front', '+Z') == '+Z', iid)
        if not valid:
            continue
        door_count += len(doors)
        check('poor_row_all_doors_retained_in_instance', instance.get('all_entrances_local_m') == doors, iid)
        check('poor_row_unit_count_matches_doors', meta.get('row_units') == len(doors), iid)
        for _, resource in _resources(scene['assets'][instance['asset_key']]):
            check('poor_row_compiled_metadata_matches_master', resource.get('author_metadata', {}).get('entrance', {}).get('all_positions') == doors, iid)
        primary = entmeta.get('position')
        entrance = instance.get('entrance', {})
        check('poor_row_primary_entrance_matches_authored', entrance.get('local_position_m') == primary, iid)
        expected_world = g.transform_point_m(primary, instance['position_m'], instance['yaw_rad'])
        check('poor_row_primary_world_transform', g._vector(entrance.get('position_m'), 3) and math.dist(expected_world, entrance['position_m']) <= TOL, iid)
        cp, rid = entrance.get('road_connection_m'), entrance.get('road_id')
        valid_target = g._vector(cp, 3) and rid in road_polys
        if valid_target:
            road = source_roads[rid]
            valid_target = g.point_segment_distance(_xz(cp), _xz(nodes[road['from_node']]), _xz(nodes[road['to_node']])) <= TOL
        check('poor_row_named_public_street_target', valid_target, iid)
        if valid_target:
            route = frontage_route_proposal(instance, doors, building_bounds[iid], cp, obstacles, obstacle_index)
            row_routes.append(route)
            check('all_poor_row_doors_reach_clear_shared_frontage_and_street', route['passed'],
                  {'instance_id': iid, 'door_count': len(doors), 'blocking_obstacle_ids': route['blocking_obstacle_ids'], 'status': route['status']})
    for value in checks.values():
        value['passed'] = value['failure_count'] == 0
    return {'passed': not failures, 'schema': 'riverstone.city.revision2.audit.v1', 'failure_count': len(failures),
            'failures': failures, 'checks': list(checks.values()), 'tolerance_m': TOL,
            'scope': 'Independent original/reparcel provenance, actual compiled all-LOD quad bounds, reserved XZ clearance, and every authored poor-row door via bounded proposed 2D frontage routes; not gameplay or navigation simulation',
            'counts': {'source_buildings': len(originals), 'instances': len(instances), 'retained_original_footprints': len(originals) - len(supersessions),
                       'explicit_replacements': len(supersessions), 'repurposed_courtyards': len(repurposed),
                       'verified_repurposed_courtyards': len(verified_repurposed), 'remaining_reserved_courtyards': sum(bool(p.get('courtyard_xz_m')) for p in effective.get('plots', [])),
                       'compiled_render_resources_read': compiled_reads, 'fabric_placements': len(fabric_polys), 'blocking_fabric': len(blocking_fabric),
                       'explicit_sample_guard_outsets': len(sampling_outsets), 'nonblocking_surface_underlays': len(nonblocking_underlays),
                       'reserved_court_access_building_conflicts': len(reserved_access_conflicts),
                       'internal_court_connections_checked': court_graph_checks,
                       'poor_row_instances': row_count, 'authored_poor_row_doors': door_count,
                       'rows_with_clear_all_door_route': sum(r['passed'] for r in row_routes), 'rows_with_blocked_route': sum(not r['passed'] for r in row_routes)},
            'building_placement_report': base, 'row_access_proposals': row_routes,
            'compiled_sampling_outsets': sampling_outsets, 'nonblocking_surface_underlays': nonblocking_underlays,
            'reserved_court_access_building_conflicts': reserved_access_conflicts,
            'route_policy': {'width_m': ACCESS_WIDTH_M, 'maximum_frontage_offset_m': MAX_FRONTAGE_OFFSET_M,
                             'maximum_connector_length_m': MAX_CONNECTOR_LENGTH_M, 'roof_threshold_owner_exception': 'only own door-to-front stub',
                             'other_buildings_and_blocking_fabric': 'no exceptions', 'status': 'proposed_routes_only_no_scene_mutation'},
            'warnings': ['Road grades, stairs to wall walks, door leaf operation and navigation remain unimplemented or outside this audit.',
                         'A clear XZ route is a geometric proposal, not a claim that a playable walking surface/navmesh exists.',
                         'All row door stubs may pass their own declared roof/threshold envelope; exact facade apertures are separately authored/compiled geometry.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('fabric', type=Path)
    parser.add_argument('original_plan', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repo-root', type=Path)
    args = parser.parse_args()
    input_bytes = {'scene': args.scene.read_bytes(), 'fabric': args.fabric.read_bytes(), 'original_plan': args.original_plan.read_bytes()}
    report = audit_revision2(*(json.loads(input_bytes[k]) for k in ('scene', 'fabric', 'original_plan')), repo_root=args.repo_root)
    report['inputs'] = {key: {'path': str(path), 'sha256': hashlib.sha256(input_bytes[key]).hexdigest(), 'byte_count': len(input_bytes[key])}
                       for key, path in [('scene', args.scene), ('fabric', args.fabric), ('original_plan', args.original_plan)]}
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(json.dumps({'passed': report['passed'], 'failure_count': report['failure_count'], 'counts': report['counts'],
                      'failure_types': dict(Counter(f['check'] for f in report['failures']))}, ensure_ascii=False, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
