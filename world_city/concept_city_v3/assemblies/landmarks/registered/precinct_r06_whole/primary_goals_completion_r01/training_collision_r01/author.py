"""Bounded native tread collision envelope. Exact visible source stays unchanged."""
from pathlib import Path
import sys,json,math,hashlib,importlib.util,copy
O=Path(__file__).resolve().parent;B=O.parents[1];sys.path.insert(0,str(B))
from resolve_pack import *
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
HELP=B/'residual_completion_r01/common_entry_repair_r03/candidate_r02/author_collision.py'
spec=importlib.util.spec_from_file_location('approved_common_envelope',HELP);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
from world_city.concept_city_v3.registered_integration.r8.runtime_precision import zero_mask

def write(n,d):p=O/n;p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');return ref(p)
def canonical(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def tris(q):return[[q[0],q[i+1],q[i]]for i in range(1,len(q)-1)if h.area3([q[0],q[i+1],q[i]])>0]
def main():
 scene_path=CITY/'evidence/r8_final110_runtime_r01/scene.json';scene=load(scene_path);p=next(p for p in scene['common_instances']if p['id']=='TRAIN:r09:fine');a=scene['common_assets'][p['asset_key']];cache=ROOT/a['render_path'];master=ROOT/a['master_path'];mesh=load(cache);source=load(master)['metadata']['source_surface'];assert p['position_m']==[-330,18,-180]and p['yaw_rad']==0 and p['scale']==[1,1,1];assert sha(cache)==a['render_sha256']
 upper=[]
 for gi,g in enumerate(mesh['groups']):
  for qi,q0 in enumerate(g['quads']):
   q=[[v[k]+p['position_m'][k]for k in range(3)]for v in q0]
   if h.normal(q)[1]>0:upper.append(dict(group_index=gi,quad_index=qi,polygon_xz_m=[[v[0],v[2]]for v in q],floor_y_m=q[0][1]))
 # Full unchanged capsule is 0.6 m diameter; the finite 1.2 m strip has 0.3 m margins.
 start=np.array([-270.2670847275223,-151.73174251534238]);direction=np.array([.9998308158271166,-.018394013223931444]);N=np.array([-direction[1],direction[0]]);end_s=(-255.625-start[0])/direction[0]+.02;length=float(end_s);ss=sorted(set([0.,length]+[i*.5 for i in range(1,math.ceil(length/.5))]));us=[-.6,-.3,0.,.3,.6];verts=[(start+direction*s+N*u).tolist()for s in ss for u in us];ids=[]
 for j in range(len(ss)-1):
  for k in range(len(us)-1):
   v=j*len(us)+k;w=v+len(us);ids.extend([[v,w,w+1],[v,w+1,v+1]])
 target=np.array([18+.125*s/length for s in ss for u in us]);fixed={i:18. for i in range(len(us))};fixed.update({len(verts)-len(us)+i:18.125 for i in range(len(us))});constraints=[];overlaps=[]
 for ti,ix in enumerate(ids):
  xy=np.array([verts[i]for i in ix]);inv=np.linalg.inv(np.array([[x,z,1]for x,z in xy]));gx,gz=inv[0,:],inv[1,:]
  for k in range(32):t=k*math.tau/32;constraints.append((ix,gx*math.cos(t)+gz*math.sin(t),.12*math.cos(math.pi/32)))
  for row in upper:
   cut=geo.convex_intersection(xy.tolist(),row['polygon_xz_m'])
   if geo.polygon_area(cut)<=1e-12:continue
   overlaps.append(dict(triangle_index=ti,native_source=row,polygon_xz_m=cut));y=row['floor_y_m']
   for v in cut:
    coeff=np.array([v[0],v[1],1])@inv;constraints.extend([(ix,coeff,y),(ix,-coeff,-y+.15)])
 rr=[];cc=[];vv=[];rhs=[];n=len(verts)
 for ix,co,lim in constraints:
  row=len(rhs)
  for i,v in zip(ix,co):rr.append(row);cc.append(i);vv.append(float(v))
  rhs.append(lim-float(np.dot(co,target[ix])))
 for i in range(n):
  for sign in[-1,1]:row=len(rhs);rr.extend([row,row]);cc.extend([i,n]);vv.extend([sign,-1]);rhs.append(0.)
 objective=np.zeros(n+1);objective[-1]=1;bounds=[(fixed[i]-target[i],fixed[i]-target[i])if i in fixed else(None,None)for i in range(n)]+[(0,None)];sol=linprog(objective,A_ub=coo_matrix((vv,(rr,cc)),shape=(len(rhs),n+1)).tocsr(),b_ub=rhs,bounds=bounds,method='highs');assert sol.success,sol.message;ys=target+sol.x[:n];proxy=[];errors=[];grades=[]
 for row in overlaps:
  ix=ids[row['triangle_index']];pl=terrain.common.plane([[verts[i][0],float(ys[i]),verts[i][1]]for i in ix]);q=[[x,terrain.common.height(pl,[x,z]),z]for x,z in row['polygon_xz_m']];diff=[row['native_source']['floor_y_m']-v[1]for v in q];assert min(diff)>-1e-7 and max(diff)<.1500001;proxy+=tris(q)if h.normal(q)[1]>0 else tris(list(reversed(q)));errors.append(dict(row,minimum_visual_above_collision_m=min(diff),maximum_visual_above_collision_m=max(diff),collision_plane_y_xz_m=pl));grades.append(math.hypot(*pl[:2]))
 corridor=[verts[0],verts[-len(us)],verts[-1],verts[len(us)-1]];retained=[];ledger=[];sourcearea=0.;keptarea=0.;removedarea=0.;negative=[]
 def owns(q):return any(geo.point_in_convex_polygon(q,r['polygon_xz_m'],1e-8)for r in upper)
 for gi,g in enumerate(mesh['groups']):
  for qi,q0 in enumerate(g['quads']):
   q=[[v[k]+p['position_m'][k]for k in range(3)]for v in q0];normal=h.normal(q);A=h.area3(q);up=normal[1]>0;vertical=abs(normal[1])<1e-10;mid=np.mean(q,axis=0);nn=np.array([normal[0],normal[2]]);nn=nn/np.linalg.norm(nn)if np.linalg.norm(nn)>0 else nn;internal=vertical and owns((mid[[0,2]]+nn*.0001).tolist())and owns((mid[[0,2]]-nn*.0001).tolist());pieces=[q];kind='upward_walking'if up else'internal_tread_riser'if internal else'preserved_negative_exterior'
   if up or internal:
    pieces,inside=h.cutprism(q,corridor)
    if internal and inside:
     below=h.clip3(inside,lambda v:17.875-v[1])
     if below:pieces.append(below)
   kept=sum(h.area3(x)for x in pieces);removed=A-kept;sourcearea+=A;keptarea+=kept;removedarea+=removed;assert removed>=-1e-8
   if kind=='preserved_negative_exterior':assert pieces==[q];negative.append(dict(group_index=gi,quad_index=qi,world_quad_sha256=canonical(q),area3_m2=A))
   if removed>1e-9:ledger.append(dict(group_index=gi,quad_index=qi,source_quad_sha256=canonical(q),source_quad_xyz_m=q,kind=kind,retained_polygons_xyz_m=pieces,removed_area3_m2=removed))
   for piece in pieces:retained+=tris(piece)
 assert abs(sourcearea-keptarea-removedarea)<1e-6
 authored=retained+proxy;auth=write('authored_collision_mesh.json',dict(triangles=authored,retained_native_triangles=len(retained),walking_triangles=len(proxy),winding='Godot clockwise'))
 _,q32,cross,zero=zero_mask([v for t in authored for v in t]);kept=[i for i,z in enumerate(zero)if not z];removals=[dict(source_triangle_index=i,source_triangle_sha256=canonical(authored[i]),source_triangle_xyz_m=authored[i],runtime_float32_vertices_xyz_m=q32[i].tolist(),runtime_float32_cross_xyz=cross[i].tolist())for i,z in enumerate(zero)if z];combined=[authored[i]for i in kept];precision=write('exact_precision_ledger.json',dict(source=auth,predicate='Exact runtime_precision.zero_mask only; no area threshold.',retained_source_indices=kept,removals=removals,nonzero_triangles_and_order_unchanged=True));world=write('collision_world.json',dict(triangles=combined,winding='Godot clockwise'))
 audit=write('geometry_audit.json',dict(status='FINITE_SOURCE_PASS_RUNTIME_PENDING',source_scene=ref(scene_path),native_placement=p,native_asset=a,source_surface=source,corridor_polygon_xz_m=corridor,actual_top_source_faces=upper,source_area3_m2=sourcearea,retained_area3_m2=keptarea,removed_area3_m2=removedarea,partition_error_m2=sourcearea-keptarea-removedarea,negative_walls_and_exterior_faces=negative,removed_native_face_ledger=ledger,profile_errors=errors,max_grade=max(grades),maximum_visual_above_collision_m=max(r['maximum_visual_above_collision_m']for r in errors),maximum_collision_above_visual_m=max(0.,-min(r['minimum_visual_above_collision_m']for r in errors)),fixed_inner_y_m=18.,fixed_outer_y_m=18.125,walking_width_m=1.2,unchanged_controller_capsule_diameter_m=.6,source_target_adjustment_m=float(sol.x[-1]),precision=precision))
 contract=dict(schema='riverstone.explicit_stair_collision_contract.v1',id='R8_TRAINING_FINITE_CONTINUOUS_ENTRY_R01',status='CANDIDATE_AWAITING_ACTUAL_PHYSICS',native_source=ref(cache),native_placement_id=p['id'],logical_collider_id_preserved=p['id'],disable_native_mesh_collider_ids=[p['id']],replacement_transform={k:p[k]for k in('position_m','yaw_rad','scale')},replacement_world_mesh=world,add_triangles_world_xyz_m=combined,retained_native_triangle_count=sum(i<len(retained)for i in kept),walking_triangle_count=sum(i>=len(retained)for i in kept),walking_width_m=1.2,max_grade=max(grades),maximum_visual_above_collision_m=max(r['maximum_visual_above_collision_m']for r in errors),maximum_collision_above_visual_m=max(0.,-min(r['minimum_visual_above_collision_m']for r in errors)),visual_native_asset_unchanged=True,native_side_guards_end_faces_bottom_and_exterior_preserved=True,removed_native_face_ledger=ledger,source_profile=ref(master),geometry_audit=audit,precision=precision,approved_pattern=ref(B/'residual_completion_r01/common_entry_repair_r03/candidate_r02/collision_contract.json'),runtime_ready=False,limits=['Only the finite 1.2 m actual native walking strip receives continuous collision. All visible 0.125 m treads, exterior walls and unchanged controller are retained.','Actual same-route bidirectional replay remains required.'])
 cr=write('collision_contract.json',contract);handoff=write('integration_handoff.json',dict(id='R8_TRAINING_FINITE_CONTINUOUS_ENTRY_R01',collision_contract=cr,native_visual_source=ref(master),native_visual_cache=ref(cache),geometry_audit=audit,precision=precision,existing_failed_trace=ref(CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_final_runtime_r01/evidence/training_failure_r01.json'),source_scene=ref(scene_path),runtime_route_id='TRAIN_RETAINED_ENTRY_R01',geometry_changes='collision only; native and terrain unchanged',runtime_ready=False));print(json.dumps(handoff),flush=True);print('triangles',len(combined),'maxgrade',max(grades),'visual embed',contract['maximum_visual_above_collision_m'],'precision removed',len(removals),flush=True)
if __name__=='__main__':main()
