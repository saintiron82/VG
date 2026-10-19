"""Generic fixed cell pools + analytic time functions over one common source.

Authoring/bake only: preserve immutable static geometry, derive bounded pools,
validate sampled states, and emit render.v1 data. No runtime object-name branch,
fluid simulation, random emissions, or mandatory per-frame state table.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import core
import coordinate_planes
from render_data import make_render_data

SCHEMA = 'riverstone.voxel.cell_animation.v1'
VERSION = 'common-cell-pools-1'


def require(value, message):
    core.require(value, message)


def finite(value, name):
    require(core.number(value), name + ' must be finite')
    return value


def positive(value, name):
    finite(value, name)
    require(value > 0, name + ' must be positive')
    return value


def vec(value, name):
    require(core.vector(value), name + ' must be finite XYZ')
    return value


def unit_axis(value, name):
    vec(value, name)
    require(math.isclose(core.dot(value, value), 1, rel_tol=0, abs_tol=1e-7), name + ' must be unit length')
    return value


def color(value):
    require(isinstance(value, str) and len(value) in (7, 9) and value.startswith('#') and
            all(c in '0123456789abcdefABCDEF' for c in value[1:]), 'hex RGB/RGBA palette required')
    return value


def geometry_selector(value):
    core.validate_selector(value)
    require(bool(value), 'empty geometry selector is not permitted')
    return value


def match_row(selector, row, instances):
    return core.selector_matches(selector, {'instance': row[3], 'component': instances[row[3]]['component'],
                                           'part': row[4], 'material': row[5], 'feature': row[6]})


def static_layer(master, exclusions):
    """Remove selected paints BEFORE sampling; all original cut scopes survive."""
    result = copy.deepcopy(master)
    source_components = {c['id']: c for c in master['components']}
    clones = {key: [] for key in source_components}
    for index, instance in enumerate(master['instances']):
        clones[instance['component']].append('static_cell_layer_' + str(index))

    def remap(operation):
        selector = operation.get('selector', {})
        if 'component' in selector:
            keys = selector['component'] if isinstance(selector['component'], list) else [selector['component']]
            selector['component'] = [clone for key in keys for clone in clones.get(key, [])]

    result['components'] = []
    for index, instance in enumerate(result['instances']):
        original_id = instance['component']
        component = copy.deepcopy(source_components[original_id])
        component['id'] = 'static_cell_layer_' + str(index)
        kept = []
        for operation in component['operations']:
            metadata = {'instance': instance['id'], 'component': original_id, 'part': operation['part'],
                        'material': operation.get('material'), 'feature': operation['id']}
            if operation['action'] == 'cut' or not any(core.selector_matches(s, metadata) for s in exclusions):
                remap(operation)
                kept.append(operation)
        component['operations'] = kept
        result['components'].append(component)
        instance['component'] = component['id']
    for operation in result.get('assembly_cuts', []):
        remap(operation)
    result['constraints'] = []  # Full-source constraints were checked before partitioning.
    return result


def cell_size(definition, pitch):
    require(isinstance(definition, dict), 'cell_size recipe required')
    if set(definition) == {'cells'}:
        return positive(definition['cells'], 'cell size in cells') * pitch
    require(set(definition) <= {'world', 'minimum_cells', 'maximum_cells'} and 'world' in definition,
            'invalid cell_size recipe')
    value = positive(definition['world'], 'world cell size')
    minimum = finite(definition.get('minimum_cells', 0), 'minimum cell size')
    maximum = finite(definition.get('maximum_cells', max(value/pitch, minimum)), 'maximum cell size')
    require(0 <= minimum <= maximum and maximum > 0, 'invalid cell size limits')
    return min(max(value, minimum*pitch), maximum*pitch)


def resolve_position(values, planes):
    require(isinstance(values, list) and len(values) == 3, 'member position requires XYZ')
    out = []
    for axis, value in enumerate(values):
        if isinstance(value, dict):
            require(set(value) == {'plane'} and value['plane'] in planes, 'unknown or malformed member plane')
            plane = planes[value['plane']]
            require(plane['axis'] == axis, 'member coordinate-plane axis mismatch')
            value = plane['value']
        out.append(finite(value, 'member position'))
    return out


def lattice_positions(source, pitch, origin, max_candidates):
    center = vec(source.get('origin'), 'lattice origin')
    axis = unit_axis(source.get('axis'), 'lattice axis')
    length = positive(source.get('length'), 'lattice length')
    minimum = finite(source.get('minimum_radius_cells', 0), 'minimum lattice radius')
    require(minimum >= 0, 'minimum lattice radius must be nonnegative')
    radius = max(positive(source.get('radius'), 'lattice radius'), minimum*pitch)
    end = [center[i]+axis[i]*length for i in range(3)]
    # A bounded capsule AABB is conservative; the axial test removes its caps.
    low = [min(center[i], end[i])-radius for i in range(3)]
    high = [max(center[i], end[i])+radius for i in range(3)]
    ranges = [range(math.floor((low[i]-origin[i])/pitch), math.ceil((high[i]-origin[i])/pitch)) for i in range(3)]
    candidates = math.prod(len(r) for r in ranges)
    if candidates > max_candidates:
        raise core.BudgetExceeded('pool lattice candidate budget exceeded')
    positions = []
    for index in itertools.product(*ranges):
        p = [origin[i]+(index[i]+.5)*pitch for i in range(3)]
        relative = [p[i]-center[i] for i in range(3)]
        along = core.dot(relative, axis)
        across2 = max(0, core.dot(relative, relative)-along*along)
        if -pitch*core.EPS <= along <= length+pitch*core.EPS and across2 <= radius*radius+pitch*pitch*core.EPS:
            positions.append(p)
    return sorted(positions, key=lambda p: (core.dot(p, axis), p[0], p[1], p[2]))


def validate_keys(value, duration):
    require(isinstance(value, list) and len(value) >= 2, 'at least two scalar keys required')
    previous = -math.inf
    for key in value:
        require(core.vector(key, 2) and previous < key[0] <= duration and key[0] >= 0, 'strict finite scalar key times required')
        previous = key[0]
    require(value[0][0] == 0 and value[-1][0] == duration, 'scalar keys must cover duration')


def validate_animation(animation, *, max_instances=100_000, max_pools=64):
    duration = positive(animation.get('duration'), 'duration')
    rate = positive(animation.get('update_hz'), 'update_hz')
    require(type(animation.get('loop')) is bool, 'explicit loop flag required')
    require(type(animation.get('seed')) is int and animation['seed'] == 0, 'v1 is deterministic and accepts only seed 0')
    require(math.isclose(duration*rate, round(duration*rate), abs_tol=1e-7) and 1 <= round(duration*rate) <= 10_000,
            'duration*update_hz must be bounded integer')
    bounds = animation.get('bounds')
    require(isinstance(bounds, dict), 'visual bounds required')
    low, high = vec(bounds.get('min'), 'bounds min'), vec(bounds.get('max'), 'bounds max')
    require(all(a < b for a, b in zip(low, high)), 'increasing visual bounds required')
    pools = animation.get('pools')
    require(isinstance(pools, list) and 0 < len(pools) <= max_pools, 'bounded nonempty pool list required')
    seen, total = set(), 0
    for pool in pools:
        require(isinstance(pool, dict) and isinstance(pool.get('id'), str) and pool['id'] and pool['id'] not in seen, 'unique pool ID required')
        seen.add(pool['id'])
        positive(pool.get('cell_size'), 'pool cell size')
        positions = pool.get('positions')
        require(isinstance(positions, list) and bool(positions) and all(core.vector(p) for p in positions), 'nonempty finite rest positions required')
        count = len(positions); total += count
        if total > max_instances:
            raise core.BudgetExceeded('fixed instance pool budget exceeded')
        palette = pool.get('palette')
        require(isinstance(palette, list) and bool(palette), 'pool palette required')
        for item in palette: color(item)
        indices = pool.get('color_indices')
        require(isinstance(indices, list) and len(indices) == count and
                all(type(i) is int and 0 <= i < len(palette) for i in indices), 'one valid color index per member required')
        band = pool.get('banded_color')
        if band is not None:
            require(isinstance(band, dict), 'banded_color must be an object')
            unit_axis(band.get('axis'), 'color axis'); positive(band.get('band_size'), 'band size')
            finite(band.get('speed'), 'band speed'); finite(band.get('step_rate'), 'band step rate')
            require(type(band.get('cycle')) is int and band['cycle'] > 0, 'positive integer band cycle required')
            require(type(band.get('bright_bands')) is int and 0 <= band['bright_bands'] <= band['cycle'], 'invalid bright band count')
            for key in ('base_index', 'highlight_index'):
                require(type(band.get(key)) is int and 0 <= band[key] < len(palette), 'invalid band color index')
        threshold = pool.get('threshold_visibility')
        if threshold is not None:
            require(isinstance(threshold, dict) and 'ballistic' not in pool, 'one visibility function per pool required')
            unit_axis(threshold.get('axis'), 'threshold axis')
            validate_keys(threshold.get('keys'), duration)
            require(threshold.get('interpolation') in ('linear', 'smoothstep'), 'unsupported scalar interpolation')
            projected = [core.dot(p, threshold['axis']) for p in positions]
            require(projected == sorted(projected), 'threshold positions must be sorted along axis')
        motion = pool.get('ballistic')
        if motion is not None:
            require(isinstance(motion, dict), 'ballistic must be an object')
            period = positive(motion.get('period'), 'motion period')
            vec(motion.get('acceleration'), 'acceleration'); unit_axis(motion.get('up_axis'), 'up axis')
            finite(motion.get('minimum_up_offset'), 'minimum up offset')
            for key in ('velocities', 'phases', 'lifetimes'):
                require(isinstance(motion.get(key), list) and len(motion[key]) == count, 'one '+key+' entry per member required')
            require(all(core.vector(v) for v in motion['velocities']), 'finite velocities required')
            require(all(core.number(v) for v in motion['phases']), 'finite phases required')
            require(all(core.number(v) and 0 < v <= period for v in motion['lifetimes']), 'lifetimes must fit period')
            if 'quantize' in motion:
                require(isinstance(motion['quantize'], dict), 'quantize must be an object')
                positive(motion['quantize'].get('pitch'), 'quantization pitch'); vec(motion['quantize'].get('origin'), 'quantization origin')
    return total


def scalar(keys, seconds, interpolation):
    for left, right in zip(keys, keys[1:]):
        if seconds <= right[0]:
            amount = max(0, min(1, (seconds-left[0])/(right[0]-left[0])))
            if interpolation == 'smoothstep': amount = amount*amount*(3-2*amount)
            return left[1]+(right[1]-left[1])*amount
    return keys[-1][1]


def evaluate(animation, seconds):
    """Debug/oracle evaluator. Runtime independently evaluates the same functions."""
    finite(seconds, 'sample time')
    duration, rate = animation['duration'], animation['update_hz']
    playhead = seconds % duration if animation['loop'] else max(0, min(duration, seconds))
    time = min(duration, math.floor(playhead*rate+1e-8)/rate)
    if animation['loop'] and time >= duration: time = 0.0
    pools = []
    for pool in animation['pools']:
        output_positions, colors, member_ids = [], [], []
        threshold = pool.get('threshold_visibility')
        limit = scalar(threshold['keys'], time, threshold['interpolation']) if threshold else None
        motion = pool.get('ballistic')
        for index, rest in enumerate(pool['positions']):
            if threshold and core.dot(rest, threshold['axis']) > limit + 1e-8: continue
            position = list(rest)
            if motion:
                age = (time-motion['phases'][index]) % motion['period']
                lifetime = motion['lifetimes'][index]
                if age >= lifetime - min(1e-8, lifetime*1e-6): continue
                offset = [motion['velocities'][index][a]*age + .5*motion['acceleration'][a]*age*age for a in range(3)]
                if core.dot(offset, motion['up_axis']) < motion['minimum_up_offset']-1e-8: continue
                position = [rest[a]+offset[a] for a in range(3)]
                quantize = motion.get('quantize')
                if quantize:
                    p, origin = quantize['pitch'], quantize['origin']
                    position = [origin[a]+(math.floor((position[a]-origin[a])/p)+.5)*p for a in range(3)]
            color_index = pool['color_indices'][index]
            band = pool.get('banded_color')
            if band:
                phase = math.floor((core.dot(rest, band['axis'])+time*band['speed'])/band['band_size']) + math.floor(time*band['step_rate'])
                color_index = band['highlight_index'] if phase % band['cycle'] < band['bright_bands'] else band['base_index']
            output_positions.append(position); colors.append(color_index); member_ids.append(index)
        pools.append({'id': pool['id'], 'visible_count': len(output_positions), 'positions': output_positions,
                      'color_indices': colors, 'member_ids': member_ids})
    return {'playhead': playhead, 'evaluation_time': time, 'pools': pools}


def make_render(master, compiled, clip, *, max_candidates=2_000_000, max_instances=100_000):
    require(isinstance(clip, dict) and clip.get('schema') == SCHEMA, 'unsupported cell animation source')
    require(clip.get('source_id') == master['id'] and clip.get('master_hash') == core.digest(master), 'clip source/master mismatch')
    require(compiled.get('schema') == 'riverstone.voxel.compiled.v1' and compiled.get('valid') is True,
            'structurally valid common compiled source required')
    require(compiled.get('master_hash') == core.digest(master) and compiled.get('payload_hash') == core.digest(compiled.get('cells')),
            'compiled source/payload mismatch')
    pitch, origin = compiled['pitch'], compiled['grid_origin']
    _, planes = coordinate_planes.resolve_master(master, {'pitch': pitch})
    instances = {i['id']: i for i in master['instances']}
    exclusions = clip.get('static_exclusions', [])
    require(isinstance(exclusions, list), 'static_exclusions must be an array')
    for selector in exclusions:
        geometry_selector(selector)
        require(any(match_row(selector, row, instances) for row in compiled['cells']), 'static exclusion matched no source cells')
    definitions = clip.get('pools')
    require(isinstance(definitions, list) and 0 < len(definitions) <= 64, 'bounded nonempty pool definitions required')
    pools = []; selected_members = set(); static_occluders = set()
    for definition in definitions:
        require(isinstance(definition, dict), 'pool definition must be an object')
        size = cell_size(definition.get('cell_size'), pitch)
        source = definition.get('source')
        require(isinstance(source, dict), 'pool source required')
        occludes = definition.get('occludes_static', False)
        require(type(occludes) is bool, 'occludes_static must be a boolean')
        if occludes:
            require(source.get('kind') == 'selected_cells' and size == pitch and
                    'threshold_visibility' not in definition and 'ballistic' not in definition,
                    'static occlusion requires always-visible fixed selected cells at source pitch')
        pool = {'id': definition.get('id'), 'cell_size': size, 'palette': copy.deepcopy(definition.get('palette'))}
        if source.get('kind') == 'selected_cells':
            selector = geometry_selector(source.get('selector'))
            rows = [row for row in compiled['cells'] if match_row(selector, row, instances)]
            coordinates = {tuple(row[:3]) for row in rows}
            require(not selected_members & coordinates, 'selected cell pools overlap')
            selected_members |= coordinates
            if occludes: static_occluders |= coordinates
            pool['positions'] = [[origin[i]+(row[i]+.5)*pitch for i in range(3)] for row in rows]
            pool['color_indices'] = [definition.get('default_color_index', 0)]*len(rows)
        elif source.get('kind') == 'axial_lattice':
            pool['positions'] = lattice_positions(source, pitch, origin, max_candidates)
            pool['color_indices'] = [definition.get('default_color_index', 0)]*len(pool['positions'])
        elif source.get('kind') == 'members':
            members = source.get('members')
            require(isinstance(members, list) and 0 < len(members) <= max_instances, 'bounded explicit members required')
            pool['positions'] = []
            for member in members:
                require(isinstance(member, dict), 'member must be an object')
                position = resolve_position(member.get('position'), planes)
                offset = vec(member.get('offset_in_cell_sizes', [0, 0, 0]), 'member offset')
                pool['positions'].append([position[a]+offset[a]*size for a in range(3)])
            pool['color_indices'] = [member.get('color_index', 0) for member in members]
        else:
            raise core.InvalidMaster('unsupported generic pool source')
        for behavior in ('banded_color', 'threshold_visibility', 'ballistic'):
            if behavior not in definition: continue
            rule = copy.deepcopy(definition[behavior])
            require(isinstance(rule, dict), 'behavior must be an object')
            if behavior == 'banded_color' and 'band_size_cells' in rule:
                require('band_size' not in rule, 'choose world or cell band size')
                rule['band_size'] = positive(rule.pop('band_size_cells'), 'band size cells')*pitch
            if behavior == 'ballistic':
                require(source['kind'] == 'members', 'ballistic source requires explicit members')
                for output, field in [('velocities', 'velocity'), ('phases', 'phase'), ('lifetimes', 'lifetime')]:
                    rule[output] = [copy.deepcopy(member.get(field)) for member in source['members']]
                if rule.pop('quantize_positions', False): rule['quantize'] = {'pitch': pitch, 'origin': origin}
            pool[behavior] = rule
        pools.append(pool)
    animation = {key: copy.deepcopy(clip.get(key)) for key in ('duration', 'loop', 'update_hz', 'seed', 'bounds')}
    animation.update(source_id=master['id'], master_hash=core.digest(master), clip_hash=core.digest(clip), pools=pools)
    validate_animation(animation, max_instances=max_instances)
    steps = round(animation['duration']*animation['update_hz'])
    if steps*sum(len(p['positions']) for p in pools) > 2_000_000:
        raise core.BudgetExceeded('sampled motion verification budget exceeded')
    for frame in range(steps + (0 if animation['loop'] else 1)):
        state = evaluate(animation, frame/animation['update_hz'])
        for pool, values in zip(pools, state['pools']):
            for position in values['positions']:
                for axis in range(3):
                    require(animation['bounds']['min'][axis]-1e-7 <= position[axis]-pool['cell_size']/2 and
                            position[axis]+pool['cell_size']/2 <= animation['bounds']['max'][axis]+1e-7,
                            'animated cell exceeds authored visual bounds')
    static_source = static_layer(master, exclusions)
    static = coordinate_planes.compile_master(static_source, {'pitch': pitch}, max_candidate_cells=max_candidates)
    restored_count = len(static['cells'])
    static['cells'] = [row for row in static['cells'] if tuple(row[:3]) not in static_occluders]
    removed_static_count = restored_count-len(static['cells'])
    static['payload_hash'] = core.digest(static['cells'])
    require(bool(static['cells']), 'static layer vanished')
    render = make_render_data(static)
    geometry = [{'id': p['id'], 'positions': p['positions'], 'cell_size': p['cell_size']} for p in pools]
    render.update(source_id=master['id'], source_revision=master['revision'], master_hash=core.digest(master),
                  payload_hash=core.digest({'static': static['payload_hash'], 'pools': geometry}),
                  cell_animation=animation, bounds=copy.deepcopy(animation['bounds']))
    render['provenance'].update(builder_version=VERSION, builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_compiled_payload_hash=compiled['payload_hash'], static_layer_master_hash=static['master_hash'],
        static_layer_payload_hash=static['payload_hash'], original_constraint_count=len(compiled['constraints']),
        original_constraints_all_passed=True, full_structure_rechecked_on_subset=False,
        clip_hash=core.digest(clip), static_cells_before_occlusion=restored_count,
        static_cells_occluded_by_fixed_pools=removed_static_count, coordinate_plane_preprocessor_sha256=static['preprocessor']['source_hash'])
    render['geometry'] = 'Static paints excluded before sampling; immutable fixed cell pools and direct analytic time functions. No fluid or physics simulation.'
    return render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('master', type=Path)
    parser.add_argument('--compiled', type=Path, required=True)
    parser.add_argument('--clip', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--oracle', type=Path)
    args = parser.parse_args()
    result = make_render(json.loads(args.master.read_text()), json.loads(args.compiled.read_text()), json.loads(args.clip.read_text()))
    args.output.parent.mkdir(exist_ok=True, parents=True)
    with args.output.open('x') as file: json.dump(result, file, sort_keys=True, separators=(',', ':')); file.write('\n')
    if args.oracle:
        animation = result['cell_animation']
        oracle = {'clip_hash': animation['clip_hash'], 'purpose': 'Optional test oracle only; runtime does not read it',
                  'states': [evaluate(animation, i/animation['update_hz']) for i in range(round(animation['duration']*animation['update_hz']))]}
        with args.oracle.open('x') as file: json.dump(oracle, file, sort_keys=True, separators=(',', ':')); file.write('\n')
    print(json.dumps({'output': str(args.output), 'pitch': result['pitch'], 'static_cells': result['cell_count'],
                      'pool_counts': {p['id']: len(p['positions']) for p in result['cell_animation']['pools']},
                      'payload_hash': result['payload_hash'], 'clip_hash': result['cell_animation']['clip_hash']}))


if __name__ == '__main__':
    main()
