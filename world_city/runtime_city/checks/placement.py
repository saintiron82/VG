#!/usr/bin/env python3
"""Independent, standard-library-only checks for city instance placement.

All distances are metres. The default 0.002 m tolerance is an explicit CAD
rounding allowance, not an area threshold. Positive-area intersections inside
that tolerance are retained in the report. Geometry uses right-handed +Y yaw:
local +Z is front, and positive yaw rotates it towards world +X.

Gate exceptions require ``gate_openings`` (or legacy singular ``gate_opening``),
each with ``local_bounds`` and explicit ``road_ids``. Only a source gatehouse may
use the exception. Its complete road/building intersection must lie in the union
of that road's designated openings, with the source-required vertical clearance.
This validates the declared opening, not the existence of a hole in a mesh.
"""

from collections import Counter, defaultdict
import argparse
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath


CAD_TOLERANCE_M = 0.002
NUMERIC_EPSILON = 1e-10
IMPLEMENTATION_TIERS = {"active_gameplay", "exterior_only", "interior_selected"}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _vector(value, size):
    return isinstance(value, (list, tuple)) and len(value) == size and all(_number(v) for v in value)


def signed_polygon_area(polygon):
    """Signed shoelace area; positive is counter-clockwise in the XZ plane."""
    if len(polygon) < 3:
        return 0.0
    # Translate to the first vertex to avoid cancellation at large coordinates.
    ox, oz = polygon[0]
    return sum((p[0] - ox) * (q[1] - oz) - (q[0] - ox) * (p[1] - oz)
               for p, q in zip(polygon, polygon[1:] + polygon[:1])) / 2.0


def polygon_area(polygon):
    return abs(signed_polygon_area(polygon))


def _cross(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def is_convex_polygon(polygon):
    if not isinstance(polygon, (list, tuple)) or len(polygon) < 3:
        return False
    if not all(_vector(p, 2) for p in polygon) or polygon_area(polygon) <= NUMERIC_EPSILON:
        return False
    orientation = 1.0 if signed_polygon_area(polygon) > 0.0 else -1.0
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        if math.dist(a, b) <= NUMERIC_EPSILON:
            return False
        if any(orientation * _cross(a, b, p) < -NUMERIC_EPSILON for p in polygon):
            return False
    return True


def point_in_convex_polygon(point, polygon, tolerance_m=CAD_TOLERANCE_M):
    """Boundary-inclusive containment with edge distances normalized to metres."""
    orientation = 1.0 if signed_polygon_area(polygon) > 0.0 else -1.0
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        length = math.dist(a, b)
        if length <= NUMERIC_EPSILON:
            continue
        if orientation * _cross(a, b, point) / length < -tolerance_m - NUMERIC_EPSILON:
            return False
    return True


def convex_polygon_contains(outer, inner, tolerance_m=CAD_TOLERANCE_M):
    return bool(inner) and all(point_in_convex_polygon(p, outer, tolerance_m) for p in inner)


def convex_intersection(subject, clip):
    """Sutherland-Hodgman intersection, valid for convex CW or CCW polygons."""
    output = [list(p) for p in subject]
    orientation = 1.0 if signed_polygon_area(clip) > 0.0 else -1.0
    for a, b in zip(clip, clip[1:] + clip[:1]):
        if not output:
            break
        inputs, output = output, []
        previous = inputs[-1]
        previous_d = orientation * _cross(a, b, previous)
        for current in inputs:
            current_d = orientation * _cross(a, b, current)
            current_inside = current_d >= -NUMERIC_EPSILON
            previous_inside = previous_d >= -NUMERIC_EPSILON
            if current_inside != previous_inside:
                denominator = previous_d - current_d
                if abs(denominator) > NUMERIC_EPSILON:
                    t = previous_d / denominator
                    output.append([previous[j] + t * (current[j] - previous[j]) for j in (0, 1)])
            if current_inside:
                output.append(list(current))
            previous, previous_d = current, current_d
    return output


def convex_penetration_m(a, b):
    """Minimum separating translation along polygon normals; <= 0 is contact/gap."""
    minimum = math.inf
    for polygon in (a, b):
        for p, q in zip(polygon, polygon[1:] + polygon[:1]):
            length = math.dist(p, q)
            if length <= NUMERIC_EPSILON:
                continue
            nx, nz = -(q[1] - p[1]) / length, (q[0] - p[0]) / length
            aa = [v[0] * nx + v[1] * nz for v in a]
            bb = [v[0] * nx + v[1] * nz for v in b]
            depth = min(max(aa) - min(bb), max(bb) - min(aa))
            minimum = min(minimum, depth)
            if minimum <= 0.0:
                return minimum
    return minimum


def positive_area_overlap(a, b, tolerance_m=0.0):
    """True for positive-area overlap deeper than the requested metre tolerance."""
    return convex_penetration_m(a, b) > tolerance_m + NUMERIC_EPSILON


def intersection_area(a, b):
    if not positive_area_overlap(a, b):
        return 0.0
    return polygon_area(convex_intersection(a, b))


def _clip_halfplane(subject, a, b, orientation, threshold, keep_inside):
    """Clip to either side of one oriented line, preserving convexity."""
    if not subject:
        return []
    output = []
    previous = subject[-1]
    previous_d = orientation * _cross(a, b, previous) - threshold
    for current in subject:
        current_d = orientation * _cross(a, b, current) - threshold
        previous_in = previous_d >= 0 if keep_inside else previous_d <= 0
        current_in = current_d >= 0 if keep_inside else current_d <= 0
        if previous_in != current_in:
            denominator = previous_d - current_d
            if abs(denominator) > NUMERIC_EPSILON:
                t = previous_d / denominator
                output.append([previous[j] + t * (current[j] - previous[j]) for j in (0, 1)])
        if current_in:
            output.append(list(current))
        previous, previous_d = current, current_d
    return output


def convex_difference(subject, clip, tolerance_m=0.0):
    """Disjoint convex pieces of subject outside clip's expanded halfplanes.

    Unlike an AABB or convex-hull union, this preserves gaps between openings.
    The expansion is the same edge-normal metre tolerance used by containment.
    """
    orientation = 1.0 if signed_polygon_area(clip) > 0 else -1.0
    inside, outside = [list(p) for p in subject], []
    for a, b in zip(clip, clip[1:] + clip[:1]):
        if not inside:
            break
        threshold = -tolerance_m * math.dist(a, b)
        piece = _clip_halfplane(inside, a, b, orientation, threshold, False)
        if polygon_area(piece) > NUMERIC_EPSILON:
            outside.append(piece)
        inside = _clip_halfplane(inside, a, b, orientation, threshold, True)
    return outside


def uncovered_area_by_union(subject, covers, tolerance_m=0.0):
    """Area left after exact polygon subtraction by each convex cover.

    Tolerance applies once to the width of an uncovered sliver, not once per
    cover edge. Expanding both covers could otherwise hide a gap twice as wide
    as the permitted CAD tolerance.
    """
    remaining = [subject]
    for cover in covers:
        remaining = [piece for polygon in remaining for piece in convex_difference(polygon, cover)]
        if not remaining:
            return 0.0
    return sum(polygon_area(polygon) for polygon in remaining
               if tolerance_m == 0 or convex_penetration_m(polygon, polygon) > tolerance_m + NUMERIC_EPSILON)


def polygon_covered_by_union(subject, covers, tolerance_m=CAD_TOLERANCE_M):
    return uncovered_area_by_union(subject, covers, tolerance_m) <= NUMERIC_EPSILON


def point_segment_distance(point, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dz * dz
    if not length2:
        return math.dist(point, a)
    t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dz) / length2))
    return math.dist(point, [a[0] + t * dx, a[1] + t * dz])


def transform_point_m(local, position_m, yaw_rad):
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    return [position_m[0] + c * local[0] + s * local[2],
            position_m[1] + local[1],
            position_m[2] - s * local[0] + c * local[2]]


def inverse_transform_point_m(world, position_m, yaw_rad):
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    x, z = world[0] - position_m[0], world[2] - position_m[2]
    return [c * x - s * z, world[1] - position_m[1], s * x + c * z]


def _valid_bounds(bounds):
    return (isinstance(bounds, dict) and _vector(bounds.get("min"), 3)
            and _vector(bounds.get("max"), 3)
            and all(bounds["max"][i] > bounds["min"][i] for i in range(3)))


def transformed_aabb_xz_m(local_bounds, position_m, yaw_rad):
    """Rotated local AABB projection, retaining its four corners (not world AABB)."""
    lo, hi = local_bounds["min"], local_bounds["max"]
    points = [[lo[0], 0.0, lo[2]], [hi[0], 0.0, lo[2]],
              [hi[0], 0.0, hi[2]], [lo[0], 0.0, hi[2]]]
    return [[p[0], p[2]] for p in (transform_point_m(v, position_m, yaw_rad) for v in points)]


def road_ribbon(a, b, width_m):
    """Closed rectangular ribbon for one plan road segment, without invented caps."""
    length = math.dist(a, b)
    if length <= NUMERIC_EPSILON or not _number(width_m) or width_m <= 0:
        raise ValueError("Road ribbon needs a positive width and distinct endpoints")
    nx, nz = -(b[1] - a[1]) / length * width_m / 2, (b[0] - a[0]) / length * width_m / 2
    return [[a[0] + nx, a[1] + nz], [b[0] + nx, b[1] + nz],
            [b[0] - nx, b[1] - nz], [a[0] - nx, a[1] - nz]]


class _SpatialIndex:
    def __init__(self, cell_m=40.0):
        self.cell_m, self.cells = cell_m, defaultdict(list)

    def keys(self, polygon):
        xs, zs = zip(*polygon)
        for x in range(math.floor(min(xs) / self.cell_m), math.floor(max(xs) / self.cell_m) + 1):
            for z in range(math.floor(min(zs) / self.cell_m), math.floor(max(zs) / self.cell_m) + 1):
                yield x, z

    def add(self, key, polygon):
        for cell in self.keys(polygon):
            self.cells[cell].append(key)

    def candidates(self, polygon):
        return sorted({key for cell in self.keys(polygon) for key in self.cells.get(cell, ())})


def validate_placements(scene, plan, tolerance_m=CAD_TOLERANCE_M):
    """Return JSON-safe checks, measured counts, and individual failure records.

    Every source building must be represented. Multiple assembly instances may
    share a source footprint; inter-instance overlap is tested between distinct
    sources. Courtyards are specifically plot courtyard polygons, not precincts
    which already contain source landmark buildings. Elevation, mesh cavity
    realization, navmesh and actual filesystem contents are outside this scope.
    """
    if not _number(tolerance_m) or not 0 <= tolerance_m <= CAD_TOLERANCE_M:
        raise ValueError("Tolerance must be between zero and the explicit 0.002 m CAD limit")
    failures, tolerated, accepted_gates, unverified = [], [], [], []
    accepted_tower_arches, declared_tower_clearances = [], []
    checks = {}

    def check(name, okay, detail=None):
        entry = checks.setdefault(name, {"name": name, "evaluated": 0, "failure_count": 0})
        entry["evaluated"] += 1
        if not okay:
            entry["failure_count"] += 1
            failures.append({"check": name, "detail": detail})

    check("scene_object", isinstance(scene, dict))
    check("plan_object", isinstance(plan, dict))
    scene = scene if isinstance(scene, dict) else {}
    plan = plan if isinstance(plan, dict) else {}
    instance_list = scene.get("instances")
    check("instances_array_nonempty", isinstance(instance_list, list) and bool(instance_list))
    instances = instance_list if isinstance(instance_list, list) else []
    source_list = plan.get("building_plans")
    check("source_buildings_array_nonempty", isinstance(source_list, list) and bool(source_list))
    source_list = source_list if isinstance(source_list, list) else []
    sources = {}
    for source in source_list:
        if not isinstance(source, dict):
            check("valid_source_record", False, source)
            continue
        sid = source.get("id")
        valid_id = isinstance(sid, str) and bool(sid)
        check("unique_source_ids", valid_id and sid not in sources, sid)
        valid = is_convex_polygon(source.get("footprint_xz_m"))
        check("convex_source_footprints", valid, sid)
        if valid_id and valid:
            sources[sid] = source

    assets = scene.get("assets")
    check("assets_map_nonempty", isinstance(assets, dict) and bool(assets))
    assets = assets if isinstance(assets, dict) else {}
    asset_resources = {}
    for key, asset in assets.items():
        resources = []
        if isinstance(asset, dict):
            if "render_path" in asset:
                resources = [("default", asset)]
            else:
                resources = [(lod, resource) for lod, resource in asset.items()
                             if isinstance(resource, dict) and (lod in {"coarse", "medium", "fine"} or "render_path" in resource)]
        check("asset_render_resources_present", bool(resources), key)
        asset_resources[key] = resources
        for lod, resource in resources:
            path = resource.get("render_path")
            relative = (isinstance(path, str) and bool(path.strip()) and not PurePosixPath(path).is_absolute()
                        and not PureWindowsPath(path).is_absolute() and ":" not in path)
            check("asset_render_paths_relative", relative, {"asset_key": key, "lod": lod, "render_path": path})

    nodes = {n["id"]: n for n in plan.get("road_nodes", []) if isinstance(n, dict) and "id" in n}
    roads, road_polygons, road_index, excluded_wall_walk = {}, {}, _SpatialIndex(), []
    excluded_stair_reservations = []
    for road in plan.get("roads", []):
        if not isinstance(road, dict):
            check("valid_road_geometry", False, road)
            continue
        rid = road.get("id")
        check("unique_road_ids", isinstance(rid, str) and bool(rid) and rid not in roads, rid)
        try:
            aa, bb = nodes[road["from_node"]]["position_m"], nodes[road["to_node"]]["position_m"]
            a, b = [aa[0], aa[2]], [bb[0], bb[2]]
            if not _vector(a, 2) or not _vector(b, 2):
                raise ValueError("Invalid road endpoints")
            polygon = road_ribbon(a, b, road["width_m"])
            roads[rid] = (road, a, b)
            check("valid_road_geometry", True)
            if road.get("kind") == "wall_walk":
                excluded_wall_walk.append(rid)
            elif (road.get("route_id") == "WALL_ACCESS" and road.get("kind") == "pedestrian"
                  and rid in {"WALL_ACCESS_south", "WALL_ACCESS_east", "WALL_ACCESS_north", "WALL_ACCESS_west"}):
                # These source links describe stairs up to elevated wall walks,
                # not a level ground strip through every wall tower on the link.
                # Their unresolved vertical geometry must not count as complete.
                excluded_stair_reservations.append(rid)
            else:
                road_polygons[rid] = polygon
                road_index.add(rid, polygon)
        except (KeyError, TypeError, ValueError, IndexError) as error:
            check("valid_road_geometry", False, {"road_id": rid, "error": str(error)})

    courtyards, courtyard_index = {}, _SpatialIndex()
    for plot in plan.get("plots", []):
        if not isinstance(plot, dict) or not plot.get("courtyard_xz_m"):
            continue
        pid, polygon = plot.get("id"), plot["courtyard_xz_m"]
        valid = isinstance(pid, str) and is_convex_polygon(polygon)
        check("convex_reserved_courtyards", valid, pid)
        check("unique_courtyard_ids", pid not in courtyards, pid)
        if valid:
            courtyards[pid] = polygon
            courtyard_index.add(pid, polygon)

    ids, covered, transformed, valid_instances, openings = set(), set(), {}, {}, {}
    for index, instance in enumerate(instances):
        if not isinstance(instance, dict):
            check("instance_records", False, {"index": index})
            continue
        iid, sid = instance.get("id"), instance.get("source_footprint_id")
        unique = isinstance(iid, str) and bool(iid) and iid not in ids
        check("unique_instance_ids", unique, iid)
        if not unique:
            continue
        ids.add(iid)
        valid_source_reference = isinstance(sid, str) and sid in sources
        check("source_footprint_references", valid_source_reference,
              {"instance_id": iid, "source_footprint_id": sid})
        if not valid_source_reference:
            continue
        source = sources[sid]
        covered.add(sid)
        check("source_footprint_unchanged", instance.get("source_footprint_xz_m") == source["footprint_xz_m"], iid)
        check("source_district_unchanged", instance.get("district_id") == source.get("district_id"), iid)
        tier = instance.get("implementation_tier")
        check("implementation_tier_preserved", isinstance(tier, str) and tier in IMPLEMENTATION_TIERS and tier == source.get("implementation_tier"), iid)
        check("preserved_record_boolean", isinstance(instance.get("preserved_record"), bool), iid)
        asset_key = instance.get("asset_key")
        check("asset_references", isinstance(asset_key, str) and asset_key in assets, iid)
        bounds, position, yaw = instance.get("local_bounds"), instance.get("position_m"), instance.get("yaw_rad")
        valid = _valid_bounds(bounds) and _vector(position, 3) and _number(yaw)
        check("finite_positive_instance_bounds_and_transform", valid, iid)
        if not valid:
            continue
        # Conservative placement must encompass every LOD, including a fine
        # sample whose occupied voxel faces extend beyond the coarse sample.
        audited_bounds = {"min": list(bounds["min"]), "max": list(bounds["max"])}
        for lod, resource in asset_resources.get(asset_key, []) if isinstance(asset_key, str) else []:
            asset_bounds = resource.get("local_bounds", resource.get("bounds"))
            if asset_bounds is None:
                continue
            consistent = (_valid_bounds(asset_bounds)
                          and all(bounds["min"][j] - tolerance_m <= asset_bounds["min"][j]
                                  and bounds["max"][j] + tolerance_m >= asset_bounds["max"][j] for j in range(3)))
            check("instance_matches_asset_bounds", consistent, {"instance_id": iid, "lod": lod})
            if _valid_bounds(asset_bounds):
                for j in range(3):
                    audited_bounds["min"][j] = min(audited_bounds["min"][j], asset_bounds["min"][j])
                    audited_bounds["max"][j] = max(audited_bounds["max"][j], asset_bounds["max"][j])
        bounds = audited_bounds
        polygon = transformed_aabb_xz_m(bounds, position, yaw)
        transformed[iid], valid_instances[iid] = polygon, instance
        check("transformed_aabb_inside_source_footprint", convex_polygon_contains(source["footprint_xz_m"], polygon, tolerance_m), iid)

        entrance = instance.get("entrance")
        entrance = entrance if isinstance(entrance, dict) else {}
        ep, cp, road_id = entrance.get("position_m"), entrance.get("road_connection_m"), entrance.get("road_id")
        check("entrance_position_finite", _vector(ep, 3), iid)
        check("road_connection_finite", _vector(cp, 3), iid)
        check("entrance_named_road_exists", road_id in roads if isinstance(road_id, str) else False, iid)
        source_access = source.get("road_access", {})
        check("source_access_road_preserved", road_id == source_access.get("road_id"), iid)
        if _vector(cp, 3) and isinstance(road_id, str) and road_id in roads:
            _, a, b = roads[road_id]
            distance = point_segment_distance([cp[0], cp[2]], a, b)
            check("connection_on_named_road", distance <= tolerance_m + NUMERIC_EPSILON,
                  {"instance_id": iid, "distance_m": distance})
            source_connection = source_access.get("connection_xz_m")
            if _vector(source_connection, 2):
                check("source_road_connection_preserved", math.dist([cp[0], cp[2]], source_connection) <= tolerance_m + NUMERIC_EPSILON, iid)
        # Roof/canopy envelopes can extend beyond the actual wall/door. Never
        # invent a door at the AABB face when authored local metadata is absent.
        if "local_position_m" not in entrance and "facade_inset_m" not in entrance:
            unverified.append({"check": "authored_entrance_local_geometry", "instance_id": iid,
                               "reason": "No authored local_position_m and facade_inset_m; world entrance is not assumed to be the AABB front"})
        else:
            local, inset = entrance.get("local_position_m"), entrance.get("facade_inset_m")
            valid_local = _vector(local, 3) and _number(inset) and inset >= 0
            check("authored_entrance_local_metadata", valid_local, iid)
            if valid_local:
                inside = all(bounds["min"][j] - tolerance_m <= local[j] <= bounds["max"][j] + tolerance_m for j in range(3))
                positive_z_facade = abs(local[2] - (bounds["max"][2] - inset)) <= tolerance_m + NUMERIC_EPSILON
                check("entrance_inside_bounds_on_declared_positive_z_facade", inside and positive_z_facade, iid)
                if _vector(ep, 3):
                    expected = transform_point_m(local, position, yaw)
                    check("entrance_authored_world_transform_consistent", math.dist(expected, ep) <= tolerance_m + NUMERIC_EPSILON,
                          {"instance_id": iid, "distance_m": math.dist(expected, ep)})

        opening = instance.get("gate_opening")
        opening_list = instance.get("gate_openings")
        is_gate = source.get("functional_role") == "gatehouse"
        if is_gate or opening is not None or opening_list is not None:
            required = source.get("opening_required_m", {})
            declared = opening_list if opening_list is not None else [opening]
            valid_openings = (is_gate and isinstance(declared, list) and bool(declared)
                              and not (opening is not None and opening_list is not None))
            primary_count, declared_roads, converted = 0, set(), []
            if valid_openings:
                for item in declared:
                    ob = item.get("local_bounds") if isinstance(item, dict) else None
                    rr = item.get("road_ids") if isinstance(item, dict) else None
                    okay = (_valid_bounds(ob) and isinstance(rr, list) and bool(rr)
                            and all(isinstance(r, str) and r in road_polygons for r in rr)
                            and len(set(rr)) == len(rr))
                    if okay:
                        okay = (
                            all(bounds["min"][j] - tolerance_m <= ob["min"][j] < ob["max"][j] <= bounds["max"][j] + tolerance_m for j in range(3))
                            and ob["max"][1] - ob["min"][1] + tolerance_m >= required.get("height", math.inf)
                            and ob["min"][1] <= bounds["min"][1] + tolerance_m)
                    if not okay:
                        valid_openings = False
                        break
                    if (ob["max"][0] - ob["min"][0] + tolerance_m >= required.get("width", math.inf)
                            and ob["min"][2] <= bounds["min"][2] + tolerance_m
                            and ob["max"][2] >= bounds["max"][2] - tolerance_m):
                        primary_count += 1
                    declared_roads.update(rr)
                    converted.append((transformed_aabb_xz_m(ob, position, yaw), set(rr)))
            valid_openings = valid_openings and primary_count > 0 and source_access.get("road_id") in declared_roads
            check("explicit_gate_opening_contract", valid_openings, iid)
            if valid_openings:
                openings[iid] = converted

        road_openings = instance.get("road_openings")
        if road_openings is not None:
            valid_arches = (source.get("functional_role") == "wall_tower"
                            and isinstance(road_openings, list) and bool(road_openings)
                            and opening is None and opening_list is None)
            converted, clearances = [], []
            if valid_arches:
                for item in road_openings:
                    ob = item.get("local_bounds") if isinstance(item, dict) else None
                    rr = item.get("road_ids") if isinstance(item, dict) else None
                    height = item.get("clearance_height_m") if isinstance(item, dict) else None
                    okay = (_valid_bounds(ob) and _number(height) and height > 0
                            and isinstance(rr, list) and bool(rr)
                            and all(isinstance(r, str) and r in road_polygons for r in rr)
                            and len(set(rr)) == len(rr))
                    if okay:
                        okay = (all(bounds["min"][j] - tolerance_m <= ob["min"][j] < ob["max"][j] <= bounds["max"][j] + tolerance_m for j in range(3))
                                and ob["min"][1] <= bounds["min"][1] + tolerance_m
                                and ob["max"][1] - ob["min"][1] + tolerance_m >= height)
                    if not okay:
                        valid_arches = False
                        break
                    converted.append((transformed_aabb_xz_m(ob, position, yaw), set(rr)))
                    clearances.append({"instance_id": iid, "road_ids": rr, "clearance_height_m": height,
                                       "status": "authored_clearance_no_source_height_requirement"})
            check("explicit_wall_tower_road_opening_contract", valid_arches, iid)
            if valid_arches:
                openings[iid] = converted
                declared_tower_clearances.extend(clearances)

    missing = sorted(set(sources) - covered)
    check("all_source_buildings_represented", not missing, {"missing_count": len(missing), "source_ids": missing})

    collisions = Counter()

    def collision(kind, iid, target, a, b):
        penetration = convex_penetration_m(a, b)
        if penetration <= NUMERIC_EPSILON:
            return
        area = intersection_area(a, b)
        if area <= NUMERIC_EPSILON:
            return
        record = {"kind": kind, "instance_id": iid, "target_id": target,
                  "intersection_area_m2": area, "penetration_m": penetration}
        if penetration <= tolerance_m + NUMERIC_EPSILON:
            tolerated.append(record)
            return
        if kind == "road" and iid in openings:
            opening_polygons = [polygon for polygon, explicit_roads in openings[iid] if target in explicit_roads]
            intersection = convex_intersection(a, b)
            raw_uncovered = uncovered_area_by_union(intersection, opening_polygons)
            uncovered = uncovered_area_by_union(intersection, opening_polygons, tolerance_m)
            record["uncovered_area_m2"] = raw_uncovered
            record["uncovered_area_beyond_tolerance_m2"] = uncovered
            if opening_polygons and uncovered <= NUMERIC_EPSILON:
                is_gate = sources[valid_instances[iid]["source_footprint_id"]].get("functional_role") == "gatehouse"
                record["exception_kind"] = "gate_opening" if is_gate else "explicit_wall_tower_arch"
                (accepted_gates if is_gate else accepted_tower_arches).append(record)
                return
        collisions[kind] += 1
        check("no_" + kind + "_overlaps", False, record)

    building_index = _SpatialIndex()
    for iid, polygon in transformed.items():
        for rid in road_index.candidates(polygon):
            collision("road", iid, rid, polygon, road_polygons[rid])
        for pid in courtyard_index.candidates(polygon):
            collision("courtyard", iid, pid, polygon, courtyards[pid])
        for other in building_index.candidates(polygon):
            if valid_instances[other]["source_footprint_id"] != valid_instances[iid]["source_footprint_id"]:
                collision("building", iid, other, polygon, transformed[other])
        building_index.add(iid, polygon)
    for kind in ("road", "courtyard", "building"):
        # This aggregate is based on observed collision counts, never a forced pass.
        if not collisions[kind]:
            check("no_" + kind + "_overlaps", True, {"tested_instances": len(transformed)})

    for entry in checks.values():
        entry["passed"] = entry["failure_count"] == 0
    return {
        "passed": not failures,
        "verification_complete": not failures and not unverified,
        "vertical_access_unimplemented": bool(excluded_wall_walk or excluded_stair_reservations),
        "scope": "Declared transformed building AABBs in XZ, source identity, access references, and explicit gate-opening contracts; not mesh, terrain, navmesh, or gameplay validation",
        "tolerance_m": tolerance_m,
        "tolerance_policy": "Positive-area overlaps are failures when normalized SAT penetration exceeds tolerance; smaller positive-area overlaps are explicitly listed",
        "checks": list(checks.values()),
        "failure_count": len(failures),
        "failures": failures,
        "counts": {
            "source_buildings": len(source_list), "instances": len(instances),
            "unique_instance_ids": len(ids), "covered_source_buildings": len(covered),
            "missing_source_buildings": len(missing), "transformed_aabbs": len(transformed),
            "assets": len(assets), "ground_road_segments": len(road_polygons),
            "excluded_wall_walk_segments": len(excluded_wall_walk), "reserved_courtyards": len(courtyards),
            "excluded_stair_to_wall_reservations": len(excluded_stair_reservations),
            "road_overlaps": collisions["road"], "courtyard_overlaps": collisions["courtyard"],
            "building_overlaps": collisions["building"], "accepted_gate_road_intersections": len(accepted_gates),
            "accepted_wall_tower_arch_intersections": len(accepted_tower_arches),
            "opening_coverage_cad_slivers": sum(r["uncovered_area_m2"] > NUMERIC_EPSILON for r in accepted_gates + accepted_tower_arches),
            "tolerated_positive_area_overlaps": len(tolerated),
            "unverified_entrance_local_geometry": len(unverified),
            "preserved_record_instances": sum(i.get("preserved_record") is True for i in instances if isinstance(i, dict)),
            "implementation_tiers": dict(Counter(str(i.get("implementation_tier", "missing")) for i in instances if isinstance(i, dict))),
        },
        "accepted_gate_road_intersections": accepted_gates,
        "accepted_wall_tower_arch_intersections": accepted_tower_arches,
        "declared_wall_tower_clearances": declared_tower_clearances,
        "tolerated_positive_area_overlaps": tolerated,
        "unverified": unverified,
        "excluded_wall_walk_road_ids": excluded_wall_walk,
        "excluded_stair_to_wall_road_ids": excluded_stair_reservations,
        "vertical_access_status": "unimplemented" if excluded_wall_walk or excluded_stair_reservations else "not_applicable",
        "warnings": [
            "Wall walks and the four explicitly identified WALL_ACCESS stair reservations are excluded only from ground-road overlap checks; vertical access is unimplemented and structural intersections remain unverified.",
            "A declared gate opening is checked geometrically, but this report cannot prove that the rendered mesh contains that opening.",
            "Explicit wall-tower arches require named road IDs and authored clearance heights; source v2 has no minimum height requirement for those arches, and physical realization is a separate mesh check.",
            "Relative render paths and optional declared asset bounds are checked; file existence, source hashes and mesh bounds require separate asset validation.",
            "preserved_record is a typed declaration; comparison with a previous scene requires a separate preservation audit.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_placements(json.loads(args.scene.read_text()), json.loads(args.plan.read_text()))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
