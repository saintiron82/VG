"""Full-width source corridors from new grounds to actual existing public tops."""
from plan_grounds import *
import heapq
from native_walks import CompositeSupportIndex

def boxmask(p):return b.mask([p])
def simplify(pts):
 out=[pts[0]]
 for a,c,d in zip(pts,pts[1:],pts[2:]):
  if (c[0]-a[0])*(d[1]-c[1])!=(c[1]-a[1])*(d[0]-c[0]):out.append(c)
 if pts[-1]!=out[-1]:out.append(pts[-1])
 return out

def main():
 t=time.monotonic();plan=load(HERE/'grounds_plan.json');m=np.load(HERE/'owner_masks.npz');r=np.load(HERE/'terrain_raster.npz');nw=np.load(HERE/'native_walk_raster.npz');h,g,public=nw['height'],nw['grade'],r['public'];obstacle=nw['obstacle'];plan['units']=load(HERE/'resolved_placements.json')['holdings'];scene=terrain.load_scene();owners=load(HERE/'actual_owner_use_ledger.json')['owners'];reserv=load(HERE/'preserved_reservations.json')['reservations'];fixed=b.mask([p for a in reserv if a['kind']in('phase01','phase02','existing_designed_garden','existing_productive_frame')for p in a['polygon_parts_xz_m']],True)
 new=b.mask([u['polygon_xz_m']for u in plan['units']]);waterfixtures=b.mask([f['footprint_xz_m']for f in load(CITY/'assemblies/waterworks/registered_services_r01/locations.json')['drawhouses']]);walk=np.isfinite(h)&(g<=.12+1e-8)&~b.buffer(obstacle,1.5)&~b.buffer(m['water'],2)&~b.buffer(new,1.5)&~b.buffer(fixed,1)&~b.buffer(waterfixtures,2)
 # A conservative1m grid clearance screen precedes exact ribbon/side checks.
 walk&=minimum_filter((np.isfinite(h)&~obstacle&~m['water']).astype(np.uint8),size=3,mode='constant').astype(bool)
 walk&=~np.load(HERE/'route_hazards.npz')['hazard']
 target=walk&public&np.load(HERE/'retained_target_mask.npz')['target'];dist=np.full(b.SHAPE,np.inf);parent=np.full((*b.SHAPE,2),-1,np.int32);heap=[]
 for z,x in np.argwhere(target):dist[z,x]=0;heap.append((0,int(z),int(x)))
 heapq.heapify(heap)
 while heap:
  cost,z,x=heapq.heappop(heap)
  if cost!=dist[z,x]:continue
  for dz,dx in ((1,0),(-1,0),(0,1),(0,-1)):
   zz,xx=z+dz,x+dx
   if not(0<=zz<b.NZ and 0<=xx<b.NX and walk[zz,xx]):continue
   dy=abs(h[zz,xx]-h[z,x])
   if dy>.16:continue
   nc=cost+1+dy*3
   if nc<dist[zz,xx]:dist[zz,xx]=nc;parent[zz,xx]=[z,x];heapq.heappush(heap,(nc,zz,xx))
 print('reachable',int(np.isfinite(dist).sum()),flush=True)
 index=CompositeSupportIndex(scene,[b.rect(*b.BOUNDS)]);sides=SideIndex(scene);routes=[];unresolved=[]
 for u in plan['units']:
  x,y,z=u['position_m'];w,d=u['dimensions_m'];starts=[('east',[x+w/2+2.5,z+.5],[x+w/2,z]),('west',[x-w/2-2.5,z+.5],[x-w/2,z]),('south',[x+.5,z+d/2+2.5],[x,z+d/2]),('north',[x+.5,z-d/2-2.5],[x,z-d/2])];choices=[]
  for direction,p,gate in starts:
   iz,ix=int(math.floor(p[1]-b.BOUNDS[1])),int(math.floor(p[0]-b.BOUNDS[0]));
   if not np.isfinite(dist[iz,ix]):continue
   pts=[];zz,xx=iz,ix
   for n in range(5000):
    pts.append([b.BOUNDS[0]+xx+.5,b.BOUNDS[1]+zz+.5]);nxt=parent[zz,xx]
    if nxt[0]<0:break
    zz,xx=map(int,nxt)
   pts=simplify([gate]+pts);polys=b.ribbon(pts,2)+[b.rect(q[0]-1,q[1]-1,q[0]+1,q[1]+1)for q in pts[1:-1]]
   checks=[terrain.audit_polygon(index,p,None)for p in polys];bad=[v for v in checks if not v['passes_existing_surface']];sideowners=[]
   for ri,c in enumerate(checks):
    for pi,s in enumerate(c['source_pieces']):sideowners.append({'id':f'{u["id"]}:{direction}:{ri}:{pi}','polygon_xz_m':s['polygon_xz_m'],'plane_y_xz_m':s['plane_y_xz_m']})
   sc=sides.audit(sideowners)
   # Segment/triangle seam jumps are tested at all clipped polygon vertices.
   seam_bad=[]
   for ci,c in enumerate(checks):
    ps=c['source_pieces']
    for a in ps:
     for q in a['polygon_xz_m']:
      ys=[terrain.common.height(v['plane_y_xz_m'],q)for v in ps if geo.point_in_convex_polygon(q,v['polygon_xz_m'],1e-7)]
      if ys and max(ys)-min(ys)>.15+1e-7:seam_bad.append([q,max(ys)-min(ys)])
   choices.append({'id':u['id']+':public_route','holding_id':u['id'],'direction':direction,'width_m':2,'polyline_xz_m':pts,'ribbon_polygons_xz_m':polys,'source_distance_m':sum(math.dist(a,c)for a,c in zip(pts,pts[1:])),'terrain_checks':[{k:v for k,v in c.items()if k not in('source_pieces','uncovered_polygons_xz_m')}for c in checks],'side_check':{'status':sc['status'],'contacts':sc['contacts'],'tested_face_pairs':sc['tested_face_owner_pairs']},'surface_seam_jump_failures':seam_bad,'pass':not bad and not sc['contacts']and not seam_bad,'target_kind':'actual_R7_retained_approach_top_named_continuation_to_be_bound'})
   # Check all four gates and retain the shortest passing actual-surface path.
  good=[c for c in choices if c['pass']]
  if good:route=min(good,key=lambda c:c['source_distance_m']);routes.append(route);print('route',u['id'],route['source_distance_m'],flush=True)
  else:unresolved.append({'holding_id':u['id'],'candidate_routes':choices,'reason':'No2m clear full-width terrain route to actual public tops passes'});print('NO_ROUTE',u['id'],len(choices),flush=True)
 write('external_routes.json',{'scene':ref(terrain.SCENE_PATH),'plan':ref(HERE/'grounds_plan.json'),'routes':routes,'unresolved':unresolved,'summary':{'passing_routes':len(routes),'unresolved':len(unresolved),'seconds':time.monotonic()-t},'runtime_player_NPC_replay':'not_run'})
if __name__=='__main__':main()
