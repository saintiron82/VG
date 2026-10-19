import json,math
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .. import author as a
from ..bounded_profile_r01.finite import inside
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'BLOCK_001_R8_C003.json').read_bytes());s=d['result']['solver_input'];p=s['vertices_xz_m'];ts=s['triangles'];fixed={int(k):v for k,v in s['fixed_heights'].items()};n=len(p);rr=[];cc=[];vv=[];rhs=[]
for ti,ids in enumerate(ts):
 u=np.array(p[ids[1]])-p[ids[0]];v=np.array(p[ids[2]])-p[ids[0]];det=u[0]*v[1]-u[1]*v[0];gx=np.array([u[1]-v[1],v[1],-u[1]])/det;gz=np.array([v[0]-u[0],-v[0],u[0]])/det
 for k in range(64):
  c=gx*math.cos(2*math.pi*k/64)+gz*math.sin(2*math.pi*k/64);row=len(rhs)
  for i,w in zip(ids,c):rr.append(row);cc.append(i);vv.append(w)
  rr.append(row);cc.append(n);vv.append(-1.);rhs.append(0.)
mat=coo_matrix((vv,(rr,cc)),shape=(len(rhs),n+1)).tocsr();obj=np.zeros(n+1);obj[n]=1;r=linprog(obj,A_ub=mat,b_ub=rhs,bounds=[(fixed[i]-12,fixed[i]-12)if i in fixed else(None,None)for i in range(n)]+[(0,None)],method='highs');print(r.success,r.fun)
if r.success:
 dual=[]
 for i in fixed:
  value=r.lower.marginals[i]+r.upper.marginals[i]
  if abs(value)>1e-6:dual.append(dict(index=i,point_xz_m=p[i],fixed_y_m=fixed[i],dual=float(value)))
 dual.sort(key=lambda x:-abs(x['dual']));active=[]
 for i,val in enumerate(r.ineqlin.marginals):
  if abs(val)>1e-8:active.append(dict(triangle_index=i//64,direction=i%64,dual=float(val),points=[p[k]for k in ts[i//64]]))
 active.sort(key=lambda x:-abs(x['dual']));write(HERE/'BLOCK_001_R8_C003_duals.json',dict(minimum_gradient=float(r.fun),fixed_duals=dual,active_triangle_constraints=active));print(dual[:10]);print(active[:3])
