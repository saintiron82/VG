"""Read-only actual district replay using the unchanged traversal_r5 harness."""
import copy,hashlib,importlib.util,json,math,pathlib,sys,collections,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';WATER=CITY/'assemblies/waterworks/registered_water_completion_r01';APP=WATER/'approaches_r02';REPAIR=WATER/'approaches_r03';COMMON=CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/common_entry_repair_r02';SCENE=None;SHA=None;BINDING=None
spec=importlib.util.spec_from_file_location('network_source',H.parent/'network_batch_r01/prepare_batch.py');n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n);b=n.b

def ref(p):return dict(path=str(p.resolve()),sha256=b.sha(p))
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def dedup(points):
 out=[]
 for p in points:
  if not out or math.dist(p,out[-1])>1e-7:out.append(p)
 return out

sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.assemblies.waterworks.registered_water_completion_r01.approaches_r02 import select_profiles as sprofile
def main():
 started=time.monotonic();assert b.sha(SCENE)==SHA,'Integrated scene changed';scene=b.read(SCENE);bridges=b.read(WATER/'crossing_interfaces.json')['crossings'];fields=b.read(APP/'fields.json')['profiles'];handoff=b.read(APP/'public_handoff.json');common=b.read(COMMON/'resolved_placements.json');roadrows={r['id']:r for r in b.read(CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json')['roads']};bybridge={r['id']:r for r in bridges};actual={p['id']:p for p in scene['common_instances']};assert 'REGISTERED_LANDSCAPE:SITE_COMMON'not in actual,'Superseded common instance retained'
 for br in bridges:assert br['placement_id']in actual
 for p in common['placements']:assert p['id']in actual
 for name in['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:(H/name).write_bytes((BASE/name).read_bytes())
 routes=[];groups={};selections=[]
 def pair(ident,points,roads,scope,group,**meta):
  points=dedup(points);assert len(points)>=2;r=b.route(ident,points,roads,scope);r.update(group=group,**meta);routes.append(r);q=copy.deepcopy(r);q.update(id=ident+'_REVERSE',points=list(reversed(points)));routes.append(q)
 def edgepoint(edge,t):return[edge[0][k]+t*(edge[1][k]-edge[0][k])for k in range(3)]
 def native_point(br,x,z):return b.transform([x,0,z],dict(position_m=br['position_m'],yaw_rad=br['yaw_rad']))
 def near_points(br,t):
  p=next(p for p in fields if p['id']==br['id']+':START_APPROACH');result=[]
  for edge in reversed(p['cross_sections_xz_m']):
   xz=[edge[0][k]+t*(edge[1][k]-edge[0][k])for k in(0,1)];result.append([xz[0],br['deck_top_y_m'],xz[1]])
  u,v=result[0],result[1];L=math.hypot(u[0]-v[0],u[2]-v[2]);result.insert(0,[u[0]+.6*(u[0]-v[0])/L,u[1],u[2]+.6*(u[2]-v[2])/L]);return result
 for br in bridges:
  W=br['road_width_m']
  for j,t in enumerate([.6/W,.5,1-.6/W]):
   near=near_points(br,t);native=[edgepoint(e['xyz_m'],t)for e in br['approach_seams']];far=native[-1];u=native[0];L=math.hypot(far[0]-u[0],far[2]-u[2]);far_out=[far[0]+.8*(far[0]-u[0])/L,far[1],far[2]+.8*(far[2]-u[2])/L];ident='CROSSING_'+br['id']+'_LANE_'+str(j);pair(ident,near+native+[far_out],[br['id']],'Full fixed deck and finite near approach at three clear traffic lanes, 0.6m from each authored side at the outer lanes; both directions.',ident,case_class='canal_crossing',bridge_id=br['id'],lane_fraction=t)
  for side in[-1,1]:
   ident='NEGATIVE_RAIL_'+br['id']+'_'+str(side);r=b.route(ident,[native_point(br,0,0),native_point(br,0,side*(W/2+1.))],[br['id']],'Actual native canal bridge rail must block departure from the dry deck.');r.update(group=ident,case_class='bridge_rail_negative',expected_failure='blocked',expected_contact_id=br['placement_id']);routes.append(r)
 def tail(br):
  edge=br['approach_seams'][1]['xyz_m'];c=edgepoint(edge,.5);road=roadrows[br['id']];st=sprofile.station_at(road,[c[0],c[2]]);j,_,_,_=sprofile.section(road,st);return[c]+[[x,br['deck_top_y_m'],z]for x,z in road['polyline_xz_m'][j+1:]]
 mn=bybridge['MARKET_NORTH'];nb=bybridge['NORTH_BACK_LANE'];north=near_points(mn,.5)+[edgepoint(e['xyz_m'],.5)for e in mn['approach_seams']]+tail(mn)+list(reversed(tail(nb)))+[edgepoint(e['xyz_m'],.5)for e in reversed(nb['approach_seams'])]+list(reversed(near_points(nb,.5)));north=b.read(REPAIR/'route_handoff.json')['points_xyz_m'];pair('NORTH_TWO_BRIDGE_INTERIOR_TURN_R03',north,['MARKET_NORTH','NORTH_BACK_LANE'],'One connected local route through both northern decks and the shared +15.6m junction; no onward whole-road-network claim.','NORTH_TWO_BRIDGE_INTERIOR_TURN_R03',case_class='local_crossing_network')
 er=bybridge['EAST_RADIAL'];ew=bybridge['EAST_WALL_SERVICE'];ep=next(p for p in fields if p['id']=='EAST_SHARED_JUNCTION');eend=edgepoint([ep['public_seam_knots_xyz_m'][0],ep['public_seam_knots_xyz_m'][-1]],.5);eaststart=near_points(er,.5)+[edgepoint(e['xyz_m'],.5)for e in er['approach_seams']];east=eaststart+[eend]+[edgepoint(e['xyz_m'],.5)for e in reversed(ew['approach_seams'])]+list(reversed(near_points(ew,.5)));pair('EAST_TWO_BRIDGE_NETWORK',east,['EAST_RADIAL','EAST_WALL_SERVICE'],'Connected local eastern radial and service-wall decks through the shared +2.5m turning apron.','EAST_TWO_BRIDGE_NETWORK',case_class='local_crossing_network');pair('EAST_RADIAL_TO_PUBLIC_TAIL',eaststart+[eend],['EAST_RADIAL','EAST_WALL_SERVICE'],'Radial deck and shared junction to the actual service-road outer terminal.','EAST_RADIAL_TO_PUBLIC_TAIL',case_class='local_crossing_network')
 # Common entry: source width 2m, three lanes leave 0.2m free beyond the capsule.
 line=common['external_routes'][0]['polyline_xz_m']
 def offset_line(offset):
  normals=[]
  for u,v in zip(line,line[1:]):
   L=math.dist(u,v);normals.append([-(v[1]-u[1])/L,(v[0]-u[0])/L])
  out=[]
  for i,p in enumerate(line):
   if i==0:norm=normals[0]
   elif i==len(line)-1:norm=normals[-1]
   else:
    norm=[normals[i-1][k]+normals[i][k]for k in(0,1)];den=sum(norm[k]*normals[i][k]for k in(0,1));norm=[v/den for v in norm]
   out.append([p[k]+offset*norm[k]for k in(0,1)])
  u,v=out[:2];L=math.dist(u,v);out.insert(0,[u[k]+.6*(u[k]-v[k])/L for k in(0,1)]);u,v=out[-2:];L=math.dist(u,v);out.append([v[k]+.8*(v[k]-u[k])/L for k in(0,1)]);return[[x,9.-i/max(1,len(out)-1),z]for i,(x,z)in enumerate(out)]
 for i,offset in enumerate([-.5,0.,.5]):pair('COMMON_FINE_ENTRY_LANE_'+str(i),offset_line(offset),['WEST_MONASTERY_EDGE','R06_COMMON_FINE_ENTRY_R02'],'Actual retained common base, fine native entrance and +8m public seam, bidirectionally; no interior or cart claim.','COMMON_FINE_ENTRY_LANE_'+str(i),case_class='common_entry',lane_offset_m=offset)
 retained=next(p for p in common['placements']if p['role']=='retained_base');render=b.read(ROOT/retained['cache']['path']);candidates=[]
 for group in render['groups']:
  for q in group['quads']:
   if min(v[1]for v in q)>.01 or max(v[1]for v in q)<.9:continue
   dx=max(v[0]for v in q)-min(v[0]for v in q);dz=max(v[2]for v in q)-min(v[2]for v in q)
   if min(dx,dz)>1e-8 or max(dx,dz)<1.5:continue
   center=[sum(v[k]for v in q)/4 for k in range(3)];center[1]=0.;normal=[(-1 if center[0]>0 else 1),0.]if dx<1e-8 else[0.,(-1 if center[2]>0 else 1)];candidates.append((center,normal,q))
 chosen=[candidates[0],max(candidates,key=lambda r:math.dist(r[0],candidates[0][0]))]
 for i,(c,norm,q)in enumerate(chosen):
  points=[b.transform([c[0]+sign*norm[0],0,c[2]+sign*norm[1]],retained)for sign in[1.,-.8]];ident='NEGATIVE_COMMON_PERIMETER_'+str(i);r=b.route(ident,points,['COMMON_COURT'],'Walk into an actual 1m-high retained native common perimeter wall.');r.update(group=ident,case_class='common_wall_negative',expected_failure='blocked',expected_contact_id=retained['id'],source_wall_quad_local_xyz_m=q);routes.append(r)
 print('ROUTES_READY',len(routes),'crossing',24,'network',6,'common',6,'negative',10,flush=True)
 # Keep complete actual surface triangles in each finite route window. The
 # controller uses the existing City.gd winding conversion a,c,b unchanged.
 allboxes=[box for r in routes for box in n.boxline(r['points'])];globalbox=[min(q[0]for q in allboxes),min(q[1]for q in allboxes),max(q[2]for q in allboxes),max(q[3]for q in allboxes)];triangles=[];index=collections.defaultdict(list)
 for mat,vs in scene['surfaces'].items():
  if mat=='water':continue
  for j in range(0,len(vs),3):
   t=vs[j:j+3];bb=b.bounds(t)
   if not b.overlaps(bb,globalbox):continue
   k=len(triangles);triangles.append((mat,j//3,t,bb))
   for cell in n.cells(bb):index[cell].append(k)
 print('INDEX_READY',len(triangles),flush=True)
 rendercache={};boundcache={};native=[];native_tops={};contracts=scene.get('collision_contracts',[]);disabled={pid for c in contracts for pid in c.get('disable_native_mesh_collider_ids',[])}
 def render(key):
  if key not in rendercache:
   a=scene['common_assets'][key];path=ROOT/a['render_path'];assert b.sha(path)==a['render_sha256'];v=b.read(path);assert not v.get('rigid_parts'),'Unsupported moving native in district '+key;rendercache[key]=v
  return rendercache[key]
 for p in scene['common_instances']:
  a=scene['common_assets'][p['asset_key']];bounds=a.get('bounds')or render(p['asset_key'])['bounds'];bb=b.instance_bounds(p,bounds)
  if b.overlaps(bb,globalbox):native.append((p,bb))
 def native_height(p,x,z):
  pid=p['id']
  if pid not in native_tops:
   ts=[]
   for group in render(p['asset_key'])['groups']:
    for quad in group['quads']:
     v=[b.transform(q,p)for q in quad];aa,cc,dd=v[:3];ny=(cc[2]-aa[2])*(dd[0]-aa[0])-(cc[0]-aa[0])*(dd[2]-aa[2])
     if ny>1e-9:ts.extend([(b.bounds(v),[v[0],v[1],v[2]]),(b.bounds(v),[v[0],v[2],v[3]])])
   native_tops[pid]=ts
  return[y for bb,t in native_tops[pid]if n.covers(bb,x,z)for y in[n.y_at(t,x,z)]if y is not None]
 floor=[]
 def actual_y(point,routeid):
  x,h,z=point;hits=[]
  for i in index.get((math.floor(x/n.CELL),math.floor(z/n.CELL)),[]):
   mat,ti,t,bb=triangles[i]
   if not n.covers(bb,x,z):continue
   # Only upward source faces supply a spawn height hint.
   aa,cc,dd=t;ny=(cc[2]-aa[2])*(dd[0]-aa[0])-(cc[0]-aa[0])*(dd[2]-aa[2])
   if ny<=1e-10:continue
   y=n.y_at(t,x,z)
   if y is not None:hits.append((y,['scene',mat,ti]))
  for p,bb in native:
   if p['id']in disabled or not n.covers(bb,x,z):continue
   hits.extend((y,['native',p['id']])for y in native_height(p,x,z))
  for c in contracts:
   for t in c.get('add_triangles_world_xyz_m',[]):
    y=n.y_at(t,x,z)
    if y is not None:hits.append((y,['contract',c['id']]))
  if hits:y,owner=min(hits,key=lambda v:abs(v[0]-h))
  else:y=h;owner=['UNSUPPORTED_SOURCE_HINT_ONLY']
  floor.append(dict(route_id=routeid,point_xz_m=[x,z],source_hint_y_m=h,actual_selected_y_m=y,owner=owner,candidates=len(hits)))
  return[x,y,z]
 assets={};placements={};buildings={};audits=[]
 for r in routes:groups.setdefault(r['group'],[]).append(r)
 for group,rs in groups.items():
  boxes=[box for r in rs for box in n.boxline(r['points'])];selected=set()
  for box in boxes:
   for cell in n.cells(box):selected.update(index.get(cell,[]))
  selected=[i for i in sorted(selected)if any(b.overlaps(triangles[i][3],box)for box in boxes)];key='SCENE:DISTRICT:'+group;path=H/'geometry'/(group+'.json');write(path,dict(scene_sha256=SHA,source_face_indices=[[triangles[i][0],triangles[i][1]]for i in selected],triangles=[[triangles[i][2][0],triangles[i][2][2],triangles[i][2][1]]for i in selected],whole_triangles_only=True,corridor_boxes_xz_m=boxes));assets[key]=dict(render_path=str(path.relative_to(ROOT)),render_sha256=b.sha(path),collision_format='actual_scene_triangles');placements[key]=dict(id=key,asset_key=key,position_m=[0,0,0],category='actual_district_scene_surface',collision_layer=1);ids=[key];boxids=[]
  for p,bb in native:
   if p['id']in disabled or not any(b.overlaps(bb,box)for box in boxes):continue
   a=scene['common_assets'][p['asset_key']];render(p['asset_key']);assets[p['asset_key']]=dict(render_path=a['render_path'],render_sha256=a['render_sha256']);placements[p['id']]=dict(p,category=p.get('category','actual_native_common_mesh'),collision_layer=3,yaw_deg=math.degrees(p.get('yaw_rad',0)));ids.append(p['id'])
  for c in contracts:
   ts=[t for t in c.get('add_triangles_world_xyz_m',[])if any(b.overlaps(b.bounds(t),box)for box in boxes)]
   if not ts:continue
   key='CONTRACT:'+c['id']+':'+group;path=H/'geometry'/('contract_'+c['id']+'_'+group+'.json');write(path,dict(contract_id=c['id'],triangles=ts,direct_godot_collision_winding=True));assets[key]=dict(render_path=str(path.relative_to(ROOT)),render_sha256=b.sha(path),collision_format='source_grade_proxy_triangles');placements[key]=dict(id=key,asset_key=key,position_m=[0,0,0],category='declared_exact_collision_contract',collision_layer=3);ids.append(key)
  for p in scene.get('boxes',[]):
   bound=dict(min=[-v/2 for v in p['size_m']],max=[v/2 for v in p['size_m']])
   if not any(b.overlaps(b.instance_bounds(p,bound),box)for box in boxes):continue
   buildings[p['id']]=dict(id=p['id'],position_m=p['position_m'],yaw_rad=p.get('yaw_rad',0),boxes=[bound],collision_layer=3);boxids.append(p['id'])
  adjusted=[actual_y(p,group)for p in rs[0]['points']]
  for i,r in enumerate(rs):r.update(points=adjusted if i==0 else list(reversed(adjusted)),placement_ids=ids,building_ids=boxids,minimum_allowed_feet_y_m=min(p[1]for p in adjusted)-1.)
  audits.append(dict(group=group,scene_triangles=len(selected),native_ids=[i for i in ids if not i.startswith(('SCENE:','CONTRACT:'))],contract_ids=[i for i in ids if i.startswith('CONTRACT:')],box_ids=boxids));print('GROUP_READY',group,len(selected),len(ids)-1,flush=True)
 sources={name:ref(path)for name,path in dict(scene=SCENE,integration_binding=BINDING,north_repair_patch=REPAIR/'surface_patch.json',north_repair_route=REPAIR/'route_handoff.json',north_repair_seal=REPAIR/'freeze_manifest.json',common_collision=CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/common_entry_repair_r03/candidate_r02/collision_contract.json',crossing_interfaces=WATER/'crossing_interfaces.json',crossing_pack=WATER/'resolved_placements.json',approach_fields=APP/'fields.json',approach_handoff=APP/'public_handoff.json',approach_freeze=APP/'freeze_manifest.json',common_pack=COMMON/'resolved_placements.json',common_interface=COMMON/'fixed_public_interface_r18.json',common_seal=COMMON/'READY_SEAL.json',original_controller=BASE/'Traversal.gd',common_loader=ROOT/'voxel_character/common/preview/RenderData.gd').items()};implementations={str(path.relative_to(ROOT)):b.sha(path)for path in[H/name for name in['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare.py']]+[BASE/'prepare.py',H.parent/'network_batch_r01/prepare_batch.py',APP/'select_profiles.py',CITY/'registered_topography/revisions/r17_district_batches/side_clearance.py']}
 data=dict(schema='riverstone.actual_district_services_capsule_batch.r03',repo_root=str(ROOT),sources=sources,implementation_hashes=implementations,assets=assets,placements=placements,buildings=buildings,routes=routes,coverage=dict(cases=len(routes),canal_crossing_directions=24,local_network_directions=6,common_entry_directions=6,negative_controls=10,collision_audit=audits),assumptions=['Unchanged traversal_r5 controller, common loader, capsule and strict original acceptance.','Exact composed repaired scene, nearby actual native cache geometry, and all declared finite collision substitutions.','Three lanes across each native canal deck, two local two-deck networks, and three lanes on the common R02 entrance.','Blocked controls use actual native bridge rails and retained common perimeter walls.','Only finite local traversal is tested; no full road-network, cart, interiors, hydraulic or moving-actor claim.'])
 write(H/'prepared_runtime.json',data);write(H/'evidence/floor_selection.json',dict(scene_sha256=SHA,records=floor));write(H/'evidence/preparation.json',dict(prepared=ref(H/'prepared_runtime.json'),cases=len(routes),sources=sources,unsupported_hints=[r for r in floor if r['owner']==['UNSUPPORTED_SOURCE_HINT_ONLY']],collision_audit=audits,seconds=time.monotonic()-started));print('PREPARED',len(routes),'unsupported',sum(r['owner']==['UNSUPPORTED_SOURCE_HINT_ONLY']for r in floor),'seconds',time.monotonic()-started,flush=True)
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--scene',required=True);parser.add_argument('--scene-sha',required=True);parser.add_argument('--binding',required=True);args=parser.parse_args();SCENE=ROOT/args.scene;SHA=args.scene_sha;BINDING=ROOT/args.binding;main()
