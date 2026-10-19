"""Small deterministic continuous-shape -> sparse-cell reference compiler.

No asset-name dispatch, imports from asset generators, AI calls, rendering, or
runtime job service. Geometry operations and semantic constraints are data.
"""
from __future__ import annotations
import argparse
from collections import deque
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path

SCHEMA = "riverstone.voxel.master.v1"
VERSION = "common-reference-1"
EPS = 1e-9
IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


class InvalidMaster(ValueError):
    pass


class BudgetExceeded(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidMaster(message)


def number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def vector(value, count=3):
    return isinstance(value, list) and len(value) == count and all(number(x) for x in value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def mv(matrix, point):
    return [dot(row, point) for row in matrix]


def transpose(matrix):
    return [list(row) for row in zip(*matrix)]


def transform(value=None):
    value = value or {}
    require(isinstance(value, dict), "transform must be an object")
    translation = value.get("translation", [0, 0, 0])
    basis = value.get("basis", IDENTITY)
    require(vector(translation), "transform translation must be finite XYZ")
    require(isinstance(basis, list) and len(basis) == 3 and all(vector(row) for row in basis), "transform basis must be 3x3")
    require(all(math.isclose(dot(a, b), float(i == j), abs_tol=1e-8)
                for i, a in enumerate(basis) for j, b in enumerate(basis)), "basis must be orthonormal; scale is a separate source edit")
    determinant = (basis[0][0] * (basis[1][1]*basis[2][2] - basis[1][2]*basis[2][1])
                   - basis[0][1] * (basis[1][0]*basis[2][2] - basis[1][2]*basis[2][0])
                   + basis[0][2] * (basis[1][0]*basis[2][1] - basis[1][1]*basis[2][0]))
    require(math.isclose(determinant, 1, abs_tol=1e-8), "basis must be a proper rotation")
    return {"translation": list(translation), "basis": copy.deepcopy(basis)}


def apply(t, p):
    return [a+b for a, b in zip(mv(t["basis"], p), t["translation"])]


def inverse(t, p):
    return mv(transpose(t["basis"]), [a-b for a, b in zip(p, t["translation"])])


def compose(parent, child):
    columns = transpose(child["basis"])
    return {"basis": [[dot(row, col) for col in columns] for row in parent["basis"]],
            "translation": apply(parent, child["translation"])}


def expanded_interval(low, high, width, anchor="center"):
    require(anchor in ("min", "max", "center"), "invalid minimum-thickness anchor")
    if high-low >= width:
        return low, high
    if anchor == "min":
        return low, low+width
    if anchor == "max":
        return high-width, high
    return (low+high-width)/2, (low+high+width)/2


def prepare_shape(source, pitch):
    """Evaluate only declared geometric minimum-thickness rules, never art edits."""
    require(isinstance(source, dict), "shape must be an object")
    shape = copy.deepcopy(source)
    kind = shape.get("kind")
    if kind == "box":
        lo, hi = shape.get("min"), shape.get("max")
        require(vector(lo) and vector(hi) and all(a < b for a, b in zip(lo, hi)), "box requires increasing XYZ bounds")
        minimum = shape.get("minimum_cells", [0, 0, 0])
        anchors = shape.get("anchors", ["center"]*3)
        require(vector(minimum) and all(n >= 0 for n in minimum), "box minimum_cells must be nonnegative XYZ")
        require(isinstance(anchors, list) and len(anchors) == 3, "box anchors must be three values")
        for i in range(3):
            lo[i], hi[i] = expanded_interval(lo[i], hi[i], minimum[i]*pitch, anchors[i])
    elif kind in ("extrusion", "lathe"):
        points = shape.get("polygon" if kind == "extrusion" else "profile")
        require(isinstance(points, list) and len(points) >= 3 and all(vector(p, 2) for p in points), f"{kind} requires a finite 2D polygon")
        if kind == "lathe":
            require(all(p[0] >= 0 for p in points), "lathe radius cannot be negative")
        else:
            lo, hi = shape.get("z_min"), shape.get("z_max")
            require(number(lo) and number(hi) and lo < hi, "extrusion requires z_min < z_max")
            minimum = shape.get("minimum_cells", 0)
            require(number(minimum) and minimum >= 0, "extrusion minimum_cells must be nonnegative")
            shape["z_min"], shape["z_max"] = expanded_interval(lo, hi, minimum*pitch, shape.get("anchor", "center"))
    elif kind == "annulus":
        inner, outer = shape.get("inner_radius"), shape.get("outer_radius")
        lo, hi = shape.get("y_min"), shape.get("y_max")
        require(all(number(n) for n in (inner, outer, lo, hi)) and 0 <= inner < outer and lo < hi, "annulus radii/y range invalid")
        minimum = shape.get("minimum_cells_y", 0)
        require(number(minimum) and minimum >= 0, "annulus minimum_cells_y must be nonnegative")
        shape["y_min"], shape["y_max"] = expanded_interval(lo, hi, minimum*pitch, shape.get("anchor_y", "max"))
    elif kind == "tube":
        points, radius = shape.get("points"), shape.get("radius")
        require(isinstance(points, list) and len(points) >= 2 and all(vector(p) for p in points), "tube requires at least two XYZ points")
        require(number(radius) and radius > 0, "tube radius must be positive")
        minimum = shape.get("minimum_radius_cells", 0)
        require(number(minimum) and minimum >= 0, "tube minimum_radius_cells must be nonnegative")
        shape["radius"] = max(radius, minimum*pitch)
    else:
        raise InvalidMaster(f"unsupported shape kind: {kind}")
    return shape


def shape_bounds(s):
    kind = s["kind"]
    if kind == "box":
        return s["min"], s["max"]
    if kind == "extrusion":
        return [min(p[0] for p in s["polygon"]), min(p[1] for p in s["polygon"]), s["z_min"]], [max(p[0] for p in s["polygon"]), max(p[1] for p in s["polygon"]), s["z_max"]]
    if kind == "lathe":
        radius = max(p[0] for p in s["profile"])
        return [-radius, min(p[1] for p in s["profile"]), -radius], [radius, max(p[1] for p in s["profile"]), radius]
    if kind == "annulus":
        radius = s["outer_radius"]
        return [-radius, s["y_min"], -radius], [radius, s["y_max"], radius]
    radius = s["radius"]
    return [min(p[i] for p in s["points"])-radius for i in range(3)], [max(p[i] for p in s["points"])+radius for i in range(3)]


def inside_polygon(x, y, points):
    inside = False
    for i, (a, b) in enumerate(points):
        c, d = points[i-1]
        if (b > y) != (d > y) and x < (c-a)*(y-b)/(d-b)+a:
            inside = not inside
    return inside


def segment_distance2(p, a, b):
    v = [y-x for x, y in zip(a, b)]
    w = [x-y for x, y in zip(p, a)]
    den = dot(v, v)
    factor = max(0, min(1, dot(w, v)/den)) if den else 0
    return sum((x-factor*y)**2 for x, y in zip(w, v))


def contains(s, p, epsilon=0):
    x, y, z = p
    kind = s["kind"]
    if kind == "box":
        return all(a-epsilon <= n < b-epsilon for a, n, b in zip(s["min"], p, s["max"]))
    if kind == "extrusion":
        return s["z_min"]-epsilon <= z < s["z_max"]-epsilon and inside_polygon(x, y, s["polygon"])
    if kind == "lathe":
        return inside_polygon(math.hypot(x, z), y, s["profile"])
    if kind == "annulus":
        return s["y_min"]-epsilon <= y < s["y_max"]-epsilon and s["inner_radius"] <= math.hypot(x, z) <= s["outer_radius"]
    return any(segment_distance2(p, a, b) <= s["radius"]**2 for a, b in zip(s["points"], s["points"][1:]))


def selector_matches(selector, cell):
    return all(cell.get(key) in value if isinstance(value, list) else cell.get(key) == value for key, value in selector.items())


def validate_selector(value):
    require(isinstance(value, dict) and set(value) <= {"instance", "component", "part", "material", "feature"}, "invalid cell selector")
    require(all(isinstance(item, str) or isinstance(item, list) and all(isinstance(v, str) for v in item) for item in value.values()), "selector values must be IDs or lists of IDs")


def indexed(items, label):
    require(isinstance(items, list), f"{label} must be an array")
    result = {}
    for value in items:
        require(isinstance(value, dict) and isinstance(value.get("id"), str) and value["id"], f"{label} ID required")
        require(value["id"] not in result, f"duplicate {label} ID {value['id']}")
        result[value["id"]] = value
    return result


def validate_master(master, pitch):
    require(isinstance(master, dict) and master.get("schema") == SCHEMA, "unsupported master schema")
    require(isinstance(master.get("id"), str) and master["id"], "master ID required")
    require(type(master.get("revision")) is int and master["revision"] > 0, "positive master revision required")
    require(master.get("axes") == {"up": "+Y", "front": "+Z", "right": "+X"}, "normalize source coordinates explicitly to project axes")
    materials = master.get("materials")
    require(isinstance(materials, dict) and bool(materials) and all(isinstance(k, str) for k in materials), "materials map required")
    components = indexed(master.get("components"), "component")
    instances = indexed(master.get("instances"), "instance")
    require(bool(components) and bool(instances), "components and instances required")
    for component in components.values():
        parts = indexed(component.get("parts"), "part")
        for part in parts.values():
            require(vector(part.get("pivot")), "finite local part pivot required")
        for operation in indexed(component.get("operations"), "operation").values():
            require(operation.get("action") in ("paint", "cut"), "operation action must be paint or cut")
            require(operation.get("part") in parts, "operation part must exist")
            if operation["action"] == "paint":
                require(operation.get("material") in materials, "unknown operation material")
            prepare_shape(operation.get("shape"), pitch)
            transform(operation.get("transform"))
            validate_selector(operation.get("selector", {}))
    for instance in instances.values():
        require(instance.get("component") in components, "unknown instance component")
        require(instance.get("parent") is None or instance.get("parent") in instances, "unknown instance parent")
        transform(instance.get("transform"))
    for operation in indexed(master.get("assembly_cuts", []), "assembly cut").values():
        prepare_shape(operation.get("shape"), pitch)
        transform(operation.get("transform"))
        validate_selector(operation.get("selector", {}))
    for c in indexed(master.get("constraints", []), "constraint").values():
        require(c.get("kind") in ("nonempty", "empty_region", "touch", "connected"), "unsupported semantic constraint")
        if c["kind"] == "touch":
            validate_selector(c.get("a")); validate_selector(c.get("b"))
        else:
            validate_selector(c.get("selector", {}))
        if c["kind"] == "empty_region":
            prepare_shape(c.get("shape"), pitch); transform(c.get("transform"))
        if c["kind"] == "nonempty":
            require(type(c.get("minimum_cells", 1)) is int and c.get("minimum_cells", 1) >= 1, "nonempty minimum must be positive integer")
    return components, instances


def resolve_pitch(request):
    require(isinstance(request, dict), "sampling request required")
    if "pitch" in request:
        require("cells" not in request and "reference_span" not in request, "choose pitch or reference_span/cells")
        pitch = request["pitch"]
    else:
        span, cells = request.get("reference_span"), request.get("cells")
        require(number(span) and span > 0 and type(cells) is int and cells > 0, "positive reference_span and cells required")
        pitch = span/cells
    require(number(pitch) and pitch > 0, "pitch must be finite and positive")
    return pitch


def neighbors(point):
    for axis in range(3):
        for sign in (-1, 1):
            p = list(point); p[axis] += sign
            yield tuple(p)


def compile_master(master, request, *, max_candidate_cells=2_000_000, max_output_cells=1_000_000, cell_bounds=None):
    """Pure compile; execution budgets/bounds never redefine master geometry.

    Optional cell_bounds={"min":[ix,iy,iz],"max":[jx,jy,jz]} intersects
    integer sample ranges only (inclusive/exclusive). Shapes, predicates,
    transforms and ordered operations are identical to the default path.
    Constraints/valid on a bounded result apply ONLY to that selection;
    global constraints require a separate complete aggregation.
    """
    pitch = resolve_pitch(request)
    if cell_bounds is not None:
        require(isinstance(cell_bounds, dict) and set(cell_bounds) == {"min", "max"}, "cell_bounds requires min/max integer XYZ")
        require(all(isinstance(cell_bounds[k], (list, tuple)) and len(cell_bounds[k]) == 3
                    and all(type(n) is int for n in cell_bounds[k]) for k in ("min", "max")), "cell_bounds requires min/max integer XYZ")
        require(all(a <= b for a, b in zip(cell_bounds["min"], cell_bounds["max"])), "cell_bounds min must not exceed max")
        cell_bounds = {k: list(cell_bounds[k]) for k in ("min", "max")}
    require(type(max_candidate_cells) is int and max_candidate_cells > 0 and type(max_output_cells) is int and max_output_cells > 0, "positive execution budgets required")
    components, instances = validate_master(master, pitch)
    origin = master.get("grid_origin", [0, 0, 0])
    require(vector(origin), "finite grid_origin required")
    origin = list(origin)
    transforms, visiting = {}, set()

    def world_transform(key):
        if key in transforms:
            return transforms[key]
        require(key not in visiting, "instance hierarchy cycle")
        visiting.add(key)
        instance = instances[key]
        value = transform(instance.get("transform"))
        if instance.get("parent") is not None:
            value = compose(world_transform(instance["parent"]), value)
        visiting.remove(key)
        transforms[key] = value
        return value

    cells, candidates = {}, 0
    instance_layers, retained_cells = [], 0

    def points_in(shape, placement):
        nonlocal candidates
        lo, hi = shape_bounds(shape)
        corners = [apply(placement, p) for p in itertools.product(*zip(lo, hi))]
        low = [min(p[i] for p in corners) for i in range(3)]
        high = [max(p[i] for p in corners) for i in range(3)]
        require(all(number(n) for n in low+high), "transformed bounds overflow")
        ranges = [range(math.floor((a-o)/pitch+EPS), math.ceil((b-o)/pitch-EPS)) for a, b, o in zip(low, high, origin)]
        if cell_bounds is not None:
            ranges = [range(max(r.start, low), min(r.stop, high))
                      for r, low, high in zip(ranges, cell_bounds["min"], cell_bounds["max"])]
        candidates += math.prod(len(r) for r in ranges)
        if candidates > max_candidate_cells:
            raise BudgetExceeded(f"candidate-cell budget exceeded: {candidates} > {max_candidate_cells}; split components or approve a larger execution budget")
        for point in itertools.product(*ranges):
            world = [o+(n+.5)*pitch for n, o in zip(point, origin)]
            if contains(shape, inverse(placement, world), epsilon=pitch*EPS):
                yield point

    for instance in instances.values():
        component = components[instance["component"]]
        placement = world_transform(instance["id"])
        instance_cells = {}
        for operation in component["operations"]:
            shape = prepare_shape(operation["shape"], pitch)
            op_placement = compose(placement, transform(operation.get("transform")))
            for point in points_in(shape, op_placement):
                if operation["action"] == "cut":
                    # Component cuts are local to this instance; global cuts are explicit.
                    if point in instance_cells and selector_matches(operation.get("selector", {}), instance_cells[point]):
                        del instance_cells[point]
                else:
                    instance_cells[point] = {"instance": instance["id"], "component": component["id"], "part": operation["part"], "material": operation["material"], "feature": operation["id"]}
                    if len(instance_cells) > max_output_cells:
                        raise BudgetExceeded("output-cell budget exceeded")
        # Keep layers until target-specific assembly cuts are complete.
        instance_layers.append(instance_cells)
        retained_cells += len(instance_cells)
        if retained_cells > max_output_cells:
            raise BudgetExceeded("retained/output-cell budget exceeded")
    for operation in master.get("assembly_cuts", []):
        for point in points_in(prepare_shape(operation["shape"], pitch), transform(operation.get("transform"))):
            for layer in instance_layers:
                if point in layer and selector_matches(operation.get("selector", {}), layer[point]):
                    del layer[point]
    for layer in instance_layers:
        cells.update(layer)

    def selected(selector):
        return {p for p, cell in cells.items() if selector_matches(selector, cell)}

    checks = []
    for c in master.get("constraints", []):
        kind = c["kind"]
        if kind == "nonempty":
            count = len(selected(c.get("selector", {})))
            passed = count >= c.get("minimum_cells", 1)
            detail = {"occupied_cells": count}
        elif kind == "empty_region":
            region = set(points_in(prepare_shape(c["shape"], pitch), transform(c.get("transform"))))
            blockers = region & selected(c.get("selector", {}))
            passed = bool(region) and not blockers
            detail = {"sampled_region_cells": len(region), "blocked_cells": len(blockers)}
        elif kind == "touch":
            a, b = selected(c["a"]), selected(c["b"])
            passed = bool(a and b) and (bool(a & b) or any(q in b for p in a for q in neighbors(p)))
            detail = {"a_cells": len(a), "b_cells": len(b)}
        else:
            points = selected(c.get("selector", {}))
            remaining = set(points)
            if remaining:
                queue = deque([min(remaining)]); remaining.remove(queue[0])
                while queue:
                    for q in neighbors(queue.popleft()):
                        if q in remaining:
                            remaining.remove(q); queue.append(q)
            passed = bool(points) and not remaining
            detail = {"occupied_cells": len(points), "unreached_cells": len(remaining)}
        checks.append({"id": c["id"], "kind": kind, "pass": passed, **detail})
    rows = [[*p, cell["instance"], cell["part"], cell["material"], cell["feature"]] for p, cell in sorted(cells.items())]
    result = {"schema": "riverstone.voxel.compiled.v1", "source_id": master["id"], "source_revision": master["revision"],
            "master_hash": digest(master), "compiler_version": VERSION,
            "compiler_source_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "request": copy.deepcopy(request), "pitch": pitch, "grid_origin": origin,
            "materials": copy.deepcopy(master["materials"]),
            "components": [{"id": c["id"], "parts": copy.deepcopy(c["parts"])} for c in components.values()],
            "instances": [{**copy.deepcopy(i), "world_transform": transforms[i["id"]]} for i in instances.values()],
            "extensions": copy.deepcopy(master.get("extensions", {})),
            "cells": rows, "payload_hash": digest(rows), "candidate_cells": candidates,
            "constraints": checks, "valid": all(check["pass"] for check in checks), "generated_with_ai": False}
    if cell_bounds is not None:
        result.update(evaluation_scope={"kind": "cell_bounds", **copy.deepcopy(cell_bounds)},
                      valid_scope="cell_bounds_only", global_constraints_evaluated=False,
                      global_constraints_valid=None)
        for check in checks:
            check.update(scope="cell_bounds_only", global_pass=None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pitch", type=float)
    group.add_argument("--cells", type=int)
    parser.add_argument("--reference-span", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-candidates", type=int, default=2_000_000)
    args = parser.parse_args()
    request = {"pitch": args.pitch} if args.pitch is not None else {"cells": args.cells, "reference_span": args.reference_span}
    try:
        master = json.loads(args.master.read_text())
        result = compile_master(master, request, max_candidate_cells=args.max_candidates)
        if args.output:
            # A new revision/output is explicit; never silently overwrite prior evidence.
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                stream.write("\n")
        print(json.dumps({k: value for k, value in result.items() if k not in ("cells", "materials", "instances")}, indent=2))
        return 0 if result["valid"] else 1
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
