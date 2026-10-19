"""Reproducible read-only 2.5D composition audit. Writes only its own directory.
No arbitrary building-to-road shortcut is added: nearest-network station distances
are separately conditional on an unproved last mile. No potable or cart certificate.
"""
from pathlib import Path
import json, math, hashlib, collections, csv, heapq, re, os
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
ROOT=Path(__file__).resolve().parents[5]; OUT=Path(__file__).resolve().parent
OBSERVED=os.environ.get('R10_OBSERVED_GRAPH')=='1';PREFIX='observed_' if OBSERVED else ''
B=ROOT/'world_city/concept_city_v3'; R=B/'traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04'; P=B/'registered_integration/r9/population_audit'
def read(p):return json.load(open(p))
def dump(name,x):
 (OUT/(PREFIX+name)).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def clean(v):
 if isinstance(v,(np.floating,float)):return float(v) if math.isfinite(v) else None
 if isinstance(v,np.integer):return int(v)
 if isinstance(v,np.ndarray):return clean(v.tolist())
 if isinstance(v,list):return [clean(x) for x in v]
 if isinstance(v,tuple):return [clean(x) for x in v]
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
 return v
sources=[R/'selected_all493_bound_r02.json',R/'certified_results_493_bound_r02.json',R/'summary.json',P/'building_module_ledger.json',P/'selected_scene_metadata.json',P/'selected_asset_metadata.json',B/'registered_source/plan.json',B/'registered_integration/r9/integration_r02/index.json',B/'assemblies/waterworks/registered_water_completion_r01/head_graph_and_asset_associations.json',B/'registered_integration/r9/market_clusters/runtime_validation/replay_r01/prepared.json',B/'registered_integration/r9/market_clusters/runtime_validation/audit_report.json']
selection,cert=read(sources[0]),read(sources[1]); assert len(selection['routes'])==493 and cert['failed']==0
plan=read(sources[6]); instances={x['id']:x for x in read(sources[4])['common_instances']}; metadata=read(sources[5]); modules=read(sources[3]); water=read(sources[8]); marketprep=read(sources[9]); marketaudit=read(sources[10])
assert marketaudit['status']=='PASS' and marketaudit['positive_passed']==28
base_sha=selection['sources']['scene']['sha256']; assert base_sha=='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
index=read(sources[7]); replacements={};pack_assets={}
for p in index['packs']:
 pp=ROOT/p['path'];assert sha(pp)==p['sha256'];sources.append(pp);pack=read(pp)
 for x in pack.get('add_instances',[]):instances[x['id']]=x
 for x in pack.get('remove_instance_ids',[]):instances.pop(x,None)
 for x in pack.get('replace_instances',[]):replacements[x['id']]=x
 pack_assets.update(pack.get('common_assets',{}))
# Existing residential leaf/entrance transforms retained by r9 roof replacement proof.
road_width={r['id']:r['width_m'] for r in plan['roads']};road_width['SOUTH_COUNTRY_ROAD']=7
routes=[];negative=[]
for r in selection['routes']:
 if r.get('expected_failure'):negative.append(r['id']);continue
 if r['id'].endswith('_REVERSE'):continue
 r=dict(r);r['evidence']='r8_493_certified_vector';routes.append(r)
for r in marketprep['routes']:
 if r.get('expected_failure') or r['id'].endswith('_REVERSE'):continue
 r=dict(r);r['evidence']='r9_market_28_certified_directional_cases';routes.append(r)
# Remove no geometry; exclude restricted destinations from through routing.
restricted_prefixes=('NOBLE:','MONASTERY_ORCHARD:','MONASTERY_HERB_GARDEN:','CLERGY_CLOISTER_GARDEN:','TRAIN_RETAINED_ENTRY','GOAL:MARKET_TO_CASTLE','GOAL:MARKET_TO_TRAINING','GOAL:MARKET_TO_NOBLE')
for r in routes:
 r['public_assumption']='restricted_destination_not_public_through' if r['id'].startswith(restricted_prefixes) else 'declared_public_vector_or_public_forecourt'
 r['width_design_m']=r.get('source_width_m')
 if r['width_design_m'] is None:
  widths=[road_width[x] for x in r.get('source_road_ids',[]) if x in road_width]
  r['width_design_m']=min(widths) if widths else None
 r['cart_verified']=False
# An optional, separately named graph uses observed runtime standing heights.
# Original route/hash/XYZ remains immutable in the source and mapping ledger.
if OBSERVED:
 runtime_path=ROOT/marketaudit['runtime_result']['path'];sources.append(runtime_path);runtime=read(runtime_path)
 samples_by_id={x['id']:x['result'].get('position_samples',[]) for x in cert['cases']}
 samples_by_id.update({x['id']:x.get('position_samples',[]) for x in runtime['routes']})
 mappings=[]
 for r in routes:
  q=np.asarray(r['points'],float);v=np.diff(q,axis=0);h=v[:,[0,2]];ll=np.linalg.norm(h,axis=1);ss=np.r_[0,np.cumsum(ll)];observations=[]
  for rid in [r['id']] if samples_by_id.get(r['id']) else [r['id']+'_REVERSE']:
   for sample in samples_by_id.get(rid,[]):
    if sample.get('ground_y_m') is None:continue
    p=np.asarray(sample['capsule_center']);t=np.clip(np.sum((p[[0,2]]-q[:-1,[0,2]])*h,axis=1)/np.maximum(ll**2,1e-12),0,1);proj=q[:-1]+t[:,None]*v;dd=np.linalg.norm(proj[:,[0,2]]-p[[0,2]],axis=1);j=int(dd.argmin())
    if dd[j]>.15:continue
    observations.append({'source_case_id':rid,'frame':sample['frame'],'station_xz_m':float(ss[j]+t[j]*ll[j]),'observed_ground_y_m':sample['ground_y_m'],'horizontal_projection_error_m':float(dd[j]),'support_id':sample.get('support_id')})
  if not observations:raise RuntimeError('No admissible runtime ground samples for '+r['id'])
  observations.sort(key=lambda x:x['station_xz_m']);sx=np.array([x['station_xz_m'] for x in observations]);sy=np.array([x['observed_ground_y_m'] for x in observations])
  # Preserve original horizontal stations; observed support interpolation changes
  # graph elevation only, never source scene, native poses, route input or physics.
  actual=np.interp(ss,sx,sy);dense=np.unique(np.r_[ss,sx]);new=np.c_[np.interp(dense,ss,q[:,0]),np.interp(dense,sx,sy),np.interp(dense,ss,q[:,2])]
  mappings.append({'id':r['id'],'source_evidence':r['evidence'],'original_points_xyz_m':q.tolist(),'observed_graph_points_xyz_m':new.tolist(),'observations':observations,'max_abs_observed_minus_waypoint_y_m':float(np.max(abs(actual-q[:,1]))),'max_sample_station_gap_m':float(np.max(np.diff(sx))) if len(sx)>1 else None,'start_station_extrapolation_m':float(sx[0]),'end_station_extrapolation_m':float(ss[-1]-sx[-1]),'mapping_method':'forward certified runtime samples projected to horizontal source-polyline station; retain all observed sample stations and original corner stations; ground_y linear interpolation between observed samples; endpoint clamp only at tiny unsampled endcaps','is_new_collision_evidence':False})
  r['points']=new.tolist()
 dump('route_observation_mapping.json',mappings)
ridx={r['id']:i for i,r in enumerate(routes)}
# Unique segments, preserving every claiming route.
segs=[];dedup={}
for ri,r in enumerate(routes):
 p=np.asarray(r['points'],float)
 for a,b in zip(p,p[1:]):
  if np.linalg.norm(a-b)<1e-8:continue
  ka,kb=tuple(np.round(a,7)),tuple(np.round(b,7));key=tuple(sorted([ka,kb]))
  if key in dedup:segs[dedup[key]]['r'].add(ri)
  else:dedup[key]=len(segs);segs.append({'a':a,'b':b,'r':{ri},'cuts':{0.,1.}})
print('Unique routes/segments',len(routes),len(segs),flush=True)
# Uniform XZ spatial hash and exact segment intersections, retaining interpolated Y.
grid=collections.defaultdict(list); cell=12.
for i,s in enumerate(segs):
 for x in range(math.floor(min(s['a'][0],s['b'][0])/cell),math.floor(max(s['a'][0],s['b'][0])/cell)+1):
  for z in range(math.floor(min(s['a'][2],s['b'][2])/cell),math.floor(max(s['a'][2],s['b'][2])/cell)+1):grid[x,z].append(i)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
seen=set(); crossings=[];rejected_height=[]
for group in grid.values():
 for ii,i in enumerate(group):
  a=segs[i];p=a['a'][[0,2]];v=a['b'][[0,2]]-p
  for j in group[ii+1:]:
   pair=(min(i,j),max(i,j))
   if pair in seen:continue
   seen.add(pair);b=segs[j]
   q=b['a'][[0,2]];w=b['b'][[0,2]]-q;den=cross(v,w);vals=[]
   if abs(den)>1e-10:
    t,u=cross(q-p,w)/den,cross(q-p,v)/den
    if -1e-7<=t<=1+1e-7 and -1e-7<=u<=1+1e-7:vals=[(min(1,max(0,t)),min(1,max(0,u)))]
   elif abs(cross(q-p,v))<1e-7 and v@v>1e-12 and w@w>1e-12:
    for t in (0.,1.):
     u=((p+t*v-q)@w)/(w@w)
     if -1e-7<=u<=1+1e-7:vals.append((t,min(1,max(0,u))))
    for u in (0.,1.):
     t=((q+u*w-p)@v)/(v@v)
     if -1e-7<=t<=1+1e-7:vals.append((min(1,max(0,t)),u))
   for t,u in vals:
    pa=a['a']+t*(a['b']-a['a']);pb=b['a']+u*(b['b']-b['a']);dy=abs(pa[1]-pb[1])
    if dy<=.25+1e-8:
     a['cuts'].add(round(t,10));b['cuts'].add(round(u,10));crossings.append((i,t,j,u,dy))
    elif dy>.5 and not a['r']&b['r']:rejected_height.append({'segment_a':i,'segment_b':j,'xz_m':pa[[0,2]].tolist(),'height_difference_m':dy})
print('Intersections',len(crossings),'height_rejections',len(rejected_height),flush=True)
# Node keys 1 micrometre XYZ; zero-length planar contacts with differing heights
# become explicit transfer edges, never hidden snapping.
nodes=[];nmap={};edges=[];seg_nodes=[]
def node(p):
 k=tuple(round(float(x),6) for x in p)
 if k not in nmap:nmap[k]=len(nodes);nodes.append([float(x) for x in p])
 return nmap[k]
for si,s in enumerate(segs):
 ns=[]
 for t in sorted(s['cuts']):ns.append((t,node(s['a']+t*(s['b']-s['a']))))
 seg_nodes.append(ns)
 for (t,u),(tt,v) in zip(ns,ns[1:]):
  if u!=v:edges.append({'u':u,'v':v,'length_m':float(np.linalg.norm(np.asarray(nodes[u])-nodes[v])),'route_indices':sorted(s['r']),'kind':'source_vector','segment_id':si})
xyz=np.asarray(nodes); tree=cKDTree(xyz[:,[0,2]])
for u,v in tree.query_pairs(.00005):
 dy=abs(xyz[u,1]-xyz[v,1])
 if dy<=.25+1e-8:edges.append({'u':u,'v':v,'length_m':max(dy,1e-9),'route_indices':[],'kind':'height_tolerant_intersection','height_gap_m':float(dy)})
public_route={i for i,r in enumerate(routes) if r['public_assumption']!='restricted_destination_not_public_through'}
# Cart screening only: width >=3 m; no segment over 10% longitudinal grade.
# Turning radii, headroom, width meshes, paving, axles and loads are untested.
def matrix(public=True,strict=False,cart=False):
 allow=[]; active=set()
 for e in edges:
  if e['kind']!='source_vector':continue
  rr=[i for i in e['route_indices'] if not public or i in public_route]
  if not rr:continue
  if cart:
   rr=[i for i in rr if (routes[i]['width_design_m'] or 0)>=3]
   delta=xyz[e['v']]-xyz[e['u']];h=math.hypot(delta[0],delta[2]);grade=abs(delta[1])/max(h,1e-8)
   if not rr or grade>.1+1e-6:continue
  allow.append(e);active.update([e['u'],e['v']])
 for e in edges:
  if e['kind']=='height_tolerant_intersection' and e['u'] in active and e['v'] in active and (not strict or e['height_gap_m']<=.02):allow.append(e)
 # csr duplicates sum: deduplicate to minimum before conversion.
 adj={}
 for e in allow:
  k=tuple(sorted([e['u'],e['v']]));adj[k]=min(adj.get(k,float('inf')),e['length_m'])
 a=[];b=[];w=[]
 for (u,v),d in adj.items():a.extend([u,v]);b.extend([v,u]);w.extend([d,d])
 return csr_matrix((w,(a,b)),shape=(len(nodes),len(nodes))),active,allow
G,active,public_edges=matrix(strict=True);Gstrict=G;Gtolerant,_,_=matrix();Gcart,cartactive,cartedges=matrix(cart=True,strict=True)
print('Graph',len(nodes),len(edges),len(active),'public nodes',flush=True)
# Nearest projection is a diagnostic attachment, never an added walking edge.
public_segment_ids=sorted({e['segment_id'] for e in public_edges if e['kind']=='source_vector'})
A=np.asarray([segs[i]['a'] for i in public_segment_ids]);V=np.asarray([segs[i]['b']-segs[i]['a'] for i in public_segment_ids]);VV=np.sum(V[:,[0,2]]**2,axis=1)
def project(p,preferred=None):
 p=np.asarray(p);t=np.clip(np.sum((p[[0,2]]-A[:,[0,2]])*V[:,[0,2]],axis=1)/np.maximum(VV,1e-12),0,1);Q=A+t[:,None]*V
 dist=np.linalg.norm(Q-p,axis=1)
 if preferred is not None:
  mask=np.array([bool(segs[i]['r']&preferred) for i in public_segment_ids]);dist[~mask]=float('inf')
 j=int(np.argmin(dist));si=public_segment_ids[j];tt=float(t[j]);q=Q[j];ns=seg_nodes[si];ends=[]
 for k,(st,n) in enumerate(ns):
  if st<=tt+1e-9:lo=(st,n)
  if st>=tt-1e-9:hi=(st,n);break
 for st,n in {lo,hi}:ends.append((n,float(np.linalg.norm(q-xyz[n]))))
 return {'segment_id':si,'point_m':q.tolist(),'horizontal_gap_m':float(np.linalg.norm((q-p)[[0,2]])),'height_gap_m':float(abs(q[1]-p[1])),'straight_gap_m':float(np.linalg.norm(q-p)),'end_nodes':ends,'route_ids':[routes[i]['id'] for i in sorted(segs[si]['r'])]}
def distances_to_station(st,G=G):
 ds=np.asarray(dijkstra(G,directed=False,indices=[n for n,w in st['end_nodes']]))
 return np.min(ds+np.asarray([w for n,w in st['end_nodes']])[:,None],axis=0)
def distance_from_station(st,dist):return min(dist[n]+w for n,w in st['end_nodes'])
def stats(ds):
 a=np.asarray(ds);f=a[np.isfinite(a)];return {'count':len(a),'reachable':len(f),'unreachable':int(len(a)-len(f)),'median_m':float(np.median(f)) if len(f) else None,'p90_m':float(np.percentile(f,90)) if len(f) else None,'max_m':float(np.max(f)) if len(f) else None}
# Target market anchors: sampled certified customer routes + named common market goal.
market_targets=[]
for r in routes:
 if r['id'].startswith('R9_CLUSTER_') and r.get('kind')=='market_cluster_customer':market_targets.append({'id':r['id'],'point_m':r['points'][0],'access':'14 selected directional customer cases only; 7 distinct stations'})
common_market=next(r['points'][-1] for r in routes if r['id']=='GOAL:PORT_TO_MARKET');market_targets.append({'id':'NAMED_MARKET_GOAL','point_m':common_market,'access':'r8 named public destination'})
market_ds=[]
for t in market_targets:t['station']=project(t['point_m']);market_ds.append(distances_to_station(t['station']))
market_d=np.min(market_ds,axis=0)
tolerant_market_d=np.min([distances_to_station(t['station'],Gtolerant) for t in market_targets],axis=0)
# Drawpoints from ACTUAL assets, not ideal hydraulic node positions.
draws=[]
for a in water['asset_associations']:
 if a.get('node_id') not in ['MARKET_DRAW','CATHEDRAL_DRAW','MONASTERY_DRAW','CASTLE_DRAW','COVERED_CISTERN']:continue
 t={'id':a['node_id'],'instance_id':a['instance_id'],'point_m':a['actual_position_m'],'hydraulic_status':a['detail'],'potability':'UNVERIFIED','public_access':'public_market_assumed' if a['node_id']=='MARKET_DRAW' else 'conditional_institutional_or_service_access'}
 t['station']=project(t['point_m']);draws.append(t)
marketdraw=next(x for x in draws if x['id']=='MARKET_DRAW');water_d=distances_to_station(marketdraw['station']);conditional_water_d=np.min([distances_to_station(x['station']) for x in draws if x['id'] in ['MARKET_DRAW','CATHEDRAL_DRAW','MONASTERY_DRAW']],axis=0)
# Per-leaf door extraction, composing all native local transforms.
master_cache={}
def master(path):
 path=str(path)
 if path not in master_cache:master_cache[path]=read(ROOT/path)
 return master_cache[path]
def rotate(v,y):
 c,s=math.cos(y),math.sin(y);x,h,z=v;return np.array([c*x+s*z,h,-s*x+c*z])
def leaf_local(row):
 # Root metadata native_modules supplies rigid transforms; same leaf metadata
 # ordering/role mapping as population audit.
 if not row['leaf_role']:return np.zeros(3),0.
 key=row['asset_key'];trail=row['leaf_role'].split('/');pos=np.zeros(3);yaw=0.
 for part in trail:
  if key in metadata:m=metadata[key]['metadata']
  else:
   candidates=[ROOT/'world_city/runtime_city/generated/r2/masters'/f'{key}.json',B/'assemblies/property/cache'/f'{key}.master.json']
   p=next(p for p in candidates if p.exists());m=read(p)['metadata']
  if m.get('modules'):
   info=next(x for x in m['modules'] if x['id']==part);child=next(x for x in m['native_modules'] if x['asset_key']==info['asset_key'])
  else:child=m['native_modules'][int(part)]
  pos=pos+rotate(child.get('translation',[0,0,0]),yaw);yaw+=child.get('yaw_rad',0);key=child['asset_key']
 return pos,yaw
res=[]
for mi,row in enumerate(modules):
 if row['category'] not in ['lodging','mixed_house']:continue
 ins=instances[row['instance_id']];source=master(row['source_master']);union=source.get('extensions',{}).get('source_assemblies')
 if union and row['leaf_role']:
  src=next(x for x in union if x['key']==row['leaf_role']);m=src['authored_dimensions'];ep=m.get('entrance',{}).get('position');placement=src['placement'];lp=np.array(placement['translation']);ly=math.atan2(placement['basis'][0][2],placement['basis'][0][0])
 else:m=source['metadata'];lp,ly=leaf_local(row);ep=m.get('entrance',{}).get('position')
 if ep is None:ep=[0,.5,m['body_bounds']['max'][2]];ek='front_face_proxy_no_door_metadata'
 else:ek='native_main_entrance_metadata'
 local=lp+rotate(ep,ly);point=rotate(local,ins.get('yaw_rad',0))+np.array(ins['position_m']);station=project(point)
 hold=re.match(r'(BLOCK_\d+:R8_[A-Z]\d+)',row['instance_id']);holding=hold.group(1) if hold else None
 related={i for i,r in enumerate(routes) if holding and (r['id']==holding+':PUBLIC_ENTRY' or any(x.startswith(holding+':') for x in r.get('source_road_ids',[]) if x!=r['id']))}
 holding_station=project(point,related) if related else None
 # Prefer holding's proven gate corridor when its physical distance is within 40m;
 # never fake the unmeasured path from the leaf door to that corridor.
 chosen=holding_station if holding_station and holding_station['straight_gap_m']<40 else station
 out={**row,'module_id':f"{row['instance_id']}::{row['leaf_role'] or row['leaf_asset_key']}",'door_point_m':point.tolist(),'door_basis':ek,'r9_roof_replaced':row['instance_id'] in replacements,'station_basis':'same_holding_certified_entry_vector' if chosen is holding_station else 'nearest_declared_public_vector_diagnostic_only','station':chosen,'nearest_public_station':station,'complete_door_route_certified':False,'market_network_m':distance_from_station(chosen,market_d),'hypothesis250mm_market_network_m':distance_from_station(chosen,tolerant_market_d),'market_draw_network_m':distance_from_station(chosen,water_d),'conditional_three_draw_network_m':distance_from_station(chosen,conditional_water_d),'last_mile_status':'UNPROVED: straight gap is not a walking distance; no shortcut added','potable_distance_m':None}
 res.append(out)
print('Residential modules',len(res),flush=True)
# Greedy six-site facility location at real public-road vector nodes, outside
# restricted precinct polygons. It is a demand model, not potable-water approval.
def point_in(p,poly):
 x,z=p;inside=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside
restricted_polys=[x['polygon_xz_m'] for x in plan['districts'] if x['id'] in ['D_CASTLE','D_TRAIN','D_NOBLE','D_CLERGY','D_MONASTERY']]
wall=plan['wall_registration']['polygon_xz_m'];candidate=[];bins=set()
for ri,r in enumerate(routes):
 if not r['id'].startswith('ROAD:') or ri not in public_route:continue
 for p in r['points']:
  x,y,z=p
  if not point_in((x,z),wall) or any(point_in((x,z),poly) for poly in restricted_polys):continue
  if y>14:continue # feeder head15.5 leaves illustrative head margin only.
  k=(round(x/20),round(z/20))
  if k in bins:continue
  st=project(p,{ri});n=min(st['end_nodes'],key=lambda v:v[1])[0]
  if np.linalg.norm(xyz[n]-p)>.01:continue
  bins.add(k);candidate.append({'node':n,'point_m':xyz[n].tolist(),'road':r['id'],'supply_status':'DESIGN_ONLY: source branch, flow, quality, construction and clear access unverified'})
D=dijkstra(G,directed=False,indices=[c['node'] for c in candidate]);C=np.asarray([[distance_from_station(r['station'],d) for r in res] for d in D]);base=np.asarray([r['market_draw_network_m'] for r in res]);cur=base.copy();chosen=[];facility=[]
# Lexicographic objective: minimize disconnected modules first, then total
# equal-weight module network distance. Not resident/household weights.
for step in range(6):
 best=None
 for i,c in enumerate(candidate):
  if i in chosen:continue
  values=np.minimum(cur,C[i]);score=(int(np.isinf(values).sum()),float(np.where(np.isfinite(values),values,0).sum()),i)
  if best is None or score<best[0]:best=(score,i,values)
 _,i,cur=best;chosen.append(i);facility.append({'addition_count':step+1,**candidate[i],'summary':stats(cur),'improvement_basis':'nearest/holding public-network station only; unproved residence last-mile and facility branch excluded'})
for j,r in enumerate(res):r['proposed_3_draw_network_m']=float(np.minimum.reduce([base]+[C[i] for i in chosen[:3]])[j]);r['proposed_6_draw_network_m']=float(cur[j])
# Logistics: actual public route station distances only; cart graph is a conservative
# dimensional/grade screen, never a pass. Every shed interior stays unproved.
logistics=[]
anchors=[('PORT_ENTRY',next(r['points'][0] for r in routes if r['id']=='GOAL:PORT_TO_MARKET'))]+[(i['id'],i['position_m']) for i in instances.values() if i['id'].startswith('PORT_SHED_')]+[(r['id'],r['points'][0]) for r in routes if r['id'].startswith('GATE:')]
market_cart=distances_to_station(project(common_market),Gcart)
for name,p in anchors:
 st=project(p);logistics.append({'id':name,'point_m':p,'station':st,'pedestrian_network_to_market_m':distance_from_station(st,market_d),'cart_dimensional_screen_to_named_market_m':distance_from_station(st,market_cart),'cart_verified':False,'warehouse_last_mile_status':'unproved doorway/loading apron link' if name.startswith('PORT_SHED_') else 'only declared anchor'})
# Route grade and private passage audit.
route_ledger=[]
for r in routes:
 q=np.asarray(r['points']);v=np.diff(q,axis=0);h=np.linalg.norm(v[:,[0,2]],axis=1);grades=np.abs(v[:,1])/np.maximum(h,1e-12)
 route_ledger.append({k:r[k] for k in ['id','case_class','evidence','public_assumption','width_design_m','cart_verified'] if k in r}|{'length_3d_m':float(np.linalg.norm(v,axis=1).sum()),'max_sample_grade':float(np.max(grades)),'segments_over_10pct':int((grades>.100001).sum()),'source_road_ids':r.get('source_road_ids',[]),'source_points_count':len(q)})
cc,labels=connected_components(G,directed=False);cs=collections.Counter(labels[list(active)])
strict_market_d=np.min([distances_to_station(t['station'],Gstrict) for t in market_targets],axis=0)
summary={'schema':'riverstone.functional_network_audit.v1','status':'READ_ONLY_ANALYTICAL_COMPOSITION_NOT_WHOLE_CITY_RUNTIME_CERTIFICATE','height_basis':'interpolated_actual_runtime_ground_samples' if OBSERVED else 'authored_declared_waypoint_hints','source_base_sha256':base_sha,'sources':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in sources], 'certification':{'old_cases':493,'old_positive_directional_cases':478,'old_negative_controls':15,'old_unique_positive_vectors':239,'market_new_positive_directional_cases':28,'market_new_unique_positive_vectors':14,'market_new_negative_controls':3,'market_all132_not_claimed':True,'cart_certified_cases':0},'graph':{'nodes':len(nodes),'source_segments':len(segs),'edges':len(edges),'public_nodes':len(active),'public_components':len(cs),'largest_component_nodes':max(cs.values()),'height_rejected_contacts_over_0_5m':len(rejected_height),'junction_tolerance_xz_m':.00005,'junction_tolerance_y_m':.02,'sensitivity_only_junction_tolerance_y_m':.25,'strict_junction_tolerance_y_m':.02,'junction_status':'geometric interpolation transfer only, not actual arbitrary-turn certification'},'residential':{'modules':len(res),'instances':len(set(r['instance_id'] for r in res)),'same_holding_entry_station_modules':sum(r['station_basis']=='same_holding_certified_entry_vector' for r in res),'complete_door_route_certified':0,'market_network_station_distances':stats([r['market_network_m'] for r in res]),'market_draw_station_distances':stats(base),'conditional_three_draw_station_distances':stats([r['conditional_three_draw_network_m'] for r in res]),'unproven_last_mile_horizontal_gap_m':stats([r['station']['horizontal_gap_m'] for r in res]),'hypothesis250mm_market_reachable_modules':sum(math.isfinite(distance_from_station(r['station'],tolerant_market_d)) for r in res)},'new_drawpoints':{'objective':'minimize unconnected modules, then sum equal-weight module network distance; no household count or population capacity inferred','candidate_count':len(candidate),'baseline':stats(base),'after_3':facility[2]['summary'],'after_6':facility[5]['summary'],'potability':'UNVERIFIED for all existing and proposed drawpoints'},'limits':['Route coordinates are certified declared XYZ hints, not a continuous as-built surveyed surface. Certified paths can use derived collision recipes absent from the base visual scene.','Arbitrary transitions at analytic intersections are not runtime-certified. Height-sensitive composition and private access exclusions are explicit.','Every residential module has a ledger; no invented off-network straight line is added to walking distance. Nearest/holding station results are conditional and do not establish door-to-market or door-to-water access.','Road width is a source design width, not swept cart clearance. Cart screen uses width>=3m and sample grade<=10%; these are analyst design screens, not universal historic standards or cart simulation.','Institutional drawpoints have no declared unrestricted public access; primary public scenario uses market fountain only, whose operational head mismatch is separately disclosed.','No industrial canal, river, livestock trough or raw source is called potable. Water quality, flows, source reliability, catchments and distribution construction are unverified.','r9 positive market28 is additive, not a full r9 rerun of the old493; proposed gates excluded until frozen inputs arrive.','Residential ledger covers536 metadata-classified leaf modules in378 instances, not a complete population census. Current r9 roof replacements preserve rigid pose and entrance geometry per their source proof.']}
dump('summary.json',clean(summary));dump('route_ledger.json',clean(route_ledger));dump('graph.json',clean({'nodes_xyz_m':nodes,'edges':edges,'routes':[{'id':r['id'],'public_assumption':r['public_assumption'],'evidence':r['evidence']} for r in routes]}));dump('residential_access_ledger.json',clean(res));dump('water_drawpoints.json',clean(draws));dump('market_targets.json',clean(market_targets));dump('facility_location_candidates.json',clean({'selected':facility,'candidates':candidate}));dump('logistics_access_ledger.json',clean(logistics));dump('height_discontinuities.json',clean(rejected_height));dump('excluded_negative_cases.json',negative)
fields=['module_id','instance_id','category','source_pack','station_basis','market_network_m','market_draw_network_m','conditional_three_draw_network_m','proposed_3_draw_network_m','proposed_6_draw_network_m','last_mile_horizontal_gap_m','last_mile_height_gap_m','complete_door_route_certified','potable_distance_m']
with open(OUT/(PREFIX+'residential_access_ledger.csv'),'w') as f:
 w=csv.DictWriter(f,fields);w.writeheader()
 for r in res:w.writerow(clean({k:r.get(k) for k in fields}|{'last_mile_horizontal_gap_m':r['station']['horizontal_gap_m'],'last_mile_height_gap_m':r['station']['height_gap_m']}))
print(json.dumps(clean({k:summary[k] for k in ['certification','graph','residential','new_drawpoints']}),indent=2),flush=True)
