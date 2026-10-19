"""Bounded source-bound collision candidates; authored scene stays unchanged."""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from .diagnose import ROOT, HERE, BASE, load, ref
from world_city.concept_city_v3.registered_integration.r8.collision_local_origin import zero_count


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, separators=(',', ':'), allow_nan=False)
        stream.write('\n')


def translated(triangles, origin):
    local = [[[v[i] - origin[i] for i in range(3)] for v in t] for t in triangles]
    assert all(v[i] == w[i] + origin[i] for t, u in zip(triangles, local) for v, w in zip(t, u) for i in range(3))
    assert zero_count(local) == zero_count(triangles) == 0
    return local


def main():
    source = BASE / 'public_network_final_runtime_r01/prepared_runtime.json'
    prepared = load(source)
    assert ref(source)['sha256'] == '09502d7ea62af9f18428ebf1a1e60c5d5f4e84e6c1ba07110c1a3afd72b29c89'
    out = HERE / 'candidate_r02'
    out.mkdir()
    operations = []

    # A single safe Z axis retains exact double roundtrip and all existing faces.
    owner = 'SCENE:PUBLIC_NETWORK:BLOCK_003:R8_C003:PUBLIC_ENTRY'
    original = ROOT / prepared['assets'][owner]['render_path']
    data = load(original)
    before = copy.deepcopy(data['triangles'])
    origin = [0.0, 0.0, -256.0]
    data['triangles'] = translated(before, origin)
    data['collision_local_origin_xyz_m'] = origin
    path = out / 'b003_c003_exact_axis_frame.json'
    write(path, data)
    prepared['assets'][owner]['render_path'] = str(path.relative_to(ROOT))
    prepared['assets'][owner]['render_sha256'] = ref(path)['sha256']
    prepared['placements'][owner]['position_m'] = origin
    operations.append({'kind': 'exact_axis_translation', 'owner': owner, 'input': ref(original),
                       'output': ref(path), 'origin_xyz_m': origin, 'triangles': len(before),
                       'world_coordinate_error_m': 0.0, 'added_or_removed_faces': 0})

    # Group existing whole faces around the two East-wall seam points; no clipping.
    owner = 'SCENE:PUBLIC_NETWORK:ROAD:EAST_WALL_SERVICE'
    original = ROOT / prepared['assets'][owner]['render_path']
    data = load(original)
    selected, remaining = [], []
    window = [185.5, 368.0, 191.0, 373.0]
    for i, triangle in enumerate(data['triangles']):
        xs, zs = [v[0] for v in triangle], [v[2] for v in triangle]
        intersects = not (max(xs) < window[0] or min(xs) > window[2] or max(zs) < window[1] or min(zs) > window[3])
        (selected if intersects else remaining).append(i)
    origin = [192.0, 0.0, 368.0]
    shifted = translated([data['triangles'][i] for i in selected], origin)
    derived = copy.deepcopy(data)
    derived['triangles'] = shifted
    derived['source_face_indices'] = [data['source_face_indices'][i] for i in selected]
    derived['collision_local_origin_xyz_m'] = origin
    retained = copy.deepcopy(data)
    retained['triangles'] = [data['triangles'][i] for i in remaining]
    retained['source_face_indices'] = [data['source_face_indices'][i] for i in remaining]
    path = out / 'east_wall_retained_frame.json'
    local_path = out / 'east_wall_finite_exact_z_frame.json'
    write(path, retained)
    write(local_path, derived)
    prepared['assets'][owner]['render_path'] = str(path.relative_to(ROOT))
    prepared['assets'][owner]['render_sha256'] = ref(path)['sha256']
    new_owner = owner + ':FINITE_Y1_SEAM_FRAME'
    prepared['assets'][new_owner] = {'render_path': str(local_path.relative_to(ROOT)), 'render_sha256': ref(local_path)['sha256'], 'collision_format': 'actual_scene_triangles'}
    prepared['placements'][new_owner] = copy.deepcopy(prepared['placements'][owner])
    prepared['placements'][new_owner].update(id=new_owner, asset_key=new_owner, position_m=origin)
    changed_routes = []
    for route in prepared['routes']:
        if owner in route['placement_ids']:
            route['placement_ids'].append(new_owner)
            changed_routes.append(route['id'])
    operations.append({'kind': 'finite_whole_face_exact_translation', 'owner': owner, 'new_owner': new_owner,
                       'input': ref(original), 'retained_output': ref(path), 'translated_output': ref(local_path),
                       'window_xz_m': window, 'origin_xyz_m': origin, 'selected_input_indices': selected,
                       'selected_source_faces': derived['source_face_indices'], 'retained_input_indices': remaining,
                       'changed_routes': changed_routes, 'world_coordinate_error_m': 0.0,
                       'added_or_removed_faces': 0, 'all_original_face_indices_once': sorted(selected + remaining) == list(range(len(data['triangles'])))})

    # Authorized finite continuous collision envelope over the existing thin fan.
    # Keep the visible source and every XZ knot; only the internal raised Y changes.
    owner = 'SCENE:PUBLIC_NETWORK:ROAD:CIVIC_WEST_APPROACH'
    original = ROOT / prepared['assets'][owner]['render_path']
    data = load(original)
    needle_index = data['source_face_indices'].index(['road', 7085])
    neighbor_index = data['source_face_indices'].index(['road', 7084])
    before = copy.deepcopy(data['triangles'][needle_index])
    neighboring = np.asarray(data['triangles'][neighbor_index])
    plane = np.linalg.solve(np.column_stack([neighboring[:, 0], neighboring[:, 2], np.ones(3)]), neighboring[:, 1])
    after = copy.deepcopy(before)
    after[1][1] = float(plane @ [after[1][0], after[1][2], 1.0])
    data['triangles'][needle_index] = after
    assert zero_count(data['triangles']) == 0
    path = out / 'civic_finite_continuous_needle_envelope.json'
    write(path, data)
    prepared['assets'][owner]['render_path'] = str(path.relative_to(ROOT))
    prepared['assets'][owner]['render_sha256'] = ref(path)['sha256']
    operations.append({'kind': 'finite_collision_only_continuous_envelope', 'owner': owner,
                       'input': ref(original), 'output': ref(path), 'source_scene_face': ['road', 7085],
                       'original_r7_source_face': ['road', 39138], 'collider_face_index': needle_index,
                       'before_triangle_xyz_m': before, 'after_triangle_xyz_m': after,
                       'fixed_adjacent_plane_source_face': ['road', 7084], 'plane_y_xz_m': plane.tolist(),
                       'max_visible_source_deviation_m': abs(after[1][1] - before[1][1]),
                       'all_xz_knots_preserved': True, 'outer_endpoint_xyz_preserved': before[0] == after[0] and before[2] == after[2],
                       'other_source_faces_unchanged': True, 'authored_scene_unchanged': True,
                       'runtime_acceptance': 'Pending unchanged controller replay, both directions.'})
    prepared['sources']['bounded_candidate_input'] = {'path': str(source), 'sha256': ref(source)['sha256']}
    prepared['implementation_hashes'][str(Path(__file__).relative_to(ROOT))] = ref(Path(__file__))['sha256']
    write(out / 'prepared_runtime.json', prepared)
    write(out / 'collision_recipe.json', {'schema': 'riverstone.final_three_routes.collision_recipe.v1',
                                         'source_prepared': ref(source), 'prepared_candidate': ref(out / 'prepared_runtime.json'),
                                         'implementation': ref(Path(__file__)), 'operations': operations,
                                         'controller_loader_and_criteria_unchanged': True,
                                         'source_scene_unchanged': prepared['sources']['scene'],
                                         'status': 'CANDIDATE_RUNTIME_PENDING'})
    print(json.dumps({'prepared': ref(out / 'prepared_runtime.json'), 'recipe': ref(out / 'collision_recipe.json'),
                      'east_selected_faces': len(selected), 'civic_deviation_m': operations[-1]['max_visible_source_deviation_m']}))


if __name__ == '__main__':
    main()
