"""Optional bounded shared-coordinate-plane resolution for the common compiler.

This module knows no assets. Source shape coordinates may refer to declarative
planes; after resolution the unchanged common core receives numeric shapes.
No expression language, eval, source generator, cell repair, or rendering.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

try:
    from . import core
except ImportError:
    import core

VERSION = 'common-coordinate-planes-1'
DEFAULT_MAX_PLANES = 4096
DEFAULT_MAX_DEPTH = 64
DEFAULT_MAX_REFERENCES = 100_000
DEFAULT_MAX_VISITED_NODES = 1_000_000


def resolve_master(master, request, *, max_planes=DEFAULT_MAX_PLANES,
                   max_depth=DEFAULT_MAX_DEPTH, max_references=DEFAULT_MAX_REFERENCES,
                   max_visited_nodes=DEFAULT_MAX_VISITED_NODES):
    """Return a numeric master plus resolved planes without mutating the source.

Snapping is in the source/master coordinate frame, before shape transforms.
Only coordinate references in actual geometry/constraint shapes are resolved.
The existing shape validator still owns geometric validity after resolution.
"""
    for value in (max_planes, max_depth, max_references, max_visited_nodes):
        core.require(type(value) is int and value > 0, 'positive plane-resolution budgets required')
    core.require(isinstance(master, dict), 'master must be an object')
    pitch = core.resolve_pitch(request)
    origin = master.get('grid_origin', [0, 0, 0])
    core.require(core.vector(origin), 'finite grid_origin required')
    declarations = master.get('coordinate_planes', [])
    core.require(isinstance(declarations, list), 'coordinate_planes must be an array')
    if len(declarations) > max_planes:
        raise core.BudgetExceeded('coordinate-plane declaration budget exceeded')
    planes = core.indexed(declarations, 'coordinate plane')
    resolved, active, dependency_depth = {}, set(), {}
    absolute_fields = {'id', 'axis', 'value', 'snap'}
    relative_fields = {'id', 'axis', 'relative_to', 'offset', 'minimum_offset_cells', 'offset_quantization'}

    def finite(value, label):
        core.require(core.number(value), label + ' must be finite')
        return value

    def quotient(value, label):
        return finite(value / pitch, label + ' / pitch')

    def get_plane(key, depth=0):
        core.require(isinstance(key, str) and key in planes, 'unknown coordinate plane')
        if depth > max_depth:
            raise core.BudgetExceeded('coordinate-plane dependency depth exceeded')
        core.require(key not in active, 'coordinate-plane dependency cycle')
        if key in resolved:
            return resolved[key]
        active.add(key)
        definition = planes[key]
        if 'relative_to' in definition:
            core.require(set(definition) <= relative_fields, 'invalid relative coordinate-plane fields')
            base = get_plane(definition['relative_to'], depth + 1)
            axis = definition.get('axis', base['axis'])
            core.require(type(axis) is int and axis == base['axis'], 'relative coordinate-plane axis mismatch')
            offset = finite(definition.get('offset'), 'plane offset')
            minimum = finite(definition.get('minimum_offset_cells', 0), 'minimum plane offset')
            core.require(minimum >= 0, 'minimum plane offset must be nonnegative')
            core.require(offset != 0 or minimum == 0, 'zero offset has no direction for a positive minimum')
            quantization = definition.get('offset_quantization', 'none')
            core.require(quantization in ('none', 'ceil_cells'), 'invalid plane offset quantization')
            magnitude = finite(max(abs(offset), finite(minimum * pitch, 'minimum world offset')), 'offset magnitude')
            if quantization == 'ceil_cells':
                cells = math.ceil(quotient(magnitude, 'offset magnitude') - core.EPS)
                # Tolerance must never erase a real positive declared offset.
                cells = max(1, cells) if magnitude > 0 else 0
                magnitude = finite(cells * pitch, 'quantized offset')
            value = finite(base['value'] + (math.copysign(magnitude, offset) if offset else 0), 'resolved plane')
            dependency_depth[key] = dependency_depth[definition['relative_to']] + 1
            if dependency_depth[key] > max_depth:
                raise core.BudgetExceeded('coordinate-plane dependency depth exceeded')
        else:
            core.require(set(definition) <= absolute_fields, 'invalid absolute coordinate-plane fields')
            axis = definition.get('axis')
            core.require(type(axis) is int and axis in (0, 1, 2), 'plane axis must be 0, 1, or 2')
            value = finite(definition.get('value'), 'plane value')
            dependency_depth[key] = 0
            snap = definition.get('snap', 'none')
            core.require(snap in ('none', 'floor', 'ceil', 'nearest'), 'invalid plane snap')
            if snap != 'none':
                position = quotient(finite(value - origin[axis], 'plane grid displacement'), 'plane grid displacement')
                if snap == 'floor':
                    index = math.floor(position + core.EPS)
                elif snap == 'ceil':
                    index = math.ceil(position - core.EPS)
                else:
                    index = math.floor(position + .5 + core.EPS)
                value = finite(origin[axis] + index * pitch, 'snapped plane')
        resolved[key] = {'axis': axis, 'value': value}
        active.remove(key)
        return resolved[key]

    # Resolve all declarations, including unused ones: malformed dead data is not accepted.
    for key in planes:
        get_plane(key)

    reference_count = visited_nodes = 0

    def replace(value, depth=0):
        nonlocal reference_count, visited_nodes
        visited_nodes += 1
        if visited_nodes > max_visited_nodes:
            raise core.BudgetExceeded('coordinate-plane traversal budget exceeded')
        if depth > max_depth:
            raise core.BudgetExceeded('coordinate-reference nesting depth exceeded')
        if isinstance(value, dict):
            if 'plane' in value:
                core.require(set(value) == {'plane'}, 'plane reference must contain only plane')
                reference_count += 1
                if reference_count > max_references:
                    raise core.BudgetExceeded('coordinate-plane reference budget exceeded')
                return get_plane(value['plane'])['value']
            return {key: replace(item, depth + 1) for key, item in value.items()}
        if isinstance(value, list):
            return [replace(item, depth + 1) for item in value]
        return copy.deepcopy(value)

    # Traverse/copy the bounded whole input first, without resolving arbitrary metadata.
    def bounded_copy(value, depth=0):
        nonlocal visited_nodes
        visited_nodes += 1
        if visited_nodes > max_visited_nodes:
            raise core.BudgetExceeded('coordinate-plane traversal budget exceeded')
        if depth > max_depth:
            raise core.BudgetExceeded('coordinate-reference nesting depth exceeded')
        if isinstance(value, dict):
            return {key: bounded_copy(item, depth + 1) for key, item in value.items()}
        if isinstance(value, list):
            return [bounded_copy(item, depth + 1) for item in value]
        return copy.deepcopy(value)

    result = bounded_copy(master)
    shape_holders = []
    core.require(isinstance(result.get('components'), list), 'components must be an array')
    for component in result['components']:
        core.require(isinstance(component, dict) and isinstance(component.get('operations'), list), 'component operations must be an array')
        shape_holders.extend(component['operations'])
    for key in ('assembly_cuts', 'constraints'):
        values = result.get(key, [])
        core.require(isinstance(values, list), key + ' must be an array')
        shape_holders.extend(values)
    for holder in shape_holders:
        core.require(isinstance(holder, dict), 'shape holder must be an object')
        if 'shape' in holder:
            holder['shape'] = replace(holder['shape'])
    return result, {key: resolved[key] for key in planes}


def compile_master(master, request, *, max_candidate_cells=2_000_000,
                   max_output_cells=1_000_000, **resolution_budgets):
    """Compile shared-plane data using the unchanged numeric common core."""
    numeric, planes = resolve_master(master, request, **resolution_budgets)
    result = core.compile_master(numeric, request, max_candidate_cells=max_candidate_cells,
                                 max_output_cells=max_output_cells)
    result['resolved_master_hash'] = result['master_hash']
    result['master_hash'] = core.digest(master)
    result['coordinate_planes'] = planes
    result['preprocessor'] = {'version': VERSION,
                              'source_hash': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    result['compiler_fingerprint'] = core.digest({'core': result['compiler_source_hash'],
                                                 'preprocessor': result['preprocessor']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('master', type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pitch', type=float)
    group.add_argument('--cells', type=int)
    parser.add_argument('--reference-span', type=float)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-candidates', type=int, default=2_000_000)
    args = parser.parse_args()
    request = {'pitch': args.pitch} if args.pitch is not None else {'cells': args.cells, 'reference_span': args.reference_span}
    try:
        result = compile_master(json.loads(args.master.read_text()), request,
                                max_candidate_cells=args.max_candidates)
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                json.dump(result, stream, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                stream.write('\n')
        print(json.dumps({key: result[key] for key in ('source_id', 'master_hash', 'payload_hash',
                                                       'pitch', 'candidate_cells', 'constraints', 'valid')}, indent=2))
        return 0 if result['valid'] else 1
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
