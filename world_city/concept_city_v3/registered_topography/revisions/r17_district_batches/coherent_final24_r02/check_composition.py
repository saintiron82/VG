"""Finite original-index and accepted-domain composition ledger."""
import json
from .prepare import HERE,write,ref
from .. import author as a

def run():
 current=json.loads((HERE/'top_scene_patch_r01.json').read_bytes());keys={(r['material'],r['triangle_index'])for r in current['surface_edits']};cuts=json.loads((HERE/'compact_cut_domains_r01.json').read_bytes())['polygons_xz_m'];index=a.geo._SpatialIndex(8)
 for i,p in enumerate(cuts):index.add(i,p)
 comparisons=[]
 for name in ['contour_bulk_r01','coherent_batch18_r01','coherent_batch20_r01']:
  folder=HERE.parent/name;prior=json.loads((folder/'top_scene_patch_r02.json').read_bytes());oldcuts=json.loads((folder/'compact_cut_domains_r02.json').read_bytes())['polygons_xz_m'];shared=keys&{(r['material'],r['triangle_index'])for r in prior['surface_edits']};hits=[]
  for p in oldcuts:
   for i in index.candidates(p):
    q=a.clip(p,cuts[i])
    if q and a.geo.polygon_area(q)>1e-8:hits.append(q)
  hits=a.common.disjoint_union(hits);comparisons.append(dict(prior_patch=ref(folder/'top_scene_patch_r02.json'),shared_original_triangle_keys=sorted(shared),positive_cut_domain_intersections=hits,positive_intersection_area_m2=sum(a.geo.polygon_area(p)for p in hits)))
 write('accepted61_composition_ledger_r01.json',dict(current_top_patch=ref(HERE/'top_scene_patch_r01.json'),comparisons=comparisons,policy='Shared original indices require geometric composition against the same frozen R7 source. Never apply stale source indices sequentially.',activation=False))
 print([(len(r['shared_original_triangle_keys']),r['positive_intersection_area_m2'])for r in comparisons],flush=True)
if __name__=='__main__':run()
