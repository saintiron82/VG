"""Resolve unactivated fragment uses without inventing access or terrain.

The sealed paint and native packs are evidence, never mutation targets.
"""
from . import geometry as g
from .activate_backlands_subset import MaskIndex, SCENE
from .coherent_bulk import nearest_road
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import Counter
import math, time

OUT = g.HERE / 'backland_completion_r01/ground_margin_closure_r01'

def area(ps): return sum(g.geo.polygon_area(p) for p in ps)

def partition(ps, masks, index):
    reserved, free = [], []
    for p in ps:
        remaining = [p]
        for j in sorted(index.index.candidates(p)):
            m = masks[j]; left = []
            for t in remaining:
                q = a.clip(t, m['polygon_xz_m'])
                if not q or g.geo.polygon_area(q) <= 1e-8:
                    left.append(t); continue
                reserved.append(dict(owner_id=m['id'], kind=m['kind'], polygon_xz_m=q))
                left += a.common.subtract([t], [m['polygon_xz_m']])
            remaining = left
            if not remaining: break
        free += remaining
    return reserved, free

def source_planes(ps, index):
    pieces, gaps = [], []
    for p in ps:
        q = a.audit_polygon(index, p, None, grade_limit=math.inf)
        pieces += q['source_pieces']
        gaps += a.common.subtract([p], [s['polygon_xz_m'] for s in q['source_pieces']])
    return pieces, gaps

def run():
    start = time.monotonic(); OUT.mkdir(exist_ok=True)
    back = g.HERE / 'backland_completion_r01'; planpath = g.CITY / 'registered_source/plan.json'
    plan = g.load(planpath); roads = plan['roads']
    legacy_path = back / 'access_handoff_final.json'; legacy = g.load(legacy_path)['held_owner_routes']
    allocation_path = back / 'ground_owner_allocation.json'; allocation = g.load(allocation_path)
    owners = {r['id']: r for r in allocation['owners']}
    native_path = back / 'phase02_ownership_correction_r01/resolved_placements_r02.json'; native = g.load(native_path)
    material_path = back / 'terrain_handoff.json'; materials = g.load(material_path)
    matids = {r['id'] for r in materials['material_owners']}
    fixturecounts = Counter(p['ground_owner_id'] for p in native['placements'])
    match_path = g.CITY / 'traversal_r5/revisions/r06_r8_precinct/public_network_r18_r01/legacy_backland_owner_route_matches_r02.json'
    matches = {r['legacy_owner_id']: r for r in g.load(match_path)['rows']}
    maskpath = back / 'phase02_ownership_correction_r01/reservation_snapshot.json'
    masks = list(g.load(maskpath)['reservations']); refs = [g.ref(maskpath)]
    terr = g.CITY / 'registered_topography/revisions/r17_district_batches'
    for folder in ['contour_bulk_r01', 'coherent_batch18_r01', 'coherent_batch20_r01']:
        p = terr / folder / 'physical_owner_handoff_r02.json'; refs.append(g.ref(p))
        masks += [dict(id=r['id'], kind='PRIVATE_PHYSICAL_OWNER', polygon_xz_m=r['polygon_xz_m']) for r in g.load(p)['physical_earth_owners']]
    addendum_path = g.HERE / 'next20_source_addendum_r01/atomic_source_addendum.json'; refs.append(g.ref(addendum_path))
    for r in g.load(addendum_path)['records']:
        h = r['replacement_holding']
        masks += [dict(id=h['id'], kind='REVISED_PRIVATE20_HOLDING_OR_ENTRY', polygon_xz_m=p) for p in [h['holding_polygon_xz_m']] + h['external_route_polygons_xz_m']]
    # No reassignment of precinct/estate source ownership, even where its native
    # realization is later than the base scene.
    for r in plan['spaces'] + plan['plots']:
        masks += [dict(id=r['id'], kind='PROTECTED_PRECINCT_OR_ESTATE', polygon_xz_m=p) for p in g.triangulate(r['polygon_xz_m'])]
    mi = MaskIndex(masks)
    basepath = g.CITY / 'registered_integration/r8/coverage_plan/baseline_masks.npz'
    apath = back / 'allocation_masks.npz'; base = g.np.load(basepath); alloc = g.np.load(apath)
    bounds = base['bounds'].tolist(); pitch = float(base['pitch']); g.GRID=pitch; g.BOUNDS=bounds
    g.NZ,g.NX=base['block_labels'].shape;g.SHAPE=(g.NZ,g.NX);g.XS=bounds[0]+(g.np.arange(g.NX)+.5)*pitch;g.ZS=bounds[1]+(g.np.arange(g.NZ)+.5)*pitch
    blockpath = g.CITY / 'registered_integration/r8/coverage_plan/baseline_blocks.json'; blocks = g.load(blockpath)['blocks']
    rem = alloc['residual'] & (alloc['allocation'] == 0); small = []
    for bi,b in enumerate(blocks, 1):
        labels,n = g.ndimage.label(rem & (base['block_labels'] == bi))
        for j in range(1,n+1):
            zz,xx = g.np.where(labels==j); count=len(xx)
            if count >= 25: continue
            m=labels==j; ps=g.parts(m); center=[float(g.XS[xx].mean()),float(g.ZS[zz].mean())]
            road=min(roads,key=lambda r:nearest_road(center,r)[0]); ev=nearest_road(center,road)
            small.append(dict(id=b['block_id']+f':SMALL_GROUND_MARGIN:{j:04}',block_id=b['block_id'],source_polygons_xz_m=ps,source_area_m2=count*pitch*pitch,representative_point_xz_m=center,nearest_named_public_road=road['id'],nearest_road_centerline_point_xz_m=ev[3],nearest_road_centerline_distance_m=ev[0],nearest_road_half_width_m=road['width_m']/2))
    assert sum(r['source_area_m2'] for r in small)==2507
    windows=[p for r in legacy for p in owners[r['id']]['polygon_parts_xz_m']]+[p for r in small for p in r['source_polygons_xz_m']]
    scene=g.load(SCENE); index=a.TriangleIndex(scene,windows); out=[]; sums=Counter()
    for entry in legacy:
        oid=entry['id']; old=owners[oid]; ps=old['polygon_parts_xz_m']; assert oid not in matids and fixturecounts[oid]==0
        reserved,free=partition(ps,masks,mi); pieces,gaps=source_planes(free,index)
        q=old['representative_point_xz_m']; road=min(roads,key=lambda r:nearest_road(q,r)[0]); rd=nearest_road(q,road)
        matched=matches[oid]; steep=[s for s in pieces if math.hypot(*s['plane_y_xz_m'][:2])>.12+1e-7]
        value=dict(id=oid,superseded_source_function=old['planned_function'],named_adjacent_owner=old['named_owner'],block_id=old['block_id'],source_area_m2=old['area_m2'],source_polygons_xz_m=ps,
          disposition='NONPUBLIC_DRAINAGE_AND_CLEARANCE_MARGIN',design_reason='This small residual fragment has no active functional paint, native fixture, gate or enclosure assignment. Replace the unimplemented generic yard/garden claim with an intentionally open nonwalking soil and drainage margin attached to the named adjacent owner.',
          reserved_priority_regions=reserved,retained_source_plane_regions=pieces,retained_source_holes_xz_m=gaps,measured_steep_source_area_m2=area([s['polygon_xz_m'] for s in steep]),
          nearest_named_public_road=road['id'],nearest_public_centerline_point_xz_m=rd[3],nearest_public_centerline_distance_m=rd[0],
          matched_owner_route_ids=[v['id'] for v in matched['matched_holding_root_routes']],owner_root_match_status=matched['classification'],
          active_material_owner=False,active_native_instances=0,new_native_instances=0,new_material_or_terrain_edits=0,new_public_or_private_route_claim=False,
          access_obligation_disposition='WITHDRAW_UNIMPLEMENTED_OCCUPIED_YARD_CLAIM; RETAIN_EXISTING_NONWALKING_GROUND',
          access_reason='An owner root is not a spur proof. No new courtyard or user destination is claimed on this fragment, so no separate traversable entrance is required. Any future productive or occupied use must reopen the explicit access gate.',
          preserved_original_failure=entry,implementation_tier='exterior_only')
        err=abs(old['area_m2']-area([p['polygon_xz_m']for p in reserved+pieces])-area(gaps));assert err<1e-5,(oid,err);value['area_partition_error_m2']=err;out.append(value)
        sums['legacy_area_m2']+=old['area_m2'];sums['legacy_reserved_priority_area_m2']+=area([p['polygon_xz_m']for p in reserved]);sums['legacy_existing_source_ground_area_m2']+=area([p['polygon_xz_m']for p in pieces]);sums['legacy_existing_hole_area_m2']+=area(gaps)
    for r in small:
        reserved,free=partition(r['source_polygons_xz_m'],masks,mi);pieces,gaps=source_planes(free,index)
        near=r['nearest_road_centerline_distance_m']-r['nearest_road_half_width_m']<=3
        r.update(disposition='PUBLIC_ROAD_DRAINAGE_AND_VISIBILITY_MARGIN' if near else 'NONPUBLIC_TERRAIN_DRAINAGE_MARGIN',named_function_owner=r['nearest_named_public_road'] if near else r['block_id']+':TERRAIN_MAINTENANCE',reserved_priority_regions=reserved,retained_source_plane_regions=pieces,retained_source_holes_xz_m=gaps,public_traversal_claim=False,new_native_instances=0,new_material_or_terrain_edits=0,boundary_policy='INTENTIONALLY_OPEN; NO_FRAGMENT_FENCES',height_policy='PRESERVE_EVERY_EXISTING_SOURCE_PLANE_AND_BANK')
        err=abs(r['source_area_m2']-area([p['polygon_xz_m']for p in reserved+pieces])-area(gaps));assert err<1e-5,(r['id'],err);r['area_partition_error_m2']=err
        sums['small_reserved_priority_area_m2']+=area([p['polygon_xz_m']for p in reserved]);sums['small_existing_source_ground_area_m2']+=area([p['polygon_xz_m']for p in pieces]);sums['small_existing_hole_area_m2']+=area(gaps)
    report=dict(schema='riverstone.ordinary_ground_margin_closure.v1',status='SOURCE_FUNCTIONS_EXPLICIT_NO_NEW_ACCESS_OR_TERRAIN_CLAIM',sources=dict(original_legacy_access=g.ref(legacy_path),original_allocation=g.ref(allocation_path),selected_native835=g.ref(native_path),sealed_material_owners=g.ref(material_path),catalog_match_evidence=g.ref(match_path),original_grid=g.ref(basepath),allocation_masks=g.ref(apath),blocks=g.ref(blockpath),source_plan=g.ref(planpath),actual_source_scene=g.ref(SCENE),reservations=refs,author=g.ref(__file__)),legacy_fragment_dispositions=out,small_fragment_dispositions=small,summary=dict(legacy_fragments=29,legacy_named_owner_root_matches=sum(bool(r['matched_owner_route_ids'])for r in out),legacy_active_material_owners=0,legacy_active_native_instances=0,legacy_occupied_courtyard_claims_withdrawn=29,unexplained_legacy_access_obligations=0,small_fragments=len(small),small_fragment_area_m2=2507,remaining_unlabelled_small_fragments=0,new_terrain_or_native_geometry=0,area_accounting_m2=dict(sums),maximum_partition_error_m2=max(r['area_partition_error_m2']for r in out+small),seconds=time.monotonic()-start),limits=['This closes source function labels, not final integrated traversal acceptance.','No accepted owner root is substituted for a missing backland spur.','The preserved original failed searches remain evidence; future occupied uses require a new explicit access design.','Every current protected owner keeps priority. Existing terrain, material, native support holes and bank faces remain unchanged.'])
    g.write(OUT/'source_plan.json',report)
    lines=['# Small ground margins and legacy access closure','', 'All 29 legacy backland access failures belong to unactivated source fragments. None is in the 440 material owners or selected 835 native instances. Their old generic occupied-yard/garden labels are withdrawn and replaced by finite nonpublic drainage and clearance margins. Fifteen named owners have catalog roots; these are not treated as backland spur proofs.','',f"The original grid's {len(small)} fragments below 25 m² total exactly 2,507 m². Each now belongs to a named nearby road margin or its block's terrain-maintenance ground. Current protected reservations retain exact priority. No geometry, paint, fences or access claims are added.",'']
    for r in out:lines += [f"- {r['id']}: {r['source_area_m2']} m², nonpublic drainage/clearance margin; adjacent owner {r['named_adjacent_owner']}; {len(r['matched_owner_route_ids'])} exact owner roots, no spur claim."]
    lines+=['','The original failed route search is preserved for every legacy ID. A future courtyard, storage, garden or other occupied use must reopen its explicit access requirement. Final city traversal still requires the integrated-scene checks.']
    (OUT/'dispositions.md').write_text('\n'.join(lines)+'\n');g.write(OUT/'manifest.json',dict(plan=g.ref(OUT/'source_plan.json'),readable=g.ref(OUT/'dispositions.md'),summary=report['summary']));print(report['summary'],flush=True);print(g.ref(OUT/'source_plan.json'),flush=True)

if __name__=='__main__':run()
