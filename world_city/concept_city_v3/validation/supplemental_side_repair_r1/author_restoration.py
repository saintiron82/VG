"""Bounded road-owned corner proposal from exact existing seam vertices."""
import sys,pathlib,json,math,hashlib
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import author as s, approaches as a,landings as l
f=json.loads((H/'targeted_original_endpoint_failures.json').read_text())['failures'][0]
P=f['edge_xyz_m'][0];B=l.TRIANGLES[10106]['triangle_xyz_m'][2];C=l.TRIANGLES[10105]['triangle_xyz_m'][2];triangle=[P,B,C];poly=[[v[0],v[2]] for v in triangle];origin=poly[0]
def area(poly):
 p=[[q[k]-poly[0][k] for k in (0,1)] for q in poly];return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))/2
road=f['endpoint_details'][0]['offset_owner'];assert road['kind']=='road' and road['road_id']=='MARKET_CONTOUR';assert all(a.geo.point_in_convex_polygon(p,road['polygon_xz_m'],1e-10) for p in poly)
# These existing native preview edges share X exactly; positive-area overlap is
# impossible for a landing triangle whose maximum X is at or left of that line.
assert B[0]==C[0]==-244.25 and P[0]>B[0]
near=[];overlaps=[]
for i in l.INDEX.candidates(poly):
 r=l.TRIANGLES[i];xs=[p[0] for p in r['polygon_xz_m']];zs=[p[1] for p in r['polygon_xz_m']]
 if max(xs)<min(p[0] for p in poly) or min(xs)>max(p[0] for p in poly) or max(zs)<min(p[1] for p in poly) or min(zs)>max(p[1] for p in poly):continue
 near.append(i)
 if max(xs)>-244.25:
  inter=a.geo.convex_intersection([[p[k]-origin[k] for k in (0,1)] for p in poly],[[p[k]-origin[k] for k in (0,1)] for p in r['polygon_xz_m']]);ar=area(inter) if len(inter)>2 else 0
  if ar>1e-14:overlaps.append(dict(triangle=i,area_m2=ar))
assert not overlaps
samples=[]
for i in range(101):
 t=i/100;q=[B[k]+t*(C[k]-B[k]) for k in range(3)];samples.append(dict(point_xyz_m=q,road_y_m=s.source_surface_height_at(road,q[0],q[2]),landing_y_m=l.height_at(q[0],q[2])))
maxroad=max(abs(r['road_y_m']-r['point_xyz_m'][1]) for r in samples);maxlanding=max(abs(r['landing_y_m']-r['point_xyz_m'][1]) for r in samples)
# Compare the patch plane with the source road across the full finite triangle.
profile=[]
for i in range(21):
 for j in range(21-i):
  u=i/20;v=j/20;q=[P[k]+u*(B[k]-P[k])+v*(C[k]-P[k]) for k in range(3)];profile.append(abs(q[1]-s.source_surface_height_at(road,q[0],q[2])))
x1,z1=B[0]-P[0],B[2]-P[2];x2,z2=C[0]-P[0],C[2]-P[2];den=x1*z2-z1*x2;gx=((B[1]-P[1])*z2-(C[1]-P[1])*z1)/den;gz=(x1*(C[1]-P[1])-x2*(B[1]-P[1]))/den
mask=f['outside_owner']['polygon_xz_m'];outside_distances=[]
for q in poly:
 if not a.geo.point_in_convex_polygon(q,mask,0):outside_distances.append(min(a.review.prior.base._project(*q,u,v)[0] for u,v in zip(mask,mask[1:]+mask[:1])))
record=dict(owner_id='RECOVERED_PUBLIC_RESIDUAL:MONASTERY_MARKET_CORNER:0',kind='restored_public_road_corner',road_id='MARKET_CONTOUR',render_land=True,material='road',priority=8.9,polygon_xz_m=poly,triangle_xyz_m=triangle,underlying_record=road,replaces_owner_id=f['outside_owner']['owner_id'])
report=dict(schema='riverstone.finite_public_corner_restoration.v1',status='finite_source_proposal_for_terrain_binding',source_profile_sha256=a.SHA,source_approach_id=f['source']['owner_id'],source_landing_triangle_indices=[10105,10106],source_landing_vertices=[B,C],original_failed_edge_xyz_m=f['edge_xyz_m'],restorations=[record],area_m2=area(poly),existing_landing_positive_area_overlap_m2=0,nearby_landing_triangles=near,public_road_containment=True,maximum_mask_edge_roundoff_distance_m=max(outside_distances,default=0),shared_landing_edge_samples=samples,shared_landing_edge_max_height_error_m=maxlanding,road_shared_edge_max_height_error_m=maxroad,full_patch_source_road_sample_count=len(profile),full_patch_source_road_max_height_error_m=max(profile),patch_planar_grade=math.hypot(gx,gz),approach_endpoint_road_height_error_m=abs(P[1]-s.source_surface_height_at(road,P[0],P[2])),limits=['Only this finite road-owned corner is restored; no landing plane extrapolation or landing domain expansion.','Existing recovered source triangles remain byte-for-byte unchanged.','The other historical mask-versus-render residuals remain separately recorded; no whole-scene watertight or traversal claim.'],inputs={str(pathlib.Path(m.__file__).relative_to(ROOT)):hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest() for m in [s,a,l]})
(H/'restoration_candidate_measurement.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:report[k] for k in ['area_m2','maximum_mask_edge_roundoff_distance_m','shared_landing_edge_max_height_error_m','road_shared_edge_max_height_error_m','full_patch_source_road_max_height_error_m','patch_planar_grade']},flush=True)
report['measured_road_datum_comparison_tolerance_m']=1e-6
report['source_height_equality_scope']='Exact existing landing edge and exact road-owned approach endpoint; the nonlinear road field differs from the finite plane by the explicitly measured sub-micrometre residual.'
report['author_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
assert maxlanding<1e-9 and maxroad<1e-6 and max(profile)<1e-6 and report['patch_planar_grade']<=.12+1e-8
p=H/'finite_road_corner_restoration.json';p.write_text(json.dumps(report,indent=2)+'\n');print('SEALED',hashlib.sha256(p.read_bytes()).hexdigest());print({k:report[k] for k in ['area_m2','maximum_mask_edge_roundoff_distance_m','shared_landing_edge_max_height_error_m','road_shared_edge_max_height_error_m','full_patch_source_road_max_height_error_m','patch_planar_grade']})
