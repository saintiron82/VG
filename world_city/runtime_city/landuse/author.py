#!/usr/bin/env python3
"""Editable r3 residual-land source overlay, never an implicit live-scene patch.

Uses exact convex differences of measured source constraints. Buildings are
rigid placements of already compiled common masters; no whole-house scaling.
No terrain decisions, mesh compilation, or existing source writes occur here.
"""
from __future__ import annotations
import argparse,copy,hashlib,heapq,json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as g
from world_city.runtime_city.checks import urban_void_audit as audit
from world_city.runtime_city.topography import author as terrain
HERE=Path(__file__).parent
FILES={'history':'world_city/city_history.json','brief':'world_city/data/city_brief.v2.json',
       'scene':'world_city/runtime_city/generated/r2/scene.flat_property.json',
       'fabric':'world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json',
       'void_audit':'world_city/runtime_city/evidence/urban_void_audit.json',
       'grade_author':'world_city/runtime_city/topography/author.py',
       'concept_image':'world_city/reference/revision_02/city_terrain_concept.png',
       'concept_prompt':'world_city/reference/revision_02/prompt.txt'}
PATCH_ID='LU_R3_D07_OLDTOWN_SOUTH_01'
PATH_ALLOW={'public_road_ribbons','compiled_road_surfaces','access_reservations'}
EPS=1e-7

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def area(p):return g.polygon_area(p)
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def center(p):return [sum(v[i] for v in p)/len(p) for i in (0,1)]
def box(p):return [min(v[0] for v in p),min(v[1] for v in p),max(v[0] for v in p),max(v[1] for v in p)]
def clean(p):
 out=[]
 for v in p:
  if not out or math.dist(v,out[-1])>EPS:out.append(v)
 if len(out)>1 and math.dist(out[0],out[-1])<=EPS:out.pop()
 return out if len(out)>=3 and area(out)>EPS else []
def subtract(poly,obstacles):
 pieces=[poly]
 for ob in obstacles:
  rem=[]
  for p in pieces:
   if g.positive_area_overlap(p,ob,0):rem.extend(q for x in g.convex_difference(p,ob) if (q:=clean(x)))
   else:rem.append(p)
  pieces=rem
  if not pieces:break
 return pieces

class Constraints:
 def __init__(self,records):
  self.records=records;self.index=g._SpatialIndex(32)
  for i,r in enumerate(records):self.index.add(i,r['polygon'])
 def candidates(self,poly):return [self.records[i] for i in self.index.candidates(poly)]
 def hits(self,poly,allow=()):
  return [r for r in self.candidates(poly) if r['category'] not in allow and g.positive_area_overlap(poly,r['polygon'],1e-6)]
 def segment_clear(self,a,b,width,allow=PATH_ALLOW):
  return math.dist(a,b)<1e-8 or not self.hits(g.road_ribbon(a,b,width),allow)
 def point_clear(self,p,width=2.4,allow=PATH_ALLOW):
  return not self.hits(rect(p[0]-width/2,p[1]-width/2,p[0]+width/2,p[1]+width/2),allow)

def load():
 data={k:json.loads((ROOT/v).read_text()) for k,v in FILES.items() if k not in ('grade_author','concept_image','concept_prompt')}
 records,_=audit.load_geometries(data['scene'],data['fabric'],data['brief'],ROOT)
 return data,Constraints(records)

def nearest_road(point,plan):
 nodes={n['id']:[n['position_m'][0],n['position_m'][2]] for n in plan['road_nodes']};result=[]
 for r in plan['roads']:
  if r['kind']=='wall_walk' or r.get('route_id')=='WALL_ACCESS':continue
  a,b=nodes[r['from_node']],nodes[r['to_node']];dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
  t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dz)/den)) if den else 0
  q=[a[0]+dx*t,a[1]+dz*t];result.append((math.dist(point,q),r['id'],q))
 return sorted(result)

def route_grid(start,end,context,width=2.4,step=2.,margin=25.,max_nodes=25000):
 """Bounded 4-neighbor search; every retained segment tested as exact ribbon."""
 if context.segment_clear(start,end,width):return [start,end]
 x0=min(start[0],end[0])-margin;x1=max(start[0],end[0])+margin
 z0=min(start[1],end[1])-margin;z1=max(start[1],end[1])+margin
 def loc(k):return [start[0]+k[0]*step,start[1]+k[1]*step]
 root=(0,0);todo=[(math.dist(start,end),0,root)];dist={root:0};prev={};tested={}
 while todo and len(dist)<max_nodes:
  _,cost,k=heapq.heappop(todo)
  if cost>dist[k]+1e-8:continue
  p=loc(k)
  if math.dist(p,end)<=step*2 and context.segment_clear(p,end,width):
   seq=[k]
   while seq[-1]!=root:seq.append(prev[seq[-1]])
   path=[loc(t) for t in reversed(seq)]+[end]
   out=[path[0]];i=0
   while i<len(path)-1:
    j=len(path)-1
    while j>i+1 and not context.segment_clear(path[i],path[j],width):j-=1
    out.append(path[j]);i=j
   return out
  for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
   kk=(k[0]+dx,k[1]+dz);q=loc(kk)
   if not(x0<=q[0]<=x1 and z0<=q[1]<=z1):continue
   if kk not in tested:tested[kk]=context.point_clear(q,width)
   if not tested[kk] or not context.segment_clear(p,q,width):continue
   nc=cost+step
   if nc<dist.get(kk,1e99):dist[kk]=nc;prev[kk]=k;heapq.heappush(todo,(nc+math.dist(q,end),nc,kk))
 return None

def path_record(identity,polyline,width,field,role,road_id=None):
 profiles=[field.profile(a,b) for a,b in zip(polyline,polyline[1:]) if math.dist(a,b)>EPS]
 return {'id':identity,'role':role,'width_m':width,'polyline_xz_m':polyline,
 'ribbon_polygons_xz_m':[g.road_ribbon(a,b,width) for a,b in zip(polyline,polyline[1:]) if math.dist(a,b)>EPS],
 'connected_public_road_id':road_id,'exact_candidate_H_profiles':profiles,
 'max_candidate_grade':max((p['max_grade'] for p in profiles),default=0),
 'surface_status':'finite_common_surface_spec_pending_coordinated_compile','minimum_clear_height_m':2.4}

def infer_use(p,plan,field):
 x,z=p;wall=plan['wall_outline_xz_m'];wall_dist=min(g.point_segment_distance(p,a,b) for a,b in zip(wall,wall[1:]+wall[:1]))
 bs=[]
 for b in plan['building_plans']:
  if b['district_id'] not in ('D09','S01'):bs.append((math.dist(p,center(b['footprint_xz_m'])),b))
 near=sorted(bs,key=lambda q:q[0])[:12];district=Counter(b['district_id'] for _,b in near).most_common(1)[0][0]
 features={f['id']:f for f in plan['site_features']};cat=features['F_CATHEDRAL_CLOSE']['footprint_xz_m']
 catdistance=min(g.point_segment_distance(p,a,b) for a,b in zip(cat,cat[1:]+cat[:1]))
 if z<-370:district='D08';role='productive_orchard_and_crop_holding';era='river_trade'
 elif wall_dist<24:district='D09';role='wall_patrol_repair_and_training_strip';era='river_trade'
 elif district=='D02' and catdistance<55:role='cathedral_service_garden_and_cemetery_extension';era='religious_precinct'
 elif district=='D02':role='clerical_lodging_service_backland';era='religious_precinct'
 elif district=='D01':role='castle_service_terrace_and_repair_yard';era='crossing_fort'
 elif district=='D04':role='merchant_warehouse_loading_and_service_court';era='river_trade'
 elif district=='D05':role='quay_storage_cart_turning_and_timber_yard';era='river_trade'
 elif district=='D06':role='craft_workcourt_and_worker_infill';era='river_trade'
 elif district=='D10':role='charitable_kitchen_garden_and_service_court';era='religious_precinct'
 elif district=='D08':role='productive_garden_and_orchard_holding';era='outer_infill'
 elif district=='D03':role='market_inn_and_shop_service_backland';era='chartered_market'
 else:district='D07';role='dense_rear_housing_and_shared_workcourt';era='chartered_market'
 return district,role,era,[b['id'] for _,b in near[:3]]

def exact_partition(data,context):
 """All source residual area, including small boundary fragments, assigned once."""
 plan=data['brief'];wall=plan['wall_outline_xz_m'];field=terrain.field_from_brief(plan);bb=box(wall)
 patches={};slivers=0
 for ix in range(math.floor(bb[0]/32),math.ceil(bb[2]/32)):
  for iz in range(math.floor(bb[1]/32),math.ceil(bb[3]/32)):
   tile=g.convex_intersection(rect(ix*32,iz*32,(ix+1)*32,(iz+1)*32),wall)
   if not clean(tile):continue
   pieces=subtract(tile,[r['polygon'] for r in context.candidates(tile)])
   for poly in pieces:
    c=center(poly);d,role,era,near=infer_use(c,plan,field)
    # Stable district-scale 96 m holding IDs, not anonymous grass scatter.
    identity=f'LU_R3_{d}_{math.floor(c[0]/96):+03d}_{math.floor(c[1]/96):+03d}'
    if identity not in patches:patches[identity]={'id':identity,'district_id':d,'role':role,'era_id':era,
      'polygons_xz_m':[],'source_neighbor_building_ids':set(),'source_gap_origin':'exact_difference_of_all_source_assignments',
      'implementation_status':'editable_functional_allocation_not_constructed','grade_design_status':'24m_14m_explicit_prompt_target; intermediate_terraces_require_new_field',
      'observed_vs_inferred':{'observed_in_concept':'layered built blocks, small greens, productive plots and service yards; no giant bare voids','inferred_from_source':'exact polygon boundaries, district attribution, function mix and dimensions are source-constrained authoring; not pixel measurements'}}
    rec=patches[identity];rec['polygons_xz_m'].append(poly);rec['source_neighbor_building_ids'].update(near)
 for r in patches.values():
  r['area_m2']=sum(area(p) for p in r['polygons_xz_m']);r['source_neighbor_building_ids']=sorted(r['source_neighbor_building_ids'])
  r['surface_spec']={'material':'earth' if 'work' in r['role'] or 'service' in r['role'] else 'grass','facets':'exact_grade_field_H','thickness_m':.4,
    'compiler':'world_city.runtime_city.topography.author.make_surface_master','max_walk_tile_span_m':8.,
    'compile_scope':'only selected paths/courts; broad fields stay coarse terrain','polygon_ownership':'these finite polygons only; no bbox fill'}
  r['functional_program']=program_for(r['role'])
 return sorted(patches.values(),key=lambda p:p['id'])

def program_for(role):
 if 'dense_rear' in role:return ['short_connected_alleys','two_or_three_storey_housing','shared_washing_and_repair_court','small_neighborhood_garden_only_at_named_node']
 if 'merchant' in role:return ['warehouse_cart_apron','stable_and_fuel_service_strip','enclosed_merchant_garden','street_link_required']
 if 'craft' in role:return ['workshop_yard','worker_house_infill','fire_separation','service_alley']
 if 'cathedral' in role:return ['bounded_burial_rows_adjacent_to_existing_close','herb_garden','processional_and_service_access']
 if 'castle' in role:return ['terraced_service_court','retaining_edge','steps_plus_continuous_ramp_route','repair_stock']
 if 'wall' in role:return ['continuous_patrol_access','repair_material_stacks','archery_training_ground','no_wall_obstruction']
 if 'garden' in role or 'orchard' in role:return ['cultivated_strips','orchard_rows','field_edge_path','limited_garden_store']
 if 'quay' in role:return ['cart_turning','loading_court','timber_and_grain_store','bank_level_review']
 return ['service_court','connected_pedestrian_access','bounded_utility_or_garden_zone']

def make_infill(data,context):
 plan,scene=data['brief'],data['scene'];field=terrain.field_from_brief(plan)
 templates={b['id']:b for b in scene['instances']}
 # Coherent two east-west back lanes plus north-south service link.
 spines=[('NORTH',[[-390,124],[-278,124]],2.4),('SOUTH',[[-348,166],[-266,166]],2.4),('CROSS',[[-333,124],[-333,166]],2.4)]
 paths=[]
 for name,points,width in spines:
  assert context.segment_clear(*points,width),('blocked_author_spine',name,context.hits(g.road_ribbon(*points,width)))
  paths.append(path_record(PATCH_ID+':ALLEY:'+name,points,width,field,'internal_shared_alley'))
 # The west gateway is a genuine road gap, not a route through a private plot.
 gateway_seeds=[([-390,124],[-423,140]),([-270,166],[-232,181])]
 gateway_attempts=[]
 for i,(start,guide) in enumerate(gateway_seeds):
  found=None
  for _,rid,end in nearest_road(guide,plan)[:20]:
   path=route_grid(start,end,context,2.4,margin=25.)
   if path:
    found=path_record(PATCH_ID+f':GATEWAY:{i+1:02d}',path,2.4,field,'public_road_connection',rid);break
  if not found:raise ValueError(('no_safe_public_gateway',i))
  paths.append(found)
 # 32 bounded houses chosen for actual unchanged dimensions, 1-3 floors.
 template_ids=['D07-B007','D07-B035','D07-B091','D07-B010','D07-B006','D07-B015','D07-B094','D07-B009']
 stations=[-384,-371,-358,-345,-320,-307,-294,-281]
 buildings=[];rejected=[];footprints=[]
 for row,(line_z,side) in enumerate([(124,-1),(124,1),(166,-1),(166,1)]):
  for col,x in enumerate(stations if row<2 else [-344,-320,-307,-294,-281]):
   template=templates[template_ids[(col+row*3)%len(template_ids)]];spec=scene['asset_specs'][template['asset_key']]
   bounds=template['local_bounds'];halfdepth=max(abs(bounds['min'][2]),abs(bounds['max'][2]));yaw=0. if side<0 else math.pi
   z=line_z+side*(halfdepth+3.);pos=[x,0.,z];poly=g.transformed_aabb_xz_m(bounds,pos,yaw)
   identity=PATCH_ID+f':HOUSE:{row+1:02d}:{col+1:02d}'
   hits=context.hits(poly)
   if hits or any(g.positive_area_overlap(poly,q) for q in footprints):rejected.append({'id':identity,'reason':'source_or_infill_envelope_overlap','blocker_ids':[r['id'] for r in hits]});continue
   if any(g.positive_area_overlap(poly,q) for p in paths for q in p['ribbon_polygons_xz_m']):rejected.append({'id':identity,'reason':'reserved_route_overlap'});continue
   all_local=template['all_entrances_local_m'];c,s=math.cos(yaw),math.sin(yaw)
   all_world=[[x+c*a+s*b,y,z-s*a+c*b] for a,y,b in all_local]
   Hvals=[terrain._eval(f['plane'],*v) for f in field.facets(poly) for v in f['polygon_xz_m']]
   # Flat-only first block: any changed grade requires a coordinated foundation.
   hmin,hmax=min(Hvals),max(Hvals);anchor=field.height(all_world[0][0],all_world[0][2]);base=anchor-all_local[0][1]
   foundation={'height_field':'topography.author.field_from_brief','terrain_min_y_m':hmin,'terrain_max_y_m':hmax,'base_y_m':base,
    'cut_top_y_m':base-2.,'bottom_y_m':min(hmin,base)-2.5,'top_y_m':base,'required_cut_fill':True,
    'status':'exact_H_support_spec_requires_atomic_terrain_integration','body_footprint_xz_m':poly}
   if hmax-hmin>.1:rejected.append({'id':identity,'reason':'candidate_terrain_not_flat_first_infill','foundation_requirement':foundation});continue
   pos[1]=base
   all_world=[[p[0],p[1]+base,p[2]] for p in all_world]
   links=[]
   for j,p in enumerate(all_world):
    end=[p[0],line_z];start=[p[0],p[2]];outside=[p[0],z-side*(halfdepth+.05)]
    # Own recessed facade is the sole exception; exterior part is fully checked.
    assert context.segment_clear(outside,end,1.8),('door_source_collision',identity,j)
    links.append(path_record(identity+f':DOOR:{j:02d}',[start,outside,end],1.8,field,'individual_actual_door_link'))
    links[-1]['owner_building_id']=identity;links[-1]['door_local_m']=all_local[j];links[-1]['own_facade_inset_exception_only']=True
   b=copy.deepcopy(template);b.update({'id':identity,'source_footprint_id':identity,'source_footprint_xz_m':poly,'position_m':pos,'yaw_rad':yaw,
     'all_entrances_world_m':all_world,'functional_role':['weaver_house_and_workroom','day_laborer_row_lodging','shoemaker_house','parish_service_lodging'][row],
     'source_building_template_id':template['id'],'source_footprint_provenance':'new_r3_infill_not_one_of_original_1308','patch_id':PATCH_ID,
     'geometry_policy':'reuse_existing_compiled_common_master_at_unit_scale','transform_scale':[1,1,1],
     'era_id':'outer_infill' if row==3 else 'chartered_market','foundation_requirement':foundation,'implementation_status':'candidate_placed_existing_geometry_not_live_integrated'})
   b['entrance']=copy.deepcopy(template['entrance']);b['entrance'].update({'position_m':all_world[0],'road_connection_m':[all_world[0][0],field.height(all_world[0][0],line_z),line_z],
    'road_id':PATCH_ID+':ALLEY:'+('NORTH' if row<2 else 'SOUTH'),'status':'actual_exterior_threshold_linked_to_public_gateway'})
   b['chunk_id']=f'{math.floor(x/64)}_{math.floor(z/64)}';b.pop('height_delta_m',None)
   buildings.append(b);footprints.append(poly);paths.extend(links)
 # Park is deliberately small relative to the housing backland. Flat first block
 # gets a shared court; steps remain a candidate on a genuinely sloped later site.
 zones=[{'id':PATCH_ID+':COURT:WASH','role':'shared_washing_repair_court','polygon_xz_m':rect(-326,143,-307,148),'material':'earth'},
        {'id':PATCH_ID+':GARDEN','role':'small_neighborhood_garden','polygon_xz_m':rect(-300,143,-281,148),'material':'grass'}]
 for zone in zones:
  assert not context.hits(zone['polygon_xz_m'])
  assert not any(g.positive_area_overlap(zone['polygon_xz_m'],q) for q in footprints)
  zone['area_m2']=area(zone['polygon_xz_m']);zone['grade_status']='candidate_exact_H_flat';zone['surface_status']='finite_common_surface_spec_not_compiled'
 # Reused measured common modules give the small zones actual parts, not labels.
 facilities=[]
 facility_rows=[('WORKBENCH_1','uf_workbench_4d91d514c111fd',[-321,144]),
                ('WORKBENCH_2','uf_workbench_4d91d514c111fd',[-312,147]),
                ('FUEL_STOCK','uf_timber_stack_856e7ef8c40c5c',[-323,147]),
                ('BED_1','uf_garden_bed_5bb2a5f66dd50b',[-296,145.5]),
                ('BED_2','uf_garden_bed_5bb2a5f66dd50b',[-291,145.5]),
                ('BED_3','uf_garden_bed_5bb2a5f66dd50b',[-286,145.5])]
 for suffix,key,p in facility_rows:
  resource=data['fabric']['assets'][key];bounds=resource['bounds'];poly=g.transformed_aabb_xz_m(bounds,[p[0],0,p[1]],0)
  assert not context.hits(poly)
  assert not any(g.positive_area_overlap(poly,q) for q in footprints)
  assert not any(g.positive_area_overlap(poly,q) for path in paths for q in path['ribbon_polygons_xz_m'])
  facilities.append({'id':PATCH_ID+':FACILITY:'+suffix,'asset_key':key,'category':data['fabric']['master_specs'][key]['kind'],
   'position_m':[p[0],field.height(*p),p[1]],'yaw_rad':0.,'transform_scale':[1,1,1],'local_bounds':bounds,
   'footprint_xz_m':poly,'source_asset_catalog':FILES['fabric'],'patch_id':PATCH_ID,
   'support_status':'exact_H_flat_reuse_existing_embed','implementation_status':'candidate_existing_compiled_common_geometry'})
 for suffix,points in [('WORKCOURT',[[-333,145.5],[-304,145.5]]),('GARDEN',[[-304,145.5],[-304,142],[-281,142]])]:
  assert all(context.segment_clear(a,b,1.8) for a,b in zip(points,points[1:]))
  rec=path_record(PATCH_ID+':PATH:'+suffix,points,1.8,field,'shared_court_or_garden_access')
  assert not any(g.positive_area_overlap(poly,q) for poly in rec['ribbon_polygons_xz_m'] for q in footprints)
  assert not any(g.positive_area_overlap(poly,f['footprint_xz_m']) for poly in rec['ribbon_polygons_xz_m'] for f in facilities)
  paths.append(rec)
 return {'id':PATCH_ID,'source_void_id':'VOID_06','district_id':'D07','status':'bounded_candidate_matches_concept_pending_integration',
   'paths':paths,'building_instances':buildings,'facility_placements':facilities,'zones':zones,'rejected_candidates':rejected,
   'source_assets_reused':sorted({b['asset_key'] for b in buildings}),
   'new_unique_building_master_count':0,'original_scene_count':len(scene['instances']),
   'resulting_building_count_if_integrated':len(scene['instances'])+len(buildings),
   'terrain_height_policy':'unit scale upright; exact H support required; no blind height flattening'}

def market_zones(data,context):
 plan=data['brief'];field=terrain.field_from_brief(plan);market=next(f for f in plan['site_features'] if f['id']=='F_MARKET_OPEN')['footprint_xz_m']
 # Disjoint bands allocate the entire 11700 m2 reservation. Existing pavilion,
 # fountain, public roads and repaired access remain geometrically protected.
 regions=[('NORTH_GRAIN','grain_stalls_and_sack_weighing',rect(-60,-50,70,-22)),
          ('SOUTH_PRODUCE','produce_stalls_and_handcart_holding',rect(-60,18,70,40)),
          ('WEST_CART','cart_unloading_and_turning',rect(-60,-22,-36,18)),
          ('EAST_CART','merchant_cart_service',rect(42,-22,70,18)),
          ('CIVIC_CORE','civic_procession_and_fountain_gathering',rect(-36,-22,42,18))]
 blockers=[r['polygon'] for r in context.candidates(market) if r['category'] in ('building_envelopes','public_road_ribbons','compiled_road_surfaces','fabric_envelopes','access_reservations')]
 blockers.append(rect(-27,-7,-13,7))
 zones=[]
 for key,role,p in regions:
  polys=subtract(p,blockers);zones.append({'id':'LU_R3_MARKET_'+key,'role':role,'source_feature_id':'F_MARKET_OPEN',
    'base_allocation_polygon_xz_m':p,'polygons_xz_m':polys,'net_functional_area_m2':sum(area(q) for q in polys),
    'public_route_and_fountain_priority':True,'protected_core_policy':'source 6996m2 core deliberately reprogrammed by explicit overlay; central procession preserved',
    'status':'editable_market_program_pending_concept','surface_spec':{'material':'stone','exact_H':True,'max_span_m':8.}})
 placements=[]
 for prefix,role,rows,key,zone_id in [
   ('GRAIN','grain_trader_stall',[-42,-32],'uf_market_stall_b7bbb02d2f9be2','LU_R3_MARKET_NORTH_GRAIN'),
   ('PRODUCE','produce_trader_stall',[25,34],'uf_market_stall_c33d20b8743e94','LU_R3_MARKET_SOUTH_PRODUCE')]:
  zone=next(z for z in zones if z['id']==zone_id)
  for row,z in enumerate(rows):
   for col,x in enumerate([-47,-37,-27,-17,-7,3,13,23,33,43,53]):
    resource=data['fabric']['assets'][key];poly=g.transformed_aabb_xz_m(resource['bounds'],[x,0,z],0)
    if context.hits(poly,('market_square',)):continue
    if not g.convex_polygon_contains(zone['base_allocation_polygon_xz_m'],poly,0):continue
    if any(g.positive_area_overlap(poly,p['footprint_xz_m']) for p in placements):continue
    placements.append({'id':f'LU_R3_MARKET_{prefix}_STALL_{row:02d}_{col:02d}',
     'asset_key':key,'category':'market_stall','functional_role':role,'zone_id':zone_id,
     'position_m':[x,field.height(x,z),z],'yaw_rad':0.,'transform_scale':[1,1,1],
     'local_bounds':resource['bounds'],'footprint_xz_m':poly,'source_asset_catalog':FILES['fabric'],
     'source_master_reused':True,'support_status':'existing_rooted_posts_on_exact_flat_H','implementation_status':'candidate_cached_geometry'} )
 # Four-metre trading aisles join the existing public edge roads through the
 # same unobstructed square; civic core and fountain remain free of new stalls.
 aisle_specs=[{'id':'LU_R3_MARKET_GRAIN_AISLE','polyline_xz_m':[[-52,-37],[58,-37]],'width_m':4.,'role':'grain_buyer_and_handcart_aisle'},
              {'id':'LU_R3_MARKET_PRODUCE_AISLE','polyline_xz_m':[[-52,29.5],[58,29.5]],'width_m':4.,'role':'produce_buyer_and_handcart_aisle'}]
 for aisle in aisle_specs:
  for a,b in zip(aisle['polyline_xz_m'],aisle['polyline_xz_m'][1:]):
   assert not any(g.positive_area_overlap(g.road_ribbon(a,b,aisle['width_m']),p['footprint_xz_m']) for p in placements)
 return {'source_area_m2':area(market),'zones':zones,'new_buildings':0,'facility_placements':placements,'trade_aisles':aisle_specs,
   'square_boundary_unchanged':True,'protected_entries':'all measured public road ribbons and repaired reservations subtracted before facility placement',
   'reserved_existing_envelope_and_access_area_m2':area(market)-sum(z['net_functional_area_m2'] for z in zones)}

def residual_region_access(data,context,infill):
 """Reserve finite service paths for every >=500m² conservative residual region.

 Direct exact-width links are preferred; bounded search follows when frontages
 intervene. A failure remains an explicit blocker, never a fictional connection.
 """
 plan=data['brief'];field=terrain.field_from_brief(plan)
 new=[{'category':'building_envelopes','id':b['id'],'polygon':b['source_footprint_xz_m']} for b in infill['building_instances']]
 new += [{'category':'fabric_envelopes','id':f['id'],'polygon':f['footprint_xz_m']} for f in infill['facility_placements']]
 route_context=Constraints(context.records+new)
 easement_context=Constraints([r for r in context.records+new if r['category'] not in ('original_plot_grounds','remaining_reserved_courtyards')])
 grid=audit.raster_inventory(context.records,plan['wall_outline_xz_m'],2.)
 regions=[]
 for rank,cells in enumerate(audit.components(grid)):
  if len(cells)*4<500:continue
  nx=grid['nx'];origin=grid['origin'];res=2.
  points=[[origin[0]+(n%nx+.5)*res,origin[1]+(n//nx+.5)*res] for n in cells]
  c=center(points);start=min(points,key=lambda q:math.dist(c,q));identity=f'LU_R3_RESIDUAL_{rank+1:03d}'
  targets=[(d,rid,p) for d,rid,p in nearest_road(start,plan)[:45] if route_context.point_clear(p,2.)]
  found=None
  for distance,rid,end in targets:
   if route_context.segment_clear(start,end,2.):found=(rid,[start,end]);break
  if not found:
   for distance,rid,end in targets[:5]:
    if distance>200:continue
    path=route_grid(start,end,route_context,2.,step=2.,margin=20.,max_nodes=6500)
    if path:found=(rid,path);break
  easements=[]
  if not found:
   # Authorized redesign may revise a narrow strip of a source plot. This is
   # explicit geometry/provenance, never a silent permission to fill a court.
   targets=[(d,rid,p) for d,rid,p in nearest_road(start,plan)[:30] if easement_context.point_clear(p,2.)]
   for distance,rid,end in targets[:12]:
    path=route_grid(start,end,easement_context,2.,step=2.,margin=30.,max_nodes=10000)
    if path:
     found=(rid,path)
     for a,b in zip(path,path[1:]):
      ribbon=g.road_ribbon(a,b,2.)
      for ob in context.hits(ribbon,PATH_ALLOW):
       if ob['category'] in ('original_plot_grounds','remaining_reserved_courtyards'):
        intersection=clean(g.convex_intersection(ribbon,ob['polygon']))
        if intersection:easements.append({'source_id':ob['id'],'source_category':ob['category'],
          'replacement_use':'shared_pedestrian_service_easement','polygon_xz_m':intersection,
          'area_m2':area(intersection),'original_source_geometry_retained':True})
     break
  record={'id':identity,'strict_residual_area_m2':len(cells)*4.,'representative_xz_m':start,
   'district_id':infer_use(start,plan,field)[0],
   'access_status':('explicit_source_plot_strip_reassignment' if easements else 'exact_width_path_reserved') if found else 'requires_explicit_frontage_passage_design',
   'source_plot_strip_reassignments':easements,
   'path':path_record(identity+':PATH',found[1],2.,field,'district_backland_service_access',found[0]) if found else None,
   'unresolved_action':None if found else 'No source-safe two-metre path found within bounded search; do not place infill until a documented frontage/plot revision opens access.'}
  regions.append(record)
 return {'threshold_m2':500.,'substantial_region_count':len(regions),'regions':regions,
   'reserved_connection_count':sum(r['path'] is not None for r in regions),
   'blocked_connection_count':sum(r['path'] is None for r in regions)}

def build(data,context):
 patches=exact_partition(data,context);infill=make_infill(data,context);market=market_zones(data,context);access=residual_region_access(data,context,infill)
 residual=sum(p['area_m2'] for p in patches)
 return {'schema':'riverstone.city.landuse.overlay.v1','revision':'r3_editable_candidate','status':'concept_aligned_source_overlay_not_live_city',
 'sources':{k:{'path':v,'sha256':digest(ROOT/v)} for k,v in FILES.items()},
 'history_provenance':'canonical 1435 fictional chronology; assignment is authored worldbuilding, not historical survey',
 'source_preservation':{'original_1308_ids_retained':True,'original_source_files_modified':False,'fixed_count_target':False,'fixed_area_target':False},
 'coordinate_system':data['scene']['coordinate_system'],'patches':patches,'first_infill_block':infill,'market_program':market,'residual_region_access':access,
 'coverage':{'wall_envelope_exact_m2':area(data['brief']['wall_outline_xz_m']),'exact_source_residual_assigned_m2':residual,
  'source_assigned_union_exact_m2':area(data['brief']['wall_outline_xz_m'])-residual,
  'source_raster_unassigned_2m_m2':data['void_audit']['areas_m2']['unassigned_cell_centres'],
  'exact_minus_2m_raster_m2':residual-data['void_audit']['areas_m2']['unassigned_cell_centres'],
  'unassigned_exact_residual_after_functional_allocation_m2':0.,'allocation_is_not_implementation':True,
  'new_building_envelope_area_m2':sum(area(b['source_footprint_xz_m']) for b in infill['building_instances'])},
 'candidate_parts_inventory':[{'kind':'shared_washing_trough','count':1,'status':'spec_required'},
   {'kind':'workbench','count':4,'common_module':'urban_fabric.author.make_master'},
   {'kind':'garden_bed','count':4,'common_module':'urban_fabric.author.make_master'},
   {'kind':'neighborhood_park_bench','count':2,'common_module':'urban_fabric.author.make_master(workbench)'},
   {'kind':'terraced_court_retaining_edge_and_steps','count':0,'status':'await_whole_city_concept_and_actual_sloped_site; never invent steps on flat oldtown ground'}],
 'integration_contract':{'parent_must_merge_explicitly':True,'new_buildings_reuse_existing_assets':True,
   'append_building_instances_from':'first_infill_block.building_instances','append_facility_placements_from':['first_infill_block.facility_placements','market_program.facility_placements'],'protect_all_paths':True,
   'foundation_requirement_must_be_consumed_before_promotion':True,'no_heavy_compile_started':True},
 'limitations':['Whole-city functional allocation is source data; it is not rendered land-use completion.',
   'Only the bounded old-town block has explicit new building placements. Other dense-infill patches require parcel-level building design.',
   '24m/14m heights follow explicit concept prompt. Intermediate 2–6m neighborhood terraces need separate exact-H authoring.',
   'Existing r3 manor/forest revision is owned elsewhere and must be reconciled before final integration.']}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(HERE/'candidate_overlay.json'));p.add_argument('--infill-only',action='store_true');args=p.parse_args()
 data,context=load();out=make_infill(data,context) if args.infill_only else build(data,context)
 Path(args.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'out':args.out,'buildings':len(out.get('building_instances',out.get('first_infill_block',{}).get('building_instances',[]))), 'coverage':out.get('coverage')},ensure_ascii=False))
if __name__=='__main__':main()
