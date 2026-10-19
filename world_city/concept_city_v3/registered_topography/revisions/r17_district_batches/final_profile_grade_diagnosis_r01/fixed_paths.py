import json,math
from pathlib import Path
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'BLOCK_001_R8_C003.json').read_bytes());s=d['result']['solver_input'];p=s['vertices_xz_m'];fixed={int(k):v for k,v in s['fixed_heights'].items()};edges={}
for t in s['triangles']:
 for u,v in zip(t,t[1:]+t[:1]):edges[tuple(sorted([u,v]))]=math.dist(p[u],p[v])
rr=[];cc=[];vv=[]
for(u,v),w in edges.items():rr.extend([u,v]);cc.extend([v,u]);vv.extend([w,w])
f=list(fixed);dist,pred=dijkstra(coo_matrix((vv,(rr,cc)),shape=(len(p),len(p))).tocsr(),indices=f,return_predecessors=True);rows=[]
for j,u in enumerate(f):
 for v in f[j+1:]:
  length=float(dist[j,v]);delta=abs(fixed[u]-fixed[v])
  if length>1e-12 and math.isfinite(length)and delta/length>.12:
   path=[v]
   while path[-1]!=u:path.append(int(pred[j,path[-1]]))
   rows.append(dict(indices=[u,v],points=[p[u],p[v]],heights=[fixed[u],fixed[v]],rise_m=delta,private_mesh_path_length_m=length,necessary_grade=delta/length,path_points=[p[k]for k in path[::-1]]))
rows.sort(key=lambda r:-r['necessary_grade']);write(HERE/'BLOCK_001_R8_C003_fixed_paths.json',dict(rows=rows));print(rows[:2])
