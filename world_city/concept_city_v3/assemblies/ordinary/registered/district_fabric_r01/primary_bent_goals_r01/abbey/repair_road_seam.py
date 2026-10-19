"""Read-only nearby road cut search avoiding full source triangles above 12%."""
from search_abbey import *
def main():
 scene=load(SC);bounds=[-270,-18,-235,12];good=[];bad=[];step=.05
 for mat,vs in scene['surfaces'].items():
  if mat in('bank','water'):continue
  ar=np.asarray(vs).reshape(-1,3,3);mn=ar.min(axis=1);mx=ar.max(axis=1);sel=np.flatnonzero((mx[:,0]>=bounds[0])&(mn[:,0]<=bounds[2])&(mx[:,2]>=bounds[1])&(mn[:,2]<=bounds[3])&(mn[:,1]>=6)&(mx[:,1]<=9))
  for i in sel:
   tri=vs[3*i:3*i+3]
   if terrain.normal_y(tri)<=1e-10:continue
   plane=terrain.common.plane(tri);poly=[[v[0],v[2]]for v in tri]
   (good if math.hypot(*plane[:2])<=.120000001 else bad).append(poly)
 mask,xs,zs=raster(good,bounds,step);obs,_,_=raster(bad,bounds,step);dist=distance_transform_edt(mask&~obs)*step;clear=dist>=.4
 d=load(O/'abbey_bent_route_proof.json');a=d['polyline_xyz_m'][0];c=d['polyline_xyz_m'][1];end=[a[i]+.12*(c[i]-a[i])for i in[0,2]];road=next(r for r in load(CAT)['routes']if r['id']=='ROAD:WEST_MONASTERY_EDGE');targets={}
 def cell(p):return round((p[1]-bounds[1])/step),round((p[0]-bounds[0])/step)
 for si,(a,c)in enumerate(zip(road['points_xyz_m'],road['points_xyz_m'][1:])):
  for t in np.linspace(0,1,max(2,math.ceil(math.dist(a,c)/.05)+1)):
   q=[a[i]+float(t)*(c[i]-a[i])for i in range(3)]
   if not(bounds[0]+.5<q[0]<bounds[2]-.5 and bounds[1]+.5<q[2]<bounds[3]-.5):continue
   ce=cell([q[0],q[2]])
   if clear[ce]:targets[ce]=dict(segment_index=si,t=float(t),point_xyz_m=q)
 en=cell(end);parents={en:None};cost={en:0.};heap=[(0.,*en)];found=None
 while heap:
  ds,z,x=heapq.heappop(heap)
  if ds!=cost[z,x]:continue
  if (z,x)in targets:found=(z,x);break
  for dz,dx in((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   zz,xx=z+dz,x+dx
   if not(0<=zz<len(zs)and 0<=xx<len(xs)and clear[zz,xx]):continue
   if dz and dx and(not clear[z,xx]or not clear[zz,x]):continue
   nd=ds+math.hypot(dz,dx)*step
   if nd<cost.get((zz,xx),float('inf')):cost[zz,xx]=nd;parents[zz,xx]=(z,x);heapq.heappush(heap,(nd,zz,xx))
 chain=[]
 if found:
  cur=found
  while cur is not None:chain.append([float(xs[cur[1]]),float(zs[cur[0]])]);cur=parents[cur]
  chain=[[targets[found]['point_xyz_m'][i]for i in[0,2]]]+chain+[end]
  def los(a,c):
   pp=np.linspace(a,c,max(2,math.ceil(math.dist(a,c)/.02)+1));ix=np.rint((pp[:,0]-bounds[0])/step).astype(int);iz=np.rint((pp[:,1]-bounds[1])/step).astype(int);return bool(np.all(dist[iz,ix]>=.39))
  simple=[chain[0]];i=0
  while i<len(chain)-1:
   j=len(chain)-1
   while j>i+1 and not los(chain[i],chain[j]):j-=1
   simple.append(chain[j]);i=j
 else:simple=[]
 out=dict(status='CANDIDATE'if found else'NO_ROUTE',scene=ref(SC),grade_limit=.12,source_road_id=road['id'],road_cut=targets[found]if found else None,polyline_xz_m=simple,old_route_connection_xz_m=end,counts=dict(good=len(good),bad=len(bad),targets=len(targets),reachable=len(parents)),bounds=bounds)
 write('road_seam_candidate.json',out);np.savez_compressed(O/'road_seam_grid.npz',clear=clear,distance=dist,xs=xs,zs=zs);print(json.dumps(out),flush=True)
if __name__=='__main__':main()
