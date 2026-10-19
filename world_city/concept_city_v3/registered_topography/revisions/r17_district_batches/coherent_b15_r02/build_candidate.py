"""Build the whole coherent B15 district as one bounded original-index patch."""
import json,time,math,collections
from .. import author as a,public_tails
from .source_preflight import HERE,FABRIC,read,write
from . import compose_cluster
from ..coherent_b15_r01.effective_routes import trim_before

def run():
 t=time.monotonic();scene=a.load_scene();layout=read('selected_layout.json');hand=read('terrain_handoff.json');plan=json.loads(a.PLAN_PATH.read_bytes());screen=json.loads((HERE/'public_root_screen.json').read_bytes());moves=json.loads((HERE/'terminal_reservations_r02.json').read_bytes());solves=json.loads((HERE/'terminal_profiles_r03.json').read_bytes());profiles=[r['profile']for r in solves['results']];flatmoves=[r['chosen']for r in moves['roots']if r['chosen']]; extra=json.loads((HERE/'terminal_reservations_r04.json').read_bytes()); extraids={r['source_node_id']for r in extra['roots']};flatmoves=[r for r in flatmoves if r['source_node_id']not in extraids]+[r['chosen']for r in extra['roots']];changes={r['source_node_id']:r for r in profiles+flatmoves}
 addendum_path=FABRIC.parent/'backbone_dryside_addendum_r01.json';addendum=json.loads(addendum_path.read_bytes())
 if a.sha(addendum_path)!='3b388ada429881a70daabe405df0b643ebd210a348f8d5d6131e4d1f40862d45' or a.sha(FABRIC/'selected_layout.json')!=addendum['source_layout']['sha256']:raise ValueError('Changed dry-side addendum')
 replacement=addendum['replacement_route']
 for parcel in hand['parcels']:
  if parcel['id']==replacement['id']:parcel['walk_polygons_xz_m']=replacement['polygons_xz_m'];parcel['route']=replacement
 for k,r in enumerate(layout['shared_private_routes']):
  if r['id']==replacement['id']:layout['shared_private_routes'][k]=replacement
 if any(p is None for p in profiles):raise ValueError('Held public profiles')
 traffic=[];ti=a.geo._SpatialIndex(16)
 for r in plan['roads']:
  for p in [a.geo.road_ribbon(u,v,r['width_m'])for u,v in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]+[public_tails.circle(q,r['width_m']/2)for q in r['polyline_xz_m'][1:-1]]:
   ti.add(len(traffic),p);traffic.append(p)
 owners=[];logical=[]
 def add(id,p,kind,material='ground_earth',floor=None,plane=None,action='field',public=False):
  p=a.common.clean(p)
  if not p:return
  ps=[p]if public or action=='hole'else a.common.subtract([p],[traffic[j]for j in ti.candidates(p)])
  for k,q in enumerate(ps):
   o=dict(id=id+':'+str(k),polygon_xz_m=q,action=action,kind=kind)
   if action!='hole':o.update(material=material,plane_y_xz_m=plane if plane is not None else[0,0,floor]);logical.append(o)
   owners.append(o)
 for parcel in hand['parcels']:
  for j,p in enumerate(parcel['footing_polygons_xz_m']):add(parcel['id']+':NATIVE:'+str(j),p,'native_footing',action='hole')
 for p in profiles:
  for j,tr in enumerate(p['triangles']):add(p['id']+':TRI:'+str(j),tr['polygon_xz_m'],'shared_public_profile','ground_stone',plane=tr['plane_y_xz_m'],public=True)
 # Fields overlap only through explicit precedence. Public strips retain their
 # actual source triangles, apart from the two declared profile collars.
 for r in flatmoves:add(r['id'],r['polygon_xz_m'],'moved_level_public_entry','ground_stone',floor=r['floor_y_m'],public=True)
 for r in screen['roots']:
  if r['status']=='FIXED_LEVEL_PUBLIC_SEAM'and r['node_id']not in changes:
   for j,p in enumerate(r['extension_polygons_xz_m']):add(r['node_id']+':TAIL:'+str(j),p,'level_public_tail','ground_stone',floor=r['proposed_floor_y_m'])
 for parcel in hand['parcels']:
  for j,p in enumerate(parcel['walk_polygons_xz_m']):
   ch=changes.get(parcel['id'])or changes.get(parcel['id']+':GATE_LINK')
   if ch:
    kept=trim_before(p,ch['private_start_edge_xz_m'],ch['source_terminal_polyline_xz_m'][0]);ps=[kept]if kept else[]
    for k,q in enumerate(a.common.subtract([p],ps)):add(parcel['id']+':RETIRED_TERMINAL:'+str(j)+':'+str(k),q,'retired_terminal_verge','ground_earth',floor=parcel['floor_y_m'])
   else:ps=[p]
   for k,q in enumerate(ps):add(parcel['id']+':WALK:'+str(j)+':'+str(k),q,'active_walking','ground_stone',floor=parcel['floor_y_m'])
  for j,p in enumerate(parcel['court_polygons_xz_m']):add(parcel['id']+':COURT:'+str(j),p,'functional_court','ground_earth',floor=parcel['floor_y_m'])
  for j,p in enumerate(parcel['whole_holding_polygons_xz_m']):add(parcel['id']+':GROUND:'+str(j),p,'coherent_holding','ground_earth',floor=parcel['floor_y_m'])
 # Restore every retired native body atomically. Existing old private floors are
 # kept outside the coherent union, with explicit nonwalking closure below.
 active={r['id']:r for r in scene['common_instances']};boxes={r['id']:r for r in scene['boxes']};records=[]
 for r in layout['retirement_records']:
  sid=r['source_id'];bid=sid+':owned_foundation'
  if sid not in active or bid not in boxes:raise ValueError('Missing retired owner '+sid)
  if a.canonical_sha(active[sid])!=a.canonical_sha(r['source_instance']):raise ValueError('Changed retired pose '+sid)
  add(sid+':RETIRED_BODY',r['old_terrain_body_hole_polygon_xz_m'],'retired_private_floor_restoration',floor=r['existing_finished_floor_y_m'],public=True)
  records.append(dict(source_id=sid,removed_foundation_proxy_id=bid,retired_source_path_ids=[p['id']for p in r['old_source_paths']],retired_actual_door_ids=[p['id']for p in r['actual_old_access_records']],old_finished_floor_y_m=r['existing_finished_floor_y_m'],body_polygon_xz_m=r['old_terrain_body_hole_polygon_xz_m'],policy='Native/private door semantics retired atomically; exposed residual body floor retains its old native threshold and explicit nonwalking boundary.'))
 print('owners',len(owners),'logical',len(logical),flush=True);patch,report,index=compose_cluster.build(scene,owners,layout['retirement_records'],[r['removed_foundation_proxy_id']for r in records]);print('tops',len(patch['surface_edits']),sum(len(v)//3 for v in patch['appended_surfaces'].values()),flush=True)
 # Compact closure domains remove material-only internal edges from work.
 physical=[]
 for o in logical:
  if o['kind']in('active_walking','functional_court','retired_terminal_verge'):continue
  physical.append(o)
 # Walking ribbons outside the whole holding remain physical ground owners.
 for h in layout['holdings']:
  for j,p in enumerate(h['external_route_polygons_xz_m']):
   for k,q in enumerate(a.common.subtract([p],[traffic[v]for v in ti.candidates(p)])):physical.insert(0,dict(id=h['id']+':GATE_PHYSICAL:'+str(j)+':'+str(k),polygon_xz_m=q,plane_y_xz_m=[0,0,h['floor_y_m']]))
 for parcel in hand['parcels']:
  if parcel['id'].startswith('B15:R8:LANE:'):
   for j,p in enumerate(parcel['walk_polygons_xz_m']):
    for k,q in enumerate(a.common.subtract([p],[traffic[v]for v in ti.candidates(p)])):physical.insert(0,dict(id=parcel['id']+':PHYSICAL:'+str(j)+':'+str(k),polygon_xz_m=q,plane_y_xz_m=[0,0,parcel['floor_y_m']]))
 # Physical ordering must keep explicit public profiles first.
 physical.sort(key=lambda o:0 if o.get('kind')=='shared_public_profile'else 2 if o.get('kind')=='retired_private_floor_restoration'else 1)
 print('physical',len(physical),flush=True);interfaces=compose_cluster.interfaces(scene,index,physical);print('sides',len(interfaces['side_surface_edits']),'unknown',len(interfaces['unknown_exterior_segments']),flush=True)
 keys={(r['material'],r['triangle_index'])for r in patch['surface_edits']}
 for r in interfaces['side_surface_edits']:
  if(r['material'],r['triangle_index'])in keys:raise ValueError('Top/side edit conflict')
  patch['surface_edits'].append(r)
 patch['appended_surfaces']['bank']=[v for tr in interfaces['appended_retaining_triangles_xyz_m']for v in tr];patch['source_surface_hashes']={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in patch['surface_edits']})};patch['source_references']=[dict(path=str((FABRIC/n).relative_to(a.ROOT)),sha256=a.sha(FABRIC/n))for n in('terrain_handoff.json','selected_layout.json','access_handoff.json','ground_proposal.json','route_graph.json')]
 patch['source_references'].append(dict(path=str(addendum_path.relative_to(a.ROOT)),sha256=a.sha(addendum_path)))
 report.update(elapsed_s=time.monotonic()-t,holdings=26,actual_doors=117,retired_ids=layout['retired_source_ids'],native_holes=sum(o['action']=='hole'for o in owners),fixed_public_roots=screen['roots'],activation=False)
 for name,d in [('candidate_scene_patch.json',patch),('composition_report.json',report),('owners.json',dict(owners=owners,physical_owners=physical)),('interfaces.json',interfaces),('retirement.json',dict(records=records,retired_source_ids=layout['retired_source_ids']))]:write(name,d)
 print('DONE',report['elapsed_s'],a.sha(HERE/'candidate_scene_patch.json'),flush=True)
if __name__=='__main__':run()
