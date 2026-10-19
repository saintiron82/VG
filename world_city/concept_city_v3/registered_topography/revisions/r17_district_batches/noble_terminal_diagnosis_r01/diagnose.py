import math,json
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import shortest_path
from ..bounded_profile_r02 import gradient

def solve_field(points,triangles,fixed,targets,limit=.12):
 n=len(points);rr=[];cc=[];vv=[];rhs=[];grads=[];edges={};fixed_edges=[];fixed_tri=[]
 for ti,ids in enumerate(triangles):
  p,q,r=[points[i]for i in ids];u=np.array(q)-p;v=np.array(r)-p;det=u[0]*v[1]-u[1]*v[0]
  gx=np.array([u[1]-v[1],v[1],-u[1]])/det;gz=np.array([v[0]-u[0],-v[0],u[0]])/det;grads.append((gx,gz))
  if all(i in fixed for i in ids):
   ys=[fixed[i]for i in ids];g=math.hypot(np.dot(gx,ys),np.dot(gz,ys));fixed_tri.append(dict(triangle_index=ti,indices=ids,points=[points[i]for i in ids],heights=ys,gradient=g))
  for x,y in zip(ids,ids[1:]+ids[:1]):
   length=math.dist(points[x],points[y]);edges[tuple(sorted([x,y]))]=length
   if x in fixed and y in fixed and length>1e-10:fixed_edges.append(dict(indices=[x,y],points=[points[x],points[y]],heights=[fixed[x],fixed[y]],grade=abs(fixed[x]-fixed[y])/length))
  for k in range(128):
   angle=2*math.pi*k/128;c=gx*math.cos(angle)+gz*math.sin(angle);row=len(rhs)
   for i,w in zip(ids,c):rr.append(row);cc.append(i);vv.append(w)
   rr.append(row);cc.append(n);vv.append(-1.);rhs.append(0.)
 mat=coo_matrix((vv,(rr,cc)),shape=(len(rhs),n+1)).tocsr();obj=np.zeros(n+1);obj[n]=1
 res=linprog(obj,A_ub=mat,b_ub=rhs,bounds=[(fixed[i],fixed[i])if i in fixed else(None,None)for i in range(n)]+[(0,None)],method='highs')
 diag=dict(minimum_directional_grade=float(res.x[n])if res.success else None,minimum_message=res.message,largest_fixed_triangles=sorted(fixed_tri,key=lambda r:-r['gradient'])[:12],largest_fixed_edges=sorted(fixed_edges,key=lambda r:-r['grade'])[:12])
 if res.success:
  ys=res.x[:n];gg=[math.hypot(np.dot(gx,ys[ids]),np.dot(gz,ys[ids]))for ids,(gx,gz)in zip(triangles,grads)];diag['minimax_maximum_actual_grade']=max(gg);diag['minimax_bad_triangles']=[dict(index=i,indices=triangles[i],points=[points[k]for k in triangles[i]],heights=list(ys[triangles[i]]),fixed=[k in fixed for k in triangles[i]],gradient=gg[i])for i in sorted(range(len(gg)),key=lambda i:-gg[i])[:15]]
 result=gradient.solve_field(points,triangles,fixed,targets,limit);result['diagnostic']=diag;result['solver_input']=dict(vertices_xz_m=points,triangles=triangles,fixed_heights={str(k):v for k,v in fixed.items()},target_heights=targets)
 return result
