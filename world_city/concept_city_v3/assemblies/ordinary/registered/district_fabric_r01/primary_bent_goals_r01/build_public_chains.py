"""Concatenate exact authoritative road segments; split only at line intersections."""
from pathlib import Path
import json,math,heapq,hashlib,sys
O=Path(__file__).resolve().parent;ROOT=next(p for p in O.parents if (p/'voxel_character').is_dir());C=ROOT/'world_city/concept_city_v3';L=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=SHA(p));CP=C/'traversal_r5/revisions/r06_r8_precinct/public_network_final_catalog_r01/route_catalog_481_r01.json';D=L(CP);R={r['id']:r for r in D['routes']};ids=['MARKET_NORTH','UPPER_CONTOUR','MARKET_CONTOUR','WEST_MONASTERY_EDGE','CASTLE_APPROACH','CATHEDRAL_APPROACH','NOBLE_RISE','NOBLE_PUBLIC_TIE'];segs=[]
for rid in ids:
 ps=R['ROAD:'+rid]['points_xyz_m']
 for i,(a,b)in enumerate(zip(ps,ps[1:])):segs.append(dict(route_id='ROAD:'+rid,segment_index=i,a=a,b=b,cuts=[0.,1.]))
def pt(s,t):return[s['a'][i]+t*(s['b'][i]-s['a'][i])for i in range(3)]
def key(p):return round(p[0],8),round(p[2],8)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def nearest(p,rid):
 out=[]
 for si,s in enumerate(segs):
  if s['route_id']!=rid:continue
  a,b=s['a'],s['b'];dx,dz=b[0]-a[0],b[2]-a[2];t=max(0.,min(1.,((p[0]-a[0])*dx+(p[2]-a[2])*dz)/(dx*dx+dz*dz)));q=pt(s,t);out.append((math.hypot(p[0]-q[0],p[2]-q[2]),si,t,q))
 return min(out)
# Exact segment intersections are source-road junction candidates, independently audited against final actual support.
intersections=[]
for i,s in enumerate(segs):
 a,b=s['a'],s['b'];u=[b[0]-a[0],b[2]-a[2]]
 for j in range(i+1,len(segs)):
  t=segs[j]
  if s['route_id']==t['route_id']:continue
  c,d=t['a'],t['b'];v=[d[0]-c[0],d[2]-c[2]];den=cross(u,v)
  if abs(den)<1e-12:continue
  w=[c[0]-a[0],c[2]-a[2]];f=cross(w,v)/den;g=cross(w,u)/den
  if -1e-10<=f<=1+1e-10 and -1e-10<=g<=1+1e-10:
   f=max(0,min(1,f));g=max(0,min(1,g));s['cuts'].append(f);t['cuts'].append(g);intersections.append(dict(source_a=dict(route_id=s['route_id'],segment_index=s['segment_index'],t=f),source_b=dict(route_id=t['route_id'],segment_index=t['segment_index'],t=g),point_a_xyz_m=pt(s,f),point_b_xyz_m=pt(t,g)))
targets={}
# These exact original road waypoints are the starts of the bounded opening branches.
for goal,rid,segment,t in [('MARKET_TO_CASTLE','ROAD:CASTLE_APPROACH',22,1.),('MARKET_TO_ABBEY','ROAD:WEST_MONASTERY_EDGE',9,1.)]:
 si=next(i for i,x in enumerate(segs)if x['route_id']==rid and x['segment_index']==segment);segs[si]['cuts'].append(t);q=pt(segs[si],t)
 targets[goal]=dict(road_id=rid,road_cut=dict(segment_index=segment,t=t,point_xyz_m=q),end=key(q),extension=[q])
adj={};edges=[];nodes={}
for s in segs:
 cuts=sorted(set(s['cuts']))
 for t0,t1 in zip(cuts,cuts[1:]):
  a,b=pt(s,t0),pt(s,t1);u,v=key(a),key(b)
  if u==v:continue
  nodes.setdefault(u,a);nodes.setdefault(v,b);j=len(edges);edge=dict(source_route_id=s['route_id'],source_segment_index=s['segment_index'],t0=t0,t1=t1,points_xyz_m=[a,b]);edges.append(edge);weight=math.hypot(a[0]-b[0],a[2]-b[2]);adj.setdefault(u,[]).append((v,weight,j,False));adj.setdefault(v,[]).append((u,weight,j,True))
start=key(R['GOAL:SOUTH_COUNTRY_TO_MARKET']['points_xyz_m'][-1]);heap=[(0,start)];ds={start:0};parents={}
while heap:
 dist,u=heapq.heappop(heap)
 if dist!=ds[u]:continue
 for v,w,j,rev in adj.get(u,[]):
  if dist+w<ds.get(v,float('inf')):ds[v]=dist+w;parents[v]=(u,j,rev);heapq.heappush(heap,(dist+w,v))
result=[]
for goal,t in targets.items():
 allowed={'MARKET_TO_CASTLE':{'MARKET_NORTH','UPPER_CONTOUR','CASTLE_APPROACH'},'MARKET_TO_ABBEY':{'MARKET_NORTH','MARKET_CONTOUR','WEST_MONASTERY_EDGE'}}.get(goal,set(ids));heap=[(0,start)];ds={start:0};parents={}
 while heap:
  dist,u=heapq.heappop(heap)
  if dist!=ds[u]:continue
  for v,w,j,rev in adj.get(u,[]):
   if edges[j]['source_route_id'][5:]not in allowed:continue
   if dist+w<ds.get(v,float('inf')):ds[v]=dist+w;parents[v]=(u,j,rev);heapq.heappush(heap,(dist+w,v))
 u=t['end'];chain=[]
 if u not in ds:print('DISCONNECTED',goal);continue
 while u!=start:
  p,j,rev=parents[u];e=dict(edges[j]);e['traversed_reverse']=rev;e['points_xyz_m']=list(reversed(e['points_xyz_m']))if rev else e['points_xyz_m'];chain.append(e);u=p
 chain.reverse();points=[chain[0]['points_xyz_m'][0]];splices=[]
 for e in chain:
  aa,bb=e['points_xyz_m']
  if math.dist(points[-1],aa)>1e-7:splices.append(dict(kind='source_hint_height_at_same_xz_junction',from_xyz_m=points[-1],to_xyz_m=aa));
  points.append(bb)
 ext=t['extension'];last=points[-1]
 if math.hypot(last[0]-ext[0][0],last[2]-ext[0][2])>1e-8:splices.append(dict(kind='finite_public_lateral_splice',from_xyz_m=last,to_xyz_m=ext[0],length_m=math.hypot(last[0]-ext[0][0],last[2]-ext[0][2])));points+=ext
 else:points+=ext[1:]
 result.append(dict(id='GOAL:'+goal,case_class='public_corridor',bidirectional=True,points_xyz_m=points,source_road_ids=sorted(set(e['source_route_id'][5:]for e in chain)),public_segment_slices=chain,splices=splices,destination=t,length_xz_m=sum(math.hypot(a[0]-b[0],a[2]-b[2])for a,b in zip(points,points[1:])),test_scope='Exact market-to-branch-start road slices; new junction finite proof and authored bent opening branch bind separately.'))
(O/'public_chain_candidates.json').write_text(json.dumps(dict(source_catalog=ref(CP),market_point_xyz_m=R['GOAL:SOUTH_COUNTRY_TO_MARKET']['points_xyz_m'][-1],routes=result,junction_candidates=intersections),indent=2)+'\n')
for r in result:print(r['id'],len(r['points_xyz_m']),r['length_xz_m'],len(r['splices']),r['source_road_ids'])
