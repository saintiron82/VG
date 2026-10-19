import json,collections
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
HERE=Path(__file__).resolve().parent
source=a.HERE.parent/'public_corridors_r18/boundary_ownership_inputs_r03.json';rows=json.loads(source.read_bytes())['masks'];ix=index(rows);w=json.loads((HERE/'water_owner_binding.json').read_bytes());out=[]
for e in w['entries']:
 hits=[]
 for p in e['remaining_polygons_xz_m']:
  for i in ix.candidates(p):
   r=rows[i];q=a.clip(p,r['polygon_xz_m']);ar=a.geo.polygon_area(q or[])
   if ar>1e-8:hits.append(dict(id=r['id'],polygon_xz_m=q,area_m2=ar,source_record=r))
 owners=collections.defaultdict(float)
 for r in hits:owners[r['id'].split(':')[0]]+=r['area_m2']
 out.append(dict(holding_id=e['holding_id'],remaining_area_m2=e['remaining_area_m2'],contacts=hits,owner_area_sums=dict(owners)));print(e['holding_id'],dict(owners),flush=True)
write(HERE/'remaining_owner_classification.json',dict(source=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),entries=out,activation=False))
