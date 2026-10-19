"""Reject malformed or downward terrain before a scene is promoted.

This checks the actual triangle vertex order consumed by existing Godot/common
RenderData. It does not change geometry or materials and is not a new mesher.
Coverage, seam heights and native footing ownership remain producer duties.
"""
import math

NORMAL_EPSILON = 1e-10


def audit_vertices(vertices, label):
    if len(vertices) % 3:
        raise ValueError('Non-triangular vertex list: ' + label)
    result = dict(triangles=len(vertices)//3, upward=0, vertical_or_tiny_projection=0,
                  downward=0, downward_projected_area_m2=0.0)
    failures = []
    for i in range(0, len(vertices), 3):
        tri = vertices[i:i+3]
        for v in tri:
            if len(v) != 3 or any(type(n) not in (int, float) or not math.isfinite(n) for n in v):
                raise ValueError('Nonfinite/malformed XYZ vertex: ' + label)
        a, b, c = tri
        ny = (b[2]-a[2])*(c[0]-a[0]) - (b[0]-a[0])*(c[2]-a[2])
        if ny < -NORMAL_EPSILON:
            result['downward'] += 1
            result['downward_projected_area_m2'] -= ny/2
            if len(failures) < 8:
                failures.append(i//3)
        elif ny > NORMAL_EPSILON:
            result['upward'] += 1
        else:
            result['vertical_or_tiny_projection'] += 1
    if failures:
        raise ValueError(f'Downward terrain in {label}: {result["downward"]} faces; first indices {failures}')
    return result


def audit_patch(patch):
    reports = {}
    for row in patch['surface_edits']:
        label = f'{row["material"]}:replacement:{row["triangle_index"]}'
        if any(len(t)!=3 for t in row['replacement_triangles_xyz_m']):
            raise ValueError('Malformed replacement triangle: '+label)
        reports[label] = audit_vertices([v for t in row['replacement_triangles_xyz_m'] for v in t], label)
    for material, vertices in patch['appended_surfaces'].items():
        reports[material+':appended'] = audit_vertices(vertices, material+':appended')
    return dict(status='pass', kind='emitted_patch', checked_groups=len(reports),
                triangles=sum(r['triangles'] for r in reports.values()),
                downward=0, reports=reports)


def audit_scene(scene):
    reports = {m:audit_vertices(v, m) for m,v in scene['surfaces'].items()}
    return dict(status='pass', kind='actual_scene_terrain',
                triangles=sum(r['triangles'] for r in reports.values()),
                downward=0, reports=reports,
                limits='Winding is not a substitute for native top coverage, support, route grades or rendered/physics review.')
