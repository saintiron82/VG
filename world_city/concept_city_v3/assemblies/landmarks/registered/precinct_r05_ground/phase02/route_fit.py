from inspect_baseline import *
from scipy import ndimage
import heapq

def main():
 data=load(HERE/'stair_fit_candidates.json');study=load(HERE/'baseline_study.json');h=study['holdings'][0];r=np.load(HERE/'baseline_raster.npz');heights=r['h0_height'];mask=r['h0_mask'];b=r['h0_bounds'];eligible=mask&np.isfinite(heights)&(abs(heights-12)<1e-6);clear=ndimage.distance_transform_edt(eligible)*.5;walk=clear>=1.25
 def ij(p):return(round((p[1]-b[1])/.5-.5),round((p[0]-b[0])/.5-.5))
 def xz(ij):return[float(b[0]+(ij[1]+.5)*.5),float(b[1]+(ij[0]+.5)*.5)]
 def nearest(p):
  z,x=ij(p);q=[(math.dist(p,xz((zz,xx))),(zz,xx))for zz in range(max(0,z-8),min(walk.shape[0],z+9))for xx in range(max(0,x-8),min(walk.shape[1],x+9))if walk[zz,xx]];return min(q)[1]if q else None
 start=nearest([-88.25,-198.25]);valid=[]
 for c in sorted(data['candidates'],key=lambda r:(r['rise_m'],r['outside_holding_m2'])):
  if c['rise_m']>6.01:continue
  target=nearest(c['upper_landing_xz_m'])
  if target is None or math.dist(xz(target),c['upper_landing_xz_m'])>2:continue
  heap=[(0,start)];cost={start:0};prev={}
  while heap:
   _,p=heapq.heappop(heap)
   if p==target:break
   for dz,dx in[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    q=(p[0]+dz,p[1]+dx)
    if not(0<=q[0]<walk.shape[0]and 0<=q[1]<walk.shape[1])or not walk[q]or not walk[p[0],q[1]]or not walk[q[0],p[1]]:continue
    new=cost[p]+math.hypot(dx,dz)
    if new<cost.get(q,1e99):cost[q]=new;prev[q]=p;heapq.heappush(heap,(new+math.dist(q,target),q))
  if target not in cost:continue
  path=[target]
  while path[-1]!=start:path.append(prev[path[-1]])
  path=list(reversed(path));simple=[path[0]]
  for i in range(1,len(path)-1):
   a,c2,d=path[i-1],path[i],path[i+1]
   if(c2[0]-a[0],c2[1]-a[1])!=(d[0]-c2[0],d[1]-c2[1]):simple.append(c2)
  simple.append(path[-1]);c=dict(c,internal_service_route_xz_m=[xz(p)for p in simple],internal_route_length_m=cost[target]*.5,route_clearance_grid_m=1.25,route_sample_floor_y_m=12);valid.append(c)
 write(HERE/'accessible_stair_candidates.json',{'base_scene':study['base_scene'],'candidates':valid,'method':'2m clear route screening at 0.5m source grid, with1.25m center clearance from non-+12 ground; final exact ribbons and native fixtures require acceptance.'});print('VALID',len(valid));print([{k:c[k]for k in('rise_m','outside_holding_m2','lower_landing_outer_edge_xz_m','upper_landing_xz_m','internal_route_length_m')}for c in valid[:8]])
if __name__=='__main__':main()
