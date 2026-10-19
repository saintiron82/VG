"""Finite six-metre port approach, matching existing quay and fixed bridge envelope."""
import pathlib,json,hashlib,sys,math,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));from world_city.concept_city_v3.registered_topography.revisions.r01_ownership.author import corridor
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as g
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=sha(p));CITY=ROOT/'world_city/concept_city_v3'
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def half(poly,c,sign=1):
 if not poly:return []
 out=[]
 for u,v in zip(poly,poly[1:]+poly[:1]):
  fu=sign*(c[0]*u[0]+c[1]*u[1]+c[2]);fv=sign*(c[0]*v[0]+c[1]*v[1]+c[2])
  if fu>=0:out.append(u)
  if (fu>=0)!=(fv>=0):
   f=fu/(fu-fv);out.append([u[k]+f*(v[k]-u[k])for k in range(2)])
 return a.common.clean(out)
def main():
 sp=H.parent/'fixed_span_walk_r02/profile.json';s=read(sp);B=np.array(s['native_pose']['basis']);T=np.array(s['native_pose']['translation']);local=lambda q:((np.array(q)-T)@B).tolist();world=lambda q:(np.array(q)@B.T+T).tolist();plan=read(CITY/'registered_source/plan.json');road=next(r for r in plan['roads']if r['id']=='PORT_BRIDGE_TIE');ps=road['polyline_xz_m'];p3=[local([x,0,z])for x,z in ps];pts=[[v[0],v[2]]for v in p3];u=np.array(pts[2])-pts[1];u=u/np.linalg.norm(u);C=[float(u[0]),float(u[1]),-float(np.dot(u,pts[1]))]
 domain=[]
 for poly in corridor(pts[1:],road['width_m']):
  p=half(half(poly,C),[0,1,-4])
  if p and g.area(p)>1e-10:domain.append(p)
 domain=g.union(domain);span=s['spans'][0];xs=span['xs_m'];yy=[v[-1]for v in span['heights_y_m']];segments=[]
 for x0,x1,y0,y1 in zip(xs,xs[1:],yy,yy[1:]):
  m=(y1-y0)/(x1-x0);plane=[m,0,y0-m*x0]
  if segments and max(abs(a-b)for a,b in zip(plane,segments[-1]['plane']))<1e-9:segments[-1]['hi']=x1
  else:segments.append(dict(lo=x0,hi=x1,plane=plane))
 segments=[dict(lo=-200,hi=-64,plane=[0,0,1.75])]+segments
 base=[[0,0,2.2],[.05/3*C[0],.05/3*C[1],2.2+.05/3*C[2]],[0,0,2.25]];owners=[]
 for poly in domain:
  for si,seg in enumerate(segments):
   q=half(half(poly,[1,0,-seg['lo']]),[-1,0,seg['hi']])
   if not q or g.area(q)<1e-10:continue
   for bi,pl in enumerate(base):
    p=q
    if bi==0:p=half(p,C,-1)
    elif bi==1:p=half(half(p,C),[C[0],C[1],C[2]-3],-1)
    else:p=half(p,[C[0],C[1],C[2]-3])
    if not p or g.area(p)<1e-10:continue
    diff=[seg['plane'][k]-pl[k]for k in range(3)]
    for side,plane in [(1,seg['plane']),(-1,pl)]:
     z=half(p,diff,side)
     if not z or g.area(z)<1e-10:continue
     tris=[]
     for j in range(1,len(z)-1):
      tri=[[p[0],a.common.height(plane,p),p[1]]for p in[z[0],z[j],z[j+1]]]
      if abs(a.normal_y(tri))<=1e-12:continue
      if a.normal_y(tri)>0:tri=[tri[0],tri[2],tri[1]]
      tris.append(tri)
     owners.append(dict(id='PORT_FINITE:'+str(len(owners)),polygon_local_xz_m=z,plane_local_y_xz_m=plane,triangles_local_xyz_m=tris,triangles_world_xyz_m=[[world(v)for v in t]for t in tris],maximum_grade=math.hypot(*plane[:2])))
 native_path=H.parent/'north_approach_r03/cache/registered_north_approach_r03_recessed_fixed.render.json';native=read(native_path);under=[];obstacles=[];nrect=0
 for gi,gg in enumerate(native['groups']):
  for qi,q in enumerate(gg['quads']):
   arr=np.asarray(q);n=np.cross(arr[1]-arr[0],arr[2]-arr[0]);mn=arr.min(0);mx=arr.max(0)
   if n[1]<=0 or mx[1]<1.5 or mn[1]>4:continue
   poly=[[v[0],v[2]]for v in q]
   for r in owners:
    if not a.intersects(a.bounds(poly),a.bounds(r['polygon_local_xz_m'])):continue
    clip=g.clip(poly,r['polygon_local_xz_m'])
    if not clip or g.area(clip)<1e-10:continue
    hs=[a.common.height(r['plane_local_y_xz_m'],p)for p in clip];nrect+=1
    if max(q[0][1]-h for h in hs)>1e-8:(under if q[0][1]<2.8 else obstacles).append(dict(group=gi,quad=qi,y=q[0][1],owner=r['id'],min_floor=min(hs),max_floor=max(hs),polygon_local_xz_m=clip))
 # Every physical polygon is an exact subset of the named six-metre ribbon and stops at the fixed-envelope boundary.
 result=dict(schema='riverstone.port_native_approach_profile.v1',status='CANDIDATE_NATIVE_AND_RUNTIME_PENDING',native_pose=s['native_pose'],source_road=road['id'],source_width_m=road['width_m'],source_plan=ref(CITY/'registered_source/plan.json'),source_outer_station=1,outer_cross_section_world_xyz_m=[world([pts[1][0]+j*(-u[1]),2.2,pts[1][1]+j*u[0]])for j in[-3,3]],fixed_envelope=ref(sp),native_source=ref(native_path),domain_local_xz_m=domain,domain_world_xz_m=[[[v[0],v[2]]for p in poly for v in[world([p[0],0,p[1]])]]for poly in domain],owners=owners,area_m2=sum(g.area(p)for p in domain),maximum_grade=max(r['maximum_grade']for r in owners),native_floor_piece_checks=nrect,native_floor_protrusions=under,native_guard_obstacles=obstacles,limits=['Full six-metre named port road footprint only. Source quay cross-section and fixed-span envelope edge remain fixed.','This profile alone is not activation: native supported source, exact actual-source ownership patch, guard clearance, and unchanged-controller replay remain required.'])
 write(H/'port_profile_candidate.json',result);print(json.dumps({k:v for k,v in result.items()if k not in ['owners','domain_local_xz_m','domain_world_xz_m','native_floor_protrusions','native_guard_obstacles','limits','source_plan']},indent=2));print('protrusions',len(under),'guards',len(obstacles))
if __name__=='__main__':main()
