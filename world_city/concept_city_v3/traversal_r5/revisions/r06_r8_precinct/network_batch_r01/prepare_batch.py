"""Exact finite current-scene road regression batch; unchanged controller/common loader."""
import pathlib,json,hashlib,math,copy,sys,importlib.util,collections,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());C=ROOT/'world_city/concept_city_v3';BASE=C/'traversal_r5';INV=H.parent/'primary_inventory/inventory.json';SCENE=C/'evidence/r8_precinct_bank_r01/scene.json';SHA='4113a70f323b5481a118eb4c70f0511ace0741e14cb9fbfb1b3031843b303769'
spec=importlib.util.spec_from_file_location('b',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
read,sha,ref,write=b.read,b.sha,b.ref,b.write
CELL=16.;PAD=6.
def cells(box):return [(x,z)for x in range(math.floor(box[0]/CELL),math.floor(box[2]/CELL)+1)for z in range(math.floor(box[1]/CELL),math.floor(box[3]/CELL)+1)]
def boxline(points):return [[min(a[0],c[0])-PAD,min(a[2],c[2])-PAD,max(a[0],c[0])+PAD,max(a[2],c[2])+PAD]for a,c in zip(points,points[1:])]
def covers(box,x,z):return box[0]-1e-8<=x<=box[2]+1e-8 and box[1]-1e-8<=z<=box[3]+1e-8
def y_at(t,x,z):
 a,c,d=t;u=c[0]-a[0];v=c[2]-a[2];w=d[0]-a[0];q=d[2]-a[2];det=u*q-v*w
 if abs(det)<1e-10:return None
 s=((x-a[0])*q-(z-a[2])*w)/det;h=(u*(z-a[2])-v*(x-a[0]))/det
 if min(s,h,1-s-h)<-1e-7:return None
 return a[1]+s*(c[1]-a[1])+h*(d[1]-a[1])
def compose(a,c):
 A=a['basis'];B=c['basis'];o=a['translation'];p=c['translation'];return {'basis':[[sum(A[i][k]*B[k][j]for k in range(3))for j in range(3)]for i in range(3)],'translation':[sum(A[i][k]*p[k]for k in range(3))+o[i]for i in range(3)]}
def main():
 assert sha(SCENE)==SHA
 scene=read(SCENE);inventory=read(INV);sources={'scene':ref(SCENE),'inventory':ref(INV),'controller':ref(BASE/'Traversal.gd'),'common_loader':ref(ROOT/'voxel_character/common/preview/RenderData.gd')}
 # Declared stair contract is a separate source, matching the independently tested substitution.
 contract_path=H.parent/'stair_proxy_r01/collision_contract.json';assert sha(contract_path)=='b6649ab28d25707b4c181eeb1c8966f10c9c58b1af5533e3098cac9cc7aeaea9';contracts=scene['collision_contracts']+[read(contract_path)];sources['stair_contract']=ref(contract_path)
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:(H/n).write_bytes((BASE/n).read_bytes())
 (H/'geometry').mkdir(exist_ok=True);(H/'evidence').mkdir(exist_ok=True)
 routes=[];groups={}
 def pair(ident,points,road_ids,scope,group=None,**extra):
  group=group or ident; r=b.route(ident,points,road_ids,scope);r.update(group=group,**extra);routes.append(r);r=copy.deepcopy(r);r.update(id=ident+'_REVERSE',points=list(reversed(points)));routes.append(r)
 for r in inventory['roads']:
  hints=r['source_xyz_hint'];points=[[x,hints[i][1]if hints and len(hints)==len(r['polyline_xz_m'])else 2.5,z]for i,(x,z)in enumerate(r['polyline_xz_m'])]
  pair('ROAD:'+r['id'],points,[r['id']],'Complete source road centreline in both directions; crossings and nearby obstacles use current actual scene.',source_width_m=r['width_m'])
 # Static closed deck and secured barrier checks are distinct from live operation.
 br=scene['bridge_mechanism'];T={'transform':br['bridge_to_world'],'position_m':br['bridge_to_world']['translation']}
 def bw(x,y,z=0):return b.transform([x,y,z],T)
 pair('BRIDGE_CLOSED_LEAF_HINGE',[bw(-11,4.25),bw(-7,4.25),bw(0,4.25),bw(7,4.25),bw(11,4.25)],['MAIN_BRIDGE'],'Exact ROAD_OPEN cached leaves and hinge covers, static pose only.')
 for side in [-1,1]:
  r=b.route('NEGATIVE_BARRIER_CENTER_GAP_'+str(side),[bw(side*15,4.5),bw(side*11,4.5)],['MAIN_BRIDGE'],'ROAD_SECURED actual barrier panels at centre gap; radius0.3 capsule must be blocked.');r.update(group='BARRIER_SECURED',bridge_state='ROAD_SECURED',expected_failure='blocked');routes.append(r)
 for g in inventory['public_gates']:
  road=next(r for r in inventory['roads']if r['id']==g['road_id']);p=g['position_xz_m'];candidates=[]
  for i,(a,c)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   v=[c[j]-a[j]for j in range(2)];t=max(0,min(1,sum((p[j]-a[j])*v[j]for j in range(2))/sum(vv*vv for vv in v)));q=[a[j]+t*v[j]for j in range(2)];candidates.append((math.dist(p,q),i,v))
  _,i,v=min(candidates);length=math.hypot(*v);u=[a/length for a in v]
  pair('GATE:'+g['id'],[[p[0]-4*u[0],2.5,p[1]-4*u[1]],[p[0]+4*u[0],2.5,p[1]+4*u[1]]],[g['road_id']],'Cross exact native public gate centre on actual road, both directions; no invented opening.')
 controls=read(BASE/'revisions/r04_r6_winding/prepared.json')
 for ident in ['NEGATIVE_UNBRIDGED_RIVER','NEGATIVE_ACTUAL_SOLID_WALL']:
  r=copy.deepcopy(next(r for r in controls['routes']if r['id']==ident));r['group']='isolated_control';routes.append(r)
 # Index actual scene triangles once; retain whole triangles, not sampled support planes.
 triangles=[];index=collections.defaultdict(list)
 for mat,vs in scene['surfaces'].items():
  if mat=='water':continue
  for i in range(0,len(vs),3):
   tri=vs[i:i+3];bb=b.bounds(tri);n=len(triangles);triangles.append((mat,i//3,tri,bb))
   for cell in cells(bb):index[cell].append(n)
 print('INDEX_READY',len(triangles),len(index),flush=True)
 native=[];scene_assets=scene['common_assets'];render_cache={};native_tops={};asset_hashes={}
 def render(key):
  if key not in render_cache:
   a=scene_assets[key];p=ROOT/a['render_path'];assert sha(p)==a['render_sha256'];d=read(p);assert not d.get('rigid_parts');render_cache[key]=d;asset_hashes[key]=a['render_sha256']
  return render_cache[key]
 for p in scene['common_instances']:
  a=scene_assets[p['asset_key']];bb=a.get('bounds')or render(p['asset_key'])['bounds'];native.append((p,b.instance_bounds(p,bb)))
 movable={}
 for state in ['ROAD_OPEN','ROAD_SECURED']:
  movable[state]=[]
  for p in br['states'][state]['movable_placements']:
   tr=compose(br['bridge_to_world'],p['transform_bridge_local']);q={'id':'BRIDGE_STATE:'+state+':'+p['id'],'asset_key':p['asset_key'],'transform':tr,'position_m':tr['translation'],'category':'actual_native_bridge_'+state,'collision_layer':3};a=scene_assets[q['asset_key']];movable[state].append((q,b.instance_bounds(q,a['bounds'])))
 disabled={pid for c in contracts for pid in c.get('disable_native_mesh_collider_ids',[])}
 def native_heights(p,x,z):
  pid=p['id']
  if pid not in native_tops:
   out=[]
   for g in render(p['asset_key'])['groups']:
    for q in g['quads']:
     w=[b.transform(v,p)for v in q];a,c,d=w[:3];ny=(c[2]-a[2])*(d[0]-a[0])-(c[0]-a[0])*(d[2]-a[2])
     if ny>1e-9:out.append((b.bounds(w),[w[0],w[1],w[2]]));out.append((b.bounds(w),[w[0],w[2],w[3]]))
   native_tops[pid]=out
  return [y for bb,t in native_tops[pid]if covers(bb,x,z)for y in [y_at(t,x,z)]if y is not None]
 spawn_records=[]
 def actual_height(point,state,routeid):
  x,h,z=point;terrain=[]
  for i in index[(math.floor(x/CELL),math.floor(z/CELL))]:
   mat,ti,t,bb=triangles[i]
   if not covers(bb,x,z):continue
   y=y_at(t,x,z)
   if y is not None:terrain.append((y,mat,ti))
  # Public top ownership is preferred; native tops supply actual finite holes/bridge decks.
  preferred=[q for q in terrain if q[1]in ['road','alley']];pool=preferred or terrain
  hits=[]
  if pool:chosen=min(pool,key=lambda q:abs(q[0]-h));y=chosen[0];owner=['scene',chosen[1],chosen[2]]
  else:
   for p,bb in native+movable[state]:
    if p['id']in disabled or not covers(bb,x,z):continue
    hits.extend((v,p['id'])for v in native_heights(p,x,z))
   for c in contracts:
    for t in c['add_triangles_world_xyz_m']:
     v=y_at(t,x,z)
     if v is not None:hits.append((v,'CONTRACT:'+c['id']))
   if hits:y,owner=min(hits,key=lambda q:abs(q[0]-h))
   else:y=h;owner='UNSUPPORTED_SOURCE_HINT_ONLY'
  return [x,y,z],{'route_id':routeid,'xz_m':[x,z],'source_hint_y_m':h,'actual_selected_y_m':y,'owner':owner,'scene_candidates':len(terrain),'native_candidates':len(hits)}
 assets={};placements={};buildings={};audit=[]
 for r in routes:
  if r['group']!='isolated_control':groups.setdefault(r['group'],[]).append(r)
 for group,rs in groups.items():
  state=rs[0].get('bridge_state','ROAD_OPEN');points=rs[0]['points'];boxes=boxline(points);bb=b.bounds(points);selected=set()
  for box in boxes:
   for cell in cells(box):selected.update(index.get(cell,[]))
  selected=[i for i in sorted(selected)if any(b.overlaps(triangles[i][3],box)for box in boxes)]
  tris=[[triangles[i][2][0],triangles[i][2][2],triangles[i][2][1]]for i in selected];faces=[[triangles[i][0],triangles[i][1]]for i in selected]
  key='SCENE:NETWORK:'+group;path=H/'geometry'/(group.replace(':','_')+'.json');write(path,{'scene_sha256':SHA,'source_face_indices':faces,'triangles':tris,'whole_triangles_only':True,'corridor_boxes_xz_m':boxes});assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_network_scene_surface','collision_layer':1};ids=[key];natives=[];boxids=[]
  for p,pbb in native+movable[state]:
   if p['id']in disabled or not any(b.overlaps(pbb,box)for box in boxes):continue
   a=scene_assets[p['asset_key']];assert sha(ROOT/a['render_path'])==a['render_sha256'];assets[p['asset_key']]={'render_path':a['render_path'],'render_sha256':a['render_sha256']};placements[p['id']]=dict(p,category=p.get('category','actual_native_common_mesh'),collision_layer=3,yaw_deg=math.degrees(p.get('yaw_rad',0)));ids.append(p['id']);natives.append(p['id'])
  for c in contracts:
   ts=[t for t in c['add_triangles_world_xyz_m']if any(b.overlaps(b.bounds(t),box)for box in boxes)]
   if not ts:continue
   key='CONTRACT:'+c['id']+':'+group;path=H/'geometry'/('contract_'+c['id']+'_'+group.replace(':','_')+'.json');write(path,{'contract_id':c['id'],'triangles':ts,'direct_godot_collision_winding':True});assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'source_grade_proxy_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'declared_exact_collision_contract','collision_layer':3};ids.append(key)
  for p in scene['boxes']:
   bound={'min':[-v/2 for v in p['size_m']],'max':[v/2 for v in p['size_m']]}
   if not any(b.overlaps(b.instance_bounds(p,bound),box)for box in boxes):continue
   buildings[p['id']]={'id':p['id'],'position_m':p['position_m'],'yaw_rad':p.get('yaw_rad',0),'boxes':[bound],'collision_layer':3};boxids.append(p['id'])
  adjusted=[]
  for point in points:
   q,rec=actual_height(point,state,group);adjusted.append(q);spawn_records.append(rec)
  for i,r in enumerate(rs):
   r.update(points=adjusted if i==0 else list(reversed(adjusted)),placement_ids=ids,building_ids=boxids,minimum_allowed_feet_y_m=min(q[1]for q in adjusted)-2,bridge_state=state)
  audit.append({'group':group,'scene_triangles':len(tris),'native_ids':natives,'box_ids':boxids,'state':state})
  print('GROUP_READY',group,len(tris),len(natives),flush=True)
 for r in routes:
  if r['group']!='isolated_control':continue
  for pid in r['placement_ids']:
   p=controls['placements'][pid];assets[p['asset_key']]=controls['assets'][p['asset_key']];placements[pid]=p
 # Negative barrier expected contact is one of two actual native panels, not an envelope.
 for r in routes:
  if r['id'].startswith('NEGATIVE_BARRIER'):r['expected_contact_prefix']='BRIDGE_STATE:ROAD_SECURED:BARRIER_'
 implementations={str(p.relative_to(ROOT)):sha(p)for p in [H/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare_batch.py']]+[BASE/'prepare.py']}
 data={'schema':'riverstone.actual_primary_network_batch.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':implementations,'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,'coverage':{'cases':len(routes),'road_corridors':42,'public_gate_probes':2,'closed_bridge_and_barrier_static_states':True,'collision_audit':audit,'actual_floor_selection_ledger':str((H/'evidence/floor_selection.json').relative_to(ROOT))},'assumptions':['Exact frozen candidate scene and finite declared stair/southern collision contracts.','All native ROAD_OPEN bridge mechanisms instantiated from exact cached meshes and composed scene transforms; secured barriers tested separately.','Original controller and strict floor/ray acceptance unchanged.','Source XZ vectors preserved; only initial/route height hints are resolved from actual finite triangle planes, never path support infill.','Complete-road individual passes do not alone establish all road-to-road turns, doorways, live actors, carts or final R8 geometry.']}
 write(H/'prepared.json',data);write(H/'evidence/floor_selection.json',{'scene_sha256':SHA,'records':spawn_records});write(H/'evidence/preparation.json',{'prepared':ref(H/'prepared.json'),'cases':len(routes),'assets':len(assets),'placements':len(placements),'groups':audit,'unsupported_height_hint_count':sum(r['owner']=='UNSUPPORTED_SOURCE_HINT_ONLY'for r in spawn_records)});print('PREPARED',len(routes),sha(H/'prepared.json'),flush=True)
if __name__=='__main__':main()
