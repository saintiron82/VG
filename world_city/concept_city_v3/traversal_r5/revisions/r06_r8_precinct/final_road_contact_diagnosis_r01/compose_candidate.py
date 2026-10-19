"""Compose the two disjoint, exact-source-bound collision recipes."""
import copy
import json
from pathlib import Path
from .diagnose import HERE, ROOT, BASE, ref, load

ORIGINAL = BASE / 'public_network_final_runtime_r01/prepared_runtime.json'
ROADS = HERE / 'candidate_r02/prepared_runtime.json'
RADIAL = BASE / 'east_radial_shared_frame_r03/prepared_all_candidate.json'
RECIPE = HERE / 'candidate_r02/collision_recipe.json'
HANDOFF = BASE / 'east_radial_shared_frame_r03/integration_handoff.json'


def apply(prepared):
    """Preserve the supplied radial aliases and replace only three named road assets."""
    baseline, roads = load(ORIGINAL), load(ROADS)
    result = copy.deepcopy(prepared)
    changed_assets = {k for k in roads['assets'] if roads['assets'][k] != baseline['assets'].get(k)}
    changed_placements = {k for k in roads['placements'] if roads['placements'][k] != baseline['placements'].get(k)}
    for key in changed_assets:
        if prepared['assets'].get(key) != baseline['assets'].get(key):
            raise ValueError('Conflicting collision asset: ' + key)
        result['assets'][key] = copy.deepcopy(roads['assets'][key])
    for key in changed_placements:
        if prepared['placements'].get(key) != baseline['placements'].get(key):
            raise ValueError('Conflicting collision placement: ' + key)
        result['placements'][key] = copy.deepcopy(roads['placements'][key])
    original_routes = {r['id']: r for r in baseline['routes']}
    road_routes = {r['id']: r for r in roads['routes']}
    for route in result['routes']:
        old = original_routes[route['id']]
        new = road_routes[route['id']]
        assert all(old[k] == new[k] for k in old if k != 'placement_ids')
        added = [p for p in new['placement_ids'] if p not in old['placement_ids']]
        assert not [p for p in old['placement_ids'] if p not in new['placement_ids']]
        for placement in added:
            if placement in route['placement_ids']:
                raise ValueError('Repeated finite frame placement: ' + placement)
            route['placement_ids'].append(placement)
    result['sources']['bounded_final_road_recipe'] = {'path': str(RECIPE), 'sha256': ref(RECIPE)['sha256']}
    result['sources']['bounded_final_road_composer'] = {'path': str(Path(__file__)), 'sha256': ref(Path(__file__))['sha256']}
    result['sources']['preserved_east_radial_handoff'] = {'path': str(HANDOFF), 'sha256': ref(HANDOFF)['sha256']}
    result['assumptions'].append('Three explicitly bound road/entry collider corrections: exact-safe coordinate frames for East-wall and B003, and the declared 8.385523 mm Civic needle collision envelope. Source scene, visible geometry and controller stay unchanged.')
    return result


def case_payload(prepared, route):
    keys = {prepared['placements'][p]['asset_key'] for p in route['placement_ids']}
    return {'route': route,
            'assets': {k: prepared['assets'][k] for k in sorted(keys)},
            'placements': {p: prepared['placements'][p] for p in route['placement_ids']},
            'buildings': {p: prepared['buildings'][p] for p in route['building_ids']}}


def main():
    assert ref(RADIAL)['sha256'] == 'c0fcbc7d59a6a3da6be9719ec3925538c2ae4c2081a014687d229e47302a5551'
    assert ref(ROADS)['sha256'] == '7f5a7ce1ba09709f854577c25196613a1708617ebd63b016b0e16c3d3fe7088d'
    original, radial = load(ORIGINAL), load(RADIAL)
    result = apply(radial)
    originals = {r['id']: r for r in original['routes']}
    changed, unchanged = [], []
    for route in result['routes']:
        target = changed if case_payload(result, route) != case_payload(original, originals[route['id']]) else unchanged
        target.append(route['id'])
    assert len(changed) == 28 and len(unchanged) == 453
    out = HERE / 'composed_candidate_r01'
    out.mkdir()
    prepared_path = out / 'prepared_all481.json'
    with prepared_path.open('x') as stream:
        json.dump(result, stream, separators=(',', ':'), allow_nan=False)
        stream.write('\n')
    with (out / 'composition_review.json').open('x') as stream:
        json.dump({'status': 'EXACT_DISJOINT_RECIPE_COMPOSITION_RUNTIME_PENDING',
                   'original_prepared': ref(ORIGINAL), 'radial_prepared': ref(RADIAL),
                   'road_prepared': ref(ROADS), 'composed_prepared': ref(prepared_path),
                   'implementation': ref(Path(__file__)), 'changed_case_ids': changed,
                   'identical_case_ids': unchanged, 'source_scene_unchanged': result['sources']['scene'],
                   'unchanged_controller_and_criteria': True}, stream, indent=2)
        stream.write('\n')
    cases = changed + ['NEGATIVE_NORTH_CAUSEWAY_EDGE_-1']
    (out / 'case_ids.txt').write_text(','.join(cases) + '\n')
    print(json.dumps({'prepared': ref(prepared_path), 'changed_cases': len(changed), 'identical_cases': len(unchanged), 'replay_cases': len(cases)}))


if __name__ == '__main__':
    main()
