"""Seven continuous finite walking envelopes over refined visible native treads."""
from pathlib import Path
import sys,json,math,time,importlib.util
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT))
from resolve_pack import *
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from build_ground_patch import faces,upper
OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('common_envelope',OUT.parent/'common_entry_repair_r03/candidate_r02/author_collision.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
normal,area3,clip3,cutprism=helper.normal,helper.area3,helper.clip3,helper.cutprism

def tris(q):return [[q[0],q[i+1],q[i]]for i in range(1,len(q)-1)if float(np.linalg.norm(normal([q[0],q[i+1],q[i]])))>1e-11]
def write(name,obj):p=OUT/name;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
def main():
 started=time.monotonic();pack=load(OUT/'resolved_native_candidate.json');sourcepack=load(ROOT/pack['sources']['original_source_profiles']['path']);contracts=[];audits=[];routes=[];handoff=[]
 for owner in pack['owners']:
  eid=owner['owner_id'];p=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='fine_access');native=load(ROOT/p['cache']['path']);pose=p['position_m'];assert p['yaw_rad']==0;tops=upper(faces(p)[0]);ui=geo._SpatialIndex(4)
  for i,r in enumerate(tops):ui.add(i,r['polygon_xz_m'])
  ext=owner['source_external_profile'];source=ext['triangulated_top_surface'];gate=next(r for r in sourcepack['gate_proposals']if r['property_id']==eid)['gates'][0];ramp=ext['polygon_regions_xz_m'][1];start=np.mean([ramp[0],ramp[-1]],axis=0);seam=np.mean(ext['public_lane_endpoint']['seam_xz_m'],axis=0);direction=(seam-start)/np.linalg.norm(seam-start);end=seam+direction*.6;turn=(np.array(gate['center_xz_m'])+.65*(np.array(gate['outside_point_xz_m'])-np.array(gate['center_xz_m']))).tolist();points=[gate['center_xz_m'],turn,start.tolist(),seam.tolist(),end.tolist()]
  # Remove collinear redundant knots but preserve the public seam index.
  sv=[]
  for r in source:
   v=r['vertices_xyz_m'];sv.append(dict(polygon=[[q[0],q[2]]for q in v],plane=terrain.common.plane(v)))
  def sourceheight(q):
   for r in sv:
    if geo.point_in_convex_polygon(q,r['polygon'],1e-7):return terrain.common.height(r['plane'],q)
   if math.dist(q,gate['center_xz_m'])<3:return ext['finished_gate_floor_y_m']
   # Only native pixel overrun at the terminal may extrapolate the exact
   # adjoining source plane; there is no new visible mesh outside the native.
   candidates=[]
   for r in sv:
    for a,c in zip(r['polygon'],r['polygon'][1:]+r['polygon'][:1]):
     d=np.subtract(c,a);t=max(0,min(1,float(np.dot(np.subtract(q,a),d)/np.dot(d,d))));dist=float(np.linalg.norm(np.subtract(q,np.array(a)+d*t)));candidates.append((dist,r))
   dist,r=min(candidates,key=lambda r:r[0]);assert dist<1.6,(eid,'outside source',q,dist);return terrain.common.height(r['plane'],q)
  dirs=[];lengths=[]
  for a,c in zip(points,points[1:]):d=np.subtract(c,a);L=float(np.linalg.norm(d));dirs.append(d/L);lengths.append(L)
  normals=[np.array([-d[1],d[0]])for d in dirs];sections=[]
  for seg,(a,d,L)in enumerate(zip(points,dirs,lengths)):
   ds=sorted(set([0.,L]+[i*.4 for i in range(1,int(L/.4)+1)if i*.4<L-1e-7]))
   for j,s in enumerate(ds):
    if seg and not j:continue
    n0=normals[seg]if seg==0 else(normals[seg-1]+normals[seg])/(1+float(normals[seg-1]@normals[seg]));n1=normals[seg]if seg==len(dirs)-1 else(normals[seg]+normals[seg+1])/(1+float(normals[seg]@normals[seg+1]));n=n0*(1-s/L)+n1*(s/L)
    sections.append(dict(point=(np.array(a)+d*s).tolist(),normal=n.tolist(),initial=seg==0 and j==0,public_seam=seg==2 and j==len(ds)-1,outer=seg==len(dirs)-1 and j==len(ds)-1))
  us=[-1.7,-1.5,-.5,0,.5,1.5,1.7];verts=[];fixed={}
  for sec in sections:
   for u in us:
    q=(np.array(sec['point'])+u*np.array(sec['normal'])).tolist();i=len(verts);verts.append(q)
    if sec['initial']:fixed[i]=ext['finished_gate_floor_y_m']
    if sec['public_seam']or sec['outer']:fixed[i]=sourceheight(q)
  idslist=[]
  for j in range(len(sections)-1):
   for k in range(6):a=j*7+k;c=a+7;idslist.extend([[a,c,c+1],[a,c+1,a+1]])
  target=np.array([sourceheight(q)for q in verts]);fixed.update({i:float(y)for i,y in enumerate(target)if abs(y-ext['finished_gate_floor_y_m'])<1e-8});constraints=[];overlaps=[]
  for ti,ids in enumerate(idslist):
   xy=np.array([verts[i]for i in ids]);inv=np.linalg.inv(np.array([[x,z,1.]for x,z in xy]));gx,gz=inv[0,:],inv[1,:]
   for k in range(32):ang=k*2*math.pi/32;constraints.append((ids,gx*math.cos(ang)+gz*math.sin(ang),.12*math.cos(math.pi/32)))
   for j in ui.candidates(xy.tolist()):
    row=tops[j];q=geo.convex_intersection(xy.tolist(),row['polygon_xz_m'])
    if geo.polygon_area(q)<1e-9:continue
    y=row['plane_y_xz_m'][2];overlaps.append(dict(triangle_index=ti,polygon_xz_m=q,native_y_m=y))
    for v in q:
     w=np.array([v[0],v[1],1.])@inv;constraints.append((ids,w,y+.075));constraints.append((ids,-w,-y+.15))
  rr=[];cc=[];vv=[];rhs=[];N=len(verts)
  for ids,coeff,limit in constraints:
   ri=len(rhs)
   for i,v in zip(ids,coeff):rr.append(ri);cc.append(i);vv.append(v)
   rhs.append(limit-float(np.dot(coeff,target[ids])))
  for i in range(N):
   for sign in(-1.,1.):ri=len(rhs);rr.extend([ri,ri]);cc.extend([i,N]);vv.extend([sign,-1]);rhs.append(0.)
  objective=np.zeros(N+1);objective[-1]=1;bounds=[(fixed[i]-target[i],fixed[i]-target[i])if i in fixed else(None,None)for i in range(N)]+[(0,None)];result=linprog(objective,A_ub=coo_matrix((vv,(rr,cc)),shape=(len(rhs),N+1)).tocsr(),b_ub=rhs,bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9});print(eid,'LP',result.success,N,len(idslist),len(rhs),flush=True)
  if not result.success:
   mismatch=[]
   for ov in overlaps:
    ids=idslist[ov['triangle_index']];pl=terrain.common.plane([[verts[i][0],float(target[i]),verts[i][1]]for i in ids]);ds=[ov['native_y_m']-terrain.common.height(pl,q)for q in ov['polygon_xz_m']];mismatch.append(dict(**ov,min_diff=min(ds),max_diff=max(ds)))
   write('FAILED_'+eid+'.json',dict(message=result.message,points=points,source_native_mismatch=sorted(mismatch,key=lambda r:r['min_diff'])));raise RuntimeError((eid,result.message))
  ys=target+result.x[:N];proxy=[];errors=[];physical=[];maxgrade=0.
  for ov in overlaps:
   ids=idslist[ov['triangle_index']];xyz=[[verts[i][0],float(ys[i]),verts[i][1]]for i in ids];pl=terrain.common.plane(xyz);maxgrade=max(maxgrade,math.hypot(*pl[:2]));q=[[x,terrain.common.height(pl,[x,z]),z]for x,z in ov['polygon_xz_m']];diff=[ov['native_y_m']-v[1]for v in q];assert min(diff)>-.0750001 and max(diff)<.1500001;errors.append(dict(**ov,minimum_native_above_collision_m=min(diff),maximum_native_above_collision_m=max(diff)));physical.append(dict(polygon_xz_m=ov['polygon_xz_m'],plane_y_xz_m=pl));proxy += [[t[0],t[2],t[1]]for t in terrain.fan_upward(q)if float(np.linalg.norm(normal(t)))>1e-11]
  walking_index=geo._SpatialIndex(4);walking_planes=[]
  for ti,ids in enumerate(idslist):
   q=[verts[i]for i in ids];walking_index.add(ti,q);walking_planes.append(terrain.common.plane([[verts[i][0],float(ys[i]),verts[i][1]]for i in ids]))
  caprow=next((r for r in load(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json')['records']if r['property_id']==eid),None);public_start=min([-2.]+[float((np.array(v)-seam)@direction)-.15 for c in caprow['candidate_columns']for v in c['polygon_xz_m']]if caprow else[-2.]);portal=b.ribbon([(seam+direction*public_start).tolist(),(seam+direction*.85).tolist()],3.4)[0];portal_trim=[]
  corridor=[[verts[j*7],verts[(j+1)*7],verts[(j+1)*7+6],verts[j*7+6]]for j in range(len(sections)-1)];ci=geo._SpatialIndex(4)
  for i,q in enumerate(corridor):ci.add(i,q)
  def owns(q):return any(geo.point_in_convex_polygon(q,tops[i]['polygon_xz_m'],1e-8)for i in ui.candidates([q]))
  retained=[];ledger=[];sourcearea=keptarea=removedarea=0.;external_kept=0;low=min(r['plane_y_xz_m'][2]for r in tops)-.125
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
        bottom=clip3(inside,lambda v:low-v[1])
        if bottom:nxt.append(bottom)
      pieces=nxt
    if vertical and not internal:
     # A public walking cap is a source-bound sub-tread discontinuity, not a
     # guard wall. Clip only its tiny collision lip above the continuous field;
     # the entire visible end face and its lower retaining collision remain.
     outside,inside=cutprism(q,portal)
     if inside:
      pieces=outside+[inside];px=[[v[0],v[2]]for v in inside];box=b.rect(min(v[0]for v in px)-1e-7,min(v[1]for v in px)-1e-7,max(v[0]for v in px)+1e-7,max(v[1]for v in px)+1e-7)
      for wi in walking_index.candidates(box):
       nxt=[];pol=[verts[i]for i in idslist[wi]];pl=walking_planes[wi]
       for piece in pieces:
        outside,inner=cutprism(piece,pol);nxt+=outside
        if inner:
         below=clip3(inner,lambda v:terrain.common.height(pl,[v[0],v[2]])-v[1]);above=clip3(inner,lambda v:v[1]-terrain.common.height(pl,[v[0],v[2]]))
         if below:nxt.append(below)
         if above:
          h=max(v[1]-terrain.common.height(pl,[v[0],v[2]])for v in above);assert h<=.1500001,(eid,'cap trim exceeds envelope',h);portal_trim.append(dict(group_index=gi,quad_index=qi,removed_polygon_xyz_m=above,maximum_above_physical_floor_m=h,plane_y_xz_m=pl));kind='public_walking_cap_lip'
       pieces=nxt
    kept=sum(area3(v)for v in pieces);removed=A-kept;assert removed>=-1e-7;keptarea+=kept;removedarea+=removed
    if kind=='preserved_exterior':external_kept+=1;assert abs(kept-A)<1e-8
    if removed>1e-8:ledger.append(dict(group_index=gi,quad_index=qi,kind=kind,source_quad_xyz_m=q,retained_polygons_xyz_m=pieces,removed_area_m2=removed))
    for piece in pieces:retained+=tris(piece)
  assert abs(sourcearea-keptarea-removedarea)<1e-6;assert maxgrade<=.1200001;combined=retained+proxy;mesh=write('geometry/'+eid+'_collision_world.json',dict(schema='riverstone.finite_native_collision_replacement.v1',triangles=combined,winding='direct Godot clockwise',retained_native_triangles=len(retained),walking_proxy_triangles=len(proxy)));physicalref=write('geometry/'+eid+'_physical_top.json',dict(owner_id=eid,top_pieces=physical,corridor_polygons_xz_m=corridor,route_points_xz_m=points))
  contract=dict(schema='riverstone.explicit_stair_collision_contract.v1',id='R8_NOBLE_SEVEN_FINE_WALKING_R01:'+eid,status='CANDIDATE_AWAITING_ACTUAL_PHYSICS',native_source=p['cache'],native_placement_id=p['id'],logical_collider_id_preserved=p['id'],disable_native_mesh_collider_ids=[p['id']],replacement_transform=dict(position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=[1,1,1]),replacement_world_mesh=mesh,add_triangles_world_xyz_m=combined,retained_native_triangle_count=len(retained),walking_triangle_count=len(proxy),walking_projected_area_m2=sum(geo.polygon_area(r['polygon_xz_m'])for r in physical),physical_envelope_band_width_m=3.4,verified_walking_width_m=2,source_clear_width_m=3,maximum_visual_above_collision_m=max(r['maximum_native_above_collision_m']for r in errors),maximum_collision_above_visual_m=max(0,-min(r['minimum_native_above_collision_m']for r in errors)),max_grade=maxgrade,visual_native_asset_unchanged=True,native_side_guards_bottom_and_nonwalking_exterior_preserved=True,visible_native_end_faces_unchanged=True,public_walking_end_cap_collision_lips=portal_trim,removed_native_face_ledger=ledger,physical_top=physicalref,source_profile=pack['sources']['original_source_profiles'],approved_pattern=ref(OUT.parent/'common_entry_repair_r03/candidate_r02/collision_contract.json'),runtime_ready=False)
  cr=write('contracts/'+eid+'_collision_contract.json',contract);contracts.append(dict(owner_id=eid,contract=cr));audits.append(dict(owner_id=eid,source_area_m2=sourcearea,retained_area_m2=keptarea,removed_area_m2=removedarea,area_partition_error_m2=sourcearea-keptarea-removedarea,retained_exterior_faces=external_kept,profile_error_by_actual_tread=errors,public_walking_end_cap_collision_lips=portal_trim,max_grade=maxgrade,source_target_max_adjustment_m=float(result.x[-1]),fixed_vertex_count=len(fixed),maximum_fixed_error_m=max(abs(ys[i]-y)for i,y in fixed.items()),maximum_visual_above_collision_m=contract['maximum_visual_above_collision_m'],maximum_collision_above_visual_m=contract['maximum_collision_above_visual_m']))
  routes.append(dict(owner_id=eid,id='NOBLE_FINE_ENTRY:'+eid,width_m=2,polyline_xz_m=points,physical_top=physicalref,named_public_road_id=ext['public_lane_endpoint']['road_id'],native_fine_id=p['id'],source_public_endpoint=ext['public_lane_endpoint'],public_transition_start_offset_m=public_start,runtime_ready=False));print(eid,'done',len(retained),len(proxy),contract['maximum_visual_above_collision_m'],contract['maximum_collision_above_visual_m'],flush=True)
 write('collision_contracts.json',dict(schema='riverstone.collision_contract_bundle.v1',id='R8_NOBLE_SEVEN_FINE_WALKING_R01',contracts=contracts));write('geometry_audit.json',dict(status='FINITE_SOURCE_GEOMETRY_RUNTIME_PENDING',owners=audits,seconds=time.monotonic()-started));write('runtime_routes.json',dict(routes=routes,baseline_unchanged_controller=True,public_R18_continuation_pending=True));print('all complete',time.monotonic()-started,flush=True)
if __name__=='__main__':main()
