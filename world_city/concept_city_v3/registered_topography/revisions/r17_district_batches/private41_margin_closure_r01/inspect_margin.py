"""Extract the exact bounded unowned source component beside B001 C002."""
import json, math
from pathlib import Path
from .. import author as a
from ..coherent_batch18_r01.route_interval import interval
HERE = Path(__file__).resolve().parent
REVIEW = a.CITY / 'registered_integration/r8/joint_boundary_r05/boundary_review.json'
OWNER = 'BLOCK_001:R8_C002:EARTH:court_polygons_xz_m:36:0:PART:0'

def run():
    review = json.loads(REVIEW.read_bytes())
    edge = next(r['edge_xz_m'] for r in review['unknown_exterior_segments'] if r['owner_id'] == OWNER)
    hand = json.loads((a.HERE / 'coherent_batch18_r01/physical_owner_handoff_r02.json').read_bytes())
    owner = next(r for r in hand['physical_earth_owners'] if r['id'] == OWNER)
    x0, z0, x1, z1 = a.bounds(edge)
    window = [[x0-1,z0-1],[x1+1,z0-1],[x1+1,z1+1],[x0-1,z1+1]]
    scene = a.load_scene()
    index = a.TriangleIndex(scene, [window])
    tops = list(index.covering(window))
    holes = a.common.subtract([window], [r['intersection_polygon_xz_m'] for r in tops])
    # Select the connected omission component incident to the exact unknown
    # edge, using shared positive-length polygon edges rather than proximity.
    selected = {i for i,p in enumerate(holes) if interval(edge[0], edge[1], p)}
    changed = True
    while changed:
        changed = False
        for i, poly in enumerate(holes):
            if i in selected:
                continue
            for j in list(selected):
                other = holes[j]
                if any((span := interval(u,v,other)) and (span[1]-span[0])*math.dist(u,v)>1e-7 for u,v in zip(poly,poly[1:]+poly[:1])):
                    selected.add(i); changed=True; break
    components = [holes[i] for i in sorted(selected)]
    window_contact = any(interval(u,v,p) for u,v in zip(window,window[1:]+window[:1]) for p in components)
    outside = a.common.subtract(components, [owner['polygon_xz_m']])
    result = dict(source_review=dict(path=str(REVIEW.relative_to(a.ROOT)),sha256=a.sha(REVIEW)), source_scene=dict(path=str(a.SCENE_PATH.relative_to(a.ROOT)),sha256=a.SCENE_SHA256), owner=owner, unknown_edge_xz_m=edge, inspection_window_xz_m=window, source_top_pieces=tops, all_missing_pieces_xz_m=holes, incident_missing_component_xz_m=components, component_area_m2=sum(a.geo.polygon_area(p) for p in components), component_touches_window=window_contact, outside_original_owner_polygons_xz_m=outside, outside_area_m2=sum(a.geo.polygon_area(p) for p in outside), activation=False)
    path=HERE/'source_component_r01.json';assert not path.exists();path.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print({k:result[k] for k in ('component_area_m2','component_touches_window','outside_area_m2')}, 'pieces',len(components),flush=True)

if __name__ == '__main__':
    run()
