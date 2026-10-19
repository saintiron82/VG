"""Bind the restored public T-junction to exact observed source vectors."""
from pathlib import Path
import json,hashlib,math
H=Path(__file__).resolve().parent; R=next(p for p in H.parents if(p/'voxel_character').is_dir()); I=H.parents[1]/'interface_runtime'
def ref(p):return {'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
gpath=H.parent/'observed_graph.json';g=json.loads(gpath.read_text());regpath=H/'registration_ledger.json';rows=json.loads(regpath.read_text());j=next(x for x in rows if x['source_node']==10836);nodes=g['nodes_xyz_m']
def adjacency(rid):
 idx=next(i for i,r in enumerate(g['routes'])if r['id']==rid);out={}
 for e in g['edges']:
  if idx not in e['route_indices']:continue
  a,b=e['u'],e['v'];out.setdefault(a,set()).add(b);out.setdefault(b,set()).add(a)
 return out
def follow(start,initial,adj,distance=3.,previous=None):
 out=[start];remaining=distance;current=initial
 for _ in range(1000):
  v=nodes[current];last=out[-1];length=math.dist([last[0],last[2]],[v[0],v[2]])
  if length>=remaining:
   t=remaining/length;out.append([last[k]+t*(v[k]-last[k])for k in range(3)]);return out
  if length>1e-8:out.append(v);remaining-=length
  possible=adj[current]-({previous}if previous is not None else set())
  # At the first target endpoint the other endpoint lies behind the split.
  if previous is None and current in [j['target_u'],j['target_v']]:possible-={j['target_u'],j['target_v']}
  assert len(possible)==1,('Nonlinear public source vector',current,possible)
  previous,current=current,next(iter(possible))
 raise AssertionError('Cannot follow observed public vector')
a=adjacency('ROAD:BLOCK_011:ALLEY');start=j['source_node'];assert len(a[start])==1
# Include the source endpoint once. Its old 5.9 mm height difference remains a
# source hint; the unchanged controller uses actual collision support.
source=[nodes[start]]+follow(nodes[start],next(iter(a[start])),a,previous=start)[1:]
b=adjacency('ROAD:CIVIC_WEST_APPROACH');routes=[]
for k,node in enumerate([j['target_u'],j['target_v']]):
 branch=follow(j['target_xyz_m'],node,b)
 points=list(reversed(source))+branch[1:]
 routes.append({'id':f'R10_GRAPH_BLOCK011_TURN_{k}','group':'BLOCK011_PUBLIC_T','points':points,'source_road_ids':['ROAD:BLOCK_011:ALLEY','ROAD:CIVIC_WEST_APPROACH'],'width_m':2,'clear_width_m':2,'cart_test':False,'both_directions':True,'test_scope':'Observed public alley endpoint to each civic street direction; both return directions. No private shortcut or geometry modification.'})
d=json.loads((I/'final_r01_market_join_request.json').read_text());d['routes']=routes;d['test_scope']='One previously omitted public graph registration; exact existing geometry and unchanged capsule controller.';d['required_evidence_kinds']=['capsule'];d['producer_sources']={'graph':ref(gpath),'registration':ref(regpath),'author':ref(Path(__file__)),'final_composition_ledger':ref(H.parents[1]/'integration_r03/candidate_ledger.json')}
out=I/'graph_block011_request_r01.json';assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n');print(out)
