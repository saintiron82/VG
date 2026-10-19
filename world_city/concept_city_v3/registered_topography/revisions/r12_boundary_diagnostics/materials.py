"""Optional exact owner/material classifier. It never evaluates or changes Y.
Use direct_material first for a zero-geometry-change fix. material_pieces is an
optional exact 2D subdivision for unlabelled ground; it must inherit the same
owner-specific height evaluator when new boundary vertices are introduced.
"""
import json
from pathlib import Path
from ..r11_ground_materials import author as terrain
from world_city.concept_city_v3.registered_source.geometry import triangulate
HERE=Path(__file__).resolve().parent;CITY=terrain.CITY;geo=terrain.geo;clean=terrain.clean
PLAN_PATH=CITY/'registered_source/plan.json';PLAN=json.loads(PLAN_PATH.read_bytes())
OWNER_MATERIAL={'CASTLE':'land_D_CASTLE','CLERGY':'land_D_CLERGY','TRAIN':'land_D_TRAIN','MARKET':'space_civic','MONASTERY':'land_D_MONASTERY','PORT':'land_D_PORT','POOR':'land_D_POOR','COMMON':'land_D_COMMON','NOBLE':'land_D_NOBLE',**{'E'+str(i):'land_D_NOBLE' for i in range(1,8)}}
def direct_material(record):
 if record.get('material'):return record['material']
 if record['kind']=='terrace':return OWNER_MATERIAL.get(record.get('registration_control_id',record['owner_id']))
 return None
ZONES=[];INDEX=geo._SpatialIndex(32)
# Base-ground paint follows the exact persisted source-plan district polygons.
# Existing terrace records instead use their exact owner identity directly.
for d in PLAN['districts']:
 material=OWNER_MATERIAL.get(d.get('registration_control_id'),'land_'+d['id'])
 for i,p in enumerate(triangulate(d['polygon_xz_m'])):ZONES.append(dict(id=d['id']+':'+str(i),polygon_xz_m=p,material=material))
for i,r in enumerate(ZONES):INDEX.add(i,r['polygon_xz_m'])
def material_pieces(record):
 material=direct_material(record)
 if material:return [dict(record,material=material,material_assignment_basis='explicit finite owner')]
 if not record.get('render_land',True):return [record]
 kind=record.get('underlying_record',record)['kind']
 if kind in ('road','replacement_road','port_tie','external_triangular_surface','reservoir_service_public_landing'):return [dict(record,material='road')]
 if kind in ('door_landing','door_approach','b015_entry','density_entry'):return [dict(record,material='alley')]
 parts=[record['polygon_xz_m']];out=[]
 for i in sorted(INDEX.candidates(record['polygon_xz_m'])):
  zone=ZONES[i];new=[]
  for p in parts:
   q=clean(geo.convex_intersection(p,zone['polygon_xz_m']))
   if q:
    out.append(dict(record,polygon_xz_m=q,material=zone['material'],material_assignment_basis='exact registered area cut',material_zone_id=zone['id']));new.extend(t for cut in geo.convex_difference(p,zone['polygon_xz_m']) if(t:=clean(cut)))
   else:new.append(p)
  parts=new
 out.extend(dict(record,polygon_xz_m=p,material='ground',material_assignment_basis='outside exact registered zones') for p in parts)
 return out

def classify_material_regions(record,polygon_xz_m):
 """Disjoint material masks for one ORIGINAL render triangle or convex piece.
 The caller must clip its original3D triangle then barycentrically lift new XZ
 vertices onto that SAME triangle plane. Never resample terrain height here.
 """
 r=dict(record,polygon_xz_m=polygon_xz_m)
 return [dict(polygon_xz_m=p['polygon_xz_m'],material=p.get('material','ground')) for p in material_pieces(r)]

def report():
 ds={d.get('registration_control_id'):d for d in PLAN['districts']};regions=[]
 for r in terrain.R04.base.terrace_regions():
  d=ds.get(r['id'])
  if d:regions.append(dict(owner_id=r['id'],source_district_id=d['id'],owner_area_m2=geo.polygon_area(r['polygon_xz_m']),source_rounded_area_m2=geo.polygon_area(d['polygon_xz_m']),maximum_corresponding_vertex_difference_m=max(__import__('math').dist(x,y) for x,y in zip(r['polygon_xz_m'],d['polygon_xz_m'])) if len(r['polygon_xz_m'])==len(d['polygon_xz_m']) else None,material=OWNER_MATERIAL[r['id']],preferred_boundary='unrounded exact owner polygon'))
 return dict(schema='riverstone.material_boundary_diagnosis.v1',source_plan_sha256=terrain.R04.sha(PLAN_PATH),owner_material_map=OWNER_MATERIAL,polygon_correspondence=regions,direct_api='direct_material(record): explicit record material wins, then exact terrace owner mapping; no vertex/height change',optional_subdivision_api='classify_material_regions(record,polygon_xz_m): disjoint exact plan masks; caller barycentrically lifts to the original rendered triangle plane, never resamples height',priority='Native/water holes are ignored. Existing explicit r11 material survives. Road/door/profile records retain prior material contracts.',geometry_change=False)
if __name__=='__main__':(HERE/'owner_material_map.json').write_text(json.dumps(report(),indent=2)+'\n')
