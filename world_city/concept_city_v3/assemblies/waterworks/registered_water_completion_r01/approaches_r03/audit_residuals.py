"""Audit finite northern field for almost-vertical retained original road slivers."""
import pathlib,json,math,hashlib,sys
sys.dont_write_bytecode=True
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.assemblies.waterworks.registered_water_completion_r01.approaches_r02 import finite
from world_city.runtime_city.checks import placement as g
H=pathlib.Path(__file__).resolve().parent;OLD=H.parent/'approaches_r02';CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'evidence/visual_registered_common_r7_palette_r01/scene.json';ACTUAL=CITY/'evidence/r8_district_r02/scene.json'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),sort_keys=True).encode()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def area3(t):
 u=[t[1][i]-t[0][i]for i in range(3)];v=[t[2][i]-t[0][i]for i in range(3)];return math.sqrt(sum((u[i]*v[j]-u[j]*v[i])**2 for i,j in[(0,1),(1,2),(2,0)]))/2

def spans(p,q,masks):
 raw=sorted(s for m in masks if(s:=finite.interval(p,q,m,1e-7)));merged=[]
 for lo,hi in raw:
  if merged and lo<=merged[-1][1]+1e-7:merged[-1][1]=max(merged[-1][1],hi)
  else:merged.append([lo,hi])
 return merged

def main():
 base=read(BASE);actual=read(ACTUAL);assert sha(BASE)=='1429ae51b7c72b12940dcf0dd7e12c2684cab95f81735d228bba64dc819317c1';assert sha(ACTUAL)=='20c6af94d661de033fe62dc1db44208e8b848dd40b21fb54175b93e0bf66b548';field=next(p for p in read(OLD/'fields.json')['profiles']if p['id']=='NORTH_SHARED_JUNCTION');masks=field['polygons_xz_m'];bb=[min(v[0]for m in masks for v in m),min(v[1]for m in masks for v in m),max(v[0]for m in masks for v in m),max(v[1]for m in masks for v in m)];retained={json.dumps(actual['surfaces']['road'][i:i+3],separators=(',',':')):i//3 for i in range(0,len(actual['surfaces']['road']),3)};oldedits={(e['material'],e['triangle_index'])for e in read(OLD/'surface_patch.json')['surface_edits']};rows=[]
 for i in range(0,len(base['surfaces']['road']),3):
  t=base['surfaces']['road'][i:i+3];xz=[[v[0],v[2]]for v in t]
  if min(v[0]for v in xz)<bb[0]-1e-5 or max(v[0]for v in xz)>bb[2]+1e-5 or min(v[1]for v in xz)<bb[1]-1e-5 or max(v[1]for v in xz)>bb[3]+1e-5:continue
  a2=g.polygon_area(xz);a3=area3(t)
  if a2>1e-7 or a3<1e-6 or min(v[1]for v in t)<15.65:continue
  line=max(((p,q)for p in xz for q in xz),key=lambda pq:math.dist(*pq));span=spans(*line,masks);raw=json.dumps(t,separators=(',',':'));rows.append(dict(material='road',triangle_index=i//3,source_triangle_sha256=digest(t),vertices_xyz_m=t,projected_area_m2=a2,actual_3d_area_m2=a3,longest_span_xz_m=line,owned_spans_t=span,entire_projected_span_owned=len(span)==1 and span[0][0]<1e-7 and span[0][1]>1-1e-7,already_edited=('road',i//3)in oldedits,actual_retained_index=retained.get(raw),clearance_above_finished_surface_m=[min(v[1]for v in t)-15.6,max(v[1]for v in t)-15.6]))
 write(H/'residual_audit.json',dict(schema='riverstone.finite_north_road_residuals.r03',base_scene=ref(BASE),actual_scene=ref(ACTUAL),prior_fields=ref(OLD/'fields.json'),prior_patch=ref(OLD/'surface_patch.json'),field_id=field['id'],finished_y_m=15.6,criteria=dict(projected_area_max_m2=1e-7,actual_3d_area_min_m2=1e-6,clearance_min_m=.05),candidates=rows));print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
