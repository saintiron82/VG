"""Three retained garden continuations, actual native portals and finite floors."""
from pathlib import Path
import sys,json,math,time,collections
from scipy.spatial import ConvexHull
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT.parent));sys.path.insert(0,str(OUT.parent/'retained_garden_access_r02'))
from resolve_pack import *
from diagnose_actual_floors import ActualGardenIndex
OUT=Path(__file__).resolve().parent

def write(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
def circle(p):return [[p[0]+math.cos(k*math.pi/4),p[1]+math.sin(k*math.pi/4)]for k in range(8)]
def ribbons(pts):return b.ribbon(pts,2)+[circle(p)for p in pts[1:-1]]
class Support(ActualGardenIndex):
 def __init__(self,scene,windows,vs):self.terrain=terrain.TriangleIndex(scene,windows);self.native=terrain.TriangleIndex({'surfaces':{'actual_native_floor':vs}},windows)
def main():
 started=time.monotonic();projection=load(BASE/'actual_native_projection.json');scene=terrain.load_scene();landscape=load(CITY/'assemblies/landscape/registered/resolved_placements.json');out=[];sources=[ref(BASE/'actual_native_projection.json')];placements=[dict(p,source=projection['assets'][p['asset_key']]['source'],cache=projection['assets'][p['asset_key']]['cache'])for p in projection['instances']]
 for path in [BASE/'resolved_connected_placements.json',OUT.parent/'resolved_residual_placements.json',OUT.parent/'residual_extensions_r02/resolved_extension_placements.json',CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json']:
  sources.append(ref(path));placements+=load(path)['placements']
 cache={};arr=np.load(OUT.parent/'all_owner_terrain_raster.npz')
 for group,floor,box,prefixes in [('cathedral',14,[110,-300,380,-70],('CLERGY_CLOISTER_GARDEN:',)),('monastery',8,[-450,-100,-220,160],('MONASTERY_ORCHARD:','MONASTERY_HERB_GARDEN:'))]:
  window=b.rect(*box);bodies=[];floors=[];vs=[];native_sources=[]
  for p in placements:
   if abs(p['position_m'][1]-floor)>20:continue
   path=p['cache']['path']
   if path not in cache:cache[path]=load(ROOT/path)
   mesh=cache[path];py=p['position_m'][1];bounds=mesh['bounds'];localbox=b.rect(bounds['min'][0],bounds['min'][2],bounds['max'][0],bounds['max'][2]);worldbox=b.xform(localbox,p)
   if geo.intersection_area(worldbox,window)<1e-8:continue
   if bounds['min'][1]+py>floor+2.2 or bounds['max'][1]+py<floor-1e-7:continue
   native_sources.append(dict(id=p['id'],source=p['source'],cache=p['cache']))
   for q in slab_rectangles(mesh,floor-py+.01,floor-py+2.2):
    q=b.xform(q,p)
    if geo.intersection_area(q,window)>1e-8:bodies.append(dict(id=p['id'],polygon_xz_m=q))
   for q in horizontal(mesh,floor-py,True):
    q=b.xform(q,p)
    if geo.intersection_area(q,window)>1e-8:
     floors.append(q)
     for t in terrain.fan_upward([[x,floor,z]for x,z in q]):vs.extend(t)
  idx=Support(scene,[window],vs);sides=SideIndex(scene,[window]);bi=geo._SpatialIndex(8)
  for i,r in enumerate(bodies):bi.add(i,r['polygon_xz_m'])
  def contacts(polys):
   hits=[]
   for q in polys:
    for i in bi.candidates(q):
     pp=geo.convex_intersection(q,bodies[i]['polygon_xz_m']);a=geo.polygon_area(pp)
     if a>1e-7:hits.append(dict(id=bodies[i]['id'],area_m2=a,polygon_xz_m=pp))
   return hits
  def check(route,pts):
   pols=ribbons(pts);hits=contacts(pols);checks=[terrain.audit_polygon(idx,q,floor)for q in pols];side=sides.audit([dict(id=route['id'],polygon_xz_m=q,floor_y_m=floor)for q in pols]);return dict(id=route['id']+':r03',source_route_id=route['id'],group=group,floor_y_m=floor,width_m=2,polyline_xz_m=pts,ribbon_polygons_xz_m=pols,surface_checks=checks,native_contacts=hits,bank_contacts=side['contacts'],passes=all(c['passes_existing_surface']for c in checks)and not hits and not side['contacts'])
  graphpath=BASE/f'entry_graph_{group}.json';graph=load(graphpath)
  def bind(row):
   pt=row['polyline_xz_m'][-1];seeds=[i for i,r in enumerate(graph['rows'])if str(i)in graph['parent']and geo.point_in_convex_polygon(pt,r['polygon_xz_m'])];chain=[]
   if seeds:
    i=seeds[0]
    while i is not None:chain.append(i);i=graph['parent'][str(i)]
   named=[s for s in graph['road_seams']if chain and geo.intersection_area(graph['rows'][chain[-1]]['polygon_xz_m'],s['polygon_xz_m'])>1e-8];row['public_binding']=dict(graph_source=ref(graphpath),actual_terminal_triangle_ids=[graph['rows'][i]['triangle_index']for i in seeds],continuation_triangle_ids=[graph['rows'][i]['triangle_index']for i in chain],named_public_road_ids=sorted({s['road_id']for s in named}),status='PASS_ACTUAL_NAMED_RETAINED_CONTINUATION'if named else'PENDING_NAMED_CONTINUATION');row['passes']=row['passes']and bool(named);return row
  print(group,'geometry',len(bodies),len(floors),flush=True)
  expanded=[]
  for rr in bodies:
   pts=np.array([[v[0]+1.55*math.cos(k*math.pi/4),v[1]+1.55*math.sin(k*math.pi/4)]for v in rr['polygon_xz_m']for k in range(8)]);expanded.append(pts[ConvexHull(pts).vertices].tolist())
  body=b.mask([r['polygon_xz_m']for r in bodies],True);exact_body_clear=~b.mask(expanded);valid=np.isfinite(arr['height'])&(np.abs(arr['height']-floor)<1e-5)&(arr['grade']<1e-5);valid|=b.mask(floors);valid&=~body;valid&=b.mask([window]);walk=ndimage.distance_transform_edt(valid)>=1.5;walk&=exact_body_clear
  targetparts=[r['polygon_xz_m']for i,r in enumerate(graph['rows'])if str(i)in graph['parent']and math.hypot(*r['plane_y_xz_m'][:2])<1e-5 and all(abs(terrain.common.height(r['plane_y_xz_m'],q)-floor)<1e-5 for q in r['polygon_xz_m'])];target=b.mask(targetparts)&walk;parent={};todo=collections.deque()
  for z,x in np.argwhere(target):parent[(int(z),int(x))]=None;todo.append((int(z),int(x)))
  while todo:
   z,x=todo.popleft()
   for dz,dx in((1,0),(-1,0),(0,1),(0,-1)):
    k=(z+dz,x+dx)
    if 0<=k[0]<b.NZ and 0<=k[1]<b.NX and walk[k]and k not in parent:parent[k]=(z,x);todo.append(k)
  for route in landscape['external_connections']:
   if not route['id'].startswith(prefixes):continue
   candidates=[];rejected=[]
   if group=='cathedral':
    portal=next(p for p in placements if p['id']=='cathedral_registered:west_cloister_walk_0');portalpoints=b.xform([[0,6],[0,-6]],portal);pts=route['polyline_xz_m'][:2]+[[255,-232]]+portalpoints+[[234.5,-219.5]];c=bind(check(route,pts));candidates.append(c);print(route['id'],'portal',c['passes'],'missing',sum(r['missing_area_m2']for r in c['surface_checks']),'bodies',len(c['native_contacts']),'banks',len(c['bank_contacts']),flush=True)
   if not any(c['passes']for c in candidates):
    prefix=route['polyline_xz_m'][:2];anchor=prefix[-1];reachable=sorted((math.dist(anchor,[b.BOUNDS[0]+x+.5,b.BOUNDS[1]+z+.5]),z,x)for z,x in parent if math.dist(anchor,[b.BOUNDS[0]+x+.5,b.BOUNDS[1]+z+.5])<30)
    for ci,(_,z,x)in enumerate(reachable[:200]):
     points=[];pos=(z,x)
     while pos is not None:points.append([b.BOUNDS[0]+pos[1]+.5,b.BOUNDS[1]+pos[0]+.5]);pos=parent[pos]
     # Exact body-clear straight segments simplify grid stairs; finite floor
     # and bank checks below still decide acceptance.
     smooth=list(prefix);last=anchor;at=0
     while at<len(points):
      chosen=at
      for k in range(len(points)-1,at-1,-1):
       if math.dist(last,points[k])<1e-8:chosen=k;break
       if not contacts(b.ribbon([last,points[k]],2)+[circle(points[k])]):chosen=k;break
      smooth.append(points[chosen]);last=points[chosen];at=chosen+1
     hits=contacts(ribbons(smooth))
     if hits:
      if len(rejected)<3:rejected.append(dict(polyline_xz_m=smooth,native_contacts=hits))
      continue
     c=bind(check(route,smooth));candidates.append(c)
     if c['passes']:break
     if len(candidates)>=15:break
    print(route['id'],'reachable',len(reachable),'tested',len(candidates),'pass',any(c['passes']for c in candidates),flush=True)
   out.append(dict(source_route_id=route['id'],candidates=candidates,rejected_route_diagnoses=rejected,native_sources=native_sources))
  write(group+'_native_geometry.json',dict(floor_y_m=floor,window=window,bodies=bodies,floor_polygons_xz_m=floors,sources=native_sources))
 write('route_search.json',dict(status='ACTUAL_NATIVE_ROUTE_SEARCH',sources=sources,routes=out,seconds=time.monotonic()-started));print('complete',time.monotonic()-started,flush=True)
if __name__=='__main__':main()
