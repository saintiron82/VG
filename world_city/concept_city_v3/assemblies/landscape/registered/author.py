"""Finite registered institutional landscapes; common sources and native instancing."""
from __future__ import annotations
import copy,json,math
from pathlib import Path
from . import context as c
from . import fit_blocks
from world_city.concept_city_v3.assemblies.property.registered import author as a
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from world_city.concept_city_v3.assemblies.landscape import recipes as reusable
from world_city.concept_city_v3.registered_topography import author as terrain
from world_city.concept_city_v3.assemblies.property.registered.r1 import author as surfaces
HERE=c.HERE;OUT=HERE/'generated'
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def standard(master_id,ops):return dict(schema='riverstone.voxel.master.v1',id=master_id,revision=1,axes={'up':'+Y','front':'+Z','right':'+X'},grid_origin=[0,0,0],materials=a.PALETTE,components=[dict(id='landscape',parts=[dict(id='solid',pivot=[0,0,0])],operations=ops)],instances=[dict(id='landscape',component='landscape')])
def small_master(kind):
 ops=[]
 def paint(shape,mat):ops.append(dict(id=kind+':'+str(len(ops)),part='solid',action='paint',shape=shape,material=mat))
 def box(lo,hi,mat):paint(dict(kind='box',min=lo,max=hi),mat)
 if kind=='burial_row_four':
  for i,x in enumerate((-4.5,-1.5,1.5,4.5)):
   box([x-.75,-.5,-1.25],[x+.75,.5,1.25],'stone_dark');box([x-.5,0,-1.75],[x+.5,1.5,-1.25],'stone_light')
   if i in (1,3):box([x-.75,.75,-1.75],[x+.75,1.25,-1.25],'stone_light');box([x-.25,1.25,-1.75],[x+.25,2,-1.25],'stone_light')
  bounds=dict(min=[-5.25,-.5,-1.75],max=[5.25,2,1.25]);clear=[12,4]
 elif kind=='columnar_cypress':
  box([-.5,-1,-.5],[.5,4,.5],'timber');paint(dict(kind='lathe',profile=[[0,1.5],[.6,1.5],[1.15,3],[1.5,6],[1.35,9],[.8,12],[0,14]]),'grass');bounds=dict(min=[-1.5,-1,-1.5],max=[1.5,14,1.5]);clear=[3,3]
 elif kind=='park_bench':
  box([-2,.5,-.5],[2,1,.5],'timber');box([-1.5,-.5,-.5],[-1,1,.5],'stone');box([1,-.5,-.5],[1.5,1,.5],'stone');bounds=dict(min=[-2,-.5,-.5],max=[2,1,.5]);clear=[4,1]
 else:raise ValueError(kind)
 m=standard('registered_landscape_'+kind,ops);m['metadata']=dict(role=kind,local_bounds=bounds,clearance_width_depth_m=clear,source_only=True);return m

def box_poly(center,w,d,yaw):return a.rect(center,w,d,yaw)
def gate_candidates(block):
 w,d=block['width'],block['depth'];local=[([7,-d/2],[0,-1]),([7,d/2],[0,1])] if block['kind']=='cemetery' else [([0,-d/2],[0,-1]),([w/2,0],[1,0]),([0,d/2],[0,1]),([-w/2,0],[-1,0])];yaw=math.radians(block['yaw']);out=[]
 for i,(p,n) in enumerate(local):
  center=a.xform(p,block['position'],yaw);normal=a.xform(n,[0,0],yaw);out.append(dict(id=block['id']+':gate:'+str(i),center_xz_m=center,inside_point_xz_m=a.add(center,normal,-3),outside_point_xz_m=a.add(center,normal,2),outward_xz=normal,width_m=4,local_center_xz_m=p))
 return out

def connect_block(b,allblocks,data):
 space=next(s for s in data['plan']['spaces'] if s['id']==('SITE_CLERGY' if b['space']=='SITE_CEMETERY' else b['space']));domain=space['polygon_xz_m'];gates=gate_candidates(b)
 if b['kind']=='public_park':
  proposal=json.loads((HERE/'park_access_candidate.json').read_text());assert proposal['source_bindings']==data['sources'];assert proposal['source_park_polygon_sha256']==a.sha(b['polygon_xz_m']);selected=copy.deepcopy(proposal['selected']);assert selected
  g=selected['candidate']['gate'];g.update(id=b['id']+':road_gate',outward_xz=[-v for v in g['inward_xz']],local_center_xz_m=a.xform([g['center_xz_m'][i]-b['position'][i] for i in range(2)],[0,0],-math.radians(b['yaw'])))
  surface=selected['external_surface'];surface.update(id=b['id']+':external_access',surface_owner='REGISTERED_LANDSCAPE:SITE_COMMON');surface['public_lane_endpoint']['shared_height_policy']='The public road owner must share the exact declared piecewise-linear terminal boundary; do not independently resample nonlinear height between source seam vertices.'
  return g,dict(id=b['id']+':public_approach',status='bounded_finite_profile_pending_independent_access_and_support',gate_id=g['id'],width_m=3,polyline_xz_m=selected['candidate']['external_centerline_xz_m'],internal_gate_branch_xz_m=selected['internal_gate_branch_xz_m'],external_surface=surface,candidate=selected['candidate'],proposal_path=str((HERE/'park_access_candidate.json').relative_to(c.ROOT)),proposal_sha256=a.file_sha(HERE/'park_access_candidate.json'))
 prefix='cathedral' if b['space'].startswith('SITE_CL') or b['space']=='SITE_CEMETERY' else 'monastery';options=[]
 for g in gates:
  for route in data['approaches']['routes']:
   points=route.get('polyline_xz_m') or []
   if not route['placement_id'].startswith(prefix):continue
   for u,v in zip(points[1:],points[2:]):
    target,t=a.near(u,v,g['outside_point_xz_m']);options.append((math.dist(g['outside_point_xz_m'],target),g,route,target))
 for distance,g,target_route,target in sorted(options,key=lambda q:q[0])[:20]:
  if not a.contained(a.rect(target,2.2,2.2),domain):continue
  start=g['outside_point_xz_m'];xmin,xmax=min(start[0],target[0])-25,max(start[0],target[0])+25;zmin,zmax=min(start[1],target[1])-25,max(start[1],target[1])+25;window=a.rect([(xmin+xmax)/2,(zmin+zmax)/2],xmax-xmin,zmax-zmin)
  obstacles=[e['polygon_xz_m'] for e in data['exclusions'] if e['kind'] in ('public_road_and_half_metre_shoulder','native_landmark_outer_envelope','native_ordinary_outer_envelope','finite_water') and a.overlap(e['polygon_xz_m'],window)]
  obstacles += [q['polygon_xz_m'] for q in allblocks if q['id']!=b['id'] and a.overlap(q['polygon_xz_m'],window)]
  middle=a.route_in_parcel(start,target,domain,obstacles,2.2)
  if not middle:continue
  points=[g['center_xz_m']]+middle;ribbons=[a.geom.road_ribbon(u,v,2.2) for u,v in zip(points,points[1:]) if math.dist(u,v)>1e-6]
  if any(a.overlap(p,b['polygon_xz_m']) for p in ribbons[1:]):continue
  return g,dict(id=b['id']+':native_walk_connection',status='horizontal_branch_to_reserved_native_approach; upstream_vertical_acceptance_pending',gate_id=g['id'],target_native_entrance_id=target_route['entrance_id'],width_m=2.2,polyline_xz_m=points,ribbon_polygons_xz_m=ribbons,finished_floor_y_m=b['floor'],full_polyline_xyz_m=[[x,b['floor'],z] for x,z in points])
 return gates[0],dict(id=b['id']+':native_walk_connection',status='unresolved_bounded_native_approach',gate_id=gates[0]['id'])

def build():
 OUT.mkdir(exist_ok=True);data=c.load();proposal=json.loads((HERE/'block_proposals.json').read_text());assert proposal['sources']==data['sources'];blocks=copy.deepcopy(proposal['blocks']);assert all(b['status']=='bounded_frame_clear' for b in blocks);new={k:small_master(k) for k in ('burial_row_four','columnar_cypress','park_bench')};assets={};placements=[];sites=[];world_index=a.geom._SpatialIndex(20);exby={}
 for j,e in enumerate(data['exclusions']):world_index.add(str(j),e['polygon_xz_m']);exby[str(j)]=e
 oldprop=json.loads((a.HERE/'r1/repair_01/resolved_placements.json').read_text());wood=json.loads((c.CITY/'assemblies/landscape/registered_woodland/resolved_placements.json').read_text())
 def asset(role):
  if role in new:
   m=new[role];return m['id'],dict(kind='new_common',master=m,resource={'pitch':.5},bounds=m['metadata']['local_bounds'],clear=m['metadata']['clearance_width_depth_m'])
  if role in ('bed','orchard'):
   v=a.catalog()['bed' if role=='bed' else 'tree'];m=oldprop['asset_manifest'][v['asset_key']];return v['asset_key'],dict(kind='verified_native_cache',cached=m,bounds=v['bounds'],clear=[v['bounds']['max'][0]-v['bounds']['min'][0],v['bounds']['max'][2]-v['bounds']['min'][2]])
  spec={'kind':'forest_tree','form':role};key=reusable.source_key(spec);m=wood['assets'][key];bounds=m['bounds'];return key,dict(kind='verified_native_cache',cached=m,bounds=bounds,clear=[12,12] if role=='broad_oak' else [14,10])
 for b in blocks:
  gate,connection=connect_block(b,blocks,data);yaw=math.radians(b['yaw']);sid=b['id'];placed=[];internal=[]
  def at(p):return a.xform(p,b['position'],yaw)
  def walk(name,points,width=3):
   wp=[at(p) for p in points];internal.append(dict(id=sid+':'+name,width_m=width,polyline_xz_m=wp,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,width) for u,v in zip(wp,wp[1:])]))
  if b['kind']=='cemetery':walk('burial_aisle',[[7,-b['depth']/2+2],[7,b['depth']/2-2]],2.5)
  else:
   walk('main_walk',[[-b['width']/2+2,0],[b['width']/2-2,0]],3);walk('cross_walk',[[0,-b['depth']/2+2],[0,b['depth']/2-2]],3)
  gate_local=gate['local_center_xz_m'];anchor=[7,0] if b['kind']=='cemetery' else [0,0]
  if b['kind']=='public_park':
   wp=connection['internal_gate_branch_xz_m'];internal.append(dict(id=sid+':gate_walk',width_m=3,polyline_xz_m=wp,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,3) for u,v in zip(wp,wp[1:])]))
  else:walk('gate_walk',[anchor,gate_local],2.5 if b['kind']=='cemetery' else 3)
  if b['kind']=='cemetery':
   for j,z in enumerate((-23,-17,-11,-5,1,7,13,19,25)):walk('burial_row_access_'+str(j),[[-8,z-3],[7,z-3]],1.5)
  reserved=[p for r in internal for p in r['ribbon_polygons_xz_m']];errors=[]
  def place(role,local,tag):
   key,rec=asset(role);pos=at(local);foot=a.rect(pos,*rec['clear'],yaw)
   hits=[exby[k]['id'] for k in world_index.candidates(foot) if a.overlap(foot,exby[k]['polygon_xz_m'])]
   if not a.contained(foot,b['polygon_xz_m']) or hits or any(a.overlap(foot,p) for p in reserved) or any(a.overlap(foot,p['footprint_xz_m']) for p in placed):raise ValueError('Designed group collision: '+sid+':'+tag+' '+str(hits))
   is_tree=role in ('orchard','broad_oak','spreading_elm','columnar_cypress');p=dict(id=sid+':'+tag,site_id=sid,asset_key=key,role=role,position_m=[pos[0],b['floor'],pos[1]],yaw_rad=yaw,scale=[1,1,1],local_bounds=rec['bounds'],footprint_xz_m=foot,ground_anchor=dict(datum_y_m=b['floor'],preserve_xz=True,support_points_xz_m=a.rect(pos,1 if role=='columnar_cypress' else 2,1 if role=='columnar_cypress' else 2,yaw) if is_tree else foot,support_kind='trunk_root' if is_tree else 'short_native_base',maximum_support_height_delta_m=.75,footing_embed_m=1 if is_tree else .5),surface_owner='REGISTERED_LANDSCAPE:'+b['space'],source_space_id=b['space']);placed.append(p);assets[key]=rec
  kind=b['kind']
  if kind=='cemetery':
   for j,z in enumerate((-23,-17,-11,-5,1,7,13,19,25)):place('burial_row_four',[-2,z],'burial_row_'+str(j))
  elif kind=='orchard':
   for ix,x in enumerate((-26,-16,-6,6,16,26)):
    for iz,z in enumerate((-46,-36,-26,-16,-6,6,16,26,36,46)):place('orchard',[x,z],f'fruit_row_{ix}_{iz}')
  elif kind=='public_park':
   for i,p in enumerate(((-35,-9),(-17,9),(12,-9),(34,9))):place('orchard',p,'small_grove_'+str(i))
   for i,p in enumerate(((-34,8),(34,-8))):place('broad_oak',p,'shade_oak_'+str(i))
   for i,p in enumerate(((-25,3),(25,-3))):place('park_bench',p,'promenade_bench_'+str(i))
  else:
   if kind=='productive_garden':xs=(-37.5,-31,-24.5,-18,-11.5,-5,5,11.5,18,24.5,31,37.5);zs=(-27.5,-23,-18.5,-14,-9.5,-5,5,9.5,14,18.5,23,27.5)
   elif kind=='cloister_garden':xs=(-13,-5,5,13);zs=(-12,-6,6,12)
   elif kind=='kitchen_garden':xs=(-19,-12,-5,5,12,19);zs=(-15,-9,-4,4,9,15)
   else:xs=(-24,-16,-8,8,16,24);zs=(-13,-7,7,13)
   for i,x in enumerate(xs):
    for j,z in enumerate(zs):place('bed',[x,z],f'crop_bed_{i}_{j}')
   if kind=='cloister_garden':
    for i,p in enumerate(((-17,-17),(-17,17),(17,-17),(17,17))):place('columnar_cypress',p,'cloister_cypress_'+str(i))
  placements.extend(placed);sites.append(dict(**{k:v for k,v in b.items() if k!='status'},gates=[gate],internal_paths=internal,external_connection=connection,placements=placed,source_errors=errors,enclosure_kind='inherited_native_cloister' if b.get('inherit_enclosure') else 'continuous_low_common_wall_with_defined_gate',wall_height_m=0 if b.get('inherit_enclosure') else 1.0 if kind=='public_park' else 1.5,metrics=dict(owned_area_m2=b['area_m2'],native_instances=len(placed),burials=36 if kind=='cemetery' else 0),status='bounded_source_candidate'))
  print(sid,len(placed),connection['status'],flush=True)
 wrappers=[]
 for space in ('SITE_CLERGY','SITE_CEMETERY','SITE_MONASTERY','SITE_COMMON'):
  subset=[s for s in sites if s['space']==space]
  if not subset:continue
  floor=subset[0]['floor'];origin=a.centre([s['position'] for s in subset]);ops=[];floor_regions=[];boundary_regions=[]
  def extrude(label,poly,y0,y1,mat='grass',action='paint'):
   if a.geom.polygon_area(poly)<1e-8:return
   op=dict(id=label,part='solid',action=action,shape=dict(kind='extrusion',polygon=[[p[0]-origin[0],-(p[1]-origin[1])] for p in poly],z_min=y0,z_max=y1),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]]))
   if action=='paint':op['material']=mat
   ops.append(op)
  clip_masks=[e['polygon_xz_m'] for e in data['exclusions'] if e['kind'] in ('public_road_and_half_metre_shoulder','native_landmark_floor_owner','existing_source_path_reservation','native_door_approach_pending_vertical_repair','native_approach_round_join')]
  for s in subset:
   poly=s['polygon_xz_m'];floor_regions.append(poly);extrude(s['id']+':owned_floor',poly,-.5,0)
   for path in s['internal_paths']:
    for i,p in enumerate(path['ribbon_polygons_xz_m']):extrude(path['id']+':'+str(i),p,-.5,0,'stone_light')
   for i,p in enumerate(s['external_connection'].get('ribbon_polygons_xz_m',[])):
    pieces=[p]
    for cut in clip_masks:
     if any(a.overlap(z,cut) for z in pieces):pieces=[part for z in pieces for part in a.geom.convex_difference(z,cut) if a.geom.polygon_area(part)>1e-7]
    for j,z in enumerate(pieces):extrude(s['id']+':connection:'+str(i)+':'+str(j),z,-.5,0,'stone_light');floor_regions.append(z)
   if s['wall_height_m']:
    for i,(u,v) in enumerate(zip(poly,poly[1:]+poly[:1])):
     direction=a.unit(u,v);n=[-direction[1],direction[0]];wall=[u,v,a.add(v,n,.75),a.add(u,n,.75)];extrude(s['id']+':wall:'+str(i),wall,-.5,s['wall_height_m'],'stone');boundary_regions.append(wall)
    for g in s['gates']:extrude(g['id']+':void',a.geom.road_ribbon(g['inside_point_xz_m'],g['outside_point_xz_m'],g['width_m']),0,3,'stone','cut')
  master=standard('registered_institutional_'+space.lower()+'_'+a.sha(ops)[:12],ops);master['metadata']=dict(one_solid_floor_and_boundary=True,source_site_ids=[s['id'] for s in subset],exclusive_floor_regions_xz_m=floor_regions,boundary_regions_xz_m=boundary_regions,origin_xz_m=origin,floor_y_m=floor,source_only=True)
  external_surfaces=[s['external_connection']['external_surface'] for s in subset if 'external_surface' in s['external_connection']]
  for surface in external_surfaces:surfaces.append_surface(master,surface,origin,floor)
  master['id']='registered_institutional_'+space.lower()+'_'+a.sha(master['components'])[:12];master['metadata']['external_surface_profiles']=external_surfaces
  budget=candidate_budget(master);assert budget['within_candidate_cap'];path=OUT/(master['id']+'.master.json');write(path,master);wrappers.append(dict(id='REGISTERED_LANDSCAPE:'+space,asset_key=master['id'],source_path=str(path.relative_to(c.ROOT)),source_sha256=a.file_sha(path),position_m=[origin[0],floor,origin[1]],yaw_rad=0,scale=[1,1,1],source_site_ids=[s['id'] for s in subset],owned_floor_regions_xz_m=floor_regions,external_surface_profiles=external_surfaces,boundary_regions_xz_m=boundary_regions,candidate_budget=budget,resource={'pitch':.5},status='source_only_pending_compile_and_owned_surface_review'))
 for key,rec in assets.items():
  if rec['kind']=='new_common':
   path=OUT/(key+'.master.json');write(path,rec.pop('master'));rec.update(source_path=str(path.relative_to(c.ROOT)),source_sha256=a.file_sha(path),candidate_budget=candidate_budget(json.loads(path.read_text())))
  else:
   cached=rec['cached'];rp=cached.get('compiled_asset_ref',cached.get('render_path'));mp=cached['master_path'];assert a.file_sha(rp)==cached['render_sha256'];assert a.file_sha(mp)==cached['master_file_sha256']
 pack=dict(schema='riverstone.registered_institutional_landscape.v1',sources=data['sources'],sites=sites,placements=placements,assets=assets,wrappers=wrappers,metrics=dict(site_count=len(sites),native_instance_count=len(placements),burial_count=36,finite_land_use_area_m2=sum(s['area_m2'] for s in sites),new_shared_prop_masters=sum(v['kind']=='new_common' for v in assets.values()),verified_reused_prop_masters=sum(v['kind']=='verified_native_cache' for v in assets.values()),new_wrapper_count=len(wrappers)),status='source_only_pending_compile_external_access_and_actual_view',runtime_ready=False,applied_to_scene=False,limits=['Public park finite ramp profile is source-checked; independent full-width support, public seam ownership and sampled common traversal remain pending.','Institutional garden branches join reserved native approach candidates whose vertical acceptance remains external.','No outside forest or estate garden is owned or placed by this pack.','Only finite owned block/link floors replace ground; broad traced precinct polygons are provenance, never blanket floor replacement.'])
 write(OUT/'source_pack.json',pack);return pack
if __name__=='__main__':build()
