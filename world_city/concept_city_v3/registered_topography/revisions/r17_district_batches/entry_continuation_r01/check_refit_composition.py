"""Exact pairwise private field compatibility for selected seven refits."""
import json,collections
from pathlib import Path
from .. import author as a
HERE=Path(__file__).resolve().parent

def run():
 summary=json.loads((HERE/'source_refit_profile_summary_r01.json').read_bytes());records=[]
 for r in summary['rows']:
  choice=next(q for q in r['trials']if q['candidate_index']==r['selected_candidate_index']);d=json.loads((a.ROOT/choice['path']).read_bytes());records.append(d)
 pairs=[]
 for i,d in enumerate(records):
  for e in records[i+1:]:
   overlap=[]
   for p in d['private_domain_polygons_xz_m']:
    for q in e['private_domain_polygons_xz_m']:
     hit=a.clip(p,q)
     if hit:overlap.append(hit)
   overlap=a.common.disjoint_union(overlap);area=sum(a.geo.polygon_area(p)for p in overlap)
   if area<1e-8:continue
   rows=[];idx=a.geo._SpatialIndex(4)
   for j,t in enumerate(e['result']['triangles']):idx.add(j,t['polygon_xz_m'])
   for t in d['result']['triangles']:
    for j in idx.candidates(t['polygon_xz_m']):
     u=e['result']['triangles'][j];hit=a.clip(t['polygon_xz_m'],u['polygon_xz_m'])
     if hit:rows.append(dict(polygon_xz_m=hit,max_height_difference_m=max(abs(a.common.height(t['plane_y_xz_m'],p)-a.common.height(u['plane_y_xz_m'],p))for p in hit)))
   pairs.append(dict(left=d['holding_id'],right=e['holding_id'],overlap_area_m2=area,max_height_difference_m=max((r['max_height_difference_m']for r in rows),default=0),intersection_pieces=rows))
 out=dict(pairs=pairs,maximum_height_difference_m=max((r['max_height_difference_m']for r in pairs),default=0),status='DISJOINT_OR_IDENTICAL_SHARED_FIELDS'if all(r['max_height_difference_m']<=1e-7 for r in pairs)else'REQUIRES_SHARED_GROUP_SOLVE',activation=False)
 p=HERE/'source_refit_composition_r01.json';assert not p.exists();p.write_text(json.dumps(out,separators=(',',':'))+'\n');print({k:v for k,v in out.items()if k!='pairs'},[(r['left'],r['right'],r['overlap_area_m2'],r['max_height_difference_m'])for r in pairs])
if __name__=='__main__':run()
