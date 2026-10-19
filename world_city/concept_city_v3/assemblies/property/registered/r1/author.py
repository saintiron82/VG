"""Reversible gate/ramp revision; frozen r0 recipes, modules and placements stay intact."""
from __future__ import annotations
import copy,json,math,time
from pathlib import Path
from .. import author as a
from ..audit import candidate_budget
from . import access_search as search
from world_city.concept_city_v3.registered_topography import author as terrain
HERE=Path(__file__).resolve().parent;OUT=HERE/'generated'
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def route_recipe(old,c):
 r=copy.deepcopy(old);pid=r['id'];floor=r['plot']['pad_floor_y_m'];poly=r['plot']['polygon_xz_m'];r['garden_pose_revision_ledger']=[]
 if pid=='E1':
  for p in r['placements']:
   if p['role'].startswith('garden_bed_'):
    dx=1.1 if p['role'].startswith('garden_bed_0') else .2;before=copy.deepcopy(p);p['position_m'][0]+=dx;p['footprint_xz_m']=[[q[0]+dx,q[1]] for q in p['footprint_xz_m']];p['ground_anchor']['support_points_xz_m']=[[q[0]+dx,q[1]] for q in p['ground_anchor']['support_points_xz_m']];r['garden_pose_revision_ledger'].append(dict(id=p['id'],old_position_m=before['position_m'],new_position_m=p['position_m'],reason='open 3.6m stable-front service corridor while retaining coherent two-column garden and >=2.1m central walk'))
  for p in r['placements']:
   if p['role']=='orchard_tree_0':
    before=copy.deepcopy(p);p['position_m'][2]-=3;p['footprint_xz_m']=[[q[0],q[1]-3] for q in p['footprint_xz_m']];p['ground_anchor']['support_points_xz_m']=[[q[0],q[1]-3] for q in p['ground_anchor']['support_points_xz_m']];r['garden_pose_revision_ledger'].append(dict(id=p['id'],old_position_m=before['position_m'],new_position_m=p['position_m'],reason='open 4m crown-clear service passage behind main hall; native tree unchanged'))
 solids=[p['footprint_xz_m'] for p in r['placements']]
 g=copy.deepcopy(c['gate']);g.update(id=pid+':registered_r1:service_gate',role='pedestrian_and_handcart_service',finished_threshold_y_m=floor,external_road_id=c['road_id'],external_grade_status='finite_ramp_pending_independent_audit',external_source_link_xz_m=c['road_connection_xz_m'])
 r['gates']=[g];routes=[]
 houses=sorted([p for p in r['placements'] if p.get('entrances')],key=lambda p:p['role']!='stable')
 for h in houses:
  for e in h['entrances']:
   width=3. if pid=='E1' and h['role']=='stable' else 1.8;threshold=e['envelope_threshold_xz_m'];start=a.add(threshold,e['outward_xz'],width/2+.15)
   middle=a.route_in_parcel(start,g['inside_point_xz_m'],poly,solids,width)
   if not middle:return None,dict(check='interior_route_unavailable',door_id=e['id'],width_m=width)
   points=[threshold]+middle+[g['center_xz_m']]
   routes.append(dict(id=e['id']+':r1_route',owner_id=h['id'],door_id=e['id'],gate_id=g['id'],width_m=width,polyline_xz_m=points,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,width) for u,v in zip(points,points[1:]) if math.dist(u,v)>1e-5],actual_door_bridge_xz_m=[[e['door_xyz_m'][0],e['door_xyz_m'][2]],threshold],full_polyline_xyz_m=[e['door_xyz_m']]+[[p[0],floor,p[1]] for p in points],surface_owner=pid+':registered_r1:infrastructure'))
 oldwalk=next(p for p in old['entrance_routes'] if p.get('kind')=='garden_walk');start=oldwalk['polyline_xz_m'][0];middle=a.route_in_parcel(start,g['inside_point_xz_m'],poly,solids,1.8)
 if not middle:return None,dict(check='garden_route_unavailable')
 points=middle+[g['center_xz_m']];routes.append(dict(id=pid+':registered_r1:garden_walk',owner_id=pid,kind='garden_walk',gate_id=g['id'],width_m=1.8,polyline_xz_m=points,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,1.8) for u,v in zip(points,points[1:]) if math.dist(u,v)>1e-5],full_polyline_xyz_m=[[p[0],floor,p[1]] for p in points],surface_owner=pid+':registered_r1:infrastructure'))
 court_center=a.LAYOUTS[pid]['court'][0];court_candidates=[court_center]+[a.centre(q['polygon_xz_m']) for q in sorted(r['ground_regions'],key=lambda q:-q['area_m2']) if 'court' in q['land_use']]
 service=None
 for cp in court_candidates:
  if a.contained(a.rect(cp,3,3),poly) and not any(a.overlap(a.rect(cp,3,3),p) for p in solids):
   service=a.route_in_parcel(cp,g['inside_point_xz_m'],poly,solids,3.)
   if service:break
 if not service:return None,dict(check='arrival_court_3m_route_unavailable')
 points=service+[g['center_xz_m']];routes.append(dict(id=pid+':registered_r1:service_court_access',owner_id=pid,kind='service_court_access',gate_id=g['id'],width_m=3.,polyline_xz_m=points,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,3.) for u,v in zip(points,points[1:]) if math.dist(u,v)>1e-5],full_polyline_xyz_m=[[p[0],floor,p[1]] for p in points],surface_owner=pid+':registered_r1:infrastructure',vehicle_scope='3m arrival to service court; 1.8m pedestrian and handcart branches to actual doors'))
 r['entrance_routes']=routes;r['surface_ownership']['owner_id']=pid+':registered_r1:infrastructure';r['source_errors']=[];r['external_access_resolved']=False;r['checks']=a.validate_recipe(r);r['infrastructure_spec']=a.infrastructure_spec(r);r['revision']='r1_access';r['supersedes_r0_recipe_sha256']=a.file_sha(a.HERE/'generated'/(pid+'.recipe.json'));r['gate_repair']=c
 return (r,None) if r['checks']['valid'] else (None,r['checks'])

def dot(u,v):return sum(x*y for x,y in zip(u,v))
def sub(u,v):return [x-y for x,y in zip(u,v)]
def cross(u,v):return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
def norm(u):d=math.sqrt(dot(u,u));return [x/d for x in u]
def triangle_grade(tri):
 n=cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]));return math.hypot(n[0],n[2])/abs(n[1])
def make_surface_record(r,c):
 floor=c['finished_floor_y_m'];start,end=c['external_centerline_xz_m'][1:];length=math.dist(start,end);u=a.unit(start,end);v=[-u[1],u[0]];triangles=[]
 def add_quad(kind,points):
  for ids in ((0,1,2),(0,2,3)):
   tri=[points[i] for i in ids];triangles.append(dict(kind=kind,vertices_xyz_m=tri,source_grade=triangle_grade(tri)))
 for p in a.triangulate(c['gate_landing_polygon_xz_m']):triangles.append(dict(kind='level_gate_turning_pocket',vertices_xyz_m=[[x,floor,z] for x,z in p],source_grade=0.))
 # Narrow finite surface strips exactly share corner and terminal samples. The
 # existing common extrusion primitive authors each triangular sloped skin.
 ns=math.ceil(length/2);sides=[-1.5,-.5,.5,1.5]
 def p_at(t,s):
  p=a.add(a.add(start,u,t*length),v,s);ep=a.add(end,v,s);y=floor+t*(terrain.dry_height_at(*ep)-floor);return [p[0],y,p[1]]
 for j in range(ns):
  for s0,s1 in zip(sides,sides[1:]):add_quad('service_ramp',[p_at(j/ns,s0),p_at((j+1)/ns,s0),p_at((j+1)/ns,s1),p_at(j/ns,s1)])
 for s0,s1 in zip(sides,sides[1:]):
  points=[a.add(a.add(end,u,t),v,s) for t,s in ((0,s0),(.5,s0),(.5,s1),(0,s1))];add_quad('public_lane_threshold_landing',[[p[0],terrain.dry_height_at(*p),p[1]] for p in points])
 samples=copy.deepcopy(c['support_samples_xyz_existing_delta'])
 for t in triangles:
  vs=t['vertices_xyz_m']
  for x,y,z in vs+[[sum(p[i] for p in vs)/3 for i in range(3)]]:
   existing=terrain.land_height_at(x,z);samples.append([x,y,z,existing,y-existing])
 return dict(id=r['id']+':registered_r1:external_access',property_id=r['id'],surface_owner=r['id']+':registered_r1:infrastructure',finished_gate_floor_y_m=floor,polygon_regions_xz_m=[c[k] for k in ('gate_landing_polygon_xz_m','owned_ramp_polygon_xz_m','road_landing_polygon_xz_m')],triangulated_top_surface=triangles,height_evaluator='barycentric interpolation within declared triangle; shared samples at every seam',public_lane_endpoint=dict(road_id=c['road_id'],road_segment_id=c['road_segment_id'],seam_xz_m=[a.add(end,v,s) for s in sides],seam_xyz_m=[p_at(1,s) for s in sides],shared_height_api='registered_topography.author.dry_height_at',same_datum_landing_polygon_xz_m=c['road_landing_polygon_xz_m']),source_clear_width_m=3,source_gate_width_m=5,level_turning_pocket_width_m=5,maximum_triangle_grade=max(t['source_grade'] for t in triangles),maximum_service_ramp_grade=max(t['source_grade'] for t in triangles if t['kind']=='service_ramp'),maximum_inherited_public_landing_grade=max(t['source_grade'] for t in triangles if t['kind']=='public_lane_threshold_landing'),maximum_cut_fill_m=max(abs(p[4]) for p in samples),support_samples_xyz_existing_delta=samples,support_owner='registered_topography.explicit_later_overlay',terrain_top_face_exclusion_required=True,skin_thickness_m=.5,ownership_policy='exclusive finite source domains plus actual compiled skin footprint; preserve all surrounding public road and ground',status='proposed_pending_independent_access_and_support_review',vehicle_scope='pedestrians and handcarts; horse-wagon swept turning path not claimed')

def append_surface(master,record,origin,floor):
 ops=master['components'][0]['operations'];provenance=[]
 for j,t in enumerate(record['triangulated_top_surface']):
  ps=t['vertices_xyz_m'];p0=ps[0];e1=norm(sub(ps[1],p0));normal=norm(cross(e1,sub(ps[2],p0)))
  if normal[1]<0:normal=[-x for x in normal]
  e2=cross(normal,e1);basis=[[e1[i],e2[i],normal[i]] for i in range(3)];poly=[[dot(sub(p,p0),e1),dot(sub(p,p0),e2)] for p in ps]
  op=dict(id='r1_access_skin_'+str(j),part='solid',action='paint',material='stone_dark',shape=dict(kind='extrusion',polygon=poly,z_min=-.5,z_max=0),transform=dict(basis=basis,translation=[p0[0]-origin[0],p0[1]-floor,p0[2]-origin[1]]));ops.append(op);provenance.append(dict(operation_id=op['id'],source_triangle=t))
 master['id']='registered_property_r1_'+a.sha(dict(master=master,access=record))[:16];master['revision']=2;master['metadata'].update(r1_source_surface_provenance=provenance,external_access_surface_id=record['id'],one_solid_floor_boundary_access=True,external_access_audit_status='pending')
 return master

def run():
 report=json.loads((OUT/'search_report.json').read_text());assert report['status']=='complete_bounded_search_not_activated';assert report['source_plan_sha256']==a.file_sha(a.CITY/'registered_source/plan.json')
 results=[];failures=[]
 for row in report['records']:
  pid=row['property_id'];old=json.loads((a.HERE/'generated'/(pid+'.recipe.json')).read_text());r=None
  for index,c in enumerate(row['candidates']):
   if any(a.overlap(p,q) for prior in results for p in prior['external_surface']['polygon_regions_xz_m'] for q in [c[k] for k in ('gate_landing_polygon_xz_m','owned_ramp_polygon_xz_m','road_landing_polygon_xz_m')]):
    failures.append(dict(property_id=pid,candidate=index,error='other_selected_estate_access_domain'));continue
   started=time.monotonic();r,error=route_recipe(old,c);print(json.dumps(dict(property_id=pid,candidate=index,route_result='pass' if r else error,elapsed_s=round(time.monotonic()-started,2))),flush=True)
   if r:
    surface=make_surface_record(r,c)
    if surface['maximum_service_ramp_grade']>.10001 or surface['maximum_inherited_public_landing_grade']>.12001:failures.append(dict(property_id=pid,candidate=index,error='surface_triangle_grade',grade=surface['maximum_triangle_grade']));r=None;continue
    r['external_surface']=surface;r['infrastructure_spec']['external_surface']=surface;master=append_surface(a.make_infrastructure_master(r['infrastructure_spec']),surface,r['origin_xz_m'],r['plot']['pad_floor_y_m']);budget=candidate_budget(master)
    if not budget['within_candidate_cap']:raise ValueError('Exceeded fixed common candidate cap')
    write(OUT/(pid+'.recipe.json'),r);write(OUT/(pid+'.infrastructure.master.json'),master);results.append(dict(property_id=pid,selected_candidate=index,gate=r['gates'][0],external_surface=surface,external_candidate=c,recipe_file=pid+'.recipe.json',recipe_sha256=a.file_sha(OUT/(pid+'.recipe.json')),master_file=pid+'.infrastructure.master.json',master_sha256=a.file_sha(OUT/(pid+'.infrastructure.master.json')),master_id=master['id'],candidate_budget=budget,actual_door_count=sum('door_id' in x for x in r['entrance_routes']),replacement_ledger=r['replacement_proposal'],supersede_r0_infrastructure_id=pid+':registered:infrastructure',supersede_r0_route_ids=[x['id'] for x in old['entrance_routes']]));break
   failures.append(dict(property_id=pid,candidate=index,error=error))
  if r is None:raise ValueError('No complete internal/external chain found for '+pid)
  write(OUT/'access_overlay.json',dict(schema='riverstone.registered_property.access_overlay.v1',registered_source_sha256=report['source_plan_sha256'],r0_seal_sha256=a.file_sha(a.HERE/'r0_seal.json'),r0_resolved_pack_sha256=a.file_sha(a.HERE/'resolved_placements.json'),search_report_sha256=a.file_sha(OUT/'search_report.json'),terrain_author_sha256=a.file_sha(Path(terrain.__file__)),records=results,rejected_internal_candidates=failures,status='partial' if len(results)<7 else 'source_complete_pending_independent_audit',runtime_ready=False,applied_to_scene=False,building_poses_unchanged=True,compiled=False))
 return results
if __name__=='__main__':run()
