"""Immutable, finite market delivery bay; source geometry and common engine stay unchanged."""
from __future__ import annotations
import json,math,hashlib
from pathlib import Path
import numpy as np
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.registered_integration.r9.market_clusters.author import corridor,ring
H=Path(__file__).resolve().parent;R=H.parents[4];C=R/'world_city/concept_city_v3';M=H.parents[1]/'r9/market_clusters';OUT=H/'candidate_r01'
SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def load(p):return json.loads(p.read_bytes())
def canon(v):return json.dumps(v,separators=(',',':'),allow_nan=False).encode()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(R)),sha256=sha(p))
def write(n,d): (OUT/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def xyz(p,y=4):return [float(p[0]),float(y),float(p[1])]
def bez(a,b,c,d,n=40):return [[float((1-t)**3*a[k]+3*(1-t)**2*t*b[k]+3*(1-t)*t*t*c[k]+t**3*d[k])for k in (0,1)]for t in np.linspace(0,1,n+1)]
def lerp(a,b,n):return [[float(a[k]+tt*(b[k]-a[k]))for k in (0,1)]for tt in np.linspace(0,1,n+1)]
def geometry():
 O=[102.51014920959473,-8.96224445535969];pre=[91.41505784216918,10.75638652919374];A=[103.,0.];B=[110.,3.];L=math.dist(A,B);t=[7/L,3/L];n=[t[1],-t[0]]
 P=[pre[0]+(pre[1]-5)*(O[0]-pre[0])/(pre[1]-O[1]),5.]
 d=[4.5136560353815,2.06543353739945];cross=lambda a,b:a[0]*b[1]-a[1]*b[0]
 radius=-cross([B[k]-O[k]for k in(0,1)],d)/(2*cross(n,d));center=[B[k]+radius*n[k]for k in(0,1)];theta=math.atan2(B[1]-center[1],B[0]-center[0])
 arc=[[center[0]+radius*math.cos(theta-a),center[1]+radius*math.sin(theta-a)]for a in np.linspace(0,math.pi,64)]
 E=arc[-1];J=[105.5,O[1]+(105.5-O[0])*d[1]/d[0]];Q=[99.75,pre[1]-(99.75-pre[0])*(pre[1]-O[1])/(O[0]-pre[0])]
 incoming=bez(P,[97.1,.65],[100.2,-1.2],A);straight=lerp(A,B,32);outgoing=arc
 ret=lerp(E,J,40)+bez(J,[103.2,J[1]-2.3*d[1]/d[0]],[101.2,Q[1]-1.45*(pre[1]-O[1])/(O[0]-pre[0])],Q)[1:]+lerp(Q,P,50)[1:]
 points=incoming+straight[1:]+outgoing[1:]+ret[1:]
 pad=g.road_ribbon([A[0]-.75*n[0],A[1]-.75*n[1]],[B[0]-.75*n[0],B[1]-.75*n[1]],5.5)
 lane=g.road_ribbon(A,B,4);mid=[106.5,1.5];apron=[mid[k]-2.75*n[k]for k in(0,1)]
 hand=[apron,[108,5.5],[110.3,6.8],[114,7]]
 return dict(P=P,A=A,B=B,E=E,O=O,pre=pre,points=points,incoming=incoming,straight=straight,outgoing=outgoing,return_path=ret,pad=pad,lane=lane,mid=mid,apron=apron,hand=hand,radius=radius,turn_center=center)
class Source:
 def __init__(self):
  self.data=load(H/'source_excerpt.json');assert self.data['base_scene']['sha256']==SHA;self.rows=[];self.idx=g._SpatialIndex(4)
  for f in self.data['source_faces']:
   p=[[v[0],v[2]]for v in f['source_triangle_xyz_m']]
   if g.polygon_area(p)<1e-10:continue
   t=f['source_triangle_xyz_m'];plane=np.linalg.solve([[v[0],v[2],1]for v in t],[v[1]for v in t]);r=dict(f,polygon=p,plane=plane.tolist())
   self.idx.add(len(self.rows),p);self.rows.append(r)
 def at(self,x,z):
  rr=[]
  for i in self.idx.candidates([[x,z]]):
   r=self.rows[i]
   if g.point_in_convex_polygon([x,z],r['polygon'],1e-7):
    a,b,c=r['plane'];y=a*x+b*z+c
    if -2<y<8:rr.append((float(y),r))
  assert rr,('unsupported_source',x,z)
  y,r=max(rr,key=lambda v:(v[0],v[1]['material']=='road'))
  return dict(xyz_m=[float(x),y,float(z)],material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],plane_y_ax_bz_c=r['plane'],source_grade=math.hypot(*r['plane'][:2]),coincident_top_source_ids=[str(q['material'])+':'+str(q['triangle_index'])for h,q in rr if abs(h-y)<1e-6])
 def path(self,pts):return [self.at(*p)['xyz_m']for p in pts]
def near(poly,box=(85,-15,130,20)):
 return max(p[0]for p in poly)>=box[0] and min(p[0]for p in poly)<=box[2] and max(p[1]for p in poly)>=box[1] and min(p[1]for p in poly)<=box[3]
def poly_distance(a,b):
 if g.positive_area_overlap(a,b,0):return 0.
 return min([g.point_segment_distance(p,q,r)for p in a for q,r in zip(b,b[1:]+b[:1])]+[g.point_segment_distance(p,q,r)for p in b for q,r in zip(a,a[1:]+a[:1])])
def fan(poly):
 out=[]
 for k in range(1,len(poly)-1):
  t=[xyz(poly[0]),xyz(poly[k]),xyz(poly[k+1])];v=np.array(t);n=np.cross(v[1]-v[0],v[2]-v[0]);
  if abs(n[1])<=1e-10:continue
  if n[1]<0:t=[t[0],t[2],t[1]]
  out.append(t)
 return out
def build():
 assert not OUT.exists(),'Immutable revision exists; author a new revision rather than overwriting.'
 source=Source();z=geometry();ctx=load(M/'source_context.json');market=load(M/'pack.json');layout=load(M/'layout.json');index=C/'registered_integration/r9/integration_r02_camera/index.json';water=H.parent/'public_water/market_low_head_r01'
 refs=[H/'source_excerpt.json',H/'extract_source.py',H/'author.py',index,M/'source_context.json',M/'layout.json',M/'pack.json',M/'runtime_routes.json',H.parent/'services/service_ledger.json',water/'pack.json',water/'surface_patch.json',water/'routes.json']
 for p in load(index)['packs']:assert sha(R/p['path'])==p['sha256'];refs.append(R/p['path'])
 assert load(index)['base_scene_sha256']==SHA
 solids={s['id']:s for s in ctx['solids']}
 for p in market['add_instances']:solids[p['id']]=dict(id=p['id'],polygon=p['footprint_xz_m'],y_min=p['native_bottom_y_m'],y_max=p['native_top_y_m'])
 wp=load(water/'pack.json')
 for p in wp['add_instances']:
  b=wp['common_assets'][p['asset_key']]['bounds'];solids[p['id']]=dict(id=p['id'],polygon=ring(b,p),y_min=p['position_m'][1]+b['min'][1],y_max=p['position_m'][1]+b['max'][1])
 solids=[s for s in solids.values()if near(s['polygon'])and s['y_max']>3.8 and s['y_min']<6.3]
 reserves=[s for s in ctx['reservations']if near(s['polygon'])]
 links=[(s,corridor(s['path_xz_m'],s['width_m']))for s in layout['routes']if near(s['path_xz_m'])]
 assert g.convex_polygon_contains(ctx['site']['polygon_xz_m'],z['pad'],0)
 pad_hits=dict(solids=[s['id']for s in solids if g.positive_area_overlap(z['pad'],s['polygon'],0)],reserves=sorted(set(s['id']for s in reserves if g.positive_area_overlap(z['pad'],s['polygon'],0))),links=[s['id']for s,pp in links if any(g.positive_area_overlap(z['pad'],p,0)for p in pp)])
 assert not any(pad_hits.values()),pad_hits
 # The finish replacement is one convex finite owner, exactly at the retained source Y4.
 edits=[];appended=[];source_area=0.;removed_area=0.;before_after=[]
 for f in source.data['source_faces']:
  if f['material']!='space_civic':continue
  t=f['source_triangle_xyz_m'];p=[[v[0],v[2]]for v in t];cut=g.convex_intersection(p,z['pad'])
  if g.polygon_area(cut)<1e-9:continue
  assert max(abs(v[1]-4)for v in t)<1e-8
  remain=g.convex_difference(p,z['pad'],0);repl=[tt for q in remain for tt in fan(q)];add=fan(cut);appended.extend(v for tt in add for v in tt)
  edits.append(dict(material='space_civic',triangle_index=f['triangle_index'],source_triangle_sha256=f['source_triangle_sha256'],source_triangle_xyz_m=t,replacement_triangles_xyz_m=repl))
  before=g.polygon_area(p);after=sum(abs(np.cross(np.array(tt[1])-tt[0],np.array(tt[2])-tt[0])[1])*.5for tt in repl+add);before_after.append(abs(before-after));source_area+=g.polygon_area(cut)
 assert abs(source_area-g.polygon_area(z['pad']))<1e-7,(source_area,g.polygon_area(z['pad']))
 waterkeys={(e['material'],e['triangle_index'])for e in load(water/'surface_patch.json')['surface_edits']};assert not any((e['material'],e['triangle_index'])in waterkeys for e in edits)
 degenerate=[]
 for tag,tt in [('replacement',tt)for e in edits for tt in e['replacement_triangles_xyz_m']]+[('append',appended[i:i+3])for i in range(0,len(appended),3)]:
  v=np.array(tt,dtype=np.float32);area=np.linalg.norm(np.cross(v[1]-v[0],v[2]-v[0]))*.5
  if area<1e-9:degenerate.append(dict(tag=tag,triangle=tt,float32_area=float(area)))
 assert not degenerate,degenerate
 full_polys=corridor(z['points'],3.5);branch_polys=corridor(z['incoming']+z['straight'][1:]+z['outgoing'][1:],3.5);hand_polys=corridor(z['hand'],1.5)
 hit_solids=sorted(set(s['id']for s in solids if any(g.positive_area_overlap(p,s['polygon'],0)for p in full_polys+hand_polys)));assert not hit_solids,hit_solids
 branch_links=sorted(set(s['id']for s,pp in links if any(g.positive_area_overlap(p,q,0)for p in branch_polys for q in pp)));assert not branch_links,branch_links
 return_link_crossings=sorted(set(s['id']for s,pp in links if any(g.positive_area_overlap(p,q,0)for p in full_polys for q in pp)))
 # Exact cross-sections, wheel supports, and conservative rigid-body footprint samples.
 samples=[];wheel_samples=[];envelope_hits=[];grades=[];max_residual=0.;max_plane_grade=0.;max_y_hint_difference=0.;all_points=source.path(z['points'])
 for i,(a,b)in enumerate(zip(z['points'],z['points'][1:])):
  dx,dz=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dz);tx,tz=dx/L,dz/L;nx,nz=tz,-tx
  for o in [-1.75,-.9,-.75,0,.75,.9,1.75]:
   rec=source.at(a[0]+o*nx,a[1]+o*nz);rec.update(station=i,lateral_m=o);samples.append(rec);max_plane_grade=max(max_plane_grade,rec['source_grade']);max_y_hint_difference=max(max_y_hint_difference,abs(rec['xyz_m'][1]-4))
  heights=[];w=[]
  for lateral,longitudinal in [(-.75,-1.25),(.75,-1.25),(-.75,1.25),(.75,1.25)]:
   q=source.at(a[0]+lateral*nx+longitudinal*tx,a[1]+lateral*nz+longitudinal*tz);heights.append(q['xyz_m'][1]);w.append(q)
  mid=sum(heights)/4;sx=((heights[1]+heights[3])-(heights[0]+heights[2]))/3;sz=((heights[2]+heights[3])-(heights[0]+heights[1]))/5
  residual=max(abs(h-(mid+sx*l+sz*f))for h,(l,f)in zip(heights,[(-.75,-1.25),(.75,-1.25),(-.75,1.25),(.75,1.25)]));max_residual=max(max_residual,residual)
  wheel_samples.append(dict(station=i,points=w,support_plane_residual_m=residual,mean_support_y_m=mid))
  footprint=[[a[0]+l*nx+f*tx,a[1]+l*nz+f*tz]for l,f in [(-1.05,-1.75),(1.05,-1.75),(1.05,1.75),(-1.05,1.75)]]
  hits=[s['id']for s in solids if g.positive_area_overlap(footprint,s['polygon'],0)]
  if hits:envelope_hits.append(dict(station=i,hits=hits))
 assert max_residual<.05,max_residual;assert not envelope_hits,envelope_hits
 for o in [-1.75,-.75,0,.75,1.75]:
  strip=[q for q in samples if q['lateral_m']==o];m=0
  for a,b in zip(strip,strip[1:]):
   ds=math.hypot(b['xyz_m'][0]-a['xyz_m'][0],b['xyz_m'][2]-a['xyz_m'][2]);m=max(m,abs(b['xyz_m'][1]-a['xyz_m'][1])/ds if ds>1e-8 else 0)
  grades.append(dict(lateral_m=o,maximum_sampled_longitudinal_grade=m))
 # Verify every edge of the finish owner shares the retained source height, without a bank or extra floor.
 edges=[]
 for i,(a,b)in enumerate(zip(z['pad'],z['pad'][1:]+z['pad'][:1])):
  for t in np.linspace(0,1,101):
   x=a[0]+t*(b[0]-a[0]);zz=a[1]+t*(b[1]-a[1]);r=source.at(x,zz);edges.append(dict(edge=i,point=r['xyz_m'],delta_y_m=r['xyz_m'][1]-4))
 assert max(abs(s['delta_y_m'])for s in edges)<1e-7
 source_floor=[source.at(*p)for p in z['pad']+[z['mid']]]
 route_common=dict(group='MARKET_DELIVERY',source_road_ids=['ROAD:MARKET_PROCESSION','ROAD:MARKET_EAST_EDGE'],clear_width_m=3.5,width_m=3.5,bidirectional=True,cart_test=True,test_scope='Exact source-supported local service circuit including off-road bay, one swept turn and existing road return. Rigid kinematic fixture only; not steering, traction, vehicle dynamics, crowd or throughput simulation.',public_target_id='ROAD:MARKET_PROCESSION:LAST_SEGMENT',supported_terminal_id='R10_MARKET_DELIVERY_BAY',native_entrance_ids=[],route_floor_policy='Every XYZ Y is queried from the topmost exact original source face, never inherited road metadata Y4.')
 routes=[dict(route_common,id='R10_MARKET_DELIVERY:DELIVER_AND_RETURN',points=all_points,points_xyz_m=all_points,length_m=sum(math.dist(a,b)for a,b in zip(all_points,all_points[1:])),operational_flow='one-way intended clockwise local service circuit; both directions requested only for bounded clearance verification'),dict(route_common,id='R10_MARKET_DELIVERY:UNLOAD_STOP_LANE',points=source.path([z['A'],z['B']]),points_xyz_m=source.path([z['A'],z['B']]),clear_width_m=4,width_m=4,length_m=math.dist(z['A'],z['B'])),dict(route_common,id='R10_MARKET_DELIVERY:HANDCARRY_TO_ORCHARD_REAR',points=source.path(z['hand']),points_xyz_m=source.path(z['hand']),clear_width_m=1.5,width_m=1.5,cart_test=False,test_scope='Pedestrian hand-carry connection from the bay apron to the retained 3m rear service link.',source_road_ids=['ROAD:MARKET_PROCESSION','R9_CLUSTER_PRODUCE_EAST:00L:SERVICE'],supported_terminal_id='R9_CLUSTER_PRODUCE_EAST:00L:SERVICE:W002')]
 fixture=load(H.parent/'network/port_full_chain/request.json')['cart_fixture']
 summary=dict(status='SOURCE_STATIC_PASS_RUNTIME_AND_RENDER_PENDING',pad_area_m2=g.polygon_area(z['pad']),bay_length_m=math.dist(z['A'],z['B']),lane_clear_width_m=4,unloading_apron_width_m=1.5,entry_turn_lane_clear_width_m=3.5,turn_centerline_radius_m=z['radius'],full_circuit_length_m=routes[0]['length_m'],simultaneous_cart_capacity=1,fixture=fixture,source_faces_edited=len(edits),source_road_faces_edited=0,added_native_instances=0,removed_native_instances=0,changed_native_instances=0,new_native_assets=0,source_floor_heights_changed=False,maximum_source_plane_grade=max_plane_grade,cross_section_grade_samples=grades,maximum_four_wheel_plane_residual_m=max_residual,maximum_source_vs_road_metadata_y_difference_m=max_y_hint_difference,maximum_pad_outer_edge_height_delta_m=max(abs(s['delta_y_m'])for s in edges),pad_hits=pad_hits,cart_envelope_native_bound_hits=envelope_hits,off_road_branch_existing_market_link_conflicts=branch_links,existing_return_road_shared_service_crossings=return_link_crossings,walk_priority='Existing service link remains unchanged. Returning carts use the already-shared public road and must yield at its existing service entrance; no automated yielding behavior is implemented.',float32_degenerate_triangles=0,maximum_original_face_area_balance_error_m2=max(before_after),patch_source_overlap_with_market_low_water=0)
 OUT.mkdir()
 patch=dict(schema='riverstone.frozen_scene.local_surface_patch.v1',id='R10_MARKET_DELIVERY_BAY_R01',base_scene_sha256=SHA,source_surface_hashes={'space_civic':source.data['source_surface_hashes']['space_civic']},surface_edits=edits,appended_surfaces={'ground_stone':appended},removed_foundation_proxy_ids=[],ownership=[dict(id='R10_MARKET_DELIVERY_BAY',kind='single_cart_delivery_hardstand',polygon_xz_m=z['pad'],floor_y_m=4,source_owner='SITE_MARKET',height_policy='Single flush replacement owner at existing Y4. No overlay collider, raised pad, bank, grading or modified road face.')],summary=dict(pad_area_m2=summary['pad_area_m2'],source_triangles_edited=len(edits),road_triangles_edited=0,source_heights_changed=False,appended_triangles=len(appended)//3,source_assets_changed=False))
 write('surface_patch.json',patch)
 write('routes.json',dict(schema='riverstone.r10.market_delivery.routes.v1',base_scene_sha256=SHA,status='NOT_REPLAYED',routes=routes,cart_fixture=fixture,exact_joins=dict(procession_entry=source.path([z['P']])[0],east_edge_exit=source.path([z['E']])[0],old_port_chain_terminal_preserved=source.path([z['O']])[0],last_port_chain_segment=source.path([z['pre'],z['O']]),integration='Split the last incoming port-chain segment at procession_entry, insert DELIVER_AND_RETURN, then return southwest along the original port route. Keep historical endpoint/493 definitions unchanged; do not append a reverse-starting branch at the old terminal.')))
 write('geometry_ownership.json',dict(schema='riverstone.r10.market_delivery.ownership.v1',geometry=z,bay_stop_xyz_m=xyz(z['mid']),bay_stop_clearances=dict(front_rear_m=(math.dist(z['A'],z['B'])-3.2)/2,each_lane_side_m=(4-1.8)/2,additional_unloading_apron_m=1.5),floor_support=source_floor,source_owner='SITE_MARKET',source_polygon=ctx['site']['polygon_xz_m'],source_patch=ref(OUT/'surface_patch.json'),reversal='Drop this candidate patch and pack; no source scene, native asset, road contract, or controller was overwritten.',scope='One cart unloads or briefly waits off the through road. No simultaneous queue/second stall, modern parking marks, logistics throughput or automatic driving is claimed.'))
 write('static_audit.json',summary)
 write('source_grade_samples.json',dict(base_scene_sha256=SHA,cross_section_samples=samples,four_wheel_samples=wheel_samples,pad_outer_edge_closure_samples=edges,road_metadata_y_m=4,route_y_correction_policy='Store exact source-supported height at each waypoint; support rays retain their original +0.75/−1.5m extent.'))
 write('pack.json',dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=SHA,common_assets={},add_instances=[],remove_instance_ids=[],replace_instances=[],inspection_cameras={'r10_market_delivery_overview':dict(position_m=[108,30,25],target_m=[105,4,0],ortho_size_m=40,render_size_px=[1536,1024]),'r10_market_delivery_eye':dict(position_m=[107,6.2,11],target_m=[108,4.4,1],fov_deg=60,render_size_px=[1536,1024])},local_surface_patch=ref(OUT/'surface_patch.json'),status='CANDIDATE_RENDER_AND_RUNTIME_PENDING',common_module_policy='No new native prop is needed. All existing common masters/render caches and every native instance remain untouched. The finite hardstand reuses the existing ground_stone terrain material and unchanged common renderer.',integration_requirements=['Apply this source-index finite patch once in a fresh merged composition. A visual index alone does not apply its surface edit.','Load routes.json explicitly for geometric tests; these sidecar routes do not create NPC/vehicle behavior.','Keep native fixed drawbridge and road collision contracts byte-identical.']))
 refs+= [OUT/p for p in ['surface_patch.json','routes.json','geometry_ownership.json','static_audit.json','source_grade_samples.json','pack.json']]
 write('freeze_manifest.json',dict(schema='riverstone.immutable_candidate_manifest.v1',base_scene_sha256=SHA,files=[ref(p)for p in dict.fromkeys(refs)],status='FROZEN_CANDIDATE_NOT_RUNTIME_APPROVAL',source_original_scene_changed=False))
 print(json.dumps(summary,indent=2))
if __name__=='__main__':build()
