"""Bind all supported grounds spurs to explicit retained entry/public-road ownership."""
from build_ledger import *
import collections, math, time
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.runtime_city.checks import placement as g
PROFILE=CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'
def run():
 t=time.monotonic();routes=load(HERE/'external_routes.json');routes_ref=ref(HERE/'external_routes.json');rec=load(PROFILE);scene=a.load_scene();out=[]
 for group,token in [('monastery','MONASTERY'),('cathedral','CLERGY'),('castle','CASTLE')]:
  batch=[r for r in routes['routes'] if token in r['holding_id']];sources=[r for k in ('approaches','landings')for r in rec[k]['triangles']if r['group_id'] in (group,group+'_public_landing')];si=g._SpatialIndex(8)
  for i,r in enumerate(sources):si.add(i,r['polygon_xz_m'])
  xzs=[v for r in sources for v in r['polygon_xz_m']];win=b.rect(min(v[0]for v in xzs)-1,min(v[1]for v in xzs)-1,max(v[0]for v in xzs)+1,max(v[1]for v in xzs)+1)
  ix=a.TriangleIndex(scene,[win]);rows=[];landing=set();road_seams=[r for r in rec['landings']['masks']if r['group_id']==group+'_public_landing']
  for row in ix.rows:
   if row['material']not in ('road','alley'):continue
   p=row['polygon_xz_m'];q=[sum(v[0]for v in p)/3,sum(v[1]for v in p)/3];matches=[sources[j]for j in si.candidates(p)if g.point_in_convex_polygon(q,sources[j]['polygon_xz_m']) and abs(a.common.height(a.common.plane(sources[j]['triangle_xyz_m']),q)-a.common.height(row['plane_y_xz_m'],q))<1e-5]
   if not matches:continue
   i=len(rows);rows.append(dict(row,recovered_owner_ids=[r['owner_id']for r in matches]))
   if any(r['group_id'].endswith('public_landing')for r in matches) and any(g.polygon_area(g.convex_intersection(p,s['polygon_xz_m']))>1e-9 for s in road_seams):landing.add(i)
  lines=collections.defaultdict(list);adj=collections.defaultdict(set)
  for i,row in enumerate(rows):
   p=row['polygon_xz_m']
   for u,v in zip(p,p[1:]+p[:1]):
    dx,dz=v[0]-u[0],v[1]-u[1];n=math.hypot(dx,dz)
    if n<1e-8:continue
    ux,uz=dx/n,dz/n
    if ux<-1e-10 or(abs(ux)<1e-10 and uz<0):ux,uz=-ux,-uz
    c=-uz*u[0]+ux*u[1];key=(round(ux,6),round(uz,6),round(c,5));aa=ux*u[0]+uz*u[1];bb=ux*v[0]+uz*v[1];lines[key].append((min(aa,bb),max(aa,bb),i,u,v))
  for edges in lines.values():
   edges.sort()
   for j,e in enumerate(edges):
    lo,hi,i,u,v=e
    for ll,hh,k,uu,vv in edges[j+1:]:
     if ll>=hi-1e-7:break
     if i==k or min(hi,hh)-max(lo,ll)<1e-7:continue
     ux,uz=v[0]-u[0],v[1]-u[1];n=math.hypot(ux,uz);ux/=n;uz/=n
     if ux<-1e-10 or(abs(ux)<1e-10 and uz<0):ux,uz=-ux,-uz
     tt=(max(lo,ll)+min(hi,hh))/2;c=-uz*u[0]+ux*u[1];q=[ux*tt-uz*c,uz*tt+ux*c]
     if abs(a.common.height(rows[i]['plane_y_xz_m'],q)-a.common.height(rows[k]['plane_y_xz_m'],q))>1e-5:continue
     adj[i].add(k);adj[k].add(i)
  # Reverse multi-source BFS, once per retained entry network, not once per holding.
  parent={i:None for i in sorted(landing)};todo=collections.deque(parent)
  while todo:
   i=todo.popleft()
   for k in sorted(adj[i]):
    if k not in parent:parent[k]=i;todo.append(k)
  cachepath=HERE/f'entry_graph_{group}.json'
  cachepath.write_text(json.dumps({'source_profile':ref(PROFILE),'scene':ref(a.SCENE_PATH),'rows':[{k:r[k]for k in ('triangle_index','polygon_xz_m','plane_y_xz_m','recovered_owner_ids')}for r in rows],'parent':parent,'landing':sorted(landing),'road_seams':road_seams},separators=(',',':'))+'\n')
  for route in batch:
   target=route['polyline_xz_m'][-1];seeds=[i for i,row in enumerate(rows)if g.point_in_convex_polygon(target,row['polygon_xz_m'])];good=[i for i in seeds if i in parent];chain=[]
   if good:
    i=good[0]
    while i is not None:chain.append(i);i=parent[i]
   end=chain[-1] if chain else None;named=[s for s in road_seams if end is not None and g.polygon_area(g.convex_intersection(rows[end]['polygon_xz_m'],s['polygon_xz_m']))>1e-9]
   out.append(dict(holding_id=route['holding_id'],route_id=route['id'],group_id=group,status='PASS'if named else'NO_NAMED_PUBLIC_CONTINUATION',terminal_xz_m=target,terminal_actual_triangle_ids=[rows[i]['triangle_index']for i in seeds],terminal_recovered_owner_ids=sorted(set(v for i in seeds for v in rows[i]['recovered_owner_ids'])),continuation_triangle_ids=[rows[i]['triangle_index']for i in chain],continuation_recovered_owner_ids=sorted(set(v for i in chain for v in rows[i]['recovered_owner_ids'])),named_public_road_ids=sorted(set(s['road_id']for s in named)),named_landing_mask_ids=sorted(set(s['owner_id']for s in named)),actual_group_triangle_count=len(rows),public_connected_triangle_count=len(parent)))
  print(group,len(rows),'connected',len(parent),'routes',len(batch),'pass',sum(v['status']=='PASS'for v in out if v['group_id']==group),flush=True)
 result=dict(schema='riverstone.precinct.r06.named_public_continuation.v1',base_scene=ref(a.SCENE_PATH),external_routes=routes_ref,retained_profiles=ref(PROFILE),route_continuations=out,summary={'pass':sum(r['status']=='PASS'for r in out),'failed':sum(r['status']!='PASS'for r in out),'seconds':time.monotonic()-t},method='Actual hash-bound R7 road/alley top triangles matched to retained recovered approach/landing ownership at the same plane height. Positive-length shared XYZ edges form the continuation graph. Public terminal landing triangles intersect an explicitly named public-road seam mask. No material-only public-owner inference.',limits=['Rendered-top graph proof does not replace whole-network capsule width replay or controller playtest.','The two metre new spurs have separate full-width finite-plane and retained-bank tests.'])
 (HERE/'public_continuation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':run()
