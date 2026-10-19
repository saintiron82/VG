"""Repair node-to-segment registration using unchanged public XZ/height tolerances.
No source point/height or geometry changes. Original graph and node IDs retained.
"""
import json,pathlib,hashlib,collections,math,numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
O=pathlib.Path(__file__).resolve().parent;N=O.parent
XZ=.00005;Y=.02;CELL=4.
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=read(N/'observed_graph.json');xyz=np.array(g['nodes_xyz_m']);routes=g['routes'];public={i for i,r in enumerate(routes)if r['public_assumption']!='restricted_destination_not_public_through'};pe=[(i,e)for i,e in enumerate(g['edges'])if e['kind']=='source_vector'and public.intersection(e['route_indices'])];active={n for _,e in pe for n in[e['u'],e['v']]};claims=collections.defaultdict(set);grid=collections.defaultdict(list)
for i,e in pe:
 a,b=xyz[e['u']],xyz[e['v']]
 for n in[e['u'],e['v']]:claims[n].update(public.intersection(e['route_indices']))
 for x in range(math.floor((min(a[0],b[0])-XZ)/CELL),math.floor((max(a[0],b[0])+XZ)/CELL)+1):
  for z in range(math.floor((min(a[2],b[2])-XZ)/CELL),math.floor((max(a[2],b[2])+XZ)/CELL)+1):grid[x,z].append(i)
candidates=[]
for n in sorted(active):
 p=xyz[n]
 for ei in grid[math.floor(p[0]/CELL),math.floor(p[2]/CELL)]:
  e=g['edges'][ei]
  if n in[e['u'],e['v']]or claims[n].intersection(e['route_indices']):continue
  a,b=xyz[e['u']],xyz[e['v']];v=b-a;vv=v[[0,2]]@v[[0,2]]
  if vv<1e-20:continue
  t=float((p[[0,2]]-a[[0,2]])@v[[0,2]]/vv)
  if not 0<t<1:continue
  q=a+t*v;dx=float(np.linalg.norm(q[[0,2]]-p[[0,2]]));dy=float(abs(q[1]-p[1]))
  if dx<=XZ and dy<=Y:
   # Existing node-to-node transfer already registers near endpoint contacts.
   if min(np.linalg.norm(q-xyz[e['u']]),np.linalg.norm(q-xyz[e['v']]))<1e-8:continue
   candidates.append({'source_node':n,'source_xyz_m':p.tolist(),'target_original_edge_index':ei,'target_original_segment_id':e['segment_id'],'target_u':e['u'],'target_v':e['v'],'target_parameter':t,'target_xyz_m':q.tolist(),'horizontal_gap_m':dx,'height_gap_m':dy,'source_route_ids':[routes[i]['id']for i in sorted(claims[n])],'target_route_ids':[routes[i]['id']for i in e['route_indices']if i in public],'runtime_turn_proven':False})
# Keep all geometrically admissible registrations, including intra-component ones.
nodes=g['nodes_xyz_m'].copy();cuts=collections.defaultdict(list);newtransfers=[]
for j,c in enumerate(candidates):
 n=len(nodes);nodes.append(c['target_xyz_m']);c['target_projection_node']=n;cuts[c['target_original_edge_index']].append((c['target_parameter'],n));newtransfers.append({'u':c['source_node'],'v':n,'length_m':max(float(np.linalg.norm(np.array(c['source_xyz_m'])-c['target_xyz_m'])),1e-9),'route_indices':[],'kind':'height_tolerant_intersection','height_gap_m':c['height_gap_m'],'horizontal_gap_m':c['horizontal_gap_m'],'registration_r02_id':j})
edges=[]
for i,e in enumerate(g['edges']):
 if i not in cuts:edges.append(e);continue
 seq=[(0,e['u'])]+sorted(cuts[i])+[(1,e['v'])]
 for (t,u),(tt,v)in zip(seq,seq[1:]):
  if u==v:continue
  out=dict(e,u=u,v=v,length_m=max(float(np.linalg.norm(np.array(nodes[u])-nodes[v])),1e-12),original_edge_index=i);edges.append(out)
edges+=newtransfers
out={'nodes_xyz_m':nodes,'edges':edges,'routes':routes,'registration_revision':{'schema':'riverstone.r10.public_graph_registration.r02','original_graph_sha256':sha(N/'observed_graph.json'),'horizontal_tolerance_m':XZ,'height_tolerance_m':Y,'source_points_changed':0,'existing_node_ids_preserved':True,'public_only':True,'new_geometry_created':False,'new_projection_nodes':len(candidates),'registration_candidates_sha256_pending':'See manifest.json'}}
(O/'observed_graph.json').write_text(json.dumps(out,indent=2)+'\n');(O/'registration_ledger.json').write_text(json.dumps(candidates,indent=2)+'\n')
manifest={'schema':'riverstone.r10.registration_fix_manifest.v1','status':'ANALYTICAL_GRAPH_REGISTRATION_FIXED_PHYSICAL_TURNS_SEPARATE','sources':{str(p.relative_to(N)):sha(p)for p in[N/'observed_graph.json',N/'observed_route_observation_mapping.json',pathlib.Path(__file__)]},'outputs':{p.name:sha(p)for p in[O/'observed_graph.json',O/'registration_ledger.json']},'thresholds':{'horizontal_m':XZ,'height_m':Y},'original_nodes':len(xyz),'added_projection_nodes':len(candidates),'original_edges':len(g['edges']),'new_edges':len(edges),'split_original_edges':len(cuts),'maximum_registered_horizontal_gap_m':max((c['horizontal_gap_m']for c in candidates),default=0),'maximum_registered_height_gap_m':max((c['height_gap_m']for c in candidates),default=0),'limits':['Original source routes and observed elevations are unchanged.','New registration is analytical interpolation, not a new native turn certificate.','Private/restricted destination vectors are excluded from these joins.','Original graph,43/35 unresolved counts and original distance ledgers remain immutable.']};(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
