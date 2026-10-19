"""One finite final24 owner partition, including explicit native step holes."""
import json,time
from .prepare import HERE, REQUEST, ref, load, write
from .. import author as a
from ...r01_ownership import author as ownership
from ...public_corridors_r18 import public_domain

def run():
    start = time.monotonic()
    request = json.loads(REQUEST.read_bytes())
    selected = set(request['matched_next_batch_holding_ids'])
    existing = set(request['already_sealed_holding_ids'])
    prep = json.loads((HERE / 'effective_prepared_parcels_r03.json').read_bytes())
    layout = json.loads((HERE / 'effective_source_layout_r03.json').read_bytes())
    pack = json.loads((HERE / 'prepared_native_pack_r03.json').read_bytes())
    groups = json.loads((HERE / 'private_profiles_summary_r02.json').read_bytes())['groups']
    assert {h for g in groups for h in g['holding_ids']} == selected
    public = []
    for road in json.loads(a.PLAN_PATH.read_bytes())['roads']:
        public.extend(ownership.corridor(road['polyline_xz_m'], road['width_m']))
    public.extend(r['polygon_xz_m'] for r in public_domain.records() if r['kind'] == 'bounded_retained_junction_extension')
    profiles = [(g, load(g)) for g in groups]
    public_fixed = [r for g, d in profiles for r in d['public_fixed_regions']]
    # Actual private cuts remain below the current finite public ownership,
    # including institutional/water approaches outside the old traffic plan.
    public.extend(r['polygon_xz_m'] for r in public_fixed)
    pi = a.geo._SpatialIndex(8)
    for i, p in enumerate(public):
        pi.add(i, p)
    def private(poly):
        return a.common.subtract([poly], [public[i] for i in sorted(pi.candidates(poly))])
    rows, physical, holes, profile_masks, cut_masks, risers = [], [], [], [], [], []
    def add(identifier, poly, kind, floor, material, hid):
        for j, p in enumerate(private(poly)):
            row = dict(id=identifier + ':' + str(j), holding_id=hid, kind=kind,
                       polygon_xz_m=p, plane_y_xz_m=[0, 0, floor], action='field', material=material)
            rows.append(row)
            physical.append(row)
    for parcel in prep['parcels']:
        if parcel['id'] not in selected:
            continue
        for j, p in enumerate(parcel['footing_polygons_xz_m']):
            holes.append(dict(id=parcel['id'] + ':NATIVE:' + str(j), holding_id=parcel['id'],
                              action='hole', kind='native_footing', polygon_xz_m=p))
    step_extensions = [load(r) for r in request['profile_native_extensions']]
    for ext in step_extensions:
        for j, p in enumerate(ext['terrain_top_exclusion_polygons_xz_m']):
            holes.append(dict(id='BLOCK_001:R8_C003:STEP_COLUMN:' + str(j), holding_id='BLOCK_001:R8_C003',
                              action='hole', kind='variable_height_native_step_column', polygon_xz_m=p))
    for group, d in profiles:
        hid = group['holding_ids'][0]
        profile_masks.extend(d['private_domain_polygons_xz_m'])
        cut_masks.extend(d['private_domain_polygons_xz_m'])
        risers.extend(dict(r, holding_id=hid) for r in d.get('vertical_risers', []))
        for j, tri in enumerate(d['result']['triangles']):
            row = dict(id=group['id'] + ':PROFILE:' + str(j), holding_id=hid, kind='private_shared_profile',
                       polygon_xz_m=tri['polygon_xz_m'], plane_y_xz_m=tri['plane_y_xz_m'], action='field',
                       material='ground_stone', gradient=tri['gradient'])
            rows.append(row)
            physical.append(row)
    partitions = request['explicit_flat_profile_margin_partitions']
    for parcel in prep['parcels']:
        hid = parcel['id']
        if hid not in selected:
            continue
        flat = partitions.get(hid, {}).get('flat_owner_polygons_xz_m', parcel['whole_holding_polygons_xz_m'])
        floor = request['selected_floor_y_m'][hid]
        cut_masks.extend(flat)
        for key, kind, material in [('walk_polygons_xz_m', 'private_internal_walking', 'ground_stone'),
                                    ('court_polygons_xz_m', 'functional_court', 'ground_earth')]:
            for j, p in enumerate(parcel[key]):
                for k, mask in enumerate(flat):
                    q = a.clip(p, mask)
                    if q:
                        add(hid + ':' + kind + ':' + str(j) + ':' + str(k), q, kind, floor, material, hid)
        for j, p in enumerate(flat):
            add(hid + ':FLAT:' + str(j), p, 'coherent_flat_core', floor, 'ground_earth', hid)
    records = [r for r in prep['retirement_records'] if set(r['affected_holding_ids']) & selected]
    assert all(set(r['affected_holding_ids']) <= selected | existing for r in records)
    assert {r['source_id'] for r in records} == set(request['exact_retirement_ids'])
    for r in records:
        add(r['source_id'] + ':RESIDUAL', r['old_body_polygon_xz_m'], 'retired_private_floor_restoration',
            r['old_finished_floor_y_m'], 'ground_earth', None)
        cut_masks.append(r['old_body_polygon_xz_m'])
    cut_masks.extend(r['polygon_xz_m'] for r in holes)
    cut_masks = [q for p in cut_masks for q in private(p)]
    def partition(source, prior=()):
        idx = a.geo._SpatialIndex(2)
        masks = list(prior)
        result = []
        for i, p in enumerate(masks):
            idx.add(i, p)
        for r in source:
            if r['kind'] != 'private_shared_profile':
                continue
            p = r['polygon_xz_m']
            for j, q in enumerate(a.common.subtract([p], [masks[i] for i in sorted(idx.candidates(p))])):
                result.append(dict(r, id=r['id'] + ':PART:' + str(j), polygon_xz_m=q))
        for p in profile_masks:
            idx.add(len(masks), p)
            masks.append(p)
        for r in source:
            if r['kind'] == 'private_shared_profile':
                continue
            p = r['polygon_xz_m']
            for j, q in enumerate(a.common.subtract([p], [masks[i] for i in sorted(idx.candidates(p))])):
                result.append(dict(r, id=r['id'] + ':PART:' + str(j), polygon_xz_m=q))
            idx.add(len(masks), p)
            masks.append(p)
        return result
    print('Partitioning final24', len(rows), 'owners;', len(holes), 'native masks', flush=True)
    render = partition(rows, [r['polygon_xz_m'] for r in holes])
    logical = partition(physical)
    poses = [p for p in pack['placements'] if p['holding_id'] in selected]
    doors = [p for p in pack['actual_doors'] if p['holding_id'] in selected]
    assets = dict(pack['assets'])
    for ext in step_extensions:
        poses.extend(ext['placements'])
        assets.update(ext['assets'])
    used = {p['asset_key'] for p in poses}
    sources = [ref(HERE / n) for n in ('effective_source_layout_r03.json', 'effective_prepared_parcels_r03.json',
               'prepared_native_pack_r03.json', 'private_profiles_summary_r02.json')] + [ref(REQUEST)]
    out = dict(schema='riverstone.r17.physical_owner_handoff.v1', status='FINAL24_TOP_AND_LOCAL_SIDE_ACCEPTANCE_PENDING',
        base_scene=dict(path=str(a.SCENE_PATH.relative_to(a.ROOT)), sha256=a.SCENE_SHA256), source_references=sources,
        accepted_holding_ids=sorted(selected), already_sealed_holding_ids=sorted(existing), held_holding_ids=[],superseded_protected_domains=request['superseded_protected_domains'],
        native_holes=holes, rendered_plane_owners=render, physical_earth_owners=logical,
        public_fixed_regions=public_fixed, retirement_records=records,
        native_earth_bearings=[r for r in prep['native_earth_bearings'] if r['holding_id'] in selected],
        profile_native_extensions=request['profile_native_extensions'], explicit_profile_risers=risers,
        preserved_surface_following_margins={h: p['surface_following_margin_polygons_xz_m'] for h,p in partitions.items()},
        summary=dict(holdings=len(selected), native_instances=len(poses), actual_doors=len(doors),
                     retired_ids=len(records), native_holes=len(holes), rendered_plane_owners=len(render),
                     physical_earth_owners=len(logical), elapsed_s=time.monotonic()-start), activation=False)
    write('physical_owner_handoff_r02.json', out)
    write('compact_cut_domains_r01.json', dict(polygons_xz_m=cut_masks, source_handoff_sha256=a.sha(HERE/'physical_owner_handoff_r02.json')))
    native = dict(pack, assets={k: assets[k] for k in used}, placements=poses, actual_doors=doors,
        replaced_placement_ids=sorted(request['exact_retirement_ids']),
        retired_foundation_proxy_ids=[r['removed_foundation_proxy_id'] for r in records],
        accepted_holding_ids=sorted(selected), profile_native_extensions=request['profile_native_extensions'],
        terrain_handoff=ref(HERE/'physical_owner_handoff_r02.json'), status=out['status'])
    write('native_pack_ready_r02.json', native)
    print(out['summary'], flush=True)

if __name__ == '__main__':
    run()
