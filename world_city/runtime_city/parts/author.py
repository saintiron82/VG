"""Staged civic/harbor part sources, using the unchanged common master contract.

No city placement, terrain changes, sampler, mesher, engine or runtime animation.
All dimensions are fictional design inferences, not historical measurements.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
HOUSE = 'voxel_character/common/assets/house/master.json'
FOUNTAIN = 'voxel_character/common/assets/fountain/master.json'
HISTORY = 'world_city/runtime_city/revisions/r2/city_history.r2.candidate.json'
AUTHOR = 'world_city/runtime_city/parts/author.py'
KINDS = (
    'quay_retaining_segment', 'timber_harbor_crane', 'river_cargo_barge',
    'warehouse_hoist', 'cathedral_flying_buttress', 'pointed_arch_cloister_bay',
    'park_terrace_stair', 'retaining_wall_corner', 'park_bench',
    'stone_planter', 'cargo_crate', 'cargo_barrel',
)


def file_ref(path):
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def box(lo, hi):
    return {'kind': 'box', 'min': list(lo), 'max': list(hi)}


def extrusion(points, low, high):
    return {'kind': 'extrusion', 'polygon': [list(p) for p in points],
            'z_min': low, 'z_max': high}


def rect_footprint(bounds):
    a, b = bounds['min'], bounds['max']
    return [[a[0], a[2]], [b[0], a[2]], [b[0], b[2]], [a[0], b[2]]]


def approved_palette(roof_family='slate_gray'):
    house = json.loads((ROOT / HOUSE).read_text())['materials']
    roofs = json.loads((ROOT / HISTORY).read_text())['roof_material_families']
    result = {key: house[key] for key in (
        'stone', 'stone_light', 'stone_dark', 'mortar',
        'timber', 'timber_light', 'timber_dark', 'iron', 'iron_light')}
    result.update(roofs[roof_family])
    return result


class Source:
    def __init__(self, kind, lo, hi):
        self.kind = kind
        self.bounds = {'min': list(lo), 'max': list(hi)}
        self.components, self.constraints, self.sockets = {}, [], []
        self.supports, self.clearances, self.hooks, self.connections = [], [], [], []
        self.planes = []
        self.design = []
        self.smoke_pitch = .2
        self.lod = {
            'policy': 'Every pitch is compiled independently from this single continuous master.',
            'source_geometry_changes_by_lod': False,
            'output_cell_edits_allowed': False,
            'collision_changes_by_lod': False,
            'collision_status': 'not_integrated',
            'candidate_visual_pitches_m': [.1, .2, .4],
            'coarse_functional_guarantee': False,
            'thin_rope_policy': 'Existing common tube minimum_radius_cells=0.75 preserves crane/hoist visual lines; no physics shape or output cells are changed.',
            'coarse_action': 'Reject a functional use if sampled clearance or support checks fail.',
        }

    def op(self, name, shape, material='stone', component='body', part='solid',
           pivot=(0, 0, 0), transform=None, action='paint'):
        comp = self.components.setdefault(component, {'id': component, 'parts': [], 'operations': []})
        if not any(p['id'] == part for p in comp['parts']):
            comp['parts'].append({'id': part, 'pivot': list(pivot),
                                 'metadata': {'runtime_animation': 'not_integrated'}})
        item = {'id': name, 'part': part, 'action': action, 'shape': shape}
        if action == 'paint': item['material'] = material
        if transform: item['transform'] = transform
        comp['operations'].append(item)

    def box(self, name, lo, hi, material='stone', **kwargs):
        self.op(name, box(lo, hi), material, **kwargs)

    def beam(self, name, start, end, radius, material='timber', minimum_radius_cells=0, **kwargs):
        self.op(name, {'kind': 'tube', 'points': [start, end], 'radius': radius,
                       'minimum_radius_cells': minimum_radius_cells}, material, **kwargs)

    def plan(self, name, polygon, y0, y1, material='timber', **kwargs):
        self.op(name, extrusion([[x, -z] for x, z in polygon], y0, y1), material,
                transform={'basis': [[1, 0, 0], [0, 0, 1], [0, -1, 0]]}, **kwargs)

    def socket(self, name, position, role, normal=(0, 1, 0)):
        self.sockets.append({'id': name, 'position_m': list(position),
                             'outward_normal': list(normal), 'role': role,
                             'coordinate_space': 'asset_local_metres'})

    def support(self, name, lo, hi, target):
        self.supports.append({'id': name, 'contact_region_m': box(lo, hi),
                              'requires': target,
                              'status': 'geometric_interface_only_not_structural_engineering'})

    def clearance(self, name, lo, hi, purpose, assert_empty=True):
        self.clearances.append({'id': name, 'region_m': box(lo, hi), 'purpose': purpose,
                                'placement_must_reserve': True,
                                'source_empty_constraint': assert_empty})
        if assert_empty:
            self.constraints.append({'id': name, 'kind': 'empty_region', 'selector': {}, 'shape': box(lo, hi)})

    def hook(self, name, component, part, pivot, axis, action, limits):
        self.hooks.append({'id': name, 'component': component, 'part': part,
                           'pivot_local_m': list(pivot), 'axis_local': list(axis),
                           'action': action, 'limits': limits,
                           'status': 'socket_and_pivot_contract_only_no_runtime_track',
                           'physics_status': 'not_integrated'})

    def finish(self):
        self.constraints.insert(0, {'id': 'part_present', 'kind': 'nonempty', 'selector': {}})
        self.constraints.extend({'id': key + '_present', 'kind': 'nonempty',
                                 'selector': {'component': key}} for key in self.components)
        return {
            'schema': 'riverstone.voxel.master.v1', 'id': 'staged_' + self.kind,
            'revision': 1, 'axes': {'up': '+Y', 'front': '+Z', 'right': '+X'},
            'grid_origin': [0, 0, 0], 'materials': approved_palette(),
            'coordinate_planes': self.planes,
            'components': list(self.components.values()),
            'instances': [{'id': key, 'component': key} for key in self.components],
            'constraints': self.constraints,
            'provenance': {
                'author': file_ref(AUTHOR),
                'source_files': [file_ref(HOUSE), file_ref(FOUNTAIN), file_ref(HISTORY),
                                 file_ref('world_city/reference/revision_02/city_terrain_concept.png'),
                                 file_ref('world_city/reference/revision_02/prompt.txt')],
                'observed': 'Existing common schema, palette roles, landmark/infrastructure/topography source interfaces.',
                'inferred': 'All new part geometry, dimensions, sockets, support zones and mechanical proportions.',
                'image_basis': 'Revision 02 whole-city concept inspected for facility families only; exact part dimensions are source/design inferences, not measured from pixels.',
                'evidence': 'fictional_game_design_inference_not_historical_reconstruction',
                'material_policy': 'Original house warm stone/timber roles; canonical r2 gray slate for roof roles. Old masters remain unchanged.',
                'new_engine': False,
            },
            'extensions': {
                'part_kind': self.kind, 'status': 'staged_prototype_needs_art_review',
                'local_bounds_m': self.bounds,
                'footprint_xz_m': rect_footprint(self.bounds),
                'sockets': self.sockets, 'supports': self.supports,
                'clearances': self.clearances, 'functional_connections': self.connections,
                'animation_hooks': self.hooks, 'lod': self.lod,
                'smoke_pitch_m': self.smoke_pitch,
                'design_notes': self.design,
                'city_placement': None, 'terrain_placement': None,
                'visual_review': 'not_run', 'whole_city_complete': False,
                'release_gate': 'New concept review, material/silhouette review, placement/support checks, traversal and runtime integration remain open.',
            },
        }


def make_master(kind):
    if kind not in KINDS: raise ValueError('Unknown staged part kind: ' + str(kind))
    if kind == 'quay_retaining_segment':
        a = Source(kind, [-2, -3, -.8], [2, .5, .8])
        a.planes = [{'id': 'quay_walk', 'axis': 1, 'value': 0, 'snap': 'none'},
                    {'id': 'cap_base', 'relative_to': 'quay_walk', 'offset': -.3}]
        a.box('retaining_mass', [-2, -3, -.7], [2, -.3, .7])
        a.box('flush_coping', [-2, {'plane': 'cap_base'}, -.8], [2, {'plane': 'quay_walk'}, .8], 'stone_light')
        for x in (-1.4, 1.4):
            a.box('mooring_post_' + str(x), [x-.15, 0, -.35], [x+.15, .5, -.05], 'timber_dark', component='mooring')
            a.socket('mooring_' + str(x), [x, .4, -.2], 'rope_attach')
        a.socket('join_left', [-2, 0, 0], 'quay_repeat', (-1, 0, 0))
        a.socket('join_right', [2, 0, 0], 'quay_repeat', (1, 0, 0))
        a.socket('land_edge', [0, 0, -.8], 'join_walk_surface', (0, 0, -1))
        a.socket('water_edge', [0, 0, .8], 'quay_face', (0, 0, 1))
        a.support('quay_foundation', [-2, -3, -.7], [2, -2.9, .7], 'Bearing ground below design bed; retaining soil remains an external dependency.')
        a.clearance('walking_strip', [-2, .01, .0], [2, 2.3, .65], 'Pedestrian strip on top; connect to wider land-side route.')
        a.clearance('berth_water_reservation', [-2, -2, .81], [2, 3, 4.5], 'Barge approach and water space.')
        a.design += ['Local top is Y=0. No global river elevation is assumed.', 'Quay stability, bed level, flood level and guard provision require placement review.']
    elif kind == 'timber_harbor_crane':
        a = Source(kind, [-1.3, -.3, -1.3], [1.3, 4.1, 3.0])
        a.box('stone_pad', [-1.2, -.3, -1.2], [1.2, 0, 1.2], 'stone_dark', component='base')
        for x in (-.85, .85):
            a.box('foot_' + str(x), [x-.15, 0, -1.1], [x+.15, .35, 1.1], 'timber_dark', component='base')
        a.box('kingpost', [-.22, 0, -.22], [.22, 3.9, .22], 'timber', component='slew_frame', part='frame')
        a.beam('jib', [0, 3.65, -.6], [0, 3.65, 2.75], .2, component='slew_frame', part='frame')
        a.beam('jib_brace', [0, 1.4, 0], [0, 3.65, 2.45], .16, 'timber_dark', component='slew_frame', part='frame')
        a.beam('rear_brace', [0, .3, -1], [0, 2, 0], .16, component='base')
        a.box('winch', [-.55, .85, -.65], [.55, 1.3, -.25], 'timber_dark', component='winch', part='drum', pivot=(0, 1.05, -.45))
        a.beam('hoist_rope', [0, 1.25, 2.65], [0, 3.65, 2.65], .11, 'timber_light', minimum_radius_cells=.75, component='hoist', part='rope', pivot=(0, 3.65, 2.65))
        a.box('load_hook', [-.15, 1.05, 2.5], [.15, 1.35, 2.8], 'iron', component='hook', part='hook', pivot=(0, 1.2, 2.65))
        a.socket('ground', [0, -.3, 0], 'quay_support')
        a.socket('load', [0, 1.05, 2.65], 'cargo_lift')
        a.support('crane_bearing', [-1.2, -.3, -1.2], [1.2, -.2, 1.2], 'Load-bearing quay foundation, not an unsupported timber deck.')
        a.clearance('operator_area', [.6, 0, -1.0], [1.8, 2.3, .3], 'Winch operator working zone; reserve from other city parts.', False)
        a.clearance('slew_envelope', [-3.1, .4, -3.1], [3.1, 4.2, 3.1], 'Reserve sweep and suspended-load area; not a pedestrian route.', False)
        a.hook('slew', 'slew_frame', 'frame', [0, 0, 0], [0, 1, 0], 'rotation_degrees', [-60, 60])
        a.hook('drum', 'winch', 'drum', [0, 1.05, -.45], [1, 0, 0], 'rotation_degrees', [0, 360])
        a.hook('lift', 'hook', 'hook', [0, 1.2, 2.65], [0, 1, 0], 'translation_metres', [0, 1.8])
        a.connections += [{'id': 'lift_system', 'parts': ['slew_frame.frame', 'winch.drum', 'hoist.rope', 'hook.hook'], 'status': 'Rigid movement/rope-length synchronization must be implemented together; static render only.'}]
        a.design += ['Hand-winch harbor crane prototype. Not a reconstructed treadwheel crane.', 'Rope is a timber-light palette role for this staged preview; rope material art review remains.']
    elif kind == 'river_cargo_barge':
        a = Source(kind, [-1.6, -.65, -4], [1.6, .8, 4])
        outer = [[-1.6,-2.6],[-.8,-4],[.8,-4],[1.6,-2.6],[1.6,2.6],[.8,4],[-.8,4],[-1.6,2.6]]
        inner = [[x*.82,z*.90] for x,z in outer]
        a.plan('hull_bottom', outer, -.65, -.4, 'timber_dark', component='hull')
        for i in range(8):
            j=(i+1)%8
            a.plan('hull_side_' + str(i), [outer[i], outer[j], inner[j], inner[i]], -.4, .6, 'timber', component='hull')
        for z in (-3.2, 3.2):
            a.box('end_deck_' + str(z), [-.7, .25, z-.35], [.7, .5, z+.35], 'timber_light', component='decks')
            a.box('bollard_' + str(z), [-.15, .5, z-.15], [.15, .8, z+.15], 'timber_dark', component='decks')
            a.socket('mooring_' + str(z), [0, .7, z], 'mooring_rope')
        a.socket('waterline', [0, 0, 0], 'align_to_local_water_surface')
        a.socket('cargo', [0, -.4, 0], 'hold_floor')
        a.support('buoyancy_reference', [-1.4, -.65, -3.5], [1.4, 0, 3.5], 'Water support/float solver; dry-dock use needs external cradle.')
        a.clearance('cargo_hold', [-1.1, -.39, -2.4], [1.1, 1.8, 2.4], 'Open hold for cargo/lift; intentionally empty source.')
        a.clearance('berth', [-2.1, -.9, -4.5], [2.1, 2.2, 4.5], 'Berth and motion reservation around hull.', False)
        a.hook('floating_body', 'hull', 'solid', [0, 0, 0], [0, 1, 0], 'external_float_transform', {'heave_m': .12, 'roll_degrees': 3, 'pitch_degrees': 2})
        a.connections += [{'id': 'rigid_barge', 'parts': ['hull.solid', 'decks.solid'], 'status': 'Whole-asset root transform required; do not move hull without decks.'}]
        a.design += ['Flat-bottom river cargo barge; no ocean-going ship, sail, rigging or buoyancy simulation claimed.']
    elif kind == 'warehouse_hoist':
        a = Source(kind, [-.6, 0, -.35], [.6, 3.8, 2.0])
        a.box('wall_bracket', [-.22, 2.2, -.35], [.22, 3.7, .1], 'timber_dark', component='bracket')
        a.box('hoist_beam', [-.18, 3.35, -.2], [.18, 3.7, 1.8], 'timber', component='bracket')
        a.beam('brace', [0, 2.35, .05], [0, 3.45, 1.4], .15, 'timber_dark', component='bracket')
        a.box('drum', [-.55, 3.2, 1.35], [.55, 3.55, 1.75], 'timber_dark', component='drum', part='spool', pivot=(0, 3.4, 1.55))
        a.beam('rope', [0, .45, 1.55], [0, 3.4, 1.55], .11, 'timber_light', minimum_radius_cells=.75, component='rope')
        a.box('hook', [-.15, .2, 1.4], [.15, .5, 1.7], 'iron', component='hook', part='hook', pivot=(0, .35, 1.55))
        a.socket('wall_mount', [0, 2.95, 0], 'warehouse_load_bearing_wall', (0,0,-1))
        a.socket('load', [0, .2, 1.55], 'cargo_lift')
        a.support('wall_bearing', [-.22, 2.2, -.35], [.22, 3.7, 0], 'Structural wall/timber beam; align with loading aperture only after facade review.')
        a.clearance('loading_column', [-.6, 0, .6], [.6, 3.2, 2], 'Cargo lift reservation.', False)
        a.hook('spool_rotation', 'drum', 'spool', [0,3.4,1.55], [1,0,0], 'rotation_degrees', [0,360])
        a.hook('cargo_lift', 'hook', 'hook', [0,.35,1.55], [0,1,0], 'translation_metres', [0,2.4])
        a.design += ['Hoist attaches to a reused warehouse master. No automatic cut into its facade.']
    elif kind == 'cathedral_flying_buttress':
        a = Source(kind, [-3, 0, -.65], [3, 8, .65])
        a.box('outer_footing', [1.7, 0, -.65], [3, .4, .65], 'stone_dark', component='pier')
        a.box('outer_pier', [1.9, .4, -.5], [2.8, 6.4, .5], 'stone', component='pier')
        a.box('pier_cap', [1.8, 6.4, -.6], [2.9, 6.8, .6], 'stone_light', component='pier')
        a.box('upper_pier', [2.1, 6.8, -.35], [2.6, 8, .35], 'stone_light', component='pier')
        a.op('flying_arch', extrusion([[-3,6.0],[-1.5,5.0],[0,4.55],[2.1,4.4],[2.1,5.05],[0,5.3],[-1.5,5.8],[-3,6.8]], -.35, .35), 'stone_light', component='arch')
        a.socket('cathedral_wall', [-3,6.4,0], 'structural_nave_wall', (-1,0,0))
        a.socket('ground_pier', [2.35,0,0], 'ground_foundation')
        a.support('pier_bearing', [1.7,0,-.65], [3,.1,.65], 'Level foundation outside aisle.')
        a.support('wall_abutment', [-3,6,-.35], [-2.9,6.8,.35], 'Nave wall bearing band; never leave inner arch end floating.')
        a.clearance('under_arch', [-2.6,.01,-.3], [1.6,4.3,.3], 'Open lower arch volume; confirm route width with adjacent bays.')
        a.connections += [{'id': 'arch_to_pier', 'a': 'arch', 'b': 'pier', 'status': 'Authored contact; host nave connection awaits placement.'}]
        a.constraints += [{'id': 'arch_touches_pier', 'kind': 'touch', 'a': {'component':'arch'}, 'b': {'component':'pier'}}]
        a.design += ['Flying buttress is a local modular prototype, not the final 70 m cathedral buttress scheme.', 'Arch profile and masonry are design inference; structural engineering not performed.']
    elif kind == 'pointed_arch_cloister_bay':
        a = Source(kind, [-2, -.2, -1.2], [2, 3.8, 1.2])
        a.box('paving', [-2,-.2,-1.2], [2,0,1.2], 'stone_dark', component='paving')
        for x in (-2,1.6):
            a.box('front_pier_' + str(x), [x,0,.7], [x+.4,2.6,1.2], 'stone', component='arcade')
            a.box('rear_pier_' + str(x), [x,0,-1.2], [x+.4,3.3,-.8], 'stone', component='arcade')
        # The sloping lower edge creates a true pointed opening. No painted icon.
        a.op('pointed_spandrel', extrusion([[-2,2.3],[-1.6,2.3],[0,3.2],[1.6,2.3],[2,2.3],[2,3.5],[-2,3.5]], .7,1.2), 'stone_light', component='arcade')
        a.op('gray_slate_canopy', extrusion([[-2,3.5],[2,3.5],[2,3.8],[-2,3.8]], -1.2,1.2), 'slate', component='roof')
        a.socket('repeat_left', [-2,0,0], 'cloister_bay', (-1,0,0))
        a.socket('repeat_right', [2,0,0], 'cloister_bay', (1,0,0))
        a.socket('garden_entry', [0,0,1.2], 'courtyard_path', (0,0,1))
        a.support('bay_bearing', [-2,-.2,-1.2], [2,-.1,1.2], 'Level terrace slab; adjoining floor grades must match.')
        a.clearance('arcade_passage', [-1.5,.01,-1.15], [1.5,2.25,1.15], '3 m wide, 2.25 m high guaranteed rectangular part of pointed opening.')
        a.design += ['Single roofed cloister bay; complete cloister corners, drainage and courtyard arrangement await concept review.']
    elif kind == 'park_terrace_stair':
        a = Source(kind, [-1.2,-.15,-.9], [1.2,.9,2.7])
        a.smoke_pitch = .15
        a.box('lower_landing', [-1.2,-.15,-.9], [1.2,0,0], 'stone_dark')
        for i in range(6):
            a.box('tread_' + str(i+1), [-1.2,-.15,i*.3], [1.2,(i+1)*.15,(i+1)*.3], 'stone_light' if i%2 else 'stone')
        a.box('upper_landing', [-1.2,-.15,1.8], [1.2,.9,2.7], 'stone_dark')
        a.socket('lower_route', [0,0,-.9], 'pedestrian_landing', (0,0,-1))
        a.socket('upper_route', [0,.9,2.7], 'pedestrian_landing', (0,0,1))
        a.support('stair_bed', [-1.2,-.15,-.9], [1.2,-.05,2.7], 'Continuous prepared terrace support; no terrain grade is authored here.')
        a.clearance('overhead', [-1.15,.91,-.85], [1.15,3.2,2.65], 'Standing clearance above highest tread/landing.')
        a.lod.update(candidate_visual_pitches_m=[.05,.15,.3],
                     traversal_pitches_m=[.05,.15],
                     rejected_traversal_pitches_m=[.1,.2,.3,.4],
                     rejection_reason='Non-divisors of 0.15 m rise/0.30 m tread can merge or unevenly quantize steps. Coarse visuals cannot define gameplay collision.')
        a.design += ['Six 0.15 m risers, 0.30 m treads, 2.40 m width and 0.90 m landings.', '0.15 m riser is a gameplay design choice, not a historical assertion or accessibility certification.', 'Separate accessible route, edge guards and character traversal require assembly review.']
    elif kind == 'retaining_wall_corner':
        a = Source(kind, [0,-.4,0], [3,1.8,3])
        a.box('wall_x', [0,-.4,0], [3,1.6,.6])
        a.box('wall_z', [0,-.4,.6], [.6,1.6,3])
        a.box('cap_x', [0,1.6,0], [3,1.8,.6], 'stone_light')
        a.box('cap_z', [0,1.6,.6], [.6,1.8,3], 'stone_light')
        a.socket('repeat_x', [3,1.8,.3], 'retaining_wall', (1,0,0))
        a.socket('repeat_z', [.3,1.8,3], 'retaining_wall', (0,0,1))
        a.support('corner_bearing', [0,-.4,0], [3,-.3,.6], 'Prepared foundation; backfill and drainage behind wall are external.')
        a.clearance('inside_corner', [.65,0,.65], [2.95,1.75,2.95], 'Inner terrace/backfill reservation, intentionally not filled in source.')
        a.design += ['Inside retaining corner; concave/convex arrangement and soil side remain placement decisions.']
    elif kind == 'park_bench':
        a = Source(kind, [-.9,0,-.35], [.9,.9,.35])
        a.box('seat', [-.9,.4,-.35], [.9,.55,.35], 'timber_light', component='seat')
        for x in (-.65,.45):
            a.box('leg_' + str(x), [x,0,-.3], [x+.2,.4,.3], 'stone_dark', component='supports')
        a.box('back', [-.9,.55,-.35], [.9,.9,-.15], 'timber', component='seat')
        a.socket('sitting', [0,.55,.1], 'seated_character', (0,0,1))
        a.support('bench_feet', [-.65,0,-.3], [.65,.1,.3], 'Level ground under two actual leg footprints.')
        a.clearance('front_access', [-1,0,.36], [1,2.1,1.5], 'Approach and standing space.')
        a.design += ['Seat height 0.55 m chosen for prototype silhouette; ergonomics and animation pose need review.']
    elif kind == 'stone_planter':
        a = Source(kind, [-.6,0,-.6], [.6,.6,.6])
        a.box('base', [-.6,0,-.6], [.6,.2,.6], 'stone_dark')
        for x in (-.6,.4): a.box('side_x_' + str(x), [x,.2,-.6], [x+.2,.6,.6], 'stone_light')
        for z in (-.6,.4): a.box('side_z_' + str(z), [-.4,.2,z], [.4,.6,z+.2], 'stone_light')
        a.socket('plant', [0,.2,0], 'separate_soil_and_vegetation')
        a.support('planter_bearing', [-.6,0,-.6], [.6,.1,.6], 'Level plaza/terrace surface.')
        a.clearance('planter_cavity', [-.39,.21,-.39], [.39,.61,.39], 'Reserved soil/plant volume; cavity is truly open.')
        a.design += ['Stone vessel only. Reuse existing garden/tree sources after botanical and material review.']
    elif kind == 'cargo_crate':
        a = Source(kind, [-.5,0,-.4], [.5,.8,.4])
        a.box('crate_box', [-.5,0,-.4], [.5,.8,.4], 'timber')
        for x in (-.4,.25): a.box('binding_' + str(x), [x,0,-.4], [x+.15,.8,.4], 'timber_dark')
        a.socket('base', [0,0,0], 'cargo_stack')
        a.socket('stack_top', [0,.8,0], 'cargo_stack')
        a.socket('lift', [0,.8,0], 'sling_attachment')
        a.support('crate_bearing', [-.5,0,-.4], [.5,.1,.4], 'Hold, loading platform or another crate; no hidden container contents.')
        a.clearance('handling', [-.7,0,-.6], [.7,1.2,.6], 'Handling reservation around cargo.', False)
    else:
        a = Source(kind, [-.45,0,-.45], [.45,1,.45])
        a.op('barrel_staves', {'kind':'lathe','profile':[[0,0],[.35,0],[.45,.35],[.45,.65],[.35,1],[0,1]]}, 'timber')
        for y in (.1,.7):
            a.op('hoop_' + str(y), {'kind':'annulus','inner_radius':.38,'outer_radius':.45,'y_min':y,'y_max':y+.2}, 'iron', component='hoops')
        a.socket('base', [0,0,0], 'cargo_floor')
        a.socket('lift', [0,1,0], 'cargo_sling')
        a.support('barrel_bearing', [-.35,0,-.35], [.35,.1,.35], 'Flat hold/loading surface; rolling animation not authored.')
        a.clearance('handling', [-.65,0,-.65], [.65,1.4,.65], 'Handling reservation.', False)
    return a.finish()


def write_sources(output=HERE / 'masters'):
    output.mkdir(parents=True, exist_ok=True)
    for kind in KINDS:
        (output / (kind + '.json')).write_text(json.dumps(make_master(kind), indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    return len(KINDS)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'masters')
    args = parser.parse_args()
    print(json.dumps({'authored': write_sources(args.output), 'output': str(args.output),
                      'status': 'staged_prototypes_no_city_placement'}))
