"""Finite native common walking collision; native visuals and controller unchanged."""
from pathlib import Path
import sys,json,math,time,collections,copy
OUT=Path(__file__).resolve().parent;RES=OUT.parents[1];BASE=RES.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
OUT=Path(__file__).resolve().parent;R02=OUT.parents[1]/'common_entry_repair_r02'

def write(name,obj):p=OUT/name;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
def normal(q):return np.cross(np.subtract(q[1],q[0]),np.subtract(q[2],q[0]))
def area3(q):return sum(float(np.linalg.norm(normal([q[0],q[i],q[i+1]])))/2 for i in range(1,len(q)-1))if len(q)>2 else 0
def clip3(q,fn,inside=True):
 out=[]
 for a,c in zip(q,q[1:]+q[:1]):
  da,dc=fn(a),fn(c);ia=da>=-1e-10 if inside else da<=1e-10;ic=dc>=-1e-10 if inside else dc<=1e-10
  if ia:out.append(a)
  if ia!=ic and abs(da-dc)>1e-15:
   t=da/(da-dc);out.append([a[j]+t*(c[j]-a[j])for j in range(3)])
 return out if area3(out)>1e-11 else []
def cutprism(q,poly):
 # Partition exact native face, including zero-plan-area vertical faces.
 center=[sum(p[k]for p in poly)/len(poly)for k in(0,1)];inside=q;outside=[]
 for a,c in zip(poly,poly[1:]+poly[:1]):
  dx,dz=c[0]-a[0],c[1]-a[1];sign=1 if dx*(center[1]-a[1])-dz*(center[0]-a[0])>=0 else-1
  fn=lambda v:sign*(dx*(v[2]-a[1])-dz*(v[0]-a[0]));piece=clip3(inside,fn,False)if inside else[]
  if piece:outside.append(piece)
  inside=clip3(inside,fn)if inside else[]
 return outside,inside
def godot_tris(q):return [[q[0],q[i+1],q[i]]for i in range(1,len(q)-1)if area3([q[0],q[i+1],q[i]])>1e-11]
def main():
 t=time.monotonic();pack=load(R02/'resolved_placements.json');p=next(p for p in pack['placements']if p['role']=='fine_access');native=load(ROOT/p['cache']['path']);pose=p['position_m'];assert p['yaw_rad']==0
 proof=load(R02/'native_ground_candidate_audit.json');tops=proof['new_native_upward_faces'];upper=[];ui=geo._SpatialIndex(4)
 for r in sorted(tops,key=lambda r:-r['plane_y_xz_m'][2]):
  for q in terrain.common.subtract([r['polygon_xz_m']],[upper[i]['polygon_xz_m']for i in ui.candidates(r['polygon_xz_m'])]):
   if geo.polygon_area(q)>1e-8:ui.add(len(upper),q);upper.append(dict(r,polygon_xz_m=q))
 ext=load(RES/'common_entry_surface_audit.json')['row'];points=ext['polyline_xz_m'];source=ext['external_surface']['triangulated_top_surface'];override=load(R02/'level_terminal_source.json');source=override['triangles']+source
 def sourceheight(q):
  for r in source:
   v=r['vertices_xyz_m'];pol=[[p[0],p[2]]for p in v]
   if geo.point_in_convex_polygon(q,pol,1e-7):return terrain.common.height(terrain.common.plane(v),q)
  for row in proof['retained_base_upward_faces']:
   if geo.point_in_convex_polygon(q,row['polygon_xz_m'],1e-7):return terrain.common.height(row['plane_y_xz_m'],q)
  raise ValueError(('outside_source',q))
 # Shared mitered cross-sections form a single finite top with no duplicate seam.
 dirs=[]
 for a,c in zip(points,points[1:]):
  v=np.subtract(c,a);dirs.append(v/np.linalg.norm(v))
 first=np.array(points[0]);bend=np.array(points[1]);end=np.array(points[2]);l0=float(np.linalg.norm(bend-first));l1=float(np.linalg.norm(end-bend));normal0=np.array([-dirs[0][1],dirs[0][0]]);normal1=np.array([-dirs[1][1],dirs[1][0]]);miter=(normal0+normal1)/(1+float(normal0@normal1));sections=[]
 for seg,(a,d,L)in enumerate([(first,dirs[0],l0),(bend,dirs[1],l1+.5)]):
  ds=sorted(set([0.,L]+[i*.5 for i in range(1,int(L/.5)+1)if i*.5<L]+([l1]if seg==1 else[])))
  for j,s in enumerate(ds):
   if seg==1 and j==0:continue
   n=miter if (seg==0 and j==len(ds)-1)else(normal0 if seg==0 else normal1);sections.append(dict(point=(a+d*s).tolist(),normal=n.tolist(),public_seam=seg==1 and abs(s-l1)<1e-7,initial=seg==0 and j==0))
 us=[-1.2,-.8,-.4,0,.4,.8,1.2];verts=[];fixed={}
 for sec in sections:
  for u in us:
   q=(np.array(sec['point'])+u*np.array(sec['normal'])).tolist();i=len(verts);verts.append(q)
   if sec['initial']:fixed[i]=9.
   if sec['public_seam']:fixed[i]=8.
 tris=[]
 for j in range(len(sections)-1):
  for k in range(len(us)-1):
   a=j*len(us)+k;c=a+len(us);tris.extend([[a,c,c+1],[a,c+1,a+1]])
 target=np.array([sourceheight(q)for q in verts]);fixed.update({i:float(y)for i,y in enumerate(target)if abs(y-8)<1e-8 or abs(y-9)<1e-8});constraints=[];overlaps=[];gradients=[]
 for ti,ids in enumerate(tris):
  xy=np.array([verts[i]for i in ids]);M=np.array([[x,z,1.]for x,z in xy]);inv=np.linalg.inv(M);gx,gz=inv[0,:],inv[1,:];gradients.append((gx,gz))
  for k in range(32):
   a=k*2*math.pi/32;constraints.append((ids,gx*math.cos(a)+gz*math.sin(a),.12*math.cos(math.pi/32)))
  q=xy.tolist()
  for ui_i in ui.candidates(q):
   row=upper[ui_i];cut=geo.convex_intersection(q,row['polygon_xz_m'])
   if geo.polygon_area(cut)<1e-9:continue
   y=row['plane_y_xz_m'][2];overlaps.append(dict(triangle_index=ti,polygon_xz_m=cut,native_y_m=y))
   for v in cut:
    weights=np.array([v[0],v[1],1.])@inv;constraints.append((ids,weights,y));constraints.append((ids,-weights,-y+.15))
 rr=[];cc=[];vv=[];rhs=[];N=len(verts)
 for ids,coeff,lim in constraints:
  ri=len(rhs)
  for i,v in zip(ids,coeff):rr.append(ri);cc.append(i);vv.append(v)
  rhs.append(lim-float(np.dot(coeff,target[ids])))
 for i in range(N):
  for sign in(-1.,1.):ri=len(rhs);rr.extend([ri,ri]);cc.extend([i,N]);vv.extend([sign,-1]);rhs.append(0.)
 objective=np.zeros(N+1);objective[-1]=1;bounds=[(fixed[i]-target[i],fixed[i]-target[i])if i in fixed else(None,None)for i in range(N)]+[(0,None)];res=linprog(objective,A_ub=coo_matrix((vv,(rr,cc)),shape=(len(rhs),N+1)).tocsr(),b_ub=rhs,bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9});print('LP',res.success,res.message,'verts',N,'tris',len(tris),'constraints',len(rhs),flush=True);assert res.success
 ys=target+res.x[:N];proxy=[];domain=[];errors=[];maxgrade=0
 for cut in overlaps:
  ids=tris[cut['triangle_index']];xyz=[[verts[i][0],float(ys[i]),verts[i][1]]for i in ids];pl=terrain.common.plane(xyz);maxgrade=max(maxgrade,math.hypot(*pl[:2]));q=[[x,terrain.common.height(pl,[x,z]),z]for x,z in cut['polygon_xz_m']];diff=[cut['native_y_m']-v[1]for v in q];errors.append(dict(native_y_m=cut['native_y_m'],polygon_xz_m=cut['polygon_xz_m'],minimum_native_above_collision_m=min(diff),maximum_native_above_collision_m=max(diff)));assert min(diff)>-1e-7 and max(diff)<.1500001
  for tri in terrain.fan_upward(q):
   if area3(tri)>1e-11:proxy.append([tri[0],tri[2],tri[1]])
  domain.append(cut['polygon_xz_m'])
 # Use the coarse full corridor prisms for exact native face clipping; top
 # triangles are additionally restricted to actual native ownership above.
 corridor=[]
 for j in range(len(sections)-1):corridor.append([verts[j*7],verts[(j+1)*7],verts[(j+1)*7+6],verts[j*7+6]])
 ci=geo._SpatialIndex(4)
 for i,q in enumerate(corridor):ci.add(i,q)
 retained=[];ledger=[];sourcearea=0.;keptarea=0.;removedarea=0.;external_kept=0
 def owns(q):return any(geo.point_in_convex_polygon(q,upper[i]['polygon_xz_m'],1e-8)for i in ui.candidates(b.rect(q[0]-.0001,q[1]-.0001,q[0]+.0001,q[1]+.0001)))
 for gi,g in enumerate(native['groups']):
  for qi,local in enumerate(g['quads']):
   q=[[v[k]+pose[k]for k in range(3)]for v in local];n=normal(q);A=area3(q);sourcearea+=A;up=n[1]>1e-9;vertical=abs(n[1])<1e-9;mid=np.mean(q,axis=0);nn=np.array([n[0],n[2]]);nn=nn/np.linalg.norm(nn)if np.linalg.norm(nn)>1e-9 else nn;internal=vertical and owns((mid[[0,2]]+nn*.0001).tolist())and owns((mid[[0,2]]-nn*.0001).tolist());pieces=[q];kind='walking_top'if up else'walking_riser'if internal else'preserved_exterior'
   if up or internal:
    px=[[v[0],v[2]]for v in q];box=b.rect(min(v[0]for v in px)-1e-7,min(v[1]for v in px)-1e-7,max(v[0]for v in px)+1e-7,max(v[1]for v in px)+1e-7)
    for ix in ci.candidates(box):
     nxt=[]
     for piece in pieces:
      outside,inside=cutprism(piece,corridor[ix]);nxt+=outside
      if internal and inside:
       low=clip3(inside,lambda v:7.875-v[1])
       if low:nxt.append(low)
     pieces=nxt
   kept=sum(area3(v)for v in pieces);removed=A-kept;assert removed>=-1e-7,(gi,qi,removed);keptarea+=kept;removedarea+=removed
   if kind=='preserved_exterior':external_kept+=1;assert abs(kept-A)<1e-8
   if removed>1e-8:ledger.append(dict(group_index=gi,quad_index=qi,kind=kind,source_quad_xyz_m=q,retained_polygons_xyz_m=pieces,removed_area_m2=removed))
   for piece in pieces:retained+=godot_tris(piece)
 assert abs(sourcearea-keptarea-removedarea)<1e-6
 assert maxgrade<=.12+1e-7
 combined=retained+proxy;mesh=write('geometry/common_collision_world.json',dict(schema='riverstone.finite_native_collision_replacement.v1',triangles=combined,winding='direct Godot clockwise',retained_native_triangles=len(retained),walking_proxy_triangles=len(proxy)))
 contract=dict(schema='riverstone.explicit_stair_collision_contract.v1',id='R8_COMMON_FINITE_CONTINUOUS_WALKING_R03',status='CANDIDATE_AWAITING_ACTUAL_PHYSICS',native_source=p['cache'],native_placement_id=p['id'],logical_collider_id_preserved=p['id'],disable_native_mesh_collider_ids=[p['id']],replacement_world_mesh=mesh,add_triangles_world_xyz_m=combined,retained_native_triangle_count=len(retained),walking_triangle_count=len(proxy),walking_projected_area_m2=sum(geo.polygon_area(q)for q in domain),walking_width_m=2.4,maximum_visual_above_collision_m=max(r['maximum_native_above_collision_m']for r in errors),maximum_collision_above_visual_m=max(0,-min(r['minimum_native_above_collision_m']for r in errors)),max_grade=maxgrade,visual_native_asset_unchanged=True,native_side_guards_end_faces_bottom_and_exterior_preserved=True,removed_native_face_ledger=ledger,fixed_public_interface=ref(R02/'fixed_public_interface_r18.json'),source_profile=ref(R02/'level_terminal_source.json'),approved_pattern=ref(CITY/'traversal_r5/revisions/r06_r8_precinct/stair_proxy_r01/collision_contract.json'),runtime_ready=False,limits=['Exact R02 visible meshes and controller remain unchanged.','Only the fine access walking collision within the 2.4 m corridor is replaced.','Old REGISTERED_LANDSCAPE:SITE_COMMON must be removed by its already-declared native replacement ledger.','Exact constant Y8 R18 terminal retained; onward public-road closure remains parent-owned.'])
 write('collision_contract.json',contract);write('geometry_audit.json',dict(status='FINITE_GEOMETRY_PASS_RUNTIME_PENDING',source_area_m2=sourcearea,retained_area_m2=keptarea,removed_area_m2=removedarea,area_partition_error_m2=sourcearea-keptarea-removedarea,retained_exterior_faces=external_kept,profile_error_by_actual_tread=errors,max_grade=maxgrade,source_target_max_adjustment_m=float(res.x[-1]),native_visual_refs=[dict(id=x['id'],source=x['source'],cache=x['cache'])for x in pack['placements']],fixed_vertex_count=len(fixed),maximum_fixed_error_m=max(abs(ys[i]-y)for i,y in fixed.items()),seconds=time.monotonic()-t));print('done',len(retained),len(proxy),'error',contract['maximum_visual_above_collision_m'],'seconds',time.monotonic()-t,flush=True)
if __name__=='__main__':main()
