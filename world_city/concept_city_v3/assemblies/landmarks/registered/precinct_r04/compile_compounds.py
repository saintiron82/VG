"""Sequential bounded common sampling with actual floor/gateway replay."""
import collections,json,time,resource,math
from plan_coverage import *
from voxel_character.common import coordinate_planes,render_data,core

def walk_report(c,row,doors):
 cells={tuple(r[:3])for r in c['cells']};pitch=c['pitch'];grid=c['grid_origin'];floor={(x,z)for x,y,z in cells if abs(grid[1]+(y+1)*pitch)<1e-7 and all((x,j,z)not in cells for j in range(y+1,y+5))};safe={q for q in floor if all((q[0]+dx,q[1]+dz)in floor for dx,dz in[(0,0),(1,0),(-1,0),(0,1),(0,-1)])};origin=row['position_m']
 plants=[p['footprint_xz_m']for p in load(HERE/'productive_placements.source.json')['placements']if p['site_id']==row['compound_id']]
 if plants:
  floor={q for q in floor if not any(geo.point_in_convex_polygon([origin[0]+grid[0]+(q[0]+.5)*pitch,origin[2]+grid[2]+(q[1]+.5)*pitch],p,0)for p in plants)}
  safe={q for q in floor if all((q[0]+dx,q[1]+dz)in floor for dx,dz in[(0,0),(1,0),(-1,0),(0,1),(0,-1)])}
 def point(q):return[origin[0]+grid[0]+(q[0]+.5)*pitch,origin[2]+grid[2]+(q[1]+.5)*pitch]
 def nearest(p):return min(safe,key=lambda q:math.dist(point(q),p))
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
  routes.append({'id':d['id']+':native_route','door_id':d['id'],'gate_id':gate['id'],'threshold_xyz_m':d['threshold_xyz_m'],'door_to_floor_sample_distance_m':math.dist(point(target),d['approach_start_xz_m']),'reachable':ok,'polyline_xz_m':path,'floor_y_m':origin[1],'width_status':'0.4m-radius native grid erosion plus four-neighbour route; full1.8m ribbon not certified','external_status':'public continuation pending'})
 n=gate['inward_xz'];u=[-n[1],n[0]];clear=[]
 for step in range(-60,61):
  t=step*.05;blocked=False
  for across in(-.25,0,.25):
   for y in(.1,1,1.9):
    x=gate['center_xz_m'][0]+u[0]*t+n[0]*across-origin[0];z=gate['center_xz_m'][1]+u[1]*t+n[1]*across-origin[2];index=(math.floor((x-grid[0])/pitch),math.floor((y-grid[1])/pitch),math.floor((z-grid[2])/pitch));blocked=blocked or index in cells
  clear.append(not blocked)
 left=right=60
 while left>0 and clear[left-1]:left-=1
 while right<120 and clear[right+1]:right+=1
 native_gate_width=(right-left)*.05 if clear[60] else 0
 return{'native_gate_clear_width_sampled_m':native_gate_width,'gate_width_method':'0.05m lateral samples through0.5m depth at three walking heights; finite slab sample, not analytic capsule proof','native_floor_cells':len(floor),'eroded_walk_cells':len(safe),'gate_component_walk_cells':len(seen),'routes':routes,'all_door_starts_reachable':all(r['reachable']and r['door_to_floor_sample_distance_m']<1 for r in routes),'gate_center_native_distance_m':math.dist(point(nearest(gate['center_xz_m'])),gate['center_xz_m'])}
def top_faces(r):
 out=[]
 for g in r['groups']:
  for q in g['quads']:
   if not all(abs(v[1])<1e-7 for v in q):continue
   u=[q[1][j]-q[0][j]for j in range(3)];v=[q[2][j]-q[0][j]for j in range(3)]
   if u[2]*v[0]-u[0]*v[2]>0:out.append([[v[0],v[2]]for v in q])
 return out

def main():
 pre=load(HERE/'all_grounds_preflight.json');fit=load(HERE/'native_building_fit.json');rows=[];tests=[];floors=[];start=time.monotonic()
 for row in pre['sources']:
  t=time.monotonic();s=load(ROOT/row['source']['path']);c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=600000,max_output_cells=180000);assert c['valid'];r=render_data.make_render_data(c);cp=HERE/'cache'/f"{s['id']}.pitch_0.5.render.json";write(cp,r);report={'id':s['id'],'compound_id':row['compound_id'],'source':row['source'],'cache':ref(cp),'master_hash':core.digest(s),'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':r['quad_count'],'bounds':r['bounds'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'position_m':row['position_m'],'yaw_rad':0,'scale':[1,1,1]};rows.append(report)
  targets=[d for d in fit['doors']if d['compound_id']==row['compound_id']]
  if not targets:
   frame=next(f for f in load(HERE/'productive_frames.json')['frames']if f['id']==row['compound_id'])
   for i,z in enumerate([0,frame['depth_m']/2-3,-frame['depth_m']/2+3]):
    p=world([0,z],frame['center_xz_m'],frame['yaw_degrees']);targets.append({'id':frame['id']+':working_aisle:'+str(i),'threshold_xyz_m':[p[0],frame['finished_floor_y_m'],p[1]],'approach_start_xz_m':p,'kind':'working_destination_not_building_door'})
  test=walk_report(c,row,targets);test['compound_id']=row['compound_id'];tests.append(test)
  for i,p in enumerate(top_faces(r)):floors.append({'id':row['compound_id']+':native_floor:'+str(i),'placement_id':row['compound_id'],'polygon_xz_m':[[x+row['position_m'][0],z+row['position_m'][2]]for x,z in p],'floor_y_m':row['position_m'][1],'support_bottom_y_m':row['position_m'][1]-.5,'basis':'Actual upward common quad; building floors and court share one grid/solid.'})
  print(row['compound_id'],c['candidate_cells'],len(c['cells']),report['seconds'],'doors_reachable',test['all_door_starts_reachable'],flush=True)
 write(HERE/'compile_report.json',{'schema':'riverstone.precinct.common_compile.v1','preflight':ref(HERE/'all_grounds_preflight.json'),'requests':rows,'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'whole_city_compile':False});write(HERE/'evidence/native_access_replay.json',{'compile_report':ref(HERE/'compile_report.json'),'compounds':tests,'all_pass':all(x['all_door_starts_reachable']for x in tests),'scope':'Finite static native floor/gate component only. Public access, full width route ribbons and character collision still pending.'});write(HERE/'actual_native_floors.json',{'compile_report':ref(HERE/'compile_report.json'),'owned_floors':floors});print('TOTAL',time.monotonic()-start,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
if __name__=='__main__':main()
