"""Cheap image-registered source draft; no mesh compiler or source mutation."""
from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from collections import Counter
from .controls import RAW,SOURCE,ESTATE_REFINEMENTS,build_controls,inverse
from .geometry import inside,triangulate,faces
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.registered_topography import author as terrain
HERE=Path(__file__).parent;CITY=HERE.parent

def area(p):return g.polygon_area(p)
def center(p):return [sum(q[k] for q in p)/len(p) for k in (0,1)]
def transform(p,origin,yaw):return [origin[0]+math.cos(yaw)*p[0]+math.sin(yaw)*p[1],origin[1]-math.sin(yaw)*p[0]+math.cos(yaw)*p[1]]
def box(pos,w,d,yaw=0):return [transform(p,pos,yaw) for p in [[-w/2,-d/2],[w/2,-d/2],[w/2,d/2],[-w/2,d/2]]]
def xz(q):return [q[0],q[2]]
def nearest(point,roads):
 result=[]
 for r in roads:
  for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   ll=sum((b[k]-a[k])**2 for k in (0,1))
   if ll<1e-9:continue
   t=max(0,min(1,sum((point[k]-a[k])*(b[k]-a[k]) for k in (0,1))/ll));q=[a[k]+t*(b[k]-a[k]) for k in (0,1)]
   result.append((math.dist(point,q),r['id'],q,i,t))
 return sorted(result)
class Domain:
 def __init__(self,polygons=()):self.polys=[];self.index=g._SpatialIndex(32);self.ids=[];[self.add(p) for p in polygons]
 def add(self,p,identity=None):
  for q in ( [p] if g.is_convex_polygon(p) else triangulate(p)):
   if area(q)>1e-6:self.index.add(len(self.polys),q);self.polys.append(q);self.ids.append(identity)
 def hits(self,p,ignore=()):return any(self.ids[i] not in ignore and g.positive_area_overlap(p,self.polys[i],1e-6) for i in self.index.candidates(p))
 def contains(self,p):return sum(area(g.convex_intersection(p,self.polys[i])) for i in self.index.candidates(p))>=area(p)-1e-5

def build():
 controls=build_controls();source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest();raw={p['id']:p for p in RAW['polygons']}
 wall=copy.deepcopy(terrain.registered_wall());boundary=wall['polygon_xz_m']
 # If the terrain version has not yet adopted the reviewed castle perimeter,
 # replace only the two provisional points that visibly cut across its precinct.
 if wall['trace_pixel_xy'][:2]==[[234,112],[411,81]]:
  points=[[178,116],[241,83],[403,67]]+wall['trace_pixel_xy'][2:];levels=[24,24,24]+wall['levels_m'][2:]
  xyz=[inverse(p,h) for p,h in zip(points,levels)];boundary=[xz(p) for p in xyz]
  wall.update(trace_pixel_xy=points,levels_m=levels,world_xyz_m=xyz,polygon_xz_m=boundary,edge_refinement='Castle perimeter follows existing CASTLE trace; no convex hull or global boundary expansion.')
 roads=copy.deepcopy(terrain.registered_roads());known={r['id'] for r in roads}
 for rc in controls['roads']:
  if rc['id'] in known:continue
  xyz=[terrain.registered_point(p) for p in rc['trace_pixel_xy']]
  roads.append(dict(rc,kind='inferred_image_aligned_connector',polyline_xz_m=[xz(p) for p in xyz],levels_m=[p[1] for p in xyz],resolved_world_xyz_m=xyz))
 for r in roads:
  pixels=r.get('control_pixel_xy')
  r['frontage_control_polyline_xz_m']=[xz(terrain.registered_point(q)) for q in pixels] if pixels else r['polyline_xz_m']
 p={'schema':'riverstone.city.source_plan.v3','revision':'registered_r0','status':'cheap_image_registered_spatial_draft_pending_review',
  'registration':{'controls_path':str(SOURCE.relative_to(HERE.parents[2])),'controls_sha256':source_hash,'source_image_sha256':RAW['source_image_sha256'],'camera_model':RAW['camera_model'],'limits':RAW['limits'],'original_controls_preserved':True},
  'inspection_cameras':{'registered':RAW['matched_engine_camera']},'boundary_xz_m':boundary,'wall_registration':wall,'districts':[],'spaces':[],'grounds':[],'plots':[],'buildings':[],'roads':roads,'paths':[],'blocks':[],'gates':[],'bridges':[],
  'correspondences':[],'inferred_connectors':[r['id'] for r in controls['roads'] if r['evidence_kind']=='inferred_image_aligned_connector'],
  'height_policy':'pad_floor_y_m is finished entrance floor; cached asset origin=pad_floor_y_m minus actual cached door-local Y. Preserve real offset doors and independently reserve their approaches.',
  'source_policy':{'old_frozen_source_unchanged':True,'whole_house_scaling':False,'compile_count':0,'building_count_is_not_target':True,'image_registration_is_design_hypothesis_not_inverse_survey':True},'unresolved':[]}
 colors={'CASTLE':'#92867c','TRAIN':'#c7ab81','NOBLE':'#adba8b','CLERGY':'#b2b29b','MARKET':'#d4c398','MONASTERY':'#9db185','POOR':'#b19a83','PORT':'#a1a79c','COMMON':'#8fa77b','BASIN':'#519ca9'}
 sitepolys={}
 for identity in ('CASTLE','TRAIN','NOBLE','CLERGY','MARKET','MONASTERY','POOR','PORT','COMMON','BASIN','CEMETERY','CLOISTER'):
  q=raw[identity];poly=[xz(inverse(a,q['assumed_height_m'])) for a in q['trace_pixel_xy']];sitepolys[identity]=poly
  rec={'id':'D_'+identity,'role':{'NOBLE':'noble','POOR':'poor','CLERGY':'clergy','MARKET':'merchant','PORT':'port'}.get(identity,identity.lower()),'polygon_xz_m':poly,'color':colors.get(identity,'#b1b6a0'),'registration_control_id':identity,'area_m2':area(poly),'trace_pixel_xy':q['trace_pixel_xy'],'assumed_floor_y_m':q['assumed_height_m']}
  if identity not in ('CEMETERY','CLOISTER'):p['districts'].append(rec)
  if identity not in ('POOR','NOBLE'):
   p['spaces'].append({'id':'SITE_'+identity,'role':q['role'],'polygon_xz_m':poly,'registration_control_id':identity,'area_m2':area(poly),'trace_pixel_xy':q['trace_pixel_xy'],'finished_floor_y_m':q['assumed_height_m'],'ownership_status':'traced_precinct_with_explicit_public_route_cuts','observed_vs_inferred':q['evidence'],'facility_program':{'TRAIN':['open_drill_field','archery_butts','barracks','horse_exercise_edge'],'MONASTERY':['church_and_cloister','orchard','kitchen_beds','charity_service_court'],'CLERGY':['cathedral','cloister','cemetery','canons_houses','school','kitchen_garden'],'MARKET':['grain_stalls','produce_stalls','cart_hold','civic_procession_corridor'],'COMMON':['small_wooded_common','public_walk','neighborhood_rest_space'],'PORT':['warehouse_frontage','bulk_loading_aprons','cranes','docks','quay_route'],'CASTLE':['keep_and_curtains','inner_and_outer_courts','service_range','gate_approach']}.get(identity,[q['role']])})
  p['correspondences'].append({'id':identity,'registration_control_id':identity,'trace_pixel_xy':q['trace_pixel_xy'],'world_xyz_m':[inverse(a,q['assumed_height_m']) for a in q['trace_pixel_xy']],'kind':'precinct_boundary','status':'same_image_trace_at_declared_datum'})
 p['districts'].append({'id':'D_MIXED','role':'merchant','polygon_xz_m':boundary,'color':'#b8a58d','priority':'fallback_only; named districts take precedence','area_m2':area(boundary),'observed_vs_inferred':'Untraced central/northern connected mixed-town envelope; individual blocks and plots provide actual ownership.'})
 estates=[]
 for q in RAW['estates']:
  refine=ESTATE_REFINEMENTS.get(q['id']);pixels=refine['pixels'] if refine else q['trace_pixel_xy'];ys=refine['ys'] if refine else [q['assumed_height_m']]*len(pixels);xyz=[inverse(a,h) for a,h in zip(pixels,ys)];poly=[xz(a) for a in xyz]
  e={'id':q['id'],'district_id':'D_NOBLE','property_type':'noble_estate_registered','land_use':'enclosed_noble_compound','polygon_xz_m':poly,'area_m2':area(poly),'trace_pixel_xy':pixels,'original_trace_pixel_xy':q['trace_pixel_xy'],'world_boundary_xyz_m':xyz,'pad_floor_y_m':q['assumed_height_m'],'registration_control_id':q['id'],'observed_vs_inferred':refine['reason'] if refine else q['evidence'],'assembly_intent':'dimension_authored_main_hall_service_lodge_stable_and_enclosed_garden; irregular_boundary_recipe_required','origin_xz_m':center(poly),'yaw_rad':-.1,'block_id':'NOBLE_'+q['id']}
  estates.append(e);p['plots'].append(e);p['correspondences'].append({'id':q['id'],'registration_control_id':q['id'],'trace_pixel_xy':pixels,'original_trace_pixel_xy':q['trace_pixel_xy'],'world_xyz_m':xyz,'kind':'estate_boundary','status':e['observed_vs_inferred']})
 waterpolys=[]
 for w in terrain.finite_water_polygons():
  poly=w.get('polygon_xz_m',[])
  if poly:waterpolys.append(poly)
 canal=[]
 for w in terrain.WATERS:
  # Reserve bank/service strips independently from finite wet polygons.
  width=w['width_m']+6
  canal.extend(g.road_ribbon(a,b,width) for a,b in zip(w['polyline_xz_m'],w['polyline_xz_m'][1:]))
 waterblock=Domain(waterpolys+canal)
 p['water_reservations']={'registered_water_module':'world_city.concept_city_v3.registered_topography.author','source_trace_ids':[w['id'] for w in RAW['water']],'finite_water_polygons':terrain.finite_water_polygons(),'channels':copy.deepcopy(terrain.WATERS),'river_north_shore_xz_m':terrain.SHORE,'reservoir_water_polygon_xz_m':sitepolys['BASIN'],'reservoir_outer_polygon_xz_m':sitepolys['BASIN'],'service_canal_polyline_xz_m':terrain.WATER_BY_ID['CRAFT_CANAL_VISIBLE']['polyline_xz_m'],'service_corridor_width_m':12,'river_polygon_xz_m':terrain.SHORE+[[terrain.SHORE[-1][0],terrain.SHORE[-1][1]+120],[terrain.SHORE[0][0],terrain.SHORE[0][1]+120]]}
 boundary_domain=Domain([boundary]);protected=Domain([sitepolys[k] for k in ('CASTLE','TRAIN','NOBLE','CLERGY','MARKET','MONASTERY','COMMON','BASIN')]);property_domain=Domain();building_domain=Domain();road_domain=Domain()
 proxy_path=CITY/'assemblies/landmarks/registered/proxy_masses.json'
 registered_proxies=json.loads(proxy_path.read_text()) if proxy_path.exists() else None
 if registered_proxies:
  for group in registered_proxies['groups']:
   origin=group['world_anchor_xyz_m']
   for m in group['masses']:
    pos=[origin[0]+m['position_local_xyz_m'][0],origin[2]+m['position_local_xyz_m'][2]]
    protected.add(box(pos,m['size_xyz_m'][0],m['size_xyz_m'][2],math.radians(m.get('yaw_degrees',0))),group['id'])
 for r in roads:
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):
   if math.dist(a,b)>1e-6:road_domain.add(g.road_ribbon(a,b,r['width_m']+.2),r['id'])
 def did(pos):
  if inside(pos,sitepolys['POOR']):return 'D_POOR'
  if pos[1]<-120:return 'D_MIXED'
  return 'D_MIXED'
 # Actual road-enclosed faces, not rectangles, define where interior alleys may go.
 face_roads=[dict(r,polyline_xz_m=r['frontage_control_polyline_xz_m']) for r in roads]
 for i,(poly,edge_ids) in enumerate(faces(face_roads,boundary)):
  if area(poly)<250:continue
  c=center(poly);bl={'id':f'BLOCK_{i:03d}','polygon_xz_m':poly,'area_m2':area(poly),'district_id':did(c),'boundary_road_ids':sorted(set(edge_ids)-{'WALL'}),'plot_ids':[],'interior_path_ids':[],'observed_vs_inferred':'Face bounded by registered streets and explicit connectors; exact interior court layout is authored.'};p['blocks'].append(bl)
  if area(poly)<2800 or protected.hits(box(c,2,2)):continue
  edges=[(a,b,rid) for a,b,rid in zip(poly,poly[1:]+poly[:1],edge_ids) if rid!='WALL' and math.dist(a,b)>18]
  options=[]
  for ai,(a,b,ar) in enumerate(edges):
   aa=[(a[k]+b[k])/2 for k in (0,1)]
   for cc,dd,br in edges[ai+1:]:
    bb=[(cc[k]+dd[k])/2 for k in (0,1)]
    if math.dist(aa,bb)<35:continue
    bend=[.46*aa[k]+.54*bb[k] for k in (0,1)];bend[0]+=3;bend[1]-=2;line=[aa,bend,bb];ribs=[g.road_ribbon(u,v,3.4) for u,v in zip(line,line[1:])]
    if not all(inside([u[k]+t*(v[k]-u[k]) for k in (0,1)],poly) for u,v in zip(line,line[1:]) for t in (.08,.2,.4,.6,.8,.92)):continue
    if any(protected.hits(rib) or waterblock.hits(rib) for rib in ribs):continue
    options.append((math.dist(aa,bb),line,ar,br))
  if options:
   _,line,ar,br=max(options,key=lambda v:v[0]);rid=bl['id']+':ALLEY';r={'id':rid,'kind':'inferred_connected_block_alley','width_m':2.4,'polyline_xz_m':line,'block_id':bl['id'],'connects_road_ids':[ar,br],'registration_control_id':None,'observed_vs_inferred':'Bent two-entry interior alley inferred within an actual registered road face; no observed street claim.'};roads.append(r);bl['interior_path_ids'].append(rid)
   for a,b in zip(line,line[1:]):road_domain.add(g.road_ribbon(a,b,2.6),rid)
 def mass(identity,district,function,pos,w,d,floors,yaw,plotid,roadid,extra=None):
  poly=box(pos,w,d,yaw);entrance=transform([0,d/2],pos,yaw)
  rec={'id':identity,'district_id':district,'function':function,'position_xz_m':pos,'width_m':w,'depth_m':d,'height_m':4.2+3*floors,'floors':floors,'yaw_rad':yaw,'entrance_xz_m':entrance,'road_id':roadid,'plot_id':plotid,'footprint_xz_m':poly,'assembly_intent':'immutable_common_catalog_exact_dimensions_no_scale','pad_floor_y_m':terrain.building_floor_at(*entrance),'ground_height_policy':'finished_threshold_floor; cached_origin_is_floor_minus_door_local_y','social_class':'wage_labor_and_craft' if district=='D_POOR' else 'merchant_and_mixed_household','roof_material':'brown_shingle' if district=='D_POOR' else 'red_clay','observed_vs_inferred':'Individual modular building is an authored mass aligned to the registered street; not an image-traced building.'}
  if extra:rec.update(extra)
  p['buildings'].append(rec);building_domain.add(poly,identity);return rec
 # Ordinary street fronts and deep rear courts. Every facade reserves a complete
 # lateral access strip before the proxy mass, allowing real offset cached doors.
 count=0
 for road in list(roads):
  if road['id'] in ('RESERVOIR_SERVICE','MAIN_BRIDGE','PORT_QUAY','PORT_BRIDGE_TIE','CASTLE_APPROACH','NOBLE_RISE','NOBLE_PUBLIC_TIE','CLERGY_EAST_GATE','CATHEDRAL_APPROACH'):continue
  frontage_line=road.get('frontage_control_polyline_xz_m',road['polyline_xz_m'])
  for si,(a,b) in enumerate(zip(frontage_line,frontage_line[1:])):
   length=math.dist(a,b)
   if length<10:continue
   ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length
   for side in (-1,1):
    n=[-uz*side,ux*side];cursor=5.;sequence=0
    while cursor<length-3:
     chord_q=[a[0]+ux*cursor,a[1]+uz*cursor];_,_,q,actual_segment,_=nearest(chord_q,[road])[0]
     ra,rb=road['polyline_xz_m'][actual_segment:actual_segment+2];actual_len=math.dist(ra,rb);au=[(rb[k]-ra[k])/actual_len for k in (0,1)];n=[-au[1]*side,au[0]*side]
     guess=[q[k]+n[k]*10 for k in (0,1)];district=did(guess);poor=district=='D_POOR'
     widths=[6,8,6,10] if poor else [8,10,12,6];width=widths[(sequence+si)%4];depth=([10,14,10,14] if poor else [14,18,10,14])[(sequence+si)%4];sequence+=1
     if cursor+width/2>length-1:break
     yaw=math.atan2(-n[0],-n[1]);offset=road['width_m']/2+2.6+depth/2;pos=[q[k]+n[k]*offset for k in (0,1)];parcel_center=[q[k]+n[k]*(road['width_m']/2+.2+(depth+5.4)/2) for k in (0,1)];parcel=box(parcel_center,width+.6,depth+5.4,yaw)
     if not boundary_domain.contains(parcel) or protected.hits(parcel) or waterblock.hits(parcel) or road_domain.hits(parcel) or property_domain.hits(parcel):cursor+=2;continue
     identity=f'B_REG_{count:04d}';plotid=f'P_REG_{count:04d}';floors=1+(sequence+si)%2 if poor else 2+(sequence+si)%2
     bld=mass(identity,district,'poor_attached_lodging_and_workshop' if poor else 'shop_house_and_productive_court',pos,width,depth,floors,yaw,plotid,road['id'])
     front_center=[q[k]+n[k]*(road['width_m']/2+1.4) for k in (0,1)];front=box(front_center,width+.6,2.4,yaw)
     q_actual=nearest(q,[road])[0][2]
     rec={'id':plotid,'district_id':district,'property_type':'street_frontage_plot','polygon_xz_m':parcel,'land_use':bld['function'],'area_m2':area(parcel),'width_m':width+.6,'depth_m':depth+5.4,'origin_xz_m':parcel_center,'yaw_rad':yaw,'road_id':road['id'],'gate_position_xz_m':bld['entrance_xz_m'],'gate_connection_xz_m':q_actual,'frontage_reservation_polygon_xz_m':front,'frontage_reservation_width_m':width+.6,'frontage_reservation_depth_m':2.4,'assembly_intent':'common_house_with_rear_workcourt','observed_vs_inferred':'Exact modular parcel authored on registered street tangent; door tie uses actual dense road.'}
     block=next((v for v in p['blocks'] if inside(pos,v['polygon_xz_m'])),None)
     if block:rec['block_id']=block['id'];block['plot_ids'].append(plotid)
     p['plots'].append(rec);property_domain.add(parcel,plotid);p['paths'].append({'id':identity+':DOOR','owner_building_id':identity,'owner_plot_id':plotid,'road_id':road['id'],'polyline_xz_m':[bld['entrance_xz_m'],q_actual],'width_m':1.8,'kind':'provisional_centered_entry; full_lateral_frontage_reserved','status':'actual_cached_door_offset_to_resolve_before_placement'})
     count+=1;cursor+=width+.7
 # Estate masses use the finite irregular holding and leave a connected central
 # service spine. The local search is bounded by each traced compound, not a city grid.
 for estate in estates:
  poly=estate['polygon_xz_m'];domain=Domain([poly]);c=center(poly);choices=nearest(c,roads);_,rid,gate,_,_=choices[0];v=[c[k]-gate[k] for k in (0,1)];length=math.hypot(*v);direction=[v[k]/length for k in (0,1)];yaw=math.atan2(-direction[0],-direction[1]);estate['road_id']=rid;estate['gate_position_xz_m']=gate
  estate_path=[gate,c];spine=Domain([g.road_ribbon(gate,c,3)]);p['paths'].append({'id':estate['id']+':SERVICE','owner_plot_id':estate['id'],'road_id':rid,'polyline_xz_m':estate_path,'width_m':3,'kind':'inferred_private_estate_service_spine','status':'candidate_clearance_review_required'})
  specs=[('main_hall',24,30,3),('stable',10,24,1),('servant_lodge',12,14,2),('kitchen',8,10,1)] if estate['area_m2']>3300 else [('main_hall',16,24,3),('stable',8,18,1),('servant_lodge',8,10,2)]
  for j,(fun,w,d,floors) in enumerate(specs):
   candidates=[]
   for lx in (-22,-16,16,22,0):
    for lz in (-24,-16,-8,0,8,16,24):
     pos=transform([lx,lz],c,yaw);fp=box(pos,w,d,yaw)
     if not domain.contains(fp) or road_domain.hits(fp) or building_domain.hits(fp) or waterblock.hits(fp) or spine.hits(fp):continue
     candidates.append((abs(lx)+(abs(lz+15) if j==0 else abs(lz)),pos))
   if not candidates:p['unresolved'].append({'id':estate['id']+':'+fun,'reason':'No bounded source mass fit in corrected estate while preserving service spine.'});continue
   _,pos=min(candidates,key=lambda x:x[0]);bld=mass(estate['id']+':'+fun,'D_NOBLE','noble_'+fun,pos,w,d,floors,yaw,estate['id'],rid,{'pad_floor_y_m':estate['pad_floor_y_m'],'social_class':'noble_household','roof_material':'gray_slate'})
   _,_,tie,_,_=nearest(bld['entrance_xz_m'],[{'id':rid,'polyline_xz_m':estate_path}])[0];p['paths'].append({'id':bld['id']+':DOOR','owner_building_id':bld['id'],'owner_plot_id':estate['id'],'road_id':rid,'polyline_xz_m':[bld['entrance_xz_m'],tie],'width_m':1.8,'kind':'estate_door_to_service_spine','status':'candidate_clearance_review_required'})
  estate['building_ids']=[b['id'] for b in p['buildings'] if b['plot_id']==estate['id']];estate['building_coverage']=sum(area(b['footprint_xz_m']) for b in p['buildings'] if b['plot_id']==estate['id'])/estate['area_m2']
 # First landmark proxies are explicit sub-volumes. Their silhouette specialist
 # replaces these source-only boxes; no precinct is treated as one solid box.
 anchors={a['id']:a for a in RAW['anchors']};p['landmark_components']=[]
 for identity,site in [('castle','CASTLE'),('cathedral','CLERGY'),('monastery','MONASTERY'),('civic','MARKET')]:
  key='market' if identity=='civic' else identity;anchor=anchors[key]['inferred_target_world_xyz_m'];origin=anchor[:]
  if identity=='castle':origin=[anchor[0],24,anchor[2]-40]
  if identity=='civic':origin=[anchor[0]-20,4,anchor[2]-60]
  group={'id':identity,'world_anchor_xyz_m':origin,'image_anchor_world_xyz_m':anchor,'registration_anchor_id':key,'source_group_key':identity,'replaces_source_building_ids':[],'masses':[],'status':'provisional_semantic_boxes; registered_silhouette_contract_pending','open_space_policy':'Courts remain open between separate masses.'}
  specs={'castle':[('keep',[-15,20,-22],[42,40,30]),('rear_range',[20,12,-30],[40,24,16]),('west_tower',[-45,26,-30],[14,52,14]),('east_tower',[45,23,-30],[14,46,14]),('service_range',[28,8,27],[40,16,16])],
   'cathedral':[('nave',[0,15,-25],[30,30,72]),('bell_tower',[-15,42,-30],[16,84,16]),('cloister_east',[48,7,-12],[14,14,65]),('cloister_north',[28,7,-40],[55,14,12]),('cloister_south',[28,7,16],[55,14,12])],
   'monastery':[('church',[0,12,-12],[24,24,65]),('tower',[-11,29,-16],[13,58,13]),('cloister_east',[45,6,25],[12,12,65]),('cloister_north',[25,6,-5],[55,12,12]),('cloister_south',[25,6,55],[55,12,12])],
   'civic':[('town_hall',[-20,12,0],[38,24,26]),('grain_hall',[27,9,0],[24,18,24])]}[identity]
  for name,offset,size in specs:group['masses'].append({'id':name,'semantic_role':name,'position_local_xyz_m':offset,'size_xyz_m':size,'yaw_degrees':32 if identity=='cathedral' and name in ('nave','bell_tower') else 40 if identity=='monastery' and name in ('church','tower') else 0})
  p['landmark_components'].append(group)
 p['landmark_component_suppressed_building_ids']=[]
 if registered_proxies:
  p['landmark_components']=copy.deepcopy(registered_proxies['groups'])
  p['landmark_component_provenance']={'path':str(proxy_path.relative_to(HERE.parents[2])),'sha256':hashlib.sha256(proxy_path.read_bytes()).hexdigest(),'status':'semantic proxy groups only; no common geometry compiled or placed'}
 # Working port and training volumes stay distinct from ordinary housing.
 quay=next(r for r in roads if r['id']=='PORT_QUAY');port_domain=Domain([sitepolys['PORT']])
 for i,fraction in enumerate((.25,.48,.72)):
  line=quay['polyline_xz_m'];lens=[math.dist(a,b) for a,b in zip(line,line[1:])];target=sum(lens)*fraction;acc=0
  for a,b,ll in zip(line,line[1:],lens):
   if acc+ll<target:acc+=ll;continue
   t=(target-acc)/ll;q=[a[k]+t*(b[k]-a[k]) for k in (0,1)];u=[(b[k]-a[k])/ll for k in (0,1)];n=[u[1],-u[0]];yaw=math.atan2(-n[0],-n[1]);pos=[q[k]+n[k]*12 for k in (0,1)];fp=box(pos,24,14,yaw)
   if port_domain.contains(fp) and not road_domain.hits(fp) and not waterblock.hits(fp):
    bld=mass(f'B_PORT_{i}','D_PORT','port_warehouse_and_loading',pos,24,14,2,yaw,None,'PORT_QUAY',{'height_m':11,'pad_floor_y_m':2.2,'replace_by_assembly_key':'registered_port_warehouse','social_class':'porters_and_merchant_storage'})
    p['paths'].append({'id':bld['id']+':DOOR','owner_building_id':bld['id'],'road_id':'PORT_QUAY','polyline_xz_m':[bld['entrance_xz_m'],q],'width_m':3,'kind':'warehouse_loading_link'})
   break
 for i,pos in enumerate(([-385,-190],[-350,-153])):
  fp=box(pos,24,10,-.2)
  if Domain([sitepolys['TRAIN']]).contains(fp) and not road_domain.hits(fp):
   bld=mass(f'B_TRAIN_{i}','D_TRAIN','barracks_and_training_store',pos,24,10,1,-.2,None,'CASTLE_APPROACH',{'height_m':7,'pad_floor_y_m':18,'replace_by_assembly_key':'registered_training_barrack','social_class':'garrison'})
   _,rid,q,_,_=nearest(bld['entrance_xz_m'],[r for r in roads if r['id']=='CASTLE_APPROACH'])[0];p['paths'].append({'id':bld['id']+':DOOR','owner_building_id':bld['id'],'road_id':rid,'polyline_xz_m':[bld['entrance_xz_m'],q],'width_m':2.4,'kind':'training_ground_path','status':'candidate_clearance_review_required'})
 stalls={'id':'market_stalls','world_anchor_xyz_m':[0,4,0],'registration_anchor_id':'market','source_group_key':'organized_market_stalls','masses':[],'replaces_source_building_ids':[],'status':'inferred_functional_stall_clusters_for_spatial_review','open_space_policy':'Central procession and perimeter cart routes excluded.'}
 market_domain=Domain([sitepolys['MARKET']])
 for ix,x in enumerate(range(38,163,12)):
  for iz,z in enumerate(range(8,85,12)):
   fp=box([x,z],6,4,.1)
   if market_domain.contains(fp) and not road_domain.hits(fp):stalls['masses'].append({'id':f'stall_{ix}_{iz}','semantic_role':'grain_or_produce_stall','position_local_xyz_m':[x,1.4,z],'size_xyz_m':[6,2.8,4],'yaw_degrees':math.degrees(.1),'color_role':'clay_roof' if (ix+iz)%2 else 'wood_brown'})
 p['landmark_components'].append(stalls)
 # Primary geometric gate/bridge declarations; full deck clearances remain a
 # separate check after this cheap spatial draft is reviewed.
 from world_city.concept_city_v3.source.author import intersect_segments
 for r in roads:
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):
   for ei,(c,d) in enumerate(zip(boundary,boundary[1:]+boundary[:1])):
    hit=intersect_segments(a,b,c,d)
    if hit and not any(math.dist(hit[0],q['position_xz_m'])<1 for q in p['gates']):
     sine=abs((b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0]))/(math.dist(a,b)*math.dist(c,d));p['gates'].append({'id':'GATE_'+r['id']+'_'+str(ei),'role':'road_gate','road_id':r['id'],'wall_edge_index':ei,'position_xz_m':hit[0],'opening_width_m':r['width_m']/max(.1,sine)+2,'status':'source_geometric_opening_pending_gate_assembly'})
   for water in terrain.WATERS:
    for wi,(c,d) in enumerate(zip(water['polyline_xz_m'],water['polyline_xz_m'][1:])):
     hit=intersect_segments(a,b,c,d)
     if hit:
      q,t,u=hit;ll=math.dist(a,b);direction=[(b[k]-a[k])/ll for k in (0,1)];sine=abs((b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0]))/(ll*math.dist(c,d));span=(water['width_m']/2+5)/max(.1,sine)+r['width_m']/2
      p['bridges'].append({'id':f'BRIDGE_{r["id"]}_{water["id"]}_{wi}','role':'registered_channel_crossing','road_id':r['id'],'water_id':water['id'],'position_xz_m':q,'deck_polyline_xz_m':[[q[k]-direction[k]*span for k in (0,1)],[q[k]+direction[k]*span for k in (0,1)]],'width_m':r['width_m']+1,'status':'candidate_full_width_span_pending_height_clearance_validation'})
 p['bridges'].append({'id':'BRIDGE_MAIN_RIVER','road_id':'MAIN_BRIDGE','role':'main_river_bridge','deck_polyline_xz_m':next(r['polyline_xz_m'] for r in roads if r['id']=='MAIN_BRIDGE'),'width_m':8,'status':'traced_axis_with_inferred_bank_landings'})
 for bl in p['blocks']:
  bs=[b for b in p['buildings'] if b.get('plot_id') in bl['plot_ids']];bl['actual_mass_footprint_area_m2']=sum(area(b['footprint_xz_m']) for b in bs);bl['gross_building_coverage']=bl['actual_mass_footprint_area_m2']/bl['area_m2']
 p['counts']={'buildings':len(p['buildings']),'plots':len(p['plots']),'roads':len(roads),'paths':len(p['paths']),'blocks':len(p['blocks']),'districts':len(p['districts']),'noble_compounds':len(estates),'landmark_component_groups':len(p['landmark_components'])}
 p['coverage']={'wall_area_m2':area(boundary),'building_footprint_area_m2':sum(area(b['footprint_xz_m']) for b in p['buildings']),'ordinary_parcel_area_m2':sum(q['area_m2'] for q in p['plots'] if q['property_type']=='street_frontage_plot'),'noble_holding_area_m2':sum(q['area_m2'] for q in estates),'policy':'District envelopes are not resolved land-use coverage. Remaining block interiors and institutional gardens are explicit incomplete first-draft work, not silently relabelled parks.'}
 p['draft_limits']=['Cheap spatial source only; no actual assembly or traversal certification.','Some estate door links and landmark envelopes require dedicated independent clearance review.','Finite public/industrial water heads and closed culvert roles are authored hypotheses from registered_topography.','Block density and residual ownership are still under review; no zero-residual claim.']
 return p

def main():
 p=build();(HERE/'plan.json').write_text(json.dumps(p,indent=2,sort_keys=True)+'\n');print(json.dumps(p['counts'],sort_keys=True));print(json.dumps(p['coverage'],sort_keys=True))
if __name__=='__main__':main()
