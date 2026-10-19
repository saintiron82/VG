"""Validate exact centre-sampled cell bounds; never grant arbitrary AABB growth.

The authoritative occupancy replay is a hashed offline common-compiler proof.
Runtime mirrors these finite checks without recompiling the building.
"""
import math

EPS = 1e-6

def vec(value):
    assert isinstance(value, list) and len(value) == 3
    assert all(isinstance(n, (int, float)) and math.isfinite(n) for n in value)
    return value

def bounds(value):
    lo, hi = vec(value['min']), vec(value['max'])
    assert all(lo[i] <= hi[i] for i in range(3))
    return lo, hi

def validate(contract, fine, coarse, source_sha, proof=None):
    assert contract['source_master_sha256'] == source_sha
    assert contract['composed_render_bounds'] == fine
    assert contract['coarse_render_bounds'] == coarse and contract['reason']
    lo, hi = bounds(fine); alo, ahi = bounds(contract['analytic_source_bounds'])
    if contract['outside_analytic_aabb_vertices'] == 0:
        assert all(alo[i]-EPS <= lo[i] <= hi[i] <= ahi[i]+EPS for i in range(3))
        return 'analytic_source'
    assert contract['outside_analytic_aabb_vertices'] > 0
    assert contract['outside_original_coarse_aabb_vertices'] == 0
    clo, chi = bounds(coarse)
    assert all(clo[i]-EPS <= lo[i] <= hi[i] <= chi[i]+EPS for i in range(3))
    env = contract['voxel_cell_envelope']; elo, ehi = bounds(env)
    origin = vec(env['grid_origin_m']); pitch = env['pitch_m']
    assert math.isfinite(pitch) and 0 < pitch <= .05
    assert env['sampling'] == 'cell_center' and env['outside_envelope_vertices'] == 0
    excess = []
    for i in range(3):
        expected_min = origin[i] + math.ceil((alo[i]-origin[i])/pitch-.5-1e-8)*pitch
        expected_max = origin[i] + (math.floor((ahi[i]-origin[i])/pitch-.5+1e-8)+1)*pitch
        assert abs(elo[i]-expected_min) <= EPS and abs(ehi[i]-expected_max) <= EPS
        assert elo[i]-EPS <= lo[i] <= hi[i] <= ehi[i]+EPS
        excess.append(max(0, alo[i]-lo[i], hi[i]-ahi[i]))
        assert excess[-1] <= pitch/2+EPS
    assert all(abs(a-b) <= EPS for a,b in zip(vec(env['max_excess_by_axis_m']),excess))
    assert abs(env['max_excess_from_analytic_m']-max(excess)) <= EPS
    assert proof and proof['schema'] == 'riverstone.common.cell_center_envelope_proof.v1'
    assert proof['source_master_sha256'] == source_sha
    assert proof['analytic_source_bounds'] == contract['analytic_source_bounds']
    assert proof['voxel_cell_envelope'] == env
    assert proof['outside_analytic_aabb_vertices'] == contract['outside_analytic_aabb_vertices']
    assert proof['outside_original_coarse_aabb_vertices'] == 0
    assert proof['source_shapes_cropped'] is False
    seen = set()
    for replay in proof['source_canonical_replay']:
        assert replay['every_witness_source_and_canonical_occupied'] is True
        assert replay['witness_cell_count'] == len(replay['witness_cells']) > 0
        rlo, rhi = bounds(replay['cell_bounds'])
        assert all(int(x) == x for x in rlo+rhi)
        for name in ('source_payload_sha256','canonical_payload_sha256'):
            assert len(replay[name]) == 64 and all(c in '0123456789abcdef' for c in replay[name])
        for cell in replay['witness_cells']:
            vec(cell); point = tuple(cell)
            assert point not in seen and all(int(cell[i]) == cell[i] and rlo[i] <= cell[i] < rhi[i] for i in range(3))
            seen.add(point)
    assert len(seen) == proof['source_occupied_boundary_cell_count'] > 0
    return 'exact_source_cell_center_envelope'
