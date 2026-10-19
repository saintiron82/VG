"""Index conflicts and exact cut-domain intersections with the sealed 41."""
import json
from .screen import HERE, write
from .. import author as a

def ref(path):
    return dict(path=str(path.relative_to(a.ROOT)), sha256=a.sha(path))

def run():
    current_path = HERE / 'top_scene_patch_r02.json'
    current = json.loads(current_path.read_bytes())
    current_keys = {(r['material'], r['triangle_index']) for r in current['surface_edits']}
    cuts = json.loads((HERE / 'compact_cut_domains_r02.json').read_bytes())['polygons_xz_m']
    index = a.geo._SpatialIndex(8)
    for i, polygon in enumerate(cuts):
        index.add(i, polygon)
    comparisons = []
    for name in ('contour_bulk_r01', 'coherent_batch18_r01'):
        folder = HERE.parent / name
        prior_path = folder / 'top_scene_patch_r02.json'
        prior = json.loads(prior_path.read_bytes())
        old_cuts = json.loads((folder / 'compact_cut_domains_r02.json').read_bytes())['polygons_xz_m']
        shared = current_keys & {(r['material'], r['triangle_index']) for r in prior['surface_edits']}
        hits = []
        for old in old_cuts:
            for i in index.candidates(old):
                hit = a.clip(old, cuts[i])
                if hit and a.geo.polygon_area(hit) > 1e-8:
                    hits.append(hit)
        hits = a.common.disjoint_union(hits)
        comparisons.append(dict(prior_patch=ref(prior_path), shared_original_triangle_keys=sorted(shared),
            positive_cut_domain_intersections=hits, positive_intersection_area_m2=sum(a.geo.polygon_area(p) for p in hits)))
    write('sealed41_composition_ledger_r01.json', dict(source_next20_patch=ref(current_path), comparisons=comparisons,
        policy='Shared original indices require geometric composition from their common frozen source. Never apply stale index patches sequentially. Positive domain intersections require explicit ownership reconciliation.', activation=False))
    print([(r['prior_patch']['path'], len(r['shared_original_triangle_keys']), r['positive_intersection_area_m2']) for r in comparisons], flush=True)

if __name__ == '__main__':
    run()
