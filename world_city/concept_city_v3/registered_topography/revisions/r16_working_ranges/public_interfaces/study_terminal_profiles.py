"""Bounded source/math study only. No scene export, new mesher, or activation.

Uses the registered R15 shared convex clipping. Full-width frozen terminal seams
are tested first; an infeasible necessary boundary condition stops a grade solve.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import collections, hashlib, json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
READ_INPUTS = {Path(__file__).resolve()}
def record_read(event, args):
 if event != 'open' or not isinstance(args[0], (str, bytes)): return
 path = Path(args[0]).resolve(); mode = args[1]
 if isinstance(mode, str) and 'r' in mode and path.is_relative_to(ROOT) and path.suffix in ('.py', '.json', '.npz'):
  READ_INPUTS.add(path)
sys.addaudithook(record_read)
# Read source instead of potentially stale compiled Python caches; write none.
sys.pycache_prefix = str(HERE / '_unused_pycache')
sys.path.insert(0, str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import author as a
CITY = ROOT / 'world_city/concept_city_v3'
PACK = CITY / 'assemblies/ordinary/registered/working_ranges_r01'
LIMIT = .12
EPS = 1e-8
EXPECTED = {
 'resolved_placements.json': '57577354dd51455f49b836e5e65e628ec9d0988888647d3f5f42e034dd9aba07',
 'terrain_handoff.json': 'ddf332fd05d588a75b8a0d55aa286725a1564b9b302c9b0e00559f5c39cdd848',
 'access_handoff.json': '48edcd3b38508ac61fbe930a6f5e38d736ac585f352ce6aea0ad1b2867ad3077',
 'native_geometry.json': '90290ba6e3199086ca97918ee866175d99337fd2a1242ee45cf87f1e0d9b8c71',
 'evidence/frozen_r5_local_triangles.json': '2aee3bf5be23985bb969019d7e0b9d096e6c90f1cadf887e48f2328eb9ff1dec',
}
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ref(path): return dict(path=str(Path(path).relative_to(ROOT)), sha256=sha(path))
def read(path): return json.loads(Path(path).read_text())
def write(name, obj): (HERE/name).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')
for name, expected in EXPECTED.items():
 assert sha(PACK/name) == expected, 'Changed sealed input: '+name
H = read(PACK/'terrain_handoff.json'); A = read(PACK/'access_handoff.json'); N = read(PACK/'native_geometry.json')
S = read(PACK/'evidence/frozen_r5_local_triangles.json')
EXPLICIT_PROTECTED = [dict(owner_id=r['id'],kind='merchant_19_'+r.get('kind','native_hole'),polygon_xz_m=r['polygon_xz_m']) for r in a.PLATFORMS+a.GATES+a.NATIVE_HOLES]
for r in read(CITY/'registered_topography/revisions/r15_merchant_local_patch/public_interfaces/accepted_masks.json')['masks']:
 EXPLICIT_PROTECTED.append(dict(owner_id=r['id'],kind='r15_accepted_public_interface',polygon_xz_m=r['polygon_xz_m']))
TRIS = []
INDEX = a.geo._SpatialIndex(8)
for i, r in enumerate(S['records']):
 p = [[v[0],v[2]] for v in r['vertices_m']]
 q = dict(r, local_snapshot_triangle_index=i, polygon_xz_m=p, plane_y_xz_m=list(a.affine_plane(r['vertices_m'])))
 TRIS.append(q); INDEX.add(i,p)
def height(row, p): return a.plane_height(row['plane_y_xz_m'], *p)
def source_ref(row): return {k:row[k] for k in ('local_snapshot_triangle_index','material','source_triangle_index','vertices_m','plane_y_xz_m')}
def disjoint(polys):
 result=[]
 for p in polys: result.extend(a.subtract([p],result))
 return result

def cross(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
def interval_in_triangle(p,q,tri):
 """Exact line/convex-triangle half-plane interval, with no geometry creation."""
 sign=1 if cross(*tri)>0 else -1; lo,hi=0.,1.
 for u,v in zip(tri,tri[1:]+tri[:1]):
  b=sign*cross(u,v,p); m=sign*(cross(u,v,q)-cross(u,v,p))
  if abs(m)<1e-13:
   if b < -1e-9: return None
  elif m>0: lo=max(lo,-b/m)
  else: hi=min(hi,-b/m)
 if hi-lo<1e-10: return None
 return max(0.,lo),min(1.,hi)
def point(p,q,t): return [p[k]+t*(q[k]-p[k]) for k in (0,1)]
def profile(p,q):
 length=math.dist(p,q); pieces=[]
 for i in sorted(INDEX.candidates([p,q])):
  r=TRIS[i];interval=interval_in_triangle(p,q,r['polygon_xz_m'])
  if not interval:continue
  lo,hi=interval;x,z=point(p,q,lo),point(p,q,hi);ys=[height(r,x),height(r,z)]
  pieces.append(dict(t_interval=[lo,hi],distance_interval_m=[lo*length,hi*length],vertices_xyz_m=[[x[0],ys[0],x[1]],[z[0],ys[1],z[1]]],length_m=(hi-lo)*length,height_change_m=ys[1]-ys[0],boundary_tangent_grade=abs(ys[1]-ys[0])/((hi-lo)*length),source_actual_triangle_gradient=math.hypot(*r['plane_y_xz_m'][:2]),source=source_ref(r)))
 pieces.sort(key=lambda r:(r['t_interval'][0],r['t_interval'][1]))
 knots=[]
 for v in sorted(t for r in pieces for t in r['t_interval']):
  if not knots or v-knots[-1]>1e-8:knots.append(v)
 discontinuities=[];gaps=[];overlaps=[]
 for t in knots:
  votes=[dict(y_m=height(r['source'], point(p,q,t)),material=r['source']['material'],source_triangle_index=r['source']['source_triangle_index']) for r in pieces if r['t_interval'][0]-1e-8<=t<=r['t_interval'][1]+1e-8]
  if votes and max(v['y_m']for v in votes)-min(v['y_m']for v in votes)>1e-6:
   discontinuities.append(dict(t=t,point_xz_m=point(p,q,t),height_votes=votes,spread_m=max(v['y_m']for v in votes)-min(v['y_m']for v in votes)))
 for lo,hi in zip(knots,knots[1:]):
  hits=[r for r in pieces if r['t_interval'][0]<(lo+hi)/2<r['t_interval'][1]]
  if not hits:gaps.append([lo,hi])
  if len(hits)>1:overlaps.append(dict(t_interval=[lo,hi],sources=[r['source'] for r in hits]))
 return dict(edge_xz_m=[p,q],full_width_m=length,pieces=pieces,incompatible_height_knots=discontinuities,uncovered_t_intervals=gaps,overlap_intervals=overlaps,minimum_required_triangle_grade=max((r['boundary_tangent_grade'] for r in pieces),default=0.),grade_violations=[r for r in pieces if r['boundary_tangent_grade']>LIMIT+1e-7],policy='Every source side kept separately; no incompatible fixed-height averaging.')
def end_edge(line,width,first=False):
 p,q=(line[0],line[1])if first else(line[-2],line[-1]);dx,dz=q[0]-p[0],q[1]-p[1];d=math.hypot(dx,dz);center=p if first else q;off=[-dz*width/(2*d),dx*width/(2*d)]
 return [[center[k]+s*off[k]for k in (0,1)]for s in(-1,1)]
def bounds(polys):
 return [min(p[0]for q in polys for p in q),min(p[1]for q in polys for p in q),max(p[0]for q in polys for p in q),max(p[1]for q in polys for p in q)]
def perimeter(polys):
 """Split shared convex-clipping edges at every seam knot, then cancel twins."""
 verts=[];buckets=collections.defaultdict(list)
 def weld(p):
  key=tuple(math.floor(v/1e-8)for v in p)
  for dx in(-1,0,1):
   for dz in(-1,0,1):
    for k in buckets[(key[0]+dx,key[1]+dz)]:
     if math.dist(p,verts[k])<1e-8:return k
  k=len(verts);verts.append(p);buckets[key].append(k);return k
 ids=[[weld(p)for p in poly]for poly in polys];edges=collections.Counter()
 for row in ids:
  for i,j in zip(row,row[1:]+row[:1]):
   p,q=verts[i],verts[j];den=math.dist(p,q)**2;knots=[(0.,i),(1.,j)]
   for k,v in enumerate(verts):
    if k in(i,j):continue
    t=sum((v[z]-p[z])*(q[z]-p[z])for z in(0,1))/den
    if 1e-9<t<1-1e-9 and math.dist(v,point(p,q,t))<1e-8:knots.append((t,k))
   knots.sort()
   for (_,v),(_,w) in zip(knots,knots[1:]):edges[tuple(sorted((v,w)))]+=1
 assert not [e for e,n in edges.items()if n>2], 'Nonmanifold candidate mask'
 return [[verts[i],verts[j]]for (i,j),n in edges.items()if n==1]
def on_edge(p,e):
 q,r=e;den=math.dist(q,r)**2;t=sum((p[k]-q[k])*(r[k]-q[k])for k in(0,1))/den
 return -1e-8<=t<=1+1e-8 and math.dist(p,point(q,r,t))<1e-7
def protected_overlaps(polys):
 result=[]
 domains=a.base.surface_domains(bounds(polys),False)
 domains=[d for d in domains if d['kind']not in('ground','terrace','road','road_shoulder')]+EXPLICIT_PROTECTED
 for d in domains:
  for poly in polys:
   if(q:=a.polygon(a.geo.convex_intersection(poly,d['polygon_xz_m']))):
    result.append(dict(owner_id=d['owner_id'],kind=d['kind'],overlap_polygon_xz_m=q,overlap_area_m2=a.geo.polygon_area(q)))
 return result

def run():
 inputs=[ref(PACK/n) for n in EXPECTED]
 for r in H['protection_refs']:
  assert sha(ROOT/r['path'])==r['sha256'];inputs.append(r)
 source_modules=[Path(a.__file__),Path(a.base.__file__),Path(a.geo.__file__),HERE/'study_terminal_profiles.py',CITY/'registered_topography/revisions/r15_merchant_local_patch/public_interfaces/solve_interfaces.py']
 inputs += [ref(p)for p in source_modules]
 results=[];candidate_unions=[]
 for num,h in enumerate(H['terminal_grade_holds']):
  route=next(r for r in A['external_routes']if r['id']==h['route_id']);width=route['width_m'];line=h['polyline_xz_m'];polys=disjoint(h['bounded_review_polygons_xz_m']);area=sum(a.geo.polygon_area(p)for p in polys)
  candidate_unions.append(polys)
  assert abs(sum(math.dist(p,q)for p,q in zip(line,line[1:]))-12)<1e-9
  protected=protected_overlaps(polys)
  native_overlap=[]
  for n in H['native_foundation_owners']:
   for owner_poly in n['polygons_xz_m']:
    for poly in polys:
     q=a.polygon(a.geo.convex_intersection(poly,owner_poly))
     if q:native_overlap.append(dict(owner_id=n['id'],overlap_polygon_xz_m=q))
  start=end_edge(line,width,True);end=end_edge(line,width)
  start_profile=profile(*start);end_profile=profile(*end)
  boundaries=[]
  for ei,e in enumerate(perimeter(polys)):
   pp=profile(*e)
   for pi,piece in enumerate(pp['pieces']):
    v=piece['vertices_xyz_m'];xz=[[v0[0],v0[2]]for v0 in v];mid=[sum(p0[k]for p0 in xz)/2 for k in(0,1)]
    kind='full_width_inner_fixed_2_5'if on_edge(mid,start)else('full_width_terminal_frozen_walk_seam'if on_edge(mid,end)else('frozen_public_road_walk_seam'if piece['source']['material']in('road','alley','ground_stone')else'possible_finite_nonwalking_backland_retaining_edge'))
    # A retaining proposal must face backland outside every reserved ribbon.
    if kind.startswith('possible'):
     dx,dz=xz[1][0]-xz[0][0],xz[1][1]-xz[0][1];length=math.hypot(dx,dz)
     probes=[[mid[0]+sign*dz/length*1e-4,mid[1]-sign*dx/length*1e-4]for sign in(-1,1)]
     exterior=[p for p in probes if not any(a.geo.point_in_convex_polygon(p,poly,1e-10)for poly in polys)]
     for other in A['external_routes']+A['internal_routes']:
      if any(a.geo.point_in_convex_polygon(p,poly,1e-10)for p in exterior for poly in other['ribbon_and_join_polygons_xz_m']):
       kind='other_reserved_lane_frozen_walk_seam';break
    boundaries.append(dict(id=f'WR16_TERMINAL_{num:02d}:BOUNDARY:{ei}:{pi}',kind=kind,**piece))
  sources=[];covered=0.;initial_bad=[]
  for i in sorted(set().union(*(INDEX.candidates(p) for p in polys))):
   r=TRIS[i]
   clips=[]
   for p in polys:
    q=a.polygon(a.geo.convex_intersection(p,r['polygon_xz_m']))
    if q:clips.append(q)
   if not clips:continue
   ar=sum(a.geo.polygon_area(q)for q in clips);covered+=ar;g=math.hypot(*r['plane_y_xz_m'][:2]);row=dict(**source_ref(r),clipped_polygons_xz_m=clips,area_m2=ar,actual_gradient=g);sources.append(row)
   if g>LIMIT+1e-7:initial_bad.append(row)
  fixed_bad=[r for r in boundaries if r['kind']in('full_width_terminal_frozen_walk_seam','frozen_public_road_walk_seam','other_reserved_lane_frozen_walk_seam') and r['boundary_tangent_grade']>LIMIT+1e-7]
  failed=bool(end_profile['grade_violations']or end_profile['incompatible_height_knots']or fixed_bad or protected or native_overlap)
  result=dict(schema='riverstone.r16_working_terminal_source_study.v1',id=h['id'],route_id=route['id'],index=num,status='SOURCE_CANDIDATE_PENDING_R6_REBIND',accepted=False,scene_activated=False,actual_r6_scene_binding=None,provisional_source_scene=S['scene'],input_bindings=inputs,original_hold_sha256=hashlib.sha256(json.dumps(h,sort_keys=True,separators=(',',':')).encode()).hexdigest(),review_length_m=12.,actual_preserved_lane_width_m=width,centerline_xz_m=line,candidate_masks=[dict(id=f'WR16_TERMINAL_{num:02d}:MASK:{i}',polygon_xz_m=p)for i,p in enumerate(polys)],candidate_union_area_m2=area,candidate_bounds_xz_m=bounds(polys),source_coverage_area_m2=covered,source_coverage_error_m2=covered-area,sealed_raw_polygon_area_m2=h['existing_actual_terrain']['projected_area_m2'],overlapping_raw_polygons_counted_once=True,inner_full_width_profile=start_profile,terminal_full_width_profile=end_profile,boundary_profiles=boundaries,protected_owner_overlaps=protected,native_owner_overlaps=native_overlap,source_triangles=sources,source_triangle_grade_failures=initial_bad,fixed_walking_boundary_grade_failures=fixed_bad,feasibility=dict(original_corridor='INFEASIBLE_FIXED_WALKING_BOUNDARY'if failed else'NECESSARY_BOUNDARY_TESTS_PASS_NOT_SOLVED',grade_limit=LIMIT,solver_run=False,reason='A continuous piecewise-affine walking surface with gradient norm <=0.12 must have every fixed boundary tangent <=0.12 and single-valued shared knots. Preserve failures; do not average and do not solve around an impossible fixed seam.',inherited_endpoint_jump_count=len(end_profile['incompatible_height_knots']),minimum_required_terminal_triangle_grade=end_profile['minimum_required_triangle_grade'],retaining_policy='Only finite lateral backland edges outside every walking ribbon are eligible for subsequent retaining-face design. Full-width terminal, inner lane and road walking seams are never retaining.'),unchanged=dict(native_threshold_y_m=2.5,internal_lanes=True,native_buildings=True,public_road_outside_candidate=True,old_plot_boundaries=True,canal_service_buffers=True),limits=['R5 exact-triangle source study only, pending R6 rebind.','No altered source scene, activation, export, mesh compiler or capsule claim.','No implicit steps or cliff ramps.','A failed fixed seam requires an explicitly named finite revision and new ownership review.'])
  write(f'terminal_{num:02d}_original_corridor.json',result)
  results.append(dict(index=num,route_id=route['id'],status=result['status'],original_corridor=result['feasibility']['original_corridor'],width_m=width,mask_count=len(polys),union_area_m2=area,source_coverage_error_m2=covered-area,terminal_minimum_triangle_grade=end_profile['minimum_required_triangle_grade'],terminal_incompatible_knots=len(end_profile['incompatible_height_knots']),fixed_walking_boundary_grade_failures=len(fixed_bad),protected_owner_overlaps=len(protected),native_owner_overlaps=len(native_overlap)))
  print(json.dumps(results[-1]),flush=True)
 overlap=[]
 for p in candidate_unions[0]:
  for q in candidate_unions[1]:
   if (piece:=a.polygon(a.geo.convex_intersection(p,q))):overlap.append(piece)
 write('terminal_overlap_audit.json',dict(schema='riverstone.r16_terminal_overlap.v1',status='SOURCE_CANDIDATE_PENDING_R6_REBIND',overlap_area_m2=sum(a.geo.polygon_area(p)for p in overlap),overlap_polygons_xz_m=overlap,policy='Any subsequent overlapping collars must use one common field and single ownership in their overlap. Never append both independently.'))
 collar_box=[[214.,132.],[228.,132.],[228.,145.],[214.,145.]]
 collar_parts=disjoint(candidate_unions[0]+candidate_unions[1]+[collar_box])
 protected=protected_overlaps(collar_parts)
 proposal=dict(schema='riverstone.r16_shared_collar_proposal.v1',id='WR16_LOWER_CONTOUR_SHARED_PUBLIC_COLLAR_STUDY_01',status='PROPOSAL_ONLY_PENDING_R6_REBIND_AND_PUBLIC_OWNER_REVIEW',accepted=False,scene_activated=False,source_scene=S['scene'],actual_r6_scene_binding=None,reason='Both original full-width fixed terminal profiles exceed12%; this single finite public-collar revision would move the frozen seam outward rather than hide a step or narrow either lane.',added_public_collar_box_xz_m=collar_box,explicit_candidate_masks=[dict(id=f'WR16_SHARED_COLLAR:MASK:{i}',polygon_xz_m=p)for i,p in enumerate(collar_parts)],candidate_union_area_m2=sum(a.geo.polygon_area(p)for p in collar_parts),candidate_bounds_xz_m=bounds(collar_parts),preserved_lane_widths_m=[2.,3.5],protected_source_owner_overlaps=protected,shared_field_required=True,proposed_changed_surface_scope='Only the exact finite candidate union. Public-road ownership change is a proposal, not permission or activation. No road centerline, width, plots, buildings, thresholds, internal lanes, canal or service buffer changes.',unchanged_inner_cross_sections=[dict(route_id=h['route_id'],edge_xz_m=end_edge(h['polyline_xz_m'],h['review_width_m'],True),fixed_y_m=2.5)for h in H['terminal_grade_holds']],tests_required_before_any_solve=['Rebind exact candidate source triangles and boundary knots to delivered R6 scene SHA.','Audit frozen outer perimeter source pieces and heights without averaging conflicting walking seams.','Respect every protected owner and route; identify which public owner permits the finite collar change.','Solve one common continuous piecewise-affine field over the entire union, with actual triangle gradient norm <=0.12, exact full-width inner +2.5 sections and fixed outer walking seams.','If any fixed outer walking seam is incompatible or >12%, reject this collar unchanged; request a separately bounded route-end revision.','Derive finite nonwalking retaining faces only on lateral backland boundaries outside all walking ribbons, with explicit top and bottom profiles.','Run independent exact source coverage, no overlap/double ownership, grade, seam, native threshold and actual scene/capsule audits.'],grade_solve_run=False,feasibility='NOT_ESTABLISHED',new_mesh_or_export=False)
 write('shared_public_collar_proposal.json',proposal)
 # This transitive manifest binds every repository source/data file actually
 # read, including the protected-owner hierarchy loaded by shared geometry.
 all_inputs=[ref(path)for path in sorted(READ_INPUTS)if path.exists() and (not path.is_relative_to(HERE) or path.name=='study_terminal_profiles.py')]
 write('source_read_manifest.json',dict(schema='riverstone.r16_source_read_manifest.v1',source_scene=S['scene'],actual_r6_scene_binding=None,inputs=all_inputs,input_count=len(all_inputs),read_only_source=True))
 write('original_corridor_summary.json',dict(status='SOURCE_CANDIDATE_PENDING_R6_REBIND',source_scene=S['scene'],actual_r6_scene_binding=None,input_bindings=inputs,transitive_input_manifest=ref(HERE/'source_read_manifest.json'),interfaces=results,accepted=False))
if __name__=='__main__':run()
