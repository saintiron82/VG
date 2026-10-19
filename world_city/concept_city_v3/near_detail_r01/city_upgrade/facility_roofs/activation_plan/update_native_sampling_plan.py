"""Refresh only the changed source's metadata estimate; never compile geometry."""
import collections
import copy
import itertools
import json
import math
import resource
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import author_facility_roofs as a
import finish_roofs as f
from prepare_handoff import baseline_check


def main():
    resource.setrlimit(resource.RLIMIT_AS, (800000000, 800000000))
    prior_path = HERE / 'compile_activation_plan.json'
    result = copy.deepcopy(a.read(prior_path))
    catalog_path = HERE / 'all_72_layered_compile_catalog.v6.json'
    selector_path = a.HERE / 'variant_selection.v3.json'
    catalog = a.read(catalog_path)
    selector = a.read(selector_path)
    sources = {r['asset_key']: r for r in catalog['assets']}
    pitch, edge = result['pitch_m'], result['chunk_edge_fine_cells']
    refreshed = []
    for row in result['variants']:
        current = sources[row['variant_asset_key']]
        if row['emitted_master_sha256'] != current['emitted_master_sha256']:
            path = a.ROOT / current['emitted_master_path']
            assert a.shared.sha(path) == current['emitted_master_sha256']
            master = f.layers.load_master(path)
            spatial = f.layers.SpatialSource(master, pitch, range_only=True)
            plan = f.layers.chunk_enumeration.enumerate_paint_chunks(
                spatial, master.get('grid_origin', [0, 0, 0]), edge, a.core.EPS)
            plan.pop('owned_lows')
            operations = [o for c in master['components'] for o in c['operations']]
            visits = collections.Counter()
            origin = master.get('grid_origin', [0, 0, 0])
            def count(low, high):
                return math.prod(max(0,
                    math.ceil((high[j] - origin[j]) / pitch - a.core.EPS)
                    - math.floor((low[j] - origin[j]) / pitch + a.core.EPS))
                    for j in range(3))
            for _, _, _, ops in spatial.items:
                for op, _, _, low, high in ops:
                    visits[op['action']] += count(low, high)
            for _, prepared, placement in spatial.cuts:
                low, high = a.core.shape_bounds(prepared)
                points = [a.core.apply(placement, v)
                          for v in itertools.product(*zip(low, high))]
                visits['assembly_cut'] += count(
                    [min(v[j] for v in points) for j in range(3)],
                    [max(v[j] for v in points) for j in range(3)])
            row.update(
                emitted_master_path=current['emitted_master_path'],
                emitted_master_sha256=current['emitted_master_sha256'],
                source_gzip_bytes=path.stat().st_size,
                operations=len(operations),
                paint_operations=sum(o['action'] == 'paint' for o in operations),
                component_cut_operations=sum(o['action'] == 'cut' for o in operations),
                assembly_cut_operations=len(master.get('assembly_cuts', [])),
                components=len(master['components']), chunk_plan=plan,
                unbounded_aabb_candidate_address_visits=dict(visits))
            refreshed.append(row['variant_asset_key'])
        if row['covering'] == 'wood_shingle' and row['required_by_current_placements']:
            if row['variant_asset_key'] == 'registered_castle_stable__wood_shingle':
                row['native_lateral_seam_gate'] = {
                    'status': 'PASS_ONE_SMALL_ROI_ONLY',
                    'validation': a.ref(HERE / 'native_seam_revision/validation.json'),
                    'full_asset_seam_validation_pending': True}
            else:
                row['native_lateral_seam_gate'] = {
                    'status': 'PENDING_REPRESENTATIVE_NATIVE_ROI',
                    'known_failure_for_this_asset': False,
                    'reason': 'Shared 25 mm lateral-joint rule can alias on the 50 mm native sampling grid. Measure this asset phase/transform before its full compile; do not infer failure or fix from another asset.',
                    'full_compile_blocked_until_checked': True}
    assert refreshed == ['registered_castle_stable__wood_shingle']
    required = [r for r in result['variants'] if r['required_by_current_placements']]
    by_key = {r['variant_asset_key']: r for r in required}
    assert set(by_key) == {r['selected_variant_asset_key'] for r in selector['placements']}
    for queued in result['recommended_serial_queue']:
        row = by_key[queued['variant_asset_key']]
        queued.update(source_gzip_bytes=row['source_gzip_bytes'],
                      source_operations=row['operations'],
                      scheduled_chunks=row['chunk_plan']['scheduled_chunks'])
        if 'native_lateral_seam_gate' in row:
            queued['native_lateral_seam_gate'] = row['native_lateral_seam_gate']
    result['summary'].update(
        required_source_gzip_bytes=sum(r['source_gzip_bytes'] for r in required),
        all_retained_source_gzip_bytes=sum(r['source_gzip_bytes'] for r in result['variants']),
        required_source_operations=sum(r['operations'] for r in required),
        scheduled_chunks_at_declared_rules=sum(r['chunk_plan']['scheduled_chunks'] for r in required),
        selected_wood_variants=len([r for r in required if r['covering'] == 'wood_shingle']),
        wood_variants_pending_native_lateral_seam_roi=9,
        wood_variants_with_one_native_lateral_seam_roi_pass=1)
    result.update(
        schema='riverstone.facility_roof.compile_activation_plan.v2',
        supersedes=a.ref(prior_path), catalog=a.ref(catalog_path),
        selector=a.ref(selector_path),
        current_source_metadata_refreshed_variants=refreshed,
        refresh_author=a.ref(Path(__file__)),
        refresh_maximum_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        preserved_prior_deliverable_files=baseline_check())
    result['serial_gates'].insert(2, 'Before full compilation of each selected wood variant, verify both headlap and lateral seams on its native 50 mm grid. Nine existing wood variants need this measurement; stable passes one small ROI only. Preserve old masters when issuing any needed refinement.')
    a.write(HERE / 'compile_activation_plan.v2.json', result)
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
