"""Small native-width merchant burgage families with explicit shared passages."""
import copy,json,math,hashlib
from pathlib import Path
from functools import lru_cache
from ..merchant_block011 import grammar as prior
from ..merchant_block011.coverage import roof_rects
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import footprint
HERE=Path(__file__).parent;ROOT=prior.ROOT;CITY=prior.CITY;PLAN=prior.PLAN;ORDINARY=prior.ORDINARY
g=prior.g;estate=prior.estate;ref=prior.ref;write=prior.write;rect=prior.rect;xform=prior.xform
KEYS={'shop8':'ordinary_r2_3372ae06ebd39f','hip12early':'ordinary_r2_7efb0dba8874db','hip12late':'ordinary_r2_8c6ac6d806c93b','deep10low':'ordinary_r2_71099b13efaf70','deep10high':'ordinary_r2_17e539135272c3','deep12early':'ordinary_r2_b91478d025a6a2'}
FAMILIES={
 'compact_rebuilt':dict(width=24,depth=32,roof='clay_red',modules=[('shop','shop8',[-7.5,8.5],'front',0),('merchant_residence','hip12late',[1.5,8.5],'front',0),('small_goods_store','stable',[-2.5,-11.5],'rear',0)],court=rect(-11,-7,7,3.5)),
 'compact_old':dict(width=24,depth=32,roof='wood_brown',modules=[('shop','shop8',[-7.5,8.5],'front',0),('older_merchant_house','hip12early',[1.5,8.5],'front',0),('small_goods_store','stable',[-2.5,-11.5],'rear',0)],court=rect(-11,-7,7,3.5)),
 'deep_workyard':dict(width=30,depth=40,roof='clay_red',modules=[('shop','deep10low',[-9.5,10.5],'front',0),('merchant_residence','deep10high',[-.5,10.5],'front',0),('rear_counting_wing','lodge',[-10.5,-1.5],'front',math.pi/2),('small_goods_store','stable',[-5.5,-15.5],'rear',0),('service_lodge','lodge',[8.5,-15.5],'rear',0)],court=[[-14,-11],[10,-11],[10,4],[-6,4],[-6,-8],[-14,-8]]),
 'wide_early_court':dict(width=30,depth=36,roof='slate_gray',modules=[('older_shop','hip12early',[-8.5,10.5],'front',0),('merchant_residence','hip12late',[2.5,10.5],'front',0),('small_goods_store','stable',[-5.5,-13.5],'rear',0),('service_lodge','lodge',[8.5,-13.5],'rear',0)],court=rect(-14,-9,11,5.5))}
FAMILIES['deep_older_workyard']=copy.deepcopy(FAMILIES['deep_workyard'])
FAMILIES['deep_older_workyard'].update(roof='wood_brown',modules=[('older_merchant_house','deep12early',[-8.5,10.5],'front',0),('shop','deep10low',[1.5,10.5],'front',0)]+FAMILIES['deep_workyard']['modules'][2:])

@lru_cache(None)
def catalog():
 out=copy.deepcopy(prior.catalog());cache=json.loads(prior.CACHE.read_text())
 for role,key in KEYS.items():
  a=cache['assets'][key]['coarse'];out[role]=dict(asset_key=key,master_path=a['master_path'],master_sha256=a['master_sha256'],render_path=a['render_path'],render_sha256=a['render_sha256'],bounds=a['bounds'],metadata=a['author_metadata'],spec=cache['asset_specs'][key])
 for role,a in out.items():
  for kind in ('master','render'):assert ref(ROOT/a[kind+'_path'])['sha256']==a[kind+'_sha256']
  r=json.loads((ROOT/a['render_path']).read_text());a['native_foundation_local_xz_m']=slab_rectangles(r,.49,.499);a['native_walking_local_xz_m']=slab_rectangles(r,.55,2.35);a['native_roof_local_xz_m']=roof_rects(r)
  if 'actual_native_doors' in a:continue
  ds=[]
  for j,q in enumerate(a['metadata']['entrance'].get('all_positions') or [a['metadata']['entrance']['position']]):
   faces=[]
   for gi,group in enumerate(r['groups']):
    if group['material'] not in ('door','door_dark'):continue
    for qi,quad in enumerate(group['quads']):
     lo=[min(v[k] for v in quad) for k in range(3)];hi=[max(v[k] for v in quad) for k in range(3)]
     if abs(hi[2]-lo[2])<1e-8 and lo[0]-1e-8<=q[0]<=hi[0]+1e-8 and abs(lo[1]-q[1])<1e-8 and abs(lo[2]-q[2])<=.251 and hi[1]>=q[1]+1:faces.append(dict(group_index=gi,quad_index=qi,vertices_local_m=quad,z=lo[2],width_m=hi[0]-lo[0]))
   assert faces,(role,q);z=max(f['z'] for f in faces);ds.append(dict(index=j,continuous_metadata_point_m=q,actual_local_xyz_m=[q[0],q[1],z],sampling_delta_m=z-q[2],native_face_evidence=[f for f in faces if abs(f['z']-z)<1e-8]))
  a['actual_native_doors']=ds
 return out

def transform_polys(polys,origin,yaw):return [[xform(q,origin,yaw) for q in poly] for poly in polys]

@lru_cache(None)
def local_recipe(family):
 f=FAMILIES[family];W,D=f['width'],f['depth'];parcel=rect(-W/2,-D/2,W/2,D/2);gate=[W/2-2,D/2];placements=[];doors=[];obstacles=[];groups={}
 for role,key,center,group,yaw in f['modules']:
  a=catalog()[key];p=dict(id=role,asset_key=a['asset_key'],role=role,local_center_xz_m=center,local_yaw_rad=yaw,group=group,roof_palette='wood_brown' if group=='rear' else f['roof'],construction_era=a['spec'].get('construction_era','early'),native_body_polygons_xz_m=[footprint(a['metadata']['body_bounds'],center,yaw)],native_foundation_polygons_xz_m=transform_polys(a['native_foundation_local_xz_m'],center,yaw),native_walking_polygons_xz_m=transform_polys(a['native_walking_local_xz_m'],center,yaw),native_roof_polygons_xz_m=transform_polys(a['native_roof_local_xz_m'],center,yaw));placements.append(p);obstacles+=p['native_walking_polygons_xz_m'];groups.setdefault(group,[]).append(role)
  for q in p['native_roof_polygons_xz_m']+p['native_foundation_polygons_xz_m']:assert estate.contained(q,parcel),(family,role,'native mask outside parcel')
  for e in a['actual_native_doors']:
   q=e['actual_local_xyz_m'];door=xform([q[0],q[2]],center,yaw);lip=xform([q[0],a['bounds']['max'][2]],center,yaw);doors.append(dict(id=role+':DOOR:'+str(e['index']),owner_id=role,actual_local_xz_m=door,threshold_lip_local_xz_m=lip,door_local_xyz_m=q,source_native_evidence=e['native_face_evidence'],native_sampling_delta_m=e['sampling_delta_m'],width_m=3 if key=='stable' else 1.8,outward=[math.sin(yaw),math.cos(yaw)]))
 routes=[]
 for d in doors:
  width=d['width_m'];start=d['threshold_lip_local_xz_m'];approach=[start[k]+d['outward'][k]*(width/2+.2) for k in (0,1)];target=[gate[0],gate[1]-2]
  line=estate.route_in_parcel(approach,target,parcel,obstacles,width)
  if line is None:raise ValueError(('no_native_clearance_route',family,d['id'],approach))
  line=[start]+line+[gate];ribbons=[g.road_ribbon(a,b,width) for a,b in zip(line,line[1:]) if math.dist(a,b)>1e-7];joins=[prior.circles(q,width) for q in line[1:-1]]
  for poly in ribbons+joins:
   assert estate.contained(poly,parcel),(family,d['id'],'parcel')
   assert not any(estate.overlap(poly,q) for q in obstacles),(family,d['id'],'native walking')
  routes.append(dict(id=d['id']+':GATE_LINK',actual_door_id=d['id'],width_m=width,polyline_xz_m=line,ribbon_polygons_xz_m=ribbons,round_join_polygons_xz_m=joins))
 for tri in estate.triangulate(f['court']):assert not any(estate.overlap(tri,q) for q in obstacles),(family,'court native overlap')
 return dict(family=family,width_m=W,depth_m=D,polygon_xz_m=parcel,gate_local_xz_m=gate,gate_width_m=3.5,placements=placements,actual_doors=doors,internal_routes=routes,groups=groups,court_polygon_xz_m=f['court'])

def build_recipe(frame):
 local=copy.deepcopy(local_recipe(frame['family']));pid=frame['id'];origin=frame['origin_xz_m'];yaw=frame['yaw_rad'];floor=frame['floor_y_m'];out=dict(id=pid,family=frame['family'],width_m=local['width_m'],depth_m=local['depth_m'],origin_xz_m=origin,yaw_rad=yaw,floor_y_m=floor,polygon_xz_m=transform_polys([local['polygon_xz_m']],origin,yaw)[0],gate_position_xz_m=xform(local['gate_local_xz_m'],origin,yaw),gate_local_xz_m=local['gate_local_xz_m'],gate_width_m=3.5,placements=[],actual_doors=[],internal_routes=[],groups=[],assets={})
 for p in local['placements']:
  q=copy.deepcopy(p);q['id']=pid+':'+p['id'];q['assembly_group_id']=pid+':'+p['group'];center=xform(p['local_center_xz_m'],origin,yaw);q.update(position_m=[center[0],floor-.5,center[1]],yaw_rad=yaw+p['local_yaw_rad'],scale=[1,1,1],pad_floor_y_m=floor)
  for key in ('native_body_polygons_xz_m','native_foundation_polygons_xz_m','native_walking_polygons_xz_m','native_roof_polygons_xz_m'):q[key]=transform_polys(p[key],origin,yaw)
  out['placements'].append(q);out['assets'][q['asset_key']]=next(a for a in catalog().values() if a['asset_key']==q['asset_key'])
 for d in local['actual_doors']:
  q=copy.deepcopy(d);point=xform(d['actual_local_xz_m'],origin,yaw);q.update(id=pid+':'+d['id'],owner_id=pid+':'+d['owner_id'],actual_door_xyz_m=[point[0],floor,point[1]],threshold_lip_xz_m=xform(d['threshold_lip_local_xz_m'],origin,yaw));out['actual_doors'].append(q)
 for r in local['internal_routes']:
  q=copy.deepcopy(r);q.update(id=pid+':'+r['id'],actual_door_id=pid+':'+r['actual_door_id'],property_id=pid,finished_floor_y_m=floor,polyline_xz_m=[xform(v,origin,yaw) for v in r['polyline_xz_m']])
  for k in ('ribbon_polygons_xz_m','round_join_polygons_xz_m'):q[k]=transform_polys(r[k],origin,yaw)
  out['internal_routes'].append(q)
 out['groups']=[dict(id=pid+':'+k,member_ids=[pid+':'+x for x in members]) for k,members in local['groups'].items()];out['court']=dict(id=pid+':SERVICE_COURT',polygon_xz_m=transform_polys([local['court_polygon_xz_m']],origin,yaw)[0],area_m2=g.polygon_area(local['court_polygon_xz_m']),role='court-served small-goods delivery and shared work space',floor_y_m=floor)
 return out

if __name__=='__main__':
 for f in FAMILIES:
  r=local_recipe(f);print(f,r['width_m'],r['depth_m'],len(r['placements']),len(r['actual_doors']),g.polygon_area(r['court_polygon_xz_m']))
