"""Explicit customer and back-of-stall service links on actual sampled plaza ground."""
import collections,math,time
from .author import *

def path_clear(ctx,points,width):
 for poly in corridor(points,width):
  if ctx.blocked(poly,4,5.8):return False
 return True

def simplify(points,ctx,width):
 out=[points[0]];i=0
 while i<len(points)-1:
  j=len(points)-1
  while j>i+1:
   # Do not shortcut far across a named court merely because its open square is clear.
   if math.dist(points[i],points[j])<18 and path_clear(ctx,[points[i],points[j]],width) and not support_route(ctx,[points[i],points[j]],width)[1]:break
   j-=1
  out.append(points[j]);i=j
 return out

def support_route(ctx,pts,width):
 samples=[];bad=[]
 for a,b in zip(pts,pts[1:]):
  dx,dz=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dz)
  if L<1e-9:continue
  n=max(1,math.ceil(L));nx,nz=-dz/L,dx/L
  for j in range(n+1):
   for side in (-1,0,1):
    x=a[0]+dx*j/n+side*width/2*nx;z=a[1]+dz*j/n+side*width/2*nz;s=ctx.height(x,z)
    if s:samples.append(s)
    else:bad.append([x,z])
 # Full terminal/turning discs are sampled at their 32 vertices, not only centerlines.
 for p in pts:
  for q in circ(*p,width/2):
   s=ctx.height(*q)
   if s:samples.append(s)
   else:bad.append(q)
 return samples,bad

def graph(ctx,width):
 good=set();r=width/2+.015
 for x in range(14,182):
  for z in range(-20,113):
   if not geo.point_in_convex_polygon([x,z],ctx.site,0):continue
   sq=square(x,z,r)
   if ctx.blocked(sq,4,5.8):continue
   # Actual ground at the whole square's corners and center; no synthetic floor.
   if any(ctx.height(*q) is None for q in sq+[[x,z]]):continue
   good.add((x,z))
 print('walk graph',width,len(good),flush=True)
 return good

def field(ctx,good,road,width):
 polygons=[r['polygon'] for r in ctx.res if r['kind']=='source_public_road' and r['id']=='ROAD:'+road]
 seeds=[n for n in good if any(geo.point_in_convex_polygon(n,p,0) for p in polygons)]
 assert seeds,road
 dist={n:0 for n in seeds};prev={n:None for n in seeds};q=collections.deque(sorted(seeds))
 while q:
  n=q.popleft()
  for dx,dz in [(0,1),(1,0),(0,-1),(-1,0)]:
   nxt=(n[0]+dx,n[1]+dz)
   if nxt in good and nxt not in dist:
    dist[nxt]=dist[n]+1;prev[nxt]=n;q.append(nxt)
 return dist,prev,seeds

def route(ctx,start,dist,prev,width):
 nearby=[n for x in range(round(start[0])-3,round(start[0])+4) for z in range(round(start[1])-3,round(start[1])+4) for n in [(x,z)] if n in dist and math.dist(n,start)<4]
 nearby.sort(key=lambda n:(dist[n]+math.dist(n,start),math.dist(n,start)))
 reasons=collections.Counter();first_bad=[]
 for n in nearby:
  if not path_clear(ctx,[start,list(n)],width):reasons['start_segment_blocked']+=1;continue
  pts=[start,list(n)];cur=n
  while prev[cur] is not None:cur=prev[cur];pts.append(list(cur))
  pts=[p for i,p in enumerate(pts) if i==0 or math.dist(p,pts[i-1])>1e-8]
  pts=simplify(pts,ctx,width)
  if not path_clear(ctx,pts,width):reasons['simplified_route_blocked']+=1;continue
  samples,bad=support_route(ctx,pts,width)
  if not bad:return pts,samples
  reasons['ground']+=1;first_bad=bad[:2]
 print('FAILED_START',start,width,len(nearby),dict(reasons),first_bad,flush=True)
 return None,None

def build():
 start=time.monotonic();ctx=Context();pack=load(HERE/'pack.json');layout=load(HERE/'layout.json');assert not layout['placement_errors']
 for p in pack['add_instances']:ctx.solids.append(dict(id=p['id'],polygon=p['footprint_xz_m'],y_min=3.5,y_max=p['native_top_y_m'],source='candidate'))
 ctx.reindex();groups={g['id']:g for g in layout['clusters']};routes=[];failed=[];fields={}
 for typ,width,local_z in [('customer',2.4,3.3),('service',3.0,-3.7)]:
  good=graph(ctx,width)
  for road in sorted({g['road'] for g in groups.values()}):fields[(typ,road)]=field(ctx,good,road,width)
  for p in pack['add_instances']:
   g=groups[p['cluster_id']];s=local(p,0,local_z);xz=[s[0],s[2]];dist,prev,seeds=fields[(typ,g['road'])];pts,samples=route(ctx,xz,dist,prev,width)
   if pts is None:failed.append(dict(id=p['id']+':'+typ,reason='No full-width, ground-supported link to designated public road'));continue
   rid=p['id']+':'+typ.upper();target=pts[-1];waypoints=[dict(id=rid+f':W{i:03d}',position_m=[q[0],ctx.height(*q)['world_y_m'],q[1]],support=ctx.height(*q)) for i,q in enumerate(pts)]
   routes.append(dict(id=rid,stall_id=p['id'],cluster_id=p['cluster_id'],route_type=typ,width_m=width,path_xz_m=pts,points_xyz_m=[w['position_m'] for w in waypoints],waypoints=waypoints,entrance_target=dict(id=rid+':PUBLIC_ENTRY',source_road_id=g['road'],position_m=waypoints[-1]['position_m'],inside_source_public_road_envelope=True),length_m=sum(math.dist(a,b) for a,b in zip(pts,pts[1:])),support_sample_count=len(samples),support_samples=samples,static_full_width_clear=True,bidirectional=True,runtime_status='NOT_REPLAYED',purpose='Customer counter approach' if typ=='customer' else 'Back-of-stall handcart service approach; static width only, no cart turning-dynamics claim'))
  print(typ,'ready',sum(r['route_type']==typ for r in routes),'failed',len(failed),flush=True)
 layout.update(routes=routes,status='STATIC_LINKS_PASS' if not failed else 'LINK_DRAFT_FAILED',route_errors=failed)
 retired=[dict(id=r['stall_id']+':CUSTOMER',stall_id=r['stall_id'],source_path='world_city/concept_city_v3/assemblies/market/registered/r3_clusters/walkspace_report.json',source_record_key='stall_routes',reason='Original source stall instance retired; superseded only in this candidate, original file unchanged.') for r in ctx.c['old_customer_routes']]
 write('layout.json',layout);write('customer_link_retirement.json',dict(schema='riverstone.market.local_link_retirement.v1',retired_customer_link_count=len(retired),retired_links=retired,new_route_ids=[r['id'] for r in routes],certified_493_retirement_count=0))
 write('route_summary.json',dict(status=layout['status'],customer_links=sum(r['route_type']=='customer' for r in routes),service_links=sum(r['route_type']=='service' for r in routes),failed=failed,seconds=time.monotonic()-start,support_samples=sum(r['support_sample_count'] for r in routes)))
 from .plan_view import draw
 draw(pack,layout,'candidate_plan.png')
 print('seconds',time.monotonic()-start,flush=True)
if __name__=='__main__':build()
