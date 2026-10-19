"""Finite row-owned backland ledger and explicit shared-yard connections."""
import json,math
from collections import deque,Counter
from .author_density import HERE,ROOT,PLAN,ref,write,bbox
from world_city.concept_city_v3.registered_source.author import Domain,box
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import transform,closest
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_source.geometry import triangulate

def clip_half(poly,n,c):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=sum(a[k]*n[k] for k in(0,1))-c;db=sum(b[k]*n[k] for k in(0,1))-c
  if da<=1e-9:out.append(a)
  if (da<0)!=(db<0):
   t=da/(da-db);out.append([a[k]+t*(b[k]-a[k]) for k in(0,1)])
 return out

def run():
 d=json.loads((HERE/'candidate.json').read_text());plan=json.loads(PLAN.read_text());members={p['id']:p for p in d['placements']};region=Domain([d['block']['polygon_xz_m']]);remain=region.polys[:];ledger=[]
 def take(polys,category):
  nonlocal remain
  owned=[]
  for poly in polys:
   nextparts=[]
   for old in remain:
    cut=geo.convex_intersection(old,poly)
    if geo.polygon_area(cut)>1e-7:
     owned.append(cut);nextparts.extend(q for q in geo.convex_difference(old,poly) if geo.polygon_area(q)>1e-7)
    else:nextparts.append(old)
   remain=nextparts
  ledger.append({'category':category,'area_m2':sum(geo.polygon_area(p) for p in owned),'polygons_xz_m':owned});return owned
 take(d['outer_union_polygons_xz_m'],'native_roof_and_body_ownership')
 roads=[]
 for r in plan['roads']:
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):
   p=geo.road_ribbon(a,b,r['width_m'])
   if geo.positive_area_overlap(p,d['block']['polygon_xz_m'],1e-8):roads.append(p)
 take([q for w in plan['water_reservations']['finite_water_polygons'] for q in triangulate(w['polygon_xz_m'])],'retained_finite_water');take(roads,'retained_public_streets')
 take([p for a in d['access_proposals'] for p in a['reserved_connection_polygons_xz_m']],'physical_door_frontage_connections')
 take([p for a in d['court_paths'] for p in a['reserved_polygons_xz_m']],'shared_court_connections')
 take([p['polygon_xz_m'] for p in d['courts']],'two_named_shared_courts')
 grounds=[]
 zones=[('B15E_PRODUCTIVE_BEDS','small_household_productive_beds',[[345,205],[361,205],[361,224],[345,224]],'B15E_SHARED_WELL_COURT'),('B15E_PRIVY_SERVICE','screened_privy_and_refuse_service_strip',[[320,226],[328,226],[328,243],[320,243]],'B15E_SHARED_WELL_COURT'),('B15E_REPAIR_STOCK','cooper_material_and_repair_stockyard',[[342,253],[354,253],[354,268],[342,268]],'B15E_REAR_WORK_COURT')]
 for ident,role,polygon,court in zones:
  pieces=take([polygon],role)
  if pieces:grounds.append({'id':ident,'role':role,'polygons_xz_m':pieces,'area_m2':sum(geo.polygon_area(p) for p in pieces),'shared_court_id':court,'facility_intent':{'small_household_productive_beds':'Four to eight raised beds with a clear maintenance walk; no new floor plane.','screened_privy_and_refuse_service_strip':'Two small screened privy sheds and covered refuse bins; final facility footprints require placement checks.','cooper_material_and_repair_stockyard':'Low timber stacks and repair stands outside the3 m court link.'}[role]})
 sites=[]
 for g in d['groups']:
  points=[]
  for ident in g['member_ids']:
   p=members[ident];origin=[p['position_m'][0],p['position_m'][2]];b=p['actual_body_bounds_local_m'];points.append(transform([0,b['min'][2]-2],origin,p['yaw_rad']))
  sites.append((g['id'],[sum(p[k] for p in points)/len(points) for k in(0,1)]))
 bb=bbox(d['block']['polygon_xz_m']);assigned=[]
 for ident,site in sites:
  cell=[[bb[0]-1,bb[1]-1],[bb[2]+1,bb[1]-1],[bb[2]+1,bb[3]+1],[bb[0]-1,bb[3]+1]]
  for other,q in sites:
   if other==ident:continue
   n=[2*(q[k]-site[k]) for k in(0,1)];c=sum(v*v for v in q)-sum(v*v for v in site);cell=clip_half(cell,n,c)
   if not cell:break
  polys=[v for p in remain if geo.polygon_area(v:=geo.convex_intersection(p,cell))>1e-7]
  if polys:
   grounds.append({'id':ident+':SHARED_WORKYARD','role':'row_owned_shared_workyard_and_drying_ground','owner_row_group_id':ident,'polygons_xz_m':polys,'area_m2':sum(geo.polygon_area(p) for p in polys),'facility_intent':'Shared household/workshop rear ground with washing, drying and hand-repair space. No automatic green-park conversion.'});assigned.extend(polys)
 ledger.append({'category':'row_owned_shared_workyards','area_m2':sum(geo.polygon_area(p) for p in assigned),'polygons_xz_m':assigned})
 # Full-width1.8m paths use a deterministic1m free-space grid, seeded from public lanes.
 roof=Domain(d['outer_union_polygons_xz_m']+[q for w in plan['water_reservations']['finite_water_polygons'] for q in triangulate(w['polygon_xz_m'])]);walkable={};seeds=[];roadmap={r['id']:r for r in plan['roads']};road_index=geo._SpatialIndex(32);roadrecords=[]
 for r in plan['roads']:
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):road_index.add(len(roadrecords),geo.road_ribbon(a,b,r['width_m']));roadrecords.append((r,a,b))
 for ix in range(math.floor(bb[0]),math.ceil(bb[2])):
  for iz in range(math.floor(bb[1]),math.ceil(bb[3])):
   q=[ix+.5,iz+.5];square=box(q,1.8,1.8)
   if not region.contains(square) or roof.hits(square):continue
   key=(ix,iz);walkable[key]=q
   for i in road_index.candidates([q]):
    r,a,b=roadrecords[i];dist,hit,_,_=closest(q,[a,b])
    if dist<=r['width_m']/2-.9+1e-7:seeds.append((key,r['id'],hit));break
 parent={k:(None,rid,q) for k,rid,q in seeds};queue=deque(parent)
 while queue:
  key=queue.popleft()
  for dx,dz in[(1,0),(-1,0),(0,1),(0,-1)]:
   k=(key[0]+dx,key[1]+dz)
   if k in walkable and k not in parent:parent[k]=(key,parent[key][1],parent[key][2]);queue.append(k)
 paths=[];unresolved=[]
 for ground in grounds:
  polys=ground['polygons_xz_m'];largest=max(polys,key=geo.polygon_area);target=[sum(p[k] for p in largest)/len(largest) for k in(0,1)];candidates=[k for k in parent if any(geo.point_in_convex_polygon(walkable[k],p,1e-7) for p in polys)]
  if not candidates:
   ground['access_status']='narrow_unwalkable_service_margin; accessed_from_adjoining_owned_yard';ground['access_ids']=[p['id'] for p in d['court_paths'] if p['owner_id']==ground.get('shared_court_id')];unresolved.append(ground['id']);continue
  key=min(candidates,key=lambda k:math.dist(walkable[k],target));line=[walkable[key]];cursor=key
  while parent[cursor][0] is not None:cursor=parent[cursor][0];line.append(walkable[cursor])
  rid=parent[key][1];_,end,_,_=closest(line[-1],roadmap[rid]['polyline_xz_m']);line.append(end)
  # Greedy line-of-sight simplification keeps the actual full-width ribbon clear.
  clean=[line[0]];i=0
  while i<len(line)-1:
   chosen=i+1
   for j in range(len(line)-1,i,-1):
    if math.dist(line[i],line[j])<1e-7:continue
    rib=geo.road_ribbon(line[i],line[j],1.8)
    if not roof.hits(rib):chosen=j;break
   clean.append(line[chosen]);i=chosen
  ident=ground['id']+':SERVICE_ACCESS';paths.append({'id':ident,'owner_ground_id':ground['id'],'width_m':1.8,'polyline_xz_m':clean,'connects_road_id':rid,'reserved_polygons_xz_m':[geo.road_ribbon(a,b,1.8) for a,b in zip(clean,clean[1:]) if math.dist(a,b)>1e-7],'finished_floor_y_m':2.5,'kind':'pedestrian_shared_yard_service_path'});ground['access_ids']=[ident];ground['access_status']='explicit_full_width_connection_to_retained_public_lane'
 total=sum(r['area_m2'] for r in ledger);report={'schema':'riverstone.block015_east_owned_grounds.v1','candidate':ref(HERE/'candidate.json'),'block_id':d['block']['id'],'gross_block_area_m2':d['block']['area_m2'],'assigned_area_m2':total,'area_accounting_delta_m2':total-d['block']['area_m2'],'grounds':grounds,'paths':paths,'ownership_ledger':ledger,'unwalkable_narrow_margin_ids':unresolved,'no_new_floor_planes':True,'status':'finite source ownership and pedestrian reservations; facility geometry and controller tests pending'};assert abs(report['area_accounting_delta_m2'])<1e-4;write(HERE/'owned_grounds.json',report);print(json.dumps({'grounds':len(grounds),'paths':len(paths),'narrow_margin_ids':unresolved,'assigned_area_m2':total,'delta_m2':report['area_accounting_delta_m2'],'areas':{r['category']:r['area_m2'] for r in ledger}},indent=2))
if __name__=='__main__':run()
