"""Reversible native drawbridge candidate; frozen fixed-bridge inputs are read only.
All geometry uses the existing common Source/compiler contract. Metric choices
are functional design inferences, not an inverse survey or structural approval.
"""
from __future__ import annotations
import copy, hashlib, itertools, json, math
from pathlib import Path
from voxel_character.common import core
from world_city.runtime_city.parts.author import Source, extrusion
from world_city.concept_city_v3.registered_topography import author as terrain
from ..compile_bridge import deck_y
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[5]
SHIP = ROOT / 'world_city/concept_city_v3/assemblies/landmarks/registered/port_r03_quay_unions/navigation_ship_contract.json'
PITCH = 0.25

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def ref(p):
    return {'path': str(p.relative_to(ROOT)), 'sha256': sha(p)}

def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, sort_keys=True) + '\n')

def load(p):
    return json.loads(p.read_text())

def rigid(basis=None, translation=None):
    return {'basis': basis or [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 'translation': translation or [0, 0, 0]}

def corners(b):
    return list(itertools.product(*zip(b['min'], b['max'])))

def aabb(points):
    return {'min': [min((p[i] for p in points)) for i in range(3)], 'max': [max((p[i] for p in points)) for i in range(3)]}

def boxpoly(x0, x1, z0, z1, frame):
    return [[q[0], q[2]] for q in (core.apply(frame, [x, 0, z]) for x, z in [(x0, z0), (x1, z0), (x1, z1), (x0, z1)])]

def source_finish(s):
    m = s.finish()
    m['provenance'].update(author=ref(Path(__file__)), fixed_bridge=ref(BASE / 'resolved_placements.json'))
    m['extensions'].update(candidate_only=True, scale_policy='native_dimensions_and_rigid_transforms_only')
    return m

def leaf_transform(side, angle):
    """side -1 is north/negative bridge X; leaf native X points inward."""
    t = math.radians(angle)
    c, s = (math.cos(t), math.sin(t))
    direction = -side
    return rigid([[direction * c, -direction * s, 0], [s, c, 0], [0, 0, direction]], [side * 7 - direction * 0.25 * s, 3.75 + 0.25 * c, 0])

def barrier_transform(side, lateral, angle, floor):
    t = math.radians(angle)
    c, s = (math.cos(t), math.sin(t))
    d = -lateral
    return rigid([[0, 0, -d], [s, c, 0], [d * c, -d * s, 0]], [side * 13, floor + 0.5, lateral * 5.75])

def leaf_chain(side, lateral, angle):
    tr = leaf_transform(side, angle)
    tip = core.apply(tr, [6.5, 0.25, lateral * 6.55])
    pulley = [side * 8.5, 13.5, -side * lateral * 8.0]
    return (tip, pulley)

def plate_transform(side, progress):
    lift = min(1.0, progress * 2) * 1.75
    slide = max(0.0, progress * 2 - 1) * 2.5
    d = -side
    return rigid([[d, 0, 0], [0, 1, 0], [0, 0, d]], [side * (7 + slide), 4 + lift, 0])

def state(angle, barrier_angle, overlay, plate_progress=None):
    items = []
    chains = []
    if plate_progress is None:
        plate_progress = 1.0 if angle > 0 else 0.0
    for side in (-1, 1):
        items.append({'id': f'HINGE_PLATE_{side}', 'asset_key': 'sliding_hinge_cover', 'transform_bridge_local': plate_transform(side, plate_progress), 'collision': 'kinematic_exact_common_mesh'})
        tr = leaf_transform(side, angle)
        items.append({'id': f'LEAF_{side}', 'asset_key': 'timber_lift_leaf_7x14', 'transform_bridge_local': tr, 'collision': 'kinematic_exact_common_mesh'})
        for lateral in (-1, 1):
            tip, pulley = leaf_chain(side, lateral, angle)
            closed_tip, _ = leaf_chain(side, lateral, 0)
            drop = math.dist(closed_tip, pulley) - math.dist(tip, pulley)
            weight = [pulley[0] + side * 2, 10.5 - drop, pulley[2]]
            rear_pulley = [weight[0], pulley[1], pulley[2]]
            items.append({'id': f'WEIGHT_{side}_{lateral}', 'asset_key': 'guided_stone_counterweight', 'transform_bridge_local': rigid(translation=weight), 'collision': 'kinematic_exact_common_mesh'})
            chains.extend([{'id': f'LIFT_CHAIN_{side}_{lateral}', 'polyline_bridge_xyz_m': [tip, pulley], 'native_link_key': 'iron_chain_link', 'link_spacing_m': 0.5, 'collision': 'visual_only_with_reserved_swept_corridor'}, {'id': f'WEIGHT_CHAIN_{side}_{lateral}', 'polyline_bridge_xyz_m': [pulley, rear_pulley, [weight[0], weight[1] + 0.75, weight[2]]], 'native_link_key': 'iron_chain_link', 'link_spacing_m': 0.5, 'collision': 'visual_only_with_reserved_swept_corridor'}])
        q = core.apply(overlay['bridge_to_world'], [side * 13, 0, 0])
        floor = round(deck_y(overlay, q[0], q[2]) / 0.25) * 0.25
        for lateral in (-1, 1):
            items.append({'id': f'BARRIER_{side}_{lateral}', 'asset_key': 'timber_road_barrier_half', 'transform_bridge_local': barrier_transform(side, lateral, barrier_angle, floor), 'collision': 'kinematic_exact_common_mesh'})
    return {'leaf_angle_degrees': angle, 'barrier_angle_degrees': barrier_angle, 'hinge_plate_progress': plate_progress, 'movable_placements': items, 'chains': chains}

def interval_sweep(side, a, b, bounds):
    """Analytical enclosure of every native box corner over a closed angle interval.
 Each coordinate is A*cos(theta)+B*sin(theta)+C; include all interior extrema.
 """
    angles = [math.radians(a), math.radians(b)]
    values = []
    d = -side
    for x, y, z in corners(bounds):
        y += 0.25
        candidates = list(angles)
        for A, B in [(d * x, -d * y), (y, x)]:
            t = math.atan2(B, A)
            for k in range(-2, 3):
                v = t + k * math.pi
                if angles[0] <= v <= angles[1]:
                    candidates.append(v)
        for t in candidates:
            values.append([side * 7 + d * (x * math.cos(t) - y * math.sin(t)), 3.75 + x * math.sin(t) + y * math.cos(t), d * z])
    return {'interval_degrees': [a, b], 'bounds_bridge_local_m': aabb(values), 'method': 'Exact trigonometric extrema of every full-envelope corner; conservative for every point in the box, not endpoint sampling.'}

def make_leaf():
    s = Source('timber_lift_leaf_7x14', [0, -0.75, -7], [7, 1.25, 7])
    s.box('continuous_wearing_deck', [0, -0.25, -7], [7, 0, 7], 'timber', component='deck')
    for i in range(14):
        s.box(f'plank_{i}', [i * 0.5, -0.08, -6.75], [(i + 1) * 0.5 - 0.025, 0, 6.75], 'timber_light' if i % 3 else 'timber_dark', component='deck')
    for z in (-5.5, -2.75, 0, 2.75, 5.5):
        s.box('longitudinal_' + str(z), [0, -0.75, z - 0.25], [6.5, -0.25, z + 0.25], 'timber_dark', component='frame')
    for x in (0.25, 2.25, 4.5, 6.25):
        s.box('cross_' + str(x), [x - 0.25, -0.6, -7], [x + 0.25, -0.25, 7], 'timber_dark', component='frame')
    for z in (-6.75, 6.75):
        s.box('rail_' + str(z), [0.5, 1, -7 if z < 0 else 6.5], [7, 1.25, -6.5 if z < 0 else 7], 'timber_dark', component='rails')
        for x in (0.75, 2.5, 4.5, 6.75):
            s.box('post_' + str(z) + '_' + str(x), [x - 0.125, -0.25, z - 0.125], [x + 0.125, 1.25, z + 0.125], 'timber', component='rails')
    s.box('recess_for_flush_hinge_cover', [0, -0.25, -7], [0.5, 0.01, 7], component='deck', action='cut')
    s.box('hinge_axle', [0, -0.45, -7], [0.5, -0.2, 7], 'iron', component='hinges')
    s.hook('native_hinge', 'deck', 'solid', [0, -0.25, 0], [0, 0, 1], 'rotate_up_degrees', [0, 90])
    return source_finish(s)

def make_plate():
    s = Source('sliding_hinge_cover', [-1.75, -0.25, -7], [0.5, 1.25, 7])
    s.box('flush_cover', [-1.75, -0.25, -7], [0.5, 0, 7], 'timber_light')
    for side in (-1, 1):
        za, zb = sorted([side * 6.5, side * 7])
        s.box('cover_rail_' + str(side), [-1.75, 1, za], [0.5, 1.25, zb], 'timber_dark')
        for x in (-1.625, 0.375):
            s.box('cover_post_' + str(side) + '_' + str(x), [x - 0.125, 0, za], [x + 0.125, 1.25, zb], 'timber')
    return source_finish(s)

def make_barrier():
    s = Source('timber_road_barrier_half', [0, -0.5, -0.125], [5.5, 0.5, 0.125])
    for y in (-0.375, 0.375):
        s.box('rail_' + str(y), [0, y - 0.125, -0.125], [5.5, y + 0.125, 0.125], 'timber_dark')
    for n in range(8):
        x = min(5.375, n * 0.765625)
        s.box('picket_' + str(n), [max(0, x - 0.125), -0.5, -0.125], [min(5.5, x + 0.125), 0.5, 0.125], 'timber_light')
    return source_finish(s)

def make_weight():
    s = Source('guided_stone_counterweight', [-0.6, -0.75, -0.6], [0.6, 0.75, 0.6])
    s.box('stone_weight', [-0.6, -0.75, -0.6], [0.6, 0.75, 0.6], 'stone_dark')
    s.box('iron_band', [-0.65, -0.1, -0.65], [0.65, 0.1, 0.65], 'iron')
    return source_finish(s)

def make_link():
    s = Source('iron_chain_link', [-0.1875, 0, -0.125], [0.1875, 0.75, 0.125])
    s.box('link', [-0.1875, 0, -0.125], [0.1875, 0.75, 0.125], 'iron')
    s.box('link_hole', [-0.0625, 0.125, -0.25], [0.0625, 0.625, 0.25], action='cut')
    return source_finish(s)

def make_fixed(overlay):
    m = copy.deepcopy(load(BASE / 'assembly_source.json'))
    m['id'] = 'registered_drawbridge_stone_approaches'
    m['revision'] = 1
    m['constraints'] = [c for c in m['constraints'] if c['kind'] != 'connected' and c['id'] not in ('central_navigation_clearance_3m', 'ARCH_BAY_04_real_barrel_void', 'ARCH_BAY_04_central_cart_headroom')]
    m['assembly_cuts'].extend([{'id': 'remove_central_arch_and_fixed_deck', 'action': 'cut', 'selector': {}, 'shape': {'kind': 'box', 'min': [-7, -8, -7.5], 'max': [7, 6, 7.5]}}, {'id': 'clear_leaf_rail_heel_sweep', 'action': 'cut', 'selector': {}, 'shape': {'kind': 'box', 'min': [-9.25, 4, -7.5], 'max': [9.25, 6, 7.5]}}])
    m['constraints'].append({'id': 'full_central_navigation_slot', 'kind': 'empty_region', 'selector': {}, 'shape': {'kind': 'box', 'min': [-6.99, -10, -8.5], 'max': [6.99, 25, 8.5]}})
    add = Source('drawbridge_fixed_hinge_piers', [-10, -6, -8.75], [10, 13.75, 8.75])
    supports = []
    for side in (-1, 1):
        xs = sorted([side * 7, side * 8.5])
        points = [core.apply(overlay['bridge_to_world'], [x, 0, z]) for x in xs for z in (-7, 0, 7)]
        bottom = min((terrain.height_at(p[0], p[2]) for p in points)) - 0.6
        add.box(f'hinge_pier_{side}', [xs[0], bottom, -7], [xs[1], 3.25, 7], 'stone_dark', component='hinge_piers')
        add.box(f'hinge_bearing_{side}', [xs[0], 3.25, -7], [xs[1], 4, 7], 'stone', component='hinge_piers')
        supports.append({'side': side, 'polygon_xz_m': boxpoly(xs[0], xs[1], -7, 7, overlay['bridge_to_world']), 'foundation_y_m': bottom, 'bed_samples': [{'xz_m': [p[0], p[2]], 'bed_y_m': terrain.height_at(p[0], p[2]), 'embed_m': terrain.height_at(p[0], p[2]) - bottom} for p in points]})
        xx = side * 10
        q = core.apply(overlay['bridge_to_world'], [xx, 0, 0])
        edge = deck_y(overlay, q[0], q[2])
        xxs = sorted([(xx, edge), (side * 7, 4)])
        add.op(f'hinge_cap_transition_{side}', extrusion([[xxs[0][0], 3.1], [xxs[1][0], 3.1], [xxs[1][0], xxs[1][1]], [xxs[0][0], xxs[0][1]]], -7, 7), 'stone', component='hinge_caps')
        for lateral in (-1, 1):
            z = lateral * 8.0
            x = side * 8.5
            p = core.apply(overlay['bridge_to_world'], [x, 0, z])
            bottom = terrain.height_at(p[0], p[2]) - 0.6
            add.box(f'gantry_stone_foot_{side}_{lateral}', [x - 0.75, bottom, z - 0.75], [x + 0.75, 4, z + 0.75], 'stone_dark', component='gantry_feet')
            add.box(f'gantry_post_{side}_{lateral}', [x - 0.35, 3.5, z - 0.35], [x + 0.35, 13.75, z + 0.35], 'timber_dark', component='gantry')
            for dx in (-0.9, 0.9):
                wx = x + side * 2 + dx
                add.box(f'weight_guide_{side}_{lateral}_{dx}', [wx - 0.1, bottom, z - 0.9], [wx + 0.1, 12, z + 0.9], 'timber_dark', component='gantry')
            add.box(f'weight_head_{side}_{lateral}', [min(x, x + side * 3) - 0.4, 13.25, z - 0.4], [max(x, x + side * 3) + 0.4, 13.75, z + 0.4], 'timber_dark', component='gantry')
            add.beam(f'brace_{side}_{lateral}', [x, 9, z], [x + side * 2, 13.25, z], 0.24, 'timber_dark', component='gantry')
        add.box(f'portal_head_{side}', [side * 8.5 - 0.4, 13.25, -8.5], [side * 8.5 + 0.4, 13.75, 8.5], 'timber_dark', component='gantry')
        for lateral in (-1, 1):
            za, zb = sorted([lateral * 5.5, lateral * 7])
            xx = side * 13.75
            add.box(f'barrier_outer_stub_{side}_{lateral}', [xx - 0.25, 3.75, za], [xx + 0.25, 5.25, zb], 'timber_dark', component='barrier_posts')
        for z in (-9.5, 9.5):
            add.box(f'winch_drum_{side}_{z}', [side * 9.5 - 0.5, 4.5, z - 0.55], [side * 9.5 + 0.5, 5.5, z + 0.55], 'timber', component='winches')
    n = add.finish()
    m['components'] += n['components']
    m['instances'] += n['instances']
    original_ids = {i['id'] for i in load(BASE / 'assembly_source.json')['instances']}
    newcuts = []
    for cut in m['assembly_cuts']:
        if cut['id'] in ('remove_central_arch_and_fixed_deck', 'clear_leaf_rail_heel_sweep'):
            newcuts.append({**copy.deepcopy(cut), 'selector': {'instance': sorted(original_ids)}})
        else:
            newcuts.append(cut)
    m['assembly_cuts'] = newcuts
    for side in (-1, 1):
        xs = sorted([side * 8.75, side * 7])
        m['assembly_cuts'].append({'id': 'hinge_cover_recess_' + str(side), 'action': 'cut', 'selector': {}, 'shape': {'kind': 'box', 'min': [xs[0], 3.75, -7], 'max': [xs[1], 4.01, 7]}})
    m['provenance'].update(drawbridge_author=ref(Path(__file__)), unchanged_fixed_bridge=ref(BASE / 'assembly_source.json'), change='Derived central 14 m opening; original nine-arch asset stays immutable. Eight side arches plus two strengthened hinge piers, native timber gantries and short hinge caps.')
    m['extensions']['hinge_supports'] = supports
    return m

def preflight(master, pitch):

    def count(shape, t):
        lo, hi = core.shape_bounds(core.prepare_shape(shape, pitch))
        bb = aabb([core.apply(t, p) for p in itertools.product(*zip(lo, hi))])
        return math.prod((math.ceil(b / pitch - core.EPS) - math.floor(a / pitch + core.EPS) for a, b in zip(bb['min'], bb['max'])))
    comps = {c['id']: c for c in master['components']}
    n = 0
    for inst in master['instances']:
        tr = core.transform(inst.get('transform'))
        for op in comps[inst['component']]['operations']:
            n += count(op['shape'], core.compose(tr, core.transform(op.get('transform'))))
    for cut in master.get('assembly_cuts', []):
        n += count(cut['shape'], core.transform(cut.get('transform')))
    for con in master['constraints']:
        if con['kind'] == 'empty_region':
            n += count(con['shape'], core.transform(con.get('transform')))
    return n

def build():
    fixed_inputs = {p.name: ref(p) for p in [BASE / 'resolved_placements.json', BASE / 'assembly_source.json', BASE / 'continuous_deck_overlay.json']}
    overlay = load(BASE / 'continuous_deck_overlay.json')
    ships = load(SHIP)
    masters = {'stone_approaches': make_fixed(overlay), 'timber_lift_leaf_7x14': make_leaf(), 'sliding_hinge_cover': make_plate(), 'timber_road_barrier_half': make_barrier(), 'guided_stone_counterweight': make_weight(), 'iron_chain_link': make_link()}
    budget = []
    for key, m in masters.items():
        pitch = 0.125 if key == 'iron_chain_link' else 0.25
        core.validate_master(m, pitch)
        path = HERE / 'masters' / f'{key}.json'
        write(path, m)
        budget.append({'asset_key': key, 'master': ref(path), 'pitch_m': pitch, 'candidate_cells': preflight(m, pitch)})
    vessel = []
    for v in ships['vessels']:
        b = {'min': [min(v['continuous_conservative_bounds_m']['min'][i], v['sampled_cache_bounds_m']['min'][i]) for i in range(3)], 'max': [max(v['continuous_conservative_bounds_m']['max'][i], v['sampled_cache_bounds_m']['max'][i]) for i in range(3)]}
        offset = -(b['min'][0] + b['max'][0]) / 2
        vessel.append({'asset_key': v['asset_key'], 'source': v['source'], 'cache': v['cache'], 'union_source_cache_bounds_local_m': b, 'route_origin_bridge_x_m': offset, 'travel_bridge_z_m': [-40, 40], 'vertical_origin': 'normal river water at vessel origin; vessel remains level, no flood/wave/roll allowance', 'minimum_design_lateral_margin_m': (12.5 - (b['max'][0] - b['min'][0])) / 2, 'full_rig_included': True})
    named = {}
    for ident, angle, barrier, road, nav in [('ROAD_OPEN', 0, 90, True, False), ('ROAD_SECURED', 0, 0, False, False), ('LIFT_READY', 0, 0, False, False), ('LIFTING_MIDPOINT', 45, 0, False, False), ('NAVIGATION_OPEN', 90, 0, False, True), ('LOWERING_MIDPOINT', 45, 0, False, False)]:
        named[ident] = {**state(angle, barrier, overlay, 1.0 if ident == 'LIFT_READY' else None), 'road_enabled': road, 'navigation_enabled': nav}
    sweep = []
    for side in (-1, 1):
        for a in range(90):
            sweep.append({'id': f'LEAF_{side}:SWEEP:{a:02}', **interval_sweep(side, a, a + 1, {'min': [0, -0.75, -7], 'max': [7, 1.25, 7]})})
    waiting = []
    for side in (-1, 1):
        xa, xb = sorted([side * 16, side * 31])
        waiting.append({'id': f'CART_WAIT_{side}', 'role': 'stopped_cart_queue', 'polygon_xz_m': boxpoly(xa, xb, -3.5, 3.5, overlay['bridge_to_world']), 'owned_by': 'retained_fixed_stone_deck', 'must_remain_clear_when_road_open': True})
        xa, xb = sorted([side * 16, side * 26])
        for lateral in (-1, 1):
            za, zb = sorted([lateral * 4.2, lateral * 6.3])
            waiting.append({'id': f'PEDESTRIAN_WAIT_{side}_{lateral}', 'role': 'pedestrian_waiting_pocket', 'polygon_xz_m': boxpoly(xa, xb, za, zb, overlay['bridge_to_world']), 'owned_by': 'retained_fixed_stone_deck'})
    ownership = {'moving_deck_polygon_xz_m': boxpoly(-7, 7, -7, 7, overlay['bridge_to_world']), 'short_hinge_transition_polygons_xz_m': [boxpoly(-10, -7, -7, 7, overlay['bridge_to_world']), boxpoly(7, 10, -7, 7, overlay['bridge_to_world'])], 'closed_floor_y_m': 4.0, 'height_rule': 'Local |X|<=7:4m; 7<|X|<10: linear from4m to unchanged fixed deck at corresponding ±10m; otherwise unchanged fixed overlay. Only applies inside 14m central deck width.', 'water_and_bed': 'Retained underneath; moving deck is disabled for traversal in all nonclosed states. No terrain surface may bridge the central slot.', 'hinge_floor_source_delta_m': max((4 - deck_y(overlay, *[core.apply(overlay['bridge_to_world'], [x, 0, 0])[i] for i in (0, 2)]) for x in (-7, 7)))}
    candidate = {'schema': 'riverstone.registered_drawbridge_candidate.v1', 'status': 'source_dimensions_and_states_pending_native_compile', 'fixed_bridge_inputs': fixed_inputs, 'vessel_contract': ref(SHIP), 'bridge_to_world': overlay['bridge_to_world'], 'world_to_bridge': overlay['world_to_bridge'], 'design': {'central_clear_masonry_span_m': 14, 'leaf_length_m': 7, 'leaf_total_width_m': 14, 'leaf_native_frame_depth_m': 0.75, 'hinge_axis_below_finished_road_m': 0.25, 'hinge_cover_dimensions_m': [2.25, 0.25, 14], 'hinge_cover_lift_m': 1.75, 'hinge_cover_retract_m': 2.5, 'closed_cart_lane_m': 8, 'closed_sidewalk_each_m': 2.4, 'closed_rail_each_m': 0.6, 'barrier_station_minimum_open_cart_and_walk_width_m': 10.5, 'barrier_closed_center_gap_m': 0.5, 'barrier_pedestrian_control_basis': '0.4m-radius adult capsule cannot pass centre or outer gaps; open barrier station retains8m cart band and1.25m walks each.', 'fully_open_angle_degrees': 90, 'fully_open_minimum_clear_rig_width_m': 12.5, 'gantry_head_y_m': 13.75, 'counterweight_rule': 'Rear guided stone weight descends by exactly the reduction in front chain length. No mass/balance/load certification.', 'source_basis': 'Publication note: project design decision; conversational attribution omitted.'}, 'navigation_vessels': vessel, 'states': named, 'transition_contract': {'sequence': ['ROAD_OPEN', 'CLOSE_BARRIERS', 'ROAD_SECURED', 'RAISE_AND_RETRACT_HINGE_COVERS', 'LIFT_READY', 'LIFTING', 'NAVIGATION_OPEN', 'LOWERING', 'EXTEND_AND_SEAT_HINGE_COVERS', 'ROAD_SECURED', 'OPEN_BARRIERS', 'ROAD_OPEN'], 'barrier_seconds': 3, 'hinge_cover_seconds': 5, 'leaf_seconds': 12, 'smooth_parameter': '3t²−2t³ over each stage', 'preconditions': ['Operator requests passage.', 'Road and both leaf/waiting exclusion boxes confirmed empty before lift.', 'Both barriers latched before leaf moves.', 'Both leaves at90 degrees and locked before vessel release.', 'Full vessel envelope has exited navigation hold zone before lowering.', 'Both leaves seated and locked before reopening road.'], 'interlocks': 'Road and navigation cannot be enabled simultaneously; any transition or fault closes both.', 'automation_claim': 'Bounded kinematic state contract only; real occupancy sensing and load physics are not implemented.'}, 'leaf_swept_volumes': sweep, 'waiting_regions': waiting, 'navigation_hold_regions': [{'id': f'NAV_WAIT_{side}', 'polygon_xz_m': boxpoly(-6.25, 6.25, side * 32 - 14, side * 32 + 14, overlay['bridge_to_world'])} for side in (-1, 1)], 'surface_ownership': ownership, 'compile_budget': budget, 'limits': ['Normal water only; no flood, wave, wake, drift, collision-response or structural certification.', 'Full rig is included, without furling or lowering the mast.', 'The 0.75m worst-vessel side margin is geometric only.', 'Fixed nine-arch candidate and BLOCK_013 density pack remain unchanged.', 'The inherited port junction retains its explicit15% local service-ramp criterion.']}
    write(HERE / 'candidate.json', candidate)
    write(HERE / 'compile_preflight.json', {'assets': budget, 'candidate_cells_total': sum((q['candidate_cells'] for q in budget)), 'maximum_single_asset_cells': max((q['candidate_cells'] for q in budget)), 'static_memory_estimate_mib': [320, 650], 'runtime_target_seconds': 120, 'new_masters': 6, 'native_compile_only': True})
    print(json.dumps({'candidate': ref(HERE / 'candidate.json'), 'budget': load(HERE / 'compile_preflight.json'), 'vessel_clearances': [{k: v[k] for k in ('asset_key', 'route_origin_bridge_x_m', 'minimum_design_lateral_margin_m')} for v in vessel]}, indent=2))
if __name__ == '__main__':
    build()
