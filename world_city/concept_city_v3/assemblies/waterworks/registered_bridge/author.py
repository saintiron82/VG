"""Bounded native-width registered bridge candidate. Source generation only.

No compiler, terrain override, source-plan edit or object scale. The immutable
16 m arch grammar is rigidly repeated below a datum-following, explicitly
owned deck. Geometric joints and foundations are authored separately.
"""
from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from voxel_character.common import core
from world_city.runtime_city.parts.author import Source,extrusion
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.assemblies.landmarks.author import ref,write,source_bounds
from world_city.concept_city_v3.registered_topography import author as terrain

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
PLAN=ROOT/'world_city/concept_city_v3/registered_source/plan.json'
BASE=HERE.parent/'masters/stone_road_bridge_bay.json'
TERRAIN=ROOT/'world_city/concept_city_v3/registered_topography/author.py'
CONTROL=ROOT/'world_city/concept_city_v3/image_registration/controls.json'
AUTHOR=Path(__file__).relative_to(ROOT)
WIDTH=14.;CART=8.;WALK=2.4;PARAPET=.6;REPEAT=16.;FOUNDATION=-5.5
PROFILE_STEP=.25

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def relative(path):return str(path.relative_to(ROOT))
def sub(a,b):return [a[i]-b[i] for i in range(2)]
def add(a,b):return [a[i]+b[i] for i in range(2)]
def mul(a,s):return [a[i]*s for i in range(2)]
def unit(a):return mul(a,1/math.hypot(*a))
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def strip(a,b,width):
 n=mul([-b[1]+a[1],b[0]-a[0]],width/(2*math.dist(a,b)))
 return [add(a,n),sub(a,n),sub(b,n),add(b,n)]
def hull(points):
 ps=sorted(set(tuple(p) for p in points))
 def half(items):
  out=[]
  for p in items:
   while len(out)>1 and cross(sub(out[-1],out[-2]),sub(p,out[-1]))<=1e-10:out.pop()
   out.append(p)
  return out
 return [list(p) for p in half(ps)[:-1]+half(reversed(ps))[:-1]]
def bounds(p):return [min(q[0] for q in p),min(q[1] for q in p),max(q[0] for q in p),max(q[1] for q in p)]
def overlaps(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-9 and min(a[3],b[3])>max(a[1],b[1])+1e-9
def surface_y(profile,p):
 if "constant_y_m" in profile:return profile["constant_y_m"]
 _,t=terrain._project(*p,profile["a_xz_m"],profile["b_xz_m"])
 if "sample_y_m" in profile:
  ys=profile["sample_y_m"];f=t*(len(ys)-1);i=min(len(ys)-2,int(f));return ys[i]+(ys[i+1]-ys[i])*(f-i)
 return profile["a_y_m"]+t*(profile["b_y_m"]-profile["a_y_m"])
def disjoint(items):
 result=[]
 for item in items:
  parts=[item['polygon_xz_m']]
  for old in result:
   parts=[piece for p in parts for piece in (geo.convex_difference(p,old['polygon_xz_m']) if overlaps(bounds(p),bounds(old['polygon_xz_m'])) else [p]) if geo.polygon_area(piece)>1e-8]
  for n,p in enumerate(parts):result.append({**item,'id':item['id']+f':piece:{n}','polygon_xz_m':p,'vertex_y_m':[surface_y(item['surface_profile'],q) for q in p],'area_m2':geo.polygon_area(p)})
 return result

class Axis:
 def __init__(self,road):
  self.road=road;self.points=road['polyline_xz_m'];self.stations=[0.]
  for a,b in zip(self.points,self.points[1:]):self.stations.append(self.stations[-1]+math.dist(a,b))
  self.length=self.stations[-1]
 def at(self,s):
  s=max(0,min(self.length,s))
  i=next((i for i in range(len(self.stations)-1) if self.stations[i+1]>=s),len(self.stations)-2)
  t=(s-self.stations[i])/(self.stations[i+1]-self.stations[i]);a,b=self.points[i:i+2]
  return [a[k]+t*(b[k]-a[k]) for k in (0,1)]
 def station(self,p):
  best=None
  for i,(a,b) in enumerate(zip(self.points,self.points[1:])):
   d,t=terrain._project(*p,a,b);candidate=(d,self.stations[i]+t*(self.stations[i+1]-self.stations[i]))
   if best is None or candidate<best:best=candidate
  return best[1]
 def forward_chord(self,s,length):
  a=self.at(s);lo=s;hi=min(self.length,s+length+1)
  if math.dist(a,self.at(hi))<length:raise ValueError('native repeat exceeds source approach')
  for _ in range(55):
   mid=(lo+hi)/2
   if math.dist(a,self.at(mid))<length:lo=mid
   else:hi=mid
  return (lo+hi)/2

def cambered_height_at(x,z,axis,spec):
 s=axis.station([x,z]);old=terrain.road_height_at('MAIN_BRIDGE',x,z)
 lo,peak,hi=spec['start_station_m'],spec['crest_station_m'],spec['end_station_m']
 if s<=lo or s>=hi:return old
 anchor=spec['start_y_m'] if s<=peak else spec['end_y_m'];span=(peak-lo) if s<=peak else (hi-peak)
 raised=anchor+(spec['crest_y_m']-anchor)*(1-((s-peak)/span)**2)
 return max(old,raised)

def master14():
 m=copy.deepcopy(json.loads(BASE.read_text()));m['id']='v3_registered_stone_arch_bay_16x14'
 m['components']=[c for c in m['components'] if c['id']!='parapet'];m['instances']=[i for i in m['instances'] if i['component']!='parapet']
 m['constraints']=[c for c in m['constraints'] if c.get('selector',{}).get('component')!='parapet']
 for c in m['components']:
  for op in c['operations']:
   if op['id']=='stone_bay':op['shape']['min'][2],op['shape']['max'][2]=-7.,7.
   if op['id']=='barrel_opening':op['shape']['z_min'],op['shape']['z_max']=-7.01,7.01
 for c in m['constraints']:
  if c['id']=='road_deck':c['shape']['min'][2],c['shape']['max'][2]=-4.,4.
  if c['id']=='center_waterway':c['shape']['min'][2],c['shape']['max'][2]=-7.01,7.01
 e=m['extensions'];e['historical_local_head_labels']={k:e['authored_parameters'].pop(k) for k in ('water_y_m','candidate_bed_y_m')};e['datum']='Local Y=0 is arch masonry top, not finished deck. Registered cap profile, river head and exact bed belong to each placement.';m['provenance']['terrain_contract']=ref(relative(TERRAIN));e['authored_parameters'].update(deck_total_width_m=14,road_clear_width_m=8,sidewalk_each_width_m=2.4,parapet_each_width_m=.6,parapets_owned_by='separate datum-following deck caps',arch_top_is_finished_deck=False)
 for c in e['clearances']:
  if c['id']=='road_deck':c['region_m']['min'][2],c['region_m']['max'][2]=-4.,4.
  if c['id']=='center_waterway':c['region_m']['min'][2],c['region_m']['max'][2]=-7.01,7.01
 for s in e['supports']:s['contact_region_m']['min'][2],s['contact_region_m']['max'][2]=-7.,7.
 e['local_bounds_m']=source_bounds(m);e['footprint_xz_m']=[[-8,-7],[8,-7],[8,7],[-8,7]]
 e.update(compiled_sample=None,actual_placed=False,status='source_only_native_width_candidate',city_placement=None,terrain_placement=None)
 m['provenance']['registered_width_adaptation']={'author':ref(str(AUTHOR)),'original_master':ref(relative(BASE)),'method':'Change continuous transverse source bounds explicitly; original 16 m length, arch cut and half-pier geometry retained. No object scale.','observed':'Image registration MAIN_BRIDGE axis; visible deck broad relative to road.','inferred':'14 m exterior, 8 m cart, 2.4 m walks, 0.6 m parapets are design values.'}
 core.validate_master(m,.2);return m

def world_point(center,tangent,x,z):
 n=[-tangent[1],tangent[0]];return [center[k]+tangent[k]*x+n[k]*z for k in (0,1)]
def pose(center,y,tangent):return {'translation':[center[0],y,center[1]],'basis':[[tangent[0],0,-tangent[1]],[0,1,0],[tangent[1],0,tangent[0]]]}

def finish_source(a):
 m=a.finish();m['provenance'].update(author=ref(str(AUTHOR)),registered_plan=ref(relative(PLAN)),registered_terrain=ref(relative(TERRAIN)),new_compile=False)
 m['extensions']['local_bounds_m']=source_bounds(m);m['extensions'].update(status='source_only_native_profile_candidate',actual_placed=False,compiled_sample=None)
 core.validate_master(m,.2);return m

def cap_master(i,profile,origin_y):
 a=Source(f'registered_bridge_cap_{i:02}',[-8,0,-7],[8,5,7]);top=[[p['local_x_m'],p['deck_y_m']-origin_y] for p in profile]
 poly=[[-8,0],[8,0]]+list(reversed(top))
 a.op('profiled_deck_spandrel',extrusion(poly,-7,7),'stone',component='deck')
 for side in (-1,1):
  edge=side*6.7
  pp=top+[[x,y+1.1] for x,y in reversed(top)]
  a.op('parapet_'+str(side),extrusion(pp,edge-.3,edge+.3),'stone_light',component='parapets')
 a.support('arch_top',[-8,-.01,-7],[8,.01,7],'Unscaled 16 × 14 m arch bay below; cap solid joins the continuous arch top.')
 a.clearance('cart_lane',[-8,max(p[1] for p in top)+.01,-4],[8,max(p[1] for p in top)+3.5,4],'8 m cart lane; variable-floor clearance also checked in the profile contract.')
 a.design=['Deck top follows the explicit cambered road overlay, with original field/profile retained in evidence.','No elevated floor across water is delegated to earth terrain.']
 return finish_source(a)

def build():
 before={relative(p):sha(p) for p in (PLAN,TERRAIN,CONTROL,BASE)}
 plan=json.loads(PLAN.read_text());road=next(r for r in plan['roads'] if r['id']=='MAIN_BRIDGE');bridge=next(b for b in plan['bridges'] if b['id']=='BRIDGE_MAIN_RIVER');axis=Axis(road)
 water=[d for d in terrain.finite_water_polygons() if d['surface_id']=='MAIN_RIVER']
 # Nine native 16 m chords span the complete finite wet width, including dry-bank bearing piers.
 starts=[28.]
 for _ in range(9):starts.append(axis.forward_chord(starts[-1],REPEAT))
 camber={'start_station_m':starts[0],'crest_station_m':(starts[4]+starts[5])/2,'end_station_m':starts[-1],'start_y_m':terrain.road_height_at('MAIN_BRIDGE',*axis.at(starts[0])),'end_y_m':terrain.road_height_at('MAIN_BRIDGE',*axis.at(starts[-1])),'crest_y_m':4.0,'shape':'two joined quadratic camber halves, clamped from below by the frozen road field','approval_basis':'Parent requested at least 3 m normal-water clearance across declared central 6 m navigation channel, bank/gate endpoints retained and cart grade at most 10 percent.'}
 bays=[];sources=[];raw_decks=[];joints=[];support=[];field_error=[];registration_error=[];camber_pixel_delta=[];maximum_lift=[]
 base=master14();basepath=HERE/'masters/stone_arch_bay_16x14.json';write(basepath,base)
 for i,(s0,s1) in enumerate(zip(starts,starts[1:])):
  a,b=axis.at(s0),axis.at(s1);t=unit(sub(b,a));center=mul(add(a,b),.5)
  profile=[]
  for j in range(65):
   x=-8+j*.25;p=world_point(center,t,x,0);h=cambered_height_at(*p,axis,camber);old=terrain.road_height_at('MAIN_BRIDGE',*p)
   camber_pixel_delta.append(math.dist(terrain.project(p[0],h,p[1]),terrain.project(p[0],old,p[1])));maximum_lift.append(h-old)
   profile.append({'local_x_m':x,'xz_m':p,'deck_y_m':h,'original_road_y_m':old,'source_axis_station_m':axis.station(p)})
   q=axis.at(axis.station(p));registration_error.append(math.dist(terrain.project(*[p[0],old,p[1]]),terrain.project(q[0],terrain.road_height_at('MAIN_BRIDGE',*q),q[1])))
  origin_y=min(p['deck_y_m'] for p in profile)-.35
  # Explicit per-bay cap follows exact frozen road H. The shared arch remains rigid.
  cap=cap_master(i,profile,origin_y);cappath=HERE/f'masters/deck_cap_{i:02}.json';write(cappath,cap);sources.append(ref(relative(cappath)))
  shape=strip(a,b,14);cart=strip(a,b,8);polyitems=[]
  for j,(p,q) in enumerate(zip(profile,profile[1:])):
   pp=strip(p['xz_m'],q['xz_m'],14)
   polyitems.append({'id':f'DECK_BAY_{i:02}_{j:02}','polygon_xz_m':pp,'vertex_y_m':[p['deck_y_m'],p['deck_y_m'],q['deck_y_m'],q['deck_y_m']],'role':'elevated_bridge_deck','bay_id':f'ARCH_BAY_{i:02}','surface_profile':{'a_xz_m':p['xz_m'],'b_xz_m':q['xz_m'],'a_y_m':p['deck_y_m'],'b_y_m':q['deck_y_m']}})
   mid=mul(add(p['xz_m'],q['xz_m']),.5);field_error.append(abs((p['deck_y_m']+q['deck_y_m'])/2-cambered_height_at(*mid,axis,camber)))
  raw_decks.append({'id':f'DECK_BAY_{i:02}','polygon_xz_m':shape,'vertex_y_m':[profile[0]['deck_y_m']]*2+[profile[-1]['deck_y_m']]*2,'role':'elevated_bridge_deck','bay_id':f'ARCH_BAY_{i:02}','surface_profile':{'a_xz_m':a,'b_xz_m':b,'sample_y_m':[p['deck_y_m'] for p in profile],'sample_pitch_m':.25}})
  pier_samples=[];footing_polys=[];extension_source=Source(f'registered_bridge_footings_{i:02}',[-8,-10,-7],[8,-5.5,7])
  for end in (-1,1):
   ground_points=[world_point(center,t,end*u,v) for u in (7.,7.5,8.) for v in (-7,-3.5,0,3.5,7)]
   native_bottom=origin_y+FOUNDATION;bottom=min(native_bottom,min(terrain.height_at(*q) for q in ground_points)-.5)
   if bottom<native_bottom-1e-7:
    x0,x1=(-8,-7) if end<0 else (7,8)
    extension_source.box(f'bed_reaching_half_pier_{end}',[x0,bottom-origin_y,-7],[x1,FOUNDATION,7],'stone_dark',component='pier_extensions')
   footing_polys.append({'end_sign':end,'polygon_xz_m':hull([world_point(center,t,end*u,v) for u in (7,8) for v in (-7,7)]),'native_foundation_y_m':native_bottom,'foundation_y_m':bottom,'extension_height_m':native_bottom-bottom})
   for u in (7.05,7.5,8.):
    for v in (-7,-3.5,0,3.5,7):
     p=world_point(center,t,end*u,v);wet=terrain.water_samples_at(*p);ground=terrain.height_at(*p)
     pier_samples.append({'xz_m':p,'foundation_y_m':bottom,'native_foundation_y_m':native_bottom,'extension_height_m':native_bottom-bottom,'bearing_ground_y_m':ground,'water_y_m':terrain.river_water_y(p[0]) if wet else None,'embed_m':ground-bottom,'wet':bool(wet)})
  extension_ref=None
  if extension_source.components:
   ep=HERE/f'masters/pier_extensions_{i:02}.json';write(ep,finish_source(extension_source));extension_ref=ref(relative(ep));sources.append(extension_ref)
  under=[]
  for j in range(13):
   x=-3+j*.5;p=world_point(center,t,x,0);head=terrain.river_water_y(p[0]);under.append({'xz_m':p,'water_y_m':head,'arch_soffit_y_m':origin_y+(-.65-.075*abs(x) if abs(x)<=2 else -.8-.25*(abs(x)-2)),'datum':'native source arch crown profile'})
  record={'id':f'ARCH_BAY_{i:02}','source':ref(relative(basepath)),'cap_source':ref(relative(cappath)),'source_station_range_m':[s0,s1],'center_xz_m':center,'endpoints_xz_m':[a,b],'transform':pose(center,origin_y,t),'scale_xyz':[1,1,1],'arch_top_y_m':origin_y,'footprint_xz_m':shape,'cart_lane_polygon_xz_m':cart,'deck_profile':profile,'foundation_samples':pier_samples,'underarch_samples':under,'assembly_group_id':'REGISTERED_MAIN_BRIDGE','native_length_m':16,'native_width_m':14,'footings':footing_polys,'pier_extension_source':extension_ref}
  bays.append(record);support.extend(pier_samples)
 # Fill only the small planar wedge between neighboring rigid bay end faces.
 # These explicit continuous common-source joints unite half piers and cap edges.
 joint_source=Source('registered_bridge_joints',[-200,-10,380],[200,5,580])
 for i,(left,right) in enumerate(zip(bays,bays[1:])):
  p=left['endpoints_xz_m'][1];poly=hull(left['footprint_xz_m'][2:]+right['footprint_xz_m'][:2]);top=cambered_height_at(*p,axis,camber);bottom=min(left['footings'][-1]['foundation_y_m'],right['footings'][0]['foundation_y_m'])
  if geo.polygon_area(poly)<1e-8:continue
  joint_source.plan(f'joint_pier_{i}',poly,bottom,top,'stone',component='pier_joints')
  # Boundary edge ribbons continue the parapet around the angular join, leaving cart and walks open.
  for side,idx in ((-1,0),(1,1)):
   # local transverse signs: footprint indices 0/+ and 1/-, end 3/+ and 2/-.
   li=2 if side<0 else 3;ri=1 if side<0 else 0
   a=left['footprint_xz_m'][li];b=right['footprint_xz_m'][ri]
   ai=add(p,mul(sub(a,p),6.4/7));bi=add(p,mul(sub(b,p),6.4/7));par=hull([a,b,ai,bi])
   if geo.polygon_area(par)>1e-8:joint_source.plan(f'joint_parapet_{i}_{idx}',par,top,top+1.1,'stone_light',component='parapet_joints')
  joints.append({'id':f'BRIDGE_JOINT_{i:02}','polygon_xz_m':poly,'deck_y_m':top,'foundation_y_m':bottom,'area_m2':geo.polygon_area(poly),'assembly_group_id':'REGISTERED_MAIN_BRIDGE'})
  raw_decks.append({'id':f'JOINT_DECK_{i:02}','polygon_xz_m':poly,'vertex_y_m':[top]*len(poly),'surface_profile':{'constant_y_m':top},'role':'elevated_bridge_joint'})
 joint_master=finish_source(joint_source);jp=HERE/'masters/bridge_joints.json';write(jp,joint_master);sources.append(ref(relative(jp)))
 # Approach ownership tapers after the existing wall opening, preserving its source width.
 gate=next(g for g in plan['gates'] if g['road_id']=='MAIN_BRIDGE');gate_s=axis.station(gate['position_xz_m']);taper_start=gate_s+2
 def width_at(s):
  if s<=taper_start:return 7.
  if s<starts[0]:return 7+7*(s-taper_start)/(starts[0]-taper_start)
  if s<=starts[-1]:return 14.
  return 14-7*(s-starts[-1])/(axis.length-starts[-1])
 approaches=[]
 for tag,lo,hi in [('north',0,starts[0]),('south',starts[-1],axis.length)]:
  ss=sorted(set([lo,hi]+[s for s in axis.stations if lo<s<hi]+[lo+(hi-lo)*j/math.ceil((hi-lo)/.5) for j in range(1,math.ceil((hi-lo)/.5))]+([taper_start] if lo<taper_start<hi else [])))
  for i,(s0,s1) in enumerate(zip(ss,ss[1:])):
   a,b=axis.at(s0),axis.at(s1);t=unit(sub(b,a));n=[-t[1],t[0]];wa,wb=width_at(s0),width_at(s1);poly=[add(a,mul(n,wa/2)),sub(a,mul(n,wa/2)),sub(b,mul(n,wb/2)),add(b,mul(n,wb/2))];ya,yb=terrain.road_height_at('MAIN_BRIDGE',*a),terrain.road_height_at('MAIN_BRIDGE',*b)
   item={'id':f'APPROACH_{tag}_{i:03}','role':'dry_supported_cart_approach','polygon_xz_m':poly,'vertex_y_m':[ya,ya,yb,yb],'width_start_end_m':[wa,wb],'surface_profile':{'a_xz_m':a,'b_xz_m':b,'a_y_m':ya,'b_y_m':yb},'source_station_range_m':[s0,s1],'grade':abs(yb-ya)/math.dist(a,b)};approaches.append(item)
 # Abutment finite bands are outside all actual water domains, not merely centreline dry.
 abutments=[]
 for tag,bay,end in [('north',bays[0],-1),('south',bays[-1],1)]:
  center=bay['center_xz_m'];t=unit(sub(*reversed(bay['endpoints_xz_m'])));pts=[world_point(center,t,end*x,z) for x,z in ((8,-7),(7,-7),(7,7),(8,7))];poly=hull(pts);wetarea=sum(geo.polygon_area(geo.convex_intersection(poly,w['polygon_xz_m'])) for w in water)
  abutments.append({'id':'ABUTMENT_'+tag.upper(),'polygon_xz_m':poly,'bearing_foundation_y_m':bay['footings'][0 if end<0 else -1]['foundation_y_m'],'water_overlap_area_m2':wetarea,'source_bay_id':bay['id'],'support':'Native terminal half-pier on dry bank; bank fill/cut faces require ownership integration.'})
 # Widening must not consume new buildings; overlap at road/gate is a planned connection.
 allpolys=[p['polygon_xz_m'] for p in raw_decks+approaches];conflicts=[]
 for b in plan['buildings']:
  fp=b.get('footprint_xz_m')
  if not fp:continue
  bb=bounds(fp)
  if bb[3]<380 or bb[0]>160 or bb[2]<100:continue
  area=sum(geo.polygon_area(geo.convex_intersection(p,fp)) for p in allpolys)
  if area>1e-6:conflicts.append({'building_id':b['id'],'area_m2':area})
 deck_owned=disjoint(raw_decks);approach_owned=disjoint(approaches)
 navbay=bays[4];nt=unit(sub(navbay['endpoints_xz_m'][1],navbay['endpoints_xz_m'][0]));nc=navbay['center_xz_m']
 navigation_underdeck=hull([world_point(nc,nt,x,z) for x in (-3,3) for z in (-7,7)])
 navigation_approach=hull([world_point(nc,nt,x,z) for x in (-3,3) for z in (-50,50)])
 navigation_water_polys=[geo.convex_intersection(navigation_approach,w['polygon_xz_m']) for w in water];navigation_water_polys=[p for p in navigation_water_polys if geo.polygon_area(p)>1e-8]
 result={'schema':'riverstone.registered_bridge_candidate.v1','id':'REGISTERED_MAIN_BRIDGE','status':'source_only_candidate_pending_common_compile_and_runtime_review','source_plan':ref(relative(PLAN)),'terrain_author':ref(relative(TERRAIN)),'registration_controls':ref(relative(CONTROL)),'source_master':ref(relative(BASE)),'author':ref(str(AUTHOR)),
 'observed_vs_inferred':{'observed':'Original MAIN_BRIDGE image axis and existing source street/gate adjacency.','inferred':'14 m exterior deck, native 16 m repeats, nine bays, profile caps, foundations, 8 m cart lane, two walks and parapets. No inverse-survey or structural certification.'},
 'road_id':'MAIN_BRIDGE','bridge_id':'BRIDGE_MAIN_RIVER','trace_pixel_xy':road['original_trace_pixel_xy'],'source_centerline_xz_m':axis.points,'source_four_control_level_labels_m':terrain.ROAD_LEVELS['MAIN_BRIDGE'],'source_resolved_deck_range_y_m':[min(road['levels_m']),max(road['levels_m'])],
 'camber_overlay':camber,'original_low_field_candidate':ref(relative(HERE/'evidence/low_field_r0/candidate.json')),
 'navigation_channel':{'bay_id':bays[4]['id'],'underdeck_polygon_xz_m':navigation_underdeck,'proposed_water_approach_polygons_xz_m':navigation_water_polys,'approach_reservation_basis':'Inferred 6 m corridor extending 50 m each side of bridge centre, clipped to finite river domains; reserve from piers and moored boats, not a certified navigation route.','local_longitudinal_interval_m':[-3,3],'local_transverse_interval_m':[-7,7],'normal_water_clearance_target_m':3,'normal_water_transverse_conservative_margin_m':.025,'normal_water_clearance_min_m':min(p['arch_soffit_y_m']-p['water_y_m'] for p in bays[4]['underarch_samples'])-.025,'claim':'One declared 6 m normal-stage channel through the central arch. No masted-ship, flood or hydraulic capacity certificate.'},
 'width_reconciliation':{'original_road_width_m':road['width_m'],'original_bridge_record_width_m':bridge['width_m'],'proposed_deck_total_width_m':14,'proposed_cart_lane_width_m':8,'sidewalk_each_m':2.4,'parapet_each_m':.6,'source_plan_modified':False,'gate_id':gate['id'],'gate_opening_width_m':gate['opening_width_m'],'gate_station_m':gate_s,'width_at_gate_m':width_at(gate_s),'full_width_station_range_m':[starts[0],starts[-1]],'north_taper_begins_station_m':taper_start,'reason':'Preserve the current 7 m gate approach; widen only beyond the wall, with dry southern narrowing.'},
 'bays':bays,'joint_source':ref(relative(jp)),'joint_transform':{'translation':[0,0,0],'basis':[[1,0,0],[0,1,0],[0,0,1]]},'joints':joints,'deck_regions':deck_owned,'approach_regions':approach_owned,'abutments':abutments,'sources':[ref(relative(basepath))]+sources,'compile_invocations':0,'actual_scene_placements':0,
 'ownership':{'terrain_role':'Remove earth deck across water; river water and bed stay below finite elevated deck ownership.','pier_role':'Nine native arch bays and small joint wedges have explicitly sampled bed-reaching supports. Water simulation has not subtracted pier volumes.','deck_datum':'Explicit camber overlay above frozen road_height_at, fixed dry-bank/gate endpoints, flat transverse sections. Quarter-metre samples and linear interpolation.','ordinary_source_pack_unchanged':True},
 'checks':{'minimum_foundation_embed_m':min(s['embed_m'] for s in support),'maximum_half_sample_deck_error_m':max(field_error),'maximum_centerline_registration_change_px':max(registration_error),'maximum_approach_grade':max(a['grade'] for a in approaches),'maximum_authored_deck_grade':max(abs(q['deck_y_m']-p['deck_y_m'])/math.dist(p['xz_m'],q['xz_m']) for b in bays for p,q in zip(b['deck_profile'],b['deck_profile'][1:])),'maximum_camber_lift_m':max(maximum_lift),'maximum_camber_image_delta_px':max(camber_pixel_delta),'central_navigation_clearance_m':min(p['arch_soffit_y_m']-p['water_y_m'] for p in bays[4]['underarch_samples'])-.025,'maximum_pier_extension_m':max(s['extension_height_m'] for s in support),'minimum_underarch_normal_head_clearance_m':min(p['arch_soffit_y_m']-p['water_y_m'] for b in bays for p in b['underarch_samples']),'total_owned_deck_area_m2':sum(p['area_m2'] for p in deck_owned),'total_owned_approach_area_m2':sum(p['area_m2'] for p in approach_owned),'new_building_conflicts':conflicts,'abutments_dry':all(a['water_overlap_area_m2']<1e-7 for a in abutments),'source_immutability':all(sha(ROOT/p)==h for p,h in before.items())},
 'remaining_limits':['No common sample or Godot collision exists for this 14 m variant yet.','Native arch/cap/joint volumes require assembly-union or explicit internal-face handling at rigid bay joints before separate cached rendering.','Footing embed is geometric only: soil strength, flood, scour, loads and hydraulic capacity are unverified.','The original low cone-field profile is preserved in evidence. The explicit cambered deck is a bounded functional correction requiring image review.','Only one declared central 6 m channel has a 3 m normal-stage target; masted ships, flood clearance and navigational operation are not certified.','Approach cut/fill skirts and south-bank continuation beyond the source endpoint require terrain ownership integration.']}
 write(HERE/'candidate.json',result)
 summary={'pack':ref(relative(HERE/'candidate.json')),'bays':len(bays),'native_master_count':len(result['sources']),'joint_count':len(joints),'deck_regions':len(deck_owned),'approach_regions':len(approach_owned),'source_centerline_length_m':axis.length,'native_arch_span_m':len(bays)*16,**result['checks'],'new_compiles':0,'scene_placements':0};write(HERE/'summary.json',summary)
 print(json.dumps(summary,indent=2));return result

if __name__=='__main__':build()
