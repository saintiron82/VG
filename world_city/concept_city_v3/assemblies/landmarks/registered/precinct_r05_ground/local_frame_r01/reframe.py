"""Re-sample three frozen source unions in their principal rigid frame.
No source shape, dimension, material or shared compiler is changed.
"""
import sys,copy,math,time,resource,collections,hashlib,itertools
from pathlib import Path
OUT=Path(__file__).resolve().parent;REG=OUT.parents[1];BASE=REG/'precinct_r04';sys.path.insert(0,str(BASE))
from plan_coverage import *
from recovered_range_factory import estimate_candidates
from compile_compounds import top_faces
from voxel_character.common import coordinate_planes,render_data,core
from world_city.concept_city_v3.assemblies.landmarks.author import placement
ANGLE=32.3;RAD=math.radians(ANGLE);IDS=['CLERGY_CANONS_CLOSE','CLERGY_SCHOOL_SERVICE','CLERGY_GUEST_ALMS'];PACK=BASE/'contact_repair_r01/resolved_placements.json'
def rot(p,angle=RAD):
 c,s=math.cos(angle),math.sin(angle);return[c*p[0]+s*p[1],-s*p[0]+c*p[1]]
def wp(p,pose,angle=RAD):
 q=rot(p,angle);return[q[0]+pose[0],q[1]+pose[2]]
def local(p,pose):return rot([p[0]-pose[0],p[1]-pose[2]],-RAD)
def faces(mesh,y,up):
 out=[]
 for g in mesh['groups']:
  for q in g['quads']:
   if not all(abs(v[1]-y)<1e-7 for v in q):continue
   a=[q[1][j]-q[0][j]for j in range(3)];b=[q[2][j]-q[0][j]for j in range(3)]
   if (a[2]*b[0]-a[0]*b[2])*up>0:out.append([[v[0],v[2]]for v in q])
 return out

def cellrects(columns,pitch=.5):
 rows=collections.defaultdict(list)
 for x,z in columns:rows[z].append(x)
 active={};out=[]
 for z in range(min(rows),max(rows)+2):
  xs=sorted(set(rows.get(z,[])));runs=[]
  if xs:
   a=prev=xs[0]
   for x in xs[1:]:
    if x!=prev+1:runs.append((a,prev+1));a=x
    prev=x
   runs.append((a,prev+1))
  nxt={}
  for run in runs:nxt[run]=active.pop(run,[run[0],z,run[1],z+1]);nxt[run][3]=z+1
  out.extend(active.values());active=nxt
 return [[[a*pitch,b*pitch],[c*pitch,b*pitch],[c*pitch,d*pitch],[a*pitch,d*pitch]]for a,b,c,d in out]
def diff(old,new):
 ix=geo._SpatialIndex(8)
 for i,p in enumerate(old):ix.add(i,p)
 inter=sum(geo.intersection_area(p,old[i])for p in new for i in ix.candidates(p))
 oa=sum(geo.polygon_area(p)for p in old);na=sum(geo.polygon_area(p)for p in new)
 return{'old_area_m2':oa,'new_area_m2':na,'intersection_m2':inter,'removed_m2':max(0,oa-inter),'added_m2':max(0,na-inter),'symmetric_difference_m2':max(0,oa+na-2*inter),'method':'Exact convex intersections of disjoint sampled-column rectangles; no raster approximation or AABB coverage.'}
def roof_columns(c):
 # Component identity is stable; include actual roof paint cells, no full building AABB.
 return{(r[0],r[2])for r in c['cells']if 'roof'in r[3].lower()}
def walk(c,row,doors):
 cells={tuple(r[:3])for r in c['cells']};p=c['pitch'];origin=row['position_m'];grid=c['grid_origin'];floor={(x,z)for x,y,z in cells if abs(grid[1]+(y+1)*p)<1e-7 and all((x,j,z)not in cells for j in range(y+1,y+5))};safe={q for q in floor if all((q[0]+dx,q[1]+dz)in floor for dx,dz in[(0,0),(1,0),(-1,0),(0,1),(0,-1)])}
 def point(q):return wp([grid[0]+(q[0]+.5)*p,grid[2]+(q[1]+.5)*p],origin)
 def nearest(q):return min(safe,key=lambda r:math.dist(point(r),q))
 gate=row['gate'];start=nearest(gate['inside_xz_m']);seen={start};prev={};queue=collections.deque([start])
 while queue:
  x,z=queue.popleft()
  for q in[(x-1,z),(x+1,z),(x,z-1),(x,z+1)]:
   if q in safe and q not in seen:seen.add(q);prev[q]=(x,z);queue.append(q)
 routes=[]
 for d in doors:
  target=nearest(d['approach_start_xz_m']);ok=target in seen;path=[]
  if ok:
   q=target;path=[q]
   while q!=start:q=prev[q];path.append(q)
   simple=[path[0]]
   for i in range(1,len(path)-1):
    if (path[i][0]-path[i-1][0],path[i][1]-path[i-1][1])!=(path[i+1][0]-path[i][0],path[i+1][1]-path[i][1]):simple.append(path[i])
   simple.append(path[-1]);path=[point(q)for q in simple]+[gate['center_xz_m']]
  routes.append({'id':d['id']+':local_frame_native_route','door_id':d['id'],'gate_id':gate['id'],'threshold_xyz_m':d['threshold_xyz_m'],'door_to_floor_sample_distance_m':math.dist(point(target),d['approach_start_xz_m']),'reachable':ok,'polyline_xz_m':path,'floor_y_m':origin[1],'width_status':'Four-neighbour native grid eroded by adjacent cells; full1.8m ribbon and capsule still unverified.','external_status':'Existing R14 exterior route must be rebound to new sampled gate footprint.'})
 def occupied(world,y):
  q=local(world,origin);return(math.floor((q[0]-grid[0])/p),math.floor((y-grid[1])/p),math.floor((q[1]-grid[2])/p))in cells
 n=gate['inward_xz'];u=[-n[1],n[0]];clear=[]
 for step in range(-80,81):
  t=step*.05;clear.append(not any(occupied([gate['center_xz_m'][j]+u[j]*t+n[j]*across for j in(0,1)],y)for across in(-.25,0,.25)for y in(.1,1,1.9)))
 l=r=80
 while l>0 and clear[l-1]:l-=1
 while r<160 and clear[r+1]:r+=1
 return{'compound_id':row['compound_id'],'native_gate_clear_width_sampled_m':(r-l)*.05 if clear[80]else 0,'gate_width_method':'0.05m lateral samples,0.5m depth, three walking heights.','floor_cells':len(floor),'safe_cells':len(safe),'routes':routes,'all_door_starts_reachable':all(r['reachable']and r['door_to_floor_sample_distance_m']<1 for r in routes)}
def prepare():
 pack=load(PACK);rows=[];inverse=placement(yaw=-ANGLE);forward=placement(yaw=ANGLE)
 for pid in IDS:
  a=next(a for a in pack['assets']if a.get('compound_id')==pid);pose=next(p for p in pack['placements']if p['id']==pid);old=load(ROOT/a['source']['path']);s=copy.deepcopy(old);s['id']=old['id']+'_principal_frame_r01';s['revision']=old.get('revision',1)+1;errors=[]
  for inst,orig in zip(s['instances'],old['instances']):
   if not inst.get('parent'):
    inst['transform']=core.compose(inverse,core.transform(orig.get('transform')));roundtrip=core.compose(forward,core.transform(inst['transform']));orig_t=core.transform(orig.get('transform'))
    errors += [abs(x-y)for k in('basis','translation')for x,y in zip(sum(roundtrip[k],[])if k=='basis'else roundtrip[k],sum(orig_t[k],[])if k=='basis'else orig_t[k])]
  for cut in s.get('assembly_cuts',[]):cut['transform']=core.compose(inverse,core.transform(cut.get('transform')))
  for con in s.get('constraints',[]):
   if 'shape'in con:con['transform']=core.compose(inverse,core.transform(con.get('transform')))
  s['provenance'].update(principal_frame_author=ref(Path(__file__)),immutable_source=a['source'],immutable_cache=a['cache']);s['extensions']['principal_sampling_frame']={'yaw_degrees':ANGLE,'world_rigid_placement_yaw_rad':RAD,'all_continuous_shapes_materials_dimensions_identical':s['components']==old['components'],'source_roundtrip_transform_max_error':max(errors),'old_extension_coordinates':'Historical union-local/world metadata retained verbatim; this explicit frame describes the new sample coordinates.','visual_review':'pending'}
  assert s['components']==old['components']and max(errors)<1e-10
  sp=OUT/'masters'/f"{s['id']}.json";write(sp,s);est=estimate_candidates(s,.5);assert est['candidate_cells_exact_aabb_visits']<610000;rows.append({'compound_id':pid,'old_asset':a,'old_placement':pose,'source':ref(sp),'estimate':est,'source_roundtrip_transform_max_error':max(errors)})
 write(OUT/'preflight.json',{'schema':'riverstone.principal_frame.preflight.v1','immutable_base_pack':ref(PACK),'immutable_r5_scene':ref(CITY/'evidence/visual_registered_common_r5/bridge_scene.json'),'sources':rows,'pitch_m':.5,'candidate_cap_each':610000,'output_cap_each':180000,'compile_order':'One sequential process, old cache replay then replacement for each of three unions.','whole_city_compile':False});print([(r['compound_id'],r['estimate']['candidate_cells_exact_aabb_visits'])for r in rows],flush=True)
def main():
 start=time.monotonic();pre=load(OUT/'preflight.json');base=load(PACK);fit=load(BASE/'native_building_fit.json');grounds=load(BASE/'all_grounds_preflight.json');replacements=[];floors=[];bearings=[];deltas=[];tests=[]
 for row in pre['sources']:
  t=time.monotonic();pid=row['compound_id'];a=row['old_asset'];pose=row['old_placement'];pos=pose['position_m'];old=coordinate_planes.compile_master(load(ROOT/a['source']['path']),{'pitch':.5},max_candidate_cells=610000,max_output_cells=180000);assert old['valid'];oldmesh=render_data.make_render_data(old);assert oldmesh==load(ROOT/a['cache']['path']);s=load(ROOT/row['source']['path']);c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=610000,max_output_cells=180000);assert c['valid'];mesh=render_data.make_render_data(c);cp=OUT/'cache'/f"{s['id']}.pitch_0.5.render.json";write(cp,mesh)
  asset={**a,'id':s['id'],'source':row['source'],'cache':ref(cp),'master_hash':core.digest(s),'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':mesh['quad_count'],'bounds':mesh['bounds'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'yaw_rad':RAD}
  newpose={**pose,'asset_key':s['id'],'source':row['source'],'cache':ref(cp),'yaw_rad':RAD,'actual_cached_bounds_local_m':mesh['bounds']};newpose['world_transform_note']='Same world source geometry; principal sampling frame is rigidly rotated32.3degrees after compilation.'
  replacements.append({'placement_id':pid,'old_asset_key':a['id'],'asset':asset,'placement':newpose})
  oldfloor=[wp(p,pos,0)for p in []] # populated as polygons below
  oldfloor=[[wp(p,pos,0)for p in poly]for poly in faces(oldmesh,0,1)];newfloor=[[wp(p,pos)for p in poly]for poly in faces(mesh,0,1)];oldbearing=[[wp(p,pos,0)for p in poly]for poly in faces(oldmesh,-.5,-1)];newbearing=[[wp(p,pos)for p in poly]for poly in faces(mesh,-.5,-1)];oldroof=[[wp(p,pos,0)for p in poly]for poly in cellrects(roof_columns(old))];newroof=[[wp(p,pos)for p in poly]for poly in cellrects(roof_columns(c))]
  for i,p in enumerate(newfloor):floors.append({'id':pid+':principal_frame_floor:'+str(i),'placement_id':pid,'polygon_xz_m':p,'floor_y_m':pos[1],'support_bottom_y_m':pos[1]-.5,'basis':'Exact transformed upward native quad, new principal-frame cache.'})
  for i,p in enumerate(newbearing):bearings.append({'id':pid+':principal_frame_bearing:'+str(i),'placement_id':pid,'polygon_xz_m':p,'bottom_y_m':pos[1]-.5,'finished_floor_y_m':pos[1],'ownership_policy':'Replace only old masks from this placement; preserve all other native owners pending exact new contact audit.'})
  deltas.append({'placement_id':pid,'continuous_source_shapes_changed':False,'continuous_source_world_transform_max_error':row['source_roundtrip_transform_max_error'],'native_floor':diff(oldfloor,newfloor),'native_bearing':diff(oldbearing,newbearing),'native_roof_projection':diff(oldroof,newroof),'old_roof_polygons_xz_m':oldroof,'new_roof_polygons_xz_m':newroof,'old_world_bounds':{k:[min(v[j]for g in oldmesh['groups']for q in g['quads']for v in q)+pos[j]if k=='min'else max(v[j]for g in oldmesh['groups']for q in g['quads']for v in q)+pos[j]for j in range(3)]for k in('min','max')}})
  ground=next(r for r in grounds['sources']if r['compound_id']==pid);report=walk(c,ground,[d for d in fit['doors']if d['compound_id']==pid]);tests.append(report);assert report['all_door_starts_reachable'],report;assert report['native_gate_clear_width_sampled_m']>=3.5,report
  print(pid,c['candidate_cells'],len(c['cells']),round(time.monotonic()-t,3),'gate',report['native_gate_clear_width_sampled_m'],'floor_delta',deltas[-1]['native_floor']['symmetric_difference_m2'],flush=True)
 write(OUT/'native_access_replay.json',{'compounds':tests,'all_pass':True,'limits':'Existing authored thresholds unchanged. New sampled internal grid routes pass; fullwidth exterior and independent terrain ownership remain pending.'});write(OUT/'native_boundary_deltas.json',{'immutable_base_pack':ref(PACK),'rows':deltas,'all_source_dimensions_unchanged':True});write(OUT/'replacement_overlay.json',{'schema':'riverstone.precinct.principal_frame_overlay.v1','immutable_base_pack':ref(PACK),'preflight':ref(OUT/'preflight.json'),'replacements':replacements,'replace_floor_and_bearing_placement_ids':IDS,'owned_floors':floors,'actual_bearing_footprints':bearings,'native_access_replay':ref(OUT/'native_access_replay.json'),'native_boundary_deltas':ref(OUT/'native_boundary_deltas.json'),'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_viewed':False,'independent_native_owner_audit':False});print(ref(OUT/'replacement_overlay.json'),flush=True)
if __name__=='__main__':prepare() if '--prepare'in sys.argv else main()
