"""Finite R5-bound interface field. New evidence only; no scene activation."""
from inspect_extents import *
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
import time
import os
GRID=os.environ.get('GRID')=='1'
BUFFER=os.environ.get('BUFFER')=='1'
PREFIX=('buffer_' if BUFFER else 'retaining_')+('grid_' if GRID else 'bound_')
PROPOSALS=json.loads((HERE/('proposed_grid_extents.json' if GRID else 'proposed_extents.json')).read_text())
RETIRED_INDEX=a.geo._SpatialIndex(8)
for _i,_r in enumerate(C['retired_owner_domains']):RETIRED_INDEX.add(_i,_r['polygon_xz_m'])
def retired_at(p):return [C['retired_owner_domains'][i] for i in RETIRED_INDEX.candidates([p]) if a.geo.point_in_convex_polygon(p,C['retired_owner_domains'][i]['polygon_xz_m'],1e-8)]

def distance(p,x,y):
 d=np.array(y)-x;den=float(d@d);t=float((np.array(p)-x)@d/den) if den else 0
 return math.dist(p,(np.array(x)+max(0,min(1,t))*d).tolist()),t

def solve(num):
 g=C['gate_profiles'][num];prop=PROPOSALS[num];gate=g['polygon_xz_m'];envelope=prop['envelope_polygon_xz_m'];floor=next(p['floor_y_m'] for p in C['platforms'] if p['property_id']==g['property_id']);protected=prop['protected'];platforms=[p['polygon_xz_m'] for p in C['platforms']]
 cutmasks=[p['polygon_xz_m'] for p in protected]+platforms
 protective_buffers=[]
 if BUFFER:
  for pr in protected:
   if pr['kind'] not in('door_landing','door_approach','b015_entry','density_entry'):continue
   xx,zz=zip(*pr['polygon_xz_m']);pad=.3;box=[[min(xx)-pad,min(zz)-pad],[max(xx)+pad,min(zz)-pad],[max(xx)+pad,max(zz)+pad],[min(xx)-pad,max(zz)+pad]]
   if a.polygon(a.geo.convex_intersection(box,gate)):continue
   protective_buffers.append(dict(owner_id=pr['owner_id'],polygon_xz_m=box,padding_m=pad,policy='Preserve unchanged entrance and a finite surrounding source band; no replacement profile enters this band.'));cutmasks.append(box)
 print('START',num,flush=True);patches=[];source_rows=[];source_by_key={}
 for mat,index,t,p in candidates(envelope):
  if mat in ('bank','water'):continue
  q=a.polygon(a.geo.convex_intersection(p,envelope))
  if not q:continue
  plane=a.affine_plane(t);key=mat+':'+str(index);source_by_key[key]=dict(material=mat,triangle_index=index,vertices_xyz_m=t,plane_y_xz_m=plane)
  for piece in a.subtract([q],cutmasks):
   overlap=a.polygon(a.geo.convex_intersection(piece,gate));parts=([overlap] if overlap else [])+a.subtract([piece],[gate])
   for pp in parts:patches.append(dict(polygon_xz_m=pp,source_key=key,source_plane=plane,material=mat))
 # The new gate may occupy an explicitly retired source hole. Fill only missing gate, never another hole.
 print('SOURCE_PATCHES',num,len(patches),flush=True);missing=a.subtract([gate],cutmasks+[r['polygon_xz_m'] for r in patches])
 for p in missing:
  # This is only the objective target. Final heights are solved jointly.
  target_tri=next((t for t in g['height_evaluator']['triangles_xyz_m'] if a.geo.point_in_convex_polygon([sum(q[0] for q in p)/len(p),sum(q[1] for q in p)/len(p)],[[v[0],v[2]] for v in t],1e-8)),g['height_evaluator']['triangles_xyz_m'][0])
  patches.append(dict(polygon_xz_m=p,source_key=None,source_plane=a.affine_plane(target_tri),material='ground_stone'))
 print('MISSING',num,len(missing),flush=True);verts=[];buckets=collections.defaultdict(list);votes=[]
 def weld(p,y=None):
  key=tuple(math.floor(v/1e-8) for v in p)
  for dx in (-1,0,1):
   for dz in (-1,0,1):
    for k in buckets[(key[0]+dx,key[1]+dz)]:
     if math.dist(p,verts[k])<1e-8:
      if y is not None:votes[k].append(y)
      return k
  k=len(verts);verts.append(list(p));votes.append([] if y is None else [y]);buckets[key].append(k);return k
 # Use a centroid fan so all collinear seam knots survive.
 records=[]
 for r in patches:
  ids=[weld(p,a.plane_height(r['source_plane'],*p)) for p in r['polygon_xz_m']];records.append((r,ids))
 print('PATCH_VERTICES',num,len(verts),len(records),flush=True);vi=a.geo._SpatialIndex(1)
 for i,p in enumerate(verts):vi.add(i,[p])
 triangles=[];tri_rows=[]
 for r,ids in records:
  boundary=[]
  for i,j in zip(ids,ids[1:]+ids[:1]):
   p,q=verts[i],verts[j];knots=[(0,i)]
   for k in vi.candidates([p,q]):
    if k in (i,j):continue
    d,t=distance(verts[k],p,q)
    if d<1e-8 and 1e-10<t<1-1e-10:knots.append((t,k))
   boundary.extend(k for _,k in sorted(knots))
  center=[sum(verts[k][j] for k in boundary)/len(boundary) for j in (0,1)];ci=weld(center,a.plane_height(r['source_plane'],*center))
  for i,j in zip(boundary,boundary[1:]+boundary[:1]):
   if len(set((ci,i,j)))==3 and a.geo.polygon_area([verts[k] for k in(ci,i,j)])>1e-10:
    triangles.append([ci,i,j]);tri_rows.append(r)
 edge_owners=collections.defaultdict(list)
 for ti,t in enumerate(triangles):
  for i,j in zip(t,t[1:]+t[:1]):edge_owners[tuple(sorted((i,j)))].append(ti)
 fixed_votes=collections.defaultdict(list);boundary=[];unknown=[]
 for e,owners in edge_owners.items():
  if len(owners)!=1:continue
  i,j=e;p,q=verts[i],verts[j];mid=[(p[k]+q[k])/2 for k in(0,1)];r=tri_rows[owners[0]];kind='frozen_outer_seam';source=r['source_key'];boundary_plane=r['source_plane'];outside_source=None
  onprotected=[pr for pr in protected if any(distance(mid,v,w)[0]<1e-7 for v,w in zip(pr['polygon_xz_m'],pr['polygon_xz_m'][1:]+pr['polygon_xz_m'][:1]))]
  entrance=next((pr for pr in onprotected if pr['kind'] in('door_landing','door_approach','b015_entry','density_entry')),None)
  if entrance:
   center=[sum(v[k] for v in entrance['polygon_xz_m'])/len(entrance['polygon_xz_m']) for k in(0,1)];D=math.dist(center,mid);probe=[mid[k]+(center[k]-mid[k])/D*1e-6 for k in(0,1)] if D else mid
   hits=[(mat,idx,xyz,a.affine_plane(xyz)) for mat,idx,xyz,poly in candidates([probe]) if a.geo.point_in_convex_polygon(probe,poly,1e-9)]
   if len(hits)==1:
    mat,idx,xyz,boundary_plane=hits[0];outside_source=dict(material=mat,triangle_index=idx,vertices_xyz_m=xyz,plane_y_xz_m=boundary_plane,owner_id=entrance['owner_id'])
  ongate=all(distance(v,*g['gate_edge_xz_m'])[0]<1e-7 for v in(p,q))
  onplatform=any(any(distance(mid,v,w)[0]<1e-7 for v,w in zip(poly,poly[1:]+poly[:1])) for poly in platforms)
  if ongate:
   kind='property_inner_full_width';fixed_votes[i].append(floor);fixed_votes[j].append(floor)
  elif onplatform:kind='new_platform_retaining_interface'
  elif retired_at(mid):kind='retired_owner_new_restoration_interface'
  elif entrance and outside_source:
   kind='protected_entrance_frozen_seam'
   for k in e:fixed_votes[k].append(a.plane_height(boundary_plane,*verts[k]))
  elif source and r['material'] not in('road','alley','ground_stone') and not entrance:
   kind='nonwalkable_existing_backland_retaining'
  elif source:
   for k in e:fixed_votes[k].append(a.plane_height(r['source_plane'],*verts[k]))
  else:
   kind='unbound_missing_source_boundary';unknown.append([p,q])
  boundary.append(dict(edge_vertex_ids=list(e),kind=kind,source_key=source,plane_y_xz_m=list(boundary_plane),outside_source=outside_source,protected_owner_ids=[pr['owner_id'] for pr in onprotected]))
 # Every knot on the entire inner gate edge is fixed, including internal knots.
 gate_node_ids=[]
 for k,p in enumerate(verts):
  if distance(p,*g['gate_edge_xz_m'])[0]<1e-7:fixed_votes[k].append(floor);gate_node_ids.append(k)
 conflicts=[dict(vertex_id=k,point_xz_m=verts[k],heights=v,spread_m=max(v)-min(v)) for k,v in fixed_votes.items() if max(v)-min(v)>1e-6]
 N=len(verts);target=np.array([sum(v)/len(v) if v else a.effective_source_height(*p) for p,v in zip(verts,votes)])
 fixed={k:sum(v)/len(v) for k,v in fixed_votes.items()};
 for k,v in fixed.items():target[k]=v
 gradients=[]
 for t in triangles:
  p,q,r=[verts[k] for k in t];ux,uz=q[0]-p[0],q[1]-p[1];vx,vz=r[0]-p[0],r[1]-p[1];det=ux*vz-uz*vx
  gradients.append((np.array([uz-vz,vz,-uz])/det,np.array([vx-ux,-vx,ux])/det))
 initial_grades=[math.hypot(float(gx@target[t]),float(gz@target[t])) for t,(gx,gz) in zip(triangles,gradients)]
 # A lower bound proves infeasibility independently of the LP.
 fixed_edges=[]
 for (i,j),owners in edge_owners.items():
  if i in fixed and j in fixed:
   d=math.dist(verts[i],verts[j]);grade=abs(fixed[i]-fixed[j])/d
   if grade>.1200001:fixed_edges.append(dict(vertex_ids=[i,j],length_m=d,height_difference_m=abs(fixed[i]-fixed[j]),minimum_gradient=grade,points_xyz_m=[[verts[k][0],fixed[k],verts[k][1]] for k in(i,j)]))
 base=dict(schema='riverstone.r15_public_interface.v1',index=num,gate_id=g['id'],property_id=g['property_id'],road_id=g['road_id'],property_floor_y_m=floor,source_contract_sha256=a.sha(HERE.parent/'source_contract.json'),source_scene_sha256=a.sha(SCENE),candidate_envelope_polygon_xz_m=envelope,protected_owners=protected,protective_buffers=protective_buffers,gate_polygon_xz_m=gate,gate_width_m=g['width_m'],vertex_count=N,triangle_count=len(triangles),initial_max_triangle_grade=max(initial_grades,default=0),fixed_vertex_count=len(fixed),fixed_conflicts=conflicts,unbound_boundary_segments=unknown,fixed_edge_grade_infeasibilities=fixed_edges,nonmanifold_edges=[list(e) for e,o in edge_owners.items() if len(o)>2],mask_area_m2=sum(a.geo.polygon_area(r['polygon_xz_m']) for r in patches),gate_area_m2=a.geo.polygon_area(gate),source_triangle_count=len(source_by_key))
 print('SETUP',num,N,len(triangles),'initial',base['initial_max_triangle_grade'],'fixed',len(fixed),'conflict',len(conflicts),'unknown',len(unknown),'bad fixed',len(fixed_edges),flush=True)
 if conflicts or unknown or fixed_edges or base['nonmanifold_edges']:
  base.update(status='INFEASIBLE_OR_UNBOUND_FIRST_ENVELOPE',accepted=False,diagnostic_boundary=boundary,vertices_xz_m=verts)
  (HERE/f'{PREFIX}interface_{num:02d}.json').write_text(json.dumps(base,indent=2)+'\n');return base
 constraints=[]
 for t,(gx,gz) in zip(triangles,gradients):
  for k in range(24):
   theta=2*math.pi*k/24;constraints.append((t,gx*math.cos(theta)+gz*math.sin(theta),.12*math.cos(math.pi/24)))
 def optimize(maximum=None):
  rows=[];cols=[];data=[];rhs=[]
  for n,(t,coef,limit) in enumerate(constraints):
   for i,v in zip(t,coef):rows.append(n);cols.append(i);data.append(v)
   rhs.append(limit-float(coef@target[t]))
  for i in range(N):
   for sign in(-1,1):
    n=len(rhs);rows.extend([n,n]);cols.extend([i,N if maximum is None else N+i]);data.extend([sign,-1]);rhs.append(0.)
  size=N+1 if maximum is None else 2*N;A=coo_matrix((data,(rows,cols)),shape=(len(rhs),size)).tocsr();objective=np.zeros(size);objective[N:]=1
  bounds=[(0,0) if i in fixed else ((None,None) if maximum is None else(-maximum,maximum)) for i in range(N)]+[(0,None)]*(size-N)
  return linprog(objective,A_ub=A,b_ub=rhs,bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
 iterations=[];h=target
 for step in range(12):
  result=optimize()
  if not result.success:
   base.update(status='LP_INFEASIBLE_FIRST_ENVELOPE',accepted=False,solver_message=result.message,diagnostic_boundary=boundary,vertices_xz_m=verts)
   (HERE/f'{PREFIX}interface_{num:02d}.json').write_text(json.dumps(base,indent=2)+'\n');print('FAILED',num,result.message,flush=True);return base
  maximum=float(result.x[-1]);result=optimize(maximum+1e-8)
  if not result.success:raise RuntimeError(result.message)
  h=target+result.x[:N];bad=[];grades=[]
  for ti,(t,(gx,gz)) in enumerate(zip(triangles,gradients)):
   x=float(gx@h[t]);z=float(gz@h[t]);grade=math.hypot(x,z);grades.append(grade)
   if grade>.12000001:bad.append(ti);constraints.append((t,(gx*x+gz*z)/grade,.12))
  iterations.append(dict(iteration=step,max_grade=max(grades),violations=len(bad),maximum_target_adjustment_m=float(np.max(np.abs(h-target)))))
  print('SOLVE',num,iterations[-1],flush=True)
  if not bad:break
 else:raise RuntimeError('Unconverged Euclidean grade cuts')
 output=[];volumes=collections.Counter();maxfill=maxcut=0
 for ti,(t,r) in enumerate(zip(triangles,tri_rows)):
  xyz=[[verts[k][0],float(h[k]),verts[k][1]] for k in t];plane=a.affine_plane(xyz);area=a.geo.polygon_area([verts[k] for k in t]);deltas=[float(h[k])-a.plane_height(r['source_plane'],*verts[k]) for k in t];maxfill=max(maxfill,*deltas);maxcut=max(maxcut,*[-v for v in deltas]);volumes['signed_net_m3']+=area*sum(deltas)/3
  output.append(dict(id=f'R15_PUBLIC_{num:02d}:{ti}',polygon_xz_m=[verts[k] for k in t],vertices_xyz_m=xyz,vertex_ids=t,plane_y_xz_m=list(plane),gradient=math.hypot(*plane[:2]),source_key=r['source_key'],material='ground_stone' if a.geo.point_in_convex_polygon([sum(v[0] for v in xyz)/3,sum(v[2] for v in xyz)/3],gate,1e-8) else r['material']))
 for row in boundary:
  row['vertices_xyz_m']=[[verts[k][0],float(h[k]),verts[k][1]] for k in row['edge_vertex_ids']]
  row['frozen_vertices_xyz_m']=[[verts[k][0],a.plane_height(row['plane_y_xz_m'],*verts[k]),verts[k][1]] for k in row['edge_vertex_ids']]
 retaining=[dict(id=f'R15_PUBLIC_{num:02d}:RETAIN:{ri}',classification='nonwalkable inherited backland/body interface; not a gate or public crossing',edge_vertex_ids=row['edge_vertex_ids'],inside_vertices_xyz_m=row['vertices_xyz_m'],outside_frozen_vertices_xyz_m=row['frozen_vertices_xyz_m'],vertices_xyz_m=row['vertices_xyz_m']+list(reversed(row['frozen_vertices_xyz_m'])),source_key=row['source_key'],protected_owner_ids=row['protected_owner_ids']) for ri,row in enumerate(boundary) if row['kind']=='nonwalkable_existing_backland_retaining']
 gate_coverage=sum(a.geo.polygon_area(q) for r in output if(q:=a.polygon(a.geo.convex_intersection(gate,r['polygon_xz_m']))))
 proof=dict(maximum_actual_clipped_triangle_grade=max(r['gradient'] for r in output),grade_limit=.12,maximum_frozen_boundary_error_m=max((abs(h[k]-a.plane_height(r['plane_y_xz_m'],*verts[k])) for r in boundary if r['kind'] in('frozen_outer_seam','protected_entrance_frozen_seam') for k in r['edge_vertex_ids']),default=0.),gate_inner_datum_error_m=max((abs(h[k]-floor) for k in gate_node_ids),default=0.),gate_coverage_area_m2=gate_coverage,gate_area_error_m2=gate_coverage-a.geo.polygon_area(gate),full_width_retained_m=g['width_m'],maximum_fill_m=maxfill,maximum_cut_m=maxcut,**volumes)
 base.update(status='FINITE_PROFILE_SOLVED_PENDING_PARENT_MASK_ACCEPTANCE',accepted=False,iterations=iterations,triangles=output,ownership_masks=[dict(id=f'R15_PUBLIC_{num:02d}:MASK:{k}',polygon_xz_m=r['polygon_xz_m']) for k,r in enumerate(patches)],boundary=boundary,retaining_sides=retaining,proof=proof,source_triangles=list(source_by_key.values()),limits=['Finite preview only; no capsule, native collision, whole-city or activation approval.','New-platform-side boundaries are explicit retaining interfaces except the full-width gate edge.','Outer frozen boundaries use exact source triangle affine heights; protected owner regions are excluded.'])
 (HERE/f'{PREFIX}interface_{num:02d}.json').write_text(json.dumps(base,separators=(',',':'))+'\n');return base
if __name__=='__main__':
 nums=[int(v) for v in sys.argv[1:]] or list(range(19));summary=[]
 for n in nums:
  try:r=solve(n);summary.append({k:v for k,v in r.items() if k in('index','status','proof','fixed_conflicts','unbound_boundary_segments','fixed_edge_grade_infeasibilities','initial_max_triangle_grade','mask_area_m2')})
  except Exception as e:
   import traceback;traceback.print_exc();summary.append(dict(index=n,error=str(e)))
 (HERE/f'{PREFIX}solve_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
