"""Measured registered design polygons, clipped to retained city wall; not cadastral/historical facts."""
import json,hashlib,csv,sys,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.source.block_geometry import triangulate,inside
class Pieces:
 def __init__(self, pieces):self.pieces=pieces
 @property
 def area(self):return sum(geo.polygon_area(x)for x in self.pieces)
 @property
 def is_valid(self):return True
 def intersection(self,other):return Pieces([c for a in self.pieces for b in other.pieces if len(c:=geo.convex_intersection(a,b))>=3 and geo.polygon_area(c)>1e-8])
 def difference(self,other):
  out=[]
  for a in self.pieces:
   remain=[a]
   for b in other.pieces:remain=[c for p in remain for c in geo.convex_difference(p,b) if geo.polygon_area(c)>1e-8]
   out.extend(remain)
  return Pieces(out)
def Polygon(poly):
 t=triangulate(poly);assert abs(sum(geo.polygon_area(p)for p in t)-geo.polygon_area(poly))<1e-4,'Incomplete triangulation'
 return Pieces(t)
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
# Small-set inclusion/exclusion avoids repeatedly splitting already-thin shared edges.
def union_area(names):
 total=0.
 for n in range(1,len(names)+1):
  for ks in itertools.combinations(names,n):
   v=polys[ks[0]].intersection(wall)
   for k in ks[1:]:v=v.intersection(polys[k])
   total+=v.area*(1 if n%2 else -1)
 assert total>=0 and total<=sum(polys[k].intersection(wall).area for k in names)+1e-4
 return total
union_m2=union_area(priv)
relig_m2=union_area(['D_CLERGY','D_MONASTERY'])
overlap=[]
keys=list(polys)
for i,k in enumerate(keys):
 for z in keys[i+1:]:
  a=polys[k].intersection(polys[z]).intersection(wall).area
  if a>.01:overlap.append({'a':k,'b':z,'area_m2':a})
nobles=[x for x in D['plots']if x.get('district_id')=='D_NOBLE']
plots=[{'id':x['id'],'inside_wall_area_m2':Polygon(x['polygon_xz_m']).intersection(wall).area,'source_building_ids':x.get('building_ids',[]),'status':'gross owned polygon; public road cuts have not been subtracted'}for x in nobles]
result={'schema':'riverstone.city.functional_area_audit.v1','source_plan':str(P.relative_to(ROOT)),'source_sha256':EXPECTED,'wall_area_m2':wall.area,'design_residents':6000,'district_rows':rows,'privileged_and_military_gross_union_m2':union_m2,'privileged_and_military_gross_union_percent':100*union_m2/wall.area,'clergy_and_abbey_gross_union_m2':relig_m2,'clergy_and_abbey_gross_union_percent':100*relig_m2/wall.area,'overlaps_inside_wall':overlap,'noble_compounds':plots,'scope':['Measured horizontal polygon areas of current image-registered design; current common geometry shares the same anchors.','Precinct gross area includes public edges, productive gardens, cemetery and service courts; it is not exclusive private luxury area.','D_MIXED spans entire wall and is a fallback, not an additional district to add.','Cemetery and cloister spaces lie within clergy precinct; not counted twice.','Historical plausibility is qualitative; no universal medieval land-use percentage asserted.']}
# Independent 5m center-sample only checks gross-union arithmetic, not exact cadastral area.
low=[min(p[k]for p in D['boundary_xz_m'])for k in (0,1)];high=[max(p[k]for p in D['boundary_xz_m'])for k in (0,1)]
grid_wall=grid_priv=0
raw={x['id']:x['polygon_xz_m']for x in D['districts']}
for ix in range(int((high[0]-low[0])/5)+1):
 for iz in range(int((high[1]-low[1])/5)+1):
  pt=[low[0]+2.5+5*ix,low[1]+2.5+5*iz]
  if inside(pt,D['boundary_xz_m']):
   grid_wall+=1
   if any(inside(pt,raw[k])for k in priv):grid_priv+=1
result['independent_grid_check']={'pitch_m':5,'sampled_wall_m2':grid_wall*25,'sampled_privileged_union_m2':grid_priv*25,'union_difference_percent_of_wall':100*abs(grid_priv*25-union_m2)/wall.area,'purpose':'Coarse independent union arithmetic check only'}
assert result['independent_grid_check']['union_difference_percent_of_wall']<.5
(OUT/'area_baseline.json').write_text(json.dumps(result,indent=2)+'\n')
with (OUT/'area_baseline.csv').open('w')as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print(json.dumps({k:result[k]for k in ['wall_area_m2','privileged_and_military_gross_union_percent','clergy_and_abbey_gross_union_percent','overlaps_inside_wall']},indent=2))
