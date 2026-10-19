"""Bounded 2-D rear-lane/gate feasibility for planning holdings. No route promotion."""
from plan import *
import heapq,time

def astar(free,target,start,max_visits=160000):
 distance=ndimage.distance_transform_edt(~target);heap=[(float(distance[start]),0.,start)];cost={start:0.};parent={};visited=0
 while heap:
  _,g,q=heapq.heappop(heap)
  if g!=cost[q]:continue
  visited+=1
  if visited>max_visits:return None,visited,'bounded_search_limit'
  if target[q]:
   path=[q]
   while q in parent:q=parent[q];path.append(q)
   return path[::-1],visited,'plan_grid_route'
  z,x=q
  for dz,dx in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   nz=z+dz;nx=x+dx
   if nz<0 or nx<0 or nz>=free.shape[0]or nx>=free.shape[1]or not free[nz,nx]:continue
   if dz and dx and(not free[z,nx]or not free[nz,x]):continue
   p=(nz,nx);ng=g+(math.sqrt(2)if dz and dx else 1)
   if ng<cost.get(p,math.inf):cost[p]=ng;parent[p]=q;heapq.heappush(heap,(ng+float(distance[p]),ng,p))
 return None,visited,'no_clear_connection_in_review_domain'

def main():
 start_time=time.monotonic();p=load(CITY/'registered_source/plan.json');d=load(HERE/'remaining_land_plan.json');r=np.load(HERE/'review_masks.npz');old=np.load(PREV/'plan_raster.npz');plots=buffer(mask([q['polygon_xz_m']for q in p['plots']]+[q['polygon_xz_m']for q in p['spaces']],2),.75);walls=p['wall_registration']['polygon_xz_m'];wall=mask([geo.road_ribbon(a,b,24)for a,b in zip(walls,walls[1:]+walls[:1])],2,False);parcels=mask([q['parcel_with_clearance_xz_m']for q in d['range_parcels']],2,False)
 obstacles=buffer(r['roof'],1)|r['water']|r['merchant']|wall|parcels
 source_domains={q['id']:mask([q['polygon_xz_m']],1)for q in p['blocks']+p['spaces']if q['id']in['BLOCK_003','BLOCK_005','BLOCK_015','SITE_CLERGY','SITE_MONASTERY']}
 results=[];freecache={}
 for zone in d['zones']:
  sid=zone['site_id'];work=zone['function']in ['canal_workyard','working_compound','estate_service_compound','institutional_workyard'];width=3.5 if work else 2.0;key=(sid,width)
  if key not in freecache:
   if sid.startswith('BLOCK'):
    roads=[q for q in p['roads']if q['width_m']>=width];target=mask([geo.road_ribbon(a,b,q['width_m'])for q in roads for a,b in zip(q['polyline_xz_m'],q['polyline_xz_m'][1:])],1,False);free=(source_domains[sid]&~plots)|target
   else:
    target=(old['precinct_classes']==6)|(old['precinct_classes']==7);free=source_domains[sid]&((old['precinct_classes']==9)|target)
   free &=~obstacles
   # Cell-center distance plus an extra cell circumradius protects full ribbons.
   clear=ndimage.distance_transform_edt(free)*PITCH>=width/2+PITCH*math.sqrt(2)
   freecache[key]=(clear,target&clear)
  free,target=freecache[key]
  for hold in zone['contiguous_holdings']:
   hm=mask(hold['polygon_parts_xz_m'],1,False);zz,xx=np.where(hm);pad=int(100/PITCH);z0=max(0,zz.min()-pad);z1=min(SHAPE[0],zz.max()+pad+1);x0=max(0,xx.min()-pad);x1=min(SHAPE[1],xx.max()+pad+1);local=free[z0:z1,x0:x1];targets=target[z0:z1,x0:x1];starts=hm[z0:z1,x0:x1]&local
   record={'holding_id':hold['id'],'zone_id':zone['id'],'width_m':width,'travel_role':'small_cart_and_service_shared'if work else'pedestrian_rear_lane','status':'unresolved','terrain_profile_approved':False,'actual_native_opening':False,'review_radius_m':100}
   if starts.any()and targets.any():
    z,x=np.where(starts);c=hold['centroid_xz_m'];scores=(BOUNDS[0]+(x+x0+.5)*PITCH-c[0])**2+(BOUNDS[1]+(z+z0+.5)*PITCH-c[1])**2;ix=int(np.argmin(scores));path,visits,status=astar(local,targets,(int(z[ix]),int(x[ix])));record.update(search_status=status,visited_cells=visits)
    if path:
     # Remove only collinear grid runs; no untested shortcut across owners.
     compressed=[path[0]]
     for i in range(1,len(path)-1):
      a,b,c=path[i-1:i+2]
      if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):compressed.append(b)
     compressed.append(path[-1]);line=[[BOUNDS[0]+(x+x0+.5)*PITCH,BOUNDS[1]+(z+z0+.5)*PITCH]for z,x in compressed];ribbons=[geo.road_ribbon(a,b,width)for a,b in zip(line,line[1:])if math.dist(a,b)>1e-9]
     record.update(status='plan_grid_connected_profile_unresolved',polyline_xz_m=line,ribbon_polygons_xz_m=ribbons,length_m=sum(math.dist(a,b)for a,b in zip(line,line[1:])),target_kind='source_public_road'if sid.startswith('BLOCK')else'existing_precinct_floor_or_access_reservation',target_point_xz_m=line[-1],gate_candidates=[])
     for iz,ix in path:
      if not hm[iz+z0,ix+x0]:record['gate_candidates']=[{'position_xz_m':[BOUNDS[0]+(ix+x0+.5)*PITCH,BOUNDS[1]+(iz+z0+.5)*PITCH],'clear_width_m':width,'status':'boundary portal inference; native jamb/leaf and full-width grade unresolved'}];break
     if sid.startswith('BLOCK'):
      choices=[]
      for road in p['roads']:
       if road['width_m']<width:continue
       for k,(a,b)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):choices.append((geo.point_segment_distance(line[-1],a,b),road['id'],k))
      record['source_target_road_id']=min(choices)[1]
    else:record['blocker']='No preserved-owner-safe lane of the declared width within 100 m; needs a named parcel consolidation or revised holding, not an implied gate.'
   else:record['blocker']='No full-width start or valid public/precinct target remains after preserved-owner clearance.'
   results.append(record)
  print(zone['id'],sum(q['status'].startswith('plan_grid')for q in results if q['zone_id']==zone['id']),'of',len(zone['contiguous_holdings']),flush=True)
 out={'schema':'riverstone.remaining_land.access_review.v1','plan':ref(HERE/'remaining_land_plan.json'),'status':'2-D planning feasibility only; no source road replacement, native opening or terrain route approval.','method':{'grid_pitch_m':PITCH,'full_width_center_clearance_m':'half declared width + 0.707107 m','search':'Bounded eight-neighbour A*, with diagonal corner cutting forbidden; compress collinear runs only.','conservative_obstacles':'Existing source plots/spaces, cached roof plus 1 m, water plus 4 m, final merchant 19, wall review corridor and all proposed range parcels.','limits':['Existing source plots are conservatively preserved even when a later retirement might free a strip.','Native terrain and drainage are not changed by these planning lines.','A path to an existing precinct reservation is not a capsule or public-road continuity certificate.','Bounded search failure is an explicit access gap, not a claim that no solution exists.']},'connections':results,'summary':{'holdings':len(results),'plan_grid_connections':sum(q['status'].startswith('plan_grid')for q in results),'unresolved_connections':sum(q['status']=='unresolved'for q in results),'seconds':time.monotonic()-start_time}};write(HERE/'access_review.json',out);print(out['summary'])
if __name__=='__main__':main()
