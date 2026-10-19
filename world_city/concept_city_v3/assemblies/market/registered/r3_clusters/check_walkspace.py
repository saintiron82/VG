"""A conservative 2.4m-wide customer path graph; geometric source validation only."""
import json,math,hashlib,collections
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.assemblies.market.registered.author import bounds_poly
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[3];ROOT=CITY.parents[1]
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def square(p,r):return[[p[0]-r,p[1]-r],[p[0]+r,p[1]-r],[p[0]+r,p[1]+r],[p[0]-r,p[1]+r]]
def main():
 P=HERE/'resolved_placements.json';d=load(P);plan=load(CITY/'registered_source/plan.json');site=next(s for s in plan['spaces'] if s['id']=='SITE_MARKET')['polygon_xz_m'];obstacles=[];index=geo._SpatialIndex(8)
 for p in d['placements']:
  poly=p.get('footprint_xz_m',bounds_poly(d['assets'][p['asset_key']]['bounds'],p['position_m'],p['yaw_rad']));index.add(len(obstacles),poly);obstacles.append((p['id'],poly))
 def clear(poly):return geo.convex_polygon_contains(site,poly,0) and not any(geo.positive_area_overlap(poly,obstacles[k][1],0) for k in index.candidates(poly))
 radius=1.2;free=set();minx=math.ceil(min(p[0] for p in site));maxx=math.floor(max(p[0] for p in site));minz=math.ceil(min(p[1] for p in site));maxz=math.floor(max(p[1] for p in site))
 for x in range(minx,maxx+1):
  for z in range(minz,maxz+1):
   if clear(square([x,z],radius)):free.add((x,z))
 road=d['access_overlay']['replace_roads'][0];rr=[geo.road_ribbon(a,b,road['width_m']) for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])];seed={p for p in free if any(geo.point_in_convex_polygon(p,r,0) for r in rr)};prev={p:None for p in seed};queue=collections.deque(sorted(seed))
 while queue:
  p=queue.popleft()
  for q in [(p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1)]:
   if q in free and q not in prev:prev[q]=p;queue.append(q)
 routes=[]
 for p in d['placements'][1:]:
  front=p['customer_front_xz_m'];candidates=sorted(((math.dist(front,q),q) for q in prev if math.dist(front,q)<2),key=lambda x:x[0]);link=None
  for distance,q in candidates:
   if distance<1e-8 or clear(geo.road_ribbon(front,q,2.4)):
    link=q;break
  path=[]
  if link is not None:
   q=link;path=[front,list(q)]
   while prev[q] is not None:q=prev[q];path.append(list(q))
  routes.append(dict(stall_id=p['id'],customer_front_xz_m=front,pass_reserved_route=bool(path),path_xz_m=path,width_m=2.4,target_road='MARKET_PROCESSION'))
 report=dict(schema='riverstone.market_customer_walkspace.v1',source_pack_sha256=sha(P),grid_pitch_m=1,conservative_square_radius_m=radius,free_nodes=len(free),connected_nodes=len(prev),stall_routes=routes,passing=sum(r['pass_reserved_route'] for r in routes),stalls=len(routes),minimum_source_aisle_m=2.4,limits=['Source configuration-space check against complete canopy bounds, intentionally more conservative than walking below a canopy.','No NPC, customer or capsule runtime approval.'])
 (HERE/'walkspace_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='stall_routes'}));print('unconnected',[r['stall_id'] for r in routes if not r['pass_reserved_route']]);return report
if __name__=='__main__':main()
