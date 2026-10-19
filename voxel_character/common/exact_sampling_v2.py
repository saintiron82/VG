"""Opt-in exact-axis sampler; the reference compiler remains byte-for-byte frozen.

Use compile_master_v2 explicitly. No default caller or global reference function
is replaced. Original master shapes, center samples, epsilon, range budgets,
operation order, cuts, selectors, labels, constraints and fallbacks are retained.
Only exactly signed-permutation boxes/extrusions use a separable predicate.

The copied ordered compile pipeline is pinned to REFERENCE_CORE_SHA256. Shape
preparation, shape predicates and validation remain reference-core functions.
Changing that reference source is an error requiring an explicit new review.
"""
from __future__ import annotations
from collections import deque
import copy
import hashlib
import itertools
import math
from pathlib import Path
from . import core as reference
from .core import (BudgetExceeded, EPS, VERSION, apply, compose, contains, digest,
                   dot, inside_polygon, inverse, mv, neighbors, number, prepare_shape, require,
                   resolve_pitch, selector_matches, shape_bounds, transform,
                   transpose, validate_master, vector)

REFERENCE_CORE_SHA256 = "2a64ed2cdf43c9adb27a821170192f69fef0153c7be98cc85c903e34ff2a407b"
SAMPLER_ID = "common.exact_sampling_v2"
SAMPLER_VERSION = "exact-axis-separable-1"


class ReferenceCompilerMismatch(RuntimeError):
    """The reviewed immutable reference source is no longer present."""


def get_sampler_provenance():
    actual = hashlib.sha256(Path(reference.__file__).read_bytes()).hexdigest()
    if actual != REFERENCE_CORE_SHA256:
        raise ReferenceCompilerMismatch(
            f"Reference core SHA mismatch: expected {REFERENCE_CORE_SHA256}, got {actual}; "
            "v2 sampling was not started. Explicitly use the reference sampler or review a new implementation.")
    return {"sampler_id": SAMPLER_ID, "sampler_version": SAMPLER_VERSION,
            "reference_core_sha256": actual,
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "reference_compiler_version": reference.VERSION,
            "exact_axis_only": True,
            "fallback": "original per-candidate reference helpers for all other cases"}


def compile_master_v2(master, request, *, max_candidate_cells=2_000_000,
                      max_output_cells=1_000_000, cell_bounds=None):
    """Explicit opt-in. Adds provenance; retains reference result semantics."""
    provenance = get_sampler_provenance()
    result = _compile_master_v2_impl(master, request,
        max_candidate_cells=max_candidate_cells, max_output_cells=max_output_cells,
        cell_bounds=cell_bounds)
    result["compiler_provenance"] = provenance
    return result


def _compile_master_v2_impl(master, request, *, max_candidate_cells=2_000_000, max_output_cells=1_000_000, cell_bounds=None):
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
        inverse_basis = transpose(placement["basis"])
        exact_permutation = all(sum(v != 0 for v in row) == 1 and
                                all(v in (0,1,-1) for v in row)
                                for row in inverse_basis)
        if exact_permutation and shape["kind"] in ("box", "extrusion") and all(ranges):
            axis_map = [next(j for j,v in enumerate(row) if v != 0) for row in inverse_basis]
            baseline = [o+(r.start+.5)*pitch for o,r in zip(origin,ranges)]
            values = []
            for local_axis,world_axis in enumerate(axis_map):
                axis_values = {}
                for n in ranges[world_axis]:
                    world = list(baseline)
                    world[world_axis] = origin[world_axis]+(n+.5)*pitch
                    delta = [a-b for a,b in zip(world,placement["translation"])]
                    axis_values[n] = dot(inverse_basis[local_axis],delta)
                values.append(axis_values)
            epsilon = pitch*EPS
            if shape["kind"] == "box":
                accepted = [None,None,None]
                for j,world_axis in enumerate(axis_map):
                    accepted[world_axis] = [n for n,value in values[j].items()
                        if shape["min"][j]-epsilon <= value < shape["max"][j]-epsilon]
                yield from itertools.product(*accepted)
                return
            accepted_z = [n for n,value in values[2].items()
                          if shape["z_min"]-epsilon <= value < shape["z_max"]-epsilon]
            if not accepted_z:return
            point = [0,0,0]
            for nx,x in values[0].items():
                point[axis_map[0]] = nx
                for ny,y in values[1].items():
                    if not inside_polygon(x,y,shape["polygon"]):continue
                    point[axis_map[1]] = ny
                    for nz in accepted_z:
                        point[axis_map[2]] = nz
                        yield tuple(point)
            return
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
