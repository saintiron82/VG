"""Coherent-datum continuation for source-bound millimetre incident risers."""
import collections,json,math,time,types
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .. import author as a
from ..incident_risers_r01 import solve as first
HERE=Path(__file__).resolve().parent
# Topology consolidates coincident vertices within 1 nm. This boundary predicate
# uses the same distance solely for incidence, never expands a clipping mask.
def interval(p,q,poly):
 sign=1 if a.geo.signed_polygon_area(poly)>0 else -1;lo,hi=0.,1.;eps=1.01e-9
 for u,v in zip(poly,poly[1:]+poly[:1]):
  length=math.dist(u,v)
  if length<1e-12:continue
  f=sign*a.geo._cross(u,v,p)/length;g=sign*a.geo._cross(u,v,q)/length;d=g-f
  if max(abs(f),abs(g))<=eps:continue
  if abs(d)<1e-14:
   if f< -eps:return None
  else:
   t=-f/d
   if d>0:lo=max(lo,t)
   else:hi=min(hi,t)
  if lo>hi+1e-12:return None
 return [max(0.,lo),min(1.,hi)]if hi-lo>1e-10 else None

def variable_solver(group,source,budgets):
 def solve(pts,tris,fixed,target_heights,limit=.12):
  n=len(pts);hids=group['holding_ids'];k=len(hids);target=np.array(target_heights);f0=np.array([next(r['floor_y_m']for r in group['source_holding_records']if r['id']==h)for h in hids]);equal=[];publicfixed={};pi=first.index(source['public_fixed_regions']);ci=first.index(group['gate_fixed_regions']);bounds_court=[]
  for hid in hids:
   b=budgets[hid];bounds_court.append((b['floor_y_m']+b['maximum_required_core_cut_m']-2.5,b['floor_y_m']-b['maximum_required_core_fill_m']+2.5))
  for i,p in enumerate(pts):
   if i in fixed:
    public_matches=[r for j in pi.candidates([p])if a.geo.point_in_convex_polygon(p,(r:=source['public_fixed_regions'][j])['polygon_xz_m'],1e-9)]
    if any(abs(a.common.height(r['plane_y_xz_m'],p)-fixed[i])<1e-7 for r in public_matches):publicfixed[i]=fixed[i]
   for j in ci.candidates([p]):
    r=group['gate_fixed_regions'][j]
    if a.geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-9):equal.append((i,hids.index(r['id'].split(':COURT_DATUM')[0])))
  gradients=[];constraints=[]
  for ids in tris:
   p,q,r=[pts[i]for i in ids];ux,uz=q[0]-p[0],q[1]-p[1];vx,vz=r[0]-p[0],r[1]-p[1];det=ux*vz-uz*vx
   if abs(det)<1e-12:return dict(status='DEGENERATE_TOPOLOGY')
   gx=np.array([uz-vz,vz,-uz])/det;gz=np.array([vx-ux,-vx,ux])/det;gradients.append((gx,gz))
   for j in range(32):
    angle=2*math.pi*j/32;constraints.append((ids,gx*math.cos(angle)+gz*math.sin(angle),limit*math.cos(math.pi/32)))
  er=[];ec=[];ev=[];eb=[]
  for i,j in equal:
   row=len(eb);er.extend([row,row]);ec.extend([i,n+j]);ev.extend([1.,-1.]);eb.append(f0[j]-target[i])
  eq=coo_matrix((ev,(er,ec)),shape=(len(eb),n+2*k+1)).tocsr();iters=[]
  for iteration in range(10):
   rr=[];cc=[];vv=[];rhs=[]
   def add(ids,values,b):
    row=len(rhs);rr.extend([row]*len(ids));cc.extend(ids);vv.extend(values);rhs.append(b)
   for ids,c,b in constraints:add(ids,c,b-float(np.dot(c,target[ids])))
   for i in range(n):
    for s in(-1.,1.):add([i,n+2*k],[s,-1.],0.)
   for j in range(k):
    for s in(-1.,1.):add([n+j,n+k+j],[s,-1.],0.)
   matrix=coo_matrix((vv,(rr,cc)),shape=(len(rhs),n+2*k+1)).tocsr();obj=np.zeros(n+2*k+1);obj[n+k:n+2*k]=1.;obj[-1]=.001
   bounds=[(publicfixed[i]-target[i],publicfixed[i]-target[i])if i in publicfixed else(None,None)for i in range(n)]+[(lo-f0[j],hi-f0[j])for j,(lo,hi)in enumerate(bounds_court)]+[(0,None)]*(k+1)
   lp=linprog(obj,A_ub=matrix,b_ub=rhs,A_eq=eq,b_eq=eb,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
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
  return dict(status='PASSED_FINITE_TRIANGLE_GRADE',vertices_xz_m=pts,heights_m=list(map(float,ys)),triangles=faces,maximum_gradient=max(grades),maximum_fixed_error_m=max((abs(ys[i]-y)for i,y in publicfixed.items()),default=0.),datum_changes=[dict(holding_id=h,original_floor_y_m=float(f0[j]),candidate_floor_y_m=float(datums[j]),delta_y_m=float(datums[j]-f0[j]),required_core_interval_m=list(bounds_court[j]))for j,h in enumerate(hids)],maximum_court_error_m=max((abs(ys[i]-datums[j])for i,j in equal),default=0.),iterations=iters,activation=False)
 return solve

def run():
 groups=json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups'];budgets={r['id']:r for r in json.loads((a.HERE/'contour_bulk_r01/required_core_budget.json').read_bytes())['rows']};rows=[]
 for hid in first.IDS:
  group=next(g for g in groups if g['holding_ids']==[hid]);p=first.INPUT/'private_profiles'/(group['id'].replace(':','_')+'.json');source=json.loads(p.read_bytes());out=HERE/(hid.replace(':','_')+'.json')
  if out.exists():d=json.loads(out.read_bytes())
  else:
   start=time.monotonic();namespace=dict(first.solve_one.__globals__);namespace['interval']=interval;namespace['regeneration']=types.SimpleNamespace(solve_field=variable_solver(group,source,budgets));solver=types.FunctionType(first.solve_one.__code__,namespace);res=solver(group,source);d=dict(id=group['id'],holding_ids=[hid],private_domain_polygons_xz_m=source['private_domain_polygons_xz_m'],public_fixed_regions=source['public_fixed_regions'],source=dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),result=res,elapsed_s=time.monotonic()-start,activation=False);first.write(out,d)
  brief=dict(holding_id=hid,status=d['result']['status'],path=str(out.relative_to(a.ROOT)),sha256=a.sha(out),elapsed_s=d['elapsed_s']);rows.append(brief);print(brief,flush=True)
 first.write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
