"""Native port, density, garden, and finite approach ownership over sealed r05."""
import json,hashlib,math
from pathlib import Path
from functools import lru_cache
from world_city.concept_city_v3.registered_topography.revisions.r05_preview_lod import review as prior
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
HERE=Path(__file__).resolve().parent
R04=prior.prior;CITY=R04.CITY
REPORT_PATH=CITY/'validation/port_market/native_floor_section_report.json'
REPORT_SHA='06767506df19d2eaf5979dcb9aadc357f911026d1334e6f2035c32309b48cd4d'
if R04.sha(REPORT_PATH)!=REPORT_SHA:raise ValueError('Native port section snapshot changed')
REPORT=json.loads(REPORT_PATH.read_bytes())
PORT_PATH=CITY/'assemblies/landmarks/registered/port_r03_quay_unions/resolved_placements.json'
PORT_SHA='b3994a2f89e61a418508b266cd9b6de482a1797030b8f294298466a0065df81a'
DENSITY_PATH=CITY/'assemblies/ordinary/registered/r1/resolved_placements.json'
DENSITY_SHA='bd23a57dfdd0955dfd83c8ed3144d7d240ad5adf7de00674bfc66ada1914685a'
LANDSCAPE_PATH=CITY/'assemblies/landscape/registered/resolved_placements.json'
LANDSCAPE_SHA='b25daabb7e3af6412520aa0dfc1e014a3855dcbf6b9d3a069cf12bf2506bd324'
for path,sha in [(PORT_PATH,PORT_SHA),(DENSITY_PATH,DENSITY_SHA),(LANDSCAPE_PATH,LANDSCAPE_SHA)]:
 if R04.sha(path)!=sha:raise ValueError('Assembly snapshot changed: '+str(path))
PORT=json.loads(PORT_PATH.read_bytes());DENSITY=json.loads(DENSITY_PATH.read_bytes());LANDSCAPE=json.loads(LANDSCAPE_PATH.read_bytes())
COOWN_PATH=PORT_PATH.parent/'finite_coownership_addendum.json';COOWN=json.loads(COOWN_PATH.read_bytes())
FLOORS=[dict(f,owner_id=f['id']+':native_union',kind='native_port_hole',render_land=False,material_hint='none') for f in PORT['owned_floors']]
from . import approaches,landings
GROUNDS_PATH=DENSITY_PATH.parent/'owned_grounds.json'
GROUNDS_SHA='90d19bf887b2b959b80a76029adc04418e03397f7e80cdbbb313c3e786eedb51'
if R04.sha(GROUNDS_PATH)!=GROUNDS_SHA:raise ValueError('Density ground ledger changed')
GROUNDS=json.loads(GROUNDS_PATH.read_bytes())
EXCLUDED=tuple(sorted(set(R04.EXCLUDED)|set(DENSITY['replaced_placement_ids'])))
OWNERS=None;INDEX=None

def _owners():
 global OWNERS,INDEX
 if OWNERS is not None:return OWNERS
 out=[dict(r) for r in R04._owners() if r['kind']!='port_common_hole' and not R04.prior.is_excluded(r,EXCLUDED)]
 def add(p,**r):
  q=clean(p)
  if q:out.append(dict(polygon_xz_m=q,material_hint='stone',**r))
 quay=[r['polygon_xz_m'] for r in out if r['kind']=='road' and r.get('road_id')=='PORT_QUAY']
 for f in FLOORS:
  if f['datum']=='pier_top_plus2.2':continue
  add(f['polygon_xz_m'],owner_id=f['owner_id'],kind='native_port_hole',render_land=False,priority=19,floor_y_m=f['floor_y_m'])
  for i,p in enumerate(quay):
   q=clean(geo.convex_intersection(f['polygon_xz_m'],p))
   if q:add(q,owner_id=f['owner_id']+':QUAY:'+str(i),kind='native_port_hole',render_land=False,priority=9,floor_y_m=2.2,road_id='PORT_QUAY')
 for r in COOWN['shared_regions']:
  add(r['polygon_xz_m'],owner_id=r['id'],kind='native_port_hole',render_land=False,priority=5.5,floor_y_m=2.2,road_id='PORT_BRIDGE_TIE')
 for b in DENSITY['component_placements']:
  add(b['actual_body_footprint_xz_m'],owner_id=b['id']+':BODY',kind='building_body_hole',priority=20,render_land=False,floor_y_m=b['pad_floor_y_m'],asset_origin_y_m=b['position_m'][1],source_mass_id=b['source_mass_id'],native_plinth_bottom_y_m=b['position_m'][1])
 for d in DENSITY['access_proposals']:
  for i,p in enumerate(R04.old.corridor(d['cached_threshold_stub_xz_m'],d['width_m'])):
   add(p,owner_id=d['id']+':THRESHOLD:'+str(i),kind='door_landing',priority=30,render_land=True,floor_y_m=2.5,door_id=d['id'])
  for i,p in enumerate(d['reserved_connection_polygons_xz_m']):
   add(p,owner_id=d['id']+':ACCESS:'+str(i),kind='density_entry',priority=31,render_land=True,floor_y_m=2.5,door_id=d['id'],status='native finished-floor candidate; capsule review pending')
 for c in DENSITY['courts']:
  add(c['polygon_xz_m'],owner_id=c['id'],kind='density_court',priority=32,render_land=True,floor_y_m=c['finished_floor_y_m'])
 for c in DENSITY['court_paths']:
  for i,p in enumerate(c['reserved_polygons_xz_m']):add(p,owner_id=c['id']+':'+str(i),kind='density_court',priority=32,render_land=True,floor_y_m=c['finished_floor_y_m'])
 public=[p for e in LANDSCAPE['external_connections'] for r in e.get('external_surface',{}).get('public_surface_override_regions',[]) for p in r['polygons_xz_m']]
 for mask in LANDSCAPE['ownership_masks']:
  for i,f in enumerate(mask['compiled_upward_faces']):
   add(f['polygon_xz_m'],owner_id=mask['owner_id']+':face:'+str(i),kind='landscape_common_hole',priority=19,render_land=False,floor_y_m=f['y_m'])
   for j,p in enumerate(public):
    if not R04.base._overlap(R04.base._bounds(p),R04.base._bounds(f['polygon_xz_m'])):continue
    q=clean(geo.convex_intersection(f['polygon_xz_m'],p))
    if q:add(q,owner_id=mask['owner_id']+':public:'+str(i)+':'+str(j),kind='landscape_common_hole',priority=9,render_land=False,floor_y_m=f['y_m'],public_interface_status='actual common top owns finite overlap; external public-side profile remains unverified')
 out += approaches.MASKS+landings.MASKS
 OWNERS=sorted(out,key=lambda r:r['priority']);INDEX=geo._SpatialIndex(32)
 for i,r in enumerate(OWNERS):INDEX.add(i,r['polygon_xz_m'])
 return OWNERS

@lru_cache(maxsize=262144)
def owner_at(x,z):
 owners=_owners()
 for i in sorted(INDEX.candidates([[x,z]])):
  r=owners[i]
  if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-8):return r
 return dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot')

def surface_domains(bounds_xz_m,conform=True):
 owners=_owners();remaining=[R04.old.rect(bounds_xz_m)];out=[]
 for i in sorted(INDEX.candidates(remaining[0])):
  r=owners[i];new=[]
  for p in remaining:
   if not geo.positive_area_overlap(p,r['polygon_xz_m'],0):new.append(p);continue
   q=clean(geo.convex_intersection(p,r['polygon_xz_m']))
   if q:out.append(dict(r,polygon_xz_m=q,review_tile_bounds_xz_m=bounds_xz_m))
   new.extend(q for cut in geo.convex_difference(p,r['polygon_xz_m']) if(q:=clean(cut)))
  remaining=new
  if not remaining:break
 out.extend(dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot',polygon_xz_m=p,review_tile_bounds_xz_m=bounds_xz_m) for p in remaining)
 if not conform:return out
 x0,z0,x1,z1=bounds_xz_m;extra=[]
 for x in (x0,x1):extra+=prior.edge_knots('z',x,z0,z1)
 for z in (z0,z1):extra+=prior.edge_knots('x',z,x0,x1)
 return R04.old.conform_domains(out,extra+landings.boundary_knots(bounds_xz_m))

def surface_height_at(r,x,z):
 if r['kind']=='landmark_ramp_hole':return approaches.height_at(x,z)
 if r['kind']=='landmark_public_hole':return landings.height_at(x,z)
 if r['kind']=='road':
  y=landings.boundary_y(x,z)
  if y is not None:return y
 if r['kind'] in ('native_port_hole','landscape_common_hole','density_entry','density_court'):return r['floor_y_m']
 return prior.surface_height_at(r,x,z)
def source_surface_height_at(r,x,z):
 if r['kind']=='landmark_ramp_hole':return approaches.height_at(x,z)
 if r['kind']=='landmark_public_hole':return landings.height_at(x,z)
 if r['kind']=='road':
  y=landings.boundary_y(x,z)
  if y is not None:return y
 if r['kind'] in ('native_port_hole','landscape_common_hole','density_entry','density_court'):return r['floor_y_m']
 return prior.source_surface_height_at(r,x,z)
def height_at(x,z):
 r=owner_at(x,z);y=source_surface_height_at(r,x,z);return y-r['bed_depth_m'] if r['kind']=='water_hole' else y
def land_height_at(x,z):
 r=owner_at(x,z);return R04.base.land_height_at(x,z) if r['kind']=='water_hole' else source_surface_height_at(r,x,z)
road_height_at=prior.road_height_at;path_height_at=prior.path_height_at
def ordinary_foundation_contracts():return [r for r in prior.ordinary_foundation_contracts() if r['source_mass_id'] not in EXCLUDED]
def supplemental_surface_domains(bounds_xz_m=None):return approaches.supplemental_surface_domains(bounds_xz_m)+landings.supplemental_surface_domains(bounds_xz_m)
def supplemental_side_records(bounds_xz_m):return approaches.side_records(bounds_xz_m,owner_at,source_surface_height_at)
finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at;water_height_at=prior.water_height_at;river_water_y=prior.river_water_y

def retaining_interfaces(bounds,records=None):
 records=records if records is not None else surface_domains(bounds);out=[];seen=set()
 for r in records:
  poly=r['polygon_xz_m']
  for a,b in zip(poly,poly[1:]+poly[:1]):
   L=math.dist(a,b)
   if L<1e-7:continue
   key=tuple(sorted(tuple(round(v,7) for v in p) for p in (a,b)))
   if key in seen:continue
   seen.add(key);m=[(a[k]+b[k])/2 for k in (0,1)];n=[-(b[1]-a[1])/L*1e-5,(b[0]-a[0])/L*1e-5]
   owners=[owner_at(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)]
   if owners[0]['owner_id']==owners[1]['owner_id'] or any(o['kind'] in ('water_hole','property_common_hole','property_lane_handoff','bridge_hole','landmark_ramp_hole','landmark_public_hole','landscape_common_hole') for o in owners):continue
   ys=[[surface_height_at(dict(o,review_tile_bounds_xz_m=bounds),*p) for p in (a,b)] for o in owners]
   if max(abs(ys[0][i]-ys[1][i]) for i in (0,1))<1e-6:continue
   out.append(dict(id='R07_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],left_owner_id=owners[0]['owner_id'],right_owner_id=owners[1]['owner_id'],from_xz_m=a,to_xz_m=b,left_y_m=ys[0],right_y_m=ys[1],vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],thickness_m=.3,collision_semantics='finite native-floor terrain interface; no traversal claim'))
 return out

def actual_shared_port_regions():return COOWN['shared_regions']

def build_contract():
 c=json.loads((CITY/'registered_topography/revisions/r07_native_interfaces/contract.json').read_bytes())
 c['recovery_support']=approaches.recovery_record()
 c['landmark_approach_preview']=approaches.contract();c['landmark_public_landing_preview']=landings.contract()
 return c
