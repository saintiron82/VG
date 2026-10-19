"""Extract only exact final-scene collision inputs for accepted resolved routes."""
import copy,hashlib,importlib.util,json,math,pathlib,sys,collections,time,argparse
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';sys.path.insert(0,str(H));import catalog,emission_revision,private_emission_revision
spec=importlib.util.spec_from_file_location('network_source',H.parent/'network_batch_r01/prepare_batch.py');n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n);b=n.b
SCENE=None;SHA=None;BINDING=None;CATALOG=None

def ref(p):return dict(path=str(p.resolve()),sha256=b.sha(p))
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 started=time.monotonic();assert b.sha(SCENE)==SHA,'Integrated scene changed';scene=b.read(SCENE);doc=b.read(CATALOG);raw=catalog.validate(doc);routes=[];groups={}
 if not scene.get('bridge_mechanism'):raise ValueError('Actual registered bridge mechanism missing')
 actual_by_id={p['id']:p for p in scene['common_instances']};activation_checks=[];field_activation=None;append_activation=None
 field_ref=doc.get('activation_requirements',{}).get('finite_public_field')
 if field_ref:
  field_path=catalog.source(field_ref);field=b.read(field_path)
  def key(t):return tuple(tuple(v)for v in t)
  actual=collections.Counter(key(scene['surfaces']['road'][i:i+3])for i in range(0,len(scene['surfaces']['road']),3))
  required=collections.Counter(key(t)for r in field['records']for t in r['triangles_xyz_m']);missing=required-actual
  field_activation=dict(source=ref(field_path),owner_records=len(field['records']),required_triangle_instances=sum(required.values()),missing_triangle_instances=sum(missing.values()),method='Exact ordered XYZ triangle multiset inclusion in actual composed road surface; no tolerance or retriangulation accepted.')
  if missing:raise ValueError('R18 finite owners not activated verbatim: '+str(field_activation))
  history=doc.get('activation_requirements',{}).get('finite_public_emission_revision')
  if history:
   previous=b.read(catalog.source(history['previous']));review=b.read(catalog.source(history['review']));assert review['candidate']==field_ref;revision=emission_revision.validate(previous,field,review);unaffected=emission_revision.triangles(revision['unchanged']);missing_unaffected=unaffected-actual;retired_still_present=revision['retired_triangles']&actual
   field_activation['bounded_emission_revision']=dict(**revision['summary'],missing_unaffected_original_triangle_instances=sum(missing_unaffected.values()),retired_triangle_instances_still_present=sum(retired_still_present.values()))
   if missing_unaffected or retired_still_present:raise ValueError('R18 old-to-new physical emission mismatch: '+str(field_activation['bounded_emission_revision']))
 append_refs=doc.get('activation_requirements',{}).get('appended_surface_patches',[])
 if append_refs:
  revision_rows=[];retired_private=collections.defaultdict(collections.Counter)
  revisions=doc.get('activation_requirements',{}).get('private_append_revisions',[])
  revised_sources={json.dumps(r['previous'],sort_keys=True) for r in revisions}
  successors={json.dumps(r['previous'],sort_keys=True):r['current']for r in revisions}
  assert len(successors)==len(revisions),'Ambiguous private revision successor'
  for revision_ref in revisions:
   cursor=revision_ref['current'];seen_revision_refs=set()
   while cursor not in append_refs:
    cursor_key=json.dumps(cursor,sort_keys=True);assert cursor_key not in seen_revision_refs,'Cyclic private emission revision';seen_revision_refs.add(cursor_key)
    assert cursor_key in successors,'Private emission chain does not reach a final active patch';cursor=successors[cursor_key]
  for revision_ref in revisions:
   previous_ref=revision_ref['previous'];current_ref=revision_ref['current'];review_ref=revision_ref['review']
   previous=b.read(catalog.source(previous_ref));current=b.read(catalog.source(current_ref));review=b.read(catalog.source(review_ref))
   assert review['source_patch']==previous_ref and review['replacement_patch']==current_ref
   assert current_ref in append_refs or json.dumps(current_ref,sort_keys=True) in revised_sources,'Revision chain does not reach an active append set'
   extras={}
   if revision_ref.get('contract'):
    assert review['contract']==revision_ref['contract'];contract=b.read(catalog.source(revision_ref['contract']));edge=contract['boundary_connection'];assert edge['walking']is False;extras[edge['material']]=edge['triangles_xyz_m']
   proof=private_emission_revision.validate(previous,current,review,extras)
   for mat,counts in proof['retired'].items():retired_private[mat].update(counts)
   revision_rows.append(dict(previous=previous_ref,current=current_ref,review=review_ref,summary=proof['summary']))
  requirements=collections.defaultdict(collections.Counter);patch_rows=[]
  for patch_ref in append_refs:
   patch_path=catalog.source(patch_ref);patch=b.read(patch_path);counts={}
   for mat,vs in patch['appended_surfaces'].items():
    assert mat!='water'and len(vs)%3==0
    requirements[mat].update(tuple(tuple(v)for v in vs[i:i+3])for i in range(0,len(vs),3));counts[mat]=len(vs)//3
   patch_rows.append(dict(source=ref(patch_path),triangle_instances_by_material=counts))
  materials={}
  for mat,required in requirements.items():
   vs=scene['surfaces'][mat];actual=collections.Counter(tuple(tuple(v)for v in vs[i:i+3])for i in range(0,len(vs),3));missing=required-actual
   retired_excess=(actual-required)&retired_private.get(mat,collections.Counter())
   materials[mat]=dict(required_triangle_instances=sum(required.values()),missing_triangle_instances=sum(missing.values()),retired_triangle_instances_still_present=sum(retired_excess.values()))
  append_activation=dict(patches=patch_rows,materials=materials,private_emission_revisions=revision_rows,method='Combined exact ordered XYZ triangle multiset inclusion for declared final private append sets. Any nonwalking predecessor retirement requires an exact immutable old-to-new source-row ledger; every unaffected predecessor triangle remains exact.')
  if any(r['missing_triangle_instances']or r['retired_triangle_instances_still_present']for r in materials.values()):raise ValueError('Released private top fields not activated verbatim: '+str(append_activation))
 for pack_ref in doc.get('activation_requirements',{}).get('native_packs',[]):
  pack_path=catalog.source(pack_ref);pack=b.read(pack_path);missing=[];mismatched=[]
  pack_assets=pack['assets']if isinstance(pack['assets'],dict)else{a['id']:dict(render_sha256=a['cache']['sha256'])for a in pack['assets']}
  for placement in pack['placements']:
   actual=actual_by_id.get(placement['id'])
   if actual is None:missing.append(placement['id']);continue
   if any(actual.get(k,0 if k=='yaw_rad'else [1,1,1]if k=='scale'else None)!=placement.get(k,0 if k=='yaw_rad'else [1,1,1]if k=='scale'else None)for k in['asset_key','position_m','yaw_rad','scale','transform']):mismatched.append(placement['id'])
   key=placement['asset_key'];assert scene['common_assets'][key]['render_sha256']==pack_assets[key]['render_sha256'],'Released native cache mismatch'
  retired=set(pack.get('replaced_placement_ids',[]))|set(pack.get('replacement_ledger',{}).get('existing_native_placements_removed',[]));retained_old=sorted(retired&set(actual_by_id));activation_checks.append(dict(pack=ref(pack_path),missing_ids=missing,mismatched_ids=mismatched,retained_superseded_ids=retained_old))
  if missing or mismatched or retained_old:raise ValueError('Released native pack not activated exactly: '+str(activation_checks[-1]))
 contract_activation=[];scene_contracts={c['id']:c for c in scene.get('collision_contracts',[])}
 for contract_ref in doc.get('activation_requirements',{}).get('collision_contracts',[]):
  path=catalog.source(contract_ref);source_contract=b.read(path);actual=scene_contracts.get(source_contract['id']);keys=['id','disable_native_mesh_collider_ids','add_triangles_world_xyz_m'];matching=actual is not None and all(actual.get(k)==source_contract.get(k)for k in keys);contract_activation.append(dict(source=ref(path),id=source_contract['id'],exact_physical_fields_match=matching))
  if not matching:raise ValueError('Declared native collision contract not activated exactly: '+source_contract['id'])
 if any(r['case_class']=='isolated_control'for r in raw):raise ValueError('Isolated fixture controls remain separate; this extractor accepts actual scene routes only')
 for r in raw:
  route=b.route(r['id'],r['points'],r['source_road_ids'],r['test_scope']);route.update(r);route['minimum_allowed_feet_y_explicit']='minimum_allowed_feet_y_m'in r;routes.append(route)
 for name in['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:(H/name).write_bytes((BASE/name).read_bytes())
 print('ROUTES_READY',len(routes),flush=True)
 # Keep complete actual surface triangles in each finite route window. The
 # controller uses the existing City.gd winding conversion a,c,b unchanged.
 allboxes=[box for r in routes for box in n.boxline(r['points'])];globalbox=[min(q[0]for q in allboxes),min(q[1]for q in allboxes),max(q[2]for q in allboxes),max(q[3]for q in allboxes)];triangles=[];index=collections.defaultdict(list);route_cells={cell for box in allboxes for cell in n.cells(box)}
 for mat,vs in scene['surfaces'].items():
  if mat=='water':continue
  for j in range(0,len(vs),3):
   t=vs[j:j+3];bb=b.bounds(t)
   if not b.overlaps(bb,globalbox)or not any(cell in route_cells for cell in n.cells(bb)):continue
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
 movable={}
 for state in sorted({r.get('bridge_state','ROAD_OPEN')for r in routes}):
  movable[state]=[]
  for p in scene['bridge_mechanism']['states'][state]['movable_placements']:
   tr=n.compose(scene['bridge_mechanism']['bridge_to_world'],p['transform_bridge_local']);q=dict(id='BRIDGE_STATE:'+state+':'+p['id'],asset_key=p['asset_key'],transform=tr,position_m=tr['translation'],category='actual_native_bridge_'+state,collision_layer=3);asset=scene['common_assets'][q['asset_key']];bounds=asset.get('bounds')or render(q['asset_key'])['bounds'];movable[state].append((q,b.instance_bounds(q,bounds)))
 # Exact source-face indexes only accelerate selection. Full source triangles,
 # duplicate face instances and original order are preserved without clipping.
 contract_rows=[];contract_index=collections.defaultdict(list)
 for c in contracts:
  for ti,t in enumerate(c.get('add_triangles_world_xyz_m',[])):
   bb=b.bounds(t)
   if not b.overlaps(bb,globalbox):continue
   i=len(contract_rows);contract_rows.append((c['id'],ti,t,bb))
   for cell in n.cells(bb):contract_index[cell].append(i)
 native_point_index={}
 for state in movable:
  cells=collections.defaultdict(list)
  for p,bb in native+movable[state]:
   if p['id']in disabled:continue
   for cell in n.cells(bb):cells[cell].append((p,bb))
  native_point_index[state]=cells
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
 def actual_y(point,routeid,state):
  x,h,z=point;hits=[]
  for i in index.get((math.floor(x/n.CELL),math.floor(z/n.CELL)),[]):
   mat,ti,t,bb=triangles[i]
   if not n.covers(bb,x,z):continue
   # Only upward source faces supply a spawn height hint.
   aa,cc,dd=t;ny=(cc[2]-aa[2])*(dd[0]-aa[0])-(cc[0]-aa[0])*(dd[2]-aa[2])
   if ny<=1e-10:continue
   y=n.y_at(t,x,z)
   if y is not None:hits.append((y,['scene',mat,ti]))
  cell=(math.floor(x/n.CELL),math.floor(z/n.CELL))
  for p,bb in native_point_index[state].get(cell,[]):
   if not n.covers(bb,x,z):continue
   hits.extend((y,['native',p['id']])for y in native_height(p,x,z))
  for i in contract_index.get(cell,[]):
   cid,ti,t,bb=contract_rows[i]
   if not n.covers(bb,x,z):continue
   y=n.y_at(t,x,z)
   if y is not None:hits.append((y,['contract',cid]))
  if hits:y,owner=min(hits,key=lambda v:abs(v[0]-h))
  else:y=h;owner=['UNSUPPORTED_SOURCE_HINT_ONLY']
  floor.append(dict(route_id=routeid,point_xz_m=[x,z],source_hint_y_m=h,actual_selected_y_m=y,owner=owner,candidates=len(hits)))
  return[x,y,z]
 assets={};placements={};buildings={};audits=[]
 for r in routes:groups.setdefault(r['group'],[]).append(r)
 for group,rs in groups.items():
  boxes=[box for r in rs for box in n.boxline(r['points'])];state=rs[0].get('bridge_state','ROAD_OPEN');assert all(r.get('bridge_state','ROAD_OPEN')==state for r in rs);selected=set()
  for box in boxes:
   for cell in n.cells(box):selected.update(index.get(cell,[]))
  selected=[i for i in sorted(selected)if any(b.overlaps(triangles[i][3],box)for box in boxes)];key='SCENE:PUBLIC_NETWORK:'+group;path=H/'geometry'/(group+'.json');write(path,dict(scene_sha256=SHA,source_face_indices=[[triangles[i][0],triangles[i][1]]for i in selected],triangles=[[triangles[i][2][0],triangles[i][2][2],triangles[i][2][1]]for i in selected],whole_triangles_only=True,corridor_boxes_xz_m=boxes));assets[key]=dict(render_path=str(path.relative_to(ROOT)),render_sha256=b.sha(path),collision_format='actual_scene_triangles');placements[key]=dict(id=key,asset_key=key,position_m=[0,0,0],category='actual_resolved_public_scene_surface',collision_layer=1);ids=[key];boxids=[]
  for p,bb in native+movable[state]:
   if p['id']in disabled or not any(b.overlaps(bb,box)for box in boxes):continue
   a=scene['common_assets'][p['asset_key']];render(p['asset_key']);assets[p['asset_key']]=dict(render_path=a['render_path'],render_sha256=a['render_sha256']);placements[p['id']]=dict(p,category=p.get('category','actual_native_common_mesh'),collision_layer=3,yaw_deg=math.degrees(p.get('yaw_rad',0)));ids.append(p['id'])
  contract_candidates=set()
  for box in boxes:
   for cell in n.cells(box):contract_candidates.update(contract_index.get(cell,[]))
  contract_groups=collections.defaultdict(list)
  for i in sorted(contract_candidates):
   cid,ti,t,bb=contract_rows[i]
   if any(b.overlaps(bb,box)for box in boxes):contract_groups[cid].append(t)
  for c in contracts:
   ts=contract_groups.get(c['id'],[])
   if not ts:continue
   key='CONTRACT:'+c['id']+':'+group;path=H/'geometry'/('contract_'+c['id']+'_'+group+'.json');write(path,dict(contract_id=c['id'],triangles=ts,direct_godot_collision_winding=True));assets[key]=dict(render_path=str(path.relative_to(ROOT)),render_sha256=b.sha(path),collision_format='source_grade_proxy_triangles');placements[key]=dict(id=key,asset_key=key,position_m=[0,0,0],category='declared_exact_collision_contract',collision_layer=3);ids.append(key)
  for p in scene.get('boxes',[]):
   bound=dict(min=[-v/2 for v in p['size_m']],max=[v/2 for v in p['size_m']])
   if not any(b.overlaps(b.instance_bounds(p,bound),box)for box in boxes):continue
   buildings[p['id']]=dict(id=p['id'],position_m=p['position_m'],yaw_rad=p.get('yaw_rad',0),boxes=[bound],collision_layer=3);boxids.append(p['id'])
  adjusted=[actual_y(p,group,state)for p in rs[0]['points']]
  for i,r in enumerate(rs):r.update(points=adjusted if i==0 else list(reversed(adjusted)),placement_ids=ids,building_ids=boxids,minimum_allowed_feet_y_m=r['minimum_allowed_feet_y_m']if r['minimum_allowed_feet_y_explicit']else min(p[1]for p in adjusted)-2.,bridge_state=state)
  audits.append(dict(group=group,scene_triangles=len(selected),native_ids=[i for i in ids if not i.startswith(('SCENE:','CONTRACT:'))],contract_ids=[i for i in ids if i.startswith('CONTRACT:')],box_ids=boxids));print('GROUP_READY',group,len(selected),len(ids)-1,flush=True)
 sources={name:ref(path)for name,path in dict(scene=SCENE,integration_binding=BINDING,resolved_route_catalog=CATALOG,original_controller=BASE/'Traversal.gd',common_loader=ROOT/'voxel_character/common/preview/RenderData.gd').items()}
 for name,row in doc['sources'].items():sources['route_source:'+name]=ref(catalog.source(row))
 for i,row in enumerate(doc.get('activation_requirements',{}).get('private_append_revisions',[])):
  for name,source_ref in row.items():sources['private_emission_revision:'+str(i)+':'+name]=ref(catalog.source(source_ref))
 implementations={str(p.relative_to(ROOT)):b.sha(p)for p in[H/name for name in['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare.py','catalog.py','emission_revision.py','private_emission_revision.py']]+[BASE/'prepare.py',H.parent/'network_batch_r01/prepare_batch.py']}
 snapshots={}
 for original,digest in implementations.items():
  source_path=ROOT/original;target=H/'source_snapshots'/(digest+'_'+source_path.name);target.parent.mkdir(exist_ok=True)
  if not target.exists():target.write_bytes(source_path.read_bytes())
  assert b.sha(target)==digest;snapshots[original]=ref(target)
 unsupported=[r for r in floor if r['owner']==['UNSUPPORTED_SOURCE_HINT_ONLY']];positive_groups={r['group']for r in routes if not r.get('expected_failure')};unsupported_positive=[r for r in unsupported if r['route_id']in positive_groups]
 if unsupported_positive:
  write(H/'evidence/rejected_unsupported_positive_waypoints.json',dict(scene=ref(SCENE),unsupported=unsupported_positive));raise ValueError('Positive route has unsupported actual-scene waypoint; no physics input emitted')
 data=dict(schema='riverstone.actual_resolved_public_network_batch.r18.v1',repo_root=str(ROOT),sources=sources,implementation_hashes=implementations,implementation_snapshots=snapshots,assets=assets,placements=placements,buildings=buildings,routes=routes,coverage=dict(cases=len(routes),case_classes=dict(collections.Counter(r['case_class']for r in routes)),ownership_coverage=doc['coverage'],collision_audit=audits),assumptions=['Unchanged traversal_r5 controller, loader, capsule and strict original acceptance.','Routes come from hash-bound resolved public geometry handoffs; obsolete source axes require explicit supersession.','Collision uses exact actual non-water scene triangles, native caches and poses, and declared scene contracts; no synthesized floor.','Actual static bridge state meshes are composed from the integrated bridge transform and declared native state placements.','Accepted owners are tested separately from held or retired coverage; even individual road passes do not certify all network turns or carts.'])
 write(H/'prepared_runtime.json',data);write(H/'evidence/floor_selection.json',dict(scene_sha256=SHA,records=floor));write(H/'evidence/preparation.json',dict(prepared=ref(H/'prepared_runtime.json'),cases=len(routes),sources=sources,unsupported_hints=unsupported,unsupported_positive_hints=unsupported_positive,collision_audit=audits,activation_checks=activation_checks,finite_public_field_activation=field_activation,appended_surface_activation=append_activation,declared_collision_contract_activation=contract_activation,seconds=time.monotonic()-started));print('PREPARED',len(routes),'unsupported',len(unsupported),'seconds',time.monotonic()-started,flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--scene',required=True);parser.add_argument('--scene-sha',required=True);parser.add_argument('--binding',required=True);parser.add_argument('--routes',required=True);args=parser.parse_args();SCENE=ROOT/args.scene;SHA=args.scene_sha;BINDING=ROOT/args.binding;CATALOG=ROOT/args.routes;main()
