import json,math
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
for owner in ['E1','E2','E5']:
 d=json.loads((HERE/(owner+'_proposal.json')).read_bytes());s=d['result']['result']['solver_input'];p=s['vertices_xz_m'];t=s['triangles'];f={int(k):v for k,v in s['fixed_heights'].items()};edges={}
 for tri in t:
  for u,v in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted([u,v]))]=math.dist(p[u],p[v])
 rr=[];cc=[];vv=[]
 for(u,v),w in edges.items():rr.extend([u,v]);cc.extend([v,u]);vv.extend([w,w])
 fixed=list(f);dist,pred=dijkstra(coo_matrix((vv,(rr,cc)),shape=(len(p),len(p))).tocsr(),indices=fixed,return_predecessors=True);rows=[]
 for j,u in enumerate(fixed):
  for v in fixed[j+1:]:
   length=float(dist[j,v]);delta=abs(f[u]-f[v])
   if length>1e-12 and math.isfinite(length) and delta/length>.119:
    path=[v]
    while path[-1]!=u:path.append(int(pred[j,path[-1]]))
    rows.append(dict(indices=[u,v],points=[p[u],p[v]],heights=[f[u],f[v]],height_difference_m=delta,mesh_path_length_m=length,necessary_grade=delta/length,path_indices=path[::-1],path_points=[p[k]for k in path[::-1]]))
 rows.sort(key=lambda r:-r['necessary_grade']);write(HERE/(owner+'_fixed_paths.json'),dict(owner_id=owner,violating_pairs=rows));print(owner,rows[:2])
