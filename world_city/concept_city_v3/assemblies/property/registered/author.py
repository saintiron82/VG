"""Finite image-registered estate recipes. Source/proxy output only, no compiler.

Buildings are native-size common modules. The irregular ownership floor and all
owned boundary spans form one common solid. Shared retaining edges have one owner.
"""
from __future__ import annotations
import copy, hashlib, json, math, heapq
from functools import lru_cache
from pathlib import Path
from world_city.concept_city_v3.assemblies.property import recipes as frozen
from world_city.runtime_city.checks import placement as geom
from world_city.runtime_city.urban_fabric.author import rect, yaw_basis
from world_city.runtime_city.urban_fabric.revisions.r3.author_overlay import route_inside, offset, polygon_covered_by_union
from world_city.concept_city_v3.registered_source.geometry import triangulate, inside
from world_city.runtime_city.infrastructure.author import PALETTE
HERE=Path(__file__).resolve().parent; CITY=HERE.parents[2]; ROOT=CITY.parents[1]
IDS=tuple('E'+str(i) for i in range(1,8)); PITCH=.5

def sha(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def file_sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(p): return [[round(v,6) for v in q] for q in p]
def centre(p): return [sum(q[i] for q in p)/len(p) for i in (0,1)]
def unit(a,b):
 d=math.dist(a,b);return [(b[i]-a[i])/d for i in (0,1)]
def add(a,b,s=1):return [a[i]+b[i]*s for i in (0,1)]
def xform(p,pos,yaw):return frozen.world_point(p,pos,yaw)
def overlap(p,q):return any(geom.intersection_area(a,b)>1e-7 for a in triangulate(p) for b in triangulate(q))
def contained(p,outer):return polygon_covered_by_union(p,triangulate(outer),1e-6)
def near(a,b,p):
 u=[b[i]-a[i] for i in (0,1)];l2=sum(v*v for v in u);t=max(0,min(1,sum((p[i]-a[i])*u[i] for i in (0,1))/l2));return add(a,u,t),t

# Intentional small finite compositions. Coordinates are authored hypotheses in
# the registered world frame, never a fitted scale of the old whole estate.
LAYOUTS={
 'E1':dict(form='older_stone_manor',name='narrow stone hall with rear kitchen garden',houses=[('main','stone',[-191,-284],0),('stable','stable',[-203,-319],math.pi/2),('servants','lodge',[-174,-315],-math.pi/2)],garden=([-189,-316],18,18),court=([-191,-264],28,14),trees=[[-204,-300],[-174,-297]]),
 'E2':dict(form='merchant_palazzo',name='palace with paired inward court wings',houses=[('main','palace',[-131,-281],-.10),('west_court_wing','palace_wing',[-151,-260],math.pi/2),('east_court_wing','palace_wing',[-109,-258],-math.pi/2),('stable','stable',[-149,-310],math.pi/2),('servants','lodge',[-110,-306],-math.pi/2)],garden=([-131,-309],24,18),court=([-131,-257],28,20),trees=[[-152,-288],[-109,-288]]),
 'E3':dict(form='timber_courtyard_house',name='timber hall and rear service wings around kitchen garden',houses=[('main','timber',[-65,-270],0),('stable','stable',[-45,-296],-math.pi/2),('servants','lodge',[-85,-298],math.pi/2)],garden=([-65,-299],24,18),court=([-65,-250],28,12),trees=[[-85,-278],[-43,-274]]),
 'E4':dict(form='older_stone_manor',name='broad stone hall ensemble and lower side wing',houses=[('main','stone',[-213,-189],-.10),('stone_side_wing','stone_wing',[-187,-188],0),('stable','stable',[-226,-216],math.pi/2),('servants','lodge',[-186,-211],-math.pi/2)],garden=([-207,-216],24,18),court=([-207,-167],38,18),trees=[[-227,-178],[-184,-164]]),
 'E5':dict(form='merchant_palazzo',name='side palace and long private garden with separate service court',houses=[('main','palace',[-108,-200],0),('rear_wing','palace_wing',[-128,-220],0),('stable','stable',[-147,-218],0),('servants','lodge',[-147,-174],0)],garden=([-142,-194],20,24),court=([-115,-176],28,18),trees=[[-128,-172],[-101,-220]]),
 'E6':dict(form='older_stone_manor',name='east-facing stone hall above a garden terrace',houses=[('main','stone',[-35,-224],math.pi/2),('stable','stable',[-75,-227],math.pi/2),('servants','lodge',[-54,-181],0)],garden=([-54,-203],22,20),court=([-19,-207],16,14),trees=[[-72,-202],[-34,-194]]),
 'E7':dict(form='timber_courtyard_house',name='wedge-shaped timber court with small south garden',houses=[('main','timber',[-124,-144],0),('stable','stable',[-143,-116],math.pi/2),('servants','lodge',[-109,-120],-math.pi/2)],garden=([-131,-97],14,12),court=([-124,-117],18,18),trees=[[-148,-145],[-101,-146]])}

@lru_cache(None)
def catalog():
 a=json.loads((HERE.parent/'generated/cache_catalog.json').read_text())['assets']; roles={}
 for k,v in a.items():
  s=v['cache_spec'];p=s['params']
  if s['provider']=='ordinary_r2':
   role={'older_stone_manor':'stone','merchant_palazzo':'palace','timber_courtyard_house':'timber'}.get(p['assembly_class']) if p['width_m']==26 else ('stable' if p['assembly_class']=='stable' else 'lodge' if p['assembly_class']=='servant_lodge' else 'palace_wing' if p['assembly_class']=='merchant_palazzo' and p['width_m']==12 else None)
  else:role='bed' if p['kind']=='garden_bed' else 'tree' if p['kind']=='forest_tree' else None
  if role:roles[role]=dict(asset_key=k,spec=s)
 s={'provider':'ordinary_r2','params':dict(assembly_class='older_stone_manor',width_m=12,depth_m=8,floors=2,floor_height_m=3.4,style='institutional',roof_form='hip',roof_pitch_degrees=40,construction_era='early')}
 roles['stone_wing']=dict(asset_key=frozen.key_for(s),spec=s)
 for v in roles.values():
  bounds,meta=frozen.describe_asset(v['spec']);v.update(bounds=bounds,metadata=meta)
 return roles

def fit_rect(desired,w,d,yaw,parcel,obstacles,search=5,margin=1.25):
 # Search makes a bounded deterministic placement correction, not density fill.
 ds=sorted(((dx*dx+dz*dz,dx,dz) for dx in range(-search*2,search*2+1) for dz in range(-search*2,search*2+1)))
 for _,ix,iz in ds:
  pos=add(desired,[ix*.5,iz*.5]);p=rect(pos,w,d,yaw)
  if contained(rect(pos,w+2*margin,d+2*margin,yaw),parcel) and not any(overlap(rect(pos,w+2*margin,d+2*margin,yaw),q) for q in obstacles):return pos,p
 raise ValueError('No bounded native-size placement at '+str(desired))

def shared_edges(plot,all_plots):
 out={};poly=plot['polygon_xz_m']
 for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  for q in all_plots:
   if q['id']==plot['id']:continue
   for j,(c,d) in enumerate(zip(q['polygon_xz_m'],q['polygon_xz_m'][1:]+q['polygon_xz_m'][:1])):
    if math.dist(a,d)<1e-4 and math.dist(b,c)<1e-4:
     owner=max((plot,q),key=lambda r:(r['pad_floor_y_m'],r['id']))['id'];out[i]=dict(other_plot_id=q['id'],other_edge_index=j,owner_plot_id=owner)
 return out

def propose_gate(plot,poly,shared,obstacles=()):
 target=plot.get('gate_position_xz_m');target=target or [centre(poly)[0],max(p[1] for p in poly)+5]
 candidates=[]
 for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  if i in shared:continue
  length=math.dist(a,b);u=unit(a,b);n=[-u[1],u[0]]
  for j in range(math.ceil(length*2)):
   distance=j*.5
   if distance<5 or distance>length-5:continue
   t=distance/length;p=add(a,u,distance)
   # Check the full cart corridor inside the wall before selecting a gate.
   inner=geom.road_ribbon(add(p,n,.1),add(p,n,7),5)
   if not contained(inner,poly) or any(overlap(inner,q) for q in obstacles):continue
   candidates.append((math.dist(p,target),i,p,t))
 if not candidates:raise ValueError('No unobstructed full-width gate in '+plot['id'])
 _,i,p,t=min(candidates);a,b=poly[i],poly[(i+1)%len(poly)];u=unit(a,b);n=[-u[1],u[0]]
 return dict(id=plot['id']+':registered_main_gate',role='main_and_service',edge_index=i,edge_t=t,width_m=5,center_xz_m=p,inside_point_xz_m=add(p,n,6),outside_point_xz_m=add(p,n,-3),external_source_link_xz_m=target,external_road_id=plot.get('road_id'),finished_threshold_y_m=plot['pad_floor_y_m'],external_grade_status='pending_registered_topography_access_audit',purpose='shared pedestrian and cart gate; separate internal service branch')

def route_in_parcel(start,end,parcel,obstacles,width=1.8):
 """Visibility route using triangulated union coverage for concave parcels."""
 nodes=[start,end]
 for p in obstacles:nodes.extend(offset(p,-(width/2+.3)))
 for v in parcel:
  for radius in (1.5,3):
   for j in range(8):
    q=add(v,[math.cos(j*math.pi/4),math.sin(j*math.pi/4)],radius)
    if contained(rect(q,width,width),parcel):nodes.append(q)
 def clear(a,b):
  if math.dist(a,b)<1e-6:return False
  p=geom.road_ribbon(a,b,width)
  return contained(p,parcel) and not any(overlap(p,q) for q in obstacles)
 edges=[[] for _ in nodes]
 for i,a in enumerate(nodes):
  for j,b in enumerate(nodes[:i]):
   if clear(a,b):
    d=math.dist(a,b);edges[i].append((j,d));edges[j].append((i,d))
 queue=[(0,0)];cost={0:0};prev={}
 while queue:
  c,i=heapq.heappop(queue)
  if c>cost[i]+1e-8:continue
  if i==1:
   path=[1]
   while path[-1]!=0:path.append(prev[path[-1]])
   return [nodes[j] for j in reversed(path)]
  for j,d in edges[i]:
   nc=c+d
   if nc<cost.get(j,math.inf):cost[j]=nc;prev[j]=i;heapq.heappush(queue,(nc,j))
 return None

def build_registered_recipe(plot,all_plots=None,datum=None):
 """Return one finite source/proxy recipe; never compile or mutate a source plan.

 plot: E1..E7 record from registered_source/plan.json. all_plots supplies shared
 boundary ownership. datum optionally has polygon_sha256, finished_floor_y_m,
 gate_id, gate_threshold_y_m and accepted=True; otherwise access stays pending.
 """
 plot=copy.deepcopy(plot);pid=plot['id'];layout=LAYOUTS[pid];poly=plot['polygon_xz_m'];floor=float(plot['pad_floor_y_m']);origin=centre(poly);shared=shared_edges(plot,all_plots or [plot]);gate=propose_gate(plot,poly,shared)
 placements=[];obstacles=[];adjustments=[];assets={};garden_props=[];houses=[]
 def place(role,asset,desired,yaw=0,search=5,margin=1.25):
  v=catalog()[asset];b=v['bounds'];w=b['max'][0]-b['min'][0];d=b['max'][2]-b['min'][2];pos,foot=fit_rect(desired,w,d,yaw,poly,obstacles,search,margin)
  door_y=v['metadata'].get('entrance',{}).get('position',[0,0,0])[1];py=floor-door_y if v['spec']['provider']=='ordinary_r2' else floor
  item=dict(id=pid+':registered:'+role,role=role,asset_key=v['asset_key'],source_provider=v['spec']['provider'],position_m=[pos[0],py,pos[1]],yaw_rad=yaw,scale=[1,1,1],local_bounds=b,footprint_xz_m=foot,finished_floor_y_m=floor,mesh_origin_policy='finished_floor_minus_actual_door_local_y' if v['spec']['provider']=='ordinary_r2' else 'root_or_base_at_owned_floor',door_local_y_m=door_y,requested_position_xz_m=desired,fit_adjustment_m=math.dist(pos,desired),assembly_class=v['spec']['params'].get('assembly_class'),roof_material_family='slate_gray' if asset in ('stone','stone_wing') else 'clay_red' if asset in ('palace','palace_wing','lodge') else 'wood_brown',ground_anchor=dict(datum_y_m=floor,preserve_xz=True,support_points_xz_m=rect(pos,2,2) if asset=='tree' else foot,maximum_support_height_delta_m=.75,footing_embed_m=1 if asset=='tree' else .5))
  placements.append(item);assets[v['asset_key']]=v['spec'];obstacles.append(foot)
  if asset not in ('bed','tree'):
   item['entrances']=[]
   for j,door in enumerate(v['metadata']['entrance']['all_positions']):
    dp=xform([door[0],door[2]],pos,yaw);ep=xform([door[0],b['max'][2]],pos,yaw);item['entrances'].append(dict(id=item['id']+':door:'+str(j),door_xyz_m=[dp[0],py+door[1],dp[1]],envelope_threshold_xz_m=ep,outward_xz=[math.sin(yaw),math.cos(yaw)]))
   body=v['metadata']['body_bounds'];item['foundation_cutout_xz_m']=[xform(q,pos,yaw) for q in rect([(body['min'][0]+body['max'][0])/2,(body['min'][2]+body['max'][2])/2],body['max'][0]-body['min'][0],body['max'][2]-body['min'][2])];houses.append(item)
  else:garden_props.append(item)
  adjustments.append(dict(id=item['id'],distance_m=item['fit_adjustment_m']));return item
 for role,key,pos,yaw in layout['houses']:place(role,key,pos,yaw)
 # A coherent frame is placed first. Beds are never individually deleted to fit.
 gp,gw,gd=layout['garden'];gcenter,gpoly=fit_rect(gp,gw,gd,0,poly,obstacles,6,1.0)
 nx=2;nz=2 if gd<=12 else 3;xs=(-max(4,gw/4),max(4,gw/4));zs=tuple((j-(nz-1)/2)*(gd-5)/max(1,nz-1) for j in range(nz))
 for ix,x in enumerate(xs):
  for iz,z in enumerate(zs):place('garden_bed_'+str(ix)+'_'+str(iz),'bed',[gcenter[0]+x,gcenter[1]+z],search=0,margin=.05)
 # Orchard punctuation belongs to this property. No separate estate planting pass.
 for i,p in enumerate(layout['trees']):place('orchard_tree_'+str(i),'tree',p,search=5,margin=.25)
 gate=propose_gate(plot,poly,shared,obstacles)
 # Route every actual door to the single usable gate through the irregular parcel.
 routes=[];route_errors=[]
 for h in houses:
  for e in h['entrances']:
   threshold=e['envelope_threshold_xz_m'];start=add(threshold,e['outward_xz'],1.05)
   middle=route_in_parcel(start,gate['inside_point_xz_m'],poly,obstacles,1.8)
   if not middle:route_errors.append(dict(check='unroutable_actual_door',door_id=e['id']));continue
   points=[threshold]+middle+[gate['center_xz_m']];ribbons=[geom.road_ribbon(a,b,1.8) for a,b in zip(points,points[1:]) if math.dist(a,b)>1e-5]
   routes.append(dict(id=e['id']+':route',owner_id=h['id'],door_id=e['id'],gate_id=gate['id'],width_m=1.8,polyline_xz_m=points,ribbon_polygons_xz_m=ribbons,actual_door_bridge_xz_m=[[e['door_xyz_m'][0],e['door_xyz_m'][2]],threshold],full_polyline_xyz_m=[e['door_xyz_m']]+[[p[0],floor,p[1]] for p in points],surface_owner=pid+':registered:infrastructure'))
 # A real garden entry is routed, but bed-row crossing gaps stay open on its floor.
 garden_entries=[[gcenter[0],gcenter[1]+sign*(gd/2-.5)] for sign in (-1,1)]+[[gcenter[0]+sign*(gw/2-.5),gcenter[1]] for sign in (-1,1)]
 middle=None
 for garden_entry in sorted(garden_entries,key=lambda p:math.dist(p,gate['inside_point_xz_m'])):
  middle=route_in_parcel(garden_entry,gate['inside_point_xz_m'],poly,obstacles,1.8)
  if middle:break
 if middle:
  points=middle+[gate['center_xz_m']];routes.append(dict(id=pid+':registered:garden_walk',owner_id=pid,kind='garden_walk',gate_id=gate['id'],width_m=1.8,polyline_xz_m=points,ribbon_polygons_xz_m=[geom.road_ribbon(a,b,1.8) for a,b in zip(points,points[1:]) if math.dist(a,b)>1e-5],full_polyline_xyz_m=[[p[0],floor,p[1]] for p in points],surface_owner=pid+':registered:infrastructure'))
 else:route_errors.append(dict(check='unroutable_garden_entry'))
 court_center,cw,cd=layout['court'];court_pieces=[]
 for tri in triangulate(poly):
  part=geom.convex_intersection(rect(court_center,cw,cd),tri)
  if geom.polygon_area(part)>1e-7:court_pieces.append(part)
 for cut in [h['footprint_xz_m'] for h in houses]+[gpoly]:court_pieces=[q for p in court_pieces for q in geom.convex_difference(p,cut) if geom.polygon_area(q)>1e-7]
 regions=[dict(id=pid+':registered:formal_garden',land_use='private_formal_kitchen_garden',polygon_xz_m=gpoly,material='grass',area_m2=gw*gd)]+[dict(id=pid+':registered:service_court:'+str(i),land_use='arrival_and_service_court',polygon_xz_m=p,material='stone_dark',area_m2=geom.polygon_area(p)) for i,p in enumerate(court_pieces)]
 if datum:
  if datum.get('polygon_sha256')!=sha(poly) or not datum.get('accepted') or abs(datum['finished_floor_y_m']-floor)>1e-6 or datum['gate_id']!=gate['id'] or abs(datum['gate_threshold_y_m']-floor)>1e-6:raise ValueError('Rejected or mismatched registered datum contract')
  gate['external_grade_status']='accepted_exact_registered_datum'
 result=dict(schema='riverstone.registered_property.recipe.v1',id=pid,property_type=layout['form'],composition_intent=layout['name'],status='source_proxy_candidate',source_plot_sha256=sha(plot),source_polygon_sha256=sha(poly),plot=plot,origin_xz_m=origin,placements=placements,cache_specs=assets,gates=[gate],entrance_routes=routes,ground_regions=regions,shared_edge_ownership={str(k):v for k,v in shared.items()},surface_ownership=dict(owner_id=pid+':registered:infrastructure',polygon_xz_m=poly,exclusive=True,floor_y_m=floor,terrain_top_faces_must_exclude=True,garden_and_path_floors_owned_here=True,foundation_cutouts_xz_m=[h['foundation_cutout_xz_m'] for h in houses]),source_errors=route_errors,fit_adjustments=adjustments,scale_policy='native_modules_only',runtime_ready=False,external_access_resolved=bool(datum),replacement_proposal=dict(source_building_ids=plot.get('building_ids',[]),apply_status='proposal_only_no_scene_mutation'))
 result['metrics']=dict(plot_area_m2=geom.polygon_area(poly),building_count=len(houses),building_footprint_m2=sum(geom.polygon_area(h['footprint_xz_m']) for h in houses),formal_garden_area_m2=gw*gd,court_area_m2=sum(r['area_m2'] for r in regions if 'court' in r['land_use']),garden_beds=nx*nz,orchard_trees=len(layout['trees']),routed_actual_doors=sum('door_id' in r for r in routes))
 result['infrastructure_spec']=infrastructure_spec(result);result['checks']=validate_recipe(result);return result

def infrastructure_spec(recipe):
 plot=recipe['plot'];poly=plot['polygon_xz_m'];origin=recipe['origin_xz_m'];floor=plot['pad_floor_y_m'];xyz=plot['world_boundary_xyz_m'];segments=[];spans=[]
 # Variable bottom Y follows the shared retaining-wall foot controls; tops stay
 # at the estate bench +3.5. Short <=6m provenance spans are sampled together.
 for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  shared=recipe['shared_edge_ownership'].get(str(i));owner=shared['owner_plot_id'] if shared else plot['id'];length=math.dist(a,b);u=unit(a,b);n=[-u[1],u[0]]
  segment=dict(edge_index=i,closure_owner_plot_id=owner,shared_with=shared.get('other_plot_id') if shared else None,a_xz_m=a,b_xz_m=b);segments.append(segment)
  if owner!=plot['id']:continue
  count=math.ceil(length/6)
  for j in range(count):
   ta,tb=j/count,(j+1)/count;pa,pb=add(a,u,ta*length),add(a,u,tb*length);ya=xyz[i][1]+ta*(xyz[(i+1)%len(xyz)][1]-xyz[i][1]);yb=xyz[i][1]+tb*(xyz[(i+1)%len(xyz)][1]-xyz[i][1])
   spans.append(dict(id=plot['id']+':edge:'+str(i)+':span:'+str(j),edge_index=i,polygon_xz_m=[pa,pb,add(pb,n,1),add(pa,n,1)],bottom_y_m=min(ya,yb,floor)-.5,top_y_m=floor+3.5,support_points_xyz_m=[[pa[0],ya,pa[1]],[pb[0],yb,pb[1]]],max_length_m=6,maximum_foot_delta_m=abs(ya-yb)))
 return dict(provider='registered_property',kind='owned_irregular_floor_and_boundary',property_id=plot['id'],origin_xz_m=origin,floor_y_m=floor,ownership_polygon_xz_m=poly,ground_regions=recipe['ground_regions'],routes=recipe['entrance_routes'],foundation_cutouts_xz_m=recipe['surface_ownership']['foundation_cutouts_xz_m'],gates=recipe['gates'],boundary_edges=segments,boundary_spans=spans,one_solid=True,pitch_m=.5)

def make_infrastructure_master(spec):
 """Ordinary common schema, one solid. No new mesher and no cell editing."""
 ops=[];origin=spec['origin_xz_m'];floor=spec['floor_y_m']
 def extrude(label,poly,y0,y1,material='stone',action='paint'):
  if geom.polygon_area(poly)<1e-8:return
  op=dict(id=label,part='solid',action=action,shape=dict(kind='extrusion',polygon=[[p[0]-origin[0],-(p[1]-origin[1])] for p in poly],z_min=y0-floor,z_max=y1-floor),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]]))
  if action=='paint':op['material']=material
  ops.append(op)
 # Concave parcel is explicitly triangulated; same-solid union removes seams.
 for j,p in enumerate(triangulate(spec['ownership_polygon_xz_m'])):extrude('owned_floor_'+str(j),p,floor-.5,floor,'grass')
 for j,r in enumerate(spec['ground_regions']):extrude('land_use_'+str(j),r['polygon_xz_m'],floor-.5,floor,r['material'])
 for j,r in enumerate(spec['routes']):
  for k,p in enumerate(r['ribbon_polygons_xz_m']):
   for n,tri in enumerate(triangulate(spec['ownership_polygon_xz_m'])):extrude('walk_'+str(j)+'_'+str(k)+'_'+str(n),geom.convex_intersection(p,tri),floor-.5,floor,'stone_dark')
 for j,p in enumerate(spec['foundation_cutouts_xz_m']):extrude('foundation_cut_'+str(j),p,floor-1,floor+.1,action='cut')
 for j,s in enumerate(spec['boundary_spans']):
  for k,tri in enumerate(triangulate(spec['ownership_polygon_xz_m'])):extrude('joined_wall_'+str(j)+'_'+str(k),geom.convex_intersection(s['polygon_xz_m'],tri),s['bottom_y_m'],s['top_y_m'])
 for j,g in enumerate(spec['gates']):
  # Source cut leaves a genuine five-metre opening down to the shared floor.
  p=geom.road_ribbon(g['inside_point_xz_m'],g['outside_point_xz_m'],g['width_m']);extrude('gate_void_'+str(j),p,floor,floor+4.5,action='cut')
 return dict(schema='riverstone.voxel.master.v1',id='registered_property_'+sha(spec)[:16],revision=1,axes=dict(up='+Y',front='+Z',right='+X'),grid_origin=[0,0,0],materials=PALETTE,components=[dict(id='infrastructure',parts=[dict(id='solid',pivot=[0,0,0])],operations=ops)],instances=[dict(id='infrastructure',component='infrastructure')],metadata=dict(one_solid_floor_and_boundary=True,source_spans=spec['boundary_spans'],shared_boundary_ownership=spec['boundary_edges'],floor_y_m=floor,source_only=True,individual_source_part_provenance=True,no_cell_editing=True))

def validate_recipe(r):
 errors=list(r['source_errors']);poly=r['plot']['polygon_xz_m'];solids=r['placements'];floor=r['plot']['pad_floor_y_m']
 for i,p in enumerate(solids):
  if p['scale']!=[1,1,1]:errors.append(dict(check='scaled_module',id=p['id']))
  if not contained(p['footprint_xz_m'],poly):errors.append(dict(check='escaping_source_plot',id=p['id']))
  for q in solids[:i]:
   if overlap(p['footprint_xz_m'],q['footprint_xz_m']):errors.append(dict(check='solid_overlap',ids=[p['id'],q['id']]))
  for e in p.get('entrances',[]):
   if abs(e['door_xyz_m'][1]-floor)>1e-7:errors.append(dict(check='wrong_actual_threshold_y',id=e['id']))
 doors={e['id'] for p in solids for e in p.get('entrances',[])};routed={a.get('door_id') for a in r['entrance_routes']}
 if doors-routed:errors.append(dict(check='missing_door_route',ids=sorted(doors-routed)))
 for path in r['entrance_routes']:
  for q in path['ribbon_polygons_xz_m']:
   # Boundary-end ribbon may extend up to half its width outside at an oblique
   # gate; ownership is clipped in the one-solid floor, not a second path plane.
   for p in solids:
    if overlap(q,p['footprint_xz_m']):errors.append(dict(check='route_solid_overlap',route=path['id'],solid=p['id']))
 return dict(valid=not errors,errors=errors,all_actual_doors_have_routes=doors<=routed,native_scale=True,one_common_boundary_solid=True,external_gate_grade_verified=r['external_access_resolved'])

def load_registered_plots():
 path=CITY/'registered_source/plan.json';raw=path.read_bytes();plan=json.loads(raw);plan['_input_file_sha256']=hashlib.sha256(raw).hexdigest();plots=[p for p in plan['plots'] if p['id'] in IDS]
 if len(plots)!=7:raise ValueError('Expected seven registered source parcels')
 return plan,plots

def generate():
 plan,plots=load_registered_plots();out=HERE/'generated';out.mkdir(exist_ok=True);recipes=[]
 for p in plots:
  try:
   from .ownership import road_owned_parcel
   ownership=road_owned_parcel(p,plan['roads'])
   if ownership['removed_union_area_m2']>.0001:raise ValueError('Public road ownership must be resolved before authoring '+p['id'])
   r=build_registered_recipe(p,plots);r['public_road_ownership_audit']=ownership;r['registered_source_sha256']=plan['_input_file_sha256']
   r['replacement_proposal']['source_owned_path_ids']=[q['id'] for q in plan['paths'] if q.get('owner_plot_id')==p['id']]
   r['replacement_proposal']['preserve_public_road_ids']=sorted({q['road_id'] for q in plan['paths'] if q.get('owner_plot_id')==p['id'] and q.get('road_id')})
   recipes.append(r);(out/(p['id']+'.recipe.json')).write_text(json.dumps(r,indent=2)+'\n');print(p['id'],r['checks'],r['metrics'],flush=True)
  except ValueError as exc:print(p['id'],'LAYOUT FAILURE',str(exc),flush=True);raise
 assets={k:v for r in recipes for k,v in r['cache_specs'].items()};cache=json.loads((HERE.parent/'cache/manifest.json').read_text())['assets'];records={}
 for k,s in assets.items():
  records[k]=dict(cache_spec=s,resource=frozen.resource_for(s),status='persisted_compiled_reuse' if k in cache else 'existing_source_requires_compile' if k in json.loads((HERE.parent/'generated/cache_catalog.json').read_text())['assets'] else 'new_source_requires_compile',verified_runtime_asset=cache.get(k))
 wrappers=[]
 for r in recipes:
  master=make_infrastructure_master(r['infrastructure_spec']);path=out/(r['id']+'.infrastructure.master.json');path.write_text(json.dumps(master,separators=(',',':'))+'\n');wrappers.append(dict(property_id=r['id'],master_id=master['id'],master_path=str(path.relative_to(ROOT)),master_sha256=file_sha(path),operation_count=sum(len(c['operations']) for c in master['components']),resource=dict(pitch=.5),status='source_only_pending_gate_grade_and_visual_review'))
 gatepack=dict(schema='riverstone.registered_property.gate_proposals.v1',registered_source_sha256=plan['_input_file_sha256'],records=[dict(property_id=r['id'],polygon_xz_m=r['plot']['polygon_xz_m'],polygon_sha256=r['source_polygon_sha256'],floor_y_m=r['plot']['pad_floor_y_m'],gates=r['gates'],boundary_ownership=r['shared_edge_ownership']) for r in recipes]);(out/'gate_proposals.json').write_text(json.dumps(gatepack,indent=2)+'\n')
 summary=dict(schema='riverstone.registered_property.source_pack.v1',status='source_proxy_candidates_no_scene_integration',source_image_sha256=file_sha(ROOT/'world_city/reference/revision_03/city_social_water_concept.png'),registration_sha256=file_sha(CITY/'image_registration/controls.json'),registered_source_sha256=plan['_input_file_sha256'],road_controls_sha256=file_sha(CITY/'registered_source/road_controls.json'),terrain_author_sha256=file_sha(CITY/'registered_topography/author.py'),properties=[dict(id=r['id'],file=r['id']+'.recipe.json',metrics=r['metrics'],checks=r['checks']) for r in recipes],asset_manifest=records,infrastructure_sources=wrappers,budget=dict(building_and_garden_unique_assets=len(assets),persisted_reused_assets=sum(k in cache for k in assets),uncompiled_shared_modules=sum(k not in cache for k in assets),uncompiled_property_infrastructure=len(wrappers),compile_candidate_cap_per_asset=300000,compile_output_cap_per_asset=100000,compile_performed=False),runtime_ready=False,unresolved_requirements=['actual exterior gate grade acceptance','direct registered 3D visual review'])
 if file_sha(CITY/'registered_source/plan.json')!=plan['_input_file_sha256']:raise ValueError('Source plan changed during recipe generation; do not seal mixed inputs')
 (out/'pack.json').write_text(json.dumps(summary,indent=2)+'\n');return recipes,summary
if __name__=='__main__':generate()
