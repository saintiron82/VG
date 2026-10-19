"""Read-only actual district replay using the unchanged traversal_r5 harness."""
import copy,hashlib,importlib.util,json,math,pathlib,sys,collections,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';B15=CITY/'registered_topography/revisions/r17_district_batches/coherent_b15_r02';SCENE=CITY/'evidence/r8_district_r01/scene.json';SHA='da681e001a40fd38d993db6f95ded85d43915acd10f1e4be0d0e68ec521a80d3'
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

def main():
 start=time.monotonic();assert b.sha(SCENE)==SHA,'Integrated scene changed';scene=b.read(SCENE);hand=b.read(B15/'route_handoff.json');fixed=b.read(B15/'fixed_public_seams.json');contract=b.read(B15/'contract.json');packpath=ROOT/contract['native_pack']['path'];assert b.sha(packpath)==contract['native_pack']['sha256'];pack=b.read(packpath);nodes={r['id']:r for r in hand['nodes']};actual={p['id']:p for p in scene['common_instances']};assert len(fixed['roots'])==22
 for p in pack['placements']:
  assert p['id']in actual,'Missing integrated native '+p['id']
  assert actual[p['id']]['position_m']==p['position_m'],'Integrated placement changed '+p['id']
 for name in['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:(H/name).write_bytes((BASE/name).read_bytes())
 routes=[];groups={};selections=[]
 def pair(ident,points,roads,scope,group,**meta):
  points=dedup(points);assert len(points)>=2
  r=b.route(ident,points,roads,scope);r.update(group=group,**meta);routes.append(r);q=copy.deepcopy(r);q.update(id=ident+'_REVERSE',points=list(reversed(points)));routes.append(q)
 for i,root in enumerate(fixed['roots']):
  node=nodes[root['id']];points=dedup(node['polyline_xyz_m']);assert math.dist(points[-1],root['active_endpoint_xyz_m'])<1e-6
  last=points[-1];prev=points[-2];L=math.hypot(last[0]-prev[0],last[2]-prev[2]);ext=[last[0]+.8*(last[0]-prev[0])/L,last[1],last[2]+.8*(last[2]-prev[2])/L];points=points+[ext]
  ident='PUBLIC_ENTRY_'+str(i+1).zfill(2);pair(ident,points,[root['public_road_id'],root['id']],'Authoritative active entry route and its terminal supersession, followed 0.8 m into actual public surface; both directions.',ident,entry_id=root['id'],source_width_m=node['width_m'],public_road_id=root['public_road_id'],case_class='public_entry')
 # One representative native threshold per holding, retaining both floor bands,
 # narrow/wide threshold necks and all 26 court contexts. Pick the longest source
 # court route deterministically to exercise the useful internal access length.
 doors={r['id']:r for r in pack['actual_doors']};byholding=collections.defaultdict(list)
 for r in hand['door_routes']:byholding[r['holding_id']].append(r)
 chosen=[]
 for i,(holding,rs)in enumerate(sorted(byholding.items())):
  r=max(rs,key=lambda v:(v['length_m'],v['id']));chosen.append(r);ident='COURT_DOOR_'+str(i+1).zfill(2);pair(ident,list(reversed(r['polyline_xyz_m'])),[r['id']],'Exact court route to the native threshold lip, stopping before the closed exterior leaf; no interior passage claim.',ident,door_id=r['door_id'],holding_id=holding,threshold_neck_width_m=r['native_door_threshold_neck']['width_m'],case_class='court_to_door');selections.append(dict(case_group=ident,holding_id=holding,door_route_id=r['id'],door_id=r['door_id'],length_m=r['length_m'],floor_y_m=r['floor_y_m'],neck_width_m=r['native_door_threshold_neck']['width_m']))
 # Four real district closed leaves and four neighboring solid facade targets.
 # No isolated wall is substituted for the actual integrated native collider.
 neg=sorted(chosen,key=lambda r:(r['floor_y_m'],r['holding_id']));neg=[neg[0],neg[2],neg[len(neg)//2],neg[-1]]
 for i,r in enumerate(neg):
  door=doors[r['door_id']];out=door['outward_xz'];tan=[-out[1],out[0]];d=door['actual_door_xyz_m'];threshold=r['polyline_xyz_m'][0]
  for kind,offset in [('CLOSED_LEAF',0.),('SOLID_FACADE',1.5)]:
   start=[d[0]+out[0]*1.25+tan[0]*offset,d[1],d[2]+out[1]*1.25+tan[1]*offset];end=[d[0]-out[0]*.8+tan[0]*offset,d[1],d[2]-out[1]*.8+tan[1]*offset];ident='NEGATIVE_'+kind+'_'+str(i+1).zfill(2);rr=b.route(ident,[start,end],[r['id']],'Actual integrated native '+kind.lower()+' must block the unchanged capsule.');rr.update(group=ident,case_class='blocked_native_negative',expected_failure='blocked',expected_contact_id=door['parcel_id'],door_id=door['id']);routes.append(rr)
 print('ROUTES_READY',len(routes),'public',44,'court',len(chosen)*2,'negative',8,flush=True)
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
 sources={name:ref(path)for name,path in dict(scene=SCENE,route_handoff=B15/'route_handoff.json',fixed_public_seams=B15/'fixed_public_seams.json',district_contract=B15/'contract.json',district_freeze=B15/'freeze_manifest.json',native_pack=packpath,original_controller=BASE/'Traversal.gd',common_loader=ROOT/'voxel_character/common/preview/RenderData.gd').items()};implementations={str(path.relative_to(ROOT)):b.sha(path)for path in[H/name for name in['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare.py']]+[BASE/'prepare.py',H.parent/'network_batch_r01/prepare_batch.py']}
 data=dict(schema='riverstone.actual_district_capsule_batch.r01',repo_root=str(ROOT),sources=sources,implementation_hashes=implementations,assets=assets,placements=placements,buildings=buildings,routes=routes,coverage=dict(cases=len(routes),public_entries=22,public_entry_directions=44,court_holdings=len(chosen),court_directions=len(chosen)*2,actual_native_blocked_controls=8,collision_audit=audits),assumptions=['Original traversal_r5 controller, capsule, strict acceptance and common native loader are unchanged.','Whole current scene triangles and exact nearby native caches, with all current declared collision substitutions.','All 22 authoritative active public nodes are tested in both directions with terminal supersessions and a 0.8m public overrun.','One longest representative court-to-closed-door threshold route per holding, both directions; no interior or cart-through-door claim.','Spawn and route Y hints are resolved only from actual finite upward faces. XZ routes remain the sealed handoff except the declared public overruns and negative controls.','This bounded district replay does not certify untested whole-city paths, protected precinct interiors, hydraulic simulation or moving actors.'])
 write(H/'prepared_runtime.json',data);write(H/'evidence/floor_selection.json',dict(scene_sha256=SHA,records=floor));write(H/'evidence/preparation.json',dict(prepared=ref(H/'prepared_runtime.json'),cases=len(routes),sources=sources,door_selection=selections,unsupported_hints=[r for r in floor if r['owner']==['UNSUPPORTED_SOURCE_HINT_ONLY']],collision_audit=audits,seconds=time.monotonic()-start));print('PREPARED',len(routes),'unsupported',sum(r['owner']==['UNSUPPORTED_SOURCE_HINT_ONLY']for r in floor),'seconds',time.monotonic()-start,flush=True)
if __name__=='__main__':main()
