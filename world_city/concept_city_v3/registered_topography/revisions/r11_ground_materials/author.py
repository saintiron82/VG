"""Material-only finite B13/B15 yard/court partitions; no added floor or grade."""
import json,copy
from pathlib import Path
from ..r10_density_reservoir import author as prior
HERE=Path(__file__).resolve().parent;CITY=prior.CITY;geo=prior.geo;clean=prior.clean;R04=prior.R04
B13_PATH=CITY/'assemblies/ordinary/registered/r1/owned_grounds.json';B13_SHA='90d19bf887b2b959b80a76029adc04418e03397f7e80cdbbb313c3e786eedb51'
if R04.sha(B13_PATH)!=B13_SHA:raise ValueError('B13 grounds changed')
B13=json.loads(B13_PATH.read_bytes());REGIONS=[];INDEX=geo._SpatialIndex(16)
for r in B13['grounds']+prior.DENSITY['ground_ownership_records']:
 material='grass' if 'productive_beds' in r['role'] else 'earth'
 for i,p in enumerate(r['polygons_xz_m']):REGIONS.append(dict(material_region_id=r['id']+':'+str(i),semantic_ground_id=r['id'],semantic_role=r['role'],material=material,polygon_xz_m=p))
for r in prior.r07.DENSITY['courts']+prior.DENSITY['courts']:
 REGIONS.append(dict(material_region_id=r['id'],semantic_ground_id=r['id'],semantic_role='retained_shared_court',material='stone',polygon_xz_m=r['polygon_xz_m']))
for i,r in enumerate(REGIONS):INDEX.add(i,r['polygon_xz_m'])
def eligible(r):return r.get('render_land',True) and r['kind'] in ('ground','terrace','density_court','b015_court')
def marked(r,m,p=None):return dict(r,polygon_xz_m=p or r.get('polygon_xz_m',m['polygon_xz_m']),material=m['material'],ground_material_owner_id=m['semantic_ground_id'],material_region_id=m['material_region_id'],material_change_only=True)
def owner_at(x,z):
 r=prior.owner_at(x,z)
 if eligible(r):
  for i in sorted(INDEX.candidates([[x,z]])):
   m=REGIONS[i]
   if geo.point_in_convex_polygon([x,z],m['polygon_xz_m'],1e-8):return marked(r,m)
 return r

def surface_domains(bounds,conform=True):
 out=[]
 for r in prior.surface_domains(bounds,conform):
  if not eligible(r):out.append(r);continue
  parts=[r['polygon_xz_m']]
  for i in sorted(INDEX.candidates(r['polygon_xz_m'])):
   m=REGIONS[i];new=[]
   for p in parts:
    q=clean(geo.convex_intersection(p,m['polygon_xz_m']))
    if q:
     out.append(marked(r,m,q));new.extend(t for cut in geo.convex_difference(p,m['polygon_xz_m']) if(t:=clean(cut)))
    else:new.append(p)
   parts=new
  out.extend(dict(r,polygon_xz_m=p) for p in parts)
 return R04.old.conform_domains(out) if conform else out
source_surface_height_at=prior.source_surface_height_at;surface_height_at=prior.surface_height_at
height_at=prior.height_at;land_height_at=prior.land_height_at;road_height_at=prior.road_height_at;path_height_at=prior.path_height_at
ordinary_foundation_contracts=prior.ordinary_foundation_contracts;finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at;water_height_at=prior.water_height_at;river_water_y=prior.river_water_y
supplemental_surface_domains=prior.supplemental_surface_domains;supplemental_side_records=prior.supplemental_side_records
retaining_interfaces=prior.retaining_interfaces

def build_contract():
 c=copy.deepcopy(prior.build_contract());c.update(revision='r11_ground_materials',schema='riverstone.registered_ground_material.r11.v1',review_module=__name__);c['exact_surface_ownership']['module']=__name__
 c['ground_material_ownership']=dict(regions=REGIONS,source_paths=[str(B13_PATH.relative_to(CITY)),str(prior.DENSITY_PATH.relative_to(CITY))],materials={'grass':'productive-bed ground green','earth':'muted workyard/stockyard/service earth','stone':'retained shared courts'},policy='Exact clipped material regions only; same owner IDs/kinds, same height APIs, no new floor planes. Public routes, actual doors and native/water masks keep priority. Roof area accounting is never a terrain mask.',height_change_m=0,source_semantic_grounds=32,retained_courts=4)
 c['references'][str(B13_PATH.relative_to(CITY))]=B13_SHA;c['module_sources'][str((HERE/'author.py').relative_to(CITY))]=R04.sha(HERE/'author.py');return c
if __name__=='__main__':(HERE/'contract.json').write_text(json.dumps(build_contract(),indent=2)+'\n');print(R04.sha(HERE/'contract.json'))
