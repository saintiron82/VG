"""Bounded, additive port work and market-edge dressings using native common assets.
Run as a module from the repository root. Never writes outside this pack directory.
"""
from __future__ import annotations
import collections,copy,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
from world_city.runtime_city.checks import placement as geo
from world_city.runtime_city.parts.author import make_master
from voxel_character.common.coordinate_planes import compile_master
from voxel_character.common.render_data import make_render_data
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
CITY=ROOT/'world_city/concept_city_v3'
BASE=CITY/'evidence/r8_final110_runtime_r01/scene.json'
BASE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
CATALOG=CITY/'traversal_r5/revisions/r06_r8_precinct/primary_goals_extension_r01/route_catalog_493_r02.json'
CERTIFIED=CITY/'traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04/selected_all493_bound_r02.json'
MARKET=CITY/'assemblies/market/registered/r3_clusters/resolved_placements.json'
WALK=CITY/'assemblies/market/registered/r3_clusters/walkspace_report.json'
PORT=CITY/'assemblies/landmarks/registered/port_r01/access_proposals.json'
PLAN=CITY/'registered_source/plan.json'

def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def ref(p):return dict(path=rel(p),sha256=sha(p))
def write(p,d):
 p=Path(p);assert HERE==p.parent or HERE in p.parents;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def local(p,x,z,y=0):
 c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);q=p['position_m'];return[q[0]+c*x+s*z,q[1]+y,q[2]-s*x+c*z]
def ring(bounds,p,margin=0):
 a,b=bounds['min'],bounds['max'];return[[q[0],q[2]]for q in [local(p,x,z)for x,z in [(a[0]-margin,a[2]-margin),(b[0]+margin,a[2]-margin),(b[0]+margin,b[2]+margin),(a[0]-margin,b[2]+margin)]]]
def overlap(a,b):return geo.positive_area_overlap(a,b,0)
def zone(poly):
 lo=[min(p[k]for p in poly)for k in (0,1)];hi=[max(p[k]for p in poly)for k in (0,1)]
 return (hi[0]>-390 and lo[0]<112 and hi[1]>250 and lo[1]<470) or (hi[0]>15 and lo[0]<185 and hi[1]>-15 and lo[1]<105)
def square(x,z,r):return [[x-r,z-r],[x+r,z-r],[x+r,z+r],[x-r,z+r]]

class Reservations:
 def __init__(self,scene):
  self.rows=[];self.index=geo._SpatialIndex(16)
  self.routes=load(CATALOG)['routes'];self.directional_count=sum(2 if r.get('bidirectional')else 1 for r in self.routes)
  assert len(self.routes)==254 and self.directional_count==493
  def add(id,poly,kind):
   if len(poly)>2 and zone(poly):self.index.add(len(self.rows),poly);self.rows.append(dict(id=id,polygon=poly,kind=kind))
  def line(id,points,width,kind):
   for a,b in zip(points,points[1:]):
    if math.dist(a,b)>1e-9:add(id,geo.road_ribbon(a,b,width),kind)
   # Endcaps explicitly reserve capsule/road turning room at every vertex.
   for x,z in points:
    radius=(width/2)/math.cos(math.pi/32)
    add(id,[[x+radius*math.cos((i+.5)*math.pi/16),z+radius*math.sin((i+.5)*math.pi/16)]for i in range(32)],kind)
  for r in self.routes:
   pts=[[p[0],p[2]]for p in r['points_xyz_m']];line(r['id'],pts,max(1.2,r.get('source_width_m') or 0), 'public_493')
  self.certified=load(CERTIFIED)['routes'];assert len(self.certified)==493
  for r in self.certified:
   pts=[[p[0],p[2]]for p in r['points']];line('CERTIFIED:'+r['id'],pts,max(1.2,r.get('source_width_m') or 0),'certified_493_exact')
  market=load(MARKET);over={r['id']:r for r in market['access_overlay']['replace_roads']}
  for r in load(PLAN)['roads']:
   r=over.get(r['id'],r);line('ROAD:'+r['id'],r['polyline_xz_m'],r['width_m'],'source_public_road')
  for r in load(PORT)['routes']:line(r['id'],r['polyline_xz_m'],r['width_m'],'port_loading_3m')
  for r in load(WALK)['stall_routes']:line(r['stall_id']+':CUSTOMER',r['path_xz_m'],r['width_m'],'market_customer_2.4m')
  fountain=next(p for p in scene['common_instances']if p['id']=='MARKET_FOUNTAIN');x,_,z=fountain['position_m']
  add('MARKET_FOUNTAIN:10M_GATHERING',[[x+10*math.cos(i*math.pi/16),z+10*math.sin(i*math.pi/16)]for i in range(32)],'gathering')
 def hits(self,p):return sorted({self.rows[i]['id']for i in self.index.candidates(p) if overlap(p,self.rows[i]['polygon'])})

class World:
 def __init__(self,scene):
  self.scene=scene;self.assets=scene['common_assets'];self.instances={p['id']:p for p in scene['common_instances']};self.solids=[];self.solidindex=geo._SpatialIndex(16);self.native_surfaces=[]
  for p in scene['common_instances']:
   a=self.assets[p['asset_key']];b=a.get('bounds')
   if b is None:b=load(ROOT/a['render_path'])['bounds']
   poly=ring(b,p)
   if not zone(poly):continue
   lo=p['position_m'][1]+b['min'][1];hi=p['position_m'][1]+b['max'][1]
   self.solidindex.add(len(self.solids),poly);self.solids.append((p['id'],poly,lo,hi))
   if p['id'].startswith(('PORT_QUAY_RUN_','PORT_PIER_')):
    self.native_surfaces.append((p['id'],poly,hi))
  for p in scene['boxes']:
   size=p['size_m'];b={'min':[-v/2 for v in size],'max':[v/2 for v in size]};poly=ring(b,p)
   if zone(poly):self.solidindex.add(len(self.solids),poly);self.solids.append((p['id'],poly,p['position_m'][1]-size[1]/2,p['position_m'][1]+size[1]/2))
  self.reservations=Reservations(scene)
  # Local actual-scene triangle support extraction; no new terrain or export.
  triangles=[];keys=[]
  for key,verts in scene['surfaces'].items():
   if key in ('water','bank'):continue
   a=np.asarray(verts,dtype=np.float64).reshape((-1,3,3));lo=a.min(axis=1);hi=a.max(axis=1)
   near=((hi[:,0]>-390)&(lo[:,0]<112)&(hi[:,2]>250)&(lo[:,2]<470))|((hi[:,0]>15)&(lo[:,0]<185)&(hi[:,2]>-15)&(lo[:,2]<105))
   flat=(hi[:,1]-lo[:,1])<.03
   near &= flat & (lo[:,1]>1.95)&(hi[:,1]<4.2)
   aa=a[near]
   for t in aa:
    poly=t[:,[0,2]].tolist()
    if geo.polygon_area(poly)>1e-9:triangles.append(t.tolist());keys.append(key)
  self.tris=triangles;self.trikeys=keys;self.groundindex=geo._SpatialIndex(8)
  for i,t in enumerate(triangles):self.groundindex.add(i,[[p[0],p[2]]for p in t])
  self.water=[[[p[0],p[2]]for p in scene['surfaces']['water'][i:i+3]]for i in range(0,len(scene['surfaces']['water']),3)]
 def support(self,poly,y):
  points=poly+[[sum(p[k]for p in poly)/len(poly) for k in (0,1)]]+[[ (a[k]+b[k])/2 for k in (0,1)]for a,b in zip(poly,poly[1:]+poly[:1])]
  out=[]
  for x,z in points:
   hits=[]
   for id,q,h in self.native_surfaces:
    if abs(h-y)<.03 and geo.point_in_convex_polygon([x,z],q,1e-6):hits.append((h,id))
   for i in self.groundindex.candidates(square(x,z,.0001)):
    t=self.tris[i];q=[[p[0],p[2]]for p in t]
    if geo.point_in_convex_polygon([x,z],q,1e-6):
     a,b,c=t;den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
     if abs(den)<1e-12:continue
     u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den;v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den
     h=u*a[1]+v*b[1]+(1-u-v)*c[1]
     if abs(h-y)<.03:hits.append((h,'scene:'+self.trikeys[i]))
   if not hits:return None
   out.append(dict(xz=[x,z],y_m=round(hits[0][0],6),source=hits[0][1]))
  return out
 def blocked(self,poly,lo,hi):
  return sorted({id for i in self.solidindex.candidates(poly)for id,q,a,b in [self.solids[i]]if b>lo+.04 and a<hi-.04 and overlap(poly,q)})

def get_assets(scene):
 sources={'crate':'registered_precinct_r06_cargo_crate','wood_stack':'b13_workyard_wood_stack','cooper_bench':'b13_workyard_cooper_bench','rack':'dry_work_rack_store','workbench':'workbench','awning':'market_r3_cloth8'}
 assets={}
 for name,oldkey in sources.items():
  a=copy.deepcopy(scene['common_assets'][oldkey]);assert sha(ROOT/a['master_path'])==a['master_sha256'];assert sha(ROOT/a['render_path'])==a['render_sha256'];a['reuse_source_asset_key']=oldkey;assets['r9_port_'+name]=a
 master=make_master('cargo_barrel');mp=HERE/'masters/cargo_barrel.json';write(mp,master);comp=compile_master(master,{'pitch':.125},max_candidate_cells=30000,max_output_cells=20000);assert comp['valid'];rd=make_render_data(comp);rp=HERE/'cache/cargo_barrel.render.json';write(rp,rd)
 assets['r9_port_barrel']=dict(master_path=rel(mp),master_sha256=sha(mp),render_path=rel(rp),render_sha256=sha(rp),bounds=rd['bounds'],pitch_m=.125,quad_count=rd['quad_count'],generator=ref(ROOT/'world_city/runtime_city/parts/author.py'),existing_recipe='cargo_barrel')
 return assets

PATTERNS={
 'grain_dispatch':[('crate',-1.25,-.7,0),('crate',0,-.7,0),('crate',1.25,-.7,0),('crate',-1.25,.55,0),('crate',0,.55,0),('crate',1.25,.55,0),('crate',-1.25,-.7,.75),('crate',0,-.7,.75),('crate',1.25,-.7,.75)],
 'barrel_bond':[('barrel',x,z,0)for z in (-.7,.7)for x in (-1.25,0,1.25)],
 'timber_repair':[('wood_stack',-2,0,0),('cooper_bench',2,0,0),('barrel',2,2,0)],
 'covered_tally':[('awning',0,0,0),('crate',-3,-3.5,0),('crate',-1.75,-3.5,0),('barrel',2,-3.5,0),('barrel',3.25,-3.5,0)],
 'cloth_warehouse':[('rack',-2,0,0),('workbench',2,0,0),('crate',2,2,0),('crate',.75,2,0)],
 'pier_transfer':[('crate',0,z,0)for z in (-1.25,0,1.25)]+[('crate',0,z,.75)for z in (-1.25,0)],
 'market_grain':[('crate',x,z,0)for x in (-.6,.6)for z in (-.6,.6)]+[('crate',-.6,-.6,.75)],
 'market_casks':[('barrel',x,z,0)for x in (-.6,.6)for z in (-.6,.6)],
 'market_repair':[('workbench',0,0,0),('barrel',2.2,0,0)],
 'market_cloth':[('rack',0,0,0),('crate',2.2,0,0)]}

def candidates(world):
 out=[]
 def candidate(id,owner,xy,kind,y=None,yaw=None):
  p=world.instances[owner];pos=local(p,*xy);pos[1]=p['position_m'][1] if y is None else y
  out.append(dict(id=id,owner=owner,kind=kind,position_m=pos,yaw_rad=p['yaw_rad']if yaw is None else yaw,local_anchor_xz_m=list(xy)))
 for i in range(6):
  for j,x in enumerate((-23,-8,8,23)):
   candidate(f'R9_PORT_SHED_{i}_BAY_{j}',f'PORT_SHED_{i}',(x,7.5),['grain_dispatch','barrel_bond'][(i+j)%2])
 # Quay workspaces are outside the broad public through-road; a maximum of one accepted configuration per named working bay.
 for i in range(4):
  for j,x in enumerate((-40,-15,15,40)):
   candidate(f'R9_PORT_QUAY_{i}_WORK_{j}',f'PORT_QUAY_RUN_{i}',(x,-6),['barrel_bond','covered_tally','grain_dispatch','timber_repair'][(i+j)%4])
 for i in range(3):
  # Only shoreward pier corner: central 3m cart/capsule spine is separately protected.
  for j,z in enumerate((-8,4)):
   candidate(f'R9_PORT_PIER_{i}_LOAD_{j}',f'PORT_PIER_{i}',(-2.5,z),'pier_transfer')
 # Explicit MARKET perimeter sites; no removal/rearrangement of native stalls.
 for i,(x,z,kind)in enumerate([(26,15,'market_grain'),(26,38,'market_casks'),(26,66,'market_repair'),(39,91,'market_grain'),(61,91,'market_cloth'),(85,91,'market_casks'),(113,91,'market_grain'),(136,91,'market_cloth'),(163,72,'market_repair'),(169,48,'market_casks'),(162,24,'market_grain'),(140,4,'market_cloth'),(116,-2,'market_grain'),(66,-2,'market_casks')]):
  out.append(dict(id=f'R9_MARKET_EDGE_{i:02d}',owner='SITE_MARKET',kind=kind,position_m=[x,4,z],yaw_rad=.1,local_anchor_xz_m=None))
 return out

def build():
 started=time.monotonic();assert sha(BASE)==BASE_SHA;scene=load(BASE);world=World(scene);assets=get_assets(scene);accepted=[];groups=[];rejected=[];reserved=[]
 site=next(s['polygon_xz_m']for s in load(PLAN)['spaces']if s['id']=='SITE_MARKET')
 for c in candidates(world):
  entries=[];fail=[]
  for j,(name,x,z,stack)in enumerate(PATTERNS[c['kind']]):
   key='r9_port_'+name;a=assets[key];p=dict(id=c['id']+f':{j:02d}_{name}',asset_key=key,position_m=local(c,x,z),yaw_rad=c['yaw_rad'],scale=[1,1,1],palette_id='native_cargo',palette_override={},source_pack='r9_port_market',function=c['kind'],group_id=c['id'],source_owner=c['owner'])
   # Native bottom exactly meets the ground or the native crate below.
   floor=c['position_m'][1];p['position_m'][1]=floor-a['bounds']['min'][1]+stack
   poly=ring(a['bounds'],p);lo=floor+stack;hi=p['position_m'][1]+a['bounds']['max'][1]
   if c['owner']=='SITE_MARKET' and not geo.convex_polygon_contains(site,poly,0):fail.append('outside_market_owner')
   if c['owner'].startswith('PORT_QUAY_RUN_'):
    supportpoly=ring(world.assets[world.instances[c['owner']]['asset_key']]['bounds'],world.instances[c['owner']])
    if not geo.convex_polygon_contains(supportpoly,poly,0):fail.append('outside_quay_owner')
   if c['owner'].startswith('PORT_PIER_'):
    pier=world.instances[c['owner']];bound=world.assets[pier['asset_key']]['bounds'];supportpoly=ring(bound,pier)
    if not geo.convex_polygon_contains(supportpoly,poly,0):fail.append('outside_pier_owner')
    # Central 3m longitudinal loading lane remains entirely empty.
    spine=ring({'min':[-1.5,0,-13],'max':[1.5,0,13]},pier)
    if overlap(poly,spine):fail.append('pier_central_3m_spine')
   routes=world.reservations.hits(poly)
   if routes:fail+=['reserved:'+s for s in routes]
   solids=world.blocked(poly,lo,hi)
   if solids:fail+=['solid:'+s for s in solids]
   # Water under an existing pier is permitted only inside that original native deck, never new river occupation.
   if not c['owner'].startswith('PORT_PIER_') and any(overlap(poly,q)for q in world.water):fail.append('water_reservation')
   support=world.support(poly,floor)
   if support is None:fail.append('actual_support_not_proven')
   if stack:
    below=[q for q in entries if q['position_m'][1]+assets[q['asset_key']]['bounds']['max'][1]<=lo+1e-6 and abs(q['position_m'][1]+assets[q['asset_key']]['bounds']['max'][1]-lo)<1e-6 and geo.convex_polygon_contains(q['footprint_xz_m'],poly,1e-6)]
    if not below:fail.append('stack_support_not_proven')
    p['stack_support_id']=below[0]['id']if below else None
   for other,q,yl,yh in reserved+[(e['id'],e['footprint_xz_m'],e['native_bottom_y_m'],e['native_top_y_m'])for e in entries]:
    if yh>lo+1e-6 and yl<hi-1e-6 and overlap(poly,q):fail.append('new_group_overlap:'+other)
   p.update(footprint_xz_m=poly,native_bottom_y_m=lo,native_top_y_m=hi,support_floor_y_m=floor,support_samples=support or [])
   if name=='awning':p.update(palette_id='port_weathered_canvas',palette_override={'plaster_light':['c8b78e','b76f50','d7c7a4','c4bc9e'][len(groups)%4]})
   entries.append(p)
  if fail:rejected.append(dict(group=c['id'],kind=c['kind'],reasons=sorted(set(fail))));continue
  accepted+=entries;groups.append(dict(**c,placement_ids=[p['id']for p in entries]))
  reserved.extend((p['id'],p['footprint_xz_m'],p['native_bottom_y_m'],p['native_top_y_m'])for p in entries)
 affected=[]
 for route in world.reservations.routes:
  pts=[[p[0],p[2]]for p in route['points_xyz_m']]
  nearby=[]
  for p in accepted:
   poly=p['footprint_xz_m']
   for a,b in zip(pts,pts[1:]):
    if math.dist(a,b)>1e-9 and overlap(poly,geo.road_ribbon(a,b,20)):
     nearby.append(p['id']);break
  if nearby:affected.append(dict(route_id=route['id'],nearby_within_10m_instance_ids=nearby,directions=2 if route.get('bidirectional')else 1,static_reserved_ribbon_clear=True))
 used={p['asset_key']for p in accepted};assets={k:v for k,v in assets.items()if k in used}
 pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=BASE_SHA,common_assets=assets,add_instances=accepted,remove_instance_ids=[],inspection_cameras={'r9_port_working_quay':dict(position_m=[-125,55,492],target_m=[-155,2.2,400],ortho_size_m=150,render_size_px=[1536,1024]),'r9_market_goods_edge':dict(position_m=[112,65,165],target_m=[100,4,45],ortho_size_m=120,render_size_px=[1536,1024])})
 # Eye cameras are anchored to retained public loading/customer routes, never to a new prop.
 port_link=next(r for r in load(PORT)['routes']if r['id']=='PORT_SHED_2:loading_bay_16:PUBLIC_LINK')
 px,pz=port_link['polyline_xz_m'][-1];port_eye=[px,3.85,pz]
 port_target=next(g['position_m']for g in groups if g['id']=='R9_PORT_SHED_2_BAY_2');port_target=[port_target[0],3.3,port_target[2]]
 market_link=next(r for r in load(WALK)['stall_routes']if r['stall_id']=='MARKET_stall_6_6:south')
 mx,mz=market_link['customer_front_xz_m'];market_eye=[mx,5.65,mz]
 camera_checks=[]
 for name,eye,target,route,floor in [('r9_port_loading_eye',port_eye,port_target,port_link['id'],2.2),('r9_market_edge_eye',market_eye,[113,4.9,91],market_link['stall_id']+':CUSTOMER',4)]:
  poly=square(eye[0],eye[2],.3);base_hits=world.blocked(poly,floor,floor+1.8)
  added_hits=[p['id']for p in accepted if p['native_top_y_m']>floor+.04 and p['native_bottom_y_m']<floor+1.8 and overlap(poly,p['footprint_xz_m'])]
  support=world.support(poly,floor);assert not base_hits and not added_hits and support,(name,base_hits,added_hits)
  pack['inspection_cameras'][name]=dict(position_m=eye,target_m=target,eye_height_m=1.65,source_route=route,purpose='Camera on retained clear route, looking across working goods toward the existing frontage; static standing check only.')
  camera_checks.append(dict(id=name,source_route=route,capsule_radius_m=.3,capsule_height_m=1.8,support_samples=support,base_solid_hits=base_hits,added_solid_hits=added_hits))
 write(HERE/'camera_checks.json',dict(schema='riverstone.camera.static_standing_checks.v1',cameras=camera_checks))
 write(HERE/'pack.json',pack);write(HERE/'placement_plan.json',dict(schema='riverstone.port_market.functional_groups.v1',groups=groups,rejected_candidates=rejected,rule='Atomic functional groups accepted only after all members pass. No requested or implied density target.'))
 report=dict(schema='riverstone.port_market.static_clearance.v1',status='PASS'if accepted else 'FAIL_NO_ACCEPTED_GROUPS',source_refs=[ref(p)for p in [BASE,PLAN,CATALOG,CERTIFIED,MARKET,WALK,PORT]],base_scene_unchanged=sha(BASE)==BASE_SHA,pack=ref(HERE/'pack.json'),unique_public_paths_checked=254,exact_certified_directional_paths_checked=len(world.reservations.certified),directional_replay_cases_preserved_by_static_exclusion=493,port_loading_links_preserved=18,market_customer_paths_preserved=104,capsule=dict(runtime_radius_m=.3,runtime_height_m=1.8,minimum_static_centerline_reserved_width_m=1.2,scope='Conservative horizontal exclusions, with full road widths where declared; no new physics replay claimed.'),accepted_groups=len(groups),accepted_instances=len(accepted),native_asset_count=len(assets),new_native_compiles=1,functional_groups=collections.Counter(g['kind']for g in groups),rejected_groups=len(rejected),affected_routes=affected,support_sample_count=sum(len(p['support_samples'])for p in accepted),minimum_y_m=min((p['native_bottom_y_m']for p in accepted),default=None),maximum_y_m=max((p['native_top_y_m']for p in accepted),default=None),bounds_xy_rule='Complete native cache bounds, not artistic proxy or center-only exclusion.',water_rule='No accepted additions overlap water triangles except goods wholly inside preexisting pier deck footprints; no boats, shoreline, water or collision mutations.',limits=['Static geometry checks do not constitute a new capsule, cart, NPC, handling or shipping simulation.','The retained market grid and its 104 customer routes remain unchanged; additions identify edge trades, not wholesale organic relocation.','Actual visual integration and close-camera review belong to the root preview task.','Supports are nine actual-scene/native-deck samples per ground footprint; stacked crates require containment on an accepted native crate top.'],seconds=round(time.monotonic()-started,2))
 write(HERE/'static_clearance_report.json',report)
 print(json.dumps({k:report[k]for k in ['status','accepted_groups','accepted_instances','functional_groups','rejected_groups','seconds']}));print('rejections',collections.Counter(reason.split(':')[0]for r in rejected for reason in r['reasons']))
 return report
if __name__=='__main__':build()
