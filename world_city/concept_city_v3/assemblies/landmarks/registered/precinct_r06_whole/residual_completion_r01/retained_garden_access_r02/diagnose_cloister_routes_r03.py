"""Find full-width exterior garden continuations from actual native floor/body geometry."""
from pathlib import Path
import sys,json,math,time,heapq,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT.parent))
from resolve_pack import *
from connect_routes import simplify
from diagnose_actual_floors import ActualGardenIndex
OUT=Path(__file__).resolve().parent
class AllFlatNativeIndex(ActualGardenIndex):
 def __init__(self,scene,windows,vs):
  self.terrain=terrain.TriangleIndex(scene,windows);self.native=terrain.TriangleIndex({'surfaces':{'retained_actual_native_floor':vs}},windows)
def main():
 t=time.monotonic();floor=14;projection=load(BASE/'actual_native_projection.json');bodies=[];floorparts=[];vs=[];cache={};sources=[]
 def consume(p,a):
  cp=a['cache']['path'];py=p['position_m'][1]
  if abs(py-floor)>20:return
  if cp not in cache:cache[cp]=load(ROOT/cp)
  mesh=cache[cp];lo,hi=mesh['bounds']['min'][1]+py,mesh['bounds']['max'][1]+py
  if lo>floor+2.2 or hi<floor-1e-5:return
  for q in slab_rectangles(mesh,floor-py+.01,floor-py+2.2):
   w=b.xform(q,p)
   if any(110<x<380 and -300<z<-70 for x,z in w):bodies.append(dict(id=p['id'],polygon_xz_m=w))
  for q in horizontal(mesh,floor-py,True):
   w=b.xform(q,p)
   if not any(110<x<380 and -300<z<-70 for x,z in w):continue
   floorparts.append(w)
   for tri in terrain.fan_upward([[x,floor,z]for x,z in w]):vs.extend(tri)
 for p in projection['instances']:consume(p,projection['assets'][p['asset_key']])
 for path in [BASE/'resolved_connected_placements.json',OUT.parent/'resolved_residual_placements.json',OUT.parent/'residual_extensions_r02/resolved_extension_placements.json',CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json']:
  pack=load(path);sources.append(ref(path))
  for p in pack['placements']:consume(p,p)
 arr=np.load(OUT.parent/'all_owner_terrain_raster.npz');valid=np.isfinite(arr['height'])&(np.abs(arr['height']-floor)<1e-5)&(arr['grade']<1e-5);valid|=b.mask(floorparts);body=b.mask([r['polygon_xz_m']for r in bodies],True);valid&=~body;valid&=b.mask([b.rect(110,-300,380,-70)]);walk=ndimage.distance_transform_edt(valid)>=1.5;walk&=~b.buffer(body,1.5)
 graph=load(BASE/'entry_graph_cathedral.json');targetparts=[r['polygon_xz_m']for i,r in enumerate(graph['rows'])if str(i)in graph['parent']and math.hypot(*r['plane_y_xz_m'][:2])<1e-5 and all(abs(terrain.common.height(r['plane_y_xz_m'],q)-floor)<1e-5 for q in r['polygon_xz_m'])];target=b.mask(targetparts)&walk
 parent={};todo=collections.deque()
 for z,x in np.argwhere(target):parent[(int(z),int(x))]=None;todo.append((int(z),int(x)))
 while todo:
  z,x=todo.popleft()
  for dz,dx in((1,0),(-1,0),(0,1),(0,-1)):
   k=(z+dz,x+dx)
   if 0<=k[0]<b.NZ and 0<=k[1]<b.NX and walk[k]and k not in parent:parent[k]=(z,x);todo.append(k)
 scene=terrain.load_scene();idx=AllFlatNativeIndex(scene,[b.rect(110,-300,380,-70)],vs);sides=SideIndex(scene,[b.rect(110,-300,380,-70)]);bi=geo._SpatialIndex(16)
 for i,r in enumerate(bodies):bi.add(i,r['polygon_xz_m'])
 src=load(CITY/'assemblies/landscape/registered/resolved_placements.json');out=[]
 for route in src['external_connections']:
  if not route['id'].startswith(('CLERGY_CEMETERY:','CLERGY_CLOISTER:','CLERGY_CLOISTER_GARDEN:')):continue
  gate=route['polyline_xz_m'][0];prefix=route['polyline_xz_m'][:2] if 'CLOISTER' in route['id'] else [gate];anchor=prefix[-1];reachable=[]
  for z,x in parent:
   q=[b.BOUNDS[0]+x+.5,b.BOUNDS[1]+z+.5];d=math.dist(anchor,q)
   if d<30:reachable.append((d,z,x))
  candidates=[]
  for _,z,x in sorted(reachable)[:500]:
   points=list(prefix);pos=(z,x)
   while pos is not None:
    points.append([b.BOUNDS[0]+pos[1]+.5,b.BOUNDS[1]+pos[0]+.5]);pos=parent[pos]
   pts=simplify(points);polys=b.ribbon(pts,2)+[b.rect(p[0]-1,p[1]-1,p[0]+1,p[1]+1)for p in pts[1:]];hits=[]
   for q in polys:
    for i in bi.candidates(q):
     ar=geo.intersection_area(q,bodies[i]['polygon_xz_m'])
     if ar>1e-7:hits.append(dict(id=bodies[i]['id'],area_m2=ar))
   if hits:
    if len(candidates)<3:candidates.append(dict(id=route['id'],polyline_xz_m=pts,native_contacts=hits,passes=False));print('blocked',route['id'],hits[:2],flush=True)
    continue
   checks=[terrain.audit_polygon(idx,q,floor)for q in polys];sc=sides.audit([dict(id=route['id'],polygon_xz_m=q,floor_y_m=floor)for q in polys]);ok=all(c['passes_existing_surface']for c in checks)and not sc['contacts'];c=dict(id=route['id']+':exterior_r02',source_route_id=route['id'],width_m=2,floor_y_m=floor,polyline_xz_m=pts,ribbon_polygons_xz_m=polys,checks=checks,native_contacts=hits,bank_contacts=sc['contacts'],passes=ok);candidates.append(c)
   if ok:break
  row=dict(id=route['id'],reachable_gate_candidates=len(reachable),routes=candidates);out.append(row);print(route['id'],'reachable',len(reachable),'tested',len(candidates),'pass',any(c['passes']for c in candidates),flush=True)
 report=dict(status='CANDIDATE_ROUTE_SEARCH',sources=sources,body_parts=len(bodies),floor_parts=len(floorparts),reachable_cells=len(parent),routes=out,seconds=time.monotonic()-t);(OUT/'cloister_route_search_r03.json').write_text(json.dumps(report,indent=2)+'\n');print('seconds',report['seconds'],flush=True)
if __name__=='__main__':main()
