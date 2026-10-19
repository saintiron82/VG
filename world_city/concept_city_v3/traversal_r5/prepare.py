#!/usr/bin/env python3
"""Bound six actual-scene capsule cases. Writes only traversal_r5.

First run --routes-only. After parent seals bridge_scene.json run --scene PATH
--scene-sha256 HASH. No source height sampling, polygon fill or collider ramps.
"""
import argparse, hashlib, json, math, pathlib, sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent; CITY=HERE.parent; ROOT=CITY.parents[1]
sys.path.insert(0,str(ROOT))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def write(p,d):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def ref(p):return {'path':str(pathlib.Path(p).resolve()),'sha256':sha(p)}
def bounds(points):return [min(p[0] for p in points),min(p[-1] for p in points),max(p[0] for p in points),max(p[-1] for p in points)]
def overlaps(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
def transform(v,p):
 if 'transform' in p:
  b=p['transform']['basis'];t=p['transform'].get('translation',p.get('position_m',[0,0,0]));return [sum(b[i][j]*v[j] for j in range(3))+t[i] for i in range(3)]
 a=p.get('yaw_rad',math.radians(p.get('yaw_deg',0)));c,s=math.cos(a),math.sin(a);t=p['position_m'];return [c*v[0]+s*v[2]+t[0],v[1]+t[1],-s*v[0]+c*v[2]+t[2]]
def instance_bounds(p,b):return bounds([transform([x,y,z],p) for x in [b['min'][0],b['max'][0]] for y in [b['min'][1],b['max'][1]] for z in [b['min'][2],b['max'][2]]])
def route(ident,points,ids,scope):return {'id':ident,'kind':'actual_scene_public_route','points':points,'length_m':sum(math.dist(a,b) for a,b in zip(points,points[1:])),'source_road_ids':ids,'test_scope':scope,'minimum_allowed_feet_y_m':min(p[1] for p in points)-2,'placement_ids':[],'building_ids':[]}
def prepare_routes():
 source={'plan':CITY/'registered_source/plan.json','south_road':CITY/'registered_topography/road_extensions/south_country_r1/contract.json','merchant_pack':CITY/'assemblies/property/registered/merchant_block011/resolved_placements.json','bridge_pack':CITY/'assemblies/waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json','terrain_binding':CITY/'registered_integration/r5/terrain_binding.json'}
 d={k:read(p) for k,p in source.items()};records={k:ref(p) for k,p in source.items()}
 south=d['south_road'];bridge=d['bridge_pack'];T={'transform':bridge['bridge_to_world']};points=[transform([64,1.25,0],T)]+south['centerline_xyz_m']
 assert math.dist(transform([72,1.25,0],T),points[1])<1e-6
 a=route('SOUTH_NATIVE_TERMINAL_TO_COUNTRY',points,['MAIN_BRIDGE','SOUTH_COUNTRY_ROAD'],'Final 8 m native terminal and exact SOUTH_COUNTRY_ROAD source stations. Central moving bridge span excluded.')
 merchant=d['merchant_pack'];public=next(r for r in merchant['external_gate_links'] if r['id']=='M11_SHOP_COURT:PUBLIC_LINK');private=next(r for r in merchant['access_proposals'] if r['id']=='M11_SHOP_COURT:converted_goods_store:DOOR:0:GATE_LINK');road=next(r for r in d['plan']['roads'] if r['id']=='MARKET_WEST_EDGE')
 assert public['segment_index']==5 and public['gate_floor_y_m']==4 and private['finished_floor_y_m']==4
 # Exact declared public target and private route; stop at standing point, not doorway.
 xz=[road['polyline_xz_m'][5],public['polyline_xz_m'][1],public['polyline_xz_m'][0]]+list(reversed(private['polyline_xz_m'][1:-1]))
 assert math.dist(xz[-1],[7.361826819370155,84.84799902241383])<1e-8
 b=route('MARKET_TO_M11_SERVICE_COURT',[[x,4,z] for x,z in xz],['MARKET_WEST_EDGE',public['id'],private['id'],'M11_SHOP_COURT:SERVICE_COURT'],'Exact source public link then reversed goods-store route, stopping at exterior standing point inside service court; no door/interior claim.')
 routes=[]
 for r in [a,b]:
  routes.append(r);q=dict(r,id=r['id']+'_REVERSE',points=list(reversed(r['points'])));routes.append(q)
 # Preserve an existing finite river-hole fixture as an isolated harness control.
 old=read(CITY/'traversal/prepared.json');water=next(r for r in old['routes'] if r['id']=='NEGATIVE_UNBRIDGED_RIVER');water=dict(water,test_scope='Retained isolated contour-source finite river-hole control; no registered-city water traversal claim.');routes.append(water)
 wall=next(r for r in old['routes'] if r['id']=='NEGATIVE_ACTUAL_SOLID_WALL');wall=dict(wall,test_scope='Exact restored isolated wall master recompiled through unchanged common framework; no city obstacle substituted.');routes.append(wall)
 sources=HERE/'sources';sources.mkdir(exist_ok=True)
 for k,r in records.items():
  p=pathlib.Path(r['path']);dest=sources/(k+'_'+r['sha256']+p.suffix)
  if not dest.exists():dest.write_bytes(p.read_bytes())
  r['snapshot_path']=str(dest)
 water_path=CITY/'traversal/geometry/UNBRIDGED_RIVER_CONTROL.json';assert sha(water_path)==old['assets']['UNBRIDGED_RIVER_CONTROL']['render_sha256']
 wp=HERE/'geometry/UNBRIDGED_RIVER_CONTROL.json';wp.write_bytes(water_path.read_bytes());records['isolated_water_control']=ref(water_path)
 master=next((CITY/'traversal/sources').glob('proxy_actual_wall_master_*.json'));records['isolated_wall_master']=ref(master)
 from voxel_character.common import coordinate_planes,core,render_data
 import mesh
 compiled=coordinate_planes.compile_master(read(master),{'pitch':.1},max_candidate_cells=100000,max_output_cells=100000);assert compiled['valid'];render=render_data.make_render_data(compiled)
 write(HERE/'controls/actual_wall.compiled.json',compiled);write(HERE/'controls/actual_wall.render.json',render)
 for name,m in [('coordinate_planes',coordinate_planes),('core',core),('render_data',render_data),('mesh',mesh)]:records['wall_replay_'+name]=ref(m.__file__)
 write(HERE/'route_plan.json',{'schema':'riverstone.r5.six_case_route_plan.v1','sources':records,'routes':routes,'scene_required':'Parent-sealed evidence/visual_registered_common_r5/bridge_scene.json, hash supplied explicitly.','controls':{'wall_cells':len(compiled['cells']),'wall_quads':render['quad_count'],'wall_pitch_m':.1},'limits':['Routes are proposed physics tests, not passes.','Four centerline walks do not certify full-width navigation, carts, stairs, NPCs, doors or operational drawbridge safety.']})
 print('ROUTES_READY',len(routes),'WALL',len(compiled['cells']),flush=True)

def build_collision(scene_path,scene_sha):
 plan=read(HERE/'route_plan.json');scene_path=pathlib.Path(scene_path).resolve();assert scene_path.name=='bridge_scene.json','Use promoted actual scene, not fixed bridge draft';assert sha(scene_path)==scene_sha,'Scene hash differs from parent seal'
 runtime=scene_path.parent/'build_runtime.json';run=read(runtime);assert run['exit_code']==0 and not run['changed_during_build'],'Actual export did not finish cleanly'
 scene=read(scene_path);assert scene.get('bridge_mechanism'),'Expected promoted drawbridge scene'
 candidate_path=CITY/'registered_integration/r5/candidate.json';assert scene['integration_sha256']==sha(candidate_path),'Scene is not the current sealed r5 integration'
 for r in plan['sources'].values():assert sha(r['path'])==r['sha256']
 sources=dict(plan['sources']);sources.update(actual_scene=ref(scene_path),build_runtime=ref(runtime),integration_candidate=ref(candidate_path),route_plan=ref(HERE/'route_plan.json'))
 terrain=read(CITY/'registered_integration/r5/terrain_binding.json');assert scene['terrain_contract']['source_plan_sha256']==plan['sources']['plan']['sha256'];sources['terrain_contract']=ref(ROOT/terrain['contract_path']);assert sources['terrain_contract']['sha256']==terrain['contract_sha256']
 assets={};placements={};boxes={};audit=[];routes=plan['routes'];render_cache={}
 def native_render(key,asset):
  if key not in render_cache:
   path=ROOT/asset['render_path'];assert sha(path)==asset['render_sha256'];render_cache[key]=read(path)
  return render_cache[key]
 # Whole original triangles are selected, never clipped, filled, resampled or flattened.
 for number,r in enumerate(routes[:4]):
  if number%2:previous=routes[number-1];r['placement_ids']=previous['placement_ids'];r['building_ids']=previous['building_ids'];continue
  box=bounds(r['points']);box=[box[0]-6,box[1]-6,box[2]+6,box[3]+6];r['collision_bounds_xz_m']=box
  triangles=[];source_faces=[];excluded_water=0
  for material,raw in scene['surfaces'].items():
   assert len(raw)%3==0
   for i in range(0,len(raw),3):
    tri=raw[i:i+3]
    if not overlaps(bounds(tri),box):continue
    if material=='water':excluded_water+=1;continue
    # Exactly the conversion used by the actual City.gd renderer.
    triangles.append([tri[0],tri[2],tri[1]]);source_faces.append([material,i//3])
  key='SCENE:'+r['id'];p=HERE/'geometry'/(r['id']+'.json');write(p,{'schema':'riverstone.actual_scene_collision_triangles.v1','scene_sha256':scene_sha,'source_face_indices':source_faces,'triangles':triangles,'selection_bounds_xz_m':box,'height_resampling':False})
  assets[key]={'render_path':str(p.relative_to(ROOT)),'render_sha256':sha(p),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_r5_scene_surface','collision_layer':1};r['placement_ids'].append(key)
  natives=[]
  for instance in scene['common_instances']:
   assert instance.get('scale',[1,1,1])==[1,1,1]
   asset=scene['common_assets'][instance['asset_key']]
   key=instance['asset_key'];native_bounds=asset.get('bounds')
   if native_bounds is None:native_bounds=native_render(key,asset)['bounds']
   if not overlaps(instance_bounds(instance,native_bounds),box):continue
   render=native_render(key,asset);assert not render.get('rigid_parts'),'Explicit rigid-part collision poses required'
   assets[key]={'render_path':asset['render_path'],'render_sha256':asset['render_sha256']};p=dict(instance,category='actual_native_common_mesh',collision_layer=3,yaw_deg=math.degrees(instance.get('yaw_rad',0)));placements[p['id']]=p;r['placement_ids'].append(p['id']);natives.append(p['id'])
  # Actual scene proxy boxes remain actual boxes; do not invent body envelopes.
  for item in scene['boxes']:
   size=item['size_m'];b={'min':[-v/2 for v in size],'max':[v/2 for v in size]}
   if not overlaps(instance_bounds(item,b),box):continue
   boxes[item['id']]={'id':item['id'],'position_m':item['position_m'],'yaw_rad':item.get('yaw_rad',0),'boxes':[b],'collision_layer':3};r['building_ids'].append(item['id'])
  # Central mechanism is far outside this fixture. Refuse silently omitting it if moved locally.
  pivot=read(CITY/'assemblies/waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json')['bridge_to_world']['translation'];assert not overlaps([pivot[0]-25,pivot[2]-25,pivot[0]+25,pivot[2]+25],box)
  audit.append({'route':r['id'],'bounds':box,'exact_scene_triangles':len(triangles),'excluded_water_surface_triangles':excluded_water,'native_instance_ids':natives,'actual_box_ids':r['building_ids'],'whole_triangle_selection':True})
 for r in routes[4:]:
  pid=r['placement_ids'][0]
  if r['id']=='NEGATIVE_UNBRIDGED_RIVER':key='CONTROL_WATER';p=HERE/'geometry/UNBRIDGED_RIVER_CONTROL.json';fmt='source_grade_proxy_triangles'
  else:key='CONTROL_WALL';p=HERE/'controls/actual_wall.render.json';fmt='common_render_quads'
  assets[key]={'render_path':str(p.relative_to(ROOT)),'render_sha256':sha(p),'collision_format':fmt};placements[pid]={'id':pid,'asset_key':key,'position_m':[0,0,0],'category':'isolated_control','collision_layer':1}
 assert sha(scene_path)==scene_sha
 implementations=[HERE/p for p in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare.py','reuse_manifest.json']]
 result={'schema':'riverstone.r5.prepared_actual_scene_capsule.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':{str(p.relative_to(ROOT)):sha(p) for p in implementations},'assets':assets,'placements':placements,'buildings':boxes,'routes':routes,'coverage':{'positive_cases':4,'negative_controls':2,'collision_audit':audit},'assumptions':['Completed promoted r5 scene triangles and actual nearby native meshes/remaining box proxies.','Native holes and discrete risers retained; water display triangles excluded; no route snapping, auto step or infinite floor.','Natural surfaces use the exact exported triangles, not independently sampled analytic height.','Southern terminal only: moving central bridge machinery excluded by explicit nonintersection bound.','No full-width, door/interior, production-controller, cart or city-NPC guarantee.']}
 write(HERE/'prepared.json',result);write(HERE/'evidence/preparation.json',{'prepared_sha256':sha(HERE/'prepared.json'),'scene':sources['actual_scene'],'collision_audit':audit,'route_ids':[r['id'] for r in routes],'status':'prepared_not_executed'});print('COLLISION_READY',len(routes),len(assets),len(placements),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--routes-only',action='store_true');p.add_argument('--scene');p.add_argument('--scene-sha256');a=p.parse_args()
 if a.routes_only:prepare_routes()
 else:
  assert a.scene and a.scene_sha256,'Parent scene path and hash required';build_collision(a.scene,a.scene_sha256)
if __name__=='__main__':main()
