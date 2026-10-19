"""Measure the actual finite gradient needed by the held private source shapes.

This is a diagnostic, not acceptance or a changed design target. Public knots
and native court datums remain exact, and no controller behavior is changed.
"""
import json,math,time,collections
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .screen import HERE,write
from . import profile_mesh
from .. import author as a

def minimum_gradient(points,triangles,fixed):
 n=len(points);equations=[];constraints=[]
 for ids in triangles:
  p,q,r=[points[i]for i in ids];ux,uz=q[0]-p[0],q[1]-p[1];vx,vz=r[0]-p[0],r[1]-p[1];det=ux*vz-uz*vx
  if abs(det)<1e-12:raise ValueError('Degenerate finite triangle')
  gx=np.array([uz-vz,vz,-uz])/det;gz=np.array([vx-ux,-vx,ux])/det;equations.append((gx,gz))
  for k in range(32):angle=2*math.pi*k/32;constraints.append((ids,gx*math.cos(angle)+gz*math.sin(angle)))
 for iteration in range(24):
  rr=[];cc=[];vv=[]
  for j,(ids,c)in enumerate(constraints):
   for i,v in zip(ids,c):rr.append(j);cc.append(i);vv.append(v)
   rr.append(j);cc.append(n);vv.append(-1.)
  mat=coo_matrix((vv,(rr,cc)),shape=(len(constraints),n+1)).tocsr();obj=np.zeros(n+1);obj[-1]=1.;bounds=[(fixed[i],fixed[i])if i in fixed else(None,None)for i in range(n)]+[(0,None)];result=linprog(obj,A_ub=mat,b_ub=np.zeros(len(constraints)),bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
  if not result.success:return dict(status='NO_FINITE_SOLUTION',message=result.message)
  ys=result.x[:n];g=result.x[-1];bad=[];grades=[]
  for ids,(gx,gz)in zip(triangles,equations):
   dx,dz=float(np.dot(gx,ys[ids])),float(np.dot(gz,ys[ids]));v=math.hypot(dx,dz);grades.append(v)
   if v>g+1e-7:bad.append((ids,(gx*dx+gz*dz)/v))
  if not bad:break
  constraints.extend(bad)
 faces=[]
 for j,ids in enumerate(triangles):
  tr=[[points[i][0],float(ys[i]),points[i][1]]for i in ids]
  if a.normal_y(tr)<0:tr=[tr[0],tr[2],tr[1]]
  faces.append(dict(vertices_xyz_m=tr,polygon_xz_m=[[v[0],v[2]]for v in tr],plane_y_xz_m=a.common.plane(tr),gradient=grades[j]))
 return dict(status='MEASURED_FINITE_GRADIENT_ONLY',minimum_linear_bound=float(g),maximum_actual_gradient=max(grades),maximum_fixed_error_m=max(abs(ys[i]-y)for i,y in fixed.items()),iterations=iteration+1,triangles=faces)

def run():
 summary=json.loads((HERE/'private_profiles_summary_r02.json').read_bytes());groups={g['id']:g for g in json.loads((HERE/'shared_private_groups_r03.json').read_bytes())['groups']};rows=[];out=HERE/'required_grade_diagnostics_r01';out.mkdir(exist_ok=True)
 for row in summary['groups']:
  if row['status']!='INFEASIBLE_FIXED_FINITE_PROFILE':continue
  t=time.monotonic();data=json.loads((a.ROOT/row['path']).read_bytes());group=groups[row['id']];fixed_regions=group['gate_fixed_regions']+data['public_fixed_regions'];parts,_=profile_mesh.grid_parts(data['private_domain_polygons_xz_m'],fixed_regions,1.);points,tris,_=profile_mesh.topology(parts,[p for r in data['public_fixed_regions']for p in r['polygon_xz_m']]);idx=a.geo._SpatialIndex(4)
  for i,r in enumerate(fixed_regions):idx.add(i,r['polygon_xz_m'])
  fixed={};conflicts=[]
  for i,p in enumerate(points):
   yy=[a.common.height(fixed_regions[j]['plane_y_xz_m'],p)for j in idx.candidates([p])if a.geo.point_in_convex_polygon(p,fixed_regions[j]['polygon_xz_m'],1e-9)]
   if yy and max(yy)-min(yy)>1e-7:conflicts.append(dict(point_xz_m=p,heights_m=yy))
   if yy:fixed[i]=yy[0]
  result=dict(status='FIXED_HEIGHT_CONFLICT',conflicts=conflicts)if conflicts else minimum_gradient(points,tris,fixed)
  record=dict(id=row['id'],holding_ids=row['holding_ids'],result=result,private_area_m2=sum(a.geo.polygon_area(p)for p in data['private_domain_polygons_xz_m']),source_routes=[dict(id=h['id'],court_y_m=h['floor_y_m'],gate_xz_m=h['gate_position_xz_m'],public_target_xz_m=h['public_target_xz_m'],centerline_length_m=sum(math.dist(u,v)for u,v in zip(h.get('external_polyline_xz_m',h.get('external_route_centerline_xz_m',[h['gate_position_xz_m'],h['public_target_xz_m']])),h.get('external_polyline_xz_m',h.get('external_route_centerline_xz_m',[h['gate_position_xz_m'],h['public_target_xz_m']]))[1:])))for h in []],elapsed_s=time.monotonic()-t,activation=False)
  # The full source route is retained in the group; report its actual key and
  # do not replace a bent route with a straight-line length.
  record['source_holding_records']=group['source_holding_records'];record['public_fixed_regions']=data['public_fixed_regions']
  p=out/(row['id'].replace(':','_')+'.json');p.write_text(json.dumps(record,separators=(',',':'))+'\n');rows.append(dict(id=row['id'],holding_ids=row['holding_ids'],status=result['status'],maximum_actual_gradient=result.get('maximum_actual_gradient'),path=str(p.relative_to(a.ROOT)),sha256=a.sha(p),elapsed_s=record['elapsed_s']));print(rows[-1],flush=True)
 write('required_grade_summary_r01.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
