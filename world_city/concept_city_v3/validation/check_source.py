#!/usr/bin/env python3
"""Independent read-only source-plan audit; failures never mutate/reroute source."""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from collections import Counter,defaultdict,deque
from pathlib import Path
import geometry as g
HERE=Path(__file__).resolve().parent;CITY=HERE.parent;ROOT=CITY.parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def components(graph):
 remaining=set(graph);out=[]
 while remaining:
  seed=min(remaining);seen={seed};queue=[seed]
  while queue:
   for n in graph[queue.pop()]:
    if n not in seen:seen.add(n);queue.append(n)
  out.append(sorted(seen));remaining-=seen
 return sorted(out,key=lambda a:(-len(a),a))
def route_graph(lines,radius=.3):
 graph={r['id']:set() for r in lines};edges=[]
 bounds={r['id']:g.bounds(r['polyline_xz_m']) for r in lines}
 for i,a in enumerate(lines):
  for b in lines[i+1:]:
   reach=(a['width_m']+b['width_m'])/2-2*radius
   ba=bounds[a['id']];bb=bounds[b['id']]
   if not g.bbox_overlap([ba[0]-reach,ba[1]-reach,ba[2]+reach,ba[3]+reach],bb):continue
   dist,p,q=g.line_distance(a['polyline_xz_m'],b['polyline_xz_m'])
   if dist<=reach+g.EPS:
    graph[a['id']].add(b['id']);graph[b['id']].add(a['id']);edges.append({'a':a['id'],'b':b['id'],'centerline_distance_m':dist,'safe_corridor_overlap_m':reach-dist,'connection_xz_m':[(p[i]+q[i])/2 for i in (0,1)]})
 return graph,edges

def check(plan_path):
 raw=Path(plan_path).read_bytes();source_sha=hashlib.sha256(raw).hexdigest();plan=json.loads(raw);issues=[];warnings=[];checks={};roads=plan['roads'];paths=plan['paths'];buildings=plan['buildings'];plots=plan['plots'];bridges=plan['bridges'];gates=plan['gates']
 def issue(code,**data):issues.append({'code':code,**data})
 ids=[]
 for kind in ['roads','paths','plots','buildings','gates','bridges','spaces','districts']:
  values=[v['id'] for v in plan[kind]]
  for id,count in Counter(values).items():
   if count>1:issue('duplicate_id',kind=kind,id=id,count=count)
 graph,edges=route_graph(roads);public_components=components(graph);checks['public_route_graph']={'components':public_components,'connection_count':len(edges),'connections':edges,'policy':'corridor connectivity after0.3m capsule-radius erosion; independent line-distance test'}
 if len(public_components)!=1:issue('public_routes_disconnected',components=public_components)
 allgraph,alledges=route_graph(roads+paths);allcomponents=components(allgraph);public_ids={r['id'] for r in roads};connected_to_public=set()
 for comp in allcomponents:
  if public_ids.intersection(comp):connected_to_public.update(comp)
 road_ids={r['id'] for r in roads};path_ids={r['id'] for r in paths};owner_paths=defaultdict(list)
 for p in paths:
  if p.get('owner_building_id'):owner_paths[p['owner_building_id']].append(p)
  if p.get('road_id') not in road_ids:issue('path_unknown_road',id=p['id'],road_id=p.get('road_id'))
  if p['id'] not in connected_to_public:issue('path_disconnected_from_public',id=p['id'])
 entrance_checks=[];all_entrance_checks=[]
 for b in buildings:
  entrance=b['entrance_xz_m'];owned=owner_paths[b['id']]
  attached=[p for p in owned if g.point_line_distance(entrance,p['polyline_xz_m'])[0]<=.05]
  reachable=[p['id'] for p in attached if p['id'] in connected_to_public]
  direct=[r['id'] for r in roads if g.point_line_distance(entrance,r['polyline_xz_m'])[0]<=r['width_m']/2-.3]
  record={'building_id':b['id'],'attached_owned_paths':[p['id'] for p in attached],'reachable_paths':reachable,'direct_public_roads':direct}
  entrance_checks.append(record)
  if not reachable and not direct:issue('entrance_not_connected',**record,entrance_xz_m=entrance)
  for door_index,door in enumerate(b.get('all_entrances_xz_m',[entrance])):
   door_paths=[p['id'] for p in owned if g.point_line_distance(door,p['polyline_xz_m'])[0]<=.05 and p['id'] in connected_to_public]
   door_roads=[r['id'] for r in roads if g.point_line_distance(door,r['polyline_xz_m'])[0]<=r['width_m']/2-.3]
   door_record={'building_id':b['id'],'door_index':door_index,'entrance_xz_m':door,'reachable_paths':door_paths,'direct_public_roads':door_roads};all_entrance_checks.append(door_record)
   if not door_paths and not door_roads:issue('declared_entrance_not_connected',**door_record)
  if b.get('road_id') not in road_ids:issue('building_unknown_road',id=b['id'],road_id=b.get('road_id'))
 checks['entrances']={'building_count':len(buildings),'connected_count':sum(bool(v['reachable_paths'] or v['direct_public_roads']) for v in entrance_checks),'records':entrance_checks}
 checks['all_declared_entrances']={'entrance_count':len(all_entrance_checks),'connected_count':sum(bool(v['reachable_paths'] or v['direct_public_roads']) for v in all_entrance_checks),'records':all_entrance_checks}
 road_polys=[(r['id'],i,g.ribbon(a,b,r['width_m'])) for r in roads for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]))]
 water=plan['water_reservations'];canal=water['service_canal_polyline_xz_m'];canal_width=water['service_corridor_width_m']
 water_polys=[('SERVICE_CANAL:'+str(i),g.ribbon(a,b,canal_width)) for i,(a,b) in enumerate(zip(canal,canal[1:]))]+[('RIVER',water['river_polygon_xz_m']),('RESERVOIR',water['reservoir_outer_polygon_xz_m'])]
 feeder=water.get('spring_feeder_polyline_xz_m',[])
 water_polys += [('SPRING_FEEDER:'+str(i),g.ribbon(a,b,water.get('spring_feeder_reserve_width_m',8))) for i,(a,b) in enumerate(zip(feeder,feeder[1:]))]
 road_bounds=[g.bounds(poly) for _,_,poly in road_polys]
 for kind,objects,polykey in [('plot',plots,'polygon_xz_m'),('building',buildings,'footprint_xz_m')]:
  polygons=[o[polykey] for o in objects];boxes=[g.bounds(p) for p in polygons]
  for i,obj in enumerate(objects):
   poly=polygons[i];box=boxes[i]
   for j,(rid,segment,rpoly) in enumerate(road_polys):
    if not g.bbox_overlap(box,road_bounds[j]):continue
    overlap=g.intersection_area(poly,rpoly)
    if overlap>1e-4:issue(kind+'_public_road_conflict',id=obj['id'],road_id=rid,road_segment=segment,overlap_area_m2=overlap)
   for wid,wpoly in water_polys:
    if not g.bbox_overlap(box,g.bounds(wpoly)):continue
    overlap=g.intersection_area(poly,wpoly)
    if overlap>1e-4:issue(kind+'_water_reservation_conflict',id=obj['id'],water_id=wid,overlap_area_m2=overlap)
   for j in range(i):
    if not g.bbox_overlap(box,boxes[j]):continue
    overlap=g.intersection_area(poly,polygons[j])
    if overlap>1e-4:issue(kind+'_overlap',id=obj['id'],other_id=objects[j]['id'],overlap_area_m2=overlap)
 # Full-width door/path corridors against OTHER building bodies; own doorway
 # contact is allowed only at its declared start, never arbitrary inside passage.
 building_bounds={b['id']:g.bounds(b['footprint_xz_m']) for b in buildings}
 for p in paths:
  for index,(a,b) in enumerate(zip(p['polyline_xz_m'],p['polyline_xz_m'][1:])):
   ribbon=g.ribbon(a,b,p['width_m'])
   if not ribbon:
    warnings.append({'code':'zero_length_path_segment','id':p['id'],'segment':index});continue
   box=g.bounds(ribbon)
   for building in buildings:
    if building['id']==p.get('owner_building_id'):continue
    if not g.bbox_overlap(box,building_bounds[building['id']]):continue
    overlap=g.intersection_area(ribbon,building['footprint_xz_m'])
    if overlap>1e-4:issue('path_other_building_conflict',id=p['id'],segment=index,building_id=building['id'],overlap_area_m2=overlap)
 # Every road/canal crossing must have a matching bridge whose deck endpoints
 # leave the actual reserved corridor. A center-only bridge label is insufficient.
 bridge_checks=[]
 for r in roads:
  for si,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   for wi,(c,d) in enumerate(zip(canal,canal[1:])):
    hit=g.segment_hit(a,b,c,d)
    if not hit:continue
    matches=[v for v in bridges if v.get('road_id')==r['id'] and v.get('water_channel_segment_index')==wi and math.dist(v['position_xz_m'],hit[0])<.5]
    if not matches:issue('unbridged_service_canal_crossing',road_id=r['id'],road_segment=si,water_segment=wi,point_xz_m=hit[0]);continue
    for bridge in matches:
     endpoint_clearances=[g.closest_point(p,c,d)[0]-canal_width/2 for p in bridge['deck_polyline_xz_m']]
     record={'bridge_id':bridge['id'],'endpoint_water_corridor_clearance_m':endpoint_clearances,'road_id':r['id']};bridge_checks.append(record)
     if min(endpoint_clearances)<.3:issue('bridge_deck_does_not_span_water_reservation',**record)
 # River/reservoir crossing ownership is separate from service-canal records.
 for r in roads:
  for si,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   for water_id,wpoly,role in [('RIVER',water['river_polygon_xz_m'],'main_river_bridge'),('RESERVOIR',water['reservoir_outer_polygon_xz_m'],'reservoir_bridge')]:
    intersection=g.convex_intersection(g.ribbon(a,b,r['width_m']),wpoly)
    if g.area(intersection)<=1e-4:continue
    matches=[v for v in bridges if v.get('road_id')==r['id'] and (v.get('role')==role or v.get('water_id')==water_id)]
    if not matches:issue('road_water_polygon_crossing_without_bridge',road_id=r['id'],segment=si,water_id=water_id,overlap_area_m2=g.area(intersection))
 checks['bridges']=bridge_checks
 # Reserve corridors are checked across the full road width, including
 # tangencies that never produce a centerline intersection. Bridge labels alone
 # cannot exempt an arbitrarily long road or a second crossing.
 bridge_coverage=[]
 for road_id,segment,rpoly in road_polys:
  road_bridges=[bridge for bridge in bridges if bridge.get('road_id')==road_id]
  bridge_polys=[g.ribbon(a,b,bridge['width_m']) for bridge in road_bridges for a,b in zip(bridge['deck_polyline_xz_m'],bridge['deck_polyline_xz_m'][1:])]
  for water_id,wpoly in water_polys:
   if not g.bbox_overlap(g.bounds(rpoly),g.bounds(wpoly)):continue
   overlap=g.convex_intersection(rpoly,wpoly);total=g.area(overlap)
   if total<=1e-4:continue
   covered=sum(g.intersection_area(overlap,bpoly) for bpoly in bridge_polys)
   record={'road_id':road_id,'segment':segment,'water_id':water_id,'reserved_overlap_area_m2':total,'uncovered_reserved_area_m2':max(0,total-covered)};bridge_coverage.append(record)
   if total-covered>1e-4:issue('road_water_reserved_area_without_owned_deck',**record)
 checks['bridge_full_width_reservation_coverage']=bridge_coverage
 blocks={block['id']:block for block in plan.get('blocks',[])};block_records=[]
 for plot in plots:
  block_id=plot.get('block_id')
  if not block_id:continue
  if block_id not in blocks:issue('plot_unknown_block',plot_id=plot['id'],block_id=block_id);continue
  block=blocks[block_id];plot_area=g.area(plot['polygon_xz_m']);inside=g.intersection_area(plot['polygon_xz_m'],block['polygon_xz_m'])
  record={'plot_id':plot['id'],'block_id':block_id,'outside_block_area_m2':max(0,plot_area-inside)};block_records.append(record)
  if plot_area-inside>1e-4:issue('plot_outside_owned_block',**record)
  if plot['id'] not in block.get('plot_ids',[]):issue('plot_block_reverse_reference_missing',plot_id=plot['id'],block_id=block_id)
 checks['block_ownership']={'blocks':len(blocks),'plots_with_block_id':len(block_records),'plots_without_block_id':len(plots)-len(block_records),'records':block_records}
 boundary=plan['boundary_xz_m'];gate_checks=[]
 for r in roads:
  for si,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   for wi,(c,d) in enumerate(zip(boundary,boundary[1:]+boundary[:1])):
    hit=g.segment_hit(a,b,c,d)
    if not hit:continue
    matches=[v for v in gates if v.get('road_id')==r['id'] and v.get('wall_edge_index')==wi and math.dist(v['position_xz_m'],hit[0])<.5]
    if not matches:issue('road_wall_crossing_without_gate',road_id=r['id'],wall_edge_index=wi,point_xz_m=hit[0]);continue
    angle=abs(g.cross(g.sub(b,a),g.sub(d,c)))/(math.dist(a,b)*math.dist(c,d));required=r['width_m']/max(angle,1e-8)+.6
    for gate in matches:
     record={'gate_id':gate['id'],'required_clear_width_m':required,'declared_width_m':gate['opening_width_m'],'road_id':r['id']};gate_checks.append(record)
     if gate['opening_width_m']+1e-7<required:issue('gate_too_narrow_for_oblique_road',**record)
 checks['gates']=gate_checks
 levels=water.get('service_water_levels_m',[])
 if len(levels)!=len(canal):issue('service_canal_level_count_mismatch')
 else:
  uphill=[{'segment':i,'from_m':a,'to_m':b} for i,(a,b) in enumerate(zip(levels,levels[1:])) if b>a+1e-8]
  for row in uphill:issue('service_canal_uphill',**row)
  checks['service_canal_head_reservation']={'heads_m':levels,'uphill_segments':uphill,'outfall_inside_river':g.point_inside(canal[-1],water['river_polygon_xz_m']),
   'scope':'service reservation only; full clean/source/drain hydrology graph awaits terrain contract'}
  if not checks['service_canal_head_reservation']['outfall_inside_river']:issue('service_canal_outfall_not_in_river')
 warnings.append({'code':'hydrology_requires_separate_contract_audit','detail':'This source audit checks reservations only. Run check_hydrology.py on the matching terrain contract for graph/head checks.'})
 counts=Counter(v['code'] for v in issues)
 snapshot=HERE/'evidence'/'sources'/('plan_'+source_sha+'.json');snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(raw)
 return {'schema':'riverstone.concept_city.independent_source_validation.v1','status':'pass' if not issues else 'fail',
  'source':{'path':str(plan_path.resolve()),'sha256':source_sha,'snapshot':str(snapshot),'revision':plan.get('revision')},
  'checker_sha256':digest(Path(__file__)),'geometry_sha256':digest(HERE/'geometry.py'),
  'counts':{'roads':len(roads),'paths':len(paths),'plots':len(plots),'buildings':len(buildings),'issues':len(issues),'by_code':dict(counts)},
  'checks':checks,'issues':issues,'warnings':warnings,
  'limitations':['Source-only geometry/connectivity, not physics or navigation.','No graphical/voxel completion claim.','Hydrology graph/head consistency is checked separately against the terrain-owned contract.']}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,default=CITY/'source/plan.json');ap.add_argument('--output',type=Path);args=ap.parse_args()
 result=check(args.plan);output=args.output or HERE/'evidence'/('source_'+result['source']['sha256'][:12]+'_'+result['checker_sha256'][:8]+'.json');write(output,result)
 print(json.dumps({'status':result['status'],'source':result['source'],'counts':result['counts'],'output':str(output),'public_components':result['checks']['public_route_graph']['components'],'connected_entrances':result['checks']['entrances']['connected_count']},indent=2));raise SystemExit(0 if result['status']=='pass' else 2)
