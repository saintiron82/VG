"""Source-bound existing-scene abbey route search; no scene or source mutations."""
from pathlib import Path
import os,sys,json,math,time,heapq,hashlib
O=Path(__file__).resolve().parent
ROOT=O.parents[7];CITY=ROOT/'world_city/concept_city_v3'
os.environ['MPLCONFIGDIR']=str(O/'mplconfig');os.environ['XDG_CACHE_HOME']=str(O/'render_cache');sys.dont_write_bytecode=True
sys.path.insert(0,str(CITY/'assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01'))
sys.path.insert(0,str(CITY/'assemblies/landmarks/registered/precinct_r06_whole'))
from resolve_pack import load,ref,b,geo,slab_rectangles,horizontal,np,terrain
from matplotlib.path import Path as MP
def raster(polys,bounds,step):
 x0,z0,x1,z1=bounds;xs=np.arange(x0,x1+step/2,step);zs=np.arange(z0,z1+step/2,step);a=np.zeros((len(zs),len(xs)),bool)
 for poly in polys:
  poly=list(poly)
  if geo.signed_polygon_area(poly)<0:poly=poly[::-1]
  x=np.array(poly);ix0=max(0,int(math.floor((x[:,0].min()-x0)/step)));ix1=min(len(xs)-1,int(math.ceil((x[:,0].max()-x0)/step)));iz0=max(0,int(math.floor((x[:,1].min()-z0)/step)));iz1=min(len(zs)-1,int(math.ceil((x[:,1].max()-z0)/step)))
  if ix0>ix1 or iz0>iz1:continue
  xx,zz=np.meshgrid(xs[ix0:ix1+1],zs[iz0:iz1+1]);hit=MP(poly).contains_points(np.column_stack((xx.ravel(),zz.ravel())),radius=1e-7).reshape(xx.shape);a[iz0:iz1+1,ix0:ix1+1]|=hit
 return a,xs,zs
from scipy.ndimage import distance_transform_edt,label
SC=CITY/'evidence/r8_final110_runtime_r01/scene.json'
PK=CITY/'assemblies/landmarks/registered/assembly_r01/resolved_placements.json'
CAT=CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_final_catalog_r01/route_catalog_481_r01.json'
def write(name,d):(O/name).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def main():
 t=time.monotonic();scene=load(SC);floor=8.;bounds=[-352,-30,-175,181];win=b.rect(*bounds);native=[];bodies=[];floors=[];cache={};bindings=[]
 for p in scene['common_instances']:
  a=scene['common_assets'][p['asset_key']];bb=a.get('bounds');py=p['position_m'][1]
  if bb is None:
   if a['render_path']not in cache:cache[a['render_path']]=load(ROOT/a['render_path'])
   bb=cache[a['render_path']]['bounds']
  if bb['min'][1]+py>floor+2.2 or bb['max'][1]+py<floor-1e-7:continue
  if geo.intersection_area(b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p),win)<1e-8:continue
  if a['render_path']not in cache:cache[a['render_path']]=load(ROOT/a['render_path'])
  mesh=cache[a['render_path']];body=[b.xform(q,p)for q in slab_rectangles(mesh,floor-py+.01,floor-py+2.2)];fs=[b.xform(q,p)for q in horizontal(mesh,floor-py,True)];bodies.extend(body);floors.extend(fs)
  bindings.append(dict(id=p['id'],asset_key=p['asset_key'],cache=dict(path=a['render_path'],sha256=a['render_sha256']),source=dict(path=a['master_path'],sha256=a['master_sha256']),position_m=p['position_m'],yaw_rad=p['yaw_rad'],body_polygons_xz_m=body,floor_polygons_xz_m=fs))
 support=[];rows=[]
 for mat,vs in scene['surfaces'].items():
  if mat in ('bank','water'):continue
  for j in range(0,len(vs),3):
   tri=vs[j:j+3]
   if max(v[1]for v in tri)>10.000001 or min(v[1]for v in tri)<5.999999:continue
   if max(v[0]for v in tri)<bounds[0]or min(v[0]for v in tri)>bounds[2]or max(v[2]for v in tri)<bounds[1]or min(v[2]for v in tri)>bounds[3]:continue
   if terrain.normal_y(tri)<=1e-10:continue
   plane=terrain.common.plane(tri)
   if math.hypot(plane[0],plane[1])>.26:continue
   poly=[[v[0],v[2]]for v in tri];support.append(poly);rows.append(dict(material=mat,triangle_index=j//3,polygon_xz_m=poly))
 print('loaded',len(support),len(floors),len(bodies),time.monotonic()-t,flush=True)
 step=.2;mask,xs,zs=raster(support+floors,bounds,step);obs,_,_=raster(bodies,bounds,step);dist=distance_transform_edt(mask&~obs)*step;clear=dist>=.5
 e=next(e for e in load(PK)['entrances']if e['id']=='monastery_registered:monastic_church:main_entry');end=[e['threshold_world_xyz_m'][i]-.6*e['forward_into_asset_world'][i]for i in [0,2]];road=next(r for r in load(CAT)['routes']if r['id']=='ROAD:WEST_MONASTERY_EDGE');start=[road['points_xyz_m'][10][i]for i in[0,2]]
 def cell(p):return round((p[1]-bounds[1])/step),round((p[0]-bounds[0])/step)
 def point(c):return[float(xs[c[1]]),float(zs[c[0]])]
 en=cell(end);st=cell(start);parents={en:None};cost={en:0.};heap=[(0.,*en)];found=None
 while heap:
  ds,z,x=heapq.heappop(heap)
  if ds!=cost[z,x]:continue
  if (z,x)==st:found=(z,x);break
  for dz,dx in((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   zz,xx=z+dz,x+dx
   if not(0<=zz<len(zs)and 0<=xx<len(xs)and clear[zz,xx]):continue
   if dz and dx and(not clear[z,xx]or not clear[zz,x]):continue
   nd=ds+math.hypot(dz,dx)*step
   if nd<cost.get((zz,xx),float('inf')):cost[zz,xx]=nd;parents[zz,xx]=(z,x);heapq.heappush(heap,(nd,zz,xx))
 chain=[]
 if found:
  cur=found
  while cur is not None:chain.append(point(cur));cur=parents[cur]
  chain=[start]+chain+[end]
 lab,n=label(clear);sizes=np.bincount(lab.ravel());print('result',len(chain),'start',start,clear[st],lab[st],'end',end,clear[en],lab[en], 'regions',n,'reachable',len(parents),'seconds',time.monotonic()-t,flush=True)
 write('search_result.json',dict(scene=ref(SC),entrance=e,source_road=ref(CAT),road_id=road['id'],road_cut=dict(segment_index=9,t=1.,point_xyz_m=road['points_xyz_m'][10]),start_xz_m=start,end_xz_m=end,polyline_xz_m=chain,grid_step_m=step,screen_clearance_m=.5,reachable=len(parents),start_component=int(lab[st]),end_component=int(lab[en]),component_sizes=sizes.tolist(),status='CANDIDATE'if chain else'NO_FLAT_EIGHT_METRE_ROUTE',bounds_xz_m=bounds))
 write('source_geometry.json',dict(scene=ref(SC),native_bindings=bindings,screened_actual_terrain_triangle_count=len(rows)))
 np.savez_compressed(O/'search_grid.npz',support=mask,obstacles=obs,clear=clear,distance=dist,xs=xs,zs=zs,labels=lab)
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(14,14));im=np.zeros(mask.shape+(3,));im[:]=[.95,.95,.95];im[mask]=[.75,.85,.75];im[clear]=[.6,.75,.6];im[obs]=[.25,.25,.25];im[lab==lab[en]]=[.65,.8,1];ax.imshow(im,origin='lower',extent=bounds[::2]+bounds[1::2]);ax.plot([start[0],end[0]],[start[1],end[1]],'r.');
 if chain:ax.plot(*np.array(chain).T,'r-',linewidth=2)
 for r in bindings:
  if len(r['floor_polygons_xz_m'])>2 or r['id'].startswith('monastery_registered:'):ax.text(r['position_m'][0],r['position_m'][2],r['id'].replace('monastery_registered:',''),fontsize=6)
 ax.set_aspect('equal');ax.grid();fig.savefig(O/'search_overview.png',dpi=150)
if __name__=='__main__':main()
