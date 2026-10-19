"""Read-only helper over persisted observed20mm public graph."""
import json,pathlib,math,numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
O=pathlib.Path(__file__).resolve().parent
class PublicGraph:
 def __init__(self):
  self.data=json.loads((O/'observed_graph.json').read_text());self.xyz=np.array(self.data['nodes_xyz_m']);self.routes=self.data['routes'];self.public={i for i,r in enumerate(self.routes) if r['public_assumption']!='restricted_destination_not_public_through'};self.edges=[e for e in self.data['edges'] if e['kind']=='source_vector' and self.public.intersection(e['route_indices'])];active={n for e in self.edges for n in [e['u'],e['v']]};allow=self.edges+[e for e in self.data['edges'] if e['kind']=='height_tolerant_intersection' and e['height_gap_m']<=.02 and e['u'] in active and e['v'] in active];adj={}
  for e in allow:
   k=tuple(sorted([e['u'],e['v']]));adj[k]=min(adj.get(k,float('inf')),e['length_m'])
  aa=[];bb=[];ww=[]
  for (u,v),w in adj.items():aa.extend([u,v]);bb.extend([v,u]);ww.extend([w,w])
  self.G=csr_matrix((ww,(aa,bb)),shape=(len(self.xyz),len(self.xyz)));self.a=self.xyz[[e['u'] for e in self.edges]];self.v=self.xyz[[e['v'] for e in self.edges]]-self.a
 def project(self,p,road=None):
  p=np.array(p);v=self.v;a=self.a;t=np.clip(np.sum((p[[0,2]]-a[:,[0,2]])*v[:,[0,2]],axis=1)/np.maximum(np.sum(v[:,[0,2]]**2,axis=1),1e-20),0,1);q=a+t[:,None]*v;ds=np.linalg.norm(q-p,axis=1)
  if road:
   ds[[not any(self.routes[i]['id']==road for i in e['route_indices']) for e in self.edges]]=np.inf
  j=int(ds.argmin());e=self.edges[j];assert math.isfinite(ds[j]);return {'point_m':q[j].tolist(),'straight_gap_m':float(ds[j]),'horizontal_gap_m':float(np.linalg.norm(q[j,[0,2]]-p[[0,2]])),'height_gap_m':float(abs(q[j,1]-p[1])),'end_nodes':[[e['u'],float(np.linalg.norm(q[j]-self.xyz[e['u']]))],[e['v'],float(np.linalg.norm(q[j]-self.xyz[e['v']]))]],'route_ids':[self.routes[i]['id'] for i in e['route_indices']]}
 def distances(self,st):
  ds=np.asarray(dijkstra(self.G,directed=False,indices=[n for n,w in st['end_nodes']]));return np.min(ds+np.array([w for n,w in st['end_nodes']])[:,None],axis=0)
 @staticmethod
 def from_station(st,ds):return min(ds[n]+w for n,w in st['end_nodes'])
def clean(x):
 if isinstance(x,(np.floating,float)):return float(x) if math.isfinite(x) else None
 if isinstance(x,np.integer):return int(x)
 if isinstance(x,np.ndarray):return clean(x.tolist())
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 return x
def stats(ds,weights=None):
 a=np.array(ds);mask=np.isfinite(a);f=a[mask];out={'count':len(a),'reachable':int(mask.sum()),'unreachable':int((~mask).sum()),'median_m':float(np.median(f)) if len(f) else None,'p90_m':float(np.percentile(f,90)) if len(f) else None,'max_m':float(max(f)) if len(f) else None}
 if weights is not None:
  w=np.array(weights);wf=w[mask];ids=np.argsort(f);s=np.cumsum(wf[ids])/sum(wf);out['area_weighted_median_m']=float(f[ids[np.searchsorted(s,.5)]]);out['area_weighted_p90_m']=float(f[ids[np.searchsorted(s,.9)]]);out['area_share_reachable']=float(w[mask].sum()/w.sum());out['assumed_6000_area_allocation_reachable']=float(6000*w[mask].sum()/w.sum());out['area_share_within_threshold']={str(d):float(w[a<=d].sum()/w.sum()) for d in [100,200,300,500]}
 return clean(out)
