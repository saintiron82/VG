#!/usr/bin/env python3
"""Image-registered candidate audit. No frozen contour results are inherited.

Checks actual source coordinates against their image correspondences and
reserved source footprints. Modular door offsets, collision and visual fidelity
remain separate approvals. Reports retain every positive-area conflict.
"""
import argparse,hashlib,importlib.util,json,math,sys
from collections import defaultdict,Counter
from pathlib import Path
import geometry as g
from check_registration import project_xyz
HERE=Path(__file__).resolve().parent;CITY=HERE.parent;ROOT=CITY.parents[1]
sys.path.insert(0,str(ROOT))

def digest(raw):return hashlib.sha256(raw).hexdigest()
def cells(box):
 for x in range(math.floor(box[0]/32),math.floor(box[2]/32)+1):
  for z in range(math.floor(box[1]/32),math.floor(box[3]/32)+1):yield x,z
def spatial(records):
 grid=defaultdict(list)
 for i,r in enumerate(records):
  r['bounds']=g.bounds(r['poly'])
  for cell in cells(r['bounds']):grid[cell].append(i)
 def query(poly):
  bounds=g.bounds(poly)
  return (records[i] for i in sorted(set(i for cell in cells(bounds) for i in grid.get(cell,[]))) if g.bbox_overlap(bounds,records[i]['bounds']))
 return query

def check(path,component_path=None):
 path=path.resolve();component_path=component_path.resolve() if component_path else None
 raw=path.read_bytes();plan=json.loads(raw);sha=digest(raw);controls_path=ROOT/plan['registration']['controls_path'];controls_raw=controls_path.read_bytes();controls=json.loads(controls_raw)
 author_path=CITY/'registered_topography/author.py';author_raw=author_path.read_bytes();dependency_inputs=[(name,p,p.read_bytes()) for name,p in [('road_controls',CITY/'registered_source/road_controls.json'),('terrain_contract',CITY/'registered_topography/contract.json'),('polygon_dependency',ROOT/'world_city/runtime_city/checks/placement.py')]];spec=importlib.util.spec_from_file_location('independent_registered_height',author_path);author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 issues=[];warnings=[];registration=[];collisions=[];connections=[];extra_inputs=list(dependency_inputs)
 if component_path:
  overlay_raw=component_path.read_bytes();overlay=json.loads(overlay_raw);replaced=set(overlay['replace_registered_group_ids']);plan['landmark_components']=[g for g in plan.get('landmark_components',[]) if g['id'] not in replaced]+overlay['groups'];extra_inputs.append(('component_overlay',component_path,overlay_raw))
  declared=overlay['source'];adaptation_path=ROOT/declared['path'];adaptation_raw=adaptation_path.read_bytes();extra_inputs.append(('component_adaptation',adaptation_path,adaptation_raw))
  if digest(adaptation_raw)!=declared['sha256']:issues.append({'code':'component_adaptation_hash_mismatch'})
 def issue(code,**kw):issues.append({'code':code,**kw})
 if author.CONTROLS_SHA256!=digest(controls_raw):issue('imported_controls_hash_mismatch')
 if author.ROAD_CONTROLS_SHA256!=digest(dependency_inputs[0][2]):issue('imported_road_controls_hash_mismatch')
 if json.loads(dependency_inputs[1][2]).get('source_plan_sha256')!=sha:issue('terrain_contract_plan_hash_mismatch')
 if digest(controls_raw)!=plan['registration']['controls_sha256']:issue('registration_controls_hash_mismatch')
 if plan['registration']['source_image_sha256']!=controls['source_image_sha256']:issue('registration_image_hash_mismatch')
 if plan['registration']['camera_model']!=controls['camera_model']:issue('registration_camera_mismatch')
 def correspondence(kind,id,pixels,xyz,stored=None):
  if len(pixels)!=len(xyz) or not xyz:issue('correspondence_count',kind=kind,id=id);return
  errors=[math.dist(project_xyz(controls['camera_model'],p),uv) for p,uv in zip(xyz,pixels)]
  record={'kind':kind,'id':id,'points':len(xyz),'maximum_projection_residual_px':max(errors)}
  if stored is not None:
   mismatch=max((math.dist(a,b) for a,b in zip(xyz,stored)),default=0.) if len(xyz)==len(stored) else float('inf')
   record['maximum_actual_to_stored_xyz_delta_m']=mismatch if math.isfinite(mismatch) else None
   if mismatch>1e-5:issue('stored_xyz_does_not_match_actual_geometry',kind=kind,id=id,maximum_delta_m=record['maximum_actual_to_stored_xyz_delta_m'])
  registration.append(record)
  if max(errors)>.001:issue('image_projection_residual',kind=kind,id=id,maximum_px=max(errors))
 for r in plan['correspondences']:correspondence(r['kind'],r['id'],r['trace_pixel_xy'],r['world_xyz_m'])
 for r in plan['roads']:
  if 'trace_pixel_xy' in r:
   xyz=[[p[0],y,p[1]] for p,y in zip(r['polyline_xz_m'],r['levels_m'])]
   correspondence('actual_road_polyline',r['id'],r['trace_pixel_xy'],xyz,r.get('resolved_world_xyz_m'))
 wall=plan['wall_registration'];correspondence('actual_wall_boundary','WALL',wall['trace_pixel_xy'],[[p[0],y,p[1]] for p,y in zip(wall['polygon_xz_m'],wall['levels_m'])],wall.get('world_xyz_m'))
 for r in plan['water_reservations']['channels']:
  correspondence('actual_channel_polyline',r['id'],r['trace_pixel_xy'],[[p[0],y,p[1]] for p,y in zip(r['polyline_xz_m'],r['levels_m'])],r.get('resolved_world_xyz_m'))
 # Actual assigned parcels and source body footprints, including noble masses.
 suppressed=set(plan.get('landmark_component_suppressed_building_ids',[]));buildings=[b for b in plan['buildings'] if b['id'] not in suppressed]
 bodies=[{'id':b['id'],'poly':b['footprint_xz_m'],'object':b} for b in buildings];body_query=spatial(bodies)
 plots={p['id']:p for p in plan['plots']};plot_rows=[{'id':p['id'],'poly':p['polygon_xz_m'],'object':p} for p in plan['plots']];plot_query=spatial(plot_rows)
 road_rows=[{'id':r['id'],'segment':i,'poly':g.ribbon(a,b,r['width_m']),'object':r} for r in plan['roads'] for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])) if math.dist(a,b)>1e-8];road_query=spatial(road_rows)
 water_rows=[{'id':w['surface_id'],'segment':i,'poly':w['polygon_xz_m']} for i,w in enumerate(plan['water_reservations']['finite_water_polygons'])];water_query=spatial(water_rows)
 def overlap_record(code,a,b,area,**extra):
  if area>1e-4:issue(code,id=a['id'],other_id=b['id'],overlap_area_m2=area,**extra)
 for a in bodies:
  for b in body_query(a['poly']):
   if a['id']<b['id']:overlap_record('body_body_overlap',a,b,g.intersection_area(a['poly'],b['poly']))
  for r in road_query(a['poly']):overlap_record('body_public_road_overlap',a,r,g.intersection_area(a['poly'],r['poly']),road_segment=r['segment'])
  for w in water_query(a['poly']):overlap_record('body_water_overlap',a,w,g.intersection_area(a['poly'],w['poly']),water_piece=w['segment'])
  p=plots.get(a['object'].get('plot_id'))
  if p:
   outside=g.area(a['poly'])-g.intersection_area(a['poly'],p['polygon_xz_m'])
   if outside>1e-4:issue('body_outside_assigned_plot',id=a['id'],plot_id=p['id'],outside_area_m2=outside)
 for a in plot_rows:
  for b in plot_query(a['poly']):
   if a['id']<b['id']:overlap_record('plot_plot_overlap',a,b,g.intersection_area(a['poly'],b['poly']))
  for r in road_query(a['poly']):overlap_record('plot_public_road_overlap',a,r,g.intersection_area(a['poly'],r['poly']),road_segment=r['segment'])
  for w in water_query(a['poly']):overlap_record('plot_water_overlap',a,w,g.intersection_area(a['poly'],w['poly']),water_piece=w['segment'])
 # Public connectivity at 0.3 m capsule-radius erosion, derived independently
 # from all actual source segments (densified curves included).
 graph={r['id']:set() for r in plan['roads']};seen=set()
 for a in road_rows:
  for b in road_query(a['poly']):
   pair=tuple(sorted([a['id'],b['id']]))
   if a['id']==b['id'] or pair in seen:continue
   ra,rb=a['object'],b['object'];aa,ab=ra['polyline_xz_m'][a['segment']:a['segment']+2];ba,bb=rb['polyline_xz_m'][b['segment']:b['segment']+2]
   distance,_,_=g.segment_distance(aa,ab,ba,bb);reach=(ra['width_m']+rb['width_m'])/2-.6
   if distance<=reach+1e-7:
    seen.add(pair);graph[a['id']].add(b['id']);graph[b['id']].add(a['id']);connections.append({'a':a['id'],'b':b['id'],'safe_corridor_overlap_m':reach-distance})
 components=[];todo=set(graph)
 while todo:
  start=next(iter(todo));found={start};stack=[start]
  while stack:
   for q in graph[stack.pop()]-found:found.add(q);stack.append(q)
  todo-=found;components.append(sorted(found))
 if len(components)!=1:issue('public_routes_disconnected',components=components)
 # Extend connectivity through compound/other explicit paths. A path ending at
 # an estate gate can legitimately reach a road through its separate gate link.
 all_lines=plan['roads']+plan['paths'];all_graph={r['id']:set() for r in all_lines}
 all_rows=[{'id':r['id'],'segment':i,'poly':g.ribbon(a,b,r['width_m']),'object':r} for r in all_lines for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])) if math.dist(a,b)>1e-8]
 all_query=spatial(all_rows);all_seen=set()
 for a in all_rows:
  for b in all_query(a['poly']):
   pair=tuple(sorted([a['id'],b['id']]))
   if a['id']==b['id'] or pair in all_seen:continue
   ra,rb=a['object'],b['object'];aa,ab=ra['polyline_xz_m'][a['segment']:a['segment']+2];ba,bb=rb['polyline_xz_m'][b['segment']:b['segment']+2]
   distance,_,_=g.segment_distance(aa,ab,ba,bb);reach=(ra['width_m']+rb['width_m'])/2-.6
   if distance<=reach+1e-7:all_seen.add(pair);all_graph[a['id']].add(b['id']);all_graph[b['id']].add(a['id'])
 reached=set(graph);stack=list(reached)
 while stack:
  for q in all_graph[stack.pop()]-reached:reached.add(q);stack.append(q)
 # Provisional source door paths are geometric candidates, never actual offset
 # cached doors. Check full width against other bodies, and declared public end.
 roads={r['id']:r for r in plan['roads']};entry_records=[]
 for p in plan['paths']:
  r=roads.get(p.get('road_id'));owner=p.get('owner_building_id');end=p['polyline_xz_m'][-1]
  distance=g.point_line_distance(end,r['polyline_xz_m'])[0] if r else None
  attached=distance is not None and distance<=(r['width_m']+p['width_m'])/2-.6+1e-6
  entry_records.append({'path_id':p['id'],'owner_building_id':owner,'declared_road_id':p.get('road_id'),'endpoint_centerline_distance_m':distance,'endpoint_attached_after_radius_erosion':attached,'path_reaches_public_via_explicit_paths':p['id'] in reached})
  if not attached:warnings.append({'code':'provisional_path_endpoint_misses_declared_road',**entry_records[-1]})
  if p['id'] not in reached:issue('provisional_path_disconnected_from_public_network',**entry_records[-1])
  for i,(a,b) in enumerate(zip(p['polyline_xz_m'],p['polyline_xz_m'][1:])):
   if math.dist(a,b)<1e-8:continue
   strip=g.ribbon(a,b,p['width_m'])
   for body in body_query(strip):
    if body['id']!=owner:overlap_record('provisional_path_other_body_overlap',{'id':p['id']},body,g.intersection_area(strip,body['poly']),path_segment=i)
 # Component envelopes include explicit vertical classification. They are
 # blockout masses, not actual compiled surfaces or arch-void proof.
 component_count=0
 for group in plan.get('landmark_components',[]):
  anchor=group['world_anchor_xyz_m']
  for mass in group['masses']:
   component_count+=1;center=[anchor[i]+mass['position_local_xyz_m'][i] for i in range(3)];size=mass['size_xyz_m'];yaw=math.radians(mass.get('yaw_degrees',0));poly=[]
   for x,z in [(-size[0]/2,-size[2]/2),(size[0]/2,-size[2]/2),(size[0]/2,size[2]/2),(-size[0]/2,size[2]/2)]:poly.append([center[0]+x*math.cos(yaw)+z*math.sin(yaw),center[2]-x*math.sin(yaw)+z*math.cos(yaw)])
   low,high=center[1]-size[1]/2,center[1]+size[1]/2
   for r in road_query(poly):
    clip=g.convex_intersection(poly,r['poly']);area=g.area(clip)
    if area<1e-4:continue
    heights=[author.road_height_at(r['id'],*p) for p in clip]
    classification='overhead' if low>=max(heights)+1.9 else 'below_deck' if high<=min(heights)+.05 else 'walking_height_overlap'
    record={'group_id':group['id'],'component_id':mass['id'],'road_id':r['id'],'segment':r['segment'],'area_m2':area,'classification':classification,'component_y_range_m':[low,high],'sampled_road_y_range_m':[min(heights),max(heights)]};collisions.append(record)
    if classification=='walking_height_overlap':issue('component_public_road_overlap',**record)
 # Every input consulted is snapshotted, including imported camera/height code.
 sources={}
 for name,p,data in [('plan',path,raw),('registration',controls_path,controls_raw),('registered_height_author',author_path,author_raw)]+extra_inputs:
  h=digest(data);snapshot=HERE/'evidence/sources'/('registered_'+name+'_'+h+p.suffix);snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(data);sources[name]={'path':str(p.relative_to(ROOT)),'sha256':h,'snapshot':str(snapshot.relative_to(ROOT))}
  if p.read_bytes()!=data:issue('input_changed_during_audit',input=name)
 counts=Counter(i['code'] for i in issues)
 return {'schema':'riverstone.registered_source.independent_audit.v1','status':'pass' if not issues else 'fail','source':sources,'checker_sha256':digest(Path(__file__).read_bytes()),'geometry_sha256':digest((HERE/'geometry.py').read_bytes()),'registration_checker_sha256':digest((HERE/'check_registration.py').read_bytes()),'counts':{'roads':len(plan['roads']),'paths':len(plan['paths']),'bodies':len(bodies),'plots':len(plots),'components':component_count,'registration_records':len(registration),'issues':len(issues),'issue_codes':dict(counts)},'registration':registration,'public_route_components':components,'public_route_connections':connections,'provisional_entry_endpoints':entry_records,'component_road_intersections':collisions,'issues':issues,'warnings':warnings,'limits':['Image correspondence arithmetic and finite source envelopes only; no visual approval inferred.','Precinct/estate boundary repairs remain explicit hypotheses requiring image review.','Provisional paths do not certify actual cached door offsets, thresholds, stairs, or controller traversal.','No old contour-source pass is inherited.','Public connectivity is planar strip connectivity; water crossings, retaining edges, slopes and source gate assemblies require separate validation.','Component envelopes classify road intersections by sampled height; detailed arch openings and actual meshes are untested.']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,default=CITY/'registered_source/plan.json');ap.add_argument('--components',type=Path);a=ap.parse_args();r=check(a.plan,a.components);tag='registered_overlay_'+r['source']['component_overlay']['sha256'][:8] if a.components else 'registered_source';out=HERE/'evidence'/(tag+'_'+r['source']['plan']['sha256'][:12]+'_'+r['checker_sha256'][:12]+'.json');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'report':str(out),'counts':r['counts'],'maximum_projection_residual_px':max(v['maximum_projection_residual_px'] for v in r['registration'])},indent=2));raise SystemExit(0 if r['status']=='pass' else 2)
