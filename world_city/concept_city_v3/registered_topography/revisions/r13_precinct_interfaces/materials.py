"""R13 finite ground-material repair; original r10/r11 data are immutable.

Distance-weld only consecutive/closing duplicate vertices before half-plane
clipping. Keep collinear seam knots and the original physical height evaluator.
"""
import copy,json,math
from pathlib import Path
from ..r11_ground_materials import author as legacy
prior=legacy.prior;geo=prior.geo;R04=prior.R04;CITY=prior.CITY
HERE=Path(__file__).resolve().parent
WELD_M=1e-9

def polygon(p):
 out=[]
 for q in p:
  if not out or math.dist(q,out[-1])>WELD_M:out.append(list(q))
 while len(out)>1 and math.dist(out[0],out[-1])<=WELD_M:out.pop()
 return out if len(out)>=3 and geo.polygon_area(out)>1e-8 else None

REGIONS=[];INDEX=geo._SpatialIndex(16);NORMALIZATION=[]
for r in legacy.REGIONS:
 p=polygon(r['polygon_xz_m'])
 if not p:raise ValueError('Degenerate material source '+r['material_region_id'])
 # These source pieces are convex. Keep the existing common clipper's domain.
 sign=1 if geo.signed_polygon_area(p)>0 else -1
 for i,b in enumerate(p):
  a=p[i-1];c=p[(i+1)%len(p)]
  if sign*geo._cross(a,b,c)<-1e-8:raise ValueError('Nonconvex material source '+r['material_region_id'])
 if len(p)!=len(r['polygon_xz_m']):NORMALIZATION.append(dict(material_region_id=r['material_region_id'],source_vertex_count=len(r['polygon_xz_m']),normalized_vertex_count=len(p),area_delta_m2=geo.polygon_area(p)-geo.polygon_area(r['polygon_xz_m'])))
 REGIONS.append(dict(r,polygon_xz_m=p))
for i,r in enumerate(REGIONS):INDEX.add(i,r['polygon_xz_m'])
eligible=legacy.eligible;marked=legacy.marked

def apply_material_regions(records,bounds=None,conform=False):
 out=[]
 for r in records:
  src=polygon(r['polygon_xz_m'])
  if not src:continue
  if not eligible(r):out.append(dict(r,polygon_xz_m=src));continue
  parts=[src]
  for i in sorted(INDEX.candidates(src)):
   m=REGIONS[i];new=[]
   for p in parts:
    q=polygon(geo.convex_intersection(p,m['polygon_xz_m']))
    if q:
     out.append(marked(r,m,q));new.extend(t for cut in geo.convex_difference(p,m['polygon_xz_m']) if(t:=polygon(cut)))
    else:new.append(p)
   parts=new
  out.extend(dict(r,polygon_xz_m=p) for p in parts)
 return R04.old.conform_domains(out) if conform else out

def surface_domains(bounds,conform=True):return apply_material_regions(prior.surface_domains(bounds,conform),bounds,conform)
def owner_at(x,z):
 r=prior.owner_at(x,z)
 if eligible(r):
  for i in sorted(INDEX.candidates([[x,z]])):
   m=REGIONS[i]
   if geo.point_in_convex_polygon([x,z],m['polygon_xz_m'],1e-8):return marked(r,m)
 return r
source_surface_height_at=prior.source_surface_height_at;surface_height_at=prior.surface_height_at
height_at=prior.height_at;land_height_at=prior.land_height_at;road_height_at=prior.road_height_at;path_height_at=prior.path_height_at
ordinary_foundation_contracts=prior.ordinary_foundation_contracts;finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at;water_height_at=prior.water_height_at;river_water_y=prior.river_water_y
supplemental_surface_domains=prior.supplemental_surface_domains;supplemental_side_records=prior.supplemental_side_records;retaining_interfaces=prior.retaining_interfaces

def build_contract():
 c=copy.deepcopy(legacy.build_contract());c.update(revision='r13_material_partition_repair',review_module=__name__);c['exact_surface_ownership']['module']=__name__
 c['ground_material_ownership']['regions']=REGIONS
 c['ground_material_partition_repair']=dict(source_revision='r11_ground_materials',legacy_module_sha256=R04.sha(Path(legacy.__file__)),distance_weld_m=WELD_M,normalized_source_masks=NORMALIZATION,policy='Remove only consecutive or closing distance-coincident vertices before existing convex clipping. Keep physical heights, source owners and all collinear seam knots.',height_change_m=0)
 c['module_sources'][str((HERE/'materials.py').relative_to(CITY))]=R04.sha(HERE/'materials.py');return c
