#!/usr/bin/env python3
"""Prepare bounded, finite optional road/bridge collision candidates.

Shared world grid triangles are clipped to authored road ownership, exact water
polygons and building holes. Only source-owned bridge spans may cover their
named water body. This is a collision adapter, not a voxel/display mesher.
"""
import hashlib,heapq,importlib.util,json,math,sys
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent;CITY=HERE.parent;ROOT=CITY.parents[1]
sys.path[:0]=[str(ROOT),str(CITY/'validation')]
import geometry as g
from world_city.runtime_city.checks.placement import convex_difference
PITCH=.5

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
def key(p):return tuple(round(float(v),7) for v in p)
def read(p):return json.loads(Path(p).read_text())
def subtract(parts,holes):
 for hole in holes:
  hb=g.bounds(hole);nextp=[]
  for p in parts:
   if not g.bbox_overlap(g.bounds(p),hb) or g.area(g.convex_intersection(p,hole))<1e-9:nextp.append(p)
   else:nextp.extend(q for q in convex_difference(p,hole) if g.area(q)>1e-9)
  parts=nextp
 return parts

def road_graph(roads,stops):
 segments=[]
 for road in roads:
  for i,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   if math.dist(a,b)>1e-8:segments.append({'road':road,'index':i,'a':a,'b':b,'cuts':[0.,1.]})
 for i,s in enumerate(segments):
  for t in segments[:i]:
   hit=g.segment_hit(s['a'],s['b'],t['a'],t['b'])
   if hit:s['cuts'].append(hit[1]);t['cuts'].append(hit[2])
  for point in stops:
   distance,_,station=g.closest_point(point,s['a'],s['b'])
   if distance<1e-5:s['cuts'].append(station)
 graph=defaultdict(list)
 for s in segments:
  cuts=sorted(set(round(max(0,min(1,t)),10) for t in s['cuts']))
  for a,b in zip(cuts,cuts[1:]):
   p=key([s['a'][k]+(s['b'][k]-s['a'][k])*a for k in (0,1)]);q=key([s['a'][k]+(s['b'][k]-s['a'][k])*b for k in (0,1)])
   if math.dist(p,q)<1e-6:continue
   graph[p].append((q,math.dist(p,q),s['road']['id']));graph[q].append((p,math.dist(p,q),s['road']['id']))
 return graph

def shortest(graph,start,end):
 start=key(start);end=key(end);queue=[(0,start)];dist={start:0};parents={}
 while queue:
  distance,node=heapq.heappop(queue)
  if node==end:break
  if distance!=dist[node]:continue
  for target,length,road in graph[node]:
   new=distance+length
   if new<dist.get(target,float('inf')):dist[target]=new;parents[target]=(node,road);heapq.heappush(queue,(new,target))
 if end not in dist:raise ValueError(('no exact source centerline route',start,end))
 points=[end];roads=[]
 while points[-1]!=start:
  previous,road=parents[points[-1]];points.append(previous);roads.append(road)
 return list(reversed(points)),list(reversed(roads))

def prepare():
 source_paths={'plan':CITY/'source/plan.json','contract':CITY/'topography/contract.json','height_author':CITY/'topography/author.py','polygon_dependency':ROOT/'world_city/runtime_city/checks/placement.py'}
 raw={k:p.read_bytes() for k,p in source_paths.items()};hashes={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()}
 plan=json.loads(raw['plan']);contract=json.loads(raw['contract'])
 if hashes['plan']!=contract['source_plan_sha256']:raise ValueError('mixed plan and terrain contract')
 spec=importlib.util.spec_from_file_location('tested_v3_grade_author',source_paths['height_author']);author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 if author.SOURCE_PLAN_SHA256!=hashes['plan']:raise ValueError('mixed imported source plan')
 road_index={r['id']:r for r in plan['roads']};assets={};placements={};routes=[];buildings={};geometry_audit=[]
 water=[(d['surface_id'],d['polygon_xz_m']) for d in contract['water_domain_polygons']]
 body_polys=[b['footprint_xz_m'] for b in plan['buildings']]
 body_bounds=[(g.bounds(p),p) for p in body_polys];water_bounds=[(g.bounds(p),wid,p) for wid,p in water]
 floors={p['building_id']:p['floor_y_m'] for p in contract['building_pads']}
 for b in plan['buildings']:
  buildings[b['id']]={'id':b['id'],'position_m':[b['position_xz_m'][0],floors.get(b['id'],author.dry_height_at(*b['position_xz_m'])),b['position_xz_m'][1]],'yaw_rad':b['yaw_rad'],'boxes':[{'min':[-b['width_m']/2,0,-b['depth_m']/2],'max':[b['width_m']/2,b['height_m'],b['depth_m']/2]}]}

 def make_mesh(id,owners,points,height_fn,holes=True):
  # Spatial index only on finite authored owner rectangles, never whole-city bounds.
  grid=defaultdict(list)
  for index,owner in enumerate(owners):
   box=g.bounds(owner['poly'])
   for ix in range(math.floor(box[0]/PITCH),math.ceil(box[2]/PITCH)):
    for iz in range(math.floor(box[1]/PITCH),math.ceil(box[3]/PITCH)):grid[ix,iz].append(index)
  height_cache={};triangles=[];maximum_error=0.;maximum_gradient=0.;area=0.;removed_water=0.;removed_body=0
  def h(point):
   k=key(point)
   if k not in height_cache:height_cache[k]=height_fn(*point)
   return height_cache[k]
  for (ix,iz),indices in sorted(grid.items()):
   x,z=ix*PITCH,iz*PITCH;corners=[[x,z],[x+PITCH,z],[x+PITCH,z+PITCH],[x,z+PITCH]];box=[x,z,x+PITCH,z+PITCH]
   local_water=[(wid,p) for bounds,wid,p in water_bounds if g.bbox_overlap(box,bounds)] if holes else []
   local_bodies=[p for bounds,p in body_bounds if g.bbox_overlap(box,bounds)] if holes else []
   for base in [[corners[0],corners[1],corners[2]],[corners[0],corners[2],corners[3]]]:
    heights=[h(p) for p in base];a,b,c=base;den=g.cross(g.sub(b,a),g.sub(c,a))
    def interpolate(p):
     u=g.cross(g.sub(p,a),g.sub(c,a))/den;v=g.cross(g.sub(b,a),g.sub(p,a))/den;return heights[0]+u*(heights[1]-heights[0])+v*(heights[2]-heights[0])
    gx=((heights[1]-heights[0])*(c[1]-a[1])-(heights[2]-heights[0])*(b[1]-a[1]))/den
    gz=((b[0]-a[0])*(heights[2]-heights[0])-(c[0]-a[0])*(heights[1]-heights[0]))/den
    owned=[]
    for index in sorted(set(indices),key=lambda i:0 if owners[i].get('bridge_water') else 1):
     owner=owners[index];poly=g.convex_intersection(base,owner['poly'])
     if g.area(poly)<1e-9:continue
     parts=subtract([poly],owned)
     before=sum(g.area(p) for p in parts)
     parts=subtract(parts,[p for wid,p in local_water if wid!=owner.get('bridge_water')]);removed_water+=before-sum(g.area(p) for p in parts)
     before=sum(g.area(p) for p in parts);parts=subtract(parts,local_bodies);removed_body+=before-sum(g.area(p) for p in parts)
     owned+=parts
     for poly in parts:
      area+=g.area(poly);maximum_gradient=max(maximum_gradient,math.hypot(gx,gz))
      for i in range(1,len(poly)-1):
       t=[poly[0],poly[i],poly[i+1]]
       if g.area(t)<1e-9:continue
       # XZ counter-clockwise order is Godot clockwise viewed from above.
       triangles.append([[p[0],interpolate(p),p[1]] for p in g.ccw(t)])
       center=[sum(p[k] for p in t)/3 for k in (0,1)];maximum_error=max(maximum_error,abs(interpolate(center)-height_fn(*center)))
  resource=HERE/'geometry'/(id+'.json');write(resource,{'schema':'riverstone.concept_city.finite_collision_proxy.v1','source_plan_sha256':hashes['plan'],'terrain_contract_sha256':hashes['contract'],'grid_pitch_m':PITCH,'finite_ownership':owners,'triangles':triangles})
  asset=id;assets[asset]={'render_path':str(resource.relative_to(ROOT)),'render_sha256':digest(resource),'collision_format':'source_grade_proxy_triangles'}
  placement='PROXY:'+id;placements[placement]={'id':placement,'asset_key':asset,'position_m':[0,0,0],'yaw_deg':0,'category':'finite_source_road_bridge_candidate','collision_layer':1}
  geometry_audit.append({'id':id,'triangles':len(triangles),'area_m2':area,'grid_pitch_m':PITCH,'maximum_sampled_triangle_center_source_error_m':maximum_error,'maximum_actual_triangle_gradient':maximum_gradient,'removed_water_area_sum_m2':removed_water,'removed_body_area_sum_m2':removed_body,'water_domains_preserved_except_named_bridge_spans':True})
  print('PREPARED_GEOMETRY',id,len(triangles),flush=True)
  return placement

 def owners_for(points,road_ids):
  owners=[]
  for rid in sorted(set(road_ids)):
   road=road_index[rid]
   for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):
    if g.line_distance([a,b],points)[0]>road['width_m']/2+1:continue
    # Clip each source road segment to finite route-local rectangles to avoid
    # loading unused distant portions of a long road.
    for p,q in zip(points,points[1:]):
     local=g.ribbon(p,q,road['width_m']+4);poly=g.convex_intersection(g.ribbon(a,b,road['width_m']),local)
     if g.area(poly)>1e-7:owners.append({'id':rid,'poly':poly})
  for bridge in plan['bridges']:
   if bridge['road_id'] not in road_ids:continue
   a,b=bridge['deck_polyline_xz_m']
   if g.line_distance([a,b],points)[0]>bridge['width_m']/2+1:continue
   owners.append({'id':bridge['id'],'poly':g.ribbon(a,b,bridge['width_m']),'bridge_water':'MAIN_RIVER' if bridge['role']=='main_river_bridge' else 'SERVICE_CANAL'})
  return owners

 def add_route(id,points,road_ids,placement,kind='public_route',expected=None,contact=None):
  xyz=[[p[0],author.road_height_at(road_ids[0] if road_ids else '',*p),p[1]] for p in points]
  nearby=[b['id'] for b in plan['buildings'] if g.point_line_distance(b['position_xz_m'],points)[0]<max(b['width_m'],b['depth_m'])/2+5]
  r={'id':id,'kind':kind,'points':xyz,'length_m':sum(math.dist(a,b) for a,b in zip(xyz,xyz[1:])),'source_road_ids':sorted(set(road_ids)),'placement_ids':[placement],'building_ids':nearby if kind=='public_route' else [],'test_scope':'finite optional continuous source-grade road/bridge collider with water/body holes; conservative nearby body envelopes; no production controller claim','minimum_allowed_feet_y_m':min(p[1] for p in xyz)-4}
  if expected:r['expected_failure']=expected
  if contact:r['expected_contact_id']=contact
  routes.append(r)

 for bridge in plan['bridges']:
  a,b=bridge['deck_polyline_xz_m'];length=math.dist(a,b);d=[(b[k]-a[k])/length for k in (0,1)];points=[[a[k]-d[k]*5 for k in (0,1)],a,b,[b[k]+d[k]*5 for k in (0,1)]]
  # The long oblique monastery deck extends across a road vertex; project the
  # endpoints to the declared road and retain all intervening source vertices.
  road=road_index[bridge['road_id']];stations=[];total=0
  for start,end in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):
   for index,point in enumerate((points[0],points[-1])):
    distance,q,t=g.closest_point(point,start,end);stations.append((index,distance,total+t*math.dist(start,end),q))
   total+=math.dist(start,end)
  ends=[min((row for row in stations if row[0]==i),key=lambda row:row[1]) for i in (0,1)];lo,hi=sorted([row[2] for row in ends]);walk=[];total=0
  walk.append(min(ends,key=lambda row:row[2])[3])
  for vertex,next_vertex in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):
   total+=math.dist(vertex,next_vertex)
   if lo<total<hi:walk.append(next_vertex)
  walk.append(max(ends,key=lambda row:row[2])[3]);points=walk
  placement=make_mesh(bridge['id'],owners_for(points,[bridge['road_id']]),points,lambda x,z:author.road_height_at(bridge['road_id'],x,z))
  add_route(bridge['id']+'_FORWARD',points,[bridge['road_id']],placement);add_route(bridge['id']+'_REVERSE',list(reversed(points)),[bridge['road_id']],placement)
 if '--bridges-only' not in sys.argv:
  stops=[[-165,-72],[30,0],[210,110],[120,390]];graph=road_graph(plan['roads'],stops);points=[];ids=[]
  for a,b in zip(stops,stops[1:]):
   part,road_ids=shortest(graph,a,b);points+=part if not points else part[1:];ids+=road_ids
  placement=make_mesh('NOBLE_MARKET_POOR_PORT',owners_for(points,ids),points,lambda x,z:author.road_height_at('',x,z))
  add_route('NOBLE_MARKET_POOR_PORT',points,ids,placement);add_route('PORT_POOR_MARKET_NOBLE',list(reversed(points)),ids,placement)
  flat=[[-20,0],[20,0]];placement=make_mesh('FLAT_MARKET_BASELINE',owners_for(flat,['R_MARKET_N']),flat,lambda x,z:author.road_height_at('R_MARKET_N',x,z));add_route('FLAT_MARKET_BASELINE',flat,['R_MARKET_N'],placement)
 water_points=[[-400,415],[-400,427]];placement=make_mesh('UNBRIDGED_RIVER_CONTROL',[{'id':'finite_source_river_bank_control','poly':[[-404,410],[-396,410],[-396,431],[-404,431]]}],water_points,author.dry_height_at)
 add_route('NEGATIVE_UNBRIDGED_RIVER',water_points,[],placement,'negative_control','ground_lost')
 for name,label in [('proxy_actual_step025','NEGATIVE_ACTUAL_0P25_RISER'),('proxy_actual_wall','NEGATIVE_ACTUAL_SOLID_WALL')]:
  render=ROOT/'world_city/runtime_city/traversal_r2/controls'/(name+'.render.json');master=render.with_name(name+'.master.json');assets[name]={'render_path':str(render.relative_to(ROOT)),'render_sha256':digest(render)};pid='CONTROL:'+name;placements[pid]={'id':pid,'asset_key':name,'position_m':[0,0,0],'yaw_deg':0,'category':'isolated_actual_common_compiled_control','collision_layer':1}
  add_route(label,[[-1,0],[1,0]],[],pid,'negative_control','blocked',pid);routes[-1]['points']=[[-1,0,0],[1,0,0]];routes[-1]['length_m']=2;routes[-1]['minimum_allowed_feet_y_m']=-4;routes[-1]['test_scope']='isolated frozen common-compiled actual obstacle; not city geometry';source_paths[name+'_master']=master;raw[name+'_master']=master.read_bytes()
 snapshots={}
 for k,p in source_paths.items():
  data=raw[k];sha=hashlib.sha256(data).hexdigest();snapshot=HERE/'sources'/(k+'_'+sha+p.suffix);snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(data);snapshots[k]={'path':str(snapshot),'sha256':sha,'original_path':str(p)}
 if any(p.read_bytes()!=raw[k] for k,p in source_paths.items()):raise RuntimeError('source changed during preparation')
 implementations=[HERE/'prepare.py',HERE/'Traversal.gd',HERE/'Traversal.tscn',HERE/'project.godot',HERE/'run.sh',HERE/'RenderData.gd',CITY/'validation/geometry.py']
 result={'schema':'riverstone.concept_city_v3.prepared_capsule.v1','repo_root':str(ROOT),'sources':snapshots,'implementation_hashes':{str(p.relative_to(ROOT)):digest(p) for p in implementations},'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,
 'coverage':{'bridges':4,'bridge_directions':8,'representative_routes':0 if '--bridges-only' in sys.argv else 2,'flat_baseline':0 if '--bridges-only' in sys.argv else 1,'negative_controls':3,'all_doors_tested':False,'stairs_tested':False,'geometry_audit':geometry_audit},
 'assumptions':['Optional finite source-grade collision adapter, not common voxel visual completion.','Road and bridge cells share a 0.5 m global grid; heights linearly interpolate source samples; measured approximation error and triangle grades are reported.','Water holes are exact finite source polygons; only named authored bridge spans may cover them.','Building body footprints are removed; nearby conservative source envelopes remain obstacles.','Source stair risers, 43+4 steep approaches and 1040 tight-frontage cases are not certified or replaced by ramps.','Frozen common-compiled wall and .25m riser controls retain actual triangles.','No within-route teleport or automatic step-up; no production controller or NPC guarantee.']}
 output=HERE/'prepared.json';write(output,result);write(HERE/'evidence/preparation.json',{'sources':snapshots,'coverage':result['coverage'],'routes':[{'id':r['id'],'length_m':r['length_m'],'source_road_ids':r['source_road_ids']} for r in routes]});print('PREPARED',output,len(routes),flush=True)

if __name__=='__main__':prepare()
