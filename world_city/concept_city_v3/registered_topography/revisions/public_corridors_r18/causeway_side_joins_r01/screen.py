import json,math,pathlib,hashlib
from ..north_junction_transition_r01.profile import half,val,minus
from .. import finite_geometry_r03 as g
from ...r17_district_batches import author as a
C=pathlib.Path('world_city/concept_city_v3');D=C/'registered_topography/revisions/public_corridors_r18/causeway_side_joins_r01';S=C/'assemblies/waterworks/registered_bridge/side_joins_r01/north_side_interfaces.json';P=C/'assemblies/waterworks/registered_bridge/north_approach_r03/profile.json'
survey=json.loads(S.read_bytes());profile=json.loads(P.read_bytes());B=profile['bridge_frame']['basis'];T=profile['bridge_frame']['translation']
def w(l):return [T[0]+B[0][0]*l[0]+B[0][2]*l[2],l[1],T[2]+B[2][0]*l[0]+B[2][2]*l[2]]
def sideplanes(sign,k):
 out=[];idx=0 if sign<0 else -1
 for n in range(3):
  u=profile['sections_local_xyz_m'][n][idx];v=profile['sections_local_xyz_m'][n+1][idx];u=w(u);v=w(v)
  dx,dz=v[0]-u[0],v[2]-u[2];L=math.hypot(dx,dz);nx,nz=sign*(-dz/L),sign*(dx/L) # left is positive native z
  # Native edge tangent gradient, lateral fall independent of any hidden field.
  slope=(v[1]-u[1])/L;gx=slope*dx/L-k*nx;gz=slope*dz/L-k*nz
  out.append([gx,gz,u[1]-gx*u[0]-gz*u[2]])
 return out

def field(pls,p):return min(max(val(pls[0],p),val(pls[1],p)),val(pls[2],p))
def inside(poly,p):
 ss=[]
 for u,v in zip(poly,poly[1:]+poly[:1]):
  L=math.dist(u,v)
  if L:ss.append(((v[0]-u[0])*(p[1]-u[1])-(v[1]-u[1])*(p[0]-u[0]))/L)
 return not ss or min(ss)>=-1e-8 or max(ss)<=1e-8

def old_height(r,p):
 hs=[]
 for row in r['current_runtime_source_faces']:
  if row['runtime_source_key'][0]=='bank':continue
  t=row['collision_triangle_xyz_m'];poly=[[v[0],v[2]]for v in t]
  if g.area(poly)<=0 or not(min(v[0]for v in poly)-1e-8<=p[0]<=max(v[0]for v in poly)+1e-8 and min(v[1]for v in poly)-1e-8<=p[1]<=max(v[1]for v in poly)+1e-8):continue
  if inside(poly,p):hs.append(val(a.common.plane(t),p))
 return max(hs)if hs else None

def main():
 out=[]
 for r,sign in zip(survey['interfaces'],[-1,1]):
  u,v=r['source_polyline_tail_xz_m'][:2];dx,dz=v[0]-u[0],v[1]-u[1];L=math.hypot(dx,dz);ns=[-dz/L,dx/L];edge=[[u[0]+t*ns[0],u[1]+t*ns[1]]for t in[-2,-1,0,1,2]]
  for k in [.06,.066,.08,.1,.12]:
   pls=sideplanes(sign,k);rows=[dict(p=q,old=old_height(r,q),field=field(pls,q))for q in edge];out.append(dict(id=r['id'],lateral_grade=k,maximum_grade=max(math.hypot(*p[:2])for p in pls),outer_cross_section=rows,planes=pls))
 (D/'initial_screen.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
