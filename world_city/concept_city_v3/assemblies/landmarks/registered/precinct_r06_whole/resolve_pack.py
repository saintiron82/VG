"""Resolve fixed native assemblies; exact native support and internal clearances."""
from author_native import *
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex

def horizontal(mesh,y,up):
 out=[]
 for g in mesh['groups']:
  for q in g['quads']:
   if max(v[1]for v in q)-min(v[1]for v in q)>1e-7 or abs(q[0][1]-y)>1e-7:continue
   n=(q[1][2]-q[0][2])*(q[2][0]-q[0][0])-(q[1][0]-q[0][0])*(q[2][2]-q[0][2])
   if (n>0)==up:out.append([[v[0],v[2]]for v in q])
 return out

def main():
 plan=load(HERE/'grounds_plan.json');scene=terrain.load_scene();compiled=load(HERE/'compiled_assets.json');assets={a['role']:a for a in compiled['assets']};native={};positions=[];bearings=[];contacts=[];units=[];paths=[]
 for role,key in [('tree','c3_property_fabric_r3_05a88415aae614ab'),('bed','c3_property_fabric_r3_b8fc7a975a10ec9f'),('trough','registered_training_water_trough'),('rack','registered_training_practice_rack'),('target','registered_training_practice_target')]:
  a=scene['common_assets'][key];assets[role]={'role':role,'id':key,'source':{'path':a['master_path'],'sha256':a['master_sha256']},'cache':{'path':a['render_path'],'sha256':a['render_sha256']},'pitch_m':load(ROOT/a['render_path'])['pitch'],'reused_unchanged_native':True}
 for role,a in assets.items():
  assert sha(ROOT/a['source']['path'])==a['source']['sha256']and sha(ROOT/a['cache']['path'])==a['cache']['sha256'];mesh=load(ROOT/a['cache']['path']);full,_=roof_rectangles(mesh,{g['material']for g in mesh['groups']});native[role]={'mesh':mesh,'foot':horizontal(mesh,mesh['bounds']['min'][1],False),'body':slab_rectangles(mesh,.01,2.2),'full':full,'bottom':mesh['bounds']['min'][1]}
 def add(u,role,x,z,serial,yaw=0):
  a=assets[role];n=native[role];p={'id':u['id']+':'+role+':'+str(serial),'holding_id':u['id'],'owner_id':u['owner_id'],'asset_key':a['id'],'source':a['source'],'cache':a['cache'],'position_m':[x,u['floor_y_m'],z],'yaw_rad':yaw,'scale':[1,1,1],'function':role,'actual_cached_bounds_local_m':n['mesh']['bounds']};positions.append(p)
  for i,poly in enumerate(n['foot']):bearings.append({'id':p['id']+':bearing:'+str(i),'placement_id':p['id'],'holding_id':u['id'],'polygon_xz_m':b.xform(poly,p),'bottom_y_m':u['floor_y_m']+n['bottom'],'finished_ground_y_m':u['floor_y_m'],'kind':'actual_native_underside'})
  p['body_parts_xz_m']=[b.xform(poly,p)for poly in n['body']];p['native_projection_parts_xz_m']=[b.xform(poly,p)for poly in n['full']];return p
 water=load(HERE/'water_service_reservations.json')['regions'];excluded=[]
 for u in plan['units']:
  conflict=[r['id']for r in water if geo.intersection_area(u['polygon_xz_m'],r['polygon_xz_m'])>1e-8]
  if conflict:excluded.append({'id':u['id'],'reason':'Parent-owned water draw reservation','water_ids':conflict});continue
  u=copy.deepcopy(u);x,y,z=u['position_m'];w,d=u['dimensions_m'];add(u,f'boundary_{w}x{d}',x,z,0);props=[]
  def prop(role,dx,dz,yaw=0):props.append(add(u,role,x+dx,z+dz,len(props),yaw))
  if u['function']=='orchard':
   for dx in(-4.25,4.25):
    for dz in(-4.25,4.25):prop('tree',dx,dz)
  elif u['function']in('kitchen_beds','medicinal_nursery'):
   for sx in(-1,1):
    for sz in(-1,1):
     qx0,qx1=2.5,w/2-1; qz0,qz1=2.5,d/2-1
     if qx1-qx0>=6 and qz1-qz0>=3:role='bed';bw,bd=6,3
     elif qx1-qx0>=3 and qz1-qz0>=6:role='bed';bw,bd=3,6
     else:role='compact_bed';bw,bd=3,2
     if qx1-qx0<bw or qz1-qz0<bd:continue
     for ax in np.arange(qx0+bw/2,qx1-bw/2+.01,bw+1):
      for az in np.arange(qz0+bd/2,qz1-bd/2+.01,bd+1):prop(role,float(sx*ax),float(sz*az),math.pi/2 if role=='bed'and bw==3 else 0)
  else:
   # Service quadrants retain a continuous4m central cart/walking cross.
   qx=(w/2+2)/2;qz=(d/2+2)/2
   if w>=24 and d>=24:prop('shelter_8x6',-qx,-qz)
   else:prop('shelter_4x3',-qx,-qz)
   if u['function']=='stable_service':
    prop('trough',qx,-qz);prop('rack',-qx,qz);prop('target'if u['owner_id']=='SITE_TRAIN'else'fuel_stack',qx,qz)
   elif u['function']=='fuel_workyard':
    prop('fuel_stack',qx,-qz);prop('fuel_stack',qx,qz);prop('cargo_crate',-qx,qz)
   else:prop('park_bench',qx,-qz);prop('park_bench',qx,qz);prop('compact_bed',-qx,qz)
  pp=[r for r in positions if r['holding_id']==u['id']];half=1 if u['function']=='orchard'else 2;pathpolys=[b.rect(x-half,z-d/2,x+half,z+d/2),b.rect(x-w/2,z-half,x+w/2,z+half)];collisions=[];outside=[]
  for placement in pp:
   for q in placement['body_parts_xz_m']:
    for route in pathpolys:
     ar=geo.intersection_area(q,route)
     if ar>1e-8:collisions.append({'placement_id':placement['id'],'area_m2':ar})
   for q in placement['native_projection_parts_xz_m']:
    if abs(geo.intersection_area(q,u['polygon_xz_m'])-geo.polygon_area(q))>1e-7:outside.append(placement['id'])
  # Exact occupied native polygons, not source envelopes, decide internal contact.
  pair=[]
  for i,a in enumerate(pp):
   for c in pp[i+1:]:
    for qa in a['body_parts_xz_m']:
     for qc in c['body_parts_xz_m']:
      ar=geo.intersection_area(qa,qc)
      if ar>1e-8:pair.append({'a':a['id'],'b':c['id'],'area_m2':ar})
  contacts.append({'holding_id':u['id'],'props':len(props),'native_body_path_contacts':collisions,'outside_native_projection_ids':sorted(set(outside)),'native_body_interplacement_contacts':pair,'pass':not collisions and not outside and not pair});assert contacts[-1]['pass'],contacts[-1]
  paths.append({'id':u['id']+':cross_paths','holding_id':u['id'],'width_m':half*2,'polygon_parts_xz_m':pathpolys,'floor_y_m':y,'native_body_clear':True,'four_static_open_gates_clear_width_m':4});u['native_placement_ids']=[p['id']for p in pp];u['facility_counts']=dict(collections.Counter(p['function']for p in pp));u['internal_routes_id']=paths[-1]['id'];u['status']='NATIVE_RESOLVED_FINITE_GROUNDS_PUBLIC_CONTINUATION_PENDING';units.append(u)
 ix=terrain.TriangleIndex(scene,[u['polygon_xz_m']for u in units]);support=[]
 for f in bearings:
  test=terrain.audit_polygon(ix,f['polygon_xz_m'],f['finished_ground_y_m']);support.append({'id':f['id'],'missing_m2':test['missing_area_m2'],'max_floor_delta_m':test['max_floor_delta_m'],'passes':test['passes_existing_surface']});assert test['passes_existing_surface'],support[-1]
 for p in positions:p.pop('body_parts_xz_m');p.pop('native_projection_parts_xz_m')
 write('native_geometry_tests.json',{'internal_route_and_contacts':contacts,'bearing_tests':support,'summary':{'holding_count':len(units),'placements':len(positions),'native_bearing_pieces':len(bearings),'all_pass':all(x['pass']for x in contacts)and all(x['passes']for x in support)},'actual_scene_viewed':False,'runtime_capsule_tested':False})
 write('resolved_placements.json',{'schema':'riverstone.precinct.r06.whole_ground_native.v1','status':'COMPILED_RESOLVED_NATIVE_GROUNDS_NOT_ACTIVATED','sources':{'scene':ref(terrain.SCENE_PATH),'plan':ref(HERE/'grounds_plan.json'),'native_preflight':ref(HERE/'native_preflight.json'),'native_tests':ref(HERE/'native_geometry_tests.json')},'assets':list(assets.values()),'placements':positions,'actual_bearing_footprints':bearings,'owned_floors':[],'internal_routes':paths,'holdings':units,'excluded_holdings':excluded,'replacement_ledger':{'existing_native_placements_removed':[],'terrain_policy':'Finite existing source-index cuts at actual native soil-bearing sections; surface planes and banks unchanged.'},'summary':{'holdings':len(units),'meaningful_domain_area_m2':sum(u['area_m2']for u in units),'placements':len(positions),'asset_types':len(assets),'native_bearing_pieces':len(bearings)},'activation_requirements':['Finite terrain patch applied atomically.','Exterior route target ownership and full network continuation resolved for every activated holding.','Actual scene art and player/NPC route checks.'],'compiled':True,'resolved':True,'placed_in_actual_scene':False,'activation':False});print(load(HERE/'resolved_placements.json')['summary'])
if __name__=='__main__':main()
