#!/usr/bin/env python3
"""Author an irregular 2D planning layout from a hand-designed street skeleton.
Not a voxel engine. Building counts are outputs, never completion constraints.
"""
from pathlib import Path
import math, json, random, collections, hashlib
R=Path(__file__).resolve().parents[2];rng=random.Random(145002)
base=json.loads((R/'world_city/revisions/v1_functional_draft/data/city_brief.v1.json').read_text())
wall=base['wall_outline_xz_m'];river=base['river_reservation']['centerline_xz_m']
def distance(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def inside(p,poly):
 x,z=p;out=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>z)!=(b[1]>z)and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:out=not out
 return out

def rect(c,w,d,u=(1,0)):
 v=(-u[1],u[0]);return[[round(c[0]+sx*u[0]*w/2+sy*v[0]*d/2,3),round(c[1]+sx*u[1]*w/2+sy*v[1]*d/2,3)]for sx,sy in[(-1,-1),(1,-1),(1,1),(-1,1)]]
def overlap(a,b,gap=.15):
 for p in(a,b):
  for i in range(len(p)):
   q,s=p[i],p[(i+1)%len(p)];ax,az=q[1]-s[1],s[0]-q[0];L=math.hypot(ax,az)
   if L<1e-8:continue
   ax/=L;az/=L;v=[x*ax+z*az for x,z in a];w=[x*ax+z*az for x,z in b]
   if max(v)+gap<=min(w)or max(w)+gap<=min(v):return False
 return True

def bkeys(p):
 xs=[a[0]for a in p];zs=[a[1]for a in p]
 return[(x,z)for x in range(math.floor((min(xs)-1)/40),math.floor((max(xs)+1)/40)+1)for z in range(math.floor((min(zs)-1)/40),math.floor((max(zs)+1)/40)+1)]
class Index:
 def __init__(self):self.shapes=[];self.b=collections.defaultdict(list)
 def add(self,p,tag):
  i=len(self.shapes);self.shapes.append((p,tag))
  for k in bkeys(p):self.b[k].append(i)
 def hits(self,p,ignore=None,gap=.15):
  return[(q,t)for i in{i for k in bkeys(p)for i in self.b.get(k,[])}for q,t in[self.shapes[i]]if t!=ignore and overlap(p,q,gap)]
def segpoly(a,b,w):
 L=distance(a,b);return rect([(a[0]+b[0])/2,(a[1]+b[1])/2],L,w,((b[0]-a[0])/L,(b[1]-a[1])/L))
def lerp(a,b,t):return(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
def catmull(points):
 out=[]
 for i in range(len(points)-1):
  p0=points[max(0,i-1)];p1=points[i];p2=points[i+1];p3=points[min(len(points)-1,i+2)]
  steps=max(2,math.ceil(distance(p1,p2)/18))
  for j in range(steps):
   t=j/steps;out.append(tuple(round(.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t*t+(-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t*t*t),3)for k in(0,1)))
 out.append(tuple(points[-1]));return out
# Gate positions are explicit points on the existing irregular wall outline.
gates={}
for name,idx,t in [('south',6,.38),('east',4,.42),('north',1,.42),('west',9,.38)]:gates[name]=lerp(wall[idx],wall[(idx+1)%len(wall)],t)
S=(45,45);W=(-65,0);E=(75,0);N=(0,-55)
# Named bends are shared junctions. They are neither a rectangular grid nor radial rings.
q1=(200,350);q2=(140,280);q3=(160,200);q4=(95,130);q5=(70,70)
w1=(-505,100);w2=(-400,75);w3=(-300,20);w4=(-170,45);w5=(-105,15)
e1=(515,130);e2=(450,55);e3=(330,45);e4=(250,-10);e5=(135,5)
n1=(100,-430);n2=(30,-370);n3=(60,-260);n4=(15,-160);n5=(60,-85)
routes=[]
def route(id,name,points,width=3.2,kind='local_lane',district=None,curve=True,frontage=True):
 samples=catmull(points)if curve else[tuple(p)for p in points]
 routes.append(dict(id=id,name=name,control_points_xz_m=[list(p)for p in points],polyline_xz_m=[list(p)for p in samples],width_m=width,kind=kind,district_hint=district,frontage=frontage,status='planned_design_inference'))
route('RT_SOUTH_MARKET','남문 시장길',[gates['south'],q1,q2,q3,q4,q5,S],7,'cart_street','D04')
route('RT_WEST_MARKET','서문 옛 장터길',[gates['west'],w1,w2,w3,w4,w5,W],6.5,'cart_street','D07')
route('RT_EAST_MARKET','동문 장인길',[gates['east'],e1,e2,e3,e4,e5,E],6,'cart_street','D06')
route('RT_NORTH_MARKET','북문 정원길',[gates['north'],n1,n2,n3,n4,n5,N],5.5,'cart_street','D08')
route('RT_MARKET_EDGE','시장 가장자리',[S,(75,45),E,(75,-55),N,(-65,-55),W,(-65,45),S],5,'market_edge',curve=False,frontage=True)
# A long, turning approach respects the castle's height difference; exact local grades remain a later gate.
castle_court=(-450,-270)
route('RT_CASTLE_CLIMB','성채 오르막 회랑',[w3,(-340,-70),(-480,-130),(-555,-220),(-510,-285),castle_court],5.5,'cart_street','D01',frontage=False)
route('RT_CASTLE_COURT','성채 중정길',[castle_court,(-485,-300),(-450,-315)],3,'pedestrian','D01',frontage=False)
cat_court=(350,-270)
route('RT_CATHEDRAL_APPROACH','성당 오름길',[e4,(300,-100),(390,-150),(445,-225),cat_court],5.5,'cart_street','D02')
route('RT_CATHEDRAL_CLOSE','성당 담장길',[cat_court,(255,-255),(235,-350),(270,-405),(420,-400),(470,-315),(445,-225)],3.5,'local_lane','D02',frontage=True)
# Unequal blocks, skew junctions, cross-block lanes, and small loops.
locals=[
('L01','윗 교구 골목',[w5,(-140,-80),(-235,-105),(-290,-180),(-220,-240),(-130,-205),n4],'D07'),
('L02','석공 뒤안길',[w3,(-365,-40),(-405,-125),(-325,-205),(-220,-240)],'D07'),
('L03','북쪽 직물 골목',[n4,(120,-210),(180,-290),(110,-340),n2],'D04'),
('L04','정원 아랫길',[n3,(-70,-290),(-140,-370),(-260,-400),(-305,-320),(-220,-240)],'D08'),
('L05','수도원 바깥길',[w2,(-425,170),(-310,230),(-220,175),w4],'D10'),
('L06','아랫 교구길',[w4,(-150,160),(-40,190),(25,120),q5],'D07'),
('L07','서기 골목',[e5,(145,-95),(190,-160),(300,-100)],'D04'),
('L08','장인 마당길',[e3,(300,140),(370,200),(450,230),e1],'D06'),
('L09','신발상 골목',[q4,(230,120),(300,140)],'D04'),
('L10','통장이 길',[q3,(250,240),(280,310),(400,340),(450,230)],'D06'),
('L11','곡물 길',[q2,(10,310),(-60,230),(-150,160)],'D05'),
('L12','남쪽 창고 뒤길',[(-310,230),(-305,330),(-150,355),(10,310)],'D05'),
('L13','구호원 골목',[w2,(-505,180),(-460,280),(-305,330)],'D10'),
('L14','과수원 길',[(-140,-370),(-60,-450),n1],'D08'),
('L15','성당 북쪽길',[(180,-290),(230,-400),(325,-450),(420,-400)],'D08'),
('L16','동쪽 주거 골목',[e2,(540,-50),(520,-160),(445,-225)],'D07'),
('L17','성채 기슭길',[(-480,-130),(-565,-45),w1],'D07'),
('L18','부두 안쪽길',[(-150,355),(-40,400),(100,390),q1],'D05'),
('A01','막다른 우물골목',[(-140,-80),(-220,-40),(-245,10)],'D07'),
('A02','도제 골목',[(-235,-105),(-185,-150),(-130,-205)],'D07'),
('A03','작은 교구 마당길',[(-150,160),(-240,110),w3],'D07'),
('A04','상인 안쪽 골목',[(25,120),(-15,65),W],'D04'),
('A05','상인 중정길',[e5,(185,70),(230,120)],'D04'),
('A06','화덕 골목',[(370,200),(390,115),e2],'D06'),
('A07','염색 뒤길',[(450,230),(520,285),(400,340)],'D06'),
('A08','하역 샛길',[(10,310),(20,245),q3],'D05'),
('A09','구호원 안뜰길',[(-425,170),(-390,260),(-305,330)],'D10'),
('A10','북쪽 주거 샛길',[(110,-340),(145,-405),(230,-400)],'D08'),
('A11','서쪽 임차 골목',[w1,(-470,20),(-405,-125)],'D07'),
('A12','시장 북서 샛길',[N,(-90,-95),(-140,-80)],'D04'),
('A13','필사실 아랫길',[(190,-160),(220,-235),(255,-255)],'D02'),
('A14','동쪽 계단길',[(390,-150),(345,-80),e3],'D06'),
('A15','남서 마당길',[(-220,175),(-200,265),(-150,355)],'D07'),
('A16','서쪽 후면길',[(-325,-205),(-370,-280),(-305,-320)],'D07'),
('A17','동쪽 주거 연결길',[e3,(400,-35),(495,-90),(520,-160)],'D07'),
('A18','작은 성당 계단길',[(400,-35),(390,-150)],'D07'),
]
for id,name,p,di in locals:route(id,name,p,2.6 if id.startswith('A')else 3.5,'local_lane',di,curve=not id.startswith('A'))
# Explicit two water posterns and a short quay loading street outside the wall.
watergates={}
for name,idx,t in [('west',7,.78),('east',6,.7)]:watergates[name]=lerp(wall[idx],wall[(idx+1)%len(wall)],t)
qw=(watergates['west'][0],455);qe=(watergates['east'][0],470)
route('RT_WATER_GATE_W','서쪽 수문 하역길',[(-305,330),watergates['west'],qw],4.5,'gate_approach','D05',curve=False,frontage=False)
route('RT_WATER_GATE_E','동쪽 수문 하역길',[(100,390),watergates['east'],qe],4.5,'gate_approach','D05',curve=False,frontage=False)
route('RT_QUAY','강변 하역길',[(-450,435),qw,(-100,465),qe,(214,456)],6,'quay_work_road','D05',frontage=True)
route('RT_BRIDGE','남문 돌다리',[gates['south'],(214,456),(225,520),(260,650)],7,'bridge',curve=False,frontage=False)
route('RT_SUBURB','문밖 마을길',[(-420,655),(-160,630),(65,660),(260,650),(460,685),(680,650)],6,'country_road','S01')
route('RT_SUB_E','동문 바깥길',[gates['east'],(705,175),(745,75),(725,-90)],5,'country_road','S01')
route('RT_SUB_LANE','문밖 뒷길',[(-160,630),(-100,685),(65,700),(260,650)],3,'local_lane','S01')
# Materialize the route graph without asserting elevations we have not designed.
nodes=[];nodekeys={};roads=[];roadindex=Index()
def node(p):
 key=(round(p[0],3),round(p[1],3))
 if key not in nodekeys:
  id=f'N{len(nodes)+1:04d}';nodekeys[key]=id;nodes.append({'id':id,'position_m':[key[0],None,key[1]],'elevation_status':'unresolved_profile'})
 return nodekeys[key]
for rt in routes:
 rt['road_ids']=[]
 for i,(a,b)in enumerate(zip(rt['polyline_xz_m'],rt['polyline_xz_m'][1:])):
  if distance(a,b)<.02:continue
  rid=f'{rt["id"]}.{i:03d}';roads.append({'id':rid,'route_id':rt['id'],'from_node':node(a),'to_node':node(b),'width_m':rt['width_m'],'kind':rt['kind'],'status':'planned','evidence':'design_inference','cart_access':rt['width_m']>=4.5});rt['road_ids'].append(rid);roadindex.add(segpoly(a,b,rt['width_m']),rid)
# Precincts reserve usable open courtyards rather than empty arbitrary blocks.
market=[[-60,-50],[70,-50],[70,40],[-60,40]]
castle_close=[[-530,-415],[-380,-435],[-300,-355],[-325,-250],[-500,-245],[-565,-325]]
cat_close=[[250,-415],[440,-405],[480,-320],[430,-240],[270,-240],[225,-340]]
gardens=[[[-250,-500],[-120,-510],[-100,-475],[-175,-420],[-250,-425]],[[-450,205],[-420,205],[-400,235],[-430,255]]]
reservations=[('market_square',market),('castle_precinct',castle_close),('cathedral_close',cat_close)]+[('garden',p) for p in gardens]
occupied=Index();wateridx=Index();wallidx=Index()
for a,b in zip(river,river[1:]):wateridx.add(segpoly(a,b,105),'river')
for a,b in zip(wall,wall[1:]+wall[:1]):wallidx.add(segpoly(a,b,8),'wall')
# The largest buildings are explicitly dimensioned, not scaled copies of a house.
counts=collections.Counter();buildings=[];plots=[];house=base['source_references']['assets'][0]
districts={x['id']:x for x in base['districts']}
def add_building(di,name,role,poly,entry,roadp,rid,tier='exterior_only',asset_status='new_assembly_required',parent_plot=None,source='design_inference',mode='walk_and_handcart'):
 counts[di]+=1;bid=f'{di}-B{counts[di]:03d}';cent=[sum(p[k]for p in poly)/len(poly)for k in(0,1)]
 b={'id':bid,'district_id':di,'name':name,'functional_role':role,'evidence':'design_inference','status':'planned_not_built','footprint_xz_m':poly,'ground_y_candidate_m':districts[di]['ground_y_candidate_m'],'height_candidate_m':rng.choice([7.5,9,10.8,12.5]),'entrance':{'position_xz_m':[round(v,3)for v in entry],'ground_y_candidate_m':districts[di]['ground_y_candidate_m'],'status':'planned_clearance_unverified'},'road_access':{'road_id':rid,'connection_xz_m':[round(v,3)for v in roadp],'mode':mode,'status':'planned'},'implementation_tier':tier,'asset_ref':house,'asset_usage':'palette_and_component_grammar_reference','assembly_status':asset_status,'assembly_note':'공통 집/부품의 재질·조립 문법 참조. 이 크기의 조립은 미제작.','source_kind':source,'inside_wall':inside(cent,wall),'plot_id':parent_plot}
 buildings.append(b);occupied.add(poly,bid);return b
rtby={x['id']:x for x in routes}
def at_route(rt,t):
 segs=list(zip(rt['polyline_xz_m'],rt['polyline_xz_m'][1:]));acc=0
 for i,(a,b)in enumerate(segs):
  length=distance(a,b)
  if acc+length>=t or i==len(segs)-1:
   f=max(0,min(1,(t-acc)/length));p=lerp(a,b,f);u=((b[0]-a[0])/length,(b[1]-a[1])/length);return p,u,rt['road_ids'][i]
  acc+=length

def landmark(di,name,role,c,w,d,entry,rid,tier='interior_selected'):
 rt=rtby[rid];p=rt['polyline_xz_m'][-1];b=add_building(di,name,role,rect(c,w,d),entry,p,rt['road_ids'][-1],tier,source='landmark_inferred_from_concept');return b
landmark('D01','큰 성 주성','castle_keep',(-440,-350),70,38,(-440,-331),'RT_CASTLE_COURT')['height_candidate_m']=32
landmark('D02','대성당','cathedral',(350,-330),32,80,(350,-290),'RT_CATHEDRAL_APPROACH')['height_candidate_m']=70
# Town hall is outside the market void; access meets north market edge.
rt=rtby['RT_MARKET_EDGE'];p,u,rid=at_route(rt,200)
add_building('D03','시청','town_hall',rect((0,-83),46,24),(0,-71),(0,-55),next(x['id']for x in roads if x['route_id']=='RT_MARKET_EDGE'and x['to_node']==node((0,-55))),'interior_selected')['height_candidate_m']=24
# Specific precinct wings share courtyard access; they are not unrelated rows of houses.
for name,c,w,d in [('성채 병영',(-515,-350),18,42),('성채 부엌',(-395,-390),25,18),('성채 곡물고',(-355,-360),18,32),('무기고',(-345,-310),20,24),('마구간',(-480,-410),42,18),('접견동',(-500,-285),38,18),('성채 예배당',(-390,-295),18,28)]:
 poly=rect(c,w,d)
 if not occupied.hits(poly) and not roadindex.hits(poly):add_building('D01',name,name,poly,(c[0],c[1]+d/2),castle_court,rtby['RT_CASTLE_CLIMB']['road_ids'][-1],'interior_selected'if name in('성채 병영','접견동')else'active_gameplay',mode='through_precinct_courtyard')
for name,c,w,d in [('회랑 서고',(280,-350),22,40),('참사회실',(295,-395),42,18),('성당 학교',(420,-355),24,36),('성직자 주택',(420,-300),24,22),('성당 작업장',(280,-285),25,20),('구호 예배당',(390,-255),20,20)]:
 poly=rect(c,w,d)
 if not occupied.hits(poly) and not roadindex.hits(poly):add_building('D02',name,name,poly,(c[0],c[1]+d/2),cat_court,rtby['RT_CATHEDRAL_APPROACH']['road_ids'][-1],'interior_selected'if name in('회랑 서고','성당 학교')else'active_gameplay',mode='through_precinct_courtyard')
# Candidate functions follow neighborhoods. Counts follow available frontage and yards.
def district(p,hint):
 x,z=p
 if hint=='S01':return'S01'
 if hint=='D05'and z>285:return'D05'
 if z<-345 and -300<x<230:return'D08'
 if x<-330 and z>120:return'D10'
 if 215<x<500 and z<-225:return'D02'
 if x<-320 and z<-240:return'D01'
 if distance(p,(0,0))<115:return'D03'
 if x>285 and z>-140:return'D06'
 if -100<x<285 and z>-210:return'D04'
 return'D07'
# Different frontages and plot depths are chosen per land use, not a fixed width.
sizes={'D01':([12,18,26],[18,25,35]),'D02':([10,16,22],[18,26,34]),'D03':([8,12,16,22],[18,24,30]),'D04':([6.4,8,10,14,18],[14,20,26,34]),'D05':([12,18,24,30],[18,26,34]),'D06':([8,12,18,24],[12,20,28,34]),'D07':([6.4,7.5,9,12,15],[10,14,19,24]),'D08':([8,12,16],[12,18,24]),'D10':([10,14,20],[14,20,30]),'S01':([8,12,18,25],[10,18,24])}
allr=sorted(routes,key=lambda x:0 if x['id']=='RT_SOUTH_MARKET'else 1 if x['kind']=='quay_work_road'else 2 if x['kind']=='cart_street'else 3)
for rt in allr:
 if not rt['frontage']:continue
 length=sum(distance(a,b)for a,b in zip(rt['polyline_xz_m'],rt['polyline_xz_m'][1:]))
 for side in(-1,1):
  t=8
  while t<length-8:
   p,u,rid=at_route(rt,t);di=district(p,rt['district_hint']);ws,ds=sizes[di];w=rng.choice(ws);dep=rng.choice(ds);t+=w/2
   if t>length-8:break
   p,u,rid=at_route(rt,t);normal=(-u[1]*side,u[0]*side);setback=rt['width_m']/2+rng.uniform(.2,.8)
   front=[p[k]+normal[k]*setback for k in(0,1)];center=[front[k]+normal[k]*dep/2 for k in(0,1)];poly=rect(center,w,dep,u)
   allowed=all(inside(q,wall)for q in poly)or(rt['kind']in('quay_work_road','country_road')or di=='S01')
   if any(abs(q[0])>790 or abs(q[1])>735 for q in poly):allowed=False
   if occupied.hits(poly)or roadindex.hits(poly,gap=.15)or wateridx.hits(poly,gap=2)or wallidx.hits(poly,gap=2):allowed=False
   if any(overlap(poly,shape)for _,shape in reservations):allowed=False
   # Open gardens and social compounds retain real unbuilt spaces.
   if di=='D08'and rng.random()<.48:allowed=False
   if di in('D01','D02')and rng.random()<.30:allowed=False
   if allowed:
    role={'D03':'시장 상점·주거','D04':'상인 점포·주거','D05':'창고·하역 작업','D06':'작업주거·생산','D07':'주거·생활 점포','D08':'정원사 주거·부속동','D10':'구호·숙박·주거','S01':'문밖 주거·여관·작업','D01':'성채 기슭 주거','D02':'성당 주변 주거'}[di]
    pid=f'P{len(plots)+1:04d}';b=add_building(di,f'{districts[di]["name"]} {counts[di]+1}',role,poly,front,p,rid,parent_plot=pid)
    # Reserve the long parcel and its courtyard intent, without inventing full interiors.
    rear_depth=rng.uniform(6,15);plotdep=dep+rear_depth;pc=[front[k]+normal[k]*plotdep/2 for k in(0,1)];plotpoly=rect(pc,w+1.8,plotdep,u)
    courtyard_center=[front[k]+normal[k]*(dep+rear_depth/2)for k in(0,1)];courtyard=rect(courtyard_center,max(3,w-1),max(3,rear_depth-1),u)
    if wateridx.hits(plotpoly)or wallidx.hits(plotpoly)or roadindex.hits(courtyard)or occupied.hits(courtyard):courtyard=None;plotpoly=poly
    plots.append({'id':pid,'district_id':di,'footprint_xz_m':plotpoly,'front_building_id':b['id'],'courtyard_xz_m':courtyard,'status':'initial_deep_plot_not_ownership_survey'})
   t+=w/2+rng.uniform(.2,1.2) if di in ('D03','D04','D07') else w/2+rng.uniform(.8,3.0)
# Some deep urban plots contain a rear workshop or store around a real yard.
# This is a functional parcel ensemble, not an additional road-front filler row.
front_by_id={b['id']:b for b in buildings}
for plot in plots:
 court=plot['courtyard_xz_m']
 if court is None:continue
 parent=front_by_id[plot['front_building_id']]
 if occupied.hits(court,ignore=parent['id']):
  plot['courtyard_xz_m']=None;plot['courtyard_status']='not_reserved_due_to_existing_footprint';continue
 poly=parent['footprint_xz_m'];u=((poly[1][0]-poly[0][0])/distance(poly[0],poly[1]),(poly[1][1]-poly[0][1])/distance(poly[0],poly[1]))
 cc=[sum(p[k] for p in court)/4 for k in (0,1)];fc=parent['entrance']['position_xz_m'];delta=[cc[k]-fc[k] for k in (0,1)];L=math.hypot(*delta);normal=[v/L for v in delta]
 width=distance(court[0],court[1]);depth=distance(court[1],court[2])
 if parent['district_id'] not in ('D03','D04','D05','D06','D07') or width<8 or depth<12 or rng.random()>.48:continue
 annex_depth=min(8,depth*.36);annex_width=width*rng.uniform(.8,1)
 c=[cc[k]+normal[k]*(depth/2-annex_depth/2) for k in (0,1)];ap=rect(c,annex_width,annex_depth,u)
 if occupied.hits(ap) or roadindex.hits(ap) or wateridx.hits(ap) or wallidx.hits(ap) or not all(inside(q,wall) for q in ap):continue
 entry=[c[k]-normal[k]*annex_depth/2 for k in (0,1)]
 a=add_building(parent['district_id'],'중정 뒤 작업동','rear_workshop_or_store',ap,entry,parent['road_access']['connection_xz_m'],parent['road_access']['road_id'],parent_plot=plot['id'],mode='via_shared_plot_passage')
 a['parent_building_id']=parent['id'];a['road_access']['passage_via_building']=parent['id'];a['road_access']['status']='covered_passage_required_unverified';parent['required_passage_width_m']=2
 plot['rear_building_id']=a['id'];newdepth=depth-annex_depth-.8;newc=[cc[k]-normal[k]*(annex_depth+.8)/2 for k in (0,1)];plot['courtyard_xz_m']=rect(newc,width,newdepth,u);plot['courtyard_status']='reserved_between_front_and_rear_buildings'
# Keep only genuinely unbuilt courtyard reservations after all ensembles are placed.
for plot in plots:
 court=plot['courtyard_xz_m']
 if court and occupied.hits(court,gap=0):plot['courtyard_xz_m']=None;plot['courtyard_status']='not_reserved_due_to_neighbor_geometry'
# Assign indispensable services to appropriate already-placeable buildings.
def name_near(di,name,loc,tier='active_gameplay',require_inside=None):
 pool=[b for b in buildings if b['district_id']==di and b['implementation_tier']=='exterior_only'and(require_inside is None or b['inside_wall']==require_inside)]
 if not pool:return None
 b=min(pool,key=lambda b:distance([sum(p[k]for p in b['footprint_xz_m'])/4 for k in(0,1)],loc));b['name']=name;b['functional_role']=name;b['implementation_tier']=tier;return b['id']
for di,name,loc,tier in[
 ('D03','공공 저울집',(30,55),'active_gameplay'),('D03','시장회관',(-65,35),'interior_selected'),('D03','빵 판매소',(-65,-20),'active_gameplay'),('D03','소금상',(75,25),'active_gameplay'),('D03','직물상',(70,-35),'active_gameplay'),('D04','상인 여관',(120,180),'interior_selected'),('D04','환전상',(100,0),'active_gameplay'),('D04','직물 창고',(210,190),'active_gameplay'),('D04','공증 서기',(150,-80),'active_gameplay'),('D05','세관',(100,390),'interior_selected'),('D05','곡물 창고',(-220,420),'active_gameplay'),('D05','수운 창고',(-120,440),'active_gameplay'),('D05','선원 주점',(-270,400),'interior_selected'),('D05','하역 관리소',(-300,435),'active_gameplay'),('D06','제분소',(400,250),'active_gameplay'),('D06','대장간',(460,210),'active_gameplay'),('D06','염색 작업장',(440,300),'active_gameplay'),('D06','목공소',(510,150),'active_gameplay'),('D06','수레 제작소',(500,200),'active_gameplay'),('D06','통 제작소',(400,330),'active_gameplay'),('D07','공동 빵집',(-220,110),'active_gameplay'),('D07','교구 교회',(-220,-110),'interior_selected'),('D07','동네 주점',(-140,160),'interior_selected'),('D10','구호원',(-420,210),'interior_selected'),('D10','배식 부엌',(-410,240),'active_gameplay'),('D10','약초 보관소',(-450,220),'active_gameplay'),('D10','수도원',(-465,175),'interior_selected'),('S01','남문 밖 여인숙',(260,650),'interior_selected'),('S01','수레 대기장 관리소',(320,665),'active_gameplay'),('D08','채소 집하장',(-40,-420),'active_gameplay')]:name_near(di,name,loc,tier)
# Gatehouses and wall towers use exact wall edges; wall is a separate circulation layer.
for idx,(a,b)in enumerate(zip(wall,wall[1:]+wall[:1])):
 routeid=f'WALL_{idx}';rid=routeid+'.000';roads.append({'id':rid,'route_id':routeid,'from_node':node(a),'to_node':node(b),'width_m':3,'kind':'wall_walk','status':'planned','evidence':'design_inference','cart_access':False})
for name,p in gates.items():
 idx=min(range(len(wall)),key=lambda i:distance(p,wall[i])+distance(p,wall[(i+1)%len(wall)]));a,b=wall[idx],wall[(idx+1)%len(wall)];L=distance(a,b);u=((b[0]-a[0])/L,(b[1]-a[1])/L);entry=[p[0]-u[1]*7,p[1]+u[0]*7];rid=rtby[{'south':'RT_SOUTH_MARKET','west':'RT_WEST_MARKET','east':'RT_EAST_MARKET','north':'RT_NORTH_MARKET'}[name]]['road_ids'][0]
 g=add_building('D09',{'south':'남문','west':'서문','east':'동문','north':'북문'}[name],'gatehouse',rect(p,18,14,u),entry,p,rid,'active_gameplay',mode='walk_and_cart_through_gate');g['opening_required_m']={'width':10,'height':5};g['height_candidate_m']=22
 roads.append({'id':'WALL_ACCESS_'+name,'route_id':'WALL_ACCESS','from_node':node(p),'to_node':node(a),'width_m':2,'kind':'pedestrian','status':'planned','evidence':'design_inference','cart_access':False})
for idx,(a,b)in enumerate(zip(wall,wall[1:]+wall[:1])):
 L=distance(a,b);u=((b[0]-a[0])/L,(b[1]-a[1])/L)
 for t in[.22,.52,.82]:
  p=lerp(a,b,t);poly=rect(p,11,11,u)
  if occupied.hits(poly,gap=3):continue
  entry=[p[0]-u[1]*5.5,p[1]+u[0]*5.5];tower=add_building('D09',f'성벽탑 {counts["D09"]-3}','wall_tower',poly,entry,p,f'WALL_{idx}.000',mode='stairs_to_wall_walk');tower['height_candidate_m']=18
# Conceptual utility and logistics edges do not imply a detailed simulation.
byname={b['name']:b['id']for b in buildings};links=[]
for label,a,b in[('곡물 하역','세관','곡물 창고'),('곡물 가공','곡물 창고','제분소'),('빵 생산','제분소','공동 빵집'),('시장 공급','공동 빵집','빵 판매소'),('구호 공급','공동 빵집','배식 부엌'),('직물 유통','세관','직물 창고'),('직물 판매','직물 창고','직물상'),('도시 기록','세관','시청'),('도구 생산','목공소','수레 제작소')]:
 if a in byname and b in byname:links.append({'id':f'FL{len(links)+1:02d}','name':label,'from_building':byname[a],'to_building':byname[b],'flow':'conceptual_goods_or_records','implementation':'abstract_transfer_or_selected_short_route','status':'conceptual_not_simulated'})
features=[{'id':'F_MARKET_FOUNTAIN','kind':'fountain','position_m':[-20,12,0],'asset_ref':base['source_references']['assets'][1],'requested_pitch_m':.1,'status':'planned_instance','evidence':'design_inference'},{'id':'F_MARKET_OPEN','kind':'market_square','footprint_xz_m':market,'status':'planned','evidence':'design_inference'},{'id':'F_CASTLE_CLOSE','kind':'precinct','footprint_xz_m':castle_close,'status':'planned_courtyard','evidence':'design_inference'},{'id':'F_CATHEDRAL_CLOSE','kind':'precinct','footprint_xz_m':cat_close,'status':'planned_courtyard','evidence':'design_inference'}]
for name,p in watergates.items():features.append({'id':'F_WATER_GATE_'+name,'kind':'water_postern','position_m':[p[0],None,p[1]],'opening_required_m':{'width':6.5,'height':4},'status':'opening_required_not_built','evidence':'design_inference'})
# Public courtyards, garden blocks and three short loading piers.
for i,poly in enumerate(gardens):features.append({'id':f'F_GARDEN_{i}','kind':'garden_reservation','footprint_xz_m':poly,'status':'planned_land_use','evidence':'design_inference'})
for i,x in enumerate([-380,-250,-120]):features.append({'id':f'F_PIER_{i}','kind':'loading_pier','footprint_xz_m':rect((x,480),7,46),'status':'planned_in_water_connection_unverified','evidence':'design_inference'})
used_well_plots=set()
for i,target in enumerate([(-205,-70),(-230,120),(110,205),(410,200),(-410,220),(50,-300),(-120,330),(300,-200)]):
 candidates=[]
 for plot in plots:
  court=plot.get('courtyard_xz_m')
  if not court or plot['id'] in used_well_plots:continue
  cc=[sum(p[k]for p in court)/4 for k in (0,1)]
  if not occupied.hits(rect(cc,3,3),gap=1):candidates.append((distance(cc,target),plot,cc))
 if candidates:
  _,plot,cc=min(candidates,key=lambda x:x[0]);used_well_plots.add(plot['id']);plot['public_access_required']=True
  features.append({'id':f'F_WELL_{i+1:02d}','kind':'well_courtyard_reservation','position_m':[cc[0],None,cc[1]],'plot_id':plot['id'],'status':'clear_2d_candidate_public_access_and_water_quality_unverified','evidence':'design_inference'})

for b in buildings:b['wall_relation']='on_wall' if b['district_id']=='D09' else 'inside' if b['inside_wall'] else 'outside'
# Preserve target quantities but report actual geometry separately.
base['schema']='riverstone.city.plan.v2'
base.update(revision=2,status='draft_layout_v2_reviewed_2d',seed=145002,layout_targets_not_constraints=True,road_nodes=nodes,roads=roads,street_routes=routes,building_plans=buildings,plots=plots,site_features=features,functional_links=links)
base['counts_report']={'building_footprints':len(buildings),'inside_wall':sum(b['wall_relation']=='inside'for b in buildings),'outside_wall':sum(b['wall_relation']=='outside'for b in buildings),'on_wall':sum(b['wall_relation']=='on_wall'for b in buildings),'districts':dict(counts),'tiers':dict(collections.Counter(b['implementation_tier']for b in buildings)),'road_segments':len(roads),'named_routes':len(routes),'courtyards':sum(bool(x['courtyard_xz_m'])for x in plots),'target_not_enforced':1440}
base['first_section']={'name':'남문에서 큰 시장까지','route_id':'RT_SOUTH_MARKET','road_ids':rtby['RT_SOUTH_MARKET']['road_ids'],'start_gate_building':byname['남문'],'end_anchor':[45,12,45],'deliverable':'coarse_terrain_plus_fine_surface_test_then_gate_market_street','terrain_test_span_m':32,'full_city_implementation':False}
base['infrastructure_networks']=[{'id':'U_QUAY_ACCESS','kind':'harbour_access','route_ids':['RT_QUAY','RT_WATER_GATE_W','RT_WATER_GATE_E'],'status':'two_posterns_and_quay_loading_road_planned','implementation':'two_controlled_openings_short_loading_road'},{'id':'U_DRINKING','kind':'water_supply','sources':[f'F_WELL_{i+1:02d}'for i in range(8)],'status':'well_cistern_conduit_design_no_network_geometry','implementation':'selected_water_points_only'},{'id':'U_DRAINAGE','kind':'drainage','downstream_outfall_candidate_xz_m':[670,450],'status':'local_gutters_cesspits_grade_unverified','implementation':'visible_local_gutters_and_state_flags'},{'id':'U_MILL_POWER','kind':'mill_power','building_id':byname.get('제분소'),'status':'animal_or_manual_power_for_inland_location','implementation':'milling_service_selected_animation'}]
base['limitations']=['2D layout design, not a historic reconstruction or game scene','Target 1440 is not enforced; actual footprints are reported separately','Road elevations are null until a terrain profile is authored; castle route length supports a candidate climb but local grades are unverified','Covered passages and courtyard access are explicit design requirements, not verified navmesh','New assemblies, all interiors and terrain coarse/fine seams remain unbuilt','Some secondary crossings need explicit navigation junction authoring in the game integration stage']
base['coordinate_system']['bounds_m']=[[-800,-24,-700],[800,130,760]]
base['coordinate_system']['road_node_y_policy']='null_until_height_profile_authored'
base['source_references']['layout_research']=[{'url':'https://tourismus.regensburg.de/fileadmin/user_upload/08_Prospekte_Downloads/Stadtplan_der_Regensburger_Altstadt.pdf','use':'urban fabric comparison; current map is not 1400 reconstruction'},{'url':'https://whc.unesco.org/en/list/624/maps/','use':'historic core spatial comparison; no traced geometry'}]
(R/'world_city/data/city_brief.v2.json').write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(base['counts_report'],ensure_ascii=False,indent=2))
