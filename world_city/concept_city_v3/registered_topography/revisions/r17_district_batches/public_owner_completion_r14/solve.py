"""Continuous private top with explicit millimetre incident-public risers.

All source public planes remain exact. The private field may terminate within
4.151 mm of each actual source plane, and every nonzero difference gets a finite
vertical sheet. An LP minimizes that boundary tolerance before target movement.
"""
import json,math,time,collections
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..public_owner_completion_r13.solve import inside,interval
from ..public_owner_completion_r05.solve import proxy as mesh
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'public_owner_completion_r06/BLOCK_008_R8_C003_profile.json'
MAX_RISER=.004151

def solve(points,tris,court,public,limit=.12):
 n=len(points);ci=index(court);pi=index(public);fixed={};seams={};targets=[]
 for i,p in enumerate(points):
  cy=[a.common.height(r['plane_y_xz_m'],p)for j in ci.candidates([p])if inside(p,(r:=court[j])['polygon_xz_m'])]
  py=[(j,a.common.height(r['plane_y_xz_m'],p))for j in pi.candidates([p])if inside(p,(r:=public[j])['polygon_xz_m'])]
  if cy:assert max(cy)-min(cy)<1e-7;fixed[i]=cy[0]
  if py:seams[i]=py
  targets.append(cy[0]if cy else py[0][1]if py else court[0]['plane_y_xz_m'][2])
 target=np.array(targets);gradients=[];constraints=[]
 for ids in tris:
  p,q,r=[points[i]for i in ids];ux,uz=q[0]-p[0],q[1]-p[1];vx,vz=r[0]-p[0],r[1]-p[1];det=ux*vz-uz*vx
  if abs(det)<1e-14:raise ValueError('Degenerate source topology')
  gx=np.array([uz-vz,vz,-uz])/det;gz=np.array([vx-ux,-vx,ux])/det;gradients.append((gx,gz))
  for k in range(32):
   angle=2*math.pi*k/32;constraints.append((ids,gx*math.cos(angle)+gz*math.sin(angle),limit*math.cos(math.pi/32)))
 iterations=[]
 for iteration in range(10):
  rr=[];cc=[];vv=[];rhs=[]
  def add(ids,c,b):
   row=len(rhs);scale=max(1.,max(map(abs,c)));rr.extend([row]*len(ids));cc.extend(ids);vv.extend(v/scale for v in c);rhs.append(b/scale)
  for ids,c,b in constraints:add(ids,c,b-float(np.dot(c,target[ids])))
  for i in range(n):
   for sign in(-1.,1.):add([i,n+1],[sign,-1.],0.)
  for i,rows in seams.items():
   for j,y in rows:
    for sign in(-1.,1.):add([i,n],[sign,-1.],sign*(y-target[i]))
  mat=coo_matrix((vv,(rr,cc)),shape=(len(rhs),n+2)).tocsr();obj=np.zeros(n+2);obj[n]=1.;obj[n+1]=1e-5
  bounds=[(fixed[i]-target[i],fixed[i]-target[i])if i in fixed else(None,None)for i in range(n)]+[(0,MAX_RISER),(0,None)]
  result=linprog(obj,A_ub=mat,b_ub=rhs,bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
  if not result.success:return dict(status='INFEASIBLE_BOUNDED_INCIDENT_RISER_PROFILE',message=result.message,vertices=n,triangles=len(tris))
  ys=target+result.x[:n];bad=[];grades=[]
  for ids,(gx,gz)in zip(tris,gradients):
   # Evaluate height differences to avoid cancellation on short triangles.
   dy=ys[ids]-ys[ids[0]];dx,dz=float(np.dot(gx,dy)),float(np.dot(gz,dy));g=math.hypot(dx,dz);grades.append(g)
   if g>limit+1e-8:bad.append((ids,(gx*dx+gz*dz)/g,limit))
  iterations.append(dict(iteration=iteration,maximum_gradient=max(grades),violations=len(bad),boundary_slack_m=float(result.x[n])))
  print(iterations[-1],flush=True)
  if not bad:break
  constraints.extend(bad)
 else:return dict(status='GRADE_REFINEMENT_HOLD',iterations=iterations)
 faces=[]
 for j,ids in enumerate(tris):
  tr=[[points[i][0],float(ys[i]),points[i][1]]for i in ids]
  if a.normal_y(tr)<0:tr=[tr[0],tr[2],tr[1]]
  faces.append(dict(id='PROFILE:'+str(j),vertices_xyz_m=tr,polygon_xz_m=[[v[0],v[2]]for v in tr],plane_y_xz_m=a.common.plane(tr),gradient=grades[j]))
 return dict(status='PASSED_FINITE_TRIANGLE_GRADE',vertices_xz_m=points,heights_m=list(map(float,ys)),triangles=faces,maximum_gradient=max(grades),grade_limit=limit,maximum_fixed_error_m=max((abs(ys[i]-y)for i,y in fixed.items()),default=0.),maximum_public_connection_height_m=max((abs(ys[i]-y)for i,rows in seams.items()for j,y in rows),default=0.),iterations=iterations,activation=False)

def run():
 start=time.monotonic();source=json.loads(SOURCE.read_bytes());domains=source['private_domain_polygons_xz_m'];court=source['court_fixed_regions'];public=source['incident_public_fixed_regions'];seams=[];boundary_sources=[]
 # Only actual boundary intersection points are knots. Public polygon interiors
 # do not tessellate the disjoint private field into artificial thin strips.
 pi=index(public)
 for poly in domains:
  for p,q in zip(poly,poly[1:]+poly[:1]):
   for j in pi.candidates([p,q]):
    span=interval(p,q,public[j]['polygon_xz_m'])
    if span and (span[1]-span[0])*math.dist(p,q)>1e-7:
     for t in span:seams.append([(1-t)*p[k]+t*q[k]for k in(0,1)])
     boundary_sources.append(dict(edge_xz_m=[p,q],span=span,public_region_id=public[j]['id']))
 parts,cells=mesh.grid_parts(domains,court,pitch=.5);points,tris,proof=mesh.topology(parts,seams);print('topology',len(points),len(tris),len(seams),flush=True)
 result=solve(points,tris,court,public);out=dict(source,source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),result=result,grade_limit=.12,maximum_permitted_incident_riser_m=MAX_RISER,public_boundary_source_incidence=boundary_sources,topology_proof=proof,cell_partition_checks=cells,elapsed_s=time.monotonic()-start,activation=False)
 if result['status']=='PASSED_FINITE_TRIANGLE_GRADE':
  edges=collections.defaultdict(list)
  for j,t in enumerate(tris):
   for u,v in zip(t,t[1:]+t[:1]):edges[tuple(sorted((u,v)))].append(j)
  risers=[];maxstep=0.
  for (u,v),inc in edges.items():
   if len(inc)!=1:continue
   p,q=points[u],points[v];y=[result['heights_m'][u],result['heights_m'][v]]
   for j in pi.candidates([p,q]):
    r=public[j];span=interval(p,q,r['polygon_xz_m'])
    if not span or(span[1]-span[0])*math.dist(p,q)<=1e-7:continue
    ps=[[(1-t)*p[k]+t*q[k]for k in(0,1)]for t in span];py=[(1-t)*y[0]+t*y[1]for t in span];sy=[a.common.height(r['plane_y_xz_m'],v)for v in ps];delta=[py[k]-sy[k]for k in(0,1)];step=max(map(abs,delta));maxstep=max(maxstep,step)
    if step<1e-8:continue
    spans=[(0.,1.)]
    if delta[0]*delta[1]<0:cross=delta[0]/(delta[0]-delta[1]);spans=[(0.,cross),(cross,1.)]
    emitted=[]
    for lo,hi in spans:
     qp=[[(1-t)*ps[0][k]+t*ps[1][k]for k in(0,1)]for t in(lo,hi)];ay=[(1-t)*py[0]+t*py[1]for t in(lo,hi)];by=[(1-t)*sy[0]+t*sy[1]for t in(lo,hi)];quad=[[qp[0][0],ay[0],qp[0][1]],[qp[1][0],ay[1],qp[1][1]],[qp[1][0],by[1],qp[1][1]],[qp[0][0],by[0],qp[0][1]]]
     emitted.extend([[quad[0],quad[1],quad[2]],[quad[0],quad[2],quad[3]]])
    risers.append(dict(source_public_region_id=r['id'],edge_xz_m=ps,private_heights_m=py,public_heights_m=sy,maximum_step_m=step,triangles_xyz_m=emitted,material='bank',walking_surface=False))
  out.update(vertical_risers=risers,maximum_public_riser_m=maxstep)
  if maxstep>MAX_RISER+1e-7:out['result']['status']='HELD_EXCESS_PUBLIC_RISER'
 write(HERE/'BLOCK_008_R8_C003.json',out);print(result['status'],out.get('maximum_public_riser_m'),flush=True)
if __name__=='__main__':run()
