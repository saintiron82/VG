"""Recovered bounded B015, reservoir service and southern-road terrain adapter.
All earlier snapshots remain immutable. Exact finite source/native domains only.
"""
import json,math,hashlib,copy
from pathlib import Path
from functools import lru_cache
from ..r09_training_access import review as prior
HERE=Path(__file__).resolve().parent;CITY=prior.CITY;ROOT=CITY.parents[1];R04=prior.R04;geo=prior.geo;clean=prior.clean
DENSITY_PATH=CITY/'assemblies/property/registered/poor_block015_east/route_repair_01/effective_placements.json';DENSITY_SHA='3f0a643e7bfe476a47e69c44f8d64cf3ce67998e94074bc3dec17011b802a604'
SERVICE_PATH=CITY/'assemblies/waterworks/registered_reservoir/service_r02/resolved_placements.json';SERVICE_SHA='85f6e928b6702fbe26c12996adc2329fff0d91876868c93c5fbe73d3f9a346f9'
HANDOFF_PATH=CITY/'assemblies/waterworks/registered_reservoir/public_access_handoff.json';HANDOFF_SHA='67d8cdffd68b2ac0ef4b6b435bb7642d99e61e26397be31751566a15ebc59f8e'
SOUTH_PATH=CITY/'registered_topography/road_extensions/south_country_r1/contract.json';SOUTH_SHA='1e54db2129ff0342582cc289f591b40feb21ea6cc1c92008227964472f1e7c33'
for p,h in [(DENSITY_PATH,DENSITY_SHA),(SERVICE_PATH,SERVICE_SHA),(HANDOFF_PATH,HANDOFF_SHA),(SOUTH_PATH,SOUTH_SHA)]:
 if R04.sha(p)!=h:raise ValueError('Changed source '+str(p))
DENSITY=json.loads(DENSITY_PATH.read_bytes());SERVICE=json.loads(SERVICE_PATH.read_bytes());HANDOFF=json.loads(HANDOFF_PATH.read_bytes());SOUTH=json.loads(SOUTH_PATH.read_bytes())
EXCLUDED=tuple(sorted(set(prior.prior.training.EXCLUDED)|set(DENSITY['replaced_placement_ids'])))
ROAD='RESERVOIR_SERVICE';TOP=18.;GRADE=.12;OWNERS=[];INDEX=geo._SpatialIndex(16)

def add(poly,**kw):
 p=clean(poly)
 if p:OWNERS.append(dict(polygon_xz_m=p,material_hint='stone',**kw))
for m in DENSITY['ownership_masks']:
 for i,p in enumerate(m['terrain_exclusion_regions_xz_m']):add(p,owner_id=m['owner_id']+':native:'+str(i),kind='b015_native_hole',priority=19,render_land=False,floor_y_m=m['floor_y_m'],native_bottom_y_m=m['floor_y_m']-m['foundation_embed_m'])
for d in DENSITY['access_proposals']:
 for i,p in enumerate(R04.old.corridor(d['cached_threshold_stub_xz_m'],d['width_m'])):add(p,owner_id=d['id']+':threshold:'+str(i),kind='b015_entry',priority=30,render_land=True,floor_y_m=2.5,door_id=d['id'])
 for i,p in enumerate(d['reserved_connection_polygons_xz_m']+d.get('reserved_round_join_polygons_xz_m',[])):add(p,owner_id=d['id']+':approach:'+str(i),kind='b015_entry',priority=31,render_land=True,floor_y_m=2.5,door_id=d['id'])
for d in DENSITY['courts']:add(d['polygon_xz_m'],owner_id=d['id'],kind='b015_court',priority=32,render_land=True,floor_y_m=d['finished_floor_y_m'])
for d in DENSITY['court_paths']+DENSITY['ground_service_paths']:
 for i,p in enumerate(d['reserved_polygons_xz_m']+d.get('reserved_round_join_polygons_xz_m',[])):add(p,owner_id=d['id']+':'+str(i),kind='b015_court',priority=32,render_land=True,floor_y_m=d['finished_floor_y_m'])
# Only newly introduced native dry floor pieces; old base masks retain identity.
BASE_IDS={r['id'] for r in prior.prior.RESERVOIR['owned_floors']}
for f in SERVICE['owned_floors']:
 if f['id'] not in BASE_IDS:add(f['polygon_xz_m'],owner_id=f['id'],kind='reservoir_service_native_hole',priority=19,render_land=False,floor_y_m=f['floor_y_m'])
for f in HANDOFF['terrain_owned_handoff_pieces']:add(f['polygon_xz_m'],owner_id=f['id'],kind='reservoir_service_handoff',priority=18,render_land=True,floor_y_m=TOP)
for f in SOUTH['triangles']:add(f['polygon_xz_m'],owner_id=f['owner_id'],kind='external_triangular_surface',priority=4.9,render_land=True,material='road',road_id=SOUTH['route_id'],triangle_xyz_m=f['vertices_xyz_m'],replaces_road_ids=['MAIN_BRIDGE'],stale_bridge_tail_permission=True)
# Actual rounded road end is broader than the source's uncapped segment strips.
# Split its precise overlap with the complete1.4m route at +18.
route=HANDOFF['replacement_route'];ROUTE_POLYS=list(R04.old.corridor([[p[0],p[2]] for p in route['points_xyz_m']],route['width_m']))
PUBLIC_FLAT=[];r07=prior.prior.prior
for r in r07._owners():
 if r['kind']!='road' or r.get('road_id')!=ROAD:continue
 for p in ROUTE_POLYS:
  q=clean(geo.convex_intersection(p,r['polygon_xz_m']))
  if q:
   pieces=[q]
   for previous in PUBLIC_FLAT:pieces=[t for s in pieces for c in geo.convex_difference(s,previous['polygon_xz_m']) if(t:=clean(c))]
   for q in pieces:PUBLIC_FLAT.append(dict(owner_id=r['owner_id'],profile_domain_id='R10_PUBLIC_FLAT:'+str(len(PUBLIC_FLAT)),kind='reservoir_service_public_landing',road_id=ROAD,priority=9,render_land=True,material_hint='road',floor_y_m=TOP,polygon_xz_m=q,replaces_road_ids=[ROAD]))
OWNERS+=PUBLIC_FLAT
OWNERS.sort(key=lambda r:r['priority'])
for i,r in enumerate(OWNERS):INDEX.add(i,r['polygon_xz_m'])
SEEDS=[r['polygon_xz_m'] for r in PUBLIC_FLAT]+[r['polygon_xz_m'] for r in HANDOFF['terrain_owned_handoff_pieces']]
pts=[p for q in SEEDS for p in q];BOUNDS=[min(p[0] for p in pts)-12,min(p[1] for p in pts)-12,max(p[0] for p in pts)+12,max(p[1] for p in pts)+12];BOX=R04.old.rect(BOUNDS)
# Parent authorized restoration only beyond the actual native stone end X=72.
POSE=[129.19202282001814,0,490.7221468911664];U=[.13324547051159727,.9910830664420328];V=[-.9910830664420328,.13324547051159727]
def bridge_world(x,z):return [POSE[0]+x*U[0]+z*V[0],POSE[2]+x*U[1]+z*V[1]]
TAIL_CLIP=[bridge_world(x,z) for x,z in ((72,-20),(100,-20),(100,20),(72,20))]
TAIL_GROUND=dict(owner_id='R10_RESTORED_SOUTH_SHOULDER',kind='ground',priority=100,render_land=True,material_hint='ground')
def stale_tail(r):return (r['kind']=='bridge_hole' and r['owner_id'].startswith('MAIN_BRIDGE')) or (r['kind'] in ('road','road_shoulder') and r.get('road_id')=='MAIN_BRIDGE')
def inside_bounds(x,z):return BOUNDS[0]-1e-8<=x<=BOUNDS[2]+1e-8 and BOUNDS[1]-1e-8<=z<=BOUNDS[3]+1e-8
@lru_cache(maxsize=65536)
def seed_distance(x,z):
 result=math.inf
 for p in SEEDS:
  if geo.point_in_convex_polygon([x,z],p,1e-10):return 0.
  result=min(result,min(R04.base._project(x,z,a,b)[0] for a,b in zip(p,p[1:]+p[:1])))
 return result

def eligible_transition(r):return r['kind'] in ('ground','terrace') or(r['kind'] in ('road','road_shoulder') and r.get('road_id')==ROAD)
def transition(r,p=None):return dict(owner_id='R10_RESERVOIR_BLEND:'+r['owner_id'],kind='reservoir_service_transition',underlying_record=r,road_id=r.get('road_id'),material_hint=r.get('material_hint','ground'),render_land=True,polygon_xz_m=p or BOX,review_tile_bounds_xz_m=r.get('review_tile_bounds_xz_m'))
def can_overlay(r,f):
 if r['kind']=='water_hole':return False
 if r['kind']=='bridge_hole':return f.get('stale_bridge_tail_permission',False) and stale_tail(r)
 if r['kind']=='road':return r.get('road_id') in f.get('replaces_road_ids',[])
 if r['kind']=='reservoir_excavation_hole':return f['kind'] in ('reservoir_service_native_hole','reservoir_service_handoff')
 if not r.get('render_land',True):return False
 return f.get('priority',50)<r.get('priority',100) or r['kind'] in ('ground','terrace','road_shoulder')
def restored_owner(r,x,z):
 if R04.prior.is_excluded(r,EXCLUDED):r=R04.prior.owner_at(x,z,EXCLUDED)
 if stale_tail(r) and geo.point_in_convex_polygon([x,z],TAIL_CLIP,1e-8):return TAIL_GROUND
 return r
@lru_cache(maxsize=131072)
def owner_at(x,z):
 r=restored_owner(prior.owner_at(x,z),x,z)
 for i in sorted(INDEX.candidates([[x,z]])):
  f=OWNERS[i]
  if can_overlay(r,f) and geo.point_in_convex_polygon([x,z],f['polygon_xz_m'],1e-8):return f
 return transition(r) if inside_bounds(x,z) and eligible_transition(r) else r

def insert_finite_domains(records,bounds,extra_owners):
 out=[];idx=geo._SpatialIndex(16)
 for i,f in enumerate(extra_owners):idx.add(i,f['polygon_xz_m'])
 for r in records:
  parts=[r['polygon_xz_m']]
  for i in sorted(idx.candidates(r['polygon_xz_m'])):
   f=extra_owners[i]
   if not can_overlay(r,f):continue
   new=[]
   for p in parts:
    q=clean(geo.convex_intersection(p,f['polygon_xz_m']))
    if q:
     out.append(dict(f,polygon_xz_m=q,review_tile_bounds_xz_m=bounds));new.extend(t for cut in geo.convex_difference(p,f['polygon_xz_m']) if(t:=clean(cut)))
    else:new.append(p)
   parts=new
  out.extend(dict(r,polygon_xz_m=p) for p in parts)
 return out

def surface_domains(bounds,conform=True):
 expanded=[]
 for r in prior.surface_domains(bounds,False):
  rs=R04.prior._replacement_domains(r['polygon_xz_m'],bounds,EXCLUDED) if R04.prior.is_excluded(r,EXCLUDED) else [r]
  for q in rs:
   p=clean(geo.convex_intersection(q['polygon_xz_m'],TAIL_CLIP)) if stale_tail(q) else None
   if p:
    expanded.append(dict(TAIL_GROUND,polygon_xz_m=p,review_tile_bounds_xz_m=bounds));expanded.extend(dict(q,polygon_xz_m=t) for cut in geo.convex_difference(q['polygon_xz_m'],TAIL_CLIP) if(t:=clean(cut)))
   else:expanded.append(q)
 out=[]
 for r in insert_finite_domains(expanded,bounds,OWNERS):
  p=clean(geo.convex_intersection(r['polygon_xz_m'],BOX)) if eligible_transition(r) else None
  if p:
   out.append(transition(r,p));out.extend(dict(r,polygon_xz_m=t) for cut in geo.convex_difference(r['polygon_xz_m'],BOX) if(t:=clean(cut)))
  else:out.append(r)
 if not conform:return out
 extra=prior.prior.landings.boundary_knots(bounds);x0,z0,x1,z1=bounds
 for x in (x0,x1):extra+=prior.prior.prior.prior.edge_knots('z',x,z0,z1)
 for z in (z0,z1):extra+=prior.prior.prior.prior.edge_knots('x',z,x0,x1)
 if R04.base._overlap(bounds,BOUNDS):
  for i in range(math.ceil(z0*4),math.floor(z1*4)+1):extra.extend([[x0,i/4],[x1,i/4]])
  for i in range(math.ceil(x0*4),math.floor(x1*4)+1):extra.extend([[i/4,z0],[i/4,z1]])
 return R04.old.conform_domains(out,extra)

def source_surface_height_at(r,x,z):
 if r['kind']=='external_triangular_surface':return R04.point_y(r['triangle_xyz_m'],x,z)
 if r['kind']=='reservoir_service_transition':return max(prior.source_surface_height_at(r['underlying_record'],x,z),TOP-GRADE*seed_distance(x,z))
 if r['kind'] in ('b015_native_hole','b015_entry','b015_court','reservoir_service_native_hole','reservoir_service_handoff','reservoir_service_public_landing','external_flat_surface'):return r['floor_y_m']
 return prior.source_surface_height_at(r,x,z)
def surface_height_at(r,x,z):
 if r['kind']=='reservoir_service_transition':
  b=r.get('review_tile_bounds_xz_m')
  if b:
   if abs(x-b[0])<1e-7 or abs(x-b[2])<1e-7:
    lo=math.floor(z*4+1e-8)/4;t=max(0,min(1,4*(z-lo)));return (1-t)*source_surface_height_at(r,x,lo)+t*source_surface_height_at(r,x,lo+.25)
   if abs(z-b[1])<1e-7 or abs(z-b[3])<1e-7:
    lo=math.floor(x*4+1e-8)/4;t=max(0,min(1,4*(x-lo)));return (1-t)*source_surface_height_at(r,lo,z)+t*source_surface_height_at(r,lo+.25,z)
 if r['kind'].startswith('b015_') or r['kind'].startswith('reservoir_service_') or r['kind'].startswith('external_'):return source_surface_height_at(r,x,z)
 return prior.surface_height_at(r,x,z)
def height_at(x,z):
 r=owner_at(x,z);y=source_surface_height_at(r,x,z);return y-r['bed_depth_m'] if r['kind']=='water_hole' else y
def land_height_at(x,z):
 r=owner_at(x,z);return prior.land_height_at(x,z) if r['kind']=='water_hole' else source_surface_height_at(r,x,z)
def road_height_at(id,x,z):
 if id==SOUTH['route_id']:
  for r in OWNERS:
   if r.get('road_id')==id and geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-7):return source_surface_height_at(r,x,z)
  raise ValueError('Outside finite south road')
 h=prior.road_height_at(id,x,z)
 return max(h,TOP-GRADE*seed_distance(x,z)) if id==ROAD and inside_bounds(x,z) else h
path_height_at=prior.path_height_at
finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at;water_height_at=prior.water_height_at;river_water_y=prior.river_water_y
supplemental_surface_domains=prior.supplemental_surface_domains;supplemental_side_records=prior.supplemental_side_records
ordinary_foundation_contracts=lambda:[r for r in prior.ordinary_foundation_contracts() if r['source_mass_id'] not in EXCLUDED]

def retaining_interfaces(bounds,records=None):
 rs=records if records is not None else surface_domains(bounds);out=[];seen=set()
 for r in rs:
  p=r['polygon_xz_m']
  for a,b in zip(p,p[1:]+p[:1]):
   L=math.dist(a,b)
   if L<1e-7:continue
   key=tuple(sorted(tuple(round(v,7) for v in q) for q in (a,b)))
   if key in seen:continue
   seen.add(key);m=[(a[k]+b[k])/2 for k in (0,1)];n=[-(b[1]-a[1])/L*1e-5,(b[0]-a[0])/L*1e-5];os=[owner_at(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)]
   if os[0]['owner_id']==os[1]['owner_id'] or any(not o.get('render_land',True) for o in os):continue
   ys=[[surface_height_at(dict(o,review_tile_bounds_xz_m=bounds),*q) for q in (a,b)] for o in os]
   if max(abs(ys[0][i]-ys[1][i]) for i in (0,1))<1e-6:continue
   out.append(dict(id='R10_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],left_owner_id=os[0]['owner_id'],right_owner_id=os[1]['owner_id'],vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],material_hint='stone',thickness_m=.3,collision_semantics='visible finite cut/fill closure; no capsule approval'))
 return out

def build_contract():
 c=copy.deepcopy(prior.build_contract());c.update(revision='r10_density_reservoir_recovered',schema='riverstone.registered_bounded_terrain.r10.recovered.v1',review_module=__name__)
 c['review_bounds_xz_m']=list(c.get('review_bounds_xz_m',[-530,-530,530,650]));c['review_bounds_xz_m'][3]=max(c['review_bounds_xz_m'][3],656)
 c['excluded_source_ids']=list(EXCLUDED);c['ordinary_foundations']=ordinary_foundation_contracts();c['exact_surface_ownership'].update(module=__name__,excluded_source_ids=list(EXCLUDED))
 c['exclusion_ledger']+=[dict(source_mass_id=id,reason='native B015 east recovered density replacement',removed_owner_kinds=['body','door','support'],replacement_source_sha256=DENSITY_SHA) for id in DENSITY['replaced_placement_ids']]
 for p,h in [(DENSITY_PATH,DENSITY_SHA),(SERVICE_PATH,SERVICE_SHA),(HANDOFF_PATH,HANDOFF_SHA),(SOUTH_PATH,SOUTH_SHA)]:c['references'][str(p.relative_to(CITY))]=h
 c['module_sources'][str((HERE/'author.py').relative_to(CITY))]=R04.sha(HERE/'author.py')
 c['bounded_density_b015']=dict(path=str(DENSITY_PATH.relative_to(CITY)),sha256=DENSITY_SHA,replaced_placement_ids=DENSITY['replaced_placement_ids'],superseded_old_path_ids=DENSITY['superseded_old_path_ids'],native_masks=DENSITY['ownership_masks'],actual_doors=DENSITY['access_proposals'],courts=DENSITY['courts'],court_paths=DENSITY['court_paths'],semantic_grounds=DENSITY['ground_ownership_records'],ground_service_paths=DENSITY['ground_service_paths'],retained_public_surface_regions=DENSITY['retained_public_surface_regions'],policy='Render10 native groups, not28 components twice. Exact59 native foundation sections and65 actual finished thresholds. Semantic yard/roof area accounting never levels whole block or cuts ground.')
 c['reservoir_service_interface']=dict(path=str(SERVICE_PATH.relative_to(CITY)),sha256=SERVICE_SHA,dry_floors=SERVICE['owned_floors'],elevated_wet_decks=SERVICE['elevated_wet_decks'],handoff=HANDOFF,actual_public_flat_domains=PUBLIC_FLAT,transition_bounds_xz_m=BOUNDS,transition_formula='max(inherited H,18−0.12 distance to finite public landing and gap union)',policy='Traffic semantics retained under exact +18 public landing. Native dry-floor holes preserve finite tank excavation below. Wet deck masks never erase water/bed.',preview_gradient_status='Analytic source bounded; finite exported triangles and capsule pending')
 c['south_country_road']=SOUTH;c['south_tail_restoration']=dict(polygon_xz_m=TAIL_CLIP,scope='Only old MAIN_BRIDGE ground/shoulder/hole domains beyond actual native terminal localX72; actual stone and water remain intact.',ledger_path=str((HERE/'south_tail_restoration.json').relative_to(CITY)))
 c['reconstruction_note']='r09/r10 post-backup bytes were lost; fresh geometry/data/source identities are explicit. Frozen r3 and all original guards remain untouched.'
 return c
if __name__=='__main__':(HERE/'contract.json').write_text(json.dumps(build_contract(),indent=2)+'\n');print(R04.sha(HERE/'contract.json'))
