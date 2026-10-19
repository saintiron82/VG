"""Bounded door-to-lane routing with actual native obstacles and frozen terrain."""
import heapq
from collections import Counter
import numpy as np
from scipy import ndimage
from .design import *
from .ground import ActualGround,geo,BOUNDS
GRID=.5
NX=round((BOUNDS[2]-BOUNDS[0])/GRID);NZ=round((BOUNDS[3]-BOUNDS[1])/GRID)
XS=BOUNDS[0]+(np.arange(NX)+.5)*GRID;ZS=BOUNDS[1]+(np.arange(NZ)+.5)*GRID

def raster(polys,touch=False):
 out=np.zeros((NZ,NX),bool)
 for p in polys:
  x0=max(0,int(math.floor((min(q[0]for q in p)-BOUNDS[0])/GRID)));x1=min(NX,int(math.ceil((max(q[0]for q in p)-BOUNDS[0])/GRID)))
  z0=max(0,int(math.floor((min(q[1]for q in p)-BOUNDS[1])/GRID)));z1=min(NZ,int(math.ceil((max(q[1]for q in p)-BOUNDS[1])/GRID)))
  if x0>=x1 or z0>=z1:continue
  hit=np.ones((z1-z0,x1-x0),bool);sgn=1 if geo.signed_polygon_area(p)>0 else -1
  for a,b in zip(p,p[1:]+p[:1]):
   dx,dz=b[0]-a[0],b[1]-a[1];val=sgn*(dx*(ZS[z0:z1,None]-a[1])-dz*(XS[None,x0:x1]-a[0]));margin=-GRID*.5*(abs(dx)+abs(dz)) if touch else 0;hit&=val>=margin-1e-8
  out[z0:z1,x0:x1]|=hit
 return out

def cell(q):return [int((q[1]-BOUNDS[1])/GRID),int((q[0]-BOUNDS[0])/GRID)]
def point(q):return [float(XS[q[1]]),float(ZS[q[0]])]
def circle(q,width):
 r=width/2/math.cos(math.pi/16);return [[q[0]+r*math.cos(i*math.pi/8),q[1]+r*math.sin(i*math.pi/8)]for i in range(16)]
def ribbons(line,width):return [geo.road_ribbon(a,b,width)for a,b in zip(line,line[1:])if math.dist(a,b)>1e-8]+[circle(q,width)for q in line[1:-1]]
def astar(free,start,end):
 start=tuple(start);end=tuple(end);heap=[(0,0,start)];cost={start:0};prev={}
 while heap:
  _,g,q=heapq.heappop(heap)
  if g!=cost[q]:continue
  if q==end:
   path=[q]
   while q in prev:q=prev[q];path.append(q)
   path=path[::-1];out=[path[0]]
   for i in range(1,len(path)-1):
    a,b,c=path[i-1:i+2]
    if(b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):out.append(b)
   return [point(p)for p in out+[path[-1]]]
  z,x=q
  for dz,dx in[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   nz,nx=z+dz,x+dx
   if not(0<=nz<NZ and 0<=nx<NX)or not free[nz,nx]:continue
   if dz and dx and(not free[z,nx]or not free[nz,x]):continue
   p=(nz,nx);ng=g+(math.sqrt(2)if dz and dx else 1)
   if ng<cost.get(p,math.inf):cost[p]=ng;prev[p]=q;heapq.heappush(heap,(ng+math.dist(p,end),ng,p))
 return None

def nearest_free(free,q,maxdist=3):
 zz,xx=np.where(free);dd=(XS[xx]-q[0])**2+(ZS[zz]-q[1])**2;i=int(np.argmin(dd));return (int(zz[i]),int(xx[i]))if dd[i]<=maxdist**2 else None

def run():
 selection=load(HERE/'selection.json');native=load(HERE/'native_geometry.json');ground=ActualGround();holds={h['id']:h for h in selection['selected_holdings']};original={r['holding_id']:r for r in load(PLAN/'access_review.json')['connections']};routes=[];gaps=[];external=[];allobstacles=[q for p in native['placements']for q in p['native_walking_obstacles_xz_m']];obs=raster(allobstacles,True)
 for hid,h in holds.items():
  old=original[hid];line=old['polyline_xz_m'];ps=ribbons(line,old['width_m']);a=ground.audit(ps);external.append(dict(id=hid+':LOWER_CONTOUR',holding_id=hid,width_m=old['width_m'],polyline_xz_m=line,ribbon_and_join_polygons_xz_m=ps,connects_source_road_id=old['source_target_road_id'],ground_audit=a,source=ref(PLAN/'access_review.json'),gate=old['gate_candidates'][0],gate_status='Source portal reservation; jambs and opening are not yet native-authored',terrain_status='source_candidate_exact_frozen_ground_screened'))
 for d in native['actual_doors']:
  hid=d['holding_id'];h=holds[hid];old=original[hid];w=d['exterior_route_width_m'];allowed=raster(h['polygon_parts_xz_m']+ribbons(old['polyline_xz_m'],old['width_m']));free=allowed&~obs;distance=ndimage.distance_transform_edt(free)*GRID;clear=distance>=w/2+GRID*math.sqrt(2);lip=d['threshold_lip_xz_m'];n=d['outward_xz'];approach=[lip[k]+n[k]*(w/2+.65)for k in (0,1)];start=nearest_free(clear,approach);end=nearest_free(clear,old['polyline_xz_m'][0]);route=astar(clear,start,end)if start and end else None
  if route is None:gaps.append(dict(door_id=d['id'],start=approach,target=old['polyline_xz_m'][0],reason='No finite full-width internal connection under actual native obstacles'));continue
  line=[lip,approach]+route+[old['polyline_xz_m'][0]];line=[q for i,q in enumerate(line)if i==0 or math.dist(q,line[i-1])>1e-7];ps=ribbons(line,w);hits=[]
  for i,p in enumerate(ps):
   for j,q in enumerate(allobstacles):
    area=geo.intersection_area(p,q)
    if area>1e-6:hits.append([i,j,area])
  if hits:gaps.append(dict(door_id=d['id'],reason='Actual native walking overlap in exact ribbon/join polygons',overlaps=hits));continue
  a=ground.audit(ps);routes.append(dict(id=d['id']+':EXTERIOR_LINK',door_id=d['id'],parcel_id=d['parcel_id'],holding_id=hid,width_m=w,polyline_xz_m=line,ribbon_and_join_polygons_xz_m=ps,length_m=sum(math.dist(a,b)for a,b in zip(line,line[1:])),connects_route_id=hid+':LOWER_CONTOUR',native_walking_overlap_area_m2=0,ground_audit=a,status='finite_full_width_exterior_reservation; independent terrain/native entrance and capsule review pending'))
 out=dict(schema='riverstone.working_ranges.access.v1',native_geometry=ref(HERE/'native_geometry.json'),selection=ref(HERE/'selection.json'),local_grid_pitch_m=GRID,center_clearance='width/2 + 0.707107 m; no diagonal corner cutting; exact polygon/native walking intersection recheck',external_routes=external,internal_routes=routes,unresolved_doors=gaps,summary=dict(actual_door_count=len(native['actual_doors']),connected_actual_doors=len(routes),unresolved_actual_doors=len(gaps),external_links=len(external),all_native_walking_obstacles_clear=not gaps),limits=['Portals are actual native closed exterior leaves, not an interior or population certificate.','The original external lane is preserved without shortcuts; gates remain named source reservations.','Ground coverage includes overlapping route polygons by multiplicity; each polygon is tested independently.','Source paths are not activated terrain or engine navigation.']);write(HERE/'access_handoff.json',out);print(json.dumps(out['summary'],indent=2));print(json.dumps(gaps,indent=2)[:4000]);return out
if __name__=='__main__':run()
