import pathlib,json,math,copy,importlib.util,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prep',H/'prepare_batch.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);b=p.b;ROOT=p.ROOT

def main():
 d=b.read(H/'prepared_checked.json');scene=b.read(p.SCENE);B=scene['bridge_mechanism']['bridge_to_world'];A=B['basis'];o=B['translation'];T={'transform':B,'position_m':o}
 oldpath=p.BASE/'revisions/r04_r6_winding/prepared.json';old=b.read(oldpath);rows={r['id']:r for r in d['routes']}
 def local(v):return [sum(A[k][i]*(v[k]-o[k])for k in range(3))for i in range(3)]
 fixed=next(i for i in scene['common_instances']if i['id']=='BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED');data=b.read(ROOT/scene['common_assets'][fixed['asset_key']]['render_path'])
 def local_floor(x):
  ys=[]
  for g in data['groups']:
   for q in g['quads']:
    a,c,e=q[:3];ny=(c[2]-a[2])*(e[0]-a[0])-(c[0]-a[0])*(e[2]-a[2])
    if ny<=0:continue
    for t in [[q[0],q[1],q[2]],[q[0],q[2],q[3]]]:
     y=p.y_at(t,x,0)
     if y is not None and y>=0:ys.append(y)
  assert ys,(x,'no native walking top');return min(ys,key=lambda y:abs(y-1.25))
 def merge_world(ident,source_ids):
  scene_faces={};native=set();boxes=set()
  for rid in source_ids:
   r=rows[rid];boxes.update(r['building_ids'])
   for pid in r['placement_ids']:
    if pid.startswith('SCENE:NETWORK:'):
     a=d['assets'][d['placements'][pid]['asset_key']];g=b.read(ROOT/a['render_path'])
     for face,t in zip(g['source_face_indices'],g['triangles']):
      key=tuple(face)
      if key in scene_faces:assert scene_faces[key]==t
      scene_faces[key]=t
    else:native.add(pid)
  file=H/'geometry'/(ident+'.json');b.write(file,{'scene_sha256':p.SHA,'source_face_indices':[list(k)for k in sorted(scene_faces)],'triangles':[scene_faces[k]for k in sorted(scene_faces)],'whole_triangles_only':True,'duplicate_original_triangles':0});key='SCENE:NETWORK:'+ident;d['assets'][key]={'render_path':str(file.relative_to(ROOT)),'render_sha256':b.sha(file),'collision_format':'actual_scene_triangles'};d['placements'][key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_network_scene_surface','collision_layer':1};return [key]+sorted(native),sorted(boxes)
 north=[b.transform([x,local_floor(x),0],T)for x in [-64,-72]]
 north+=[v for v in reversed(rows['ROAD:MAIN_BRIDGE']['points'])if local(v)[0]<-72.001]
 north+=rows['ROAD:SOUTH_MARKET_AXIS']['points']
 north+=rows['ROAD:MARKET_PROCESSION']['points'][1:]
 defs=[('NATIVE_NORTH_TERMINAL_TO_MARKET',north,['ROAD:MAIN_BRIDGE','ROAD:SOUTH_MARKET_AXIS','ROAD:MARKET_PROCESSION'],'Starts on exact native axis at X−64; follows actual north terminal to declared public road continuation. The remaining source connector is a test hypothesis, never support infill.'),('AUTHORITATIVE_SOUTH_TERMINAL_COUNTRY',next(r['points']for r in old['routes']if r['id']=='SOUTH_NATIVE_TERMINAL_TO_COUNTRY'),['ROAD:MAIN_BRIDGE','ROAD:SOUTH_COUNTRY_ROAD'],'Exact unchanged vectors of the passed R6 southern fixture, recropped from the current scene.')]
 for ident,points,src,scope in defs:
  ids,boxes=merge_world(ident,src)
  for reverse in [False,True]:
   r=b.route(ident+('_REVERSE'if reverse else ''),list(reversed(points))if reverse else points,[s.removeprefix('ROAD:')for s in src],scope);r.update(group=ident,placement_ids=ids,building_ids=boxes,bridge_state='ROAD_OPEN');d['routes'].append(r)
 for r in d['routes']:
  if r['id'].startswith('ROAD:MAIN_BRIDGE'):r['test_scope']='Legacy registered MAIN_BRIDGE centreline hypothesis; native-axis continuation is separately tested. No final alignment assertion.'
 d['sources']['checked_preparation']=b.ref(H/'prepared_checked.json');d['sources']['passed_southern_vectors']=b.ref(oldpath);d['implementation_hashes'][str(pathlib.Path(__file__).resolve().relative_to(ROOT))]=b.sha(pathlib.Path(__file__).resolve());d['coverage']['cases']=len(d['routes']);b.write(H/'prepared_runtime.json',d)
 b.write(H/'evidence/native_bridge_alignment.json',{'fixed_local_bounds':scene['common_assets'][fixed['asset_key']]['bounds'],'north_test_native_points_xyz_m':north[:2],'main_gate_local_xyz_m':local([117.00169999579944,1.2045723773,404.20606541995414]),'shared_market_axis_endpoint_local_xyz_m':local(rows['ROAD:SOUTH_MARKET_AXIS']['points'][0]),'unsupported_registered_station_local_xyz_m':local([118.27671044705853,1.09659980658,414.8110938061721]),'status':'Actual runtime continuation pending. No road/collision edits.'})
 print(json.dumps({'prepared':b.ref(H/'prepared_runtime.json'),'cases':len(d['routes']),'north_native_start':north[:2]}))
if __name__=='__main__':main()
