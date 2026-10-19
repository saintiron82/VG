"""Bind the exact twenty-holding native addendum, including cancelled panels."""
import json
from .screen import HERE, write
from .. import author as a
SOURCE = HERE.parent / 'coherent_batch18_r01'
ADDENDUM = a.CITY / 'assemblies/ordinary/registered/district_fabric_r01/next20_source_addendum_r01/atomic_source_addendum.json'
ADDENDUM_SHA = 'fa9063a5ee2c650891df403be1439a412002c9049b76de6bb930fb7132920e80'
REQUEST = HERE.parent / 'public_dependency_review_r01/next20_atomic_rebind_request_r01.json'

def run():
    assert a.sha(ADDENDUM) == ADDENDUM_SHA
    add = json.loads(ADDENDUM.read_bytes())
    req = json.loads(REQUEST.read_bytes())
    assert add['status'] == 'ATOMIC_SOURCE_READY_FOR_R17_COMPOSITION'
    audit_path = a.ROOT / add['native_audit']['path']
    assert a.sha(audit_path) == add['native_audit']['sha256']
    assert json.loads(audit_path.read_bytes())['passed']
    selected = set(req['matched_next_batch_holding_ids'])
    assert selected == set(add['matched_next_batch_holding_ids'])
    records = {r['holding_id']: r for r in add['records']}
    assert set(records) == selected and all(r['passed'] for r in records.values())
    layout = json.loads((SOURCE / 'effective_source_layout_r03.json').read_bytes())
    prepared = json.loads((SOURCE / 'effective_prepared_parcels_r03.json').read_bytes())
    pack = json.loads((SOURCE / 'prepared_native_pack_r03.json').read_bytes())

    def replace_by_holding(original, replacement):
        # Entire selected lists are authoritative, so removed boundary panels
        # cannot survive merely because they are absent from a per-ID lookup.
        kept = [r for r in original if r.get('holding_id') not in selected]
        result = kept + replacement
        assert len({r['id'] for r in result}) == len(result)
        return result

    for obj in (layout, pack):
        obj['placements'] = replace_by_holding(obj['placements'], add['placements'])
        obj['actual_doors'] = replace_by_holding(obj['actual_doors'], add['actual_doors'])
    layout['holdings'] = [records[h['id']]['replacement_holding'] if h['id'] in selected else h for h in layout['holdings']]
    prepared['parcels'] = [records[h['id']]['replacement_terrain_parcel'] if h['id'] in selected else h for h in prepared['parcels']]
    prepared['native_earth_bearings'] = replace_by_holding(prepared['native_earth_bearings'], add['native_earth_bearings'])
    pack['assets'].update(add['assets'])
    source_ref = dict(path=str(ADDENDUM.relative_to(a.ROOT)), sha256=ADDENDUM_SHA)
    for obj in (layout, prepared, pack):
        obj.setdefault('source_references', []).append(source_ref)
    cancelled = set(add['superseded_proposed_native_ids'])
    assert not cancelled & {r['id'] for r in layout['placements']}
    assert set(add['retired_source_ids']) == set(req['exact_retirement_ids'])
    write('effective_source_layout_r03.json', layout)
    write('effective_prepared_parcels_r03.json', prepared)
    write('prepared_native_pack_r03.json', pack)
    write('atomic_rebind_binding_r01.json', dict(source_addendum=source_ref, native_audit=add['native_audit'],
          selected_holding_ids=sorted(selected), exact_internal_routes=add['door_routes'],
          superseded_proposed_native_ids=sorted(cancelled), boundary_opening_ledger=add['boundary_opening_ledger'],
          unchanged_other_native_records=True, activation=False))
    print('Bound', len(selected), 'holdings;', len(add['placements']), 'native placements;', len(cancelled), 'cancelled boundary panels', flush=True)

if __name__ == '__main__':
    run()
