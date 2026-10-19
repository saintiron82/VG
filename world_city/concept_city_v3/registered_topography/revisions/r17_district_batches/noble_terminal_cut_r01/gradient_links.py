"""Finite district grade fields on shared source topology.

No voxel mesher. Heights are solved on caller-supplied finite triangles, with
exact fixed walking seams and a measured Euclidean gradient bound per triangle.
Nonwalking lateral closures are separate explicit source geometry.
"""
import math
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .. import author as a

def solve_field(vertices_xz_m,triangles,fixed_heights,target_heights,limit=.12,equalities=()):
 n=len(vertices_xz_m);target=np.asarray(target_heights,float);gradients=[];constraints=[]
 for ids in triangles:
  p,q,r=[vertices_xz_m[i]for i in ids];ux,uz=q[0]-p[0],q[1]-p[1];vx,vz=r[0]-p[0],r[1]-p[1];det=ux*vz-uz*vx
  if abs(det)<1e-12:raise ValueError('Degenerate grade topology')
  gx=np.array([uz-vz,vz,-uz])/det;gz=np.array([vx-ux,-vx,ux])/det;gradients.append((gx,gz))
  for k in range(32):
   angle=2*math.pi*k/32;constraints.append((ids,gx*math.cos(angle)+gz*math.sin(angle),limit*math.cos(math.pi/32)))
 iterations=[]
 for iteration in range(8):
  rr=[];cc=[];vv=[];rhs=[]
  for ids,c,b in constraints:
   row=len(rhs)
   for i,v in zip(ids,c):rr.append(row);cc.append(i);vv.append(v)
   rhs.append(b-float(np.dot(c,target[ids])))
  for i in range(n):
   for sign in(-1.,1.):
    row=len(rhs);rr.extend([row,row]);cc.extend([i,n]);vv.extend([sign,-1.]);rhs.append(0.)
  mat=coo_matrix((vv,(rr,cc)),shape=(len(rhs),n+1)).tocsr();obj=np.zeros(n+1);obj[-1]=1.
  bounds=[(fixed_heights[i]-target[i],fixed_heights[i]-target[i])if i in fixed_heights else(None,None)for i in range(n)]+[(0,None)]
  er=[];ec=[];ev=[];eb=[]
  for j,(left,right,delta) in enumerate(equalities):
   er.extend([j,j]);ec.extend([right,left]);ev.extend([1.,-1.]);eb.append(delta-target[right]+target[left])
  em=coo_matrix((ev,(er,ec)),shape=(len(eb),n+1)).tocsr()if eb else None
  result=linprog(obj,A_ub=mat,b_ub=rhs,A_eq=em,b_eq=eb if eb else None,bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
  if not result.success:return dict(status='INFEASIBLE_FIXED_FINITE_PROFILE',message=result.message,vertex_count=n,triangle_count=len(triangles),grade_limit=limit)
  ys=target+result.x[:n];bad=[];grades=[]
  for ids,(gx,gz)in zip(triangles,gradients):
   dx,dz=float(np.dot(gx,ys[ids])),float(np.dot(gz,ys[ids]));g=math.hypot(dx,dz);grades.append(g)
   if g>limit+1e-8:bad.append((ids,(gx*dx+gz*dz)/g,limit))
  iterations.append(dict(iteration=iteration,max_gradient=max(grades),violations=len(bad),maximum_vertex_adjustment_m=float(max(abs(result.x[:n])))))
  if not bad:break
  constraints.extend(bad)
 else:raise ValueError('Gradient refinement did not converge')
 faces=[]
 for j,ids in enumerate(triangles):
  tri=[[vertices_xz_m[i][0],float(ys[i]),vertices_xz_m[i][1]]for i in ids]
  if a.normal_y(tri)<0:tri=[tri[0],tri[2],tri[1]]
  faces.append(dict(id='PROFILE:'+str(j),vertices_xyz_m=tri,polygon_xz_m=[[v[0],v[2]]for v in tri],plane_y_xz_m=a.common.plane(tri),gradient=grades[j]))
 return dict(status='PASSED_FINITE_TRIANGLE_GRADE',vertices_xz_m=vertices_xz_m,heights_m=list(map(float,ys)),triangles=faces,fixed_vertex_count=len(fixed_heights),maximum_fixed_error_m=max((abs(ys[i]-y)for i,y in fixed_heights.items()),default=0.),maximum_gradient=max(grades),grade_limit=limit,iterations=iterations,activation=False)
