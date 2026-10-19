#!/usr/bin/env python3
"""Clean concept-city v3 source plan: roads/land use first, finite massing second."""
from __future__ import annotations
import copy,hashlib,json,math,sys
from collections import Counter,defaultdict,deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as g
HERE=Path(__file__).parent
BOUNDARY=[[-430,-330],[-240,-380],[120,-370],[370,-325],[455,-140],[455,140],[375,335],[190,380],[-190,375],[-390,300],[-460,100],[-465,-150]]
CANAL=[[-511.42857142857144,420],[-460,300],[-340,280],[-180,280],[-30,270],[130,260],[270,270],[350,310],[370,330],[390,345],[410,365],[455.29411764705884,420]]
CANAL_LEVELS=[1.9657142857142857,1.9,1.7,1.5,1.3,1.1,.8,.5,-.3,-.4,-1.2,-1.9011764705882355]
PALETTE={'castle':'#8f877d','water_gardens':'#899e70','cathedral':'#a6a5aa','noble':'#a9b58d','merchants':'#bb9974','civic':'#d4c098','monastery':'#a8b58b','old_town':'#b49378','poor':'#977863','craft':'#a88e72','port':'#9d9d87'}

def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def area(p):return g.polygon_area(p)
def center(p):return [sum(v[i] for v in p)/len(p) for i in (0,1)]
def hullbox(p):return [min(v[0] for v in p),min(v[1] for v in p),max(v[0] for v in p),max(v[1] for v in p)]
def clean(p):
 out=[]
 for v in p:
  if not out or math.dist(v,out[-1])>1e-7:out.append(v)
 if len(out)>1 and math.dist(out[0],out[-1])<1e-7:out.pop()
 return out if len(out)>2 and area(out)>1e-6 else []
def footprint(pos,w,d,yaw=0):return g.transformed_aabb_xz_m({'min':[-w/2,0,-d/2],'max':[w/2,1,d/2]},[pos[0],0,pos[1]],yaw)
def transform(p,pos,yaw):return [pos[0]+math.cos(yaw)*p[0]+math.sin(yaw)*p[1],pos[1]-math.sin(yaw)*p[0]+math.cos(yaw)*p[1]]
def nearest(point,roads):
 result=[]
 for r in roads:
  for j,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dz)/(dx*dx+dz*dz)))
   q=[a[0]+t*dx,a[1]+t*dz];result.append((math.dist(point,q),r['id'],q))
 return sorted(result)
def intersect_segments(a,b,c,d):
 ux,uz=b[0]-a[0],b[1]-a[1];vx,vz=d[0]-c[0],d[1]-c[1];den=ux*vz-uz*vx
 if abs(den)<1e-10:return None
 t=((c[0]-a[0])*vz-(c[1]-a[1])*vx)/den;u=((c[0]-a[0])*uz-(c[1]-a[1])*ux)/den
 return ([a[0]+t*ux,a[1]+t*uz],t,u) if -1e-8<=t<=1+1e-8 and -1e-8<=u<=1+1e-8 else None

def build():
 from world_city.concept_city_v3.source.control_streets import ROADS
 from world_city.concept_city_v3.source.block_geometry import faces,triangulate,inside
 from world_city.concept_city_v3.source.ground_program import subtract,add_ground_program
 old=json.loads((HERE/'rejected_r0/plan.json').read_text())
 plan={k:copy.deepcopy(old[k]) for k in ['schema','coordinate_system','boundary_xz_m','districts','spaces','water_reservations','source_policy']}
 plan.update(revision='v3_r1_contour_blocks',status='second_source_blockout_for_review',roads=copy.deepcopy(ROADS),buildings=[],plots=[],paths=[],gates=[],bridges=[],blocks=[])
 plan['source_policy']['rejected_predecessor']='source/rejected_r0; orthogonal layout rejected by visual review'
 plan['water_reservations'].update(service_canal_polyline_xz_m=CANAL,service_water_levels_m=CANAL_LEVELS,spring_feeder_polyline_xz_m=[[30,-510],[30,-440],[0,-370],[0,-358]],spring_feeder_levels_m=[24,22,17,16],spring_feeder_reserve_width_m=8,reservoir_water_polygon_xz_m=rect(-48,-358,48,-312))
 roads=plan['roads'];road_ribbons=[(r['id'],g.road_ribbon(a,b,r['width_m'])) for r in roads for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]
 canal_ribbons=[g.road_ribbon(a,b,14) for a,b in zip(CANAL,CANAL[1:])]
 protected=[s['polygon_xz_m'] for s in plan['spaces']]
 rejected=[];plotpolys=[];buildingpolys=[]
 # Preserve the agreed estate frames, their private routes, and landmark masses.
 for p in old['plots']:
  if p['property_type']=='noble_estate':plan['plots'].append(copy.deepcopy(p));plotpolys.append(p['polygon_xz_m'])
 noble_ids={p['id'] for p in plan['plots']}
 for b in old['buildings']:
  if b.get('plot_id') in noble_ids or b.get('replace_by_assembly_key'):
   plan['buildings'].append(copy.deepcopy(b));buildingpolys.append(b['footprint_xz_m'])
 bids={b['id'] for b in plan['buildings']}
 for p in old['paths']:
  if p.get('owner_plot_id') in noble_ids or p.get('owner_building_id') in bids:
   p=copy.deepcopy(p)
   if p.get('owner_building_id') and not p.get('owner_plot_id'):
    b=next(b for b in plan['buildings'] if b['id']==p['owner_building_id'])
    _,rid,q=nearest(b['entrance_xz_m'],[r for r in roads if r['id']==b['road_id']])[0];p['road_id']=rid
    p['polyline_xz_m']=[b['entrance_xz_m'],q]
    if b['id']=='B_CATHEDRAL_CLOISTER':p['polyline_xz_m']=[b['entrance_xz_m'],[340,-215],[340,-170],[300,-140]]
    if b['id']=='B_MONASTERY_CHAPEL':p['polyline_xz_m']=[b['entrance_xz_m'],[-319,182],[-319,220],[-190,220]]
   plan['paths'].append(p)
 # Landmark access is reserved before ordinary street fronts, never added after them.
 access_ribbons=[g.road_ribbon(a,b,p['width_m']+.4) for p in plan['paths'] for a,b in zip(p['polyline_xz_m'],p['polyline_xz_m'][1:]) if math.dist(a,b)>1e-6]
 protected.extend(access_ribbons)
 # Planar road faces give real irregular blocks. Their finite buildable remainder
 # excludes all routes, civic precincts, estates and both water reservations.
 obstacles=protected+plotpolys+canal_ribbons+[p for _,p in road_ribbons]
 for i,(poly,edge_ids) in enumerate(faces(roads,BOUNDARY)):
  triangles=triangulate(poly);net=[q for t in triangles for q in subtract(t,obstacles)]
  amount=sum(area(q) for q in net)
  if amount<80:continue
  largest=max(net,key=area);c=center(largest);district_rec=next(d for d in plan['districts'] if g.point_in_convex_polygon(c,d['polygon_xz_m'],1e-4))
  rec={'id':f'BLOCK_{i:03d}','polygon_xz_m':poly,'triangulated_polygon_xz_m':triangles,'buildable_polygons_xz_m':net,'buildable_area_m2':amount,'district_id':district_rec['id'],'role':district_rec['role'],'boundary_road_ids':sorted(set(edge_ids)-{'WALL'}),'plot_ids':[],'interior_path_ids':[]}
  plan['blocks'].append(rec)
  # A two-entry bent alley is selected from actual boundary-road midpoints,
  # only where its whole ribbon remains in this face and clears reservations.
  if amount<1600 or district_rec['role'] in ('noble','monastery','port','castle'):continue
  endpoints=[]
  for a,b,rid in zip(poly,poly[1:]+poly[:1],edge_ids):
   if rid!='WALL' and math.dist(a,b)>12:endpoints.append(([(a[0]+b[0])/2,(a[1]+b[1])/2],rid))
  options=[]
  for ai,(a,ar) in enumerate(endpoints):
   for b,br in endpoints[ai+1:]:
    if math.dist(a,b)<35:continue
    mid=[(a[0]+b[0])/2+2,(a[1]+b[1])/2-1.5]
    path=[a,mid,b]
    if not all(inside([u[0]+t*(v[0]-u[0]),u[1]+t*(v[1]-u[1])],poly) for u,v in zip(path,path[1:]) for t in [.1,.25,.5,.75,.9]):continue
    ribbons=[g.road_ribbon(u,v,2.8) for u,v in zip(path,path[1:])]
    if any(g.positive_area_overlap(q,o,1e-6) for q in ribbons for o in protected+plotpolys+canal_ribbons):continue
    options.append((math.dist(a,b),path,ar,br))
  if options:
   _,line,ar,br=max(options,key=lambda o:o[0])
   rid=rec['id']+':ALLEY';r={'id':rid,'width_m':2.8,'polyline_xz_m':line,'kind':'connected_block_interior_alley','block_id':rec['id'],'connects_road_ids':[ar,br]}
   roads.append(r);rec['interior_path_ids'].append(rid)
 for r in roads[len(ROADS):]:
  road_ribbons.extend((r['id'],g.road_ribbon(a,b,r['width_m'])) for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]))
 road_polygons=[p for _,p in road_ribbons]
 collision_indexes={}
 def hits(poly,polygons):
  key=id(polygons)
  if key not in collision_indexes:collision_indexes[key]=[g._SpatialIndex(32),0]
  idx,count=collision_indexes[key]
  for i in range(count,len(polygons)):idx.add(i,polygons[i])
  collision_indexes[key][1]=len(polygons)
  return any(g.positive_area_overlap(poly,polygons[i],1e-6) for i in idx.candidates(poly))
 def plot(identity,district_id,typ,pos,w,d,yaw=0,gate_road=None):
  poly=footprint(pos,w,d,yaw)
  blockers=[]
  if not g.convex_polygon_contains(BOUNDARY,poly,0):blockers.append('wall_boundary')
  if hits(poly,protected):blockers.append('named_space')
  if hits(poly,canal_ribbons):blockers.append('service_water_corridor')
  if hits(poly,road_polygons):blockers.append('public_road')
  if hits(poly,plotpolys):blockers.append('other_plot')
  if blockers:rejected.append({'id':identity,'reasons':blockers});return None
  gate=transform([0,d/2],pos,yaw);candidates=nearest(gate,[r for r in roads if gate_road is None or r['id']==gate_road]);dist,rid,end=candidates[0]
  rec={'id':identity,'district_id':district_id,'property_type':typ,'polygon_xz_m':poly,'land_use':typ,
   'width_m':w,'depth_m':d,'origin_xz_m':pos,'yaw_rad':yaw,'gate_front':'+Z','gate_position_xz_m':gate,'road_id':rid,
   'gate_connection_xz_m':end,'area_m2':w*d,'assembly_intent':'replace_by_property_recipe_with_same_plot_id'}
  plan['plots'].append(rec);plotpolys.append(poly)
  plan['paths'].append({'id':identity+':GATE','owner_plot_id':identity,'polyline_xz_m':[gate,end],'width_m':2.4 if typ=='poor_block' else 3.,'road_id':rid,'kind':'property_gate_link'})
  return rec
 def mass(identity,district_id,function,pos,w,d,h,yaw,entrance,road_id,plot_id=None,assembly='ordinary_house',floors=2):
  p=footprint(pos,w,d,yaw)
  if not g.convex_polygon_contains(BOUNDARY,p,0):return False
  if hits(p,road_polygons) or hits(p,canal_ribbons):return False
  if hits(p,buildingpolys):return False
  b={'id':identity,'district_id':district_id,'function':function,'position_xz_m':pos,'width_m':w,'depth_m':d,'height_m':h,'yaw_rad':yaw,
   'entrance_xz_m':entrance,'road_id':road_id,'assembly_intent':assembly,'plot_id':plot_id,'floors':floors,'footprint_xz_m':p,
   'social_class':{'noble_estate':'noble_household','merchant_court':'merchant_household','poor_block':'wage_laborer_and_artisan'}.get(assembly,'mixed_livelihood'),
   'ground_height_policy':'terrain.height_at + explicit support; no duplicated flat Y','roof_material':('gray_slate' if 'noble' in function or 'clergy' in function else 'brown_shingle' if 'poor' in function else 'red_clay')}
  plan['buildings'].append(b);buildingpolys.append(p);return True
 def populate(rec):
  pos=rec['origin_xz_m'];yaw=rec['yaw_rad'];typ=rec['property_type'];w,d=rec['width_m'],rec['depth_m'];identity=rec['id'];rid=rec['road_id'];did=rec['district_id']
  if typ=='noble_estate':
   spec=[('noble_main_hall',[-8,-12],24,18,15,3),('stable_and_coach_store',[24,3],10,24,7,1),('servant_lodge',[-24,10],10,18,8,2),('estate_kitchen',[7,15],12,10,7,1)]
  elif typ=='merchant_court':
   spec=[('merchant_shop_house',[-8,10],12,18,13,3),('warehouse',[9,-10],12,18,10,2),('merchant_service_lodge',[-9,-11],10,14,8,2)]
  elif typ=='craft_workyard':
   spec=[('workshop',[-10,-9],16,18,9,2),('worker_house',[10,-10],12,14,8,2),('store_shed',[-10,13],16,10,6,1),('workshop_house',[11,13],12,10,10,2)]
  else:
   spec=[]
   for col,x in enumerate([-8,8] if typ=='poor_block' else [-12,12]):
    for row,z in enumerate([-13.5,-4.5,4.5,13.5] if typ=='poor_block' else [-15,-5,5,15]):
     # Local +Z rotates toward the shared central alley, preserving narrow doors.
     byaw=math.pi/2 if col==0 else -math.pi/2
     width,depth=(8.,10.) if typ=='poor_block' else (8.,12.)
     wp=transform([x,z],pos,yaw);wyaw=yaw+byaw;ep=transform([0,depth/2],wp,wyaw)
     bid=identity+f':H{col}{row}';floors=1+(row+col)%3;function='poor_attached_pair' if typ=='poor_block' else 'old_town_house_and_shop'
     if mass(bid,did,function,wp,width,depth,5+floors*2.6,wyaw,ep,rid,identity,typ,floors):
      join=transform([0,z],pos,yaw);plan['paths'].append({'id':bid+':DOOR','owner_building_id':bid,'owner_plot_id':identity,'polyline_xz_m':[ep,join],'width_m':1.8,'road_id':rid,'kind':'actual_door_link'})
   alley=[transform(p,pos,yaw) for p in [[0,d/2],[0,6],[-.5,1],[.5,-5],[.5,-d/2+1]]]
   plan['paths'].append({'id':identity+':INNER','owner_plot_id':identity,'polyline_xz_m':alley,'width_m':2.2,'road_id':rid,'kind':'bent_shared_alley'})
   rec['court_polygon_xz_m']=footprint(transform([0,0],pos,yaw),3.,d-2,yaw);return
  # Main/service buildings and a central gate path leave purposeful enclosed court.
  for j,(function,lp,bw,bd,h,floors) in enumerate(spec):
   wp=transform(lp,pos,yaw);ep=transform([0,bd/2],wp,yaw);bid=identity+f':B{j:02d}'
   if mass(bid,did,function,wp,bw,bd,h,yaw,ep,rid,identity,typ,floors):
    join=transform([0,lp[1]+bd/2+2],pos,yaw)
    plan['paths'].append({'id':bid+':DOOR','owner_building_id':bid,'owner_plot_id':identity,'polyline_xz_m':([ep,transform([24,24],pos,yaw),transform([0,24],pos,yaw),transform([0,d/2],pos,yaw)] if typ=='noble_estate' and function=='stable_and_coach_store' else [ep,join,transform([0,d/2],pos,yaw)]),'width_m':1.8,'road_id':rid,'kind':'individual_door_to_gate'})
  rec['court_polygon_xz_m']=footprint(transform([0,0],pos,yaw),8.,d-4,yaw)

 # Deep court parcels follow the individual road tangent, not global X/Z rows.
 # Frontage spacing is one metre; each accepted compound already has internal
 # door routes, shared court and rear service buildings before gap infill begins.
 compound_count=0
 for r in list(roads):
  if r['kind'] in ('market_edge','civic_approach','military_service','noble_quarter_lane') or r['id'] in ('R_PORT','R_PORT_W','R_CASTLE','R_CATHEDRAL'):continue
  for si,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   length=math.dist(a,b);ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length
   for side in(-1,1):
    n=[-uz*side,ux*side];cursor=17.
    while cursor<length-12:
     q=[a[0]+ux*cursor,a[1]+uz*cursor];guess=[q[0]+n[0]*22,q[1]+n[1]*22]
     dr=next((d for d in plan['districts'] if g.point_in_convex_polygon(guess,d['polygon_xz_m'],0)),None)
     if not dr or dr['role'] in ('noble','monastery','castle','port'):cursor+=31;continue
     typ='merchant_court' if dr['role'] in ('merchants','civic') else 'poor_block' if dr['role'] in ('poor','craft') else 'old_town_block'
     w,d=(36,42) if typ=='merchant_court' else (30,36) if typ=='poor_block' else (40,42)
     pos=[q[0]+n[0]*(r['width_m']/2+d/2+.6),q[1]+n[1]*(r['width_m']/2+d/2+.6)];yaw=math.atan2(-n[0],-n[1])
     rec=plot(f'P_COURT_{compound_count:03d}',dr['id'],typ,pos,w,d,yaw,r['id'])
     if rec:
      populate(rec);compound_count+=1
      block=next((bl for bl in plan['blocks'] if inside(pos,bl['polygon_xz_m'])),None)
      if block:rec['block_id']=block['id'];block['plot_ids'].append(rec['id'])
     cursor+=w+1.2
 # Short continuous frontages complete irregular corner gaps. Exact common
 # dimensions are retained; no whole-house resizing and no random scattering.
 infill_count=0
 for r in list(roads):
  if r['kind'] in ('civic_approach','military_service','noble_quarter_lane') or r['id'] in ('R_PORT','R_PORT_W','R_CASTLE','R_CATHEDRAL'):continue
  for segment,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   length=math.dist(a,b);ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length
   for side in (-1,1):
    cursor=5.
    while cursor<length-4:
     width=[6.,8.,10.,12.][(infill_count+segment)%4];depth=[14.,18.,14.][(infill_count+segment)%3]
     q=[a[0]+ux*cursor,a[1]+uz*cursor];n=[-uz*side,ux*side];pos=[q[0]+n[0]*(r['width_m']/2+depth/2+.45),q[1]+n[1]*(r['width_m']/2+depth/2+.45)]
     cursor+=width+.65
     dr=next((d for d in plan['districts'] if g.point_in_convex_polygon(pos,d['polygon_xz_m'],0)),None)
     if not dr or dr['role'] in ('noble','monastery','castle','port'):continue
     yaw=math.atan2(-n[0],-n[1]);pc=[pos[0]+n[0]*2,pos[1]+n[1]*2];parcel=footprint(pc,width+.4,depth+4,yaw)
     if not g.convex_polygon_contains(BOUNDARY,parcel,0):continue
     if (hits(parcel,protected) or hits(parcel,plotpolys) or hits(parcel,canal_ribbons)):continue
     if hits(parcel,road_polygons):continue
     bid=f'B_EDGE_{infill_count:03d}';pid=f'P_EDGE_{infill_count:03d}';ep=transform([0,depth/2],pos,yaw)
     fun={'merchants':'shop_and_merchant_lodging','civic':'shop_and_trader_lodging','old_town':'house_and_small_workshop','poor':'poor_row_lodging','craft':'craft_house_and_store','water_gardens':'gardener_and_waterkeeper_house','cathedral':'clergy_and_school_house'}.get(dr['role'],'mixed_house')
     if mass(bid,dr['id'],fun,pos,width,depth,8+3*((infill_count+segment)%3),yaw,ep,r['id'],pid,'ordinary_common_catalog',1+(infill_count+segment)%3):
      rec={'id':pid,'district_id':dr['id'],'property_type':'street_frontage_plot','land_use':fun,'polygon_xz_m':parcel,'area_m2':area(parcel),'width_m':width+.4,'depth_m':depth+4,'origin_xz_m':pc,'yaw_rad':yaw,'gate_front':'+Z','gate_position_xz_m':ep,'gate_connection_xz_m':q,'road_id':r['id'],'assembly_intent':'common_house_with_productive_rear_court'}
      plan['plots'].append(rec);plotpolys.append(parcel);plan['paths'].append({'id':bid+':DOOR','owner_building_id':bid,'owner_plot_id':pid,'polyline_xz_m':[ep,q],'width_m':1.8,'road_id':r['id'],'kind':'frontage_door_link'})
      block=next((bl for bl in plan['blocks'] if inside(pos,bl['polygon_xz_m'])),None)
      if block:rec['block_id']=block['id'];block['plot_ids'].append(pid)
      infill_count+=1
 # A finer finite pass closes eligible frontage gaps with catalog-sized houses.
 # Each accepted strip is bounded and checked before the next candidate; this
 # does not put houses into existing private courts or squeeze out door routes.
 for r in list(roads):
  if r['kind'] in ('civic_approach','military_service','noble_quarter_lane') or r['id'] in ('R_PORT','R_PORT_W','R_CASTLE','R_CATHEDRAL'):continue
  for segment,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   length=math.dist(a,b);ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length
   for side in (-1,1):
    n=[-uz*side,ux*side]
    for at in range(4,int(length)-3,3):
     q=[a[0]+ux*at,a[1]+uz*at]
     for width,depth in [(12.,18.),(10.,14.),(8.,10.),(6.,10.),(6.,6.)]:
      pos=[q[0]+n[0]*(r['width_m']/2+depth/2+.4),q[1]+n[1]*(r['width_m']/2+depth/2+.4)];yaw=math.atan2(-n[0],-n[1])
      dr=next((d for d in plan['districts'] if g.point_in_convex_polygon(pos,d['polygon_xz_m'],0)),None)
      if not dr or dr['role'] in ('noble','monastery','castle','port'):break
      pc=[pos[0]+n[0],pos[1]+n[1]];parcel=footprint(pc,width+.2,depth+2,yaw)
      if not g.convex_polygon_contains(BOUNDARY,parcel,0):continue
      if (hits(parcel,protected) or hits(parcel,plotpolys) or hits(parcel,canal_ribbons)):continue
      if hits(parcel,road_polygons):continue
      bid=f'B_CORNER_{infill_count:03d}';pid=f'P_CORNER_{infill_count:03d}';ep=transform([0,depth/2],pos,yaw)
      fun='poor_attached_lodging' if dr['role'] in ('poor','craft') else 'merchant_shop' if dr['role'] in ('merchants','civic') else 'mixed_worker_house'
      if mass(bid,dr['id'],fun,pos,width,depth,8+3*(infill_count%2),yaw,ep,r['id'],pid,'ordinary_common_catalog',1+infill_count%2):
       rec={'id':pid,'district_id':dr['id'],'property_type':'street_frontage_plot','land_use':fun,'polygon_xz_m':parcel,'area_m2':area(parcel),'width_m':width+.2,'depth_m':depth+2,'origin_xz_m':pc,'yaw_rad':yaw,'gate_front':'+Z','gate_position_xz_m':ep,'gate_connection_xz_m':q,'road_id':r['id'],'assembly_intent':'common_attached_house_corner_plot'}
       plan['plots'].append(rec);plotpolys.append(parcel);plan['paths'].append({'id':bid+':DOOR','owner_building_id':bid,'owner_plot_id':pid,'polyline_xz_m':[ep,q],'width_m':1.8,'road_id':r['id'],'kind':'corner_frontage_door_link'})
       block=next((bl for bl in plan['blocks'] if inside(pos,bl['polygon_xz_m'])),None)
       if block:rec['block_id']=block['id'];block['plot_ids'].append(pid)
       infill_count+=1;break
 from world_city.concept_city_v3.source.recipe_proxies import adopt
 adopt(plan,nearest)
 plan['protected_design_catalog']=copy.deepcopy(old['protected_design_catalog'])
 for d in plan['protected_design_catalog']:d['placed_building_id']=None;d['status']='catalogued_pending_contour_market_frontage_review'
 # Gate/watergate and bridge records derive exact intersections, not guessed gaps.
 for r in roads:
  for j,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   for k,(c,d) in enumerate(zip(BOUNDARY,BOUNDARY[1:]+BOUNDARY[:1])):
    hit=intersect_segments(a,b,c,d)
    if hit and not any(math.dist(hit[0],v['position_xz_m'])<1 for v in plan['gates']):plan['gates'].append({'id':f'GATE_{len(plan["gates"])+1:02d}','role':'road_gate','position_xz_m':hit[0],'road_id':r['id'],'opening_width_m':r['width_m']/max(.05,abs(((b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0]))/(math.dist(a,b)*math.dist(c,d))))+2.,'wall_edge_index':k})
   for k,(c,d) in enumerate(zip(CANAL,CANAL[1:])):
    hit=intersect_segments(a,b,c,d)
    if hit:
     point,t,u=hit;length=math.dist(a,b);ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length;cosine=abs(ux*(d[0]-c[0])/math.dist(c,d)+uz*(d[1]-c[1])/math.dist(c,d));sine=max(.05,math.sqrt(max(0,1-cosine*cosine)));span=(7+(r['width_m']+.6)/2*cosine)/sine+3.
     plan['bridges'].append({'id':f'BRIDGE_SERVICE_{len(plan["bridges"])+1:02d}','role':'service_canal_crossing','road_id':r['id'],'position_xz_m':point,
       'deck_polyline_xz_m':[[point[0]-span*ux,point[1]-span*uz],[point[0]+span*ux,point[1]+span*uz]],'width_m':r['width_m']+.6,
       'water_channel_segment_index':k,'water_level_m':CANAL_LEVELS[k]+u*(CANAL_LEVELS[k+1]-CANAL_LEVELS[k]),'deck_height_policy':'max(terrain approaches, water + 2.0m); authored ramps required'})
 for j,(a,b) in enumerate(zip(CANAL,CANAL[1:])):
  for k,(c,d) in enumerate(zip(BOUNDARY,BOUNDARY[1:]+BOUNDARY[:1])):
   hit=intersect_segments(a,b,c,d)
   if hit:plan['gates'].append({'id':f'WATERGATE_{j}_{k}','role':'service_canal_watergate','position_xz_m':hit[0],'opening_width_m':14/max(.05,abs(((b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0]))/(math.dist(a,b)*math.dist(c,d))))+2.,'wall_edge_index':k,'water_segment_index':j})
 plan['bridges'].append({'id':'BRIDGE_MAIN_RIVER','role':'main_river_bridge','road_id':'R_MARKET_EAST','position_xz_m':[120,465],'deck_polyline_xz_m':[[120,398],[120,530]],'width_m':9,'deck_height_policy':'terrain worker river crossing profile','water_level_m':-2})

 plan['rejected_parcel_candidates']=rejected
 plan['counts']={'buildings':len(plan['buildings']),'plots':len(plan['plots']),'roads':len(roads),'paths':len(plan['paths']),'blocks':len(plan['blocks']),'districts':len(plan['districts']),'noble_compounds':len(noble_ids),'by_plot_type':dict(Counter(p['property_type'] for p in plan['plots']))}
 plan['coverage']={'wall_area_m2':area(BOUNDARY),'district_partition_area_m2':sum(d['area_m2'] for d in plan['districts']),'parcel_area_m2':sum(p['area_m2'] for p in plan['plots']),'building_footprint_area_m2':sum(area(b['footprint_xz_m']) for b in plan['buildings'])}
 from world_city.concept_city_v3.source.review_metadata import enrich
 return enrich(add_ground_program(plan))

def main():
 p=build();(HERE/'plan.json').write_text(json.dumps(p,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(p['counts']));print(json.dumps(p['coverage']));print(json.dumps({k:v for k,v in p['residual_ledger'].items() if k!='districts'}))
if __name__=='__main__':main()
