"""Rank unapproved 20–250mm geometric joins. No routes or terrain changed."""
import json,pathlib,math,collections
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra,connected_components
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[4];B=ROOT/'world_city/concept_city_v3';g=json.load(open(O/'graph.json'));res=json.load(open(O/'residential_access_ledger.json'));mt=json.load(open(O/'market_targets.json'));points=np.asarray(g['nodes_xyz_m']);n=len(points);valid={i for i,r in enumerate(g['routes']) if r['public_assumption']!='restricted_destination_not_public_through'};a=[];b=[];w=[];active=set();nr=collections.defaultdict(set)
for e in g['edges']:
 if e['kind']=='source_vector' and set(e['route_indices'])&valid:
  a.extend([e['u'],e['v']]);b.extend([e['v'],e['u']]);w.extend([e['length_m']]*2);active.update([e['u'],e['v']])
  for v in (e['u'],e['v']):nr[v].update(g['routes'][i]['id'] for i in set(e['route_indices'])&valid)
seams=[]
for e in g['edges']:
 if e['kind']!='source_vector' and e['u'] in active and e['v'] in active:
  if e.get('height_gap_m',0)<=.02:a.extend([e['u'],e['v']]);b.extend([e['v'],e['u']]);w.extend([e['length_m']]*2)
  else:seams.append(e)
# Duplicate route vectors must not sum edge costs.
adj={}
for u,v,d in zip(a,b,w):adj[u,v]=min(adj.get((u,v),float('inf')),d)
a,b,w=zip(*[(u,v,d) for (u,v),d in adj.items()]);G=csr_matrix((w,(a,b)),shape=(n,n));_,label=connected_components(G,directed=False)
seams=[e for e in seams if label[e['u']]!=label[e['v']]]
# all market destinations exist as exact graph nodes.
goals=sorted({int(v[0]) for t in mt for v in t['station']['end_nodes']})
market_d=np.min(dijkstra(G,directed=False,indices=goals),axis=0)
def from_nodes(ds):return np.array([min(ds[int(n)]+float(w) for n,w in r['station']['end_nodes']) for r in res])
def stats(ds):
 f=ds[np.isfinite(ds)];return {'reachable':len(f),'unreachable':len(ds)-len(f),'median_m':float(np.median(f)),'p90_m':float(np.percentile(f,90)),'max_m':float(max(f))}
base=from_nodes(market_d);endpoint_ids=sorted({e[k] for e in seams for k in ('u','v')});DD=dijkstra(G,directed=False,indices=endpoint_ids);di={v:DD[i] for i,v in enumerate(endpoint_ids)};selected=[];used=set();current=market_d.copy();priority=[]
for step in range(6):
 best=None
 for i,e in enumerate(seams):
  if i in used:continue
  u,v=e['u'],e['v'];candidate=np.minimum.reduce([current,current[u]+e['length_m']+di[v],current[v]+e['length_m']+di[u]])
  rdist=from_nodes(candidate);finite=np.isfinite(rdist);before=from_nodes(current);newly=int((finite&~np.isfinite(before)).sum());gain=float(np.sum(before[np.isfinite(before)]-rdist[np.isfinite(before)]))
  score=(-newly,-gain,i)
  if best is None or score<best[0]:best=(score,i,candidate,rdist,newly,gain)
 _,i,current,rdist,newly,gain=best;used.add(i);e=seams[i]
 if newly==0 and gain<1e-6:break
 # For subsequent joins, use explicit augmented strict graph to include paths
 # whose endpoint distances improve through earlier selected joins.
 selected.append(e);u,v=e['u'],e['v'];G=G.tolil();G[u,v]=e['length_m'];G[v,u]=e['length_m'];G=G.tocsr();current=np.min(dijkstra(G,directed=False,indices=goals),axis=0);DD=dijkstra(G,directed=False,indices=endpoint_ids);di={v:DD[j] for j,v in enumerate(endpoint_ids)}
 priority.append({'priority':step+1,'node_u':u,'node_v':v,'xyz_u':points[u].tolist(),'xyz_v':points[v].tolist(),'authored_height_gap_m':e['height_gap_m'],'route_ids_u':sorted(nr[u]),'route_ids_v':sorted(nr[v]),'newly_reachable_modules_if_join_valid':newly,'total_distance_saved_for_already_reachable_modules_m':gain,'after_hypothetical_join':stats(from_nodes(current)),'newly_reachable_module_ids':[r['module_id'] for r,bef,aft in zip(res,base,from_nodes(current)) if not np.isfinite(bef) and np.isfinite(aft)],'approval':'NOT_APPROVED; do not add to strict network until actual junction replay'})
# Actual replay samples: interpolate ground height along the nearest observed
# path sample interval, retaining lateral separation and interval length.
cert=json.load(open(B/'traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04/certified_results_493_bound_r02.json'));cases={x['id']:x['result'] for x in cert['cases']}
def observed(route_ids,p):
 result=[];p=np.array(p)
 for rid in route_ids:
  for rr in [rid,rid+'_REVERSE']:
   c=cases.get(rr);samples=c.get('position_samples',[]) if c else []
   good=[x for x in samples if x.get('ground_y_m') is not None]
   if not good:continue
   q=np.array([[x['capsule_center'][0],x['ground_y_m'],x['capsule_center'][2]] for x in good]);j=int(np.linalg.norm(q[:,[0,2]]-p[[0,2]],axis=1).argmin());entry={'route_id':rr,'nearest_observed_xyz':q[j].tolist(),'nearest_sample_horizontal_offset_m':float(np.linalg.norm(q[j,[0,2]]-p[[0,2]])),'nearest_observed_minus_authored_y_m':float(q[j,1]-p[1]),'frame':good[j]['frame']}
   best=None
   for aa,bb in zip(q,q[1:]):
    v=bb-aa;h=v[[0,2]];t=np.clip(((p-aa)[[0,2]]@h)/max(float(h@h),1e-12),0,1);x=aa+t*v;offset=float(np.linalg.norm((x-p)[[0,2]]));span=float(np.linalg.norm(h))
    if best is None or offset<best[0]:best=(offset,span,float(x[1]))
   if best:entry.update({'interpolated_observed_ground_y_m':best[2],'interpolation_lateral_offset_m':best[0],'observed_sample_interval_length_m':best[1],'interpolation_is_not_exact_contact_replay':True})
   result.append(entry)
 return sorted(result,key=lambda x:x.get('interpolation_lateral_offset_m',1e9))
for x in priority:
 x['observed_u']=observed(x['route_ids_u'],x['xyz_u']);x['observed_v']=observed(x['route_ids_v'],x['xyz_v'])
 if x['observed_u'] and x['observed_v']:
  u,v=x['observed_u'][0],x['observed_v'][0];delta=abs(u.get('interpolated_observed_ground_y_m',u['nearest_observed_xyz'][1])-v.get('interpolated_observed_ground_y_m',v['nearest_observed_xyz'][1]));x['best_observed_height_difference_m']=delta
  x['interpretation']='LIKELY_WAYPOINT_HINT_MISMATCH; observed standing profiles agree within20mm, still replay turn' if delta<=.02 and max(u.get('interpolation_lateral_offset_m',99),v.get('interpolation_lateral_offset_m',99))<.25 else 'UNRESOLVED: actual samples differ or are too distant; inspect exact source surfaces and replay transition'
out={'schema':'riverstone.strict_graph_height_seam_priority.v1','strict_baseline':stats(base),'unapproved_intercomponent_height_joins':len(seams),'priorities':priority,'limits':['Greedy effects are hypothetical and cumulative. No junction is added to the production/default strict graph.','Ground_y samples are sparse measured runtime support; their interpolation is diagnostic, not a collision proof.','A waypoint mismatch does not imply a terrain repair is needed. Test the transition on unchanged geometry before editing.']};(O/'height_seam_priorities.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
