"""Stage one complete final24 addendum and source-bound profile set."""
import json
from pathlib import Path
from .. import author as a
from ..final24_atomic_rebind_r01.prepare_request import nested_result
HERE = Path(__file__).resolve().parent
REQUEST = a.HERE / 'final24_atomic_rebind_r01/completed_request_r01.json'
SOURCE = a.HERE / 'coherent_batch20_r01'

def ref(path):
    return dict(path=str(path.relative_to(a.ROOT)), sha256=a.sha(path))

def load(binding):
    path = a.ROOT / binding['path']
    assert a.sha(path) == binding['sha256'], str(path)
    return json.loads(path.read_bytes())

def write(name, value):
    path = HERE / name
    serialized = json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n'
    if path.exists():
        assert path.read_text() == serialized, str(path)
        return
    path.write_text(serialized)

def run():
    request = json.loads(REQUEST.read_bytes())
    binding = json.loads((HERE / 'input_binding.json').read_bytes())
    add_binding = binding['atomic_source_addendum']
    add = load(add_binding)
    selected = set(request['matched_next_batch_holding_ids'])
    assert len(selected) == 23 and selected == set(add['matched_next_batch_holding_ids'])
    assert add['status'] == 'ATOMIC_SOURCE_READY_FOR_R17_COMPOSITION'
    assert load(add['native_audit'])['passed']
    records = {r['holding_id']: r for r in add['records']}
    assert set(records) == selected and all(r['passed'] for r in records.values())
    layout = load(request['source_layout'])
    prepared = load(request['source_prepared_parcels'])
    pack = load(request['source_native_pack'])
    b07 = load(request['b07_sources']['layout'])
    b07hand = load(request['b07_sources']['terrain_handoff'])
    # Replace entire selected lists so deliberately withheld panels cannot survive.
    def replace(original, replacement):
        result = [r for r in original if r.get('holding_id') not in selected] + replacement
        assert len({r['id'] for r in result}) == len(result)
        return result
    for obj in (layout, pack):
        obj['placements'] = replace(obj['placements'], add['placements'])
        obj['actual_doors'] = replace(obj['actual_doors'], add['actual_doors'])
    oldholdings = {r['id']: r for r in layout['holdings'] + b07['holdings']}
    oldparcels = {r['id']: r for r in prepared['parcels'] + b07hand['parcels']}
    layout['holdings'] = [records[h]['replacement_holding'] if h in selected else row
                          for h, row in oldholdings.items()]
    prepared['parcels'] = [records[h]['replacement_terrain_parcel'] if h in selected else row
                           for h, row in oldparcels.items()]
    prepared['native_earth_bearings'] = replace(prepared['native_earth_bearings'], add['native_earth_bearings'])
    pack['assets'].update(add['assets'])
    oldids = {r['source_id'] for r in prepared['retirement_records']}
    for r in b07hand['retirement_records']:
        if r['source_id'] in oldids:
            continue
        affected = [h['id'] for h in b07['holdings'] if r['source_id'] in h['retired_source_ids']]
        assert affected, r['source_id']
        prepared['retirement_records'].append(dict(
            source_id=r['source_id'], affected_holding_ids=affected,
            source_instance=r['source_instance'], removed_foundation_proxy_id=r['source_id'] + ':owned_foundation',
            old_body_polygon_xz_m=r['old_terrain_body_hole_polygon_xz_m'],
            old_finished_floor_y_m=r['existing_finished_floor_y_m'],
            retired_path_ids=[v['id'] for v in r['old_source_paths']],
            retired_actual_door_ids=[v['id'] for v in r['actual_old_access_records']],
            source_record=r, policy='Retire atomically; restore only residual old body outside the new coherent owner.'))
    for obj in (layout, prepared, pack):
        obj.setdefault('source_references', []).append(binding['atomic_source_addendum'])
    assert set(add['retired_source_ids']) == set(request['exact_retirement_ids'])
    for name, value in [('effective_source_layout_r03.json', layout),
                        ('effective_prepared_parcels_r03.json', prepared),
                        ('prepared_native_pack_r03.json', pack)]:
        write(name, value)
    profile_dir = HERE / 'profiles'
    profile_dir.mkdir(exist_ok=True)
    rows = []
    public = []
    for hid, binding in request['profile_bindings'].items():
        original = load(binding)
        result = dict(nested_result(original))
        assert result['status'] in ('PASSED_FINITE_TRIANGLE_GRADE', 'FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE')
        result['status'] = 'PASSED_FINITE_TRIANGLE_GRADE'
        result['grade_limit'] = original.get('grade_limit', result.get('grade_limit', .12))
        # Court values in diagnostic inputs are superseded only by the exact
        # atomic datum now bound in the native addendum.
        fixed_courts = [dict(r, plane_y_xz_m=[0, 0, request['selected_floor_y_m'][hid]])
                        for r in original.get('court_fixed_regions', [])]
        record = dict(original, id='PRIVATE_GROUP:' + hid, holding_ids=[hid], result=result,
                      court_fixed_regions=fixed_courts, source_profile=binding, activation=False)
        if 'vertical_risers' not in record:
            record['vertical_risers'] = original['result'].get('vertical_risers', [])
        name = 'profiles/' + hid.replace(':', '_') + '.json'
        write(name, record)
        rows.append(dict(id=record['id'], holding_ids=[hid], status='PASSED_FINITE_TRIANGLE_GRADE', **ref(HERE / name)))
        public.extend(record['public_fixed_regions'])
    write('private_profiles_summary_r02.json', dict(groups=rows, source_request=ref(REQUEST), activation=False))
    write('resolved_public_inputs_r01.json', dict(public_fixed_regions=public,
          source_request=ref(REQUEST), public_prerequisites=request['public_prerequisites']))
    write('atomic_rebind_binding_r01.json', dict(source_addendum=add_binding,
          exact_internal_routes=add['door_routes'], native_audit=add['native_audit'],
          superseded_proposed_native_ids=add['superseded_unactivated_source_native_ids'],
          explicit_deferred_source_placements=add['explicit_deferred_source_placements'],
          superseded_domain_handoffs=add['superseded_domain_handoffs'],
          profile_native_extensions=request['profile_native_extensions'], activation=False))
    print('Prepared final24 native sources and profiles', flush=True)

if __name__ == '__main__':
    run()
