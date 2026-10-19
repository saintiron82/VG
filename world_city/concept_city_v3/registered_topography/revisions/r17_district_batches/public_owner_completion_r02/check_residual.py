import json
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..final_profile_audit_r01.exact_clip import clip,difference
from .bind import OLD,RECOVERED,HERE
P=HERE/'actual_public_inputs.json';e=next(r for r in json.loads(P.read_bytes())['entries']if r['holding_id']=='BLOCK_008:R8_C003');r=json.loads(RECOVERED.read_bytes());owners=[]
for kind in ['approaches','landings']:
 for i,t in enumerate(r[kind]['triangles']):owners.append(dict(t,id=kind+':'+str(i),plane_y_xz_m=a.common.plane(t['triangle_xyz_m'])))
ix=index(owners);rows=[]
for p in e['remaining_polygons_xz_m']:
 hits=[];rem=[p]
 for i in ix.candidates(p):
  s=owners[i];q=clip(p,s['polygon_xz_m']);ar=a.geo.polygon_area(q)
  if ar>1e-12:
   hits.append(dict(id=s['id'],polygon_xz_m=q,area_m2=ar,plane_y_xz_m=s['plane_y_xz_m'],source_triangle_xyz_m=s['triangle_xyz_m']));rem=[v for z in rem for v in difference(z,s['polygon_xz_m'])]
 rows.append(dict(polygon_xz_m=p,area_m2=a.geo.polygon_area(p),hits=hits,exact_remaining_polygons_xz_m=rem,exact_remaining_area_m2=sum(a.geo.polygon_area(x)for x in rem)))
print('original',sum(x['area_m2']for x in rows),'exact missing',sum(x['exact_remaining_area_m2']for x in rows),'hits',sum(len(x['hits'])for x in rows));print([(x['area_m2'],x['exact_remaining_area_m2'],len(x['hits']))for x in sorted(rows,key=lambda x:-x['area_m2'])[:8]])
write(HERE/'residual_exact_review.json',dict(rows=rows,source=dict(path=str(P.relative_to(a.ROOT)),sha256=a.sha(P))))
