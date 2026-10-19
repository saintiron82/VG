"""Bounded full-width profile solve with explicit coherent court variables.

Public planes and finite route domains stay fixed. Court variables are bounded
by the actual required-core 2.5 m cut/fill screen. Results are source proposals:
native transforms and retirement/support ownership must be rebound atomically.
"""
import json,math,time,collections
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .. import author as a
from ..contour_bulk_r01 import profile_mesh
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'contour_bulk_r01'

def solve(group,data,budgets,limit=.12):
 public=data['public_fixed_regions'];court=group['gate_fixed_regions'];regions=court+public
 parts,cells=profile_mesh.grid_parts(data['private_domain_polygons_xz_m'],regions,1.)
 pts,tris,proof=profile_mesh.topology(parts,[p for r in public for p in r['polygon_xz_m']]);n=len(pts);hids=group['holding_ids'];k=len(hids);f0=np.array([next(h['floor_y_m']for h in group['source_holding_records']if h['id']==hid)for hid in hids]);bounds_court=[]
 for hid,old in zip(hids,f0):
  b=budgets[hid];lo=b['floor_y_m']+b['maximum_required_core_cut_m']-2.5;hi=b['floor_y_m']-b['maximum_required_core_fill_m']+2.5;bounds_court.append((lo,hi))
 target=np.array([min(group['gate_targets'],key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m']for p in pts]);pi=a.geo._SpatialIndex(4);ci=a.geo._SpatialIndex(4)
 for j,r in enumerate(public):pi.add(j,r['polygon_xz_m'])
 for j,r in enumerate(court):ci.add(j,r['polygon_xz_m'])
 fixed={};equal=[];conflicts=[]
 for i,p in enumerate(pts):
  ys=[a.common.height(public[j]['plane_y_xz_m'],p)for j in pi.candidates([p])if a.geo.point_in_convex_polygon(p,public[j]['polygon_xz_m'],1e-9)]
  if ys and max(ys)-min(ys)>1e-7:conflicts.append(dict(point_xz_m=p,ys=ys))
  if ys:fixed[i]=ys[0]
  for j in ci.candidates([p]):
   if a.geo.point_in_convex_polygon(p,court[j]['polygon_xz_m'],1e-9):
    hid=court[j]['id'].split(':COURT_DATUM')[0];equal.append((i,hids.index(hid)))
 if conflicts:return dict(status='PUBLIC_FIXED_CONFLICT',conflicts=conflicts)
 gradients=[];constraints=[]
 for ids in tris:
  p,q,r=[pts[i]for i in ids];ux,uz=q[0]-p[0],q[1]-p[1];vx,vz=r[0]-p[0],r[1]-p[1];det=ux*vz-uz*vx
  if abs(det)<1e-12:return dict(status='DEGENERATE_TOPOLOGY')
  gx=np.array([uz-vz,vz,-uz])/det;gz=np.array([vx-ux,-vx,ux])/det;gradients.append((gx,gz))
  for j in range(32):
   angle=2*math.pi*j/32;constraints.append((ids,gx*math.cos(angle)+gz*math.sin(angle),limit*math.cos(math.pi/32)))
 eqr=[];eqc=[];eqv=[];eqrhs=[]
 for i,j in equal:
  row=len(eqr)//2;eqr.extend([row,row]);eqc.extend([i,n+j]);eqv.extend([1.,-1.]);eqrhs.append(f0[j]-target[i])
 eq=coo_matrix((eqv,(eqr,eqc)),shape=(len(eqrhs),n+2*k+1)).tocsr();iters=[]
 for iteration in range(10):
  rr=[];cc=[];vv=[];rhs=[]
  def add(ids,values,b):
   row=len(rhs);rr.extend([row]*len(ids));cc.extend(ids);vv.extend(values);rhs.append(b)
  for ids,c,b in constraints:add(ids,c,b-float(np.dot(c,target[ids])))
  for i in range(n):
   for s in(-1.,1.):add([i,n+2*k],[s,-1.],0.)
  for j in range(k):
   for s in(-1.,1.):add([n+j,n+k+j],[s,-1.],0.)
  matrix=coo_matrix((vv,(rr,cc)),shape=(len(rhs),n+2*k+1)).tocsr();objective=np.zeros(n+2*k+1);objective[n+k:n+2*k]=1.;objective[-1]=.001
  bounds=[(fixed[i]-target[i],fixed[i]-target[i])if i in fixed else(None,None)for i in range(n)]+[(lo-f0[j],hi-f0[j])for j,(lo,hi)in enumerate(bounds_court)]+[(0,None)]*(k+1)
  lp=linprog(objective,A_ub=matrix,b_ub=rhs,A_eq=eq,b_eq=eqrhs,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
  if not lp.success:return dict(status='NO_FEASIBLE_COHERENT_DATUM',message=lp.message,core_floor_intervals_m=dict(zip(hids,bounds_court)),vertices=n,triangles=len(tris))
  ys=target+lp.x[:n];datums=f0+lp.x[n:n+k];bad=[];grades=[]
  for ids,(gx,gz)in zip(tris,gradients):
   dx,dz=float(np.dot(gx,ys[ids])),float(np.dot(gz,ys[ids]));g=math.hypot(dx,dz);grades.append(g)
   if g>limit+1e-8:bad.append((ids,(gx*dx+gz*dz)/g,limit))
  iters.append(dict(iteration=iteration,maximum_gradient=max(grades),violations=len(bad)))
  if not bad:break
  constraints.extend(bad)
 else:return dict(status='GRADIENT_REFINEMENT_HOLD',iterations=iters)
 faces=[]
 for j,ids in enumerate(tris):
  tr=[[pts[i][0],float(ys[i]),pts[i][1]]for i in ids]
  if a.normal_y(tr)<0:tr=[tr[0],tr[2],tr[1]]
  faces.append(dict(vertices_xyz_m=tr,polygon_xz_m=[[v[0],v[2]]for v in tr],plane_y_xz_m=a.common.plane(tr),gradient=grades[j]))
 return dict(status='FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE',datum_changes=[dict(holding_id=hid,original_floor_y_m=float(f0[j]),candidate_floor_y_m=float(datums[j]),delta_y_m=float(datums[j]-f0[j]),required_core_interval_m=list(bounds_court[j]))for j,hid in enumerate(hids)],maximum_gradient=max(grades),maximum_fixed_error_m=max((abs(ys[i]-y)for i,y in fixed.items()),default=0.),maximum_court_error_m=max((abs(ys[i]-datums[j])for i,j in equal),default=0.),triangles=faces,downward_triangles=sum(a.normal_y(tr['vertices_xyz_m'])<=0 for tr in faces),topology_proof=proof,cell_partition_checks=cells,iterations=iters)

def run():
 groups={g['id']:g for g in json.loads((SOURCE/'shared_private_groups_r03.json').read_bytes())['groups']};summ=json.loads((SOURCE/'private_profiles_summary_r02.json').read_bytes());budgets={r['id']:r for r in json.loads((SOURCE/'required_core_budget.json').read_bytes())['rows']};out=HERE/'coherent_datum_profiles';out.mkdir(exist_ok=True);rows=[]
 for row in summ['groups']:
  if row['status']!='INFEASIBLE_FIXED_FINITE_PROFILE':continue
  path=out/(row['id'].replace(':','_')+'.json')
  if path.exists():d=json.loads(path.read_bytes())
  else:
   t=time.monotonic();data=json.loads((a.ROOT/row['path']).read_bytes());g=groups[row['id']]
   try:res=solve(g,data,budgets)
   except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',error=type(e).__name__,message=str(e))
   d=dict(id=row['id'],holding_ids=row['holding_ids'],source_profile=dict(path=row['path'],sha256=a.sha(a.ROOT/row['path'])),source_core_budget=dict(path=str((SOURCE/'required_core_budget.json').relative_to(a.ROOT)),sha256=a.sha(SOURCE/'required_core_budget.json')),result=res,elapsed_s=time.monotonic()-t,activation=False,policy='Candidate court datums only; all native poses, actual doors, internal paths and finite support must be rebound before activation. Full original private width and all exact public planes are retained.');path.write_text(json.dumps(d,separators=(',',':'))+'\n')
  r=dict(id=d['id'],holding_ids=d['holding_ids'],status=d['result']['status'],datum_changes=d['result'].get('datum_changes'),maximum_gradient=d['result'].get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),elapsed_s=d['elapsed_s']);rows.append(r);print(r,flush=True)
 p=HERE/'coherent_datum_summary_r01.json';assert not p.exists();p.write_text(json.dumps(dict(rows=rows,holding_counts=dict(collections.Counter(r['status']for r in rows for _ in r['holding_ids'])),activation=False),separators=(',',':'))+'\n')
if __name__=='__main__':run()
