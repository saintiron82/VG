"""R14 finite precinct and merchant owners. Candidate until interface audit seals."""
import copy,json,math,hashlib
from pathlib import Path
from functools import lru_cache
from ..r13_precinct_interfaces import materials as prior
from ..r12_boundary_diagnostics import materials as paint
from . import collar,recovered_corner
HERE=Path(__file__).resolve().parent;CITY=prior.CITY;ROOT=CITY.parents[1];R04=prior.R04;geo=prior.geo;clean=prior.polygon
REFERENCES={
 'assemblies/landmarks/registered/precinct_r04/contact_repair_r01/resolved_placements.json':'f6cad68490d353d4089d461b6ae82e089d1e7be892ac0f77ceb2393b0249a3a5',
 'assemblies/landmarks/registered/precinct_r04/access_r02/exterior_access_proposal.json':'44e8fcbc15629e5dfa940bddf7c69a9818dc11bb85bab59f8d3ca269753a692f',
 'assemblies/landmarks/registered/precinct_r04/access_r02/abbey_shoulder_request.json':'b584c521b2d71899dc2a26aa370bb2ed0f25f6603af120679dd0ffb975cf20a4',
 'assemblies/property/registered/merchant_block011/resolved_placements.json':'571b88141be76a953fd479299697b657abba19c1894945b28e787f026e8d5e91',
 'assemblies/property/registered/merchant_block011/terrain_handoff.json':'4cbdffaedfcbdb1dc2389792adbd463b0c3971d608eaf983818dfe5be926c940',
 'registered_topography/revisions/r14_precinct_merchant/support/resolved_support.json':'128c313a273c906ea2ad8bb10e859651a2fcfe21446760f7732e86e22d67d6c9'}
for p,h in REFERENCES.items():
 if R04.sha(CITY/p)!=h:raise ValueError('Changed r14 source '+p)
PRE,ACCESS,SHOULDER,MERCHANT,HANDOFF,SUPPORT=[json.loads((CITY/p).read_bytes()) for p in REFERENCES]
SUPPORT_REFERENCES={
 'registered_topography/revisions/r14_precinct_merchant/support/resolved_merchant_support.json':'f9ddee450e5853097194ca30da209239cf44a96b3084cccb15d623f34e08e2a6',
 'assemblies/landmarks/registered/precinct_r04/abbey_guard_r01/resolved_placements.json':'b9194d2bd9f1a01143aaa99afce20c7ab8a4dbb6145c8660b7dcc00c79fc85fe'}
for p,h in SUPPORT_REFERENCES.items():
 if R04.sha(CITY/p)!=h:raise ValueError('Changed r14 support '+p)
MERCHANT_SUPPORT,GUARD=[json.loads((CITY/p).read_bytes()) for p in SUPPORT_REFERENCES]
EXCLUDED=tuple(sorted(set(prior.prior.EXCLUDED)|set(MERCHANT['replaced_placement_ids'])))
OWNERS=[];INDEX=geo._SpatialIndex(16);MATERIALS=[];MAT_INDEX=geo._SpatialIndex(16)
def add(p,**kw):
 p=clean(p)
 if p:OWNERS.append(dict(polygon_xz_m=p,**kw))
# Lowest native contact footprints include walls, not merely visible walking tops.
for r in PRE['actual_bearing_footprints']:
 add(r['polygon_xz_m'],owner_id=r['id'],kind='r14_precinct_native_hole',priority=19,render_land=False,floor_y_m=r['finished_floor_y_m'],native_bottom_y_m=r['bottom_y_m'],source_placement_id=r['placement_id'])
# All1684 upward floor masks are covered exactly by the2177 bottom-bearing
# footprints (zero uncovered area). Avoid duplicate logical owners.
for r in MERCHANT['ownership_masks']:
 for i,p in enumerate(r['terrain_exclusion_regions_xz_m']):add(p,owner_id=r['owner_id']+':foundation:'+str(i),kind='r14_merchant_native_hole',priority=19,render_land=False,floor_y_m=r['floor_y_m'],native_bottom_y_m=r['floor_y_m']-r['foundation_embed_m'],property_id=r['property_id'])
for r in ACCESS['routes']:
 for i,p in enumerate(r['ribbon_polygons_xz_m']+r['join_polygons_xz_m']):add(p,owner_id=r['id']+':'+str(i),route_id=r['id'],kind='r14_precinct_path',priority=35,render_land=True,floor_y_m=r['gate_y_m'],material='stone')
for r in HANDOFF['properties']:
 add(r['platform_polygon_xz_m'],owner_id=r['property_id']+':PLATFORM',property_id=r['property_id'],kind='r14_merchant_platform',priority=40,render_land=True,floor_y_m=r['finished_floor_y_m'])
 gate=r['finite_gate_approach'];add(gate['polygon_xz_m'],owner_id=gate['id'],property_id=r['property_id'],kind='r14_merchant_gate',priority=9,render_land=True,floor_y_m=r['finished_floor_y_m'],material='stone',road_id=gate['road_id'],replaces_road_ids=[gate['road_id']])
 for m in r['materials']:
  if m['material']=='native_asset_owned':continue
  material={'cobblestone':'stone','compacted_gravel':'ground','packed_earth':'earth'}[m['material']]
  for i,p in enumerate(m['polygons_xz_m']):
   p=clean(p)
   if p:MATERIALS.append(dict(polygon_xz_m=p,material=material,property_id=r['property_id'],semantic_role=m['role']))
OWNERS.sort(key=lambda r:r['priority'])
for i,r in enumerate(OWNERS):INDEX.add(i,r['polygon_xz_m'])
for i,r in enumerate(MATERIALS):MAT_INDEX.add(i,r['polygon_xz_m'])
# One bounded +4 gate collar. The dry field has a floor of1 m here, so a
# 26 m finite buffer makes the12% envelope inactive at every outer edge.
GATE=next(r['finite_gate_approach'] for r in HANDOFF['properties'] if r['property_id']=='M11_SHOP_COURT')
SEED=GATE['polygon_xz_m'];COLLAR_ROAD=GATE['road_id'];COLLAR_FLOOR=4.;COLLAR_GRADE=.12
COLLAR_BOUNDS=[min(p[0] for p in SEED)-26,min(p[1] for p in SEED)-26,max(p[0] for p in SEED)+26,max(p[1] for p in SEED)+26];COLLAR_BOX=R04.old.rect(COLLAR_BOUNDS)
@lru_cache(maxsize=65536)
def gate_distance(x,z):
 if geo.point_in_convex_polygon([x,z],SEED,1e-10):return 0.
 return min(R04.base._project(x,z,a,b)[0] for a,b in zip(SEED,SEED[1:]+SEED[:1]))
def collar_eligible(r):return r['kind'] in ('ground','terrace') or(r['kind'] in ('road','road_shoulder') and r.get('road_id')==COLLAR_ROAD)
def collar_record(r,p=None):
 out=dict(owner_id='R14_GATE_COLLAR:'+r['owner_id'],kind='r14_merchant_transition',underlying_record=r,road_id=r.get('road_id'),render_land=True,polygon_xz_m=p or COLLAR_BOX,review_tile_bounds_xz_m=r.get('review_tile_bounds_xz_m'))
 if r.get('material'):out['material']=r['material']
 return out


def allowed(r,f):
 if not r.get('render_land',True):return False
 if r['kind'] in ('road','replacement_road','port_tie','external_triangular_surface','reservoir_service_public_landing'):
  return r.get('road_id') in f.get('replaces_road_ids',[])
 if r['kind'] in ('door_landing','door_approach','b015_entry','density_entry'):return False
 return r['kind'] in ('ground','terrace','road_shoulder') or f.get('priority',50)<r.get('priority',100)

def expanded_record(r,x,z):
 return R04.prior.owner_at(x,z,EXCLUDED) if R04.prior.is_excluded(r,EXCLUDED) else r
@lru_cache(maxsize=131072)
def owner_at(x,z):
 corner=recovered_corner.point_owner(x,z)
 if corner:return corner
 r=expanded_record(prior.owner_at(x,z),x,z)
 for i in sorted(INDEX.candidates([[x,z]])):
  f=OWNERS[i]
  if allowed(r,f) and geo.point_in_convex_polygon([x,z],f['polygon_xz_m'],1e-8):return f
 if collar_eligible(r) and geo.point_in_convex_polygon([x,z],COLLAR_BOX,1e-8):
  r=collar_record(r)
  return collar.point_record(r,x,z) if r.get('road_id')==COLLAR_ROAD else r
 return r

def insert(records,bounds):
 out=[]
 for r in records:
  p=clean(r['polygon_xz_m'])
  if not p:continue
  parts=[p]
  for i in sorted(INDEX.candidates(p)):
   f=OWNERS[i]
   if not allowed(r,f):continue
   new=[]
   for p in parts:
    q=clean(geo.convex_intersection(p,f['polygon_xz_m']))
    if q:
     out.append(dict(f,polygon_xz_m=q,review_tile_bounds_xz_m=bounds));new.extend(t for c in geo.convex_difference(p,f['polygon_xz_m']) if(t:=clean(c)))
    else:new.append(p)
   parts=new
  out.extend(dict(r,polygon_xz_m=p) for p in parts)
 return out

def platform_materials(record):
 if record['kind']!='r14_merchant_platform':return [record]
 parts=[record['polygon_xz_m']];out=[]
 for i in sorted(MAT_INDEX.candidates(parts[0])):
  m=MATERIALS[i]
  if m['property_id']!=record['property_id']:continue
  new=[]
  for p in parts:
   q=clean(geo.convex_intersection(p,m['polygon_xz_m']))
   if q:
    out.append(dict(record,polygon_xz_m=q,material=m['material'],material_role=m['semantic_role']));new.extend(t for c in geo.convex_difference(p,m['polygon_xz_m']) if(t:=clean(c)))
   else:new.append(p)
  parts=new
 out.extend(dict(record,polygon_xz_m=p,material='earth') for p in parts)
 return out

def surface_domains(bounds,conform=True):
 expanded=[]
 for r in recovered_corner.restore_domains(prior.surface_domains(bounds,conform),bounds,clean):
  if R04.prior.is_excluded(r,EXCLUDED):expanded.extend(R04.prior._replacement_domains(r['polygon_xz_m'],bounds,EXCLUDED))
  else:expanded.append(r)
 out=[]
 for r in insert(expanded,bounds):
  p=clean(geo.convex_intersection(r['polygon_xz_m'],COLLAR_BOX)) if collar_eligible(r) else None
  if p:
   out.extend(dict(collar_record(r,mp['polygon_xz_m']),material=mp['material']) for mp in paint.classify_material_regions(r,p));out.extend(dict(r,polygon_xz_m=t) for cut in geo.convex_difference(r['polygon_xz_m'],COLLAR_BOX) if(t:=clean(cut)))
  else:out.extend(platform_materials(r))
 out=[q for r in out for q in (collar.pieces(r,clean) if r['kind']=='r14_merchant_transition' and r.get('road_id')==COLLAR_ROAD else [r])]
 if not conform:return out
 extra=[];x0,z0,x1,z1=bounds
 if R04.base._overlap(bounds,COLLAR_BOUNDS):
  for i in range(math.ceil(z0*4),math.floor(z1*4)+1):extra.extend([[x0,i/4],[x1,i/4]])
  for i in range(math.ceil(x0*4),math.floor(x1*4)+1):extra.extend([[i/4,z0],[i/4,z1]])
 return R04.old.conform_domains(out,extra)

def source_surface_height_at(r,x,z):
 if r['kind']=='restored_public_road_corner':return recovered_corner.y(r,x,z)
 if r['kind']=='r14_public_profile':return source_surface_height_at(r['underlying_record'],x,z)
 if r['kind']=='r14_merchant_transition':return max(prior.source_surface_height_at(r['underlying_record'],x,z),COLLAR_FLOOR-COLLAR_GRADE*gate_distance(x,z))
 return r['floor_y_m'] if r['kind'].startswith('r14_') else prior.source_surface_height_at(r,x,z)
def surface_height_at(r,x,z):
 if r['kind']=='restored_public_road_corner':return recovered_corner.y(r,x,z)
 if r['kind']=='r14_public_profile':return collar.y(r,x,z)
 if r['kind']=='r14_merchant_transition':return max(prior.surface_height_at(r['underlying_record'],x,z),COLLAR_FLOOR-COLLAR_GRADE*gate_distance(x,z))
 return source_surface_height_at(r,x,z) if r['kind'].startswith('r14_') else prior.surface_height_at(r,x,z)
def height_at(x,z):
 r=owner_at(x,z);h=source_surface_height_at(r,x,z);return h-r['bed_depth_m'] if r['kind']=='water_hole' else h
def land_height_at(x,z):
 r=owner_at(x,z);return prior.land_height_at(x,z) if r['kind']=='water_hole' else source_surface_height_at(r,x,z)
def road_height_at(id,x,z):
 h=prior.road_height_at(id,x,z)
 return max(h,COLLAR_FLOOR-COLLAR_GRADE*gate_distance(x,z)) if id==COLLAR_ROAD and geo.point_in_convex_polygon([x,z],COLLAR_BOX,1e-8) else h
path_height_at=prior.path_height_at
finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at;water_height_at=prior.water_height_at;river_water_y=prior.river_water_y
supplemental_surface_domains=prior.supplemental_surface_domains
def supplemental_side_records(bounds_xz_m):
 from world_city.concept_city_v3.validation.supplemental_side_repair_r1.side_repair import side_records
 return side_records(bounds_xz_m,owner_at,source_surface_height_at)
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
   out.append(dict(id='R14_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],left_owner_id=os[0]['owner_id'],right_owner_id=os[1]['owner_id'],vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],material_hint='stone',collision_semantics='exact finite retaining preview; capsule unverified'))
 return out

def build_contract():
 c=copy.deepcopy(prior.build_contract());c.update(schema='riverstone.precinct_merchant_terrain.r14.v1',revision='r14_precinct_merchant_candidate',review_module=__name__);c['exact_surface_ownership']['module']=__name__;c['exact_surface_ownership']['excluded_source_ids']=list(EXCLUDED);c['excluded_source_ids']=list(EXCLUDED);c['ordinary_foundations']=ordinary_foundation_contracts()
 c['references'].update(REFERENCES);c['references'].update(SUPPORT_REFERENCES);c['module_sources'][str((HERE/'author.py').relative_to(CITY))]=R04.sha(HERE/'author.py')
 for name in ('collar.py','collar_profile.json','recovered_corner.py'):
  path=HERE/name;c['references'][str(path.relative_to(CITY))]=R04.sha(path)
 c['module_sources'][str((HERE/'collar.py').relative_to(CITY))]=R04.sha(HERE/'collar.py')
 c['module_sources'][str((HERE/'recovered_corner.py').relative_to(CITY))]=R04.sha(HERE/'recovered_corner.py')
 c['references'][str(recovered_corner.PATH.relative_to(CITY))]=recovered_corner.SHA256
 side_path=recovered_corner.SIDE_HELPER_PATH;c['module_sources'][str(side_path.relative_to(CITY))]=recovered_corner.SIDE_HELPER_SHA256
 c['recovered_public_corner_restoration']=dict(source_path=str(recovered_corner.PATH.relative_to(CITY)),sha256=recovered_corner.SHA256,restorations=recovered_corner.RECORDS,area_m2=recovered_corner.DATA['area_m2'],grade=recovered_corner.DATA['patch_planar_grade'],side_helper=str(side_path.relative_to(CITY)),policy='Restore only the exact missing road-owned corner; keep all frozen landing triangles and masks. Split the affected supplemental boundary at the existing landing vertex before outside-height evaluation.')
 c['interface_review_evidence']=[dict(path=str((HERE/name).relative_to(CITY)),sha256=R04.sha(HERE/name)) for name in ('ownership_audit_repaired.json','preview_audit_repaired.json','profile_interfaces.json','interface_audit.json','supplemental_preflight.json') if (HERE/name).exists()]
 seam=json.loads((HERE/'profile_interfaces.json').read_bytes())
 c['new_public_preview_joins']=dict(gate_edge_count=26,outer_road_and_shoulder_edge_count=41,maximum_rendered_height_difference_m=2.3092638912203256e-14,scope='Only the new gate and finite public collar outer boundaries. No all-public-seam or character-passage approval.')
 c['public_seam_classification']=dict(complete_record_count=len(seam['public_seam_failures']),records=seam['public_seam_failures'],policy='Retain every finding. Inherited ordinary-door side steps remain unresolved; the one nonlinear evaluator/linear boundary difference has matching rendered endpoint profiles.')
 c['exclusion_ledger']+=[dict(source_mass_id=id,reason='seven finite native merchant compounds',removed_owner_kinds=['body','door','support'],replacement_source_sha256=REFERENCES['assemblies/property/registered/merchant_block011/resolved_placements.json']) for id in MERCHANT['replaced_placement_ids']]
 c['precinct_native_interfaces']=dict(native_pack=REFERENCES['assemblies/landmarks/registered/precinct_r04/contact_repair_r01/resolved_placements.json'],owned_floors=PRE['owned_floors'],actual_bearings=PRE['actual_bearing_footprints'],external_routes=ACCESS['routes'],shoulder_request=SHOULDER,bounded_native_support=SUPPORT,physical_guard_pack=GUARD,policy='Exact native occupied footprints, not broad precinct erasure. Protected lane/native/wet owners remain. The finite +8 pedestrian shoulder has an explicit retaining preview and separate native timber guard.')
 c['merchant_compound_interfaces']=dict(native_pack=REFERENCES['assemblies/property/registered/merchant_block011/resolved_placements.json'],properties=HANDOFF['properties'],actual_doors=MERCHANT['actual_doors'],replaced_placement_ids=MERCHANT['replaced_placement_ids'],superseded_source_path_ids=MERCHANT['superseded_source_path_ids'],bounded_native_support=MERCHANT_SUPPORT,policy='One exact platform owner per compound; native foundation holes first, finite material regions next. Retained lower yards stay on inherited ground. Public gate side continuity under review.')
 c['merchant_gate_collar']=dict(bounds_xz_m=COLLAR_BOUNDS,seed_polygon_xz_m=SEED,road_id=COLLAR_ROAD,top_y_m=COLLAR_FLOOR,grade=COLLAR_GRADE,formula='max(inherited H,4−0.12 distance to exact gate ribbon)',outer_boundary_policy='Finite26m buffer; envelope below dry floor1 at outer boundary. Preview boundary vertices share the fixed linear profile.',excluded_owners='All native, water and ordinary door owners retain their exact masks; unrelated public lanes retain priority.',preview_profile=dict(path=str((HERE/'collar_profile.json').relative_to(CITY)),sha256=collar.SHA256,source_triangle_count=len(collar.TRIANGLES),source_plane_gradient_bound=.12,maximum_vertex_adjustment_m=collar.DATA['iterations'][-1]['max_vertex_adjustment_m'],ownership_policy='Road and support-shoulder polygons clip the shared planes before fan triangulation. Material and native-floor cuts retain those planes.',source_api_policy='height_at/road_height_at retain the continuous analytic source. surface_height_at is the declared spatial-preview evaluator; it is not a capsule collision field.'),retained_neighbour_wall_contact=dict(source_mass_id='B_REG_0279',body_floor_y_m=3.44,maximum_exterior_fill_above_body_floor_m=.11450252525968319,policy='Body and door holes remain unchanged. Finite exterior soil contact is below the cached body wall; no origin lift or new interior floor.'),status='source grades and actual public-preview planes checked; independent/capsule approval pending')
 c['activation_status']='finite source and spatial-preview candidate; native supports and guard present; capsule/cart traversal remains unverified';return c
if __name__=='__main__':(HERE/'contract.json').write_text(json.dumps(build_contract(),indent=2)+'\n');print(R04.sha(HERE/'contract.json'))
