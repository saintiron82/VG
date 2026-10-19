"""Finite native park spill ownership and continuous adjacent grade repair."""
import json,math,hashlib
from pathlib import Path
from functools import lru_cache
from ..r07_native_interfaces import author as prior
from . import approaches,landings,training
geo=prior.geo;clean=prior.clean;HERE=Path(__file__).resolve().parent;CITY=prior.CITY
REPORT_PATH=CITY/'validation/evidence/registered_landscape_b25daabb7e3a_1d73da4f2fa6.json'
REPORT=json.loads(REPORT_PATH.read_bytes())
RESERVOIR_PATH=CITY/'assemblies/waterworks/registered_reservoir/resolved_placements.json'
RESERVOIR_SHA='cf868c32b145acae0b81a06d6c136db29e1e68c85ff3e9e417e67d63e6aeacdf'
if prior.R04.sha(RESERVOIR_PATH)!=RESERVOIR_SHA:raise ValueError('Reservoir snapshot changed')
RESERVOIR=json.loads(RESERVOIR_PATH.read_bytes());RESERVOIR_OWNERS=[];RESERVOIR_INDEX=geo._SpatialIndex(16)
for f in RESERVOIR['owned_floors']:
 RESERVOIR_OWNERS.append(dict(owner_id=f['id'],kind='reservoir_native_hole',polygon_xz_m=f['polygon_xz_m'],floor_y_m=f['floor_y_m'],render_land=False,material_hint='stone'))
for r in RESERVOIR['terrain_excavation_requests']:
 parts=[r['polygon_xz_m']]
 for p in r['exclude_road_keepouts_xz_m']:
  parts=[q for poly in parts for cut in geo.convex_difference(poly,p) if(q:=clean(cut))]
 for i,p in enumerate(parts):RESERVOIR_OWNERS.append(dict(owner_id=r['id']+':'+str(i),kind='reservoir_excavation_hole',polygon_xz_m=p,floor_y_m=r['bottom_y_m'],top_y_m=r['top_y_m'],render_land=False,material_hint='none'))
for i,r in enumerate(RESERVOIR_OWNERS):RESERVOIR_INDEX.add(i,r['polygon_xz_m'])
ROI=[-265,-49,-244,-44];ROAD='WEST_MONASTERY_EDGE';TOP=8.;GRADE=.12
COMMON=[]
for m in prior.LANDSCAPE['ownership_masks']:
 if not m['owner_id'].endswith('SITE_COMMON'):continue
 for i,f in enumerate(m['compiled_upward_faces']):
  if abs(f['y_m']-TOP)>1e-7 or not prior.R04.base._overlap(ROI,prior.R04.base._bounds(f['polygon_xz_m'])):continue
  for j,r in enumerate(prior._owners()):
   if r['kind']!='road' or r.get('road_id')!=ROAD:continue
   q=clean(geo.convex_intersection(f['polygon_xz_m'],r['polygon_xz_m']))
   if q:COMMON.append(dict(owner_id='PARK_NATIVE_ROAD:'+str(i)+':'+str(j),kind='park_native_common_hole',road_id=ROAD,polygon_xz_m=q,material_hint='stone',render_land=False,floor_y_m=TOP))
if not COMMON:raise ValueError('No native park/public interface')
# Source road segment ribbons overlap at bends. Publish one disjoint common
# union rather than counting those logical reservations twice.
_disjoint=[]
for r in COMMON:
 parts=[r['polygon_xz_m']]
 for previous in _disjoint:
  parts=[q for p in parts for cut in geo.convex_difference(p,previous['polygon_xz_m']) if(q:=clean(cut))]
 _disjoint.extend(dict(r,owner_id=r['owner_id']+':piece:'+str(i),polygon_xz_m=p) for i,p in enumerate(parts))
COMMON=_disjoint
xs=[p[0] for r in COMMON for p in r['polygon_xz_m']];zs=[p[1] for r in COMMON for p in r['polygon_xz_m']]
BOUNDS=[min(xs)-24,min(zs)-24,max(xs)+24,max(zs)+24];BOX=prior.R04.old.rect(BOUNDS)

def distance_to_native(x,z):
 result=float('inf')
 for r in COMMON:
  p=r['polygon_xz_m']
  if geo.point_in_convex_polygon([x,z],p,1e-10):return 0.
  result=min(result,min(prior.R04.base._project(x,z,a,b)[0] for a,b in zip(p,p[1:]+p[:1])))
 return result

def eligible(r):return r['kind'] in ('ground','terrace') or (r['kind'] in ('road','road_shoulder') and r.get('road_id')==ROAD)
def inside_bounds(x,z):return BOUNDS[0]-1e-8<=x<=BOUNDS[2]+1e-8 and BOUNDS[1]-1e-8<=z<=BOUNDS[3]+1e-8

def transition(r,p=None):return dict(owner_id='PARK_TRANSITION:'+r['owner_id'],kind='park_grade_transition',underlying_record=r,road_id=r.get('road_id'),material_hint=r.get('material_hint','ground'),render_land=True,polygon_xz_m=p or BOX,review_tile_bounds_xz_m=r.get('review_tile_bounds_xz_m'))
@lru_cache(maxsize=131072)
def owner_at(x,z):
 if inside_bounds(x,z):
  for r in COMMON:
   if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-8):return r
 r=training.owner_overlay(prior.owner_at(x,z),x,z)
 if r['kind'] in ('ground','terrace','road_shoulder'):
  for i in sorted(RESERVOIR_INDEX.candidates([[x,z]])):
   f=RESERVOIR_OWNERS[i]
   if geo.point_in_convex_polygon([x,z],f['polygon_xz_m'],1e-8):return f
 return transition(r) if inside_bounds(x,z) and eligible(r) else r

def source_surface_height_at(r,x,z):
 if r['kind']=='landmark_ramp_hole':return approaches.height_at(x,z)
 if r['kind']=='landmark_public_hole':return landings.height_at(x,z)
 if r['kind']=='road':
  y=landings.boundary_y(x,z)
  if y is not None:return y
 if r['kind']=='park_native_common_hole':return TOP
 if r['kind'] in ('reservoir_native_hole','reservoir_excavation_hole','training_native_hole'):return r['floor_y_m']
 if r['kind']=='park_grade_transition':
  h=prior.source_surface_height_at(r['underlying_record'],x,z);d=distance_to_native(x,z)
  return min(TOP+GRADE*d,max(TOP-GRADE*d,h))
 return prior.source_surface_height_at(r,x,z)

def surface_height_at(r,x,z):
 if r['kind']=='landmark_ramp_hole':return approaches.height_at(x,z)
 if r['kind']=='landmark_public_hole':return landings.height_at(x,z)
 if r['kind']=='road':
  y=landings.boundary_y(x,z)
  if y is not None:return y
 if r['kind']=='park_grade_transition':
  if distance_to_native(x,z)<1e-7:return TOP
  b=r.get('review_tile_bounds_xz_m')
  if b:
   if abs(x-b[0])<1e-7 or abs(x-b[2])<1e-7:
    lo=math.floor(z*4+1e-8)/4;t=max(0,min(1,4*(z-lo)));return (1-t)*source_surface_height_at(r,x,lo)+t*source_surface_height_at(r,x,lo+.25)
   if abs(z-b[1])<1e-7 or abs(z-b[3])<1e-7:
    lo=math.floor(x*4+1e-8)/4;t=max(0,min(1,4*(x-lo)));return (1-t)*source_surface_height_at(r,lo,z)+t*source_surface_height_at(r,lo+.25,z)
  return source_surface_height_at(r,x,z)
 if r['kind'] in ('reservoir_native_hole','reservoir_excavation_hole','training_native_hole'):return r['floor_y_m']
 return prior.surface_height_at(r,x,z) if r['kind']!='park_native_common_hole' else TOP

def surface_domains(bounds_xz_m,conform=True):
 out=[]
 for r in training.overlay_domains(prior.surface_domains(bounds_xz_m,False),bounds_xz_m):
  remaining=[r['polygon_xz_m']]
  if r['kind'] in ('ground','terrace','road_shoulder'):
   for i in sorted(RESERVOIR_INDEX.candidates(r['polygon_xz_m'])):
    f=RESERVOIR_OWNERS[i];rest=[]
    for p in remaining:
     q=clean(geo.convex_intersection(p,f['polygon_xz_m']))
     if q:
      out.append(dict(f,polygon_xz_m=q,review_tile_bounds_xz_m=bounds_xz_m));rest.extend(t for cut in geo.convex_difference(p,f['polygon_xz_m']) if(t:=clean(cut)))
     else:rest.append(p)
    remaining=rest
  # Exact native top replaces only its declared public overlap. Water, bodies,
  # unrelated traffic, and other common sources keep their prior ownership.
  if r.get('road_id')==ROAD and r['kind']=='road':
   for f in COMMON:
    rest=[]
    for p in remaining:
     q=clean(geo.convex_intersection(p,f['polygon_xz_m']))
     if q:
      out.append(dict(f,polygon_xz_m=q,review_tile_bounds_xz_m=bounds_xz_m));rest.extend(t for cut in geo.convex_difference(p,f['polygon_xz_m']) if(t:=clean(cut)))
     else:rest.append(p)
    remaining=rest
  for p in remaining:
   q=clean(geo.convex_intersection(p,BOX)) if eligible(r) else None
   if q:
    out.append(transition(r,q));out.extend(dict(r,polygon_xz_m=t) for cut in geo.convex_difference(p,BOX) if(t:=clean(cut)))
   else:out.append(dict(r,polygon_xz_m=p))
 if not conform:return out
 extra=landings.boundary_knots(bounds_xz_m)
 x0,z0,x1,z1=bounds_xz_m
 for x in (x0,x1):extra+=prior.prior.edge_knots('z',x,z0,z1)
 for z in (z0,z1):extra+=prior.prior.edge_knots('x',z,x0,x1)
 if prior.R04.base._overlap(bounds_xz_m,BOUNDS):
  for i in range(math.ceil(z0*4),math.floor(z1*4)+1):extra.extend([[x0,i/4],[x1,i/4]])
  for i in range(math.ceil(x0*4),math.floor(x1*4)+1):extra.extend([[i/4,z0],[i/4,z1]])
 return prior.R04.old.conform_domains(out,extra)

def height_at(x,z):
 r=owner_at(x,z);y=source_surface_height_at(r,x,z);return y-r['bed_depth_m'] if r['kind']=='water_hole' else y
def land_height_at(x,z):
 r=owner_at(x,z);return prior.land_height_at(x,z) if r['kind']=='water_hole' else source_surface_height_at(r,x,z)
def road_height_at(id,x,z):
 old=prior.road_height_at(id,x,z)
 if id!=ROAD or not inside_bounds(x,z):return old
 d=distance_to_native(x,z);return min(TOP+GRADE*d,max(TOP-GRADE*d,old))
# Existing exact source profiles are retained verbatim.
path_height_at=prior.path_height_at
def supplemental_surface_domains(bounds_xz_m=None):return approaches.supplemental_surface_domains(bounds_xz_m)+landings.supplemental_surface_domains(bounds_xz_m)
def supplemental_side_records(bounds_xz_m):return approaches.side_records(bounds_xz_m,owner_at,source_surface_height_at)
def ordinary_foundation_contracts():return [r for r in prior.ordinary_foundation_contracts() if r['source_mass_id'] not in training.EXCLUDED]
finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at;water_height_at=prior.water_height_at;river_water_y=prior.river_water_y

def retaining_interfaces(bounds,records=None):
 # Same bounded interface algorithm, evaluated with this adapter's owner API.
 rs=records if records is not None else surface_domains(bounds);out=[];seen=set()
 for r in rs:
  p=r['polygon_xz_m']
  for a,b in zip(p,p[1:]+p[:1]):
   L=math.dist(a,b)
   if L<1e-7:continue
   key=tuple(sorted(tuple(round(v,7) for v in q) for q in (a,b)))
   if key in seen:continue
   seen.add(key);m=[(a[k]+b[k])/2 for k in (0,1)];n=[-(b[1]-a[1])/L*1e-5,(b[0]-a[0])/L*1e-5]
   owners=[owner_at(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)]
   if owners[0]['owner_id']==owners[1]['owner_id'] or any(o['kind'] in ('water_hole','property_common_hole','property_lane_handoff','bridge_hole','landmark_ramp_hole','landmark_public_hole','landscape_common_hole','reservoir_native_hole','reservoir_excavation_hole','training_native_hole') for o in owners):continue
   ys=[[surface_height_at(dict(o,review_tile_bounds_xz_m=bounds),*q) for q in (a,b)] for o in owners]
   if max(abs(ys[0][i]-ys[1][i]) for i in (0,1))<1e-6:continue
   out.append(dict(id='R08_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],left_owner_id=owners[0]['owner_id'],right_owner_id=owners[1]['owner_id'],vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],material_hint='stone',thickness_m=.3,collision_semantics='finite source interface; no traversal claim'))
 return out

def build_contract():
 c=prior.build_contract();c['revision']='r08_park_interface';c['schema']='riverstone.registered_park_interface.r08.v1';c['review_module']='world_city.concept_city_v3.registered_topography.revisions.r08_park_interface.author'
 c['park_native_interface']=dict(report_path=str(REPORT_PATH.relative_to(CITY)),report_sha256=prior.R04.sha(REPORT_PATH),extra_native_overlap_m2=sum(r['unowned_overlap_area_m2'] for r in REPORT['mask_lane_conflicts']),native_common_public_regions=COMMON,correction_bounds_xz_m=BOUNDS,floor_y_m=TOP,analytic_road_grade_bound=GRADE,formula='clamp inherited H to [8−0.12 distance,8+0.12 distance] from the exact native common/public union',scope='The actual road lane remains travel-reserved with one visible common owner. Adjacent road/shoulder and unoccupied ground receive a bounded continuous source field. Other bodies/common floors/water retain ownership.',preview_status='source field/ownership; actual finite preview triangle gradients and capsule traversal unverified')
 c['landmark_approach_preview']=approaches.contract();c['landmark_public_landing_preview']=landings.contract()
 c['superseded_landmark_profile_sources']=[prior.approaches.SHA,prior.landings.SHA]
 c['training_native_interface']=training.contract();c['excluded_source_ids']=list(training.EXCLUDED);c['ordinary_foundations']=ordinary_foundation_contracts()
 c['exact_surface_ownership'].update(module=c['review_module'],excluded_source_ids=list(training.EXCLUDED),configuration='explicit additive registered native ownership; standard surface_domains / height APIs')
 c['exclusion_ledger'] += [dict(source_mass_id=id,reason='native training replacement',removed_owner_kinds=['body','door','support'],replacement_source_sha256=training.SHA) for id in training.DATA['replacement_ledger']['source_building_ids']]
 c['references'][str(training.PATH.relative_to(CITY))]=training.SHA
 for p in (HERE/'approaches.py',HERE/'landings.py',HERE/'training.py'):c['module_sources'][str(p.relative_to(CITY))]=prior.R04.sha(p)
 for p in (approaches.PATH,landings.PATH):c['references'][str(p.relative_to(CITY))]=prior.R04.sha(p)
 c['omit_source_waterbed_polygons']=[dict(r,surface_id='NORTHERN_RESERVOIR') for r in RESERVOIR['native_bed_masks']]
 c['omitted_water_bank_indices']=[r['contract_index'] for r in RESERVOIR['superseded_reservoir_bank_faces']]
 c['reservoir_native_interface']=dict(source_path=str(RESERVOIR_PATH.relative_to(CITY)),source_sha256=RESERVOIR_SHA,dry_floors=RESERVOIR['owned_floors'],finite_excavations=RESERVOIR['terrain_excavation_requests'],effective_excavation_polygons=[r for r in RESERVOIR_OWNERS if r['kind']=='reservoir_excavation_hole'],pending_access_links=RESERVOIR['access_links'],policy='Water top remains unchanged. Omit only the exact native bed masks and47 indexed original banks. Dry native floors and native hollow-volume excavation exclude road keepouts. The tiny service entrance handoff remains an explicit pending source profile.')
 c['references'][str(RESERVOIR_PATH.relative_to(CITY))]=RESERVOIR_SHA
 c['common_framework_next_milestone_plan']=dict(path=str((HERE/'common_export_plan.json').relative_to(CITY)),sha256=prior.R04.sha(HERE/'common_export_plan.json'),status='budgeted source plan only; no compilation scheduled')
 c['module_sources'][str((HERE/'author.py').relative_to(CITY))]=prior.R04.sha(HERE/'author.py');c['references'][str(REPORT_PATH.relative_to(CITY))]=prior.R04.sha(REPORT_PATH)
 return c
if __name__=='__main__':
 c=build_contract();(HERE/'contract.json').write_text(json.dumps(c,indent=2)+'\n');print(json.dumps(dict(author_sha256=prior.R04.sha(HERE/'author.py'),contract_sha256=prior.R04.sha(HERE/'contract.json'),common_regions=len(COMMON),bounds=BOUNDS)))
