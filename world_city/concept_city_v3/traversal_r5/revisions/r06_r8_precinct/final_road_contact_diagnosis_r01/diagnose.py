"""Read-only exact source and live-engine face measurements for two routes."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'voxel_character').is_dir())
BASE = HERE.parent


def load(path):
    return json.loads(path.read_bytes())


def ref(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def geometry(triangle, point):
    p = np.asarray(point, dtype=np.float64)
    t = np.asarray(triangle, dtype=np.float64)
    xz = t[:, [0, 2]]
    normal = np.cross(t[1] - t[0], t[2] - t[0])
    signs, distances, lines = [], [], []
    for i in range(3):
        a, b = xz[i], xz[(i + 1) % 3]
        v, w = b - a, p - a
        cross = float(v[0] * w[1] - v[1] * w[0])
        signs.append(cross)
        fraction = max(0.0, min(1.0, float(w @ v / (v @ v)))) if v @ v else 0.0
        distances.append(float(np.linalg.norm(p - (a + fraction * v))))
        lines.append(cross / float(np.linalg.norm(v)) if np.linalg.norm(v) else None)
    inside = all(s >= 0 for s in signs) or all(s <= 0 for s in signs)
    area = abs(float(normal[1])) * 0.5
    plane = None
    if area > 0:
        plane = np.linalg.solve(np.column_stack([xz, np.ones(3)]), t[:, 1])
    return {
        'projected_area_m2': area,
        'area_3d_m2': float(np.linalg.norm(normal)) * .5,
        'normal_xyz': normal.tolist(),
        'point_inside_inclusive_exact_sign': inside,
        'point_outside_distance_m': 0.0 if inside else min(distances),
        'signed_edge_distances_m': lines,
        'plane_y_xz_m': None if plane is None else plane.tolist(),
        'plane_height_at_ray_m': None if plane is None else float(plane @ [*p, 1.0]),
        'gradient': None if plane is None else float(np.linalg.norm(plane[:2])),
    }


def signature(triangle):
    return tuple(sorted(tuple(v) for v in triangle))


def main():
    prepared_path = BASE / 'public_network_final_runtime_r01/prepared_runtime.json'
    original_path = BASE / 'public_network_final_runtime_r01/evidence/road_failures_r01.json'
    event_path = HERE / 'evidence/original_final481/observer_events.jsonl'
    replay_path = HERE / 'evidence/original_final481/replay.json'
    prepared = load(prepared_path)
    original = {r['result']['id']: r['result'] for r in load(original_path)['cases']}
    replay = load(replay_path)
    parity = []
    for row in replay['routes']:
        old = original[row['id']]
        differences = [k for k in old if old[k] != row.get(k)]
        critical = ['status', 'pass', 'physics_frames', 'not_on_floor_frames', 'max_not_on_floor_streak', 'ground_ray_miss_frames', 'obstacle_contact_ids']
        assert all(old[k] == row[k] for k in critical), (row['id'], differences)
        parity.append({'id': row['id'], 'strict_result_and_failure_counts_identical': True, 'all_result_fields_identical': not differences, 'other_result_field_differences': differences, 'end_position_delta_m': [row['end_position'][i] - old['end_position'][i] for i in range(3)]})
    events = [json.loads(line) for line in event_path.read_text().splitlines()]
    failure_events = [r for r in events if r['event'] == 'post_step_contact_or_support_event'
                      and (not r['on_floor'] or r['original_ground_ray_miss_delta'] > 0)]
    snapshots = {(r['case'], r['walk_physics_frame']): r for r in events
                 if r['event'] == 'read_only_shapes_at_support_or_floor_event'}
    index_path = ROOT / 'world_city/concept_city_v3/evidence/r8_final110_precision_r01/retained_source_index_map.json'
    index_map = load(index_path)
    assets, rows, target_faces = {}, [], {}
    for event in failure_events:
        key = (event['case'], event['walk_physics_frame'])
        snap = snapshots[key]
        point = [float(np.float32(snap['point'][i])) for i in [0, 2]]
        faces = []
        for collider in snap['colliders']:
            if not collider['nearby_faces']:
                continue
            owner = collider['collider']['source_id']
            if owner not in assets:
                assets[owner] = load(ROOT / prepared['assets'][owner]['render_path'])
            asset = assets[owner]
            origin = prepared['placements'][owner]['position_m']
            for face in collider['nearby_faces']:
                i = int(face['face_index'])
                material, scene_index = asset['source_face_indices'][i]
                source = [[v[k] + origin[k] for k in range(3)] for v in asset['triangles'][i]]
                record = {
                    'collider_owner': owner, 'collider_face_index': i,
                    'runtime_scene_face': [material, scene_index],
                    'authored_scene_face': [material, index_map[material][scene_index]],
                    'precise_world_triangle_xyz_m': source,
                    'live_engine_face': face,
                    'precise_measurements': geometry(source, point),
                    'live_float32_measurements': geometry(face['world_xyz_float32_m'], point),
                }
                faces.append(record)
                target_faces[(material, scene_index)] = source
        rows.append({'case': key[0], 'frame': key[1], 'event': event, 'nearby_faces': faces})

    # Find provenance in the untouched R7 source without inventing a nearest owner.
    r7_path = ROOT / 'world_city/concept_city_v3/evidence/visual_registered_common_r7_palette_r01/scene.json'
    wanted = {signature(t): key for key, t in target_faces.items()}
    r7 = load(r7_path)
    original_faces = {}
    for material in {k[0] for k in target_faces}:
        vertices = r7['surfaces'][material]
        for i in range(0, len(vertices), 3):
            key = wanted.get(signature(vertices[i:i + 3]))
            if key:
                original_faces.setdefault(key, []).append([material, i // 3])
    del r7
    for row in rows:
        for face in row['nearby_faces']:
            face['exact_unchanged_r7_source_faces'] = original_faces.get(tuple(face['runtime_scene_face']), [])

    civic = next(r for r in rows if r['case'] == 'ROAD:CIVIC_WEST_APPROACH')
    spike = next(f for f in civic['nearby_faces'] if f['runtime_scene_face'] == ['road', 7085])
    neighbor = next(f for f in civic['nearby_faces'] if f['runtime_scene_face'] == ['road', 7084])
    triangle = spike['precise_world_triangle_xyz_m']
    plane = neighbor['precise_measurements']['plane_y_xz_m']
    deviations = [v[1] - (plane[0] * v[0] + plane[1] * v[2] + plane[2]) for v in triangle]
    output = {
        'schema': 'riverstone.final_runtime.two_road_contact_diagnosis.v1',
        'status': 'Original strict outcomes and failure counts reproduced; read-only geometry diagnosis',
        'sources': {'prepared': ref(prepared_path), 'original_failure_cases': ref(original_path),
                    'observer_events': ref(event_path), 'observer_replay': ref(replay_path),
                    'runtime_index_map': ref(index_path), 'unchanged_r7': ref(r7_path),
                    'diagnostic_implementation': ref(Path(__file__))},
        'original_case_result_parity': parity,
        'case_frame_face_measurements': rows,
        'civic_thin_raised_face': {
            'runtime_scene_face': ['road', 7085],
            'original_r7_faces': spike['exact_unchanged_r7_source_faces'],
            'precise_measurements': spike['precise_measurements'],
            'live_float32_measurements': spike['live_float32_measurements'],
            'height_deviation_from_adjacent_road7084_plane_m': deviations,
            'classification': 'Nonzero thin raised source fan beside the exact airborne frames; all rays retain valid neighboring road support. Causal repair replay is still required.',
        },
        'east_wall_classification': 'Both exact ray centers have precise Y1 road support but lie just outside the live float32 road edges. The capsule remains grounded. This is measured coordinate quantization, not an absent authored floor or height step.',
        'minimal_correction_proposals': [
            {'case': 'ROAD:EAST_WALL_SERVICE_REVERSE', 'proposal': 'Use a bounded common local-coordinate frame for the exact coincident road/private seam through the existing actual-scene collider contract. Preserve all precise source vertices, winding, planes and route criteria. Validate roundtrip and both directions before adoption.'},
            {'case': 'ROAD:CIVIC_WEST_APPROACH', 'proposal': 'First distinguish runtime recovery on the existing nonzero thin raised face from a real support gap. If source correction is authorized, compose a finite source-bound fan retriangulation using road7084–7087 and their exact outer knots, explicitly reconciling the interior raised knot. Do not remove nonzero geometry by an area threshold.'},
        ],
        'limits': ['No geometry, prepared input, controller or acceptance criterion changed.',
                   'Repeated observer rays are diagnostic; original controller miss counts are logged independently.',
                   'This report does not assert a candidate correction has passed runtime.'],
    }
    with (HERE / 'diagnosis.json').open('x') as file:
        json.dump(output, file, indent=2, allow_nan=False)
        file.write('\n')
    print(json.dumps({'report': ref(HERE / 'diagnosis.json'), 'exact_case_parity': parity,
                      'civic_spike_deviation_m': max(deviations),
                      'civic_r7_faces': spike['exact_unchanged_r7_source_faces']}))


if __name__ == '__main__':
    main()
