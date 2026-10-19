"""Visual-QA correction overlay; frozen R2 source and terrain are never edited."""
from __future__ import annotations
import argparse,copy,hashlib,heapq,json,math,random,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks.placement import (_SpatialIndex,positive_area_overlap,polygon_area,convex_polygon_contains,point_in_convex_polygon,road_ribbon,transformed_aabb_xz_m,convex_intersection,polygon_covered_by_union)
from world_city.runtime_city.urban_fabric.author import rect,center,unit,add,mix,digest,yaw_basis,fit_rect
from world_city.runtime_city.urban_fabric.revisions.r3.probe import offset
from world_city.runtime_city.infrastructure.author import PALETTE
HERE=Path(__file__).parent
SCHEMA='riverstone.voxel.master.v1'
TREE_FORMS={
 'broad_oak': {'width_m':12,'depth_m':12,'height_m':12,'trunk_height':7,'lobes':[[-2,5,-1,4,6],[2,7,1,3.5,5],[1,5,-2,3.5,5]]},
 'forked_oak': {'width_m':12,'depth_m':10,'height_m':15,'trunk_height':8,'lobes':[[-3,8,0,3,5],[3,7,1,3,6],[0,10,-1,3.5,5]],'forked':True},
 'leaning_ash': {'width_m':10,'depth_m':9,'height_m':14,'trunk_height':9,'lobes':[[-1,7,0,3.5,5],[1,9,1,3.5,5],[2,7,-1,3,5]]},
 'low_hazel': {'width_m':8,'depth_m':8,'height_m':8,'trunk_height':4,'lobes':[[-1.5,2,0,2.5,5],[1.5,3,1,2.5,5],[0,2,-1.5,2.5,5]],'forked':True},
 'tall_birch': {'width_m':8,'depth_m':8,'height_m':17,'trunk_height':12,'lobes':[[-1,9,0,2.5,4],[1,11,-1,2.5,4],[0,13,1,2.5,4]],'pale_trunk':True},
 'spreading_elm': {'width_m':14,'depth_m':10,'height_m':11,'trunk_height':6,'lobes':[[-3,5,0,4,5],[3,5,0,4,6],[0,6,1,3.5,5]],'forked':True},
}


def master_bounds(spec):
 k=spec['kind']
 if k=='forest_tree':
  t=TREE_FORMS[spec['form']];return t['width_m'],t['depth_m'],t['height_m']
 return spec.get('width_m',1),spec.get('depth_m',1),spec.get('height_m',1)


def make_master(spec):
 """Finite reusable standard-common source shapes, safe at declared .5/1 m pitch."""
 k=spec['kind'];w,d,h=master_bounds(spec);ops=[];palette=dict(PALETTE)
 house=json.loads((ROOT/'voxel_character/common/assets/house/master.json').read_text())['materials'];palette.update({p:house[p] for p in ('timber','timber_light','timber_dark','stone','stone_light','stone_dark')})
 def op(shape,mat,feature,translate=None):
  o={'id':f'op_{len(ops):03d}','part':'solid','action':'paint','material':mat,'shape':shape,'feature':feature}
  if translate:o['transform']={'translation':translate}
  ops.append(o)
 def box(lo,hi,mat,feature):op({'kind':'box','min':lo,'max':hi},mat,feature)
 def lobe(x,y,z,r,height,mat='grass'):
  # Rounded, asymmetrical clusters of revolved broad crowns, not stacked pyramids.
  profile=[[0,0],[r*.55,0],[r*.86,height*.18],[r,height*.45],[r*.84,height*.72],[r*.45,height*.94],[0,height]]
  op({'kind':'lathe','profile':profile},mat,'rounded_canopy_lobe',[x,y,z])
 if k=='wall_panel':
  box([-w/2,-.5,-.5],[w/2,h-.5,.5],'stone','continuous_estate_wall')
  box([-w/2,h-.5,-.5],[w/2,h,.5],'stone_light','full_width_coping')
 elif k=='corner_post':
  box([-.5,-1,-.5],[.5,h,.5],'stone_light','joined_wall_corner')
 elif k=='gate_post':
  box([-w/2,-1,-d/2],[w/2,h,d/2],'stone','intentional_gate_pier')
  box([-w/2,h-.5,-d/2],[w/2,h,d/2],'stone_light','gate_pier_cap')
 elif k=='court_paving':
  box([-w/2,-.5,-d/2],[w/2,0,d/2],'stone_dark','continuous_working_court')
 elif k=='garden_bed':
  box([-w/2,-.5,-d/2],[w/2,.5,d/2],'stone','stepped_garden_bed_enclosure')
  box([-w/2+.5,.5,-d/2+.5],[w/2-.5,1.5,d/2-.5],'grass','productive_garden_bed')
 elif k=='formal_garden':
  box([-w/2,-.5,-d/2],[w/2,0,d/2],'stone_light','garden_paths')
  # Four broad clearly readable planting beds; central crossing remains flush.
  for sx in (-1,1):
   for sz in (-1,1):
    x0,x1=(-w/2+.5,-.75) if sx<0 else (.75,w/2-.5)
    z0,z1=(-d/2+.5,-.75) if sz<0 else (.75,d/2-.5)
    box([x0,0,z0],[x1,.5,z1],'stone','raised_bed_boundary')
    box([x0+.5,.5,z0+.5],[x1-.5,1.5,z1-.5],'grass','coherent_productive_bed')
 elif k=='forest_tree':
  t=TREE_FORMS[spec['form']];mat='stone_light' if t.get('pale_trunk') else 'timber_dark'
  box([-1,-1,-1],[1,t['trunk_height'],1],mat,'rooted_trunk')
  if t.get('forked'):
   for sign in (-1,1):op({'kind':'tube','points':[[0,t['trunk_height']*.5,0],[sign*2,t['trunk_height']*.9,0],[sign*3,t['trunk_height']+1,0]],'radius':.9,'minimum_radius_cells':1},mat,'forked_structural_branch')
  for values in t['lobes']:lobe(*values)
 elif k=='understory':
  lobe(-.5,-.25,0,1.5,2.5);lobe(.7,0,.5,1.3,2)
 else:raise ValueError(k)
 return {'schema':SCHEMA,'id':'uf_r3_'+k+'_'+digest(spec)[:14],'revision':3,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':palette,
         'components':[{'id':'module','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'module_0','component':'module'}],
         'metadata':{'authoring':'standard_common_master_only','spec':copy.deepcopy(spec),'sampling_contract':'walls .5 m; tree trunks/branches/crowns >= 1 m resources','no_scaled_tree_variants':True}}


class World:
 def __init__(self,scene):
  self.index=_SpatialIndex(32);self.items={}
  for i in scene['instances']:self.add(i['id'],transformed_aabb_xz_m(i['local_bounds'],i['position_m'],i['yaw_rad']),'building')
  n={x['id']:[x['position_m'][0],x['position_m'][2]] for x in scene['road_nodes']}
  for r in scene['roads']:self.add(r['id'],road_ribbon(n[r['from_node']],n[r['to_node']],r['width_m']),'road')
  river=scene['river_reservation']
  for j,(a,b) in enumerate(zip(river['centerline_xz_m'],river['centerline_xz_m'][1:])):self.add('river:'+str(j),road_ribbon(a,b,river['width_candidate_m']+2),'river')
 def add(self,k,poly,kind):self.items[k]={'polygon':poly,'kind':kind};self.index.add(k,poly)
 def hits(self,p,kinds=('building','road','river'),ignore=()):
  return [k for k in self.index.candidates(p) if k not in ignore and self.items[k]['kind'] in kinds and positive_area_overlap(p,self.items[k]['polygon'],.003)]


def poly_offset_variable(poly,values):
 lines=[]
 for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  u=unit(a,b);lines.append((add(a,[-u[1],u[0]],values[i]),u))
 out=[]
 for i,(p,u) in enumerate(lines):
  q,v=lines[i-1];den=u[0]*v[1]-u[1]*v[0];qp=[q[0]-p[0],q[1]-p[1]];t=(qp[0]*v[1]-qp[1]*v[0])/den;out.append(add(p,u,t))
 return out


def projected(p,a,b):
 u=unit(a,b);length=math.dist(a,b);t=max(0,min(length,(p[0]-a[0])*u[0]+(p[1]-a[1])*u[1]));return add(a,u,t),t


def route_inside(start,end,region,buildings,width=1.4,extra_allowed=()):
 """Dijkstra visibility graph with full swept ribbon constrained inside the ring."""
 nodes=[start,end]
 for p in buildings:
  for v in offset(p,-(width/2+.25)):nodes.append(v)
 nodes.extend(offset(region,1.1))
 def clear(a,b):
  if math.dist(a,b)<.01:return False
  p=road_ribbon(a,b,width)
  return polygon_covered_by_union(p,[region]+list(extra_allowed),.025) and not any(positive_area_overlap(p,q,.003) for q in buildings)
 edges=defaultdict(list)
 for i,a in enumerate(nodes):
  for j,b in enumerate(nodes[:i]):
   if clear(a,b):dist=math.dist(a,b);edges[i].append((j,dist));edges[j].append((i,dist))
 queue=[(0,0)];cost={0:0};prev={}
 while queue:
  c,i=heapq.heappop(queue)
  if c>cost[i]+1e-8:continue
  if i==1:
   path=[1]
   while path[-1]!=0:path.append(prev[path[-1]])
   return [nodes[n] for n in reversed(path)]
  for j,d in edges[i]:
   nc=c+d
   if nc<cost.get(j,math.inf):cost[j]=nc;prev[j]=i;heapq.heappush(queue,(nc,j))
 return None


def outside_route(start,end,world_ctx,ring,width):
 # Wall/corner solid thickness is part of the obstacle, not only its centerline.
 ring=offset(ring,-.75)
 bounds=rect(center([start,end]),abs(start[0]-end[0])+50,abs(start[1]-end[1])+50)
 polys=[world_ctx.items[k]['polygon'] for k in world_ctx.index.candidates(bounds) if world_ctx.items[k]['kind']=='building']+[ring]
 nodes=[start,end]
 for p in polys:nodes.extend(offset(p,-(width/2+.3)))
 def clear(a,b):
  if math.dist(a,b)<.01:return False
  poly=road_ribbon(a,b,width)
  return not world_ctx.hits(poly,kinds=('building',)) and not positive_area_overlap(poly,ring,.002)
 edges=defaultdict(list)
 for i,a in enumerate(nodes):
  for j,b in enumerate(nodes[:i]):
   if clear(a,b):d=math.dist(a,b);edges[i].append((j,d));edges[j].append((i,d))
 queue=[(0,0)];cost={0:0};prev={}
 while queue:
  c,i=heapq.heappop(queue)
  if c>cost[i]+1e-8:continue
  if i==1:
   path=[1]
   while path[-1]!=0:path.append(prev[path[-1]])
   return [nodes[n] for n in reversed(path)]
  for j,d in edges[i]:
   nc=c+d
   if nc<cost.get(j,math.inf):cost[j]=nc;prev[j]=i;heapq.heappush(queue,(nc,j))
 return None


def build_revision_overlay(scene,r2_fabric,plan=None):
 world_ctx=World(scene);instances={i['id']:i for i in scene['instances']};by_prop={p['id']:p for p in r2_fabric['properties']}
 placements=[];specs={};access=[];properties=[];errors=[];removed=[];replaced_access=[]
 def place(pid,spec,pos,yaw=0,category=None,property_id=None,collision=True,overlap_group=None):
  w,d,h=master_bounds(spec);poly=rect(pos,w,d,yaw);key='uf_r3_'+spec['kind']+'_'+digest(spec)[:14];specs.setdefault(key,spec)
  pitch=1 if spec['kind']=='forest_tree' else .5
  root=rect(pos,2,2,yaw) if spec['kind']=='forest_tree' else poly
  p={'id':pid,'asset_key':key,'master_key':key,'spec':spec,'position_m':[pos[0],0,pos[1]],'yaw_rad':yaw,'yaw_deg':math.degrees(yaw),'transform':{'translation':[pos[0],0,pos[1]],'basis':yaw_basis(yaw)},
     'category':category or spec['kind'],'property_id':property_id,'requested_pitch_m':pitch,'footprint_xz_m':poly,'clearance_footprint_xz_m':poly,
     'collision_enabled':collision,'collision_policy':'trunk_root_only' if spec['kind']=='forest_tree' else 'solid' if collision else 'walkable_flush_or_soft_understory',
     'collision_footprint_xz_m':root if spec['kind']=='forest_tree' else poly,'intentional_overlap_group':overlap_group,
     'local_bounds':{'min':[-w/2,-1,-d/2],'max':[w/2,h,d/2]},'stream_chunk_xz':[math.floor(pos[0]/64),math.floor(pos[1]/64)],
     'ground_anchor':{'policy':'project_y_only_sample_root_or_support_points','sample_center_xz_m':pos,'support_points_xz_m':root,'support_footprint_kind':'trunk_root' if spec['kind']=='forest_tree' else 'short_module_base','datum_y_m':0,'preserve_xz':True,'footing_embed_m':.5 if spec['kind'] in ('wall_panel','garden_bed','court_paving','formal_garden') else 1,'maximum_support_height_delta_m':.75,'exceedance_action':'author_steps_or_report_do_not_scale_or_float'}}
  placements.append(p);return p
 def reserve(aid,path,width,owner,kind):
  if not path:return None
  r={'id':aid,'owner_id':owner,'kind':kind,'polyline_xz_m':path,'width_m':width,'ribbon_polygons_xz_m':[road_ribbon(a,b,width) for a,b in zip(path,path[1:]) if math.dist(a,b)>.01]};access.append(r);return r
 # Boundary is authored as one topological ring with explicit gaps before any modules exist.
 for propid in ('UF_ESTATE_01','UF_ESTATE_02','UF_ESTATE_03'):
  prop=by_prop[propid];region=prop['footprint_xz_m'];builds=[instances[k] for k in prop['source_building_ids']];bpolys=[world_ctx.items[b['id']]['polygon'] for b in builds]
  insets=[.25]*len(region)
  if propid=='UF_ESTATE_03':insets=[.25,.55,.55,.55,.25,.25,.25,.25]
  ring=poly_offset_variable(region,insets);inner=offset(ring,.7)
  # Deliberate residence, service and narrow lodge postern gates; no incidental holes.
  gates=[]
  for gi,b in enumerate(builds):
   road=b['entrance']['road_connection_m'];roadpos=[road[0],road[2]]
   yaw=b['yaw_rad'];front=[math.sin(yaw),math.cos(yaw)];pos=[b['position_m'][0],b['position_m'][2]];threshold=add(pos,front,b['local_bounds']['max'][2])
   options=[]
   for ei,(a,z) in enumerate(zip(ring,ring[1:]+ring[:1])):
    q,t=projected(threshold,a,z);length=math.dist(a,z);width=3.5 if gi==0 else 3.0 if gi==1 else 2.0
    if length<width+2:continue
    t=max(width/2+.7,min(length-width/2-.7,t));q=add(a,unit(a,z),t)
    if any(ei==g['edge_index'] and abs(t-g['center_distance_m'])<(width+g['width_m'])/2+2 for g in gates):continue
    options.append((math.dist(q,threshold)+.1*math.dist(q,roadpos),ei,q,t,width,roadpos))
   if not options:errors.append({'property_id':propid,'error':'no_gate_candidate'});continue
   _,ei,q,t,width,roadpos=min(options);a,z=ring[ei],ring[(ei+1)%len(ring)];u=unit(a,z);n=[-u[1],u[0]]
   gates.append({'id':propid+':gate:'+str(gi),'edge_index':ei,'center_xz_m':q,'center_distance_m':t,'width_m':width,'clear_interval_m':[t-width/2,t+width/2],'inside_point_xz_m':add(q,n,1.7),'outward_point_xz_m':add(q,n,-1.4),'passage_polygon_xz_m':road_ribbon(add(q,n,2.5),add(q,n,-1.5),width),'outside_road_connection_xz_m':roadpos,'building_id':b['id']})
  own_access=[]
  for b in builds:
   route_width=1.2 if b['id']=='D04-B122' else 1.8
   ent=b['entrance'];local=ent.get('local_position_m',[0,0,b['local_bounds']['max'][2]])
   yaw=b['yaw_rad'];front=[math.sin(yaw),math.cos(yaw)];right=[math.cos(yaw),-math.sin(yaw)];pos=[b['position_m'][0],b['position_m'][2]]
   threshold=add(add(pos,right,local[0]),front,b['local_bounds']['max'][2])
   options=[]
   for g in gates:
    for lead in (.3,.5,.75,1.0):
     start=add(threshold,front,lead)
     if world_ctx.hits(road_ribbon(threshold,start,route_width),kinds=('building',)):continue
     path=route_inside(start,g['center_xz_m'],inner,bpolys,route_width,[g['passage_polygon_xz_m']])
     if path:
      path=[threshold]+path
      options.append((sum(math.dist(a,z) for a,z in zip(path,path[1:])),g,path))
   if not options:
    errors.append({'property_id':propid,'building_id':b['id'],'error':'no_inside_gate_route'});continue
   _,gate,path=min(options,key=lambda q:q[0]);outside=outside_route(gate['outward_point_xz_m'],gate['outside_road_connection_xz_m'],world_ctx,ring,route_width)
   if not outside:errors.append({'property_id':propid,'building_id':b['id'],'error':'no_exterior_gate_road_route'});continue
   path=path+[gate['outward_point_xz_m']]+outside[1:]
   a=reserve('R3:'+b['id']+':estate_entry',path,route_width,b['id'],'estate_to_intentional_gate');a['gate_id']=gate['id'];a['access_mode']='pedestrian_and_horse_lead_constrained_turn' if route_width<1.8 else 'pedestrian_and_service';a['road_ids']=world_ctx.hits(rect(path[-1],.1,.1),kinds=('road',));own_access.append(a)
  # Exact panel runs cover the whole complement of gate intervals. Nothing is dropped.
  wall_ids=[];runs=[]
  for ei,(a,z) in enumerate(zip(ring,ring[1:]+ring[:1])):
   length=math.dist(a,z);u=unit(a,z);yaw=math.atan2(-u[1],u[0]);cuts=sorted(g['clear_interval_m'] for g in gates if g['edge_index']==ei);cursor=0
   for lo,hi in cuts+[[length,length]]:
    if lo-cursor>.05:
     start,end=cursor,lo;segments=[];at=start
     while end-at>1e-7:
      remaining=end-at;size=next((v for v in (6,4,2,1) if v<=remaining+1e-7),1)
      # The last cached metre overlaps inward, ending exactly on the intended endpoint.
      c=end-size/2 if remaining<size else at+size/2
      p=place(f'R3:{propid}:wall:{ei}:{len(segments)}:{round(start,2)}',{'kind':'wall_panel','width_m':size,'depth_m':1,'height_m':2.5},add(a,u,c),yaw,'estate_boundary',propid,overlap_group=propid+':boundary')
      segments.append(p['id']);wall_ids.append(p['id']);at+=min(size,remaining)
     runs.append({'edge_index':ei,'interval_m':[start,end],'placement_ids':segments})
    cursor=hi
  for j,v in enumerate(ring):
   p=place(f'R3:{propid}:corner:{j}',{'kind':'corner_post','width_m':1,'depth_m':1,'height_m':3},v,category='estate_boundary',property_id=propid,overlap_group=propid+':boundary');wall_ids.append(p['id'])
  # Gate piers sit just outside clear opening ends, their width never steals the declared gap.
  for g in gates:
   a,z=ring[g['edge_index']],ring[(g['edge_index']+1)%len(ring)];u=unit(a,z)
   for side in (-1,1):
    q=add(g['center_xz_m'],u,side*(g['width_m']/2+.5));p=place(g['id']+':pier:'+str(side),{'kind':'gate_post','width_m':1,'depth_m':1,'height_m':3.5},q,math.atan2(-u[1],u[0]),'estate_gate',propid,overlap_group=propid+':boundary');wall_ids.append(p['id'])
  # One legible garden composition instead of scattered tiny planters.
  forbidden=bpolys+[q for a in own_access for q in a['ribbon_polygons_xz_m']]
  main=instances[prop['retained_primary_id']];yaw=main['yaw_rad'];front=[math.sin(yaw),math.cos(yaw)]
  desired=add([main['position_m'][0],main['position_m'][2]],front,-(main['local_bounds']['max'][2]+7))
  garden=fit_rect(inner,desired,[12,10,8],[8,6],yaw,forbidden,.5)
  garden_id=None;garden_ids=[]
  if garden:
   pos,poly,w,d=garden
   if propid=='UF_ESTATE_03':
    # Same coherent quartered garden, subdivided only for per-piece grade anchors.
    right=[math.cos(yaw),-math.sin(yaw)];front=[math.sin(yaw),math.cos(yaw)]
    def at(x,z):return add(add(pos,right,x),front,z)
    for sx in (-1,1):
     for sz in (-1,1):
      p=place(f'R3:{propid}:garden:bed:{sx}:{sz}',{'kind':'garden_bed','width_m':w/2-1,'depth_m':d/2-1,'height_m':1.5},at(sx*(w/4+.5),sz*(d/4+.5)),yaw,'estate_formal_garden',propid);garden_ids.append(p['id'])
    for sz in (-1,1):
     p=place(f'R3:{propid}:garden:path:z:{sz}',{'kind':'court_paving','width_m':2,'depth_m':d/2,'height_m':.5},at(0,sz*d/4),yaw,'estate_garden_path',propid,collision=False);garden_ids.append(p['id'])
    for sx in (-1,1):
     p=place(f'R3:{propid}:garden:path:x:{sx}',{'kind':'court_paving','width_m':w/2-1,'depth_m':2,'height_m':.5},at(sx*(w/4+.5),0),yaw,'estate_garden_path',propid,collision=False);garden_ids.append(p['id'])
   else:
    p=place('R3:'+propid+':garden',{'kind':'formal_garden','width_m':w,'depth_m':d,'height_m':1.5},pos,yaw,'estate_formal_garden',propid);garden_ids.append(p['id'])
   garden_id=garden_ids[0];forbidden.append(poly)
  else:errors.append({'property_id':propid,'error':'no_coherent_garden_fit'})
  # Joined floor tiles make the service court visibly distinct without blocking doors.
  c=center(region);pave_ids=[]
  for x in range(math.floor(min(v[0] for v in inner)/4)*4,math.ceil(max(v[0] for v in inner)/4)*4,4):
   for z in range(math.floor(min(v[1] for v in inner)/4)*4,math.ceil(max(v[1] for v in inner)/4)*4,4):
    q=[x+2,z+2];poly=rect(q,4,4)
    if not convex_polygon_contains(inner,poly,0) or any(positive_area_overlap(poly,p,.003) for p in bpolys+([garden[1]] if garden else [])):continue
    p=place(f'R3:{propid}:court:{x}:{z}',{'kind':'court_paving','width_m':4,'depth_m':4,'height_m':.5},q,category='estate_service_court',property_id=propid,collision=False);pave_ids.append(p['id'])
  per=sum(math.dist(a,b) for a,b in zip(ring,ring[1:]+ring[:1]));walllen=sum(r['interval_m'][1]-r['interval_m'][0] for r in runs)
  properties.append({'id':propid,'source_property_id':propid,'unchanged_building_ids':prop['source_building_ids'],'footprint_xz_m':region,'boundary_centerline_xz_m':ring,'wall_runs':runs,'gates':gates,'wall_placement_ids':wall_ids,'garden_placement_id':garden_id,'garden_placement_ids':garden_ids,'garden_footprint_xz_m':garden[1] if garden else None,'court_placement_ids':pave_ids,'boundary_perimeter_m':per,'designed_wall_length_m':walllen,'intentional_gate_length_m':sum(g['width_m'] for g in gates),'unexplained_gap_m':per-walllen-sum(g['width_m'] for g in gates),'paved_service_court_area_m2':16*len(pave_ids),'coherent_garden_area_m2':garden[2]*garden[3] if garden else 0})
  removed.extend(p['id'] for p in r2_fabric['placements'] if p.get('property_id')==propid)
  replaced_access.extend(a['id'] for a in r2_fabric['access_reservations'] if a.get('owner_id') in prop['source_building_ids'] or a.get('owner_id')==propid)
 # Forest: seeded cluster centres, an explicit winding clearing, irregular Poisson darts.
 forest=[]
 for old in r2_fabric['vegetation_land_use']:
  if old['land_use']!='outside_wall_woodland':continue
  patch=old['footprint_xz_m'];pid=old['id'];rng=random.Random(int(digest(pid+'r3_cluster_forest')[:16],16));xs=[p[0] for p in patch];zs=[p[1] for p in patch];xmin,xmax,zmin,zmax=min(xs),max(xs),min(zs),max(zs)
  area=polygon_area(patch);target=int(area/120);centres=[]
  for j in range(max(5,int(area/4000))):centres.append([rng.uniform(xmin+12,xmax-12),rng.uniform(zmin+12,zmax-12),rng.uniform(15,27),rng.uniform(16,32)])
  taken=[];trunk_index=_SpatialIndex(8);accepted=[];attempts=0;forms=list(TREE_FORMS)
  def clearing(p):
   # A curved ground gap breaks each patch without making a grid road through it.
   mid=xmin+(xmax-xmin)*.52+math.sin((p[1]-zmin)/(zmax-zmin)*math.pi*2)*min(16,(xmax-xmin)*.14)
   return abs(p[0]-mid)<3.5 and zmin+15<p[1]<zmax-15
  while len(taken)<target and attempts<target*100:
   attempts+=1;c=rng.choice(centres)
   if rng.random()<.8:p=[rng.gauss(c[0],c[2]),rng.gauss(c[1],c[3])]
   else:p=[rng.uniform(xmin,xmax),rng.uniform(zmin,zmax)]
   if clearing(p):continue
   form=forms[rng.randrange(len(forms))];spec={'kind':'forest_tree','form':form};w,d,h=master_bounds(spec);yaw=rng.uniform(-math.pi,math.pi);poly=rect(p,w,d,yaw)
   if not convex_polygon_contains(patch,poly,0) or world_ctx.hits(poly):continue
   probe=rect(p,10,10)
   if any(math.dist(p,taken[int(k)])<4.5 for k in trunk_index.candidates(probe)):continue
   trunk_index.add(str(len(taken)),rect(p,1,1));taken.append(p)
   q=place(f'R3:{pid}:tree:{len(taken)-1:04d}',spec,p,yaw,'outer_woodland_tree',pid,overlap_group=pid+':foliage');accepted.append(q['id'])
  understory=[]
  for j in range(int(len(taken)*.55)):
   p=add(rng.choice(taken),[math.cos(j*2.4),math.sin(j*2.4)],rng.uniform(2.5,5));poly=rect(p,4,4)
   if clearing(p) or not convex_polygon_contains(patch,poly,0) or world_ctx.hits(poly):continue
   q=place(f'R3:{pid}:understory:{j:04d}',{'kind':'understory','width_m':4,'depth_m':4,'height_m':2.5},p,rng.uniform(-math.pi,math.pi),'forest_understory',pid,collision=False,overlap_group=pid+':foliage');understory.append(q['id'])
  removed.extend(old['placement_ids'])
  # Sample projected crown envelopes on a fixed 2 m audit grid; report method honestly.
  next_accepted=[p for p in placements if p['id'] in set(accepted)];polys=[p['footprint_xz_m'] for p in next_accepted];sidx=_SpatialIndex(16)
  for j,poly in enumerate(polys):sidx.add(str(j),poly)
  total=covered=leaf_covered=0;leaf_samples=[]
  for x in range(math.ceil(xmin),math.floor(xmax),2):
   for z in range(math.ceil(zmin),math.floor(zmax),2):
    v=[x+1,z+1]
    if not point_in_convex_polygon(v,patch,0):continue
    total+=1
    candidates=sidx.candidates(rect(v,.1,.1))
    if any(point_in_convex_polygon(v,polys[int(k)],0) for k in candidates):covered+=1
    leaf=False
    for k in candidates:
     tree=next_accepted[int(k)];t=TREE_FORMS[tree['spec']['form']];theta=tree['yaw_rad'];tx,tz=tree['position_m'][0],tree['position_m'][2]
     dx,dz=v[0]-tx,v[1]-tz;lx=math.cos(theta)*dx-math.sin(theta)*dz;lz=math.sin(theta)*dx+math.cos(theta)*dz
     if any((lx-x)**2+(lz-z)**2<=r*r for x,y,z,r,h in t['lobes']):leaf=True;break
    leaf_covered+=leaf;leaf_samples.append((v,leaf))
  core_stats=[]
  for cx,cz,sx,sz in centres:
   samples=[occupied for v,occupied in leaf_samples if abs(v[0]-cx)<=20 and abs(v[1]-cz)<=20]
   if samples:core_stats.append({'center_xz_m':[cx,cz],'size_m':40,'projected_canopy_fraction':sum(samples)/len(samples)})
  nearest=[min(math.dist(a,b) for j,b in enumerate(taken) if j!=i) for i,a in enumerate(taken)];mean=sum(nearest)/len(nearest);cv=(sum((v-mean)**2 for v in nearest)/len(nearest))**.5/mean
  forest.append({'id':pid,'footprint_xz_m':patch,'area_m2':area,'cluster_centres':centres,'tree_placement_ids':accepted,'understory_placement_ids':understory,'tree_forms':dict(Counter(p['spec'].get('form') for p in placements if p['id'] in set(accepted))),'canopy_envelope_union_fraction_2m_grid':covered/total,'projected_rounded_canopy_union_fraction_2m_grid':leaf_covered/total,'wooded_core_windows':core_stats,'canopy_measurement_note':'2 m sampled conservative crown-envelope union; not exact leaf projection','nearest_trunk_distance_mean_m':mean,'nearest_trunk_distance_cv':cv,'minimum_trunk_spacing_m':4.5,'distribution':'seeded_irregular_cluster_mixture_with_winding_clearing_no_planting_grid'})
 result={'schema':'riverstone.city.urban_fabric.overlay.v1','revision':'visual_qa_r3','base_scene_revision':scene['revision'],'base_scene_building_pose_sha256':digest([{k:i[k] for k in ('id','position_m','yaw_rad')} for i in scene['instances']]),'base_fabric_sha256':digest(r2_fabric),'placements':placements,'master_specs':specs,'property_records':properties,'vegetation_land_use':forest,'access_reservations':access,'replacement_ledger':{'remove_placement_ids':sorted(set(removed)),'remove_access_reservation_ids':sorted(set(replaced_access)),'replace_property_ids':[p['id'] for p in properties],'preserve_all_building_poses':True,'preserve_all_roads':True,'terrain_source_edited':False},'author_errors':errors,'compile_budget':{'unique_masters':len(specs),'maximum_candidates_per_master':250000,'maximum_output_cells_per_master':100000,'forest_pitch_m':1,'wall_garden_ground_pitch_m':.5,'no_whole_city_compile':True},'limitations':['Source geometry plus small-master sampling tests only; actual R3 visual QA remains required.','Tree canopy overlap is intentional; trunk/root footprints remain separated.','Main/source terrain remains frozen; root/support anchors require Y projection.','D04-B122 stable retains a 1.2 m pedestrian/horse-lead route at its constrained fixed-envelope turn; no wagon access is claimed there. Other estate routes are 1.8 m.']}
 result['entrance_route_overrides']=[{'building_id':a['owner_id'],'access_reservation_id':a['id'],'access_polyline_xz_m':a['polyline_xz_m'],'width_m':a['width_m'],'road_ids':a['road_ids'],'gate_id':a['gate_id']} for a in access]
 result['checks']=validate_overlay(result,scene,r2_fabric);return result


def validate_overlay(data,scene,r2_fabric):
 """Independent source checks; never waive an overlap by deleting a wall panel."""
 errors=list(data['author_errors']);world_ctx=World(scene);props={p['id']:p for p in data['property_records']};byid={p['id']:p for p in data['placements']}
 if len(byid)!=len(data['placements']):errors.append({'check':'duplicate_placement_id'})
 solids=[p for p in data['placements'] if p['category'] in ('estate_boundary','estate_gate','estate_formal_garden')]
 for p in data['placements']:
  expected=rect([p['position_m'][0],p['position_m'][2]],*master_bounds(p['spec'])[:2],p['yaw_rad'])
  if any(math.dist(a,b)>1e-7 for a,b in zip(expected,p['clearance_footprint_xz_m'])):errors.append({'id':p['id'],'check':'stale_clearance_envelope'})
  if data['master_specs'].get(p['asset_key'])!=p['spec']:errors.append({'id':p['id'],'check':'placement_master_spec_mismatch'})
  hits=world_ctx.hits(expected)
  if hits:errors.append({'id':p['id'],'check':'building_road_river_intersection','targets':hits})
  if not p.get('ground_anchor',{}).get('support_points_xz_m'):errors.append({'id':p['id'],'check':'missing_ground_anchor'})
  if p['spec']['kind']=='wall_panel' and p['spec']['width_m']>6:errors.append({'id':p['id'],'check':'wall_support_span_exceeds_6m'})
 for prop in props.values():
  if abs(prop['unexplained_gap_m'])>.0001:errors.append({'property_id':prop['id'],'check':'unexpected_boundary_gap'})
  if len(prop['gates'])<2 or len(prop['gates'])>3:errors.append({'property_id':prop['id'],'check':'expected_two_or_three_deliberate_gates'})
  if not prop['garden_placement_id']:errors.append({'property_id':prop['id'],'check':'missing_coherent_garden'})
  missing=set(prop['wall_placement_ids']+prop['garden_placement_ids']+prop['court_placement_ids'])-set(byid)
  if missing:errors.append({'property_id':prop['id'],'check':'missing_property_geometry','ids':sorted(missing)})
  # Sample every 0.2 m of wall centerline, excluding only declared clear gates.
  walls=[byid[k]['footprint_xz_m'] for k in prop['wall_placement_ids'] if k in byid]
  ring=prop['boundary_centerline_xz_m']
  for ei,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
   length=math.dist(a,b);u=unit(a,b);gaps=[g['clear_interval_m'] for g in prop['gates'] if g['edge_index']==ei]
   for j in range(math.ceil(length/.2)+1):
    t=min(length,j*.2)
    if any(lo+1e-6<t<hi-1e-6 for lo,hi in gaps):continue
    q=add(a,u,t)
    if not any(point_in_convex_polygon(q,p,.005) for p in walls):errors.append({'property_id':prop['id'],'check':'physical_wall_centerline_gap','edge':ei,'distance_m':t});break
 all_access=[a for a in r2_fabric['access_reservations'] if a['id'] not in data['replacement_ledger']['remove_access_reservation_ids']]+data['access_reservations']
 new_ids={a['id'] for a in data['access_reservations']}
 for a in all_access:
  for poly in a['ribbon_polygons_xz_m']:
   if a['id'] in new_ids:
    hits=world_ctx.hits(poly,kinds=('building',))
    if hits:errors.append({'id':a['id'],'check':'access_building_intersection','targets':hits})
   for p in solids:
    if positive_area_overlap(poly,p['footprint_xz_m'],.005):errors.append({'id':a['id'],'check':'access_estate_geometry_intersection','target':p['id']})
  if a['id'] in new_ids and not world_ctx.hits(rect(a['polyline_xz_m'][-1],.1,.1),kinds=('road',)):errors.append({'id':a['id'],'check':'access_not_connected_to_public_road'})
 for f in data['vegetation_land_use']:
  if len(f['tree_forms'])<5:errors.append({'id':f['id'],'check':'insufficient_tree_geometry_variants'})
  if f['nearest_trunk_distance_cv']<.10:errors.append({'id':f['id'],'check':'forest_spacing_too_uniform'})
  for k in f['tree_placement_ids']+f['understory_placement_ids']:
   if k not in byid:errors.append({'id':k,'check':'missing_forest_geometry'});continue
   if not convex_polygon_contains(f['footprint_xz_m'],byid[k]['footprint_xz_m'],0):errors.append({'id':k,'check':'forest_outside_reserved_patch'})
 kept_solids=[p for p in r2_fabric['placements'] if p['id'] not in data['replacement_ledger']['remove_placement_ids'] and p.get('collision_enabled') and p.get('footprint_xz_m')]
 for p in solids:
  for q in kept_solids:
   if positive_area_overlap(p['footprint_xz_m'],q['footprint_xz_m'],.005):errors.append({'id':p['id'],'check':'retained_prop_solid_intersection','target':q['id']})
 pose_hash=digest([{k:i[k] for k in ('id','position_m','yaw_rad')} for i in scene['instances']])
 if pose_hash!=data['base_scene_building_pose_sha256']:errors.append({'check':'base_building_pose_hash_changed'})
 oldids={p['id'] for p in r2_fabric['placements']}
 if not set(data['replacement_ledger']['remove_placement_ids'])<=oldids:errors.append({'check':'unknown_replacement_ledger_id'})
 return {'valid':not errors,'errors':errors,'retained_access_reservations_checked':len(all_access)-len(new_ids),'new_access_reservations_checked':len(new_ids),'source_building_poses_unchanged':True,'whole_city_compile_performed':False}


def apply_revision_overlay(base_fabric,overlay):
 """Return merged fabric data. Scene pose/terrain application remains the parent caller's job."""
 if digest(base_fabric)!=overlay['base_fabric_sha256']:raise ValueError('Base fabric does not match the checked repaired R2 input')
 if not overlay['checks']['valid']:raise ValueError('Refuse invalid urban-fabric overlay')
 result=copy.deepcopy(base_fabric);ledger=overlay['replacement_ledger'];removed=set(ledger['remove_placement_ids']);removed_access=set(ledger['remove_access_reservation_ids'])
 result['placements']=[p for p in result['placements'] if p['id'] not in removed]+copy.deepcopy(overlay['placements'])
 result['access_reservations']=[a for a in result['access_reservations'] if a['id'] not in removed_access]+copy.deepcopy(overlay['access_reservations'])
 result['master_specs'].update(copy.deepcopy(overlay['master_specs']))
 for key,incoming in [('properties',overlay['property_records']),('vegetation_land_use',overlay['vegetation_land_use'])]:
  updates={p['id']:p for p in incoming};merged=[]
  for old in result[key]:
   p=copy.deepcopy(old)
   if old['id'] in updates:
    p.update(copy.deepcopy(updates[old['id']]))
    if key=='vegetation_land_use':p['placement_ids']=p['tree_placement_ids']+p['understory_placement_ids']
   merged.append(p)
  result[key]=merged
 result['visual_qa_r3_overlay']={'revision':overlay['revision'],'replacement_ledger':copy.deepcopy(ledger),'checks':copy.deepcopy(overlay['checks']),'entrance_route_overrides':copy.deepcopy(overlay['entrance_route_overrides'])}
 return result


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'generated/overlay.json');args=ap.parse_args()
 scene=json.loads((ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json').read_text());fabric=json.loads((ROOT/'world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json').read_text());data=build_revision_overlay(scene,fabric)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False)+'\n')
 summary={'placements':len(data['placements']),'masters':len(data['master_specs']),'checks':data['checks'],'properties':[{k:p[k] for k in ('id','boundary_perimeter_m','designed_wall_length_m','intentional_gate_length_m','unexplained_gap_m','paved_service_court_area_m2','coherent_garden_area_m2')} for p in data['property_records']], 'forest':[{k:p[k] for k in ('id','tree_forms','canopy_envelope_union_fraction_2m_grid','projected_rounded_canopy_union_fraction_2m_grid','wooded_core_windows','nearest_trunk_distance_cv')} for p in data['vegetation_land_use']]}
 (args.output.parent/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
 if not data['checks']['valid']:raise SystemExit(1)
if __name__=='__main__':main()
