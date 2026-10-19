"""Bounded native infill outside retained actual stone/quay floors; common compiler only."""
import pathlib,json,hashlib,sys,math,time,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));from voxel_character.common import coordinate_planes,render_data
from world_city.runtime_city.parts.author import extrusion,box
from world_city.concept_city_v3.assemblies.waterworks.registered_bridge.south_approach_r02 import author as old
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as g
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=sha(p));CITY=ROOT/'world_city/concept_city_v3'
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 pp=H.parent/'side_joins_r01/port_profile_candidate.json';p=read(pp);B=np.asarray(p['native_pose']['basis']);T=np.asarray(p['native_pose']['translation']);prepared=read(CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01/prepared_runtime.json');route=next(q for q in prepared['routes']if q['id']=='ROAD:PORT_BRIDGE_TIE');floors=[];source_refs=[]
 for pid in route['placement_ids']:
  po=prepared['placements'][pid];ass=prepared['assets'][po['asset_key']]
  if ass.get('collision_format'):continue
  path=ROOT/ass['render_path'];assert sha(path)==ass['render_sha256'];native=read(path);yaw=po.get('yaw_rad',0);c,s=math.cos(yaw),math.sin(yaw);NB=np.array([[c,0,s],[0,1,0],[-s,0,c]]);NT=np.array(po['position_m']);source_refs.append(dict(id=pid,pose=po,asset=ass))
  for gi,gg in enumerate(native['groups']):
   for qi,q in enumerate(gg['quads']):
    q=np.asarray(q);n=np.cross(q[1]-q[0],q[2]-q[0]);world=q@NB.T+NT
    if n[1]<=0 or not(1.4<=world[:,1].max()<=2.8):continue
    local=(world-T)@B;poly=[[float(v[0]),float(v[2])]for v in local]
    if not any(a.intersects(a.bounds(poly),a.bounds(d))for d in p['domain_local_xz_m']):continue
    if abs(g.area(poly))<1e-10:continue
    floors.append(dict(instance=pid,group=gi,quad=qi,polygon_local_xz_m=poly,local_quad_xyz_m=local.tolist()))
 floor_polys=[r['polygon_local_xz_m']for r in floors];nominal=g.subtract(p['domain_local_xz_m'],floor_polys);pieces=[]
 for owner in p['owners']:
  for poly in g.subtract([owner['polygon_local_xz_m']],floor_polys):
   if g.area(poly)>1e-9:pieces.append(dict(polygon_local_xz_m=poly,plane_local_y_xz_m=owner['plane_local_y_xz_m'],source_owner_id=owner['id']))
 write(H/'native_infill_plan.json',dict(profile=ref(pp),native_pose=p['native_pose'],nominal_outside_native_polygons=nominal,nominal_infill_area_m2=sum(g.area(q)for q in nominal),source_native_floors=floors,source_native_refs=source_refs,pieces=pieces,limits=['New supported infill only outside retained native floor footprints; no bridge cache, guard, hinge or state geometry is modified.','Quarter-metre support and fine visible cap are source-compiled independently. Fine collision is replaced by exact continuous profile; physical support remains active.']))
 original=read(H.parent/'drawbridge_candidate/masters/stone_approaches.json');assets=[]
 for kind,pitch,guard,topdrop in [('support',.25,.125,.2),('fine',.05,0,0)]:
  name='registered_port_approach_r01_'+kind;m=dict(schema='riverstone.voxel.master.v1',id=name,revision=1,axes=original['axes'],grid_origin=[0,0,0],materials=original['materials'],coordinate_planes=[],components=[],instances=[],constraints=[dict(id='present',kind='nonempty',selector={})],provenance=dict(profile=ref(pp),infill_plan=ref(H/'native_infill_plan.json'),author=ref(H/'build.py'),common_compiler_only=True,pitch_m=pitch,scaling=False,finite_named_road_id='PORT_BRIDGE_TIE'))
  for i,r in enumerate(pieces):
   poly=r['polygon_local_xz_m'];gx,gz,k=r['plane_local_y_xz_m'];grade=math.hypot(gx,gz);u=[gx/grade,gz/grade]if grade>1e-12 else[1,0];v=[-u[1],u[0]];origin=[poly[0][0],a.common.height([gx,gz,k],poly[0]),poly[0][1]];expanded=old.hull([[x+dx,z+dz]for x,z in poly for dx in[-guard,guard]for dz in[-guard,guard]])if guard else poly;ss=[(q[0]-origin[0])*u[0]+(q[1]-origin[2])*u[1]for q in expanded];tt=[(q[0]-origin[0])*v[0]+(q[1]-origin[2])*v[1]for q in expanded];lo,hi=min(ss),max(ss);vl,vh=min(tt),max(tt);hull=old.hull([[origin[0]+s*u[0]+t*v[0],origin[2]+s*u[1]+t*v[1]]for s in[lo,hi]for t in[vl,vh]]);bottom=lambda s:-4.5-origin[1]if kind=='support'else grade*s-.4
   ops=[dict(id='supported_graded_stone',part='solid',action='paint',material='stone',shape=extrusion([[lo,bottom(lo)],[hi,bottom(hi)],[hi,grade*hi-topdrop],[lo,grade*lo-topdrop]],vl,vh),transform=dict(basis=[[u[0],0,v[0]],[0,1,0],[u[1],0,v[1]]],translation=origin))]
   for j,cut in enumerate(old.geo.convex_difference(hull,expanded)):
    if g.area(cut)>1e-10:ops.append(dict(id='finite_clip_'+str(j),part='solid',action='cut',shape=extrusion([[x,-z]for x,z in cut],-5,4),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
   cid='infill_'+str(i);m['components'].append(dict(id=cid,parts=[dict(id='solid',pivot=[0,0,0])],operations=ops));m['instances'].append(dict(id=cid,component=cid))
  mp=H/'sources'/(name+'.json');write(mp,m);start=time.monotonic();co=coordinate_planes.compile_master(m,dict(pitch=pitch),max_candidate_cells=4000000,max_output_cells=1000000);assert co['valid'],co.get('constraints');ren=render_data.make_render_data(co);cp=H/'cache'/(name+'.compiled.json');rp=H/'cache'/(name+'.render.json');write(cp,co);write(rp,ren);r=dict(id=name,source=ref(mp),compiled=ref(cp),cache=ref(rp),pitch_m=pitch,output_cells=len(co['cells']),candidate_cells=co['candidate_cells'],bounds=ren['bounds'],quad_count=ren['quad_count'],seconds=time.monotonic()-start);assets.append(r);print(json.dumps(r),flush=True)
 yaw=math.atan2(B[0,2],B[0,0]);pids=['BRIDGE_MAIN_RIVER:PORT_SUPPORT_APPROACH_R01','BRIDGE_MAIN_RIVER:PORT_VISIBLE_APPROACH_R01'];pack=dict(schema='riverstone.native_port_finite_infill.v1',status='COMPILED_PENDING_OWNERSHIP_AND_ACTUAL_NATIVE_REPLAY',assets=assets,placements=[dict(id=pid,asset_key=r['id'],position_m=T.tolist(),yaw_rad=yaw,scale=[1,1,1],palette_id='native_bridge',palette_override={})for pid,r in zip(pids,assets)],source_refs=[ref(pp),ref(H/'native_infill_plan.json')],replaced_placement_ids=[]);write(H/'resolved_placements.json',pack)
 contract=read(H.parent/'side_joins_r01/port_collision_candidate.json');contract['native_and_ownership_activation_pending']=True;contract['native_pack']=ref(H/'resolved_placements.json');write(H/'collision_contract.json',contract)
if __name__=='__main__':main()
