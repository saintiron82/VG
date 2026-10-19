#!/usr/bin/env python3
"""Index the preserved R10 city into whole-face source-bound streaming tiles.

This is a placement/render-data adapter, not a compiler, mesher, terrain sampler,
or collision repair. Original source files and shared native assets stay intact.
Use --output for a fresh repository-local destination; --verify checks an
existing pack. The sealed default destination is never overwritten.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'voxel_character').is_dir())
CITY = ROOT / 'world_city/concept_city_v3'
OUT = HERE.parent / 'generated/tile_r01'
sys.path.insert(0, str(ROOT))
from world_city.concept_city_v3.registered_integration.r6 import merge_patches

BASE_SHA = '2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
PATCH_SHA = 'e9d2a71550ac0844fd4ae8c0cc3e56a7cee77dc9f283a321b707ba57c2bd76d5'
INDEX_SHA = '89aef5e605d68de7b02907bed0651d7fc85098104001cd43470c3502d2f844bb'
CASTLE_SHA = 'b230ba1592cb285382996907ec39ba0b0d127765acc434285b1557de6bb7d1d3'
INPUTS = {
    'base_scene': ('evidence/r8_final110_runtime_r01/scene.json', BASE_SHA),
    'finite_patch': ('registered_integration/r10_functional_audit/integration_r04/surface_patch.json', PATCH_SHA),
    'visual_index': ('registered_integration/r10_functional_audit/integration_r04/index.json', INDEX_SHA),
    'castle_addendum': ('assemblies/ordinary/registered/district_fabric_r01/primary_bent_goals_r01/castle/surface_patch.json', CASTLE_SHA),
}
TILE_SIZE = 64.0
UINT_NONE = 0xffffffff
RECORD = struct.Struct('<9d4I')
DTYPE = np.dtype([('vertices', '<f8', (3, 3)), ('source_kind', '<u4'),
                  ('material_index', '<u4'), ('source_triangle_index', '<u4'),
                  ('replacement_index', '<u4')])
SUPPORTED_CONTRACTS = {
    'SOUTHERN_FINITE_GRADED_LANE', 'SOUTHERN_NATIVE_FLAT_TERMINAL_APRON',
    'PHASE02_STAIR_FINITE_CONTINUOUS_WALKING', 'NORTH_APPROACH_R04_CONTINUOUS_ROAD',
    'R8_COMMON_FINITE_CONTINUOUS_WALKING_R03',
    'R8_NOBLE_SEVEN_FINE_WALKING_R02:E1', 'R8_NOBLE_SEVEN_FINE_WALKING_R02:E2',
    'R8_NOBLE_SEVEN_FINE_WALKING_R01:E3', 'R8_NOBLE_SEVEN_FINE_WALKING_R02:E4',
    'R8_NOBLE_SEVEN_FINE_WALKING_R02:E5', 'R8_NOBLE_SEVEN_FINE_WALKING_R02:E6',
    'R8_NOBLE_SEVEN_FINE_WALKING_R02:E7',
    'FIXED_BRIDGE_STONE_SPANS_CONTINUOUS_WALK_R02',
    'R8_ORDINARY_FINAL_B001_C003_FINE_STEPS', 'PORT_BRIDGE_FINITE_APPROACH_R01',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def ref(path):
    return {'path': relative(path), 'sha256': sha(path)}


def resolve(reference):
    path = Path(reference['path'])
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Source outside repository: ' + str(path))
    if sha(path) != reference['sha256']:
        raise ValueError('Source hash drift: ' + str(path))
    return path


def write(path, value):
    Path(path).write_text(json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n')


def tile_id(x, z):
    return f'{int(x)}_{int(z)}'


def owner_of(triangle):
    center = np.asarray(triangle, dtype=np.float64).mean(axis=0)
    return tile_id(math.floor(center[0] / TILE_SIZE), math.floor(center[2] / TILE_SIZE))


def cells_for_bounds(bounds):
    """Closed bbox intersection, including cells touching an exact tile edge."""
    lo_x, lo_z, hi_x, hi_z = bounds
    first_x = math.floor(math.nextafter(float(lo_x) / TILE_SIZE, -math.inf))
    first_z = math.floor(math.nextafter(float(lo_z) / TILE_SIZE, -math.inf))
    for x in range(first_x, math.floor(float(hi_x) / TILE_SIZE) + 1):
        for z in range(first_z, math.floor(float(hi_z) / TILE_SIZE) + 1):
            yield tile_id(x, z)


def xz_bounds(points):
    a = np.asarray(points, dtype=np.float64)
    return [float(a[:, 0].min()), float(a[:, 2].min()),
            float(a[:, 0].max()), float(a[:, 2].max())]


def instance_bounds(placement, bounds):
    low, high = bounds['min'], bounds['max']
    corners = np.asarray([[x, y, z] for x in [low[0], high[0]]
                          for y in [low[1], high[1]] for z in [low[2], high[2]]])
    yaw = float(placement.get('yaw_rad', 0))
    c, s = math.cos(yaw), math.sin(yaw)
    basis = np.asarray(placement.get('transform', {}).get('basis', [[c, 0, s], [0, 1, 0], [-s, 0, c]]))
    return xz_bounds(corners @ basis.T + np.asarray(placement['position_m']))


def checked_triangles(value, name, require_up=False, require_runtime_winding=False):
    a = np.asarray(value, dtype=np.float64).reshape(-1, 3, 3)
    if not np.isfinite(a).all():
        raise ValueError('Nonfinite triangle: ' + name)
    if not len(a):
        return a
    n = np.cross(a[:, 1] - a[:, 0], a[:, 2] - a[:, 0])
    f = a.astype(np.float32)
    fn = np.cross(f[:, 1] - f[:, 0], f[:, 2] - f[:, 0])
    if np.any(np.all(n == 0, axis=1)) or np.any(np.all(fn == 0, axis=1)):
        raise ValueError('Zero-area source/runtime triangle: ' + name)
    if require_runtime_winding and np.any(np.sum(n * fn, axis=1) <= 0):
        raise ValueError('Float32 winding changes: ' + name)
    if require_up and np.any(fn[:, 1] <= 0):
        raise ValueError('Append-only top surface has wrong winding: ' + name)
    return a


def face_key(triangle, oriented=False):
    """Exact float64 geometry identity, signed zero normalized, no tolerance weld."""
    points = [tuple(0.0 if v == 0 else float(v) for v in p) for p in triangle]
    if oriented:
        first = min(range(3), key=lambda i: points[i])
        points = points[first:] + points[:first]
    else:
        points.sort()
    return struct.pack('<9d', *(v for p in points for v in p))


def resolved_surfaces(scene, patch, castle):
    """Yield authored faces with fully reversible source identifiers."""
    edits = {(r['material'], r['triangle_index']): r for r in patch['surface_edits']}
    for material, verts in scene['surfaces'].items():
        checked_triangles(verts, 'base/' + material)
        for i in range(len(verts) // 3):
            tri = verts[3*i:3*i+3]
            edit = edits.get((material, i))
            if edit is None:
                yield material, tri, 0, i, UINT_NONE
                continue
            if tri != edit['source_triangle_xyz_m']:
                raise ValueError('Finite replacement source mismatch')
            a = checked_triangles(edit['replacement_triangles_xyz_m'], f'edit/{material}/{i}')
            normal = np.cross(np.asarray(tri[1])-tri[0], np.asarray(tri[2])-tri[0])
            lo = xz_bounds(tri)
            for j, replacement in enumerate(a):
                if np.dot(normal, np.cross(replacement[1]-replacement[0], replacement[2]-replacement[0])) <= 0:
                    raise ValueError('Replacement winding drift')
                bb = xz_bounds(replacement)
                if bb[0] < lo[0]-1e-7 or bb[1] < lo[1]-1e-7 or bb[2] > lo[2]+1e-7 or bb[3] > lo[3]+1e-7:
                    raise ValueError('Replacement outside finite source bounds')
                yield material, replacement, 1, i, j
    for kind, patch_value in [(2, patch), (3, castle)]:
        for material, verts in patch_value['appended_surfaces'].items():
            if material not in scene['materials']:
                raise ValueError('Unknown appended material')
            a = checked_triangles(verts, f'append/{kind}/{material}', require_up=kind == 3 or material != 'bank')
            for i, triangle in enumerate(a):
                yield material, triangle, kind, i, UINT_NONE


def static_bridge_placements(bridge):
    """Bake only the exact source ROAD_OPEN pose; retain native geometry shared."""
    frame = bridge['bridge_to_world']
    wb = np.asarray(frame['basis'], dtype=np.float64)
    wo = np.asarray(frame['translation'], dtype=np.float64)
    result = []
    for p in bridge['states']['ROAD_OPEN']['movable_placements']:
        if p['collision'] != 'kinematic_exact_common_mesh':
            raise ValueError('Unsupported bridge collision mode')
        tr = p['transform_bridge_local']
        basis = wb @ np.asarray(tr['basis'])
        pos = wb @ np.asarray(tr['translation']) + wo
        result.append({'id':'BRIDGE_STATE:ROAD_OPEN:'+p['id'], 'asset_key':p['asset_key'],
            'position_m':pos.tolist(), 'transform':{'basis':basis.tolist()}, 'scale':[1,1,1],
            'palette_id':'source_default', 'palette_override':{}, 'collision_enabled':True,
            'source_bridge_state':'ROAD_OPEN','source_bridge_placement_id':p['id']})
    for chain in bridge['states']['ROAD_OPEN']['chains']:
        if chain['collision'] != 'visual_only_with_reserved_swept_corridor':
            raise ValueError('Unsupported chain collision mode')
        pts = np.asarray(chain['polyline_bridge_xyz_m'],dtype=np.float64)
        for segment,(a,b) in enumerate(zip(pts,pts[1:])):
            length = float(np.linalg.norm(b-a))
            if length < .00001: continue
            direction = (b-a)/length
            count = max(1,math.ceil(length/float(chain['link_spacing_m'])))
            # Shortest-arc quaternion from UP, matching BridgeMechanism.gd.
            up = np.asarray([0.,1.,0.]); qv=np.cross(up,direction); qw=1.+float(np.dot(up,direction))
            if qw < 1e-12: qv=np.asarray([1.,0.,0.]);qw=0.
            qnorm=math.sqrt(float(np.dot(qv,qv))+qw*qw);qv/=qnorm;qw/=qnorm
            x,y,z=qv
            orientation=np.asarray([[1-2*(y*y+z*z),2*(x*y-z*qw),2*(x*z+y*qw)], [2*(x*y+z*qw),1-2*(x*x+z*z),2*(y*z-x*qw)], [2*(x*z-y*qw),2*(y*z+x*qw),1-2*(x*x+y*y)]])
            for j in range(count):
                angle=math.pi*.5 if j%2 else 0.;c,s=math.cos(angle),math.sin(angle)
                twist=np.asarray([[c,0,s],[0,1,0],[-s,0,c]])
                basis=wb @ orientation @ twist
                pos=wb @ (a+direction*(length*j/count))+wo
                result.append({'id':f'BRIDGE_STATE:ROAD_OPEN:{chain["id"]}:{segment}:{j}',
                    'asset_key':chain['native_link_key'],'position_m':pos.tolist(),
                    'transform':{'basis':basis.tolist()},'scale':[1,1,1], 'palette_id':'source_default',
                    'palette_override':{},'collision_enabled':False,'source_bridge_state':'ROAD_OPEN',
                    'source_chain_id':chain['id'],'source_chain_segment':segment,'source_chain_link':j})
    return result


def validate_contract_set(contracts):
    if {c['id'] for c in contracts} != SUPPORTED_CONTRACTS or len(contracts) != len(SUPPORTED_CONTRACTS):
        raise ValueError('Unknown, absent, or duplicate collision contract; explicit adapter required')


def validate_output(output, *, fresh):
    """Resolve repository-local output without creating or replacing anything."""
    path = Path(output)
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Output must stay inside the repository: ' + str(path))
    if fresh and path.exists():
        raise ValueError('Output already exists and will be preserved; choose a fresh repository-local --output directory or use --verify')
    if not fresh and not path.is_dir():
        raise ValueError('Verification requires an existing output directory: ' + str(path))
    return path


def build(output=OUT):
    start = time.monotonic()
    out = validate_output(output, fresh=True)
    inputs = {key: {'path': relative(CITY/path), 'sha256': digest} for key, (path, digest) in INPUTS.items()}
    sources = dict(inputs)
    scene, patch, index, castle = [read(resolve(inputs[key])) for key in ['base_scene', 'finite_patch', 'visual_index', 'castle_addendum']]
    merge_patches.merge([patch], BASE_SHA)
    merge_patches.validate_against_scene(scene, patch)
    if castle['schema'] != 'riverstone.frozen_scene_patch.v1' or castle['base_scene_sha256'] != BASE_SHA:
        raise ValueError('Castle addendum identity')
    if any(castle.get(key) for key in ['surface_edits', 'removed_foundation_proxy_ids', 'source_surface_hashes']):
        raise ValueError('Castle addendum is not append-only')
    preparer_path = CITY/'registered_integration/r10_functional_audit/interface_runtime/prepare.py'
    spec = importlib.util.spec_from_file_location('tile_source_preparer', preparer_path)
    preparer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preparer)
    assets, placements, composition = preparer.compose_natives(scene, index, sources)
    sources['compose_natives_implementation'] = ref(preparer_path)
    for name in ['RenderData.gd']:
        sources['common_' + name] = ref(ROOT/'voxel_character/common/preview'/name)
    for name in ['VisualAddendum.gd', 'FiniteSurfaceReplacement.gd', 'FiniteSurfaceAddendum.gd', 'BridgeMechanism.gd', 'City.gd']:
        sources['source_' + name] = ref(CITY/'preview_r9'/name)
    material_ids = list(scene['materials'])
    material_index = {m: i for i, m in enumerate(material_ids)}
    contracts = scene.get('collision_contracts', [])
    validate_contract_set(contracts)
    disabled = {pid for c in contracts for pid in c.get('disable_native_mesh_collider_ids', [])}
    placement_map = {p['id']: p for p in placements}
    if len(placement_map) != len(placements) or not disabled <= placement_map.keys():
        raise ValueError('Duplicate native ID or absent disabled collider')
    asset_bounds = {}
    for key, asset in assets.items():
        path = resolve({'path': asset['render_path'], 'sha256': asset['render_sha256']})
        sources['native/' + key] = ref(path)
        data = read(path)
        if data.get('schema') != 'riverstone.voxel.render.v1' or data.get('rigid_parts'):
            raise ValueError('Unsupported native render or dynamic rigid parts: ' + key)
        asset_bounds[key] = data['bounds']
        if asset.get('bounds') and asset['bounds'] != data['bounds']:
            raise ValueError('Native bounds disagree: ' + key)
        asset['bounds'] = data['bounds']
        asset['render_path'] = relative(path)
    precision_warnings = []
    for mat, verts in scene['surfaces'].items():
        a=np.asarray(verts,dtype=np.float64).reshape(-1,3,3);f=a.astype(np.float32)
        n=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);fn=np.cross(f[:,1]-f[:,0],f[:,2]-f[:,0])
        changed=np.flatnonzero(np.sum(n*fn,axis=1)<=0).tolist()
        if changed: precision_warnings.append({'base_material':mat,'source_face_indices':changed,'reason':'Pre-existing source sliver normal changes after world-coordinate float32 conversion; exact source geometry retained.'})
    for contract in contracts:
        if contract.get('source_native_face_retirements'):
            raise ValueError('Native face retirement requires an explicit supported adapter')
        for key in ['native_source', 'source_native_render', 'replacement_local_mesh', 'replacement_world_mesh', 'source_profile', 'profile_source', 'native_successor_compatibility']:
            value = contract.get(key)
            if isinstance(value, dict) and 'path' in value and 'sha256' in value:
                sources['contract/' + contract['id'] + '/' + key] = ref(resolve(value))
        pid = contract.get('native_placement_id')
        if pid:
            if pid not in placement_map:
                raise ValueError('Contract native is missing: ' + pid)
            p = placement_map[pid]
            native = contract.get('native_source')
            if native and native['sha256'] != assets[p['asset_key']]['render_sha256']:
                raise ValueError('Contract collider/native hash differs: ' + pid)
            expected = contract.get('replacement_transform')
            if expected and (expected['position_m'] != p['position_m'] or expected.get('yaw_rad', 0) != p.get('yaw_rad', 0)):
                raise ValueError('Contract/native pose differs: ' + pid)
        a = checked_triangles(contract['add_triangles_world_xyz_m'], 'contract/' + contract['id'], require_runtime_winding=False)
        f = a.astype(np.float32)
        n = np.cross(a[:,1]-a[:,0], a[:,2]-a[:,0])
        fn = np.cross(f[:,1]-f[:,0], f[:,2]-f[:,0])
        changed = np.flatnonzero(np.sum(n*fn,axis=1)<=0).tolist()
        if changed: precision_warnings.append({'contract_id':contract['id'], 'source_face_indices':changed, 'reason':'Pre-existing source sliver normal changes after world-coordinate float32 conversion. Exact authored coordinates and winding are preserved; no geometry repair or global precision certification.'})
    out.mkdir(parents=True)
    (out/'tiles').mkdir()
    tiles = {}
    dependency = collections.defaultdict(set)
    files = {}
    counters = collections.Counter()
    source_counts = collections.Counter()
    seen_render = {}
    seen_collision = {}
    duplicate_aliases = []

    def tile(ident):
        if ident not in tiles:
            tiles[ident] = {'common_instances': [], 'boxes': [], 'contract_triangles': [],
                            'contract_face_refs': [], 'render_skip_indices': [],
                            'collision_skip_indices': [], 'contract_collision_skip_indices': [],
                            'face_count': 0, 'material_face_counts': collections.Counter()}
        return tiles[ident]

    def bind(bounds, owner):
        for ident in cells_for_bounds(bounds):
            dependency[ident].add(owner)

    world_bounds = [math.inf, math.inf, -math.inf, -math.inf]
    for material, triangle, kind, source_face, replacement in resolved_surfaces(scene, patch, castle):
        ident = owner_of(triangle)
        t = tile(ident)
        local_index = t['face_count']
        bbox = xz_bounds(triangle)
        bind(bbox, ident)
        for i in [0, 1]: world_bounds[i] = min(world_bounds[i], bbox[i])
        for i in [2, 3]: world_bounds[i] = max(world_bounds[i], bbox[i])
        face_id = [kind, material_index[material], source_face, replacement]
        render_key = (material_index[material], face_key(triangle, oriented=True))
        collision_key = face_key(triangle)
        if render_key in seen_render:
            t['render_skip_indices'].append(local_index)
            duplicate_aliases.append({'face': face_id, 'render_alias_of': seen_render[render_key]})
            counters['exact_render_duplicates'] += 1
        else:
            seen_render[render_key] = [ident, local_index]
        if material == 'water':
            t['collision_skip_indices'].append(local_index)
            counters['water_display_faces'] += 1
        elif collision_key in seen_collision:
            t['collision_skip_indices'].append(local_index)
            duplicate_aliases.append({'face': face_id, 'collision_alias_of': seen_collision[collision_key]})
            counters['exact_collision_duplicates'] += 1
        else:
            seen_collision[collision_key] = [ident, 'terrain', local_index]
        if ident not in files:
            files[ident] = (out/'tiles'/f'{ident}.bin').open('wb')
        files[ident].write(RECORD.pack(*(float(v) for p in triangle for v in p), *face_id))
        t['face_count'] += 1
        t['material_face_counts'][material] += 1
        source_counts[f'{kind}/{material}'] += 1
        counters['terrain_faces'] += 1
        if counters['terrain_faces'] % 250000 == 0:
            print(f"Indexed {counters['terrain_faces']:,} whole source faces", flush=True)
    for stream in files.values(): stream.close()
    del seen_render
    for ci, contract in enumerate(contracts):
        for fi, triangle in enumerate(contract['add_triangles_world_xyz_m']):
            ident = owner_of(triangle)
            t = tile(ident)
            local_index = len(t['contract_triangles'])
            key = face_key(triangle)
            if key in seen_collision:
                t['contract_collision_skip_indices'].append(local_index)
                duplicate_aliases.append({'contract_face': [ci, fi], 'collision_alias_of': seen_collision[key]})
                counters['exact_contract_collision_duplicates'] += 1
            else:
                seen_collision[key] = [ident, 'contract', local_index]
            t['contract_triangles'].append(triangle)
            t['contract_face_refs'].append([ci, fi])
            bind(xz_bounds(triangle), ident)
            counters['contract_faces'] += 1
    del seen_collision
    bridge = scene['bridge_mechanism']
    bridge_placements = static_bridge_placements(bridge)
    for p in placements + bridge_placements:
        ident = tile_id(math.floor(p['position_m'][0]/TILE_SIZE), math.floor(p['position_m'][2]/TILE_SIZE))
        tile(ident)['common_instances'].append(p)
        bind(instance_bounds(p, asset_bounds[p['asset_key']]), ident)
    removed_boxes = set(patch.get('removed_foundation_proxy_ids', []))
    boxes = [b for b in scene['boxes'] if b['id'] not in removed_boxes]
    if len({b['id'] for b in boxes}) != len(boxes): raise ValueError('Duplicate box ID')
    for b in boxes:
        ident = tile_id(math.floor(b['position_m'][0]/TILE_SIZE), math.floor(b['position_m'][2]/TILE_SIZE))
        tile(ident)['boxes'].append(b)
        bind(instance_bounds(b, {'min': [-v/2 for v in b['size_m']], 'max': [v/2 for v in b['size_m']]}), ident)
    # Keep bridge state together as an exact source-bound group. Runtime loads it
    # only when these cells intersect interest, with ROAD_OPEN immutable in r01.
    bridge = scene['bridge_mechanism']
    if not bridge['states']['ROAD_OPEN']['road_enabled']:
        raise ValueError('No source-supported closed bridge road state')
    bridge_bounds = []
    world_basis = np.asarray(bridge['bridge_to_world']['basis'])
    world_origin = np.asarray(bridge['bridge_to_world']['translation'])
    for p in bridge['states']['ROAD_OPEN']['movable_placements']:
        if p['collision'] != 'kinematic_exact_common_mesh':
            raise ValueError('Unsupported bridge collider policy')
        bb = asset_bounds[p['asset_key']]
        corners = np.asarray([[x,y,z] for x in [bb['min'][0],bb['max'][0]] for y in [bb['min'][1],bb['max'][1]] for z in [bb['min'][2],bb['max'][2]]])
        pose = p['transform_bridge_local']
        bridge_bounds.extend((corners @ np.asarray(pose['basis']).T + np.asarray(pose['translation'])) @ world_basis.T + world_origin)
    write(out/'bridge_mechanism.json', bridge)
    metadata = []
    for c in contracts:
        metadata.append({k: v for k, v in c.items() if k not in ['add_triangles_world_xyz_m', 'removed_native_face_ledger', 'native_flat_apron_pieces', 'sections']})
        metadata[-1]['triangle_count'] = len(c['add_triangles_world_xyz_m'])
    write(out/'collision_contracts.json', {'schema': 'riverstone.playable.collision_contract_metadata.v1', 'contracts': metadata,
        'triangle_convention': 'godot_clockwise_front', 'disabled_native_collider_ids': sorted(disabled),
        'unsupported_contract_policy': 'reject; never construct fallback support'})
    records = {}
    # Empty cells with nonempty dependencies are real index records, so long
    # triangles or large native assemblies never disappear across ownership edges.
    for ident in sorted(set(tiles) | set(dependency)):
        t = tile(ident)
        x, z = [int(v) for v in ident.split('_')]
        binary = out/'tiles'/f'{ident}.bin'
        if not binary.exists(): binary.write_bytes(b'')
        json_path = out/'tiles'/f'{ident}.json'
        write(json_path, dict(t, material_face_counts=dict(t['material_face_counts'])))
        records[ident] = {'id': ident, 'cell_xz': [x,z], 'bounds_xz_m': [x*TILE_SIZE,z*TILE_SIZE,(x+1)*TILE_SIZE,(z+1)*TILE_SIZE],
            'terrain_path': relative(binary), 'terrain_sha256': sha(binary), 'face_count': t['face_count'],
            'instances_path': relative(json_path), 'instances_sha256': sha(json_path),
            'native_count': len(t['common_instances']), 'box_count': len(t['boxes']), 'contract_face_count': len(t['contract_triangles']),
            'dependency_owner_tiles': sorted(dependency.get(ident, set()) | ({ident} if t['face_count'] or t['common_instances'] or t['boxes'] or t['contract_triangles'] else set()))}
    sources = {key: ref(resolve(value)) for key, value in sources.items()}
    write(out/'duplicate_aliases.json', duplicate_aliases)
    audit = {'schema': 'riverstone.playable.city_tile_audit.v1', 'status': 'PASS', 'base_surface_faces': sum(len(v)//3 for v in scene['surfaces'].values()),
        'finite_retired_source_faces': len(patch['surface_edits']), 'finite_replacement_faces': sum(len(r['replacement_triangles_xyz_m']) for r in patch['surface_edits']),
        'source_kind_material_counts': dict(source_counts), 'counts': dict(counters), 'native_composition': composition,
        'retained_box_count': len(boxes), 'source_precision_warnings':precision_warnings, 'bridge_static_placement_count':len(bridge_placements), 'removed_box_ids': sorted(removed_boxes), 'contract_count': len(contracts),
        'validation': ['Exact source hashes, full source-face provenance and triangle values', 'Whole triangle centroid ownership; closed AABB dependencies for every intersected cell',
                       'All source materials and native palettes/transforms retained', 'No resampling, new floor, clipping, voxel compilation, or source mutation',
                       'All 15 explicit collision contracts supported; disabled native IDs checked', 'Exact duplicate render/collision faces retained for provenance and excluded by explicit skip indices',
                       'No float64 or float32 degenerate faces; source-authored winding preserved; existing contract sliver precision limitations separately listed'],
        'elapsed_s': time.monotonic()-start}
    manifest = {'schema': 'riverstone.playable.city_tile_index.v1', 'tile_size_m': TILE_SIZE, 'world_origin_m': [0,0,0], 'world_bounds_xz_m': world_bounds,
        'sources': sources, 'material_ids': material_ids, 'materials': scene['materials'], 'render_materials':scene['materials'], 'material_provenance':{'profile':'baseline','source':relative(CITY/'registered_integration/r10_functional_audit/run_city_r04.sh'),'geometry_change':False}, 'common_assets': assets,
        'disabled_native_collider_ids': sorted(disabled), 'disabled_native_instance_ids':sorted(disabled), 'collision_contracts': metadata, 'collision_contracts_ref': ref(out/'collision_contracts.json'),
        'bridge_mechanism': ref(out/'bridge_mechanism.json'), 'bridge_interest_cells': list(cells_for_bounds(xz_bounds(bridge_bounds))),
        'bridge_runtime_state': 'ROAD_OPEN', 'bridge_motion_enabled': False, 'inspection_cameras': scene['inspection_cameras'],
        'tiles': records, 'counts': dict(counters, native_instances=len(placements)+len(bridge_placements), source_native_instances=len(placements), bridge_static_instances=len(bridge_placements), shared_native_assets=len(assets), boxes=len(boxes), indexed_cells=len(records)),
        'binary_layout': {'endianness':'little','stride_bytes':88,'vertex_format':'9 float64 world XYZ in authored a,b,c order',
            'metadata_format':'4 uint32: source_kind, material_index, source_triangle_index, replacement_index',
            'source_kinds':{'0':'base_scene','1':'finite_patch_replacement','2':'finite_patch_appended','3':'castle_addendum_appended'}, 'no_replacement_index':UINT_NONE},
        'loading_policy': {'interest_radius_m':48.0,'recommended_interest_radius_m':96.0,'safety_margin_m':16.0,'minimum_radius_cells':1,'capsule_max_radius_m':0.5,'spring_arm_max_length_m':8.0,
            'max_speed_m_s':8.0,'preload_seconds':1.0,'algorithm':'Load at least the player cell and its eight neighbors (minimum 64m guaranteed reach). Configurable interest radius starts at 48m plus 16m safety margin; 96m plus margin is recommended when budget permits. Union selected cell dependency_owner_tiles once, not recursively. Stage all new owner terrain/native/box/contract colliders, then release old owners. Freeze movement while required owner data is pending or failed.',
            'whole_triangles_only':True,'aabb_dependencies_include_touching_edges':True,'deduplicate_owners':True,
            'render_winding':'terrain a,c,b with normals from a,b,c; common RenderData unchanged',
            'collision_winding':'terrain a,c,b; contract_triangles are already Godot clockwise and must not be flipped',
            'water_support':False,'exact_duplicate_policy':'Apply render_skip_indices, collision_skip_indices, contract_collision_skip_indices from each tile companion',
            'no_fallback_floor':True}, 'coverage_audit': ref(out/'coverage_audit.json') if (out/'coverage_audit.json').exists() else None}
    write(out/'coverage_audit.json', audit)
    manifest['coverage_audit'] = ref(out/'coverage_audit.json')
    write(out/'index.json', manifest)
    total_bytes = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if total_bytes > 200_000_000: raise ValueError('Tile pack exceeds 200MB budget')
    print(json.dumps({'status':'PASS','output':relative(out),'counts':manifest['counts'],'bytes':total_bytes,'elapsed_s':time.monotonic()-start}, indent=2))


def verify(output=OUT, deep=False):
    """Check every hash, ID, centroid owner, transformed bbox dependency and face."""
    output = validate_output(output, fresh=False)
    index = read(output/'index.json')
    if index['schema'] != 'riverstone.playable.city_tile_index.v1': raise ValueError('Unknown index')
    for reference in index['sources'].values(): resolve(reference)
    for key in ['collision_contracts_ref', 'bridge_mechanism', 'coverage_audit']: resolve(index[key])
    counts = collections.Counter()
    ids = set()
    boxes = set()
    sources = set()
    contract_faces = set()
    arrays = {}
    native_values = {}
    box_values = {}
    contract_values = {}
    for ident, tile in index['tiles'].items():
        path = resolve({'path':tile['terrain_path'],'sha256':tile['terrain_sha256']})
        data = read(resolve({'path':tile['instances_path'],'sha256':tile['instances_sha256']}))
        a = np.fromfile(path, dtype=DTYPE)
        if path.stat().st_size != tile['face_count']*88 or len(a)!=tile['face_count']: raise ValueError('Binary length')
        if deep: arrays[ident] = a
        for i, row in enumerate(a):
            key = tuple(int(row[k]) for k in ['source_kind','material_index','source_triangle_index','replacement_index'])
            if key in sources: raise ValueError('Duplicate source face ownership')
            sources.add(key)
            if owner_of(row['vertices']) != ident: raise ValueError('Wrong centroid owner')
            for cell in cells_for_bounds(xz_bounds(row['vertices'])):
                if ident not in index['tiles'][cell]['dependency_owner_tiles']: raise ValueError('Missing whole-face dependency')
        for p in data['common_instances']:
            if p['id'] in ids: raise ValueError('Duplicate native owner')
            ids.add(p['id'])
            if deep: native_values[p['id']] = p
            for cell in cells_for_bounds(instance_bounds(p,index['common_assets'][p['asset_key']]['bounds'])):
                if ident not in index['tiles'][cell]['dependency_owner_tiles']: raise ValueError('Missing native bbox dependency')
        for b in data['boxes']:
            if b['id'] in boxes: raise ValueError('Duplicate box owner')
            boxes.add(b['id'])
            if deep: box_values[b['id']] = b
            bbox = instance_bounds(b, {'min':[-v/2 for v in b['size_m']], 'max':[v/2 for v in b['size_m']]})
            for cell in cells_for_bounds(bbox):
                if ident not in index['tiles'][cell]['dependency_owner_tiles']: raise ValueError('Missing box dependency')
        for key, tri in zip(data['contract_face_refs'],data['contract_triangles']):
            if tuple(key) in contract_faces: raise ValueError('Duplicate contract face owner')
            contract_faces.add(tuple(key))
            if deep: contract_values[tuple(key)] = tri
            if owner_of(tri)!=ident: raise ValueError('Wrong contract centroid')
            for cell in cells_for_bounds(xz_bounds(tri)):
                if ident not in index['tiles'][cell]['dependency_owner_tiles']: raise ValueError('Missing contract dependency')
        counts['terrain_faces']+=len(a)
    if len(ids)!=index['counts']['native_instances'] or len(boxes)!=index['counts']['boxes'] or counts['terrain_faces']!=index['counts']['terrain_faces'] or len(contract_faces)!=index['counts']['contract_faces']:
        raise ValueError('Coverage count mismatch')
    if deep:
        scene, patch, castle = [read(resolve(index['sources'][k])) for k in ['base_scene','finite_patch','castle_addendum']]
        material_index = {m:i for i,m in enumerate(index['material_ids'])}
        by_source = {}
        for ident,a in arrays.items():
            for i,row in enumerate(a):
                key=tuple(int(row[k]) for k in ['source_kind','material_index','source_triangle_index','replacement_index'])
                by_source[key]=(ident,i)
        checked = 0
        for mat,tri,kind,fi,ri in resolved_surfaces(scene,patch,castle):
            key=(kind,material_index[mat],fi,ri)
            ident,i=by_source[key]
            if not np.array_equal(arrays[ident][i]['vertices'],tri): raise ValueError('Changed authored coordinates')
            checked+=1
        if checked!=len(by_source): raise ValueError('Extra or missing source faces')
        for ci, contract in enumerate(scene['collision_contracts']):
            for fi, tri in enumerate(contract['add_triangles_world_xyz_m']):
                if contract_values.get((ci,fi)) != tri: raise ValueError('Contract geometry altered')
        source_index = read(resolve(index['sources']['visual_index']))
        preparer_path = resolve(index['sources']['compose_natives_implementation'])
        spec = importlib.util.spec_from_file_location('verify_tile_preparer',preparer_path)
        preparer=importlib.util.module_from_spec(spec);spec.loader.exec_module(preparer)
        _, expected_native, _ = preparer.compose_natives(scene,source_index,{})
        expected_native += static_bridge_placements(scene['bridge_mechanism'])
        if {p['id']:p for p in expected_native} != native_values: raise ValueError('Native placement, palette, or transform changed')
        expected_boxes={p['id']:p for p in scene['boxes'] if p['id'] not in patch.get('removed_foundation_proxy_ids',[])}
        if expected_boxes != box_values: raise ValueError('Box source mismatch')
        if index['materials'] != scene['materials'] or index['render_materials'] != scene['materials']: raise ValueError('Baseline material source mismatch')
    return {'status':'PASS','verified_terrain_faces':len(sources),'verified_native_ids':len(ids),'verified_contract_faces':len(contract_faces),'verified_boxes':len(boxes),'deep_source_parity':deep}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--deep', action='store_true')
    parser.add_argument('--output', type=Path, default=OUT, help='Repository-relative or absolute pack directory; building requires a fresh path, verification requires an existing directory')
    options = parser.parse_args()
    if options.verify: print(json.dumps(verify(output=options.output, deep=options.deep),indent=2))
    else: build(output=options.output)
