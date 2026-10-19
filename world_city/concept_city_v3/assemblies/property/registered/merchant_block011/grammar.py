"""Native merchant court grammar. Fixed modules and finite frames; no house scaling."""
import copy,json,math,hashlib
from pathlib import Path
from functools import lru_cache
from world_city.concept_city_v3.assemblies.property.registered import author as estate
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import transform,footprint,union_bounds
from world_city.runtime_city.checks import placement as g
HERE=Path(__file__).parent;CITY=HERE.parents[3];ROOT=CITY.parents[1]
PLAN=CITY/'registered_source/plan.json';ORDINARY=CITY/'assemblies/ordinary/registered/resolved_placements.json';CACHE=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json';PROPERTY=CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json'
FRAME_WIDTH=36;FRAME_DEPTH=42
VARIANTS={
 'palazzo_service': [('main_shop_residence','palace',[-3,7],'main'),('converted_goods_store','stable',[-5.5,-16],'rear'),('counting_and_small_goods','lodge',[8.5,-16],'rear')],
 'attached_shop_court': [('cloth_merchant_shop_residence','shop_low',[-9,10],'front'),('grain_merchant_shop_residence','shop_high',[6,10],'front'),('converted_goods_store','stable',[-5.5,-16],'rear'),('counting_and_small_goods','lodge',[8.5,-16],'rear')]
}
VARIANTS['attached_shop_wing_court']=VARIANTS['attached_shop_court'][:2]+[('rear_counting_workshop','lodge',[-13,-2],'front',math.pi/2)]+VARIANTS['attached_shop_court'][2:]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def xform(q,origin,yaw):return transform(q,origin,yaw)
def worldpoly(poly,frame):return [xform(q,frame['origin_xz_m'],frame['yaw_rad']) for q in poly]
def circles(q,width):
 r=width/2/math.cos(math.pi/32)
 return [[q[0]+r*math.cos(i*math.pi/16),q[1]+r*math.sin(i*math.pi/16)] for i in range(32)]

@lru_cache(None)
def catalog():
 prop=json.loads(PROPERTY.read_text())['asset_manifest'];city=json.loads(CACHE.read_text());out={}
 for role in ('palace','stable','lodge'):
  src=estate.catalog()[role];a=prop[src['asset_key']];out[role]=dict(asset_key=src['asset_key'],master_path=str(Path(a['master_path']).relative_to(ROOT)),master_sha256=a['master_file_sha256'],render_path=str(Path(a['compiled_asset_ref']).relative_to(ROOT)),render_sha256=a['render_sha256'],bounds=a['bounds'],metadata=src['metadata'],spec=src['spec']['params'])
 for role,key in [('shop_low','ordinary_r2_002218a4f7c83a'),('shop_high','ordinary_r2_70ff17eef270d8')]:
  a=city['assets'][key]['coarse'];out[role]=dict(asset_key=key,master_path=a['master_path'],master_sha256=a['master_sha256'],render_path=a['render_path'],render_sha256=a['render_sha256'],bounds=union_bounds(city['assets'][key]),metadata=a['author_metadata'],spec=city['asset_specs'][key])
 for role,a in out.items():
  for kind in ('master','render'):assert ref(ROOT/a[kind+'_path'])['sha256']==a[kind+'_sha256']
  render=json.loads((ROOT/a['render_path']).read_text());doors=[]
  for j,metadata in enumerate(a['metadata']['entrance'].get('all_positions') or [a['metadata']['entrance']['position']]):
   x,y,z=metadata;faces=[]
   for gi,group in enumerate(render['groups']):
    if group['material'] not in ('door','door_dark'):continue
    for qi,q in enumerate(group['quads']):
     lo=[min(v[i] for v in q) for i in range(3)];hi=[max(v[i] for v in q) for i in range(3)]
     if abs(hi[2]-lo[2])<1e-8 and lo[0]-1e-8<=x<=hi[0]+1e-8 and abs(lo[1]-y)<1e-8 and hi[1]>=y+1 and abs(lo[2]-z)<=.251:faces.append(dict(group_index=gi,quad_index=qi,vertices_local_m=q,z=lo[2]))
   assert faces,(role,metadata);front=max(f['z'] for f in faces);faces=[f for f in faces if abs(f['z']-front)<1e-8];doors.append(dict(index=j,continuous_metadata_point_m=metadata,actual_local_xyz_m=[x,y,front],sampling_delta_m=front-z,native_face_evidence=faces))
  a['actual_native_doors']=doors
 return out

def build_recipe(frame):
 """frame: id, variant, origin_xz_m, yaw_rad, floor_y_m; optional irregular ownership polygon.

 Returns source placements/routes within the proven 36x42 platform. A caller must
 validate source-domain containment, roads/water/fixed exclusions and terrain.
 """
 assert frame['variant'] in VARIANTS;pid=frame['id'];poly=worldpoly(rect(-18,-21,18,21),frame);out=dict(id=pid,variant=frame['variant'],origin_xz_m=frame['origin_xz_m'],yaw_rad=frame['yaw_rad'],floor_y_m=frame['floor_y_m'],polygon_xz_m=poly,gate_local_xz_m=[16,21],gate_width_m=3.5,placements=[],actual_doors=[],internal_routes=[],groups=[],assets={});local_obstacles=[]
 for module in VARIANTS[frame['variant']]:
  role,key,center,group=module[:4];localyaw=module[4] if len(module)>4 else 0;yaw=frame['yaw_rad']+localyaw
  a=catalog()[key];origin=xform(center,frame['origin_xz_m'],frame['yaw_rad']);floor=frame['floor_y_m'];py=floor-a['actual_native_doors'][0]['actual_local_xyz_m'][1];ident=pid+':'+role;body=a['metadata']['body_bounds'];outer=a['bounds'];outerlocal=footprint(outer,center,localyaw);local_obstacles.append(outerlocal)
  p=dict(id=ident,asset_key=a['asset_key'],role=role,assembly_group_id=pid+':'+group,source_function='merchant shop and residence' if 'residence' in role else 'converted broad-bay goods warehouse' if key=='stable' else 'counting room and small-goods store',position_m=[origin[0],py,origin[1]],yaw_rad=yaw,scale=[1,1,1],local_center_xz_m=center,local_yaw_rad=localyaw,actual_body_footprint_xz_m=footprint(body,origin,yaw),actual_outer_footprint_xz_m=footprint(outer,origin,yaw),pad_floor_y_m=floor,asset_origin_policy='Finished floor minus actual cached native door Y',roof_palette='clay_red' if key in ('palace','shop_high') else 'wood_brown' if key=='stable' else 'slate_gray');out['placements'].append(p);out['assets'][a['asset_key']]=a
  for e in a['actual_native_doors']:
   q=e['actual_local_xyz_m'];door=xform([q[0],q[2]],origin,yaw);liplocal=xform([q[0],outer['max'][2]],center,localyaw);lip=xform(liplocal,frame['origin_xz_m'],frame['yaw_rad']);out['actual_doors'].append(dict(id=ident+':DOOR:'+str(e['index']),owner_id=ident,actual_door_xyz_m=[door[0],floor,door[1]],door_local_m=q,continuous_metadata_point_m=e['continuous_metadata_point_m'],native_sampling_delta_m=e['sampling_delta_m'],actual_cached_threshold_evidence=e['native_face_evidence'],threshold_lip_xz_m=lip,threshold_lip_property_local_xz_m=liplocal,outward_property_local_xz_m=[math.sin(localyaw),math.cos(localyaw)],render_sha256=a['render_sha256'],physical_opening_only=True,population_or_household_inference=False,route_width_m=3 if key=='stable' else 1.8))
 for group in sorted(set(p['assembly_group_id'] for p in out['placements'])):out['groups'].append(dict(id=group,member_ids=[p['id'] for p in out['placements'] if p['assembly_group_id']==group],common_union_required=sum(p['assembly_group_id']==group for p in out['placements'])>1))
 for d in out['actual_doors']:
  ins=next(p for p in out['placements'] if p['id']==d['owner_id']);start=d['threshold_lip_property_local_xz_m'];width=d['route_width_m'];end=[16,18.5]
  if 'residence' in ins['role']:
   rowz=start[1]+1.05;line=[start,[start[0],rowz],[16,rowz],[16,21]]
  else:
   approach=[start[k]+d['outward_property_local_xz_m'][k]*(width/2+.3) for k in (0,1)];line=estate.route_in_parcel(approach,end,rect(-18,-21,18,21),local_obstacles,width)
   if line is None:raise ValueError('No full-width service path: '+d['id'])
   line=[start]+line;line.append([16,21])
  world=[xform(q,frame['origin_xz_m'],frame['yaw_rad']) for q in line];polys=[g.road_ribbon(a,b,width) for a,b in zip(world,world[1:])];joins=[circles(q,width) for q in world[1:-1]];out['internal_routes'].append(dict(id=d['id']+':GATE_LINK',property_id=pid,actual_door_id=d['id'],width_m=width,polyline_xz_m=world,ribbon_polygons_xz_m=polys,round_join_polygons_xz_m=joins,finished_floor_y_m=frame['floor_y_m'],route_status='finite source candidate; native floor and terrain binding pending'))
 court=rect(-15,-11,13,-5 if frame['variant']=='palazzo_service' else 0) if frame['variant']!='attached_shop_wing_court' else [[-15,-11],[13,-11],[13,0],[-8,0],[-8,-8.5],[-15,-8.5]];out['court']=dict(id=pid+':SERVICE_COURT',polygon_xz_m=worldpoly(court,frame),area_m2=g.polygon_area(court),role='goods handling, shared delivery and turning court',floor_y_m=frame['floor_y_m']);out['gate_position_xz_m']=xform([16,21],frame['origin_xz_m'],frame['yaw_rad']);return out
