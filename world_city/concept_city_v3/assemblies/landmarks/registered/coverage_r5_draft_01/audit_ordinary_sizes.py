"""Retained native roof geometry versus its original registered mass contract."""
import json, math, collections
from pathlib import Path
from project_native import HERE, ROOT, ref, sha
CITY = ROOT / 'world_city/concept_city_v3'

def main():
    c = json.loads((HERE / 'input/draft_candidate.json').read_text())
    proof = json.loads((HERE / 'asset_projection_proofs.json').read_text())
    plan = json.loads((CITY / 'registered_source/plan.json').read_text())
    buildings = {b['id']: b for b in plan['buildings']}
    plots = {p['id']: p for p in plan['plots']}
    rows = []
    for i in c['common_instances']:
        if i['source_pack'] != 'ordinary':
            continue
        src = buildings[i['id']]
        a = proof['assets'][i['asset_key']]
        roof = a['roof_rectangles_local_xz_m']
        delta = i['yaw_rad'] - src['yaw_rad']
        cs, sn = (math.cos(delta), math.sin(delta))
        pts = [[cs * q[0] + sn * q[1], -sn * q[0] + cs * q[1]] for p in roof for q in p]
        w = max((q[0] for q in pts)) - min((q[0] for q in pts))
        d = max((q[1] for q in pts)) - min((q[1] for q in pts))
        mass = src['width_m'] * src['depth_m']
        actual = a['roof_projection_area_m2']
        row = {'instance_id': i['id'], 'asset_key': i['asset_key'], 'source_plot_id': src['plot_id'], 'source_block_id': plots[src['plot_id']].get('block_id'), 'source_mass_width_m': src['width_m'], 'source_mass_depth_m': src['depth_m'], 'source_mass_area_m2': mass, 'actual_native_roof_width_in_source_axes_m': w, 'actual_native_roof_depth_in_source_axes_m': d, 'actual_native_roof_union_area_m2': actual, 'roof_width_ratio': w / src['width_m'], 'roof_depth_ratio': d / src['depth_m'], 'roof_area_ratio': actual / mass, 'mass_minus_roof_area_m2': mass - actual, 'yaw_delta_rad': delta, 'anchor_shift_m': math.dist([i['position_m'][0], i['position_m'][2]], src['position_xz_m']), 'source_observation': src['observed_vs_inferred'], 'roof_geometry': a['render'], 'significant_span_shortfall': w / src['width_m'] < 0.9 - 1e-08 or d / src['depth_m'] < 0.9 - 1e-08, 'rule': 'Publication note: project design decision; conversational attribution omitted.'}
        rows.append(row)
    assetrows = []
    for key in sorted({r['asset_key'] for r in rows}):
        rr = [r for r in rows if r['asset_key'] == key]
        assetrows.append({'asset_key': key, 'retained_instances': len(rr), 'flagged_instance_ids': [r['instance_id'] for r in rr if r['significant_span_shortfall']], 'minimum_width_ratio': min((r['roof_width_ratio'] for r in rr)), 'minimum_depth_ratio': min((r['roof_depth_ratio'] for r in rr)), 'source_blocks': sorted({r['source_block_id'] for r in rr})})
    blocks = []
    for bid in sorted({r['source_block_id'] for r in rows}):
        rr = [r for r in rows if r['source_block_id'] == bid]
        blocks.append({'block_id': bid, 'retained_ordinary_instances': len(rr), 'flagged_instance_ids': [r['instance_id'] for r in rr if r['significant_span_shortfall']], 'registered_mass_area_sum_m2': sum((r['source_mass_area_m2'] for r in rr)), 'native_roof_area_sum_m2': sum((r['actual_native_roof_union_area_m2'] for r in rr)), 'mass_minus_roof_area_sum_m2': sum((r['mass_minus_roof_area_m2'] for r in rr)), 'note': 'Instance-area sums only; use coverage_accounting.json for clipped union coverage.'})
    flagged = [r for r in rows if r['significant_span_shortfall']]
    doc = {'schema': 'riverstone.registered_ordinary.roof_mass_size_audit.v1', 'candidate_snapshot': ref(HERE / 'input/draft_candidate.json'), 'source_plan': ref(CITY / 'registered_source/plan.json'), 'native_projections': ref(HERE / 'asset_projection_proofs.json'), 'analyzer': ref(Path(__file__)), 'rows': rows, 'assets': assetrows, 'blocks': blocks, 'summary': {'retained_ordinary_instances': len(rows), 'significant_span_shortfall_instances': len(flagged), 'flagged_asset_count': len({r['asset_key'] for r in flagged}), 'registered_mass_area_sum_m2': sum((r['source_mass_area_m2'] for r in rows)), 'native_roof_area_sum_m2': sum((r['actual_native_roof_union_area_m2'] for r in rows)), 'flagged_mass_minus_roof_area_sum_m2': sum((r['mass_minus_roof_area_m2'] for r in flagged)), 'within_10_percent_on_both_spans': len(rows) - len(flagged)}, 'prioritized_replacement_review': flagged, 'limits': ['Actual roof area is the exact native quad projection union, never a cache bounding box.', 'Width/depth are roof-span diagnostics in source axes; they are not used as roof area.', 'Original registered masses are authored proxy contracts, not traced individual image roofs.', 'A roof-box shortfall does not by itself authorize whole-building scaling or show a missing dwelling.', 'The eight undersized cases do not explain city-wide low roof coverage; existing source plots and block interiors also need coherent program/frontage review.']}
    (HERE / 'ordinary_size_audit.json').write_text(json.dumps(doc, indent=2) + '\n')
    print(doc['summary'])
    print([(r['instance_id'], r['source_block_id'], r['asset_key'], r['roof_width_ratio'], r['roof_depth_ratio']) for r in flagged])
if __name__ == '__main__':
    main()
