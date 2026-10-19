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
CANAL=[[-520,440],[-460,300],[-340,280],[-180,280],[-30,270],[130,260],[270,270],[350,310],[370,330],[390,345],[410,365],[480,450]]
CANAL_LEVELS=[2,1.9,1.7,1.5,1.3,1.1,.8,.5,-.3,-.4,-1.2,-2]
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
 plan={'schema':'riverstone.concept_city.source.v3','revision':'v3_clean_source_blockout_01','status':'authored_source_for_first_runtime_blockout',
 'coordinate_system':{'units':'metres','up':'+Y','north':'-Z','east':'+X','height_owner':'concept_city_v3/topography; source plan never duplicates H'},
 'boundary_xz_m':BOUNDARY,'districts':[],'roads':[],'buildings':[],'plots':[],'spaces':[],'paths':[],'gates':[],'bridges':[],
 'water_reservations':{'reservoir_outer_polygon_xz_m':rect(-60,-370,60,-300),'source_xz_m':[30,-510],
  'service_canal_polyline_xz_m':CANAL,'service_corridor_width_m':14,'service_water_levels_m':CANAL_LEVELS,
  'river_polygon_xz_m':rect(-650,420,650,510),'height_and_flow_owner':'terrain worker; these are coordination reservations'},
 'source_policy':{'old_1308_layout_constraints_retired':True,'old_sources_unmodified':True,'no_fixed_building_count_or_city_area_target':True,
   'observed_in_concept':'contiguous noble compounds, dense poorer/craft neighborhoods, clergy closes, commercial courts, visible separate clean and service water',
   'authored_not_measured_from_pixels':'all coordinates, widths, floor counts, parcels, paths and districts',
   'concept_image':'world_city/reference/revision_03/city_social_water_concept.png'}}
 def district(identity,role,bounds):
  p=clean(g.convex_intersection(rect(*bounds),BOUNDARY))
  if p:plan['districts'].append({'id':identity,'role':role,'polygon_xz_m':p,'color':PALETTE[role],'area_m2':area(p),
   'ground_program':{'castle':'fortified precinct and military support','water_gardens':'clean-water service, orchard and cultivated holdings','cathedral':'clergy residence, cemetery and ecclesiastical gardens','noble':'enclosed estate grounds and household service courts','merchants':'shop frontages, warehouse courts and stables','civic':'organized market and civic procession','monastery':'cloister, charitable service and productive gardens','old_town':'dense mixed housing, parish service and little shared courts','poor':'tightly packed wage-laborer housing and communal courts','craft':'working yards, mills and poorer workshop housing','port':'goods exchange, cart movement, warehouses and quay service'}[role]})
 district('D_CASTLE','castle',[-500,-500,-190,-170]);district('D_WATER','water_gardens',[-190,-500,130,-170]);district('D_CATHEDRAL','cathedral',[130,-500,500,-170])
 district('D_NOBLE','noble',[-500,-170,-45,80]);district('D_MERCHANT_N','merchants',[-45,-170,160,-60]);district('D_CIVIC','civic',[-45,-60,160,80]);district('D_MERCHANT_E','merchants',[160,-170,330,80]);district('D_CRAFT_N','craft',[330,-170,500,80])
 district('D_MONASTERY','monastery',[-500,80,-190,300]);district('D_OLD','old_town',[-190,80,100,300]);district('D_POOR','poor',[100,80,330,300]);district('D_CRAFT_S','craft',[330,80,500,300]);district('D_PORT','port',[-500,300,500,500])
 def space(identity,role,bounds,**extra):
  p=clean(g.convex_intersection(rect(*bounds),BOUNDARY));plan['spaces'].append({'id':identity,'role':role,'polygon_xz_m':p,'area_m2':area(p),**extra})
 space('S_CASTLE','fortified_castle_precinct',[-410,-335,-215,-175],landmark_anchor_xz_m=[-300,-250])
 space('S_CATHEDRAL','cathedral_cloister_and_clergy_close',[155,-325,355,-175],landmark_anchor_xz_m=[250,-230])
 space('S_MONASTERY','monastery_cloister_hospital_and_garden',[-390,80,-195,225],landmark_anchor_xz_m=[-270,120])
 space('S_TRAINING','military_training_ground',[-405,-160,-230,-80],clear_drill_polygon_xz_m=rect(-390,-145,-250,-95))
 space('S_RESERVOIR','clean_water_reservoir_and_cistern',[-60,-370,60,-300])
 space('S_MARKET','grain_produce_market_and_civic_square',[-45,0,85,85],functional_zones=[{'id':'grain','polygon_xz_m':rect(-40,5,15,35)},{'id':'produce','polygon_xz_m':rect(30,5,80,35)},{'id':'civic_procession','polygon_xz_m':rect(-40,40,80,80)}])
 space('S_TOWN_HALL','town_hall_and_grain_hall',[-30,-55,70,-10],landmark_anchor_xz_m=[20,-30])
 space('S_PORT_LOGISTICS','bulk_goods_exchange_and_cart_unloading',[-230,305,60,370])
 space('S_COMMON','small_urban_common',[-185,10,-140,55])
 def road(identity,points,width=6,kind='cart_street'):
  plan['roads'].append({'id':identity,'width_m':width,'polyline_xz_m':points,'kind':kind,'height_policy':'terrain_author_evaluated_profile; bridges explicitly override deck'})
 road('R_NORTH',[[90,-400],[90,-372],[70,-325],[70,-260],[65,-185],[45,-110],[20,-60],[95,-55]],7)
 road('R_MARKET_EAST',[[95,-55],[95,90],[70,150],[110,230],[120,330],[120,390],[120,465],[120,550]],8)
 road('R_CASTLE',[[-300,-175],[-250,-155],[-210,-120],[-220,-65],[-200,0],[-150,65],[-55,90],[95,90]],7)
 road('R_CATHEDRAL',[[250,-175],[310,-145],[310,-90],[230,-65],[160,-55],[95,-55]],7)
 road('R_WEST',[[-490,0],[-460,0],[-400,0],[-320,0],[-220,-10],[-150,65]],7)
 road('R_EAST',[[490,70],[455,70],[380,70],[300,75],[220,90],[95,90]],7)
 road('R_MONASTERY',[[-410,320],[-310,285],[-190,250],[-190,130],[-150,65]],6)
 road('R_PORT',[[-390,335],[-250,335],[-100,340],[120,335],[300,335],[385,300]],8)
 road('R_WORKING',[[-190,250],[-105,245],[40,250],[110,230],[220,235],[335,250],[385,300]],6)
 road('R_TRAINING',[[-400,-140],[-230,-140],[-210,-120]],4,'military_service')
 road('R_NOBLE_N',[[-220,-65],[-220,-72],[-40,-72],[-5,-110],[45,-110]],4)
 road('R_NOBLE_M',[[-220,-10],[-210,12],[-45,12],[-45,90]],4)
 road('R_GARDEN_W',[[-170,-180],[-160,-230],[-120,-280],[-85,-300],[-85,-340],[70,-340]],4)
 road('R_GARDEN_CONNECT',[[-170,-180],[-80,-185],[65,-185]],5)
 # Connected small local lanes precede all regular parcel massing.
 for j,z in enumerate([-168,-120,-72]):road(f'R_MN_{j}',[[-40,z],[160,z]],3.2,'local_service_lane')
 road('R_MN_CONNECT',[[150,-168],[150,-55],[160,-55]],3.2,'local_service_lane')
 for j,z in enumerate([-164,-114,-64,-14,36,78]):road(f'R_ME_{j}',[[160,z],[310,z]],3.2,'local_service_lane')
 road('R_ME_W',[[160,-164],[160,90]],4,'local_service_lane');road('R_ME_E',[[310,-164],[310,90]],4,'local_service_lane')
 for j,z in enumerate([92,140,188,236]):road(f'R_OLD_H_{j}',[[-190,z],[105,z]],2.6,'local_alley')
 for j,x in enumerate([-177.5,-132.5,-87.5,-42.5,2.5,47.5,92.5]):road(f'R_OLD_V_{j}',[[x,92],[x,250]],2.4,'local_alley')
 road('R_OLD_LINK',[[-190,92],[-190,130]],3,'local_alley')
 for j,z in enumerate([93,133,173,213,253]):road(f'R_POOR_H_{j}',[[110,z],[335,z]],2.4,'local_alley')
 road('R_POOR_W',[[110,90],[110,253]],2.8,'local_alley');road('R_POOR_E',[[335,70],[335,253]],3,'local_alley')
 for j,z in enumerate([-155,-103,-53,-3,47,97,147,197,247]):road(f'R_CRAFT_H_{j}',[[335,z],[438,z]],3.2,'workshop_lane')
 road('R_CRAFT_W',[[335,-155],[335,253]],4,'workshop_lane');road('R_CRAFT_E',[[438,-155],[438,247]],4,'workshop_lane')
 # A market perimeter and north entrance preserve the town hall forecourt.
 road('R_MARKET_W',[[-45,0],[-45,90]],5,'market_edge');road('R_MARKET_N',[[-45,0],[95,0]],5,'market_edge')
 road('R_HALL_APPROACH',[[20,-10],[20,0]],4,'civic_approach')
 roads=plan['roads'];road_ribbons=[(r['id'],g.road_ribbon(a,b,r['width_m'])) for r in roads for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]
 canal_ribbons=[g.road_ribbon(a,b,14) for a,b in zip(CANAL,CANAL[1:])]
 protected=[s['polygon_xz_m'] for s in plan['spaces']]
 rejected=[];plotpolys=[];buildingpolys=[]
 def plot(identity,district_id,typ,pos,w,d,yaw=0,gate_road=None):
  poly=footprint(pos,w,d,yaw)
  blockers=[]
  if not g.convex_polygon_contains(BOUNDARY,poly,0):blockers.append('wall_boundary')
  if any(g.positive_area_overlap(poly,p,1e-6) for p in protected):blockers.append('named_space')
  if any(g.positive_area_overlap(poly,p,1e-6) for p in canal_ribbons):blockers.append('service_water_corridor')
  if any(g.positive_area_overlap(poly,p,1e-6) for _,p in road_ribbons):blockers.append('public_road')
  if any(g.positive_area_overlap(poly,p,1e-6) for p in plotpolys):blockers.append('other_plot')
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
  if any(g.positive_area_overlap(p,q,1e-6) for _,q in road_ribbons) or any(g.positive_area_overlap(p,q,1e-6) for q in canal_ribbons):return False
  if any(g.positive_area_overlap(p,q,1e-6) for q in buildingpolys):return False
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
 # Explicit connected noble quarter: 8 large compounds, two frontage directions.
 noble=[([-165,-115],0,'R_NOBLE_N'),([-85,-115],0,'R_NOBLE_N'),([-365,-40],0,'R_WEST'),([-285,-45],0,'R_WEST'),([-167,-32],0,'R_NOBLE_M'),([-85,-28],0,'R_NOBLE_M'),([-365,40],math.pi,'R_WEST'),([-285,40],math.pi,'R_WEST')]
 for i,(p,y,rid) in enumerate(noble):
  rec=plot(f'P_NOBLE_{i+1:02d}','D_NOBLE','noble_estate',p,70,62,y,rid)
  if rec:populate(rec)
 for iz,z in enumerate([-144,-96]):
  for ix,x in enumerate([-7,34,75,116]):
   rec=plot(f'P_MN_{iz}{ix}','D_MERCHANT_N','merchant_court',[x,z],36,42)
   if rec:populate(rec)
 for iz,z in enumerate([-139,-89,-39,11,59]):
  for ix,x in enumerate([188,231,274]):
   rec=plot(f'P_ME_{iz}{ix}','D_MERCHANT_E','merchant_court',[x,z],36,42)
   if rec:populate(rec)
 for iz,z in enumerate([116,164,212]):
  for ix,x in enumerate([-155,-110,-65,-20,25,70]):
   rec=plot(f'P_OLD_{iz}{ix}','D_OLD','old_town_block',[x,z],40,42)
   if rec:populate(rec)
 for iz,z in enumerate([113,153,193,233]):
  for ix,x in enumerate([130,164,198,232,266,300]):
   rec=plot(f'P_POOR_{iz}{ix}','D_POOR','poor_block',[x,z],30,36)
   if rec:populate(rec)
 for iz,z in enumerate([-128,-78,-28,22,72,122,172,222]):
  for ix,x in enumerate([361,411]):
   rec=plot(f'P_CRAFT_{iz}{ix}','D_CRAFT_N' if z<80 else 'D_CRAFT_S','craft_workyard',[x,z],42,44)
   if rec:populate(rec)
 # Fill eligible street gaps only after every public route and compound is fixed.
 # Dimensions are existing common catalog bins; courts and water stay reserved.
 district_roles={d['id']:d['role'] for d in plan['districts']}
 infill_count=0
 for r in list(roads):
  if r['kind'] in ('civic_approach','market_edge'):continue
  for segment,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   length=math.dist(a,b);ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length
   for step in range(1,int(length/11)):
    t=step*11/length;q=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]
    for side in (-1,1):
     n=[-uz*side,ux*side];pos=[q[0]+n[0]*(r['width_m']/2+7+.7),q[1]+n[1]*(r['width_m']/2+7+.7)]
     district_rec=next((d for d in plan['districts'] if g.point_in_convex_polygon(pos,d['polygon_xz_m'],0)),None)
     if not district_rec or district_rec['role'] not in ('merchants','old_town','poor','craft'):continue
     width=[6.,8.,10.][(step+segment)%3];depth=14.;yaw=math.atan2(-n[0],-n[1]);poly=footprint(pos,width,depth,yaw)
     parcel_center=[pos[0]+n[0]*1.5,pos[1]+n[1]*1.5];parcel=footprint(parcel_center,width+1,depth+4,yaw)
     if not g.convex_polygon_contains(BOUNDARY,parcel,0):continue
     if any(g.positive_area_overlap(parcel,p,1e-6) for p in protected+plotpolys+canal_ribbons):continue
     if any(g.positive_area_overlap(parcel,p,1e-6) for _,p in road_ribbons):continue
     bid=f'B_FRONTAGE_{infill_count+1:03d}';pid=f'P_FRONTAGE_{infill_count+1:03d}';ep=[pos[0]-n[0]*depth/2,pos[1]-n[1]*depth/2]
     function={'merchants':'shop_and_merchant_lodging','old_town':'house_and_small_workshop','poor':'poor_row_lodging','craft':'craft_house_and_store'}[district_rec['role']]
     if mass(bid,district_rec['id'],function,pos,width,depth,10+((step+segment)%2)*2.5,yaw,ep,r['id'],pid,'ordinary_common_catalog',2+(step+segment)%2):
      plan['plots'].append({'id':pid,'district_id':district_rec['id'],'property_type':'street_frontage_plot','land_use':function,'polygon_xz_m':parcel,'area_m2':area(parcel),
       'width_m':width+1,'depth_m':depth+4,'origin_xz_m':parcel_center,'yaw_rad':yaw,'gate_front':'+Z','gate_position_xz_m':ep,'gate_connection_xz_m':q,'road_id':r['id'],
       'assembly_intent':'ordinary_catalog_house_with_small_rear_work_strip'})
      plotpolys.append(parcel);plan['paths'].append({'id':bid+':DOOR','owner_building_id':bid,'owner_plot_id':pid,'polyline_xz_m':[ep,q],'width_m':1.8,'road_id':r['id'],'kind':'frontage_door_link'});infill_count+=1
 # Preserve the seven authored house designs as a continuous market-west frontage.
 approved=[('D03-B016',9.6,15.6,1),('D03-B017',12.8,20.8,2),('D03-B022',12.8,15.6,2),('D03-B023',6.4,26.,1),('D03-B024',6.4,26.,3),('D03-B025',9.6,15.6,2),('D03-B026',9.6,15.6,1)]
 plan['protected_design_catalog']=[];cursor=6.
 for source_id,w,d,floors in approved:
  z=cursor+w/2;x=-45-2.5-1.-d/2;ep=[-48.5,z];identity='B_APPROVED_'+source_id
  okay=mass(identity,'D_CIVIC','approved_market_shop_house',[x,z],w,d,5+floors*3.,math.pi/2,ep,'R_MARKET_W',None,'approved_r4_house_record',floors)
  plan['protected_design_catalog'].append({'source_design_id':source_id,'width_m':w,'depth_m':d,'floors':floors,'placed_building_id':identity if okay else None,'status':'placed' if okay else 'catalogued_not_forced_into_circulation'})
  if okay:
   plan['buildings'][-1]['source_design_id']=source_id;plan['paths'].append({'id':identity+':DOOR','owner_building_id':identity,'polyline_xz_m':[ep,[-45,z]],'width_m':1.8,'road_id':'R_MARKET_W','kind':'approved_frontage_door_link'})
  cursor+=w+1.
 # Landmark footprints are explicit assembly slots, not arbitrary scaled houses.
 landmarks=[('B_CASTLE_KEEP','D_CASTLE','castle_keep',[-310,-265],56,42,30,[-310,-244],'R_CASTLE','castle'),
 ('B_CATHEDRAL','D_CATHEDRAL','cathedral_nave',[250,-255],48,90,42,[250,-210],'R_CATHEDRAL','cathedral'),
 ('B_MONASTERY','D_MONASTERY','monastery_hospital',[-290,120],80,45,17,[-250,120],'R_MONASTERY','monastery'),
 ('B_TOWN_HALL','D_CIVIC','town_hall',[0,-32],46,24,21,[0,-20],'R_HALL_APPROACH','town_hall')]
 for identity,did,f,p,w,d,h,e,rid,a in landmarks:mass(identity,did,f,p,w,d,h,0,e,rid,None,a,3)
 # Real clear training edges and port warehouses, with roads already reserved.
 for i,x in enumerate([-375,-315,-255]):
  mass(f'B_BARRACK_{i}','D_CASTLE','barracks_and_stable',[x,-153],45,12,8,0,[x,-147],'R_TRAINING',None,'barracks',1)
 for i,x in enumerate([-210,-135,-60,205,280]):
  mass(f'B_PORT_WAREHOUSE_{i}','D_PORT','port_warehouse',[x,355 if x<250 else 347],58,18 if x<250 else 14,11,math.pi,[x,346 if x<250 else 340],'R_PORT',None,'warehouse',2)
 # Smaller landmark proxy masses keep recognizable silhouettes until replacement.
 for identity,did,function,pos,w,d,h,entrance,rid,assembly in [
  ('B_CASTLE_TOWER_W','D_CASTLE','castle_tower',[-370,-300],12,12,24,[-370,-294],'R_CASTLE','castle'),
  ('B_CASTLE_TOWER_E','D_CASTLE','castle_tower',[-235,-300],12,12,24,[-235,-294],'R_CASTLE','castle'),
  ('B_CATHEDRAL_TOWER_W','D_CATHEDRAL','cathedral_tower',[225,-199],14,14,48,[225,-192],'R_CATHEDRAL','cathedral'),
  ('B_CATHEDRAL_TOWER_E','D_CATHEDRAL','cathedral_tower',[275,-199],14,14,48,[275,-192],'R_CATHEDRAL','cathedral'),
  ('B_CATHEDRAL_CLOISTER','D_CATHEDRAL','cloister_service_range',[308,-248],24,44,12,[308,-226],'R_CATHEDRAL','cathedral'),
  ('B_GRAIN_HALL','D_CIVIC','grain_hall',[56,-32],28,28,13,[56,-18],'R_HALL_APPROACH','grain_hall'),
  ('B_MONASTERY_CHAPEL','D_MONASTERY','monastery_chapel',[-335,182],24,42,22,[-323,182],'R_MONASTERY','monastery'),
  ('B_MONASTERY_SERVICE','D_MONASTERY','monastery_service',[-240,183],28,22,10,[-226,183],'R_MONASTERY','monastery')]:
  mass(identity,did,function,pos,w,d,h,0,entrance,rid,None,assembly,2)
 # Link standalone landmark/service doors through their reserved close; internal
 # compound routing is independently checked and corrected before promotion.
 for b in plan['buildings']:
  if not b.get('plot_id') and not any(p.get('owner_building_id')==b['id'] for p in plan['paths']):
   _,rid,q=nearest(b['entrance_xz_m'],[r for r in roads if r['id']==b['road_id']])[0]
   plan['paths'].append({'id':b['id']+':DOOR','owner_building_id':b['id'],'polyline_xz_m':([b['entrance_xz_m'],[340,-215],[340,-165],[310,-145]] if b['id']=='B_CATHEDRAL_CLOISTER' else [b['entrance_xz_m'],[-319,182],[-319,220],[-190,220]] if b['id']=='B_MONASTERY_CHAPEL' else [b['entrance_xz_m'],q]),'width_m':2.,'road_id':rid,'kind':'landmark_or_service_door_link'})
  if b['assembly_intent'] in ('castle','cathedral','monastery','town_hall','grain_hall','warehouse','barracks'):
   b['replace_by_assembly_key']=b['assembly_intent'];b['assembly_group_id']='ASSEMBLY_'+b['assembly_intent'].upper()
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
 plan['counts']={'buildings':len(plan['buildings']),'plots':len(plan['plots']),'roads':len(roads),'paths':len(plan['paths']),'districts':len(plan['districts']),
  'noble_compounds':sum(p['property_type']=='noble_estate' for p in plan['plots']),'by_plot_type':dict(Counter(p['property_type'] for p in plan['plots']))}
 plan['coverage']={'wall_area_m2':area(BOUNDARY),'district_partition_area_m2':sum(d['area_m2'] for d in plan['districts']),
  'parcel_area_m2':sum(p['area_m2'] for p in plan['plots']),'building_footprint_area_m2':sum(area(b['footprint_xz_m']) for b in plan['buildings']),
  'policy':'Every wall-interior point belongs to a functional district; specific streets, sites and enclosed parcels give nested use, never an automatic park blanket.'}
 from world_city.concept_city_v3.source.ground_program import add_ground_program
 return add_ground_program(plan)

def main():
 p=build();(HERE/'plan.json').write_text(json.dumps(p,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(p['counts']));print(json.dumps(p['coverage']))
if __name__=='__main__':main()
