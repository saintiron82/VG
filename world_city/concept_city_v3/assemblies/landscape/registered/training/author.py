"""Finite registered drill ground: native perimeter modules and a genuinely open center."""
from __future__ import annotations
import copy,json,math
from pathlib import Path
from .. import context as c,author as landscape
from world_city.concept_city_v3.assemblies.property.registered import author as a
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from world_city.concept_city_v3.assemblies.property.registered.r1 import author as surfaces
from world_city.concept_city_v3.registered_topography.revisions.r07_native_interfaces import author as terrain
HERE=Path(__file__).resolve().parent;OUT=HERE/'generated';FLOOR=18.;SITE='SITE_TRAIN'
CORE=[[-379,-205],[-345,-221],[-272,-191],[-266,-161],[-309,-139],[-373,-165]]
LAYOUT=[('barrack_north','barrack',[-393,-198],math.pi/2),('barrack_south','barrack',[-392,-179],math.pi/2),('stable','stable',[-350,-145],math.pi-.38),('stores','lodge',[-375,-155],math.pi-.38)]
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def prop_master(kind):
 ops=[]
 def box(lo,hi,mat,action='paint'):
  q=dict(id=kind+':'+str(len(ops)),part='solid',action=action,shape=dict(kind='box',min=lo,max=hi))
  if action=='paint':q['material']=mat
  ops.append(q)
 if kind=='practice_target':
  for x in (-1,1):box([x-.25,-.5,-.5],[x+.25,3,.5],'timber')
  box([-1.25,1,-.5],[1.25,3.5,.5],'timber_light');box([-.75,1.5,.5],[.75,3,1],'mortar');box([-.25,2,.5],[.25,2.5,1],'earth');bounds=dict(min=[-1.25,-.5,-.5],max=[1.25,3.5,1])
 elif kind=='practice_rack':
  for x in (-1.75,1.75):box([x-.25,-.5,-.75],[x+.25,2.5,.75],'timber')
  box([-2,1,-.25],[2,1.5,.25],'timber');box([-2,2,-.25],[2,2.5,.25],'timber')
  for x in (-1,-.5,0,.5,1):box([x-.25,0,.25],[x+.25,2.5,.75],'timber_light')
  bounds=dict(min=[-2,-.5,-.75],max=[2,2.5,.75])
 elif kind=='water_trough':
  box([-2,-.5,-1],[2,1.5,1],'stone');box([-1.5,.5,-.5],[1.5,2,.5],'stone','cut');box([-1.5,.5,-.5],[1.5,1,.5],'water');bounds=dict(min=[-2,-.5,-1],max=[2,1.5,1])
 else:raise ValueError(kind)
 m=landscape.standard('registered_training_'+kind,ops);m['metadata']=dict(role=kind,local_bounds=bounds,sampling_safe_minimum_feature_m=.5);return m

def native_catalog(data):
 prop=json.loads((a.HERE/'r1/repair_01/resolved_placements.json').read_text());ordinary=data['ordinary'];out={}
 for role in ('stable','lodge'):
  catalog=a.catalog()[role];v=copy.deepcopy(prop['asset_manifest'][catalog['asset_key']]);out[role]=dict(asset_key=catalog['asset_key'],cache=v,metadata=catalog['metadata'])
 key='ordinary_r2_357c8088248bad';v=copy.deepcopy(ordinary['assets'][key]);v.update(asset_key=key,compiled_asset_ref=v['render_path'],master_file_sha256=v['master_sha256']);out['barrack']=dict(asset_key=key,cache=v,metadata=v['author_metadata']);return out

def source_inputs():
 data=c.load();fort_path=c.CITY/'assemblies/fortifications/registered/placement_r02/resolved_placements.json';fort=json.loads(fort_path.read_text());data['fortifications']=fort;data['sources']['fortifications']=dict(path=str(fort_path.relative_to(c.ROOT)),sha256=a.file_sha(fort_path));data['sources']['active_terrain_author']=dict(path=str(Path(terrain.__file__).relative_to(c.ROOT)),sha256=a.file_sha(terrain.__file__))
 data['exclusions']=[e for e in data['exclusions'] if not e['id'].startswith(('B_TRAIN_0:','B_TRAIN_1:'))]
 for p in fort['placements']:data['exclusions'].append(dict(id=p['id'],polygon_xz_m=p['outer_footprint_xz_m'],kind='native_fortification_outer_envelope'))
 return data

def make_gate(plan,poly):
 road=next(r for r in plan['roads'] if r['id']=='CASTLE_APPROACH');u,v=road['polyline_xz_m'][10:12];lo,hi=0.,1.
 for _ in range(50):
  t=(lo+hi)/2;point=a.add(u,[v[i]-u[i] for i in (0,1)],t)
  if terrain.road_height_at(road['id'],*point)<FLOOR:lo=t
  else:hi=t
 center=a.add(u,[v[i]-u[i] for i in (0,1)],(lo+hi)/2);tangent=a.unit(u,v);outward=[tangent[1],-tangent[0]];end=a.add(center,outward,road['width_m']/2);start=a.add(end,outward,12);gate=a.add(end,outward,14);right=[-outward[1],outward[0]];ramp=a.geom.road_ribbon(start,end,3);pocket=a.geom.road_ribbon(gate,start,5);landing=a.geom.road_ribbon(end,a.add(end,outward,-.5),3)
 assert a.contained(pocket,poly) and a.contained(ramp,poly)
 g=dict(id='TRAIN:level_court_gate',center_xz_m=gate,inside_point_xz_m=a.add(gate,outward,3),outside_point_xz_m=start,outward_xz=[-x for x in outward],width_m=5,finished_floor_y_m=FLOOR,road_id=road['id'])
 tri=[]
 def add(kind,points):
  for ids in ((0,1,2),(0,2,3)):
   ps=[points[i] for i in ids];tri.append(dict(kind=kind,vertices_xyz_m=ps,source_grade=surfaces.triangle_grade(ps)))
 add('level_gate_pocket',[[p[0],FLOOR,p[1]] for p in pocket]);direction=a.unit(start,end);right=[-direction[1],direction[0]];sides=(-1.5,-.5,.5,1.5)
 def at(t,s):
  p=a.add(a.add(start,direction,t*12),right,s);ep=a.add(end,right,s);return [p[0],FLOOR+t*(terrain.road_height_at(road['id'],*ep)-FLOOR),p[1]]
 for j in range(6):
  for s0,s1 in zip(sides,sides[1:]):add('service_ramp',[at(j/6,s0),at((j+1)/6,s0),at((j+1)/6,s1),at(j/6,s1)])
 for s0,s1 in zip(sides,sides[1:]):
  points=[a.add(a.add(end,direction,t),right,s) for t,s in ((0,s0),(.5,s0),(.5,s1),(0,s1))];add('public_lane_threshold_landing',[[p[0],terrain.road_height_at(road['id'],*p),p[1]] for p in points])
 support=[]
 for t in tri:
  for x,y,z in t['vertices_xyz_m']+[[sum(p[i] for p in t['vertices_xyz_m'])/3 for i in range(3)]]:
   existing=terrain.land_height_at(x,z);support.append([x,y,z,existing,y-existing])
 surface=dict(id='TRAIN:public_approach',property_id=SITE,surface_owner='TRAIN:owned_ground',finished_gate_floor_y_m=FLOOR,polygon_regions_xz_m=[pocket,ramp,landing],triangulated_top_surface=tri,height_evaluator='barycentric interpolation within explicit shared triangles',source_clear_width_m=3,source_gate_width_m=5,level_turning_pocket_width_m=5,ramp_run_m=12,public_lane_endpoint=dict(road_id=road['id'],road_segment_id='CASTLE_APPROACH:10',seam_xyz_m=[at(1,s) for s in sides],same_datum_landing_polygon_xz_m=landing,shared_height_api='registered_topography.revisions.r07_native_interfaces.author.road_height_at',shared_height_policy='Public owner must share the declared piecewise-linear seam, with any adjacent transition explicitly owned.'),support_samples_xyz_existing_delta=support,maximum_cut_fill_m=max(abs(p[4]) for p in support),maximum_triangle_grade=max(t['source_grade'] for t in tri),maximum_service_ramp_grade=max(t['source_grade'] for t in tri if t['kind']=='service_ramp'),maximum_inherited_public_landing_grade=max(t['source_grade'] for t in tri if t['kind']=='public_lane_threshold_landing'),status='pending_independent_interface_support_and_actual_view',skin_thickness_m=.5)
 return g,surface

def build():
 OUT.mkdir(exist_ok=True);data=source_inputs();space=next(s for s in data['plan']['spaces'] if s['id']==SITE);poly=space['polygon_xz_m'];assert a.contained(CORE,poly);catalog=native_catalog(data);placements=[];assets={};doors=[];support=[]
 idx=a.geom._SpatialIndex(20);by={}
 for j,e in enumerate(data['exclusions']):idx.add(str(j),e['polygon_xz_m']);by[str(j)]=e
 def hits(foot):return [by[k]['id'] for k in idx.candidates(foot) if a.overlap(foot,by[k]['polygon_xz_m'])]
 for name,role,pos,yaw in LAYOUT:
  rec=catalog[role];cache=rec['cache'];bounds=cache['bounds'];w=bounds['max'][0]-bounds['min'][0];d=bounds['max'][2]-bounds['min'][2];foot=a.rect(pos,w,d,yaw);assert a.contained(foot,poly) and not hits(foot) and not a.overlap(foot,CORE),(name,hits(foot));metadata=rec['metadata'];localy=metadata['entrance']['position'][1];origin=FLOOR-localy;entrances=[];outward=a.xform([0,1],[0,0],yaw)
  for j,point in enumerate(metadata['entrance'].get('all_positions',[metadata['entrance']['position']])):
   xz=a.xform([point[0],point[2]],pos,yaw);threshold=a.xform([point[0],bounds['max'][2]],pos,yaw);door=dict(id='TRAIN:'+name+':door:'+str(j),owner_id='TRAIN:'+name,door_xyz_m=[xz[0],origin+point[1],xz[1]],door_local_xyz_m=point,envelope_threshold_xz_m=threshold,outward_xz=outward,threshold_floor_y_m=FLOOR,closed_native_leaf=True);entrances.append(door);doors.append(door)
  positions=[pos]+foot;checks=[dict(point_xz_m=p,terrain_y_m=terrain.land_height_at(*p),owner_id=terrain.owner_at(*p)['owner_id'],floor_delta_m=FLOOR-terrain.land_height_at(*p)) for p in positions];assert max(abs(p['floor_delta_m']) for p in checks)<1e-6;support.append(dict(placement_id='TRAIN:'+name,samples=checks,foundation_embed_m=localy))
  placements.append(dict(id='TRAIN:'+name,asset_key=rec['asset_key'],role=role,semantic_function='two-door_garrison_sleeping_range' if role=='barrack' else 'horse_stable' if role=='stable' else 'drill_equipment_and_feed_store',source_provider='verified_common_cache',position_m=[pos[0],origin,pos[1]],yaw_rad=yaw,scale=[1,1,1],footprint_xz_m=foot,local_bounds=bounds,body_bounds=metadata['body_bounds'],entrances=entrances,finished_threshold_y_m=FLOOR,source_space_id=SITE,roof_material_intent='brown_wood' if role in ('barrack','stable') else 'red_clay',runtime_material_remap_pending=True));assets[rec['asset_key']]=dict(kind='verified_native_cache',cached=cache)
 prop_defs=[('practice_target',[-377,-214],-.38),('practice_target',[-369,-217],-.38),('practice_target',[-361,-220],-.38),('practice_target',[-353,-223],-.38),('practice_rack',[-384,-173],math.pi/2),('practice_rack',[-365,-150],math.pi-.38),('water_trough',[-337,-142],math.pi-.38)]
 for j,(kind,pos,yaw) in enumerate(prop_defs):
  m=prop_master(kind);bounds=m['metadata']['local_bounds'];lo=[math.floor(x/.5)*.5 for x in bounds['min']];hi=[math.ceil(x/.5)*.5 for x in bounds['max']];w=hi[0]-lo[0];d=hi[2]-lo[2];foot_center=a.xform([(lo[0]+hi[0])/2,(lo[2]+hi[2])/2],pos,yaw);foot=a.rect(foot_center,w,d,yaw);assert a.contained(foot,poly) and not hits(foot) and not a.overlap(foot,CORE),(kind,pos,hits(foot));assert not any(a.overlap(foot,p['footprint_xz_m']) for p in placements);key=m['id'];assets[key]=dict(kind='new_common',master=m,resource={'pitch':.5});placements.append(dict(id='TRAIN:'+kind+':'+str(j),asset_key=key,role=kind,position_m=[pos[0],FLOOR,pos[1]],yaw_rad=yaw,scale=[1,1,1],local_bounds=bounds,footprint_xz_m=foot,source_space_id=SITE))
 gate,surface=make_gate(data['plan'],poly);obstacles=[p['footprint_xz_m'] for p in placements]+[CORE]+[e['polygon_xz_m'] for e in data['exclusions'] if e['kind'] in ('public_road_and_half_metre_shoulder','native_fortification_outer_envelope','native_landmark_outer_envelope','native_ordinary_outer_envelope','finite_water') and a.overlap(e['polygon_xz_m'],poly)];routes=[]
 for p in placements:
  for door in p.get('entrances',[]):
   width=3 if p['role']=='stable' else 1.8;threshold=door['envelope_threshold_xz_m'];start=a.add(threshold,door['outward_xz'],width/2+.2);middle=a.route_in_parcel(start,gate['inside_point_xz_m'],poly,obstacles,width);assert middle,('No perimeter access',door['id']);points=[threshold]+middle+[gate['center_xz_m']];routes.append(dict(id=door['id']+':route',owner_id=p['id'],door_id=door['id'],gate_id=gate['id'],width_m=width,polyline_xz_m=points,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,width) for u,v in zip(points,points[1:])],actual_door_bridge_xz_m=[[door['door_xyz_m'][0],door['door_xyz_m'][2]],threshold],full_polyline_xyz_m=[door['door_xyz_m']]+[[x,FLOOR,z] for x,z in points]))
 # A dedicated 3m branch reaches the unobstructed drill center; other circulation stays at its edge.
 target=a.centre(CORE);middle=a.route_in_parcel(gate['inside_point_xz_m'],target,poly,[p['footprint_xz_m'] for p in placements]+obstacles[len(placements)+1:],3);assert middle;points=[gate['center_xz_m']]+middle;routes.append(dict(id='TRAIN:drill_field_entry',kind='open_field_access',gate_id=gate['id'],width_m=3,polyline_xz_m=points,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,3) for u,v in zip(points,points[1:])]))
 pack=dict(schema='riverstone.registered_training.source.v1',sources=data['sources'],source_space=space,source_space_sha256=a.sha(space),placements=placements,assets=assets,actual_doors=doors,internal_routes=routes,gate=gate,external_surface=surface,central_exercise_reservation=dict(id='TRAIN:central_drill_core',polygon_xz_m=CORE,area_m2=a.geom.polygon_area(CORE),physical_obstacles_allowed=False,purpose='Connected open formation and drill ground; no housing, trees or practice props'),native_support_samples=support,replacement_ledger=dict(source_building_ids=['B_TRAIN_0','B_TRAIN_1'],source_owned_path_ids=['B_TRAIN_0:DOOR','B_TRAIN_1:DOOR'],reason='Native garrison range and stable/store modules, with exact floor-18m door-to-road links replacing source paths aimed at the 24m uphill road terminus.'),status='source_candidate_pending_compilation_and_independent_access',runtime_ready=False,applied_to_scene=False)
 for key,asset in assets.items():
  if asset['kind']=='new_common':
   m=asset.pop('master');path=OUT/(key+'.master.json');write(path,m);asset.update(source_path=str(path.relative_to(c.ROOT)),source_sha256=a.file_sha(path),candidate_budget=candidate_budget(m))
  else:
   v=asset['cached'];assert a.file_sha(v['compiled_asset_ref'])==v['render_sha256'];assert a.file_sha(v['master_path'])==v['master_file_sha256']
 write(OUT/'source_pack.json',pack);print(json.dumps(dict(placements=len(placements),doors=len(doors),routes=len(routes),open_core_m2=a.geom.polygon_area(CORE),gate=gate['center_xz_m'],ramp_grade=surface['maximum_service_ramp_grade'],landing_grade=surface['maximum_inherited_public_landing_grade'],cut_fill=surface['maximum_cut_fill_m'])),flush=True);return pack
if __name__=='__main__':build()
