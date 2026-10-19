"""One bounded sparse shared-height solve on active public triangle neighbors.
Exact source constraints have zero adjustment. XZ/topology never changes.
The output remains a candidate until finite ownership and seam checks pass.
"""
import collections,json,math,time
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .height_field import HERE,fixed_sources
from . import public_domain as d
from .grid_candidate import grade
from ..r17_district_batches import author as a
SOURCE=HERE/'field_refinement_r01.json';LIMIT=.12

def main():
 start=time.monotonic();source=json.loads(SOURCE.read_bytes());tris=source['triangles_xyz_m'];regions,segments,refs=fixed_sources();assert source['source_refs']==refs;traffic=d.polygons();ti=a.geo._SpatialIndex(8)
 for i,p in enumerate(traffic):ti.add(i,p)
 exclusions=d.outer_handoff()['exclusions'];ei=a.geo._SpatialIndex(8)
 for i,r in enumerate(exclusions):ei.add(i,r['polygon_xz_m'])
 active=[];parts=[]
 for n,t in enumerate(tris):
  p=[[v[0],v[2]]for v in t];hits=a.common.disjoint_union([q for j in ti.candidates(p)if(q:=a.clip(p,traffic[j]))]);owned=a.common.subtract(hits,[exclusions[j]['polygon_xz_m']for j in ei.candidates(p)])
  if owned:active.append(n);parts.append(dict(source_triangle_index=n,polygons_xz_m=owned))
 vertices=[];ids={};faces=[];adj=collections.defaultdict(set)
 for t in tris:
  row=[]
  for v in t:
   key=tuple(round(v[k],10)for k in(0,2))
   if key not in ids:ids[key]=len(vertices);vertices.append([v[0],v[2]])
   row.append(ids[key])
  faces.append(row)
  for i in row:adj[i].update(row)
 bad=[n for n in active if grade(tris[n])>LIMIT+1e-7];near=set(i for n in bad for i in faces[n])
 for _ in range(2):near.update(j for i in list(near)for j in adj[i])
 ri=a.geo._SpatialIndex(8);si=a.geo._SpatialIndex(8)
 for i,r in enumerate(regions):ri.add(i,r['polygon_xz_m'])
 for i,r in enumerate(segments):si.add(i,[[p[0],p[2]]for p in r['xyz_m']])
 fixed=set();fixed_reasons={}
 for i in near:
  p=vertices[i];owners=[]
  for j in ri.candidates([p]):
   if a.geo.point_in_convex_polygon(p,regions[j]['polygon_xz_m'],1e-9):owners.append(regions[j]['id'])
  for j in si.candidates([p]):
   vs=segments[j]['xyz_m'];u,v=[[x[0],x[2]]for x in vs]
   if a.geo.point_segment_distance(p,u,v)<1e-8:owners.append(segments[j]['id'])
  if owners:fixed.add(i);fixed_reasons[str(i)]=owners
 free=sorted(near-fixed);fi={v:i for i,v in enumerate(free)};N=len(free);affected=[n for n in active if any(i in fi for i in faces[n])];immutable_bad=[n for n in bad if n not in affected]
 print('active',len(active),'bad',len(bad),'free',N,'fixed-near',len(fixed),'affected',len(affected),'immutable-bad',immutable_bad,flush=True)
 gradients={};constraints=[]
 for n in affected:
  p,q,r=tris[n];ux,uz=q[0]-p[0],q[2]-p[2];vx,vz=r[0]-p[0],r[2]-p[2];det=ux*vz-uz*vx;gx=np.array([uz-vz,vz,-uz])/det;gz=np.array([vx-ux,-vx,ux])/det;base=a.common.plane(tris[n])[:2];gradients[n]=(gx,gz,base)
  for k in range(16):
   angle=2*math.pi*k/16;constraints.append((n,math.cos(angle),math.sin(angle)))
 iterations=[];last=None
 if immutable_bad:
  status='HELD_FIXED_SOURCE_TRIANGLES_REQUIRE_TOPOLOGY_REPAIR'
 else:
  for it in range(10):
   data=[];cols=[];rows=[];rhs=[]
   for n,c,s in constraints:
    gx,gz,base=gradients[n];coef=c*gx+s*gz;row=len(rhs)
    for i,cf in zip(faces[n],coef):
     if i in fi:rows.append(row);cols.append(fi[i]);data.append(float(cf))
    rhs.append(LIMIT-c*base[0]-s*base[1])
   for i in range(N):
    for sign in(-1,1):
     row=len(rhs);rows.extend([row,row]);cols.extend([i,N]);data.extend([sign,-1]);rhs.append(0.)
   matrix=coo_matrix((data,(rows,cols)),shape=(len(rhs),N+1)).tocsr();obj=np.zeros(N+1);obj[-1]=1
   result=linprog(obj,A_ub=matrix,b_ub=rhs,bounds=[(-.05,.05)]*N+[(0,.05)],method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9,'time_limit':30})
   if not result.success:status='HELD_BOUNDED_LOCAL_SOLVE';iterations.append(dict(iteration=it,status=int(result.status),message=result.message));break
   delta={v:float(result.x[i])for v,i in fi.items()};candidate=[[[v[0],v[1]+delta.get(i,0.),v[2]]for v,i in zip(t,face)]for t,face in zip(tris,faces)];viol=[]
   for n in affected:
    pl=a.common.plane(candidate[n]);g=math.hypot(*pl[:2])
    if g>LIMIT+1e-7:viol.append(n);constraints.append((n,pl[0]/g,pl[1]/g))
   row=dict(iteration=it,maximum_active_gradient=max(grade(candidate[n])for n in active),violating_active_triangles=len(viol),max_height_adjustment_m=float(result.x[-1]),seconds=time.monotonic()-start);iterations.append(row);print(row,flush=True);last=candidate
   if not viol:status='LOCAL_SHARED_HEIGHT_CANDIDATE_PASSES_ACTIVE_GRADIENTS';break
  else:status='HELD_CUTTING_PLANE_LIMIT'
 report=dict(status=status,source_mesh_sha256=a.sha(SOURCE),source_refs=refs,active_triangle_count=len(active),active_input_bad_count=len(bad),free_vertex_count=N,fixed_near_vertex_count=len(fixed),fixed_owner_reasons=fixed_reasons,immutable_bad_triangles=immutable_bad,iterations=iterations,seconds=time.monotonic()-start,scope='Gradient checks apply to source triangles with retained traffic after known native exclusions. Final all-pack/water ownership, exact boundary coverage and actual-controller tests remain required.')
 (HERE/'local_height_solve_review_r01.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
 if last is not None:(HERE/'field_local_solved_r01.json').write_text(json.dumps(dict(report=report,triangles_xyz_m=last,active_source_triangles=active,finite_public_parts=parts),separators=(',',':'))+'\n')
 print(status,flush=True)
if __name__=='__main__':main()
