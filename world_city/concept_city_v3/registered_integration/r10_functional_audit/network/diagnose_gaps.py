"""Diagnose graph gaps without adding any route or changing geometry."""
import json,pathlib,collections,math
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
O=pathlib.Path(__file__).resolve().parent
g=json.load(open(O/'graph.json'));res=json.load(open(O/'residential_access_ledger.json'));pts=np.array(g['nodes_xyz_m']);n=len(pts);valid={i for i,r in enumerate(g['routes']) if r['public_assumption']!='restricted_destination_not_public_through'};a=[];b=[];active=set();nr=collections.defaultdict(set)
for e in g['edges']:
 if e['kind']=='source_vector' and set(e['route_indices'])&valid:
  a.append(e['u']);b.append(e['v']);active.update([e['u'],e['v']])
  for v in (e['u'],e['v']):nr[v].update(g['routes'][i]['id'] for i in set(e['route_indices'])&valid)
for e in g['edges']:
 if e['kind']!='source_vector' and e.get('height_gap_m',0)<=.02 and e['u'] in active and e['v'] in active:a.append(e['u']);b.append(e['v'])
G=csr_matrix((np.ones(len(a)),(a,b)),shape=(n,n));_,labels=connected_components(G,directed=False);size=collections.Counter(labels[list(active)]);main=size.most_common(1)[0][0];mn=np.array([i for i in active if labels[i]==main]);tree=cKDTree(pts[mn]);tree2=cKDTree(pts[mn][:,[0,2]]);report=[]
for cid,count in size.most_common():
 if cid==main:continue
 nn=np.array([i for i in active if labels[i]==cid]);dist,ix=tree.query(pts[nn]);j=int(dist.argmin());u,v=int(nn[j]),int(mn[ix[j]])
 dist2,ix2=tree2.query(pts[nn][:,[0,2]]);j2=int(dist2.argmin());u2,v2=int(nn[j2]),int(mn[ix2[j2]])
 affected=[r['module_id'] for r in res if any(labels[int(x[0])]==cid for x in r['station']['end_nodes'])]
 report.append({'component_id':int(cid),'nodes':count,'residential_modules':len(affected),'module_ids':affected,'nearest_main_component_3d_gap_m':float(dist[j]),'nearest_a_xyz':pts[u].tolist(),'nearest_b_xyz':pts[v].tolist(),'a_routes':sorted(nr[u]),'b_routes':sorted(nr[v]),'height_gap_m':float(abs(pts[u,1]-pts[v,1])),'horizontal_gap_m':float(np.linalg.norm((pts[u]-pts[v])[[0,2]])),'minimum_planar_gap_m':float(dist2[j2]),'height_at_minimum_planar_gap_m':float(abs(pts[u2,1]-pts[v2,1])),'status':'EVIDENCE_GAP_ONLY: validate actual surface and turning capsule before making a connector'})
report.sort(key=lambda r:(-r['residential_modules'],r['nearest_main_component_3d_gap_m']))
(O/'component_gap_priorities.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report[:15],indent=2))
# Exact Euclidean segment-pair minimum: endpoints projected to opposite segment,
# plus interior closest points of the two infinite lines when both are in bounds.
source=[e for e in g['edges'] if e['kind']=='source_vector' and set(e['route_indices'])&valid]
main_edges=[e for e in source if labels[e['u']]==main]
A=pts[[e['u'] for e in main_edges]];B=pts[[e['v'] for e in main_edges]];U=B-A;UU=np.sum(U*U,axis=1)
for rr in report:
 es=[e for e in source if labels[e['u']]==rr['component_id']];best=(float('inf'),None)
 for e in es:
  c,d=pts[e['u']],pts[e['v']];v=d-c;vv=float(v@v);W=A-c;uv=U@v;uw=np.sum(U*W,axis=1);vw=W@v;den=UU*vv-uv*uv
  ts=[]
  for t in [0.,1.]:
   p=A+t*U;s=np.clip(((p-c)@v)/max(vv,1e-20),0,1);ts.append((np.full(len(A),t),s))
  for s in [0.,1.]:
   q=c+s*v;t=np.clip(np.sum((q-A)*U,axis=1)/np.maximum(UU,1e-20),0,1);ts.append((t,np.full(len(A),s)))
  t=(uv*vw-vv*uw)/np.where(abs(den)>1e-20,den,1);s=(UU*vw-uv*uw)/np.where(abs(den)>1e-20,den,1);mask=(abs(den)>1e-20)&(t>=0)&(t<=1)&(s>=0)&(s<=1);ts.append((np.where(mask,t,np.nan),np.where(mask,s,np.nan)))
  for t,s in ts:
   pa=A+t[:,None]*U;pb=c+s[:,None]*v;dist=np.linalg.norm(pa-pb,axis=1);dist[np.isnan(dist)]=float('inf');j=int(dist.argmin())
   if dist[j]<best[0]:best=(float(dist[j]),{'component_xyz_m':pb[j].tolist(),'main_xyz_m':pa[j].tolist(),'component_routes':[g['routes'][i]['id'] for i in e['route_indices']],'main_routes':[g['routes'][i]['id'] for i in main_edges[j]['route_indices']],'horizontal_gap_m':float(np.linalg.norm((pb[j]-pa[j])[[0,2]])),'height_gap_m':float(abs(pb[j,1]-pa[j,1]))})
 rr['minimum_segment_3d_gap_m']=best[0];rr['minimum_segment_gap']=best[1]
(O/'component_gap_priorities.json').write_text(json.dumps(report,indent=2)+'\n')
