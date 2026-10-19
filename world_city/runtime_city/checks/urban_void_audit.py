#!/usr/bin/env python3
"""Read-only, stdlib spatial inventory of assigned and residual urban land.

The output is a planning diagnosis, never approval to fill a space. Areas are
cell-centre raster estimates. Residual region cells additionally exclude a
half-diagonal buffer around every assignment, so narrow access ribbons cannot
disappear between samples. Bounding boxes are locators, not proposed parcels.
"""
import argparse
from array import array
from collections import Counter, deque
import hashlib
import importlib.util
import json
import math
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('revision2_void_helpers', Path(__file__).with_name('revision2.py'))
r2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r2)
g = r2.g

CATEGORIES = [
    'building_envelopes', 'public_road_ribbons', 'compiled_road_surfaces',
    'market_square', 'castle_cathedral_precincts', 'remaining_reserved_courtyards',
    'explicit_property_grounds', 'original_plot_grounds', 'named_garden_or_orchard',
    'institutional_cemetery_or_garden', 'fabric_envelopes', 'wall_envelopes',
    'river_reservation', 'access_reservations', 'other_named_site_grounds',
]
BITS = {name: 1 << i for i, name in enumerate(CATEGORIES)}
PHYSICAL = sum(BITS[k] for k in ('building_envelopes', 'compiled_road_surfaces',
    'market_square', 'castle_cathedral_precincts', 'fabric_envelopes', 'wall_envelopes', 'river_reservation'))


def halfplanes(poly):
    if not g.is_convex_polygon(poly):
        raise ValueError('Raster requires a valid convex polygon; no convex-hull substitution is allowed')
    orient = 1 if g.signed_polygon_area(poly) > 0 else -1
    result = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dz)
        result.append((-orient * dz / n, orient * dx / n, orient * (dz*a[0] - dx*a[1]) / n))
    return result


def contains(point, planes, buffer=0):
    return all(a*point[0] + b*point[1] + c >= -buffer - 1e-9 for a, b, c in planes)


def bounds(poly):
    return [[min(p[i] for p in poly) for i in (0, 1)], [max(p[i] for p in poly) for i in (0, 1)]]


def load_geometries(scene, fabric, plan, root):
    """Read actual vertices for every used building/fabric/road/wall resource."""
    records, cache = [], {}
    def add(category, identity, polygon):
        if polygon:
            records.append({'category': category, 'id': identity, 'polygon': polygon, 'planes': halfplanes(polygon)})
    def actual(asset):
        result = []
        for _, res in r2._resources(asset):
            path = res['render_path']
            if path not in cache:
                raw = (root / path).read_bytes()
                cache[path] = (r2.mesh_vertex_bounds(json.loads(raw)), hashlib.sha256(raw).hexdigest())
            result.append(cache[path][0])
        if not result:
            raise ValueError('Missing compiled render resource')
        return r2.union_bounds(result)
    for inst in scene['instances']:
        add('building_envelopes', inst['id'], g.transformed_aabb_xz_m(actual(scene['assets'][inst['asset_key']]), inst['position_m'], inst['yaw_rad']))
    for inst in fabric['placements']:
        add('fabric_envelopes', inst['id'], g.transformed_aabb_xz_m(actual(fabric['assets'][inst['asset_key']]), inst['position_m'], inst.get('yaw_rad', math.radians(inst.get('yaw_deg', 0)))))
    for inst in scene['infrastructure']['placements']:
        cat = inst['category']
        if cat not in ('wall', 'road', 'road_join_draw_only', 'bridge', 'dock', 'dock_connector'):
            continue
        add('wall_envelopes' if cat == 'wall' else 'compiled_road_surfaces', inst['id'],
            g.transformed_aabb_xz_m(actual(scene['infrastructure']['assets'][inst['asset_key']]), inst['position_m'], math.radians(inst.get('yaw_deg', 0))))
    nodes = {n['id']: [n['position_m'][0], n['position_m'][2]] for n in plan['road_nodes']}
    for road in plan['roads']:
        if road['kind'] == 'wall_walk' or road.get('route_id') == 'WALL_ACCESS':
            continue
        add('public_road_ribbons', road['id'], g.road_ribbon(nodes[road['from_node']], nodes[road['to_node']], road['width_m']))
    repurposed = set(fabric['repurposed_courtyard_plot_ids'])
    for plot in plan['plots']:
        add('original_plot_grounds', plot['id'], plot['footprint_xz_m'])
        if plot.get('courtyard_xz_m') and plot['id'] not in repurposed:
            add('remaining_reserved_courtyards', plot['id'], plot['courtyard_xz_m'])
    for prop in fabric['properties']:
        add('explicit_property_grounds', prop['id'], prop['footprint_xz_m'])
    for rec in fabric['vegetation_land_use']:
        add('named_garden_or_orchard', rec['id'], rec['footprint_xz_m'])
    for rec in fabric['institutional_grounds']:
        add('institutional_cemetery_or_garden', rec['id'], rec['footprint_xz_m'])
    for feat in plan['site_features']:
        cat = {'market_square': 'market_square', 'precinct': 'castle_cathedral_precincts',
               'garden_reservation': 'named_garden_or_orchard'}.get(feat['kind'], 'other_named_site_grounds')
        add(cat, feat['id'], feat.get('footprint_xz_m'))
    for res in fabric['access_reservations']:
        for j, poly in enumerate(r2._ribbons(res['polyline_xz_m'], res['width_m'])):
            add('access_reservations', res['id'] + ':' + str(j), poly)
    river = plan['river_reservation']
    for j, poly in enumerate(r2._ribbons(river['centerline_xz_m'], river['width_candidate_m'])):
        add('river_reservation', str(j), poly)
    return records, cache


def raster_inventory(records, wall, resolution):
    low, high = bounds(wall)
    origin = [math.floor(v / resolution)*resolution for v in low]
    nx, nz = [math.ceil((high[i] - origin[i])/resolution) for i in (0, 1)]
    count = nx*nz
    masks = array('I', [0])*count
    guarded = bytearray(count)
    inside = bytearray(count)
    interior = bytearray(count)
    wp = halfplanes(wall)
    radius = resolution / math.sqrt(2)
    for iz in range(nz):
        z = origin[1] + (iz + .5)*resolution
        for ix in range(nx):
            point = [origin[0] + (ix + .5)*resolution, z]
            n = iz*nx + ix
            inside[n] = contains(point, wp)
            interior[n] = contains(point, wp, -radius)
    for rec in records:
        low, high = bounds(rec['polygon'])
        xmin, zmin = [max(0, math.floor((low[i] - radius - origin[i])/resolution)) for i in (0, 1)]
        xmax, zmax = [min((nx, nz)[i]-1, math.floor((high[i] + radius - origin[i])/resolution)) for i in (0, 1)]
        bit, planes = BITS[rec['category']], rec['planes']
        for iz in range(zmin, zmax+1):
            z = origin[1] + (iz+.5)*resolution
            for ix in range(xmin, xmax+1):
                n = iz*nx+ix
                if not inside[n]:
                    continue
                point = [origin[0] + (ix+.5)*resolution, z]
                if contains(point, planes):
                    masks[n] |= bit
                if not guarded[n] and contains(point, planes, radius):
                    guarded[n] = 1
    sums = Counter()
    for n, m in enumerate(masks):
        if not inside[n]:
            continue
        for cat, bit in BITS.items():
            if m & bit:
                sums[cat] += 1
        sums['assigned_union'] += bool(m)
        sums['physical_envelope_or_surface_union'] += bool(m & PHYSICAL)
        sums['assigned_open_not_physical_envelope_or_surface'] += bool(m) and not (m & PHYSICAL)
        sums['unassigned_cell_centres'] += not m
        sums['strict_unassigned_full_cells'] += bool(interior[n] and not guarded[n])
    area = resolution**2
    totals = {k: round(v*area, 3) for k, v in sums.items()}
    totals['wall_interior_sampled'] = sum(inside)*area
    return {'resolution': resolution, 'origin': origin, 'nx': nx, 'nz': nz, 'masks': masks,
            'inside': inside, 'strict': bytearray(int(interior[n] and not guarded[n]) for n in range(count)), 'areas_m2': totals}


def components(grid):
    nx, nz, todo = grid['nx'], grid['nz'], bytearray(grid['strict'])
    result = []
    for seed in range(len(todo)):
        if not todo[seed]:
            continue
        todo[seed] = 0
        queue, cells = deque([seed]), []
        while queue:
            n = queue.popleft()
            cells.append(n)
            x, z = n % nx, n // nx
            for m in ([n-1] if x else []) + ([n+1] if x+1 < nx else []) + ([n-nx] if z else []) + ([n+nx] if z+1 < nz else []):
                if todo[m]:
                    todo[m] = 0
                    queue.append(m)
        result.append(cells)
    return sorted(result, key=len, reverse=True)


def suggest(district):
    return {
        'D01': 'Survey the castle approach and retaining slope first; then assign service gardens or military yards only on verified buildable terraces. Do not disguise the unimplemented 52 m terrain candidate with scatter.',
        'D02': 'Extend a bounded cathedral cemetery, clerical garden or service close with a legible processional approach; keep the existing cathedral precinct intact.',
        'D03': 'Define inn/service courts and narrow rear plots at the market edge, retaining the named square and civic access; do not treat the entire clearing as extra plaza.',
        'D04': 'Subdivide merchant backlands into warehouse/loading courts, stable/service strips and a few coherent garden/manor holdings connected to existing streets.',
        'D05': 'Define warehouse cart-turning/loading courts and timber storage yards; investigate bank/flood levels before any new structure.',
        'D06': 'Subdivide workshop backlands into shared work yards and limited service infill; preserve fire separation and explicit service alleys.',
        'D07': 'Subdivide the oversized block interior into deep rear yards, shared service courts and connected narrow alleys; consider bounded attached-row or workshop infill only after parcel/access design.',
        'D08': 'Assign long productive garden strips, orchard holdings and occasional coherent timber/manor gardens with low boundaries and field-edge lanes.',
        'D10': 'Extend the charitable/monastic holding with bounded kitchen/herb gardens, service courts and, if authored, a small burial ground; preserve visitor access.',
    }.get(district, 'Author an explicit parcel and access plan before deciding a land use.')


def region_record(cells, grid, plan, rank):
    nx, res, origin = grid['nx'], grid['resolution'], grid['origin']
    xs, zs = [n % nx for n in cells], [n // nx for n in cells]
    centroid = [origin[0]+(sum(xs)/len(xs)+.5)*res, origin[1]+(sum(zs)/len(zs)+.5)*res]
    rep = min(cells, key=lambda n: (origin[0]+(n%nx+.5)*res-centroid[0])**2+(origin[1]+(n//nx+.5)*res-centroid[1])**2)
    point = [origin[0]+(rep%nx+.5)*res, origin[1]+(rep//nx+.5)*res]
    buildings = []
    for b in plan['building_plans']:
        if b['district_id'] in ('D09', 'S01'):
            continue
        poly = b['footprint_xz_m']
        center = [sum(p[i] for p in poly)/len(poly) for i in (0, 1)]
        buildings.append((math.dist(point, center), b))
    nearest = sorted(buildings, key=lambda x: x[0])[:12]
    district_counts = Counter(b['district_id'] for _, b in nearest)
    district = district_counts.most_common(1)[0][0]
    anchor = min((d for d in plan['districts'] if d['id'] not in ('D09','S01')), key=lambda d: math.dist(point,d['anchor_xz_m']))
    box = [[origin[0]+min(xs)*res, origin[1]+min(zs)*res], [origin[0]+(max(xs)+1)*res, origin[1]+(max(zs)+1)*res]]
    # Run-length encoding supplies the actual irregular region without pretending
    # that its bounding rectangle is available for construction.
    rows = {}
    for n in cells:
        rows.setdefault(n//nx, []).append(n%nx)
    runs = []
    for iz in sorted(rows):
        ordered = sorted(rows[iz]); start = end = ordered[0]
        for ix in ordered[1:]:
            if ix == end+1:
                end = ix
            else:
                runs.append([iz, start, end]); start = end = ix
        runs.append([iz, start, end])
    edge_distance = min(g.point_segment_distance(point, a, b) for a,b in zip(plan['wall_outline_xz_m'], plan['wall_outline_xz_m'][1:]+plan['wall_outline_xz_m'][:1]))
    advice = suggest(district)
    qualifier = 'Nearby source-building attribution, not a legally or geometrically bounded district.'
    # Explicit geographic qualifiers are important for long connected backlands:
    # a representative-point vote must not imply one use for the entire region.
    if box[0][0] > 350 and box[0][1] < -400 and box[1][1] > 0:
        advice = 'Split the long eastern wall-side backland: bounded cathedral gardens/cemetery extension toward the north, workshop service holdings toward the south, and an explicit defensible wall-access strip. Establish access and terrain before any infill.'
        qualifier = 'Crosses cathedral, residential and craft vicinity; do not allocate the entire component from its D06 representative vote.'
    elif box[1][0] < -450 and box[0][1] < -300:
        advice = 'Separate the western defensive/possible castle-slope belt from lower old-town rear holdings. Author the slope/retaining and wall-access constraint first; use buildable lower parts for bounded gardens and subdivided service yards.'
        qualifier = 'D07 frontage beside D01/castle terrain candidate and western wall; slope remains unimplemented.'
    elif -550 <= point[0] <= -350 and -280 <= point[1] <= -120:
        advice = 'Resolve the castle-foot terrace/slope before infill; where buildable, subdivide old-town rear gardens and service courts with a connected alley to existing streets.'
        qualifier = 'D07 buildings border the unimplemented D01 castle-foot terrain transition.'
    elif anchor['id'] == 'D02' and point[1] < -350:
        advice = 'Extend productive northern garden/orchard holdings, with a distinct clerical garden or cemetery edge near the cathedral. Keep the existing named precinct and processional approach clear.'
    elif anchor['id'] == 'D08':
        advice = 'Subdivide the northern backland into long productive garden/orchard strips and coherent low-density holdings; use narrow alley/service-yard infill only on the older D07 frontage edge.'
    elif anchor['id'] == 'D10':
        advice = 'Subdivide old-town rear yards and a shared access alley, with an explicitly bounded charitable/monastic kitchen-garden holding along the D10 edge. Preserve existing courts and well access.'
    elif anchor['id'] == 'D02':
        advice = 'Define a transition south of the cathedral: clerical gardens/service courts on the precinct edge and subdivided residential/merchant rear plots below, connected by a legible rear lane.'
    return {'id': 'VOID_%02d' % rank, 'strict_cell_area_m2': len(cells)*res*res,
        'approximate_bounds_xz_m': box, 'representative_xz_m': point,
        'centroid_xz_m': [round(v,2) for v in centroid], 'district_hint': district,
        'nearest_anchor_district': anchor['id'], 'nearest_12_building_district_votes': dict(district_counts),
        'district_qualification': qualifier, 'representative_distance_to_wall_m': round(edge_distance,2),
        'nearest_source_buildings': [{'id': b['id'], 'district_id': b['district_id'], 'distance_to_representative_m': round(d,1)} for d,b in nearest],
        'suggested_use': advice, 'proposal_basis': 'canonical fictional city history and nearby source building functions, not a historical reconstruction',
        'row_runs_iz_ix_inclusive': runs, 'status': 'unassigned_to_every_geometric_layer_at_conservative_grid_resolution'}


def audit(scene, fabric, plan, root, resolution=2):
    records, resources = load_geometries(scene, fabric, plan, root)
    grid = raster_inventory(records, plan['wall_outline_xz_m'], resolution)
    coarse = raster_inventory(records, plan['wall_outline_xz_m'], resolution*2)
    groups = components(grid)
    regions = [region_record(cells, grid, plan, i+1) for i,cells in enumerate(groups[:10])]
    total = g.polygon_area(plan['wall_outline_xz_m'])
    market = next(f for f in plan['site_features'] if f['id'] == 'F_MARKET_OPEN')['footprint_xz_m']
    market_area = g.polygon_area(market)
    stalls = [r for r in records if r['category']=='fabric_envelopes' and r['id'].startswith('UF_MARKET_')]
    stall_area = sum(g.intersection_area(market, r['polygon']) for r in stalls)
    named = [{'id': f['id'], 'kind': f['kind'], 'area_m2': g.polygon_area(f['footprint_xz_m']),
              'bounds_xz_m': bounds(f['footprint_xz_m'])} for f in plan['site_features'] if f.get('footprint_xz_m')]
    areas = grid['areas_m2']
    exact_named = {
        'explicit_property_record_sum_m2_not_union': sum(g.polygon_area(p['footprint_xz_m']) for p in fabric['properties']),
        'institutional_grounds_record_sum_m2': sum(g.polygon_area(p['footprint_xz_m']) for p in fabric['institutional_grounds']),
        'outside_woodland_record_sum_m2': sum(g.polygon_area(p['footprint_xz_m']) for p in fabric['vegetation_land_use'] if p['land_use']=='outside_wall_woodland'),
    }
    return {'schema': 'riverstone.urban_void_audit.v1', 'status': 'planning_gaps_quantified_no_geometry_changed',
        'scope': 'r2 flat property scene plus repaired access overlay; pending r3 manor/forest geometry excluded',
        'method': {'grid_resolution_m': resolution, 'convergence_grid_resolution_m': resolution*2,
            'area_estimator': 'cell-centre samples clipped to wall interior; categories overlap, use union for totals',
            'component_estimator': '4-connected full cells; wall eroded and all assignments conservatively expanded by half cell diagonal',
            'component_assignment_buffer_m': resolution/math.sqrt(2), 'grid_origin_xz_m': grid['origin'],
            'grid_shape_x_z': [grid['nx'],grid['nz']], 'component_run_encoding': '[row_z, first_column_x, last_column_x], inclusive',
            'building_and_fabric_coverage': 'all-LOD actual compiled vertex AABB projections, conservative roof/envelope area rather than precise occupied ground or habitable area',
            'district_attribution': 'No district polygons exist. Majority of 12 nearest non-wall source buildings; nearest district anchor reported separately.'},
        'source_counts': {'buildings': len(scene['instances']), 'original_plots': len(plan['plots']), 'explicit_properties': len(fabric['properties']),
            'remaining_reserved_courtyards': len([p for p in plan['plots'] if p.get('courtyard_xz_m') and p['id'] not in set(fabric['repurposed_courtyard_plot_ids'])]),
            'compiled_resources_read': len(resources), 'polygon_records': len(records)},
        'wall_envelope_exact_m2': round(total,3), 'areas_m2': grid['areas_m2'],
        'exclusive_wall_interior_partition_m2': {
            'actual_building_road_wall_fabric_or_named_paved_surface': areas['physical_envelope_or_surface_union'],
            'assigned_open_ground_outside_those_envelopes': areas['assigned_open_not_physical_envelope_or_surface'],
            'unassigned_at_cell_centres': areas['unassigned_cell_centres'],
        },
        'exact_named_record_areas': exact_named,
        'coarse_grid_areas_m2': coarse['areas_m2'],
        'coarse_fine_unassigned_difference_m2': coarse['areas_m2']['unassigned_cell_centres'] - areas['unassigned_cell_centres'],
        'unassigned_fraction_of_wall_interior': round(grid['areas_m2']['unassigned_cell_centres']/total,6),
        'strict_component_count': len(groups), 'largest_residual_regions': regions,
        'named_site_areas': named,
        'market': {'source_square_bounds_xz_m': bounds(market), 'source_square_area_m2': market_area,
            'protected_civic_core_area_m2': g.polygon_area(fabric['market_protected_core_xz_m']),
            'compiled_stall_count': len(stalls), 'sum_stall_envelope_area_in_square_m2': round(stall_area,3),
            'stall_envelope_fraction': round(stall_area/market_area,6),
            'classification': 'named market reservation, not unassigned land; large programmed void still warrants functional and visual redesign',
            'proposal': 'Preserve fountain and through-routes; explicitly zone trader rows, service/loading windows and civic gathering ground. Reducing the 6996 m2 protected core or 11700 m2 source square requires an explicit source-policy revision, not hidden infill.'},
        'visual_observations': {
            'overview.png': 'Street-front ribbons surround broad ground-colour block interiors; castle, cathedral, river and exterior woodland are clearly distinct and must not be counted as generic gaps.',
            'market.png': 'Sparse edge stalls around an extremely large uniform plaza; this agrees with measured named-square area, not evidence of an unassigned parcel.',
            'old_town.png': 'Large continuous bare interiors behind ring-like frontage rows; residual-space inventory tests these independently of camera perspective.',
            'estate_stone.png': 'Much visible open ground belongs to the explicitly bounded estate and neighboring source plots; bare appearance alone does not make it unassigned.'},
        'limits': ['Original plots are initial deep-plot planning footprints, not a cadastral ownership survey; overlapping plot areas are unioned, never summed as exclusive land.',
            'The audited city envelope is the authored 105 ha wall polygon. The 1600 x 1460 m terrain rectangle is not a city boundary; exterior woodland, river and suburbs are not residual interior space.',
            'Cell-centre uncertainty is not a statistical confidence interval. The coarse/fine total difference tests stability only; small individual rectangles may alias more strongly. Exact named-polygon areas are supplied separately.',
            'Full-cell residual areas are conservative lower estimates; thin strips and cells touching reservations are deliberately excluded. Region boxes may span holes, roads or assigned land; only encoded cells are residual.',
            'AABB envelopes overestimate occupied built ground, so this audit understates residual land near nonrectangular buildings.',
            'No authored floodplain polygon or terrain slopes exist in these inputs. River ribbon is excluded; unverified bank setbacks and slope candidates are not invented as assignments.',
            'D08 cultivation and D01 slopes are narrative intentions, not geometric reservations beyond the named polygons. They can motivate new assignments but cannot excuse current unmapped ground.',
            'The source market and precincts are intentional reservations. Their scale/programming can still be unsatisfactory; that requires a deliberate design change.',
            'This is not parcel clearance, structural, drainage, navmesh or gameplay validation. Proposals do not authorize construction.']}


def self_checks():
    def rect(x0,z0,x1,z1):
        return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
    wall = rect(0,0,20,20)
    poly = rect(5,5,15,15)
    rows = [{'category':'explicit_property_grounds','id':'reserved','polygon':poly,'planes':halfplanes(poly)}]
    grid = raster_inventory(rows,wall,1)
    assert grid['areas_m2']['wall_interior_sampled']==400
    assert grid['areas_m2']['explicit_property_grounds']==100
    assert grid['areas_m2']['unassigned_cell_centres']==300
    rows.append({'category':'building_envelopes','id':'building','polygon':poly,'planes':halfplanes(poly)})
    overlap = raster_inventory(rows,wall,1)
    assert overlap['areas_m2']['assigned_union']==100
    assert sum(len(c) for c in components(overlap))==sum(overlap['strict'])
    for n,value in enumerate(overlap['strict']):
        if value:
            ix,iz=n%overlap['nx'],n//overlap['nx']
            cell=rect(ix,iz,ix+1,iz+1)
            assert g.convex_polygon_contains(wall,cell,0)
            assert g.intersection_area(poly,cell)<1e-9
    # A sub-cell-width access ribbon must still sever the conservative residual.
    slit=rect(9.9,0,10.1,20)
    narrow=raster_inventory([{'category':'access_reservations','id':'thin','polygon':slit,'planes':halfplanes(slit)}],wall,2)
    assert len(components(narrow))==2
    return {'passed':True,'checks':['known_rectangle_area','overlap_union_not_double_counted','component_cell_conservation','strict_cells_inside_wall','strict_cells_avoid_assignment','sub_cell_access_ribbon_retained']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', default='world_city/runtime_city/generated/r2/scene.flat_property.json')
    parser.add_argument('--fabric', default='world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json')
    parser.add_argument('--plan', default='world_city/data/city_brief.v2.json')
    parser.add_argument('--output', default='world_city/runtime_city/evidence/urban_void_audit.json')
    parser.add_argument('--grid-m', type=float, default=2.0)
    args = parser.parse_args()
    if not .5 <= args.grid_m <= 4:
        parser.error('--grid-m must be between 0.5 and 4 metres')
    root = Path(__file__).resolve().parents[3]
    inputs, data = {}, []
    for key in ('scene','fabric','plan'):
        path = root/getattr(args,key); raw = path.read_bytes()
        inputs[key] = {'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}
        data.append(json.loads(raw))
    report = audit(*data, root, args.grid_m)
    report['self_checks'] = self_checks()
    for name in ('overview','market','old_town','estate_stone'):
        path = root/'world_city/runtime_city/evidence/visual_r2_property'/f'{name}.png'
        inputs['image_'+name] = {'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'pixel_review': 'reviewed_by_agent'}
    hp = root/'world_city/city_history.json'
    history_raw = hp.read_bytes()
    history = json.loads(history_raw)
    inputs['canonical_history'] = {'path': str(hp.relative_to(root)), 'sha256': hashlib.sha256(history_raw).hexdigest()}
    report['canonical_land_use_basis'] = {
        'fictional_design': history['fictional_design'], 'snapshot_year': history['city']['snapshot_year'],
        'districts': {k: {name:v[name] for name in ('function','plot','density','property_types') if name in v}
                      for k,v in history['district_rules'].items()},
        'governing_landuse_contract': history['landuse_contract'],
    }
    report['inputs'] = inputs
    (root/args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'areas_m2': report['areas_m2'], 'largest_regions': [{k:v for k,v in r.items() if k not in ('row_runs_iz_ix_inclusive','nearest_source_buildings')} for r in report['largest_residual_regions']]},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
