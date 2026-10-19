"""Finite source exterior walks to recovered native approach surfaces."""
import heapq
from plan_coverage import *
def main():
 plan=load(HERE/'coverage_plan.json');pre=load(HERE/'all_grounds_preflight.json');prod=load(HERE/'productive_frames.json');land=load(LAND);gardens=load(GARDEN);recovery=load(CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json');routes=[];failures=[];stats=[]
 for site in plan['sites']:
  sid=site['id'];group='cathedral'if sid=='SITE_CLERGY'else'monastery';obstacles=[]
  for f in land['owned_floors']:obstacles.append(f['polygon_xz_m'])
  obstacles += [s['polygon_xz_m']for s in gardens['sites']]
  obstacles += [c['requested_frame_xz_m']for c in plan['compounds']]
  obstacles += [f['polygon_xz_m']for f in prod['frames']]
  boxes=[offset(p,-1.0)for p in obstacles];index=geo._SpatialIndex(16)
  for i,p in enumerate(boxes):index.add(i,p)
  sitepoly=site['polygon_xz_m'];tri=triangulate(sitepoly);cache={}
  def point(q):return[q[0]+.5,q[1]+.5]
  def valid(q):
   if q not in cache:
    p=point(q);cache[q]=any(geo.point_in_convex_polygon(p,t,0)for t in tri)and not any(geo.point_in_convex_polygon(p,boxes[i],0)for i in index.candidates(rect(p,.01,.01)))
   return cache[q]
  def nearby(p,radius=5):
   q=(math.floor(p[0]),math.floor(p[1]));choices=sorted((math.dist(point((q[0]+dx,q[1]+dz)),p),(q[0]+dx,q[1]+dz))for dx in range(-radius,radius+1)for dz in range(-radius,radius+1));return next((v for _,v in choices if valid(v)),None)
  targets={}
  for i,m in enumerate(recovery['approaches']['masks']):
   if m['group_id']!=group:continue
   p=prop.centre(m['polygon_xz_m']);q=nearby(p,1)
   if q is not None and math.dist(point(q),p)<1.5:targets[q]={'id':'RECOVERED_R3_APPROACH:'+group+':'+str(i),'point_xz_m':p}
  goal_rows=[]
  for row in pre['sources']:
   belongs=next((c['site_id']for c in plan['compounds']if c['id']==row['compound_id']),None)or next((f['site_id']for f in prod['frames']if f['id']==row['compound_id']),None)
   if belongs!=sid:continue
   g=row['gate'];q=nearby(g['outside_xz_m']);goal_rows.append((row,g,q))
  goals={q for _,_,q in goal_rows if q};dist={q:0 for q in targets};prev={};seed={q:q for q in targets};heap=[(0,q)for q in targets];heapq.heapify(heap);reached=set()
  while heap and reached!=goals:
   cost,q=heapq.heappop(heap)
   if cost>dist[q]+1e-8:continue
   if q in goals:reached.add(q)
   for dx,dz in[(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]:
    n=(q[0]+dx,q[1]+dz)
    if not valid(n)or(dx and dz and(not valid((q[0]+dx,q[1]))or not valid((q[0],q[1]+dz)))):continue
    nc=cost+math.hypot(dx,dz)
    if nc<dist.get(n,1e99):dist[n]=nc;prev[n]=q;seed[n]=seed[q];heapq.heappush(heap,(nc,n))
  for row,g,q in goal_rows:
   if q is None or q not in reached:failures.append({'gate_id':g['id'],'reason':'No bounded exterior route to preserved native approach'});continue
   cells=[q]
   while cells[-1]in prev:cells.append(prev[cells[-1]])
   simple=[cells[0]]
   for i in range(1,len(cells)-1):
    if(cells[i][0]-cells[i-1][0],cells[i][1]-cells[i-1][1])!=(cells[i+1][0]-cells[i][0],cells[i+1][1]-cells[i][1]):simple.append(cells[i])
   simple.append(cells[-1]);target=targets[seed[q]];points=[g['center_xz_m'],g['outside_xz_m']]+[point(v)for v in simple]+[target['point_xz_m']];points=[p for i,p in enumerate(points)if i==0 or math.dist(p,points[i-1])>1e-6];ribbons=[geo.road_ribbon(a,b,1.8)for a,b in zip(points,points[1:])];routes.append({'id':g['id']+':exterior_candidate','site_id':sid,'gate_id':g['id'],'target':target,'width_m':1.8,'polyline_xz_m':points,'ribbon_polygons_xz_m':ribbons,'join_polygons_xz_m':[circle(p,.9)for p in points[1:-1]],'length_m':sum(math.dist(a,b)for a,b in zip(points,points[1:])),'gate_y_m':g['floor_y_m'],'grade_policy':'Retain host bench where finite; exact target sampled profile and terrain ownership must be supplied by terrain adapter.','status':'source_route_candidate; no native floor/character acceptance'})
  stats.append({'site_id':sid,'network_seeds':len(targets),'searched_grid_nodes':len(dist),'reached_gates':len(reached),'total_gates':len(goal_rows)})
 write(HERE/'exterior_access_proposal.json',{'schema':'riverstone.precinct.exterior_walk_source_proposal.v1','registered_source':ref(SOURCE),'native_pack':ref(HERE/'resolved_placements.json'),'recovered_approaches':ref(CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'),'routes':routes,'failures':failures,'search_stats':stats,'preserved_old_route_ids':False,'actual_native_external_surfaces':False,'full_width_independent_audit':False});print('ROUTES',len(routes),'FAILURES',failures,stats)
if __name__=='__main__':main()
