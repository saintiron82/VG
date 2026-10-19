"""Opt-in recovered training owner; frozen r08 is never mutated."""
import copy,json,hashlib
from functools import lru_cache
from . import author as a
from .recovery_support import author as prior
CITY=a.CITY;HERE=a.HERE;geo=a.geo;clean=a.clean;R04=prior.prior.R04
PATH=HERE/'resolved_placements.json';DATA=json.loads(PATH.read_bytes());OWNERS=[];INDEX=geo._SpatialIndex(8)
for i,f in enumerate(DATA['actual_public_surface_overrides']):OWNERS.append(dict(owner_id='R09_PUBLIC:'+str(i),kind='r09_training_native_hole',road_id=f['road_id'],priority=9,polygon_xz_m=f['polygon_xz_m'],floor_y_m=f['actual_compiled_top_y_m'],render_land=False,material_hint='stone'))
for m in DATA['ownership_masks']:
 if not m['owner_id'].startswith('TRAIN:r09:'):continue
 for i,f in enumerate(m['compiled_upward_faces']):OWNERS.append(dict(owner_id=m['owner_id']+':face:'+str(i),kind='r09_training_native_hole',priority=19,polygon_xz_m=f['polygon_xz_m'],floor_y_m=f['y_m'],render_land=False,material_hint=f['material']))
for i,r in enumerate(OWNERS):INDEX.add(i,r['polygon_xz_m'])
def stale(r):return r['kind']=='training_native_hole' and (r['owner_id'].startswith('TRAIN_PUBLIC_NATIVE:') or r['owner_id'].startswith('TRAIN:owned_ground:'))
def under(x,z):
 r=prior.prior.owner_at(x,z)
 if R04.prior.is_excluded(r,prior.training.EXCLUDED):r=R04.prior.owner_at(x,z,prior.training.EXCLUDED)
 return r

def allowed(r,f):
 if r['kind']=='water_hole':return False
 if r['kind']=='road':return f['priority']==9 and r.get('road_id')==f.get('road_id')
 return r.get('priority',100)>=19 or r['kind'] in ('ground','terrace','road_shoulder')
@lru_cache(maxsize=131072)
def owner_at(x,z):
 r=prior.owner_at(x,z)
 if stale(r):r=under(x,z)
 for i in sorted(INDEX.candidates([[x,z]])):
  f=OWNERS[i]
  if allowed(r,f) and geo.point_in_convex_polygon([x,z],f['polygon_xz_m'],1e-8):return f
 return r

def surface_domains(bounds,conform=True):
 old=prior.surface_domains(bounds,False);expanded=[];fallback=None
 for r in old:
  if not stale(r):expanded.append(r);continue
  if fallback is None:
   fallback=[]
   for q in prior.prior.surface_domains(bounds,False):
    if R04.prior.is_excluded(q,prior.training.EXCLUDED):fallback.extend(R04.prior._replacement_domains(q['polygon_xz_m'],bounds,prior.training.EXCLUDED))
    else:fallback.append(q)
  for q in fallback:
   p=clean(geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m']))
   if p:expanded.append(dict(q,polygon_xz_m=p))
 out=[]
 for r in expanded:
  parts=[r['polygon_xz_m']]
  for i in sorted(INDEX.candidates(r['polygon_xz_m'])):
   f=OWNERS[i]
   if not allowed(r,f):continue
   rest=[]
   for p in parts:
    q=clean(geo.convex_intersection(p,f['polygon_xz_m']))
    if q:
     out.append(dict(f,polygon_xz_m=q,review_tile_bounds_xz_m=bounds));rest.extend(t for cut in geo.convex_difference(p,f['polygon_xz_m']) if(t:=clean(cut)))
    else:rest.append(p)
   parts=rest
  out.extend(dict(r,polygon_xz_m=p) for p in parts)
 if not conform:return out
 extra=prior.landings.boundary_knots(bounds);x0,z0,x1,z1=bounds
 for x in (x0,x1):extra+=prior.prior.prior.edge_knots('z',x,z0,z1)
 for z in (z0,z1):extra+=prior.prior.prior.edge_knots('x',z,x0,x1)
 return R04.old.conform_domains(out,extra)

def source_surface_height_at(r,x,z):return r['floor_y_m'] if r['kind']=='r09_training_native_hole' else prior.source_surface_height_at(r,x,z)
def surface_height_at(r,x,z):return r['floor_y_m'] if r['kind']=='r09_training_native_hole' else prior.surface_height_at(r,x,z)
def height_at(x,z):
 r=owner_at(x,z);y=source_surface_height_at(r,x,z);return y-r['bed_depth_m'] if r['kind']=='water_hole' else y
def land_height_at(x,z):
 r=owner_at(x,z);return prior.land_height_at(x,z) if r['kind']=='water_hole' else source_surface_height_at(r,x,z)
road_height_at=prior.road_height_at;path_height_at=prior.path_height_at
ordinary_foundation_contracts=prior.ordinary_foundation_contracts
finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at;water_height_at=prior.water_height_at;river_water_y=prior.river_water_y
supplemental_surface_domains=prior.supplemental_surface_domains;supplemental_side_records=prior.supplemental_side_records

def retaining_interfaces(bounds,records=None):
 # Native training sides are already present in the common solid.
 rs=records if records is not None else surface_domains(bounds);out=[]
 for r in prior.retaining_interfaces(bounds,rs):
  v=r['vertices_xyz_m'];m=[sum(q[k] for q in v)/4 for k in (0,2)]
  if owner_at(*m)['kind']=='r09_training_native_hole':continue
  out.append(r)
 return out

def build_contract():
 c=prior.build_contract();c.update(schema='riverstone.registered_training_repair.r09.recovered.v1',revision='r09_training_access_recovered',review_module=__name__)
 c['training_native_interface']=dict(source_path=str(PATH.relative_to(CITY)),source_sha256=a.sha(PATH),reconstruction=DATA['reconstruction'],native_masks=DATA['ownership_masks'],actual_public_surface_overrides=DATA['actual_public_surface_overrides'],external_access_surfaces=DATA['external_access_surfaces'],replacement_native_placement_ids=DATA['replacement_native_placement_ids'],audit_path=str((HERE/'native_audit.json').relative_to(CITY)),audit_sha256=a.sha(HERE/'native_audit.json'),status='native geometry candidate; real125mm treads and measured public step; capsule/cart unverified')
 c['references'][str(PATH.relative_to(CITY))]=a.sha(PATH);c['module_sources'][str((HERE/'review.py').relative_to(CITY))]=a.sha(HERE/'review.py');c['exact_surface_ownership'].update(module=__name__);return c
if __name__=='__main__':a.write(HERE/'contract.json',build_contract());print(a.sha(HERE/'contract.json'))
