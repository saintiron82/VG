import json,math,collections
from pathlib import Path
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from .. import author as a
from ..bounded_profile_r01.finite import inside
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
D=a.HERE/'noble_terminal_diagnosis_r01/E1_proposal.json'
d=json.loads(D.read_bytes());s=d['result']['result']['solver_input'];points=s['vertices_xz_m'];tris=s['triangles'];fixed={int(k):v for k,v in s['fixed_heights'].items()};sector=d['result']['incident_sector_ledger'][0];copies=sector['copies'];v=copies[0];tris=[[v if k in copies else k for k in t]for t in tris];edges=collections.defaultdict(list)
for j,t in enumerate(tris):
 for x,y in zip(t,t[1:]+t[:1]):edges[tuple(sorted([x,y]))].append(j)
inner=[i for i,p in enumerate(points)if any(inside(p,r['polygon_xz_m'])for r in d['fixed_inner_regions'])];public=[i for i,p in enumerate(points)if any(inside(p,r['polygon_xz_m'])for r in d['fixed_public_regions'])];blocked=set(public)-{v};rr=[];cc=[];vv=[]
for(x,y),inc in edges.items():
 if x in blocked or y in blocked:continue
 rr.extend([x,y]);cc.extend([y,x]);vv.extend([math.dist(points[x],points[y])]*2)
dist,pred=dijkstra(coo_matrix((vv,(rr,cc)),shape=(len(points),len(points))).tocsr(),indices=v,return_predecessors=True);end=min(inner,key=lambda i:dist[i]);path=[end]
assert math.isfinite(dist[end])
while path[-1]!=v:path.append(int(pred[path[-1]]))
path.reverse();cut=set(tuple(sorted([x,y]))for x,y in zip(path,path[1:]));adj=collections.defaultdict(list)
for e,inc in edges.items():
 if e not in cut and len(inc)==2:adj[inc[0]].append(inc[1]);adj[inc[1]].append(inc[0])
components=[];seen=set()
for i in range(len(tris)):
 if i in seen:continue
 todo=[i];component=[]
 while todo:
  j=todo.pop()
  if j in seen:continue
  seen.add(j);component.append(j);todo.extend(adj[j])
 components.append(component)
write(HERE/'cut_design.json',dict(source=dict(path=str(D.relative_to(a.ROOT)),sha256=a.sha(D)),vertex_path=path,path_points=[points[i]for i in path],length_m=float(dist[end]),component_triangles=components,original_triangles=tris,points=points,fixed_heights={str(k):v for k,v in fixed.items()},start_sector=sector))
print('path',path,'length',dist[end],'components',list(map(len,components)))
