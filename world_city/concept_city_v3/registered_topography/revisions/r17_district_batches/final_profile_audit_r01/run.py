import json
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from .exact_clip import clip
HERE=Path(__file__).resolve().parent
rows=[]
for row in json.loads((a.HERE/'final_district_profiles_r01/summary.json').read_bytes())['rows']:
 d=json.loads((a.ROOT/row['path']).read_bytes());t=d['result']['triangles'];ix=index(t);hits=[];total=0.
 for i,r in enumerate(t):
  for j in ix.candidates(r['polygon_xz_m']):
   if j<=i:continue
   q=clip(r['polygon_xz_m'],t[j]['polygon_xz_m']);area=a.geo.polygon_area(q);total+=area
   if area>1e-9:hits.append(dict(indices=[i,j],polygon_xz_m=q,area_m2=area))
 rows.append(dict(holding_id=row['holding_id'],profile_source=dict(path=row['path'],sha256=row['sha256']),positive_overlap_area_m2=total,overlaps=hits));print(row['holding_id'],total,hits[:2])
write(HERE/'exact_overlap_review.json',dict(rows=rows,policy='Zero-threshold signed halfplane clipping; no short-edge absolute cross-product tolerance. Previous generic overlap diagnostic is retained.'))
