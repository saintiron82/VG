import json,pathlib,hashlib,math
from world_city.concept_city_v3.registered_integration.r6.merge_patches import canonical_sha
C=pathlib.Path('world_city/concept_city_v3');R=C/'registered_topography/revisions/public_corridors_r18';D=R/'local_contact_reviews_r01'
P=C/'registered_topography/revisions/r17_district_batches/coherent_final24_r01/profiles/BLOCK_002_R8_C004.json';J=R/'shared_noble_cap_r03/producer_16.json';S=C/'evidence/r8_district_61_noble_r02_contracts_runtime/authored_scene.json'
def load(p):return json.loads(p.read_text())
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def h(r,p):a,b,c=r['plane_y_xz_m'];return a*p[0]+b*p[1]+c
p=[78.8615237477,-133.5440851629]
profile=load(P);rs=[next(r for r in profile['public_fixed_regions'] if r['id'].endswith(k)) for k in ['CURRENT_R04:28','CURRENT_R18:2']]
bank=load(J)['appended_surfaces']['bank'];tris=[bank[i*3:i*3+3] for i in [17795,17796]]
a=[tris[0][0][0],tris[0][0][2]];b=[tris[0][1][0],tris[0][1][2]];v=[b[0]-a[0],b[1]-a[1]];L=math.hypot(*v);t=((p[0]-a[0])*v[0]+(p[1]-a[1])*v[1])/L**2;dist=abs(v[0]*(p[1]-a[1])-v[1]*(p[0]-a[0]))/L
assert 0<=t<=1 and dist<1e-9
for x,r in [(tris[0][0],rs[1]),(tris[0][1],rs[1]),(tris[0][2],rs[0]),(tris[1][2],rs[0])]:assert abs(x[1]-h(r,[x[0],x[2]]))<1e-11
scene=load(S);road=scene['surfaces']['road'];hits=[]
for i in range(0,len(road),3):
 q=road[i:i+3]
 if not(min(x[0] for x in q)-1e-8<=p[0]<=max(x[0] for x in q)+1e-8 and min(x[2] for x in q)-1e-8<=p[1]<=max(x[2] for x in q)+1e-8):continue
 cr=[]
 for k in range(3):
  u=q[k];w=q[(k+1)%3];d=math.hypot(w[0]-u[0],w[2]-u[2]);cr.append(((w[0]-u[0])*(p[1]-u[2])-(w[2]-u[2])*(p[0]-u[0]))/d if d else 0)
 if min(cr)<-1e-8 and max(cr)>1e-8:continue
 match=[]
 for r in rs:
  residual=max(abs(x[1]-h(r,[x[0],x[2]])) for x in q)
  if residual<1e-10:match.append(dict(profile_region_id=r['id'],maximum_vertex_plane_residual_m=residual))
 if match:hits.append(dict(material='road',triangle_index=i//3,triangle_sha256=canonical_sha(q),triangle_xyz_m=q,matches=match))
assert all(any(any(z['profile_region_id']==r['id'] for z in x['matches']) for x in hits) for r in rs)
report=dict(status='PASS_EXACT_EXISTING_RISER_CLOSURE_RUNTIME_PENDING',profile=ref(P),joint_producer=ref(J),actual_authored_scene=ref(S),point_xz_m=p,point_heights_m=[h(r,p) for r in rs],step_m=h(rs[1],p)-h(rs[0],p),fixed_public_regions=rs,edge_xz_m=[a,b],length_m=L,point_distance_to_edge_m=dist,side_triangles=[dict(material='bank',triangle_index=i,triangle_sha256=canonical_sha(q),triangle_xyz_m=q) for i,q in zip([17795,17796],tris)],actual_current_top_triangles=hits,limits=['This is a finite source/actual-top and side-closure check, not an unchanged-controller pass for this new final-batch route.','The reported 1.328 mm discontinuity is preserved explicitly, with no averaged height or regrade.'])
O=D/'b002_c004_existing_riser.json';O.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(report=ref(O),step_m=report['step_m'],edge_length_m=L,actual_top_triangle_count=len(hits)),indent=2))
