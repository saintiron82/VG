"""Finite preview profile from common source masks; no voxel compilation.

Existing convex clipping and fan triangulation supply topology. A sparse LP
adjusts shared heights only, fixing every exterior seam and the gate at +4.
The full Euclidean triangle gradient is checked after directional cuts.
"""
import json, math, time, collections
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from . import author as a
from world_city.concept_city_v3.review_geometry import fan

PITCH=1.
def halfplane(poly,A,B,C):
 den=A*A+B*B
 if den<1e-20:return poly if C>=-1e-12 else []
 q=[-C*A/den,-C*B/den];r=[q[0]+B,q[1]-A]
 return a.clean(a.geo._clip_halfplane(poly,q,r,1.,0.,True))
def sectors():
 # Polygonal distance facets explicitly meet at each gate corner. This
 # prevents a grid fan from extending a flat gate edge beyond its endpoint.
 p,q=a.SEED[:2];angle=math.atan2(q[1]-p[1],q[0]-p[0]);planes=[(0.,0.,0.)]
 for k in range(64):
  t=angle+2*math.pi*k/64;nx,nz=math.cos(t),math.sin(t);planes.append((nx,nz,-max(nx*x+nz*z for x,z in a.SEED)))
 out=[]
 for A,B,C in planes:
  p=a.COLLAR_BOX
  for D,E,F in planes:
   p=halfplane(p,A-D,B-E,C-F)
   if not p:break
  if p:out.append(dict(polygon_xz_m=p))
 return out
def run():
 start=time.monotonic();rs=[]
 # Solve a regular shared field before clipping to thin road/shoulder masks.
 # Fixing every tiny ownership fragment first can make valid analytic data
 # infeasible on a skinny triangle. The source gate is a fixed internal edge.
 rs=sectors()
 idx=a.geo._SpatialIndex(8)
 for i,r in enumerate(rs):idx.add(i,r['polygon_xz_m'])
 tris=[];vertices=[];buckets=collections.defaultdict(list)
 def weld(p):
  key=tuple(math.floor(v/1e-8) for v in p)
  for dx in (-1,0,1):
   for dz in (-1,0,1):
    for n in buckets[(key[0]+dx,key[1]+dz)]:
     if math.dist(p,vertices[n])<1e-8:return n
  n=len(vertices);vertices.append(p);buckets[key].append(n);return n
 b=a.COLLAR_BOUNDS
 for ix in range(math.floor(b[0]/PITCH),math.ceil(b[2]/PITCH)):
  for iz in range(math.floor(b[1]/PITCH),math.ceil(b[3]/PITCH)):
   x,z=ix*PITCH,iz*PITCH;cell=[[x,z],[x+PITCH,z],[x+PITCH,z+PITCH],[x,z+PITCH]]
   for k in idx.candidates(cell):
    p=a.clean(a.geo.convex_intersection(cell,rs[k]['polygon_xz_m']))
    if not p:continue
    gate=a.clean(a.geo.convex_intersection(p,a.SEED));pieces=([gate] if gate else [])+[q for raw in a.geo.convex_difference(p,a.SEED) if(q:=a.clean(raw))]
    for t in [t for piece in pieces for t in fan(piece)]:
     if a.geo.polygon_area(t)>1e-10:
      ids=[weld(q) for q in t]
      if len(set(ids))==3:tris.append(ids)
 # Conform every triangle edge to nearby existing vertices before solving.
 # This preserves shared seam knots even when adjacent source masks subdivide.
 vi=a.geo._SpatialIndex(1)
 for i,p in enumerate(vertices):vi.add(i,[p])
 conformed=[]
 for ids in tris:
  poly=[]
  for i,j in zip(ids,ids[1:]+ids[:1]):
   p,q=vertices[i],vertices[j];L=math.dist(p,q);knots=[(0,i)]
   for k in vi.candidates([p,q]):
    if k in (i,j):continue
    d,t=a.R04.base._project(*vertices[k],p,q)
    if d<1e-8 and 1e-10<t<1-1e-10:knots.append((t,k))
   poly.extend(k for _,k in sorted(knots))
  for t in fan(poly):
   if a.geo.polygon_area([vertices[k] for k in t])>1e-10:conformed.append(t)
 tris=conformed
 edges=collections.Counter(tuple(sorted((i,j))) for t in tris for i,j in zip(t,t[1:]+t[:1]));fixed={i for e,c in edges.items() if c==1 for i in e}
 fixed.update(i for i,p in enumerate(vertices) if a.gate_distance(*p)<1e-8)
 target=np.array([max(a.prior.road_height_at(a.COLLAR_ROAD,*p),4-.12*a.gate_distance(*p)) for p in vertices]);N=len(vertices)
 gradients=[]
 for t in tris:
  p,q,r=[vertices[i] for i in t];ux,uz=q[0]-p[0],q[1]-p[1];vx,vz=r[0]-p[0],r[1]-p[1];det=ux*vz-uz*vx
  gradients.append((np.array([uz-vz,vz,-uz])/det,np.array([vx-ux,-vx,ux])/det))
 target_grades=[math.hypot(float(np.dot(gx,target[t])),float(np.dot(gz,target[t]))) for t,(gx,gz) in zip(tris,gradients)];worst=max(range(len(tris)),key=lambda n:target_grades[n]);print('Initial triangle',target_grades[worst],[[*vertices[i],target[i]] for i in tris[worst]],'fixed',sum(i in fixed for i in tris[worst]),'nodes',N,'triangles',len(tris),flush=True)
 constraints=[]
 for n,t in enumerate(tris):
  gx,gz=gradients[n]
  for k in range(32):
   angle=2*math.pi*k/32;constraints.append((t,gx*math.cos(angle)+gz*math.sin(angle),.12*math.cos(math.pi/32)))
 def optimize(maximum=None):
  rows=[];cols=[];data=[];rhs=[]
  for n,(t,c,limit) in enumerate(constraints):
   for i,v in zip(t,c):rows.append(n);cols.append(i);data.append(v)
   rhs.append(limit-float(np.dot(c,target[t])))
  off=len(rhs)
  for i in range(N):
   for sign in (-1,1):
    n=len(rhs);rows.extend([n,n]);cols.extend([i,N if maximum is None else N+i]);data.extend([sign,-1]);rhs.append(0.)
  size=N+1 if maximum is None else 2*N
  A=coo_matrix((data,(rows,cols)),shape=(len(rhs),size)).tocsr();objective=np.zeros(size);objective[N:]=1
  bounds=[(0,0) if i in fixed else ((None,None) if maximum is None else (-maximum,maximum)) for i in range(N)]+[(0,None)]*(size-N)
  return linprog(objective,A_ub=A,b_ub=rhs,bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
 iterations=[]
 for step in range(12):
  result=optimize()
  if not result.success:raise RuntimeError(result.message)
  result=optimize(float(result.x[-1])+1e-9)
  if not result.success:raise RuntimeError(result.message)
  h=target+result.x[:N];bad=[];maximum=0
  for n,t in enumerate(tris):
   gx,gz=gradients[n];x=float(np.dot(gx,h[t]));z=float(np.dot(gz,h[t]));g=math.hypot(x,z);maximum=max(maximum,g)
   if g>.120000001:
    bad.append(n);constraints.append((t,(gx*x+gz*z)/g,.12))
  iterations.append(dict(iteration=step,max_gradient=maximum,violations=len(bad),max_vertex_adjustment_m=float(max(abs(result.x[:N]))),sum_vertex_adjustment_m=float(sum(abs(result.x[:N])))));print(iterations[-1],flush=True)
  if not bad:break
 else:raise RuntimeError('Gradient cutting planes did not converge')
 records=[]
 for n,t in enumerate(tris):
  points=[[vertices[i][0],float(h[i]),vertices[i][1]] for i in t];gx,gz=gradients[n];px,pz=float(np.dot(gx,h[t])),float(np.dot(gz,h[t]));c=points[0][1]-px*points[0][0]-pz*points[0][2]
  records.append(dict(id='R14_M11_ROAD_PROFILE:'+str(n),polygon_xz_m=[vertices[i] for i in t],vertices_xyz_m=points,plane_y_xz_m=[px,pz,c]))
 boundary=[dict(edge_vertex_ids=list(e),vertices_xyz_m=[[vertices[i][0],float(h[i]),vertices[i][1]] for i in e]) for e,c in edges.items() if c==1]
 out=dict(schema='riverstone.r14_finite_public_collar.v1',source_plan_sha256=a.prior.build_contract()['source_plan_sha256'],input_author_sha256=a.R04.sha(a.HERE/'author.py'),road_id=a.COLLAR_ROAD,bounds_xz_m=b,pitch_m=PITCH,vertex_count=N,triangle_count=len(tris),area_m2=sum(a.geo.polygon_area(r['polygon_xz_m']) for r in records),iterations=iterations,triangles=records,boundary=boundary,seconds=time.monotonic()-start,limitations=['Finite preview geometry, not native voxel terrain or capsule approval.','Every exterior vertex is fixed to the analytic source; linear boundary segments must be shared with surrounding preview.'])
 (a.HERE/'collar_profile.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print({k:v for k,v in out.items() if k not in ('triangles','boundary')},flush=True)
if __name__=='__main__':run()
