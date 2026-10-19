"""Measured registered design polygons, clipped to retained city wall; not cadastral/historical facts."""
import json,hashlib,csv
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
P=ROOT/'world_city/concept_city_v3/registered_source/plan.json'
EXPECTED='685592393dd5b3bffa189d497db8bff14ba4d893d5d81089a66427bd5a6b588c'
assert hashlib.sha256(P.read_bytes()).hexdigest()==EXPECTED
D=json.loads(P.read_bytes());wall=Polygon(D['boundary_xz_m']);assert wall.is_valid
polys={x['id']:Polygon(x['polygon_xz_m'])for x in D['districts'] if x['id']!='D_MIXED'}
rows=[]
for x in D['districts']:
 if x['id']=='D_MIXED':continue
 p=polys[x['id']];assert p.is_valid,x['id'];clip=p.intersection(wall)
 rows.append({'id':x['id'],'role':x['role'],'gross_source_m2':p.area,'inside_wall_m2':clip.area,'outside_wall_m2':p.difference(wall).area,'wall_share_percent':100*clip.area/wall.area,'m2_per_design_resident_6000':clip.area/6000})
priv=['D_CASTLE','D_TRAIN','D_NOBLE','D_CLERGY','D_MONASTERY']
union=unary_union([polys[k]for k in priv]).intersection(wall)
relig=unary_union([polys[k]for k in ['D_CLERGY','D_MONASTERY']]).intersection(wall)
overlap=[]
keys=list(polys)
for i,k in enumerate(keys):
 for z in keys[i+1:]:
  a=polys[k].intersection(polys[z]).intersection(wall).area
  if a>.01:overlap.append({'a':k,'b':z,'area_m2':a})
nobles=[x for x in D['plots']if x.get('district_id')=='D_NOBLE']
plots=[{'id':x['id'],'inside_wall_area_m2':Polygon(x['polygon_xz_m']).intersection(wall).area,'source_building_ids':x.get('building_ids',[]),'status':'gross owned polygon; public road cuts have not been subtracted'}for x in nobles]
result={'schema':'riverstone.city.functional_area_audit.v1','source_plan':str(P.relative_to(ROOT)),'source_sha256':EXPECTED,'wall_area_m2':wall.area,'design_residents':6000,'district_rows':rows,'privileged_and_military_gross_union_m2':union.area,'privileged_and_military_gross_union_percent':100*union.area/wall.area,'clergy_and_abbey_gross_union_m2':relig.area,'clergy_and_abbey_gross_union_percent':100*relig.area/wall.area,'overlaps_inside_wall':overlap,'noble_compounds':plots,'scope':['Measured horizontal polygon areas of current image-registered design; current common geometry shares the same anchors.','Precinct gross area includes public edges, productive gardens, cemetery and service courts; it is not exclusive private luxury area.','D_MIXED spans entire wall and is a fallback, not an additional district to add.','Cemetery and cloister spaces lie within clergy precinct; not counted twice.','Historical plausibility is qualitative; no universal medieval land-use percentage asserted.']}
(OUT/'area_baseline.json').write_text(json.dumps(result,indent=2)+'\n')
with (OUT/'area_baseline.csv').open('w')as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print(json.dumps({k:result[k]for k in ['wall_area_m2','privileged_and_military_gross_union_percent','clergy_and_abbey_gross_union_percent','overlaps_inside_wall']},indent=2))
