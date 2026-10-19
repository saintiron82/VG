"""Explicit immutable, reusable full-master sampling plans.

The default compiler and the reviewed v2 module are never changed. Prepare one
plan for an exact source/request, then call compile_prepared with different
integer cell_bounds. No geometry is cropped: ordered paints, cuts, selectors,
constraints, minimum-thickness rules and candidate/output budgets are retained.
Only immutable shape/transform/range preparation is amortized. The predicate is
the reviewed v2 exact-axis algorithm, with reference fallback for other shapes
and arbitrary rotations.

max_plan_bytes bounds retained plan storage, not caller inputs or result cells.
Callers must also enforce a process limit and execution/output budgets. No disk
cache, implicit cache, monkeypatch, automatic checkpoint migration or global
plan registry exists. Resume identity MUST include sampler provenance and each
plan_key, in addition to the caller's other inputs and chunk ownership contract.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, fields, is_dataclass
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
from types import MappingProxyType

from . import core as reference
from .core import (BudgetExceeded, EPS, VERSION, apply, compose, contains, digest,
                   dot, inside_polygon, inverse, neighbors, number, prepare_shape,
                   require, resolve_pitch, shape_bounds, transform, transpose,
                   validate_master, vector)

REFERENCE_CORE_SHA256 = "2a64ed2cdf43c9adb27a821170192f69fef0153c7be98cc85c903e34ff2a407b"
REFERENCE_V2_SHA256 = "e19e884b4decadaaf8c585952a8c5121f5872d9a3a73b74b4ca9dfc05de8c225"
SAMPLER_ID = "common.prepared_sampling_v3"
SAMPLER_VERSION = "immutable-full-master-exact-plan-1"
_MODULE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class ReferenceCompilerMismatch(RuntimeError):
    """A reviewed implementation changed; never resume under its old identity."""


class PlanSourceMismatch(ValueError):
    """A source, request or backend identity does not match the prepared plan."""


class _FrozenList(tuple):
    """Retain the distinction between source JSON lists and Python tuples."""
    __slots__ = ()


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return _FrozenList(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    # Source inputs are JSON data. Refuse mutable/non-JSON extension objects
    # rather than retain caller aliases inside a supposedly immutable plan.
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise reference.InvalidMaster("prepared plans require JSON-compatible source metadata")


def _thaw(value):
    if isinstance(value, MappingProxyType):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, _FrozenList):
        return [_thaw(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_thaw(v) for v in value)
    return value


def _deep_size(value, seen=None):
    """Conservative retained Python bytes; shared objects counted once."""
    if seen is None:
        seen = set()
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, (dict, MappingProxyType)):
        if isinstance(value, MappingProxyType):
            size += sys.getsizeof(dict(value))  # include backing dict storage
        size += sum(_deep_size(k, seen) + _deep_size(v, seen) for k, v in value.items())
    elif isinstance(value, (tuple, list)):
        size += sum(_deep_size(v, seen) for v in value)
    elif is_dataclass(value):
        size += sum(_deep_size(getattr(value, f.name), seen) for f in fields(value))
    return size


def get_sampler_provenance():
    paths = ((Path(reference.__file__), REFERENCE_CORE_SHA256, "reference core"),
             (Path(__file__).with_name("exact_sampling_v2.py"), REFERENCE_V2_SHA256, "reviewed v2"),
             (Path(__file__), _MODULE_SHA256, "loaded v3"))
    for path, expected, label in paths:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ReferenceCompilerMismatch(f"{label} SHA mismatch: expected {expected}, got {actual}; prepare/resume refused")
    return {"sampler_id": SAMPLER_ID, "sampler_version": SAMPLER_VERSION,
            "implementation_sha256": _MODULE_SHA256,
            "reference_core_sha256": REFERENCE_CORE_SHA256,
            "reviewed_v2_sha256": REFERENCE_V2_SHA256,
            "reference_compiler_version": VERSION,
            "source_geometry": "immutable full-master snapshot; no geometry crop",
            "predicate": "v2 exact signed-permutation box/extrusion; reference fallback"}


@dataclass(frozen=True, slots=True)
class _Sample:
    shape: object
    placement: object
    ranges: tuple
    inverse_basis: tuple
    axis_map: tuple | None


@dataclass(frozen=True, slots=True)
class _Operation:
    sample: _Sample
    action: str
    selector: tuple
    cell: object


@dataclass(frozen=True, slots=True)
class _Constraint:
    data: object
    selector: tuple
    a: tuple
    b: tuple
    sample: _Sample | None


@dataclass(frozen=True, slots=True)
class PreparedMaster:
    """Immutable input bytes, metadata and ordered geometry plan, with identity."""
    source_snapshot_json: bytes
    request_snapshot_json: bytes
    source_hash: str
    request_hash: str
    plan_key: str
    pitch: float
    grid_origin: tuple
    retained_bytes: int
    operation_count: int
    provenance: object
    _template: object
    _layers: tuple
    _cuts: tuple
    _constraints: tuple


def _selector(value):
    return tuple((k, tuple(v) if isinstance(v, list) else v) for k, v in value.items())


def _matches(selector, cell):
    return all(cell.get(k) in v if isinstance(v, tuple) else cell.get(k) == v for k, v in selector)


def _sample(shape, placement, pitch, origin):
    lo, hi = shape_bounds(shape)
    corners = [apply(placement, p) for p in itertools.product(*zip(lo, hi))]
    low = [min(p[i] for p in corners) for i in range(3)]
    high = [max(p[i] for p in corners) for i in range(3)]
    require(all(number(n) for n in low + high), "transformed bounds overflow")
    ranges = tuple(range(math.floor((a-o)/pitch+EPS), math.ceil((b-o)/pitch-EPS))
                   for a, b, o in zip(low, high, origin))
    ib = tuple(tuple(r) for r in transpose(placement["basis"]))
    exact = all(sum(v != 0 for v in row) == 1 and all(v in (0, 1, -1) for v in row) for row in ib)
    axis_map = tuple(next(j for j, v in enumerate(row) if v != 0) for row in ib) if exact else None
    return _Sample(_freeze(shape), _freeze(placement), ranges, ib, axis_map)


def _canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def prepare_master(master, request, *, max_plan_bytes=128*1024*1024):
    """Capture and prepare exactly this master/request once, without sampling.

    All source shapes and operations remain in the plan. New source edits require
    a new plan. Preparation does not evaluate global constraints; compilation
    evaluates the original constraints with the same full/bounded scope.
    """
    provenance = get_sampler_provenance()
    pitch = resolve_pitch(request)
    require(type(max_plan_bytes) is int and max_plan_bytes > 0, "positive plan-memory budget required")
    if _deep_size(master) + _deep_size(request) > max_plan_bytes:
        raise BudgetExceeded("plan-memory budget exceeded by source snapshot")
    source, request = copy.deepcopy(master), copy.deepcopy(request)
    components, instances = validate_master(source, pitch)
    origin = source.get("grid_origin", [0, 0, 0])
    require(vector(origin), "finite grid_origin required")
    origin = tuple(origin)
    source_bytes, request_bytes = _canonical_bytes(source), _canonical_bytes(request)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    request_hash = hashlib.sha256(request_bytes).hexdigest()
    plan_key = digest({"schema": "riverstone.voxel.prepared_plan.v1", "source_hash": source_hash,
                       "request_hash": request_hash, "pitch": pitch, "backend": provenance})
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

    # Prepare each component-local source operation only once, even for repeated
    # instances. World bounds depend on placement and are prepared per instance.
    local = {key: tuple((op, prepare_shape(op["shape"], pitch), transform(op.get("transform")))
                        for op in component["operations"])
             for key, component in components.items()}
    layers, cuts, constraints = [], [], []
    # Account incrementally as well as at the end; reject large plans before
    # constructing all remaining operations. This is conservative (shared source
    # strings between operations may be counted multiple times during the guard).
    running_bytes = len(source_bytes) + len(request_bytes)

    def account(value):
        nonlocal running_bytes
        running_bytes += _deep_size(value)
        if running_bytes > max_plan_bytes:
            raise BudgetExceeded("plan-memory budget exceeded while preparing operations")
        return value

    for instance in instances.values():
        component = components[instance["component"]]
        placement = world_transform(instance["id"])
        ops = []
        for operation, shape, op_transform in local[component["id"]]:
            cell = None if operation["action"] == "cut" else _freeze({
                "instance": instance["id"], "component": component["id"],
                "part": operation["part"], "material": operation["material"], "feature": operation["id"]})
            ops.append(account(_Operation(_sample(shape, compose(placement, op_transform), pitch, origin),
                operation["action"], _selector(operation.get("selector", {})), cell)))
        layers.append(tuple(ops))
    for operation in source.get("assembly_cuts", []):
        cuts.append(account(_Operation(_sample(prepare_shape(operation["shape"], pitch),
            transform(operation.get("transform")), pitch, origin), "cut",
            _selector(operation.get("selector", {})), None)))
    for c in source.get("constraints", []):
        sample = (_sample(prepare_shape(c["shape"], pitch), transform(c.get("transform")), pitch, origin)
                  if c["kind"] == "empty_region" else None)
        constraints.append(account(_Constraint(_freeze(c), _selector(c.get("selector", {})),
            _selector(c.get("a", {})), _selector(c.get("b", {})), sample)))
    template = _freeze({"schema": "riverstone.voxel.compiled.v1", "source_id": source["id"],
        "source_revision": source["revision"], "master_hash": source_hash, "compiler_version": VERSION,
        "compiler_source_hash": _MODULE_SHA256, "request": request, "pitch": pitch,
        "grid_origin": list(origin), "materials": source["materials"],
        "components": [{"id": c["id"], "parts": c["parts"]} for c in components.values()],
        "instances": [{**i, "world_transform": transforms[i["id"]]} for i in instances.values()],
        "extensions": source.get("extensions", {}), "generated_with_ai": False})
    plan = PreparedMaster(source_bytes, request_bytes, source_hash, request_hash, plan_key, pitch,
        origin, 0, sum(map(len, layers)) + len(cuts), _freeze(provenance), template,
        tuple(layers), tuple(cuts), tuple(constraints))
    retained_bytes = _deep_size(plan) + sys.getsizeof(0)  # conservative size of nonzero int
    if retained_bytes > max_plan_bytes:
        raise BudgetExceeded(f"plan-memory budget exceeded: {retained_bytes} > {max_plan_bytes}")
    # The object has not escaped preparation; all published fields are frozen.
    object.__setattr__(plan, "retained_bytes", retained_bytes)
    return plan


def assert_plan_matches(plan, master=None, request=None, *, source_hash=None, plan_key=None):
    """Explicit checkpoint/source guard. Omit master for a cheap trusted-hash check.

    Matching canonical hashes never silently reinterpret a new source or engine.
    A caller wishing to validate mutable source objects supplies master/request.
    The full immutable snapshot is checked here, not rehashed on every chunk.
    """
    if not isinstance(plan, PreparedMaster):
        raise PlanSourceMismatch("expected a PreparedMaster")
    if dict(plan.provenance) != get_sampler_provenance():
        raise PlanSourceMismatch("prepared backend identity changed")
    if hashlib.sha256(plan.source_snapshot_json).hexdigest() != plan.source_hash:
        raise PlanSourceMismatch("immutable source snapshot hash mismatch")
    if hashlib.sha256(plan.request_snapshot_json).hexdigest() != plan.request_hash:
        raise PlanSourceMismatch("immutable request snapshot hash mismatch")
    if master is not None and digest(master) != plan.source_hash:
        raise PlanSourceMismatch("master differs from immutable prepared source")
    if request is not None and digest(request) != plan.request_hash:
        raise PlanSourceMismatch("request differs from immutable prepared request")
    if source_hash is not None and source_hash != plan.source_hash:
        raise PlanSourceMismatch("expected source hash differs from prepared source")
    if plan_key is not None and plan_key != plan.plan_key:
        raise PlanSourceMismatch("checkpoint plan key differs from prepared plan")
    return True


def _execution_options(cell_bounds, max_candidate_cells, max_output_cells):
    if cell_bounds is not None:
        require(isinstance(cell_bounds, dict) and set(cell_bounds) == {"min", "max"}, "cell_bounds requires min/max integer XYZ")
        require(all(isinstance(cell_bounds[k], (list, tuple)) and len(cell_bounds[k]) == 3
                    and all(type(n) is int for n in cell_bounds[k]) for k in ("min", "max")), "cell_bounds requires min/max integer XYZ")
        require(all(a <= b for a, b in zip(cell_bounds["min"], cell_bounds["max"])), "cell_bounds min must not exceed max")
        cell_bounds = {k: list(cell_bounds[k]) for k in ("min", "max")}
    require(type(max_candidate_cells) is int and max_candidate_cells > 0 and type(max_output_cells) is int and max_output_cells > 0, "positive execution budgets required")
    return cell_bounds


def compile_prepared(plan, *, max_candidate_cells=2_000_000, max_output_cells=1_000_000, cell_bounds=None):
    """Execute an explicitly prepared full master, intersecting only sample ranges."""
    require(isinstance(plan, PreparedMaster), "PreparedMaster required")
    provenance = get_sampler_provenance()
    if dict(plan.provenance) != provenance:
        raise PlanSourceMismatch("prepared backend identity changed")
    cell_bounds = _execution_options(cell_bounds, max_candidate_cells, max_output_cells)
    pitch, origin = plan.pitch, plan.grid_origin
    cells, candidates, instance_layers, retained_cells = {}, 0, [], 0

    def points_in(sample):
        nonlocal candidates
        ranges = sample.ranges
        if cell_bounds is not None:
            ranges = tuple(range(max(r.start, low), min(r.stop, high))
                           for r, low, high in zip(ranges, cell_bounds["min"], cell_bounds["max"]))
        candidates += math.prod(len(r) for r in ranges)
        if candidates > max_candidate_cells:
            raise BudgetExceeded(f"candidate-cell budget exceeded: {candidates} > {max_candidate_cells}; split components or approve a larger execution budget")
        if not all(ranges):
            return
        shape, placement = sample.shape, sample.placement
        inverse_basis, axis_map = sample.inverse_basis, sample.axis_map
        if axis_map is not None and shape["kind"] in ("box", "extrusion"):
            baseline = [o+(r.start+.5)*pitch for o, r in zip(origin, ranges)]
            values = []
            for local_axis, world_axis in enumerate(axis_map):
                axis_values = {}
                for n in ranges[world_axis]:
                    world = list(baseline)
                    world[world_axis] = origin[world_axis]+(n+.5)*pitch
                    delta = [a-b for a, b in zip(world, placement["translation"])]
                    axis_values[n] = dot(inverse_basis[local_axis], delta)
                values.append(axis_values)
            epsilon = pitch*EPS
            if shape["kind"] == "box":
                accepted = [None, None, None]
                for j, world_axis in enumerate(axis_map):
                    accepted[world_axis] = [n for n, value in values[j].items()
                        if shape["min"][j]-epsilon <= value < shape["max"][j]-epsilon]
                yield from itertools.product(*accepted)
                return
            accepted_z = [n for n, value in values[2].items()
                          if shape["z_min"]-epsilon <= value < shape["z_max"]-epsilon]
            if not accepted_z:
                return
            point = [0, 0, 0]
            for nx, x in values[0].items():
                point[axis_map[0]] = nx
                for ny, y in values[1].items():
                    if not inside_polygon(x, y, shape["polygon"]):
                        continue
                    point[axis_map[1]] = ny
                    for nz in accepted_z:
                        point[axis_map[2]] = nz
                        yield tuple(point)
            return
        for point in itertools.product(*ranges):
            world = [o+(n+.5)*pitch for n, o in zip(point, origin)]
            if contains(shape, inverse(placement, world), epsilon=pitch*EPS):
                yield point

    for operations in plan._layers:
        instance_cells = {}
        for operation in operations:
            for point in points_in(operation.sample):
                if operation.action == "cut":
                    if point in instance_cells and _matches(operation.selector, instance_cells[point]):
                        del instance_cells[point]
                else:
                    instance_cells[point] = operation.cell
                    if len(instance_cells) > max_output_cells:
                        raise BudgetExceeded("output-cell budget exceeded")
        instance_layers.append(instance_cells)
        retained_cells += len(instance_cells)
        if retained_cells > max_output_cells:
            raise BudgetExceeded("retained/output-cell budget exceeded")
    for operation in plan._cuts:
        for point in points_in(operation.sample):
            for layer in instance_layers:
                if point in layer and _matches(operation.selector, layer[point]):
                    del layer[point]
    for layer in instance_layers:
        cells.update(layer)

    def selected(selector):
        return {p for p, cell in cells.items() if _matches(selector, cell)}

    checks = []
    for constraint in plan._constraints:
        c, kind = constraint.data, constraint.data["kind"]
        if kind == "nonempty":
            count = len(selected(constraint.selector))
            passed = count >= c.get("minimum_cells", 1)
            detail = {"occupied_cells": count}
        elif kind == "empty_region":
            region = set(points_in(constraint.sample))
            blockers = region & selected(constraint.selector)
            passed = bool(region) and not blockers
            detail = {"sampled_region_cells": len(region), "blocked_cells": len(blockers)}
        elif kind == "touch":
            a, b = selected(constraint.a), selected(constraint.b)
            passed = bool(a and b) and (bool(a & b) or any(q in b for p in a for q in neighbors(p)))
            detail = {"a_cells": len(a), "b_cells": len(b)}
        else:
            points = selected(constraint.selector)
            remaining = set(points)
            if remaining:
                queue = deque([min(remaining)])
                remaining.remove(queue[0])
                while queue:
                    for q in neighbors(queue.popleft()):
                        if q in remaining:
                            remaining.remove(q)
                            queue.append(q)
            passed = bool(points) and not remaining
            detail = {"occupied_cells": len(points), "unreached_cells": len(remaining)}
        checks.append({"id": c["id"], "kind": kind, "pass": passed, **detail})
    rows = [[*p, cell["instance"], cell["part"], cell["material"], cell["feature"]]
            for p, cell in sorted(cells.items())]
    result = _thaw(plan._template)
    result.update(cells=rows, payload_hash=digest(rows), candidate_cells=candidates,
                  constraints=checks, valid=all(check["pass"] for check in checks),
                  compiler_provenance={**provenance, "plan_key": plan.plan_key,
                      "source_hash": plan.source_hash, "request_hash": plan.request_hash})
    if cell_bounds is not None:
        result.update(evaluation_scope={"kind": "cell_bounds", **copy.deepcopy(cell_bounds)},
                      valid_scope="cell_bounds_only", global_constraints_evaluated=False,
                      global_constraints_valid=None)
        for check in checks:
            check.update(scope="cell_bounds_only", global_pass=None)
    return result


def compile_master_v3(master, request, *, max_candidate_cells=2_000_000,
                      max_output_cells=1_000_000, cell_bounds=None,
                      max_plan_bytes=128*1024*1024):
    """Explicit one-shot convenience; reusable callers should retain the plan."""
    resolve_pitch(request)
    cell_bounds = _execution_options(cell_bounds, max_candidate_cells, max_output_cells)
    plan = prepare_master(master, request, max_plan_bytes=max_plan_bytes)
    return compile_prepared(plan, max_candidate_cells=max_candidate_cells,
                            max_output_cells=max_output_cells, cell_bounds=cell_bounds)
