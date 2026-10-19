"""Bind authored water graph to actual visible assets; no simulated flow claim."""
from .audit import *
def run():
 s=a.load_scene();c=json.loads(CONTRACT.read_text());graph=c['water_graph'];nodes={n['id']:n for n in graph['nodes']};adj=collections.defaultdict(list);incoming=collections.defaultdict(list);checks=[];issues=[]
 for e in graph['edges']:
  src,dst=nodes[e['source']],nodes[e['target']];drop=src['head_y_m']-dst['head_y_m'];mode=e['mode'];valid=(mode=='gravity'and drop>0)or(mode=='manual_lift'and bool(e.get('energy_source')))or(mode=='level_join'and abs(drop)<=e.get('head_tolerance_m',0));checks.append(dict(**e,drop_m=drop,source_head_consistent=valid));adj[src['id']].append(dst['id']);incoming[dst['id']].append(src['id'])
  if not valid:issues.append(dict(code='HEAD_EDGE_INVALID',edge=e))
  if src['network']=='industrial_nonpotable'and dst['network']in('raw_source','raw_storage','protected_supply'):issues.append(dict(code='DIRTY_TO_CLEAN',edge=e))
 def reach(seed):
  seen={seed};todo=[seed]
  while todo:
   for q in adj[todo.pop()]:
    if q not in seen:seen.add(q);todo.append(q)
  return seen
 roots=[n for n in nodes if not incoming[n]];sources={n:[r for r in roots if n in reach(r)]for n in nodes};outlets={n:'RIVER_OUTFALL'in reach(n)for n in nodes if nodes[n]['network']=='industrial_nonpotable'};assert all(outlets.values());assert not issues
 inventory=json.loads((HERE/'actual_geometry_audit.json').read_text());dominant={r['water_triangle_index']:max(r['domains'],key=lambda q:q['area_m2'])['surface_id']for r in inventory['water_triangles']};vs=s['surfaces']['water'];tris=[vs[j:j+3]for j in range(0,len(vs),3)];joins=collections.defaultdict(lambda:dict(shared_length_m=0.,max_actual_head_delta_m=0.,pairs=[]));overlaps=[]
 for i,t in enumerate(tris):
  p=[[v[0],v[2]]for v in t];pl=a.common.plane(t)
  for j,u in enumerate(tris[:i]):
   q=[[v[0],v[2]]for v in u];area=g.polygon_area(g.convex_intersection(p,q))
   if area>1e-6:overlaps.append(dict(a=i,b=j,area_m2=area))
   if dominant[i]==dominant[j]:continue
   upl=a.common.plane(u)
   for v,w in zip(p,p[1:]+p[:1]):
    length=math.dist(v,w)
    if length<1e-8:continue
    tx,tz=(w[0]-v[0])/length,(w[1]-v[1])/length
    for x,y in zip(q,q[1:]+q[:1]):
     if max(abs((z[0]-v[0])*tz-(z[1]-v[1])*tx)for z in[x,y])>1e-5:continue
     tt=[(z[0]-v[0])*tx+(z[1]-v[1])*tz for z in[x,y]];lo,hi=max(0,min(tt)),min(length,max(tt))
     if hi-lo<1e-6:continue
     edge=[[v[0]+d*tx,v[1]+d*tz]for d in[lo,hi]];key=' | '.join(sorted([dominant[i],dominant[j]]));r=joins[key];r['shared_length_m']+=hi-lo;r['max_actual_head_delta_m']=max(r['max_actual_head_delta_m'],*(abs(a.common.height(pl,z)-a.common.height(upl,z))for z in edge));r['pairs'].append([i,j])
 required=[['SPRING_VISIBLE','NORTHERN_RESERVOIR'],['NORTHERN_CHANNEL_VISIBLE','NORTHERN_RESERVOIR'],['CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE'],['EAST_CHANNEL_VISIBLE','MAIN_RIVER']]
 for pair in required:assert ' | '.join(sorted(pair))in joins,pair
 assert not overlaps
 warnings=[dict(code='ACTUAL_VERTEX_ONLY_WATER_JOIN_HEAD_STEP',surfaces=k,maximum_delta_m=r['max_actual_head_delta_m'])for k,r in joins.items()if r['max_actual_head_delta_m']>1e-5]
 byid={p['id']:p for p in s['common_instances']};assoc=[]
 def association(node,instance,status,detail):
  p=byid[instance];n=nodes[node];assoc.append(dict(node_id=node,node_head_y_m=n['head_y_m'],node_network=n['network'],source_roots=sources[node],instance_id=instance,actual_position_m=p['position_m'],offset_from_graph_node_xz_m=math.dist(n['xz_m'],[p['position_m'][0],p['position_m'][2]]),status=status,detail=detail))
 association('RAW_SPRING','RESERVOIR_SPRING_INTAKE','ACTUAL_NATIVE','Native intake at spring mouth; capacity unbuilt.')
 association('RESERVOIR','RESERVOIR_BED','ACTUAL_NATIVE','Native bed and perimeter contain the visible reservoir, except explicit intake/overflow/supply mouths.')
 association('COVERED_CISTERN','RESERVOIR_DRAWPOINT','ACTUAL_NATIVE_PLUS_NEW_WATER_DISK','Protected conduit and open draw shaft are physically present. New transparent stored-water disk is Y15.5. Long clean branches remain graph-only.')
 association('MARKET_DRAW','MARKET_FOUNTAIN','ACTUAL_NATIVE_STATIC','Native water-colored surfaces reach Y6.1; graph supply head Y4.6 is an inlet association only. Gravity supply to upper bowl is not established; powered circulation/manual filling is unbuilt. Existing opaque static water cells are retained, not reclassified as fluid.')
 services=json.loads((HERE.parent/'registered_services_r01/resolved_placements.json').read_text())
 mapping={'clergy':'CATHEDRAL_DRAW','abbey':'MONASTERY_DRAW','castle':'CASTLE_DRAW'}
 for p in services['placements']:
  rid=p['id'].split(':')[-1];n=nodes[rid];assoc.append(dict(node_id=rid,node_head_y_m=n['head_y_m'],source_roots=sources[rid],instance_id=p['id'],actual_position_m=p['position_m'],local_stored_head_y_m=p['water_head_y_m'],offset_from_graph_node_xz_m=math.dist(n['xz_m'],[p['position_m'][0],p['position_m'][2]]),status='SEALED_NEW_NATIVE_PACK_PENDING_INTEGRATION',detail=('Independent high-quarter stored water at Y22 under a Y24 floor, manually drawn. The Y15.5 reservoir cannot gravity-feed this storage. R14 CASTLE_CISTERN is a separate local-rain source with an explicit manual-lift edge; catchment and filling operation are unbuilt.' if rid=='CASTLE_DRAW' else 'Reservoir-associated manual draw from lower stored water, not groundwater at source pressure head. Covered distribution branch has no rendered buried pipe or fluid solver.')))
 mill=json.loads((HERE.parent/'registered_mill_r01/interface_contract.json').read_text());assoc.append(dict(node_id='EAST_CHANNEL_VISIBLE:1 -> EAST_CHANNEL_VISIBLE:2',instance_id='REGISTERED_MILL:EAST_CANAL',actual_position_xz_m=mill['site']['position_xz_m'],actual_water_head_y_m=mill['head_y_m'],status='SEALED_NEW_NATIVE_PACK_PENDING_INTEGRATION',detail='Rigid wheel is geometrically wet, with canal outlet association to CANAL_JOIN and RIVER_OUTFALL; rotation/torque/power are unbuilt.'))
 training=byid['TRAIN:water_trough:6'];assoc.append(dict(node_id=None,instance_id=training['id'],actual_position_m=training['position_m'],status='ACTUAL_NATIVE_NO_SOURCE_GRAPH_LINK',detail='Static trough with existing opaque water-colored cells. No supply branch or filling operation is established; no new gravity connection is inferred.'))
 write('head_graph_and_asset_associations.json',dict(base_scene=ref(a.SCENE_PATH),water_contract=ref(CONTRACT),graph_nodes=graph['nodes'],graph_edges=checks,source_roots=roots,node_source_roots=sources,industrial_nodes_reach_outfall=outlets,actual_cross_surface_joins=dict(joins),actual_positive_area_water_overlaps=overlaps,asset_associations=assoc,source_only_edges=[e for e in graph['edges']if 'covered'in e.get('role','')or(e['source']=='COVERED_CISTERN')],issues=issues,warnings=warnings,interpretation=graph['interpretation'],limits=['Separate household draw and process-canal branches are fictional design decisions, not universal medieval historical facts.','A directed head graph proves source association and relative heads only. It is not a built-pipe network or flow calculation.','No discharge, spring yield, friction, pump capacity, backwater, flood stage, water quality, torque or structural engineering result is asserted.']))
 print('GRAPH_PASS_WITH_ACTUAL_MESH_WARNINGS',warnings,len(nodes),'nodes',len(checks),'edges',dict(joins),flush=True)
if __name__=='__main__':run()
