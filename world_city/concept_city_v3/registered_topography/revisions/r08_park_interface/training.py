"""Exact native training masks, with the sampled public tread explicitly failed."""
import json
from ..r07_native_interfaces import author as prior
geo=prior.geo;clean=prior.clean;CITY=prior.CITY
PATH=CITY/'assemblies/landscape/registered/training/resolved_placements.json'
SHA='9eb840f6710d24c028e61f66718689a04db00290d094c878d9a5dab0fa5035b8'
if prior.R04.sha(PATH)!=SHA:raise ValueError('Training pack changed')
DATA=json.loads(PATH.read_bytes());EXCLUDED=tuple(sorted(set(prior.EXCLUDED)|set(DATA['replacement_ledger']['source_building_ids'])))
OWNERS=[];INDEX=geo._SpatialIndex(16)
for i,f in enumerate(DATA['actual_public_surface_overrides']):
 OWNERS.append(dict(owner_id='TRAIN_PUBLIC_NATIVE:'+str(i),kind='training_native_hole',polygon_xz_m=f['polygon_xz_m'],floor_y_m=f['actual_compiled_top_y_m'],road_id=f['road_id'],priority=9,render_land=False,material_hint='stone',public_grade_status='FAILED native0.5m tread sampling; not a seamless public road'))
for m in DATA['ownership_masks']:
 for i,p in enumerate(m.get('terrain_exclusion_regions_xz_m',[])):
  OWNERS.append(dict(owner_id=m['owner_id']+':section:'+str(i),kind='training_native_hole',polygon_xz_m=p,floor_y_m=m['floor_y_m'],priority=19,render_land=False,material_hint='stone'))
 for i,f in enumerate(m.get('compiled_upward_faces',[])):
  OWNERS.append(dict(owner_id=m['owner_id']+':face:'+str(i),kind='training_native_hole',polygon_xz_m=f['polygon_xz_m'],floor_y_m=f['y_m'],priority=19,render_land=False,material_hint=f.get('material','earth')))
for i,r in enumerate(OWNERS):INDEX.add(i,r['polygon_xz_m'])
def allowed(source,overlay):
 if source['kind']=='water_hole':return False
 if source['kind']=='road':return overlay['priority']==9 and source.get('road_id')==overlay.get('road_id')
 return source.get('priority',100)>=19 or source['kind'] in ('ground','terrace','road_shoulder','building_body_hole','door_landing','door_approach')
def owner_overlay(r,x,z):
 if prior.R04.prior.is_excluded(r,EXCLUDED):r=prior.R04.prior.owner_at(x,z,EXCLUDED)
 for i in sorted(INDEX.candidates([[x,z]])):
  p=OWNERS[i]
  if allowed(r,p) and geo.point_in_convex_polygon([x,z],p['polygon_xz_m'],1e-8):return p
 return r

def overlay_domains(records,bounds):
 out=[];expanded=[]
 for r in records:
  if prior.R04.prior.is_excluded(r,EXCLUDED):expanded.extend(prior.R04.prior._replacement_domains(r['polygon_xz_m'],bounds,EXCLUDED))
  else:expanded.append(r)
 for r in expanded:
  remaining=[r['polygon_xz_m']]
  for i in sorted(INDEX.candidates(r['polygon_xz_m'])):
   f=OWNERS[i]
   if not allowed(r,f):continue
   rest=[]
   for p in remaining:
    q=clean(geo.convex_intersection(p,f['polygon_xz_m']))
    if q:
     out.append(dict(f,polygon_xz_m=q,review_tile_bounds_xz_m=bounds));rest.extend(t for cut in geo.convex_difference(p,f['polygon_xz_m']) if(t:=clean(cut)))
    else:rest.append(p)
   remaining=rest
  out.extend(dict(r,polygon_xz_m=p) for p in remaining)
 return out

def contract():
 return dict(source_path=str(PATH.relative_to(CITY)),source_sha256=SHA,replacements=DATA['replacement_ledger'],native_masks=DATA['ownership_masks'],actual_public_surface_overrides=DATA['actual_public_surface_overrides'],external_access_surfaces=DATA['external_access_surfaces'],status='exact native geometry ownership for visual review; public native0.5m sampled tread handoff FAILED and needs bounded correction',public_failure='One occupied native tread reaches18.5m against the source edge around18.29m. Other native tread portions are18m. These are actual occupied masks, not a continuous walking datum; do not raise the whole road to conceal them.')
