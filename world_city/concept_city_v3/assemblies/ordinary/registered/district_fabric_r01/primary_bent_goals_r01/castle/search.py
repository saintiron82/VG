from pathlib import Path
import sys,json,math,heapq,time
ROOT=Path(__file__).resolve().parents[8];sys.path.insert(0,str(ROOT))
CITY=ROOT/'world_city/concept_city_v3';SRC=CITY/'assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01';sys.path.insert(0,str(SRC))
from find_branches import raster, b, geo, slab_rectangles, horizontal, np, load
from scipy.ndimage import distance_transform_edt
OUT=Path(__file__).resolve().parent
def raster(polys,bounds,step):
 x0,z0,x1,z1=bounds;xs=np.arange(x0,x1+step/2,step);zs=np.arange(z0,z1+step/2,step);out=np.zeros((len(zs),len(xs)),bool)
 for poly in polys:
  x=np.array(poly);ix0=max(0,int(math.floor((x[:,0].min()-x0)/step)));ix1=min(len(xs)-1,int(math.ceil((x[:,0].max()-x0)/step)));iz0=max(0,int(math.floor((x[:,1].min()-z0)/step)));iz1=min(len(zs)-1,int(math.ceil((x[:,1].max()-z0)/step)))
  if ix0>ix1 or iz0>iz1:continue
  xx,zz=np.meshgrid(xs[ix0:ix1+1],zs[iz0:iz1+1]);cross=[]
  for a,c in zip(poly,poly[1:]+poly[:1]):cross.append((c[0]-a[0])*(zz-a[1])-(c[1]-a[1])*(xx-a[0]))
  arr=np.array(cross);hit=np.all(arr>=-1e-8,axis=0)|np.all(arr<=1e-8,axis=0);out[iz0:iz1+1,ix0:ix1+1]|=hit
 return out,xs,zs
scene=load(CITY/'evidence/r8_final110_runtime_r01/scene.json');bounds=[-326,-254,-273,-195];win=b.rect(*bounds);floor=24;polys=[];toprows=[]
for mat,vs in scene['surfaces'].items():
 for i in range(0,len(vs),3):
  tri=vs[i:i+3]
  if min(v[0]for v in tri)>bounds[2] or max(v[0]for v in tri)<bounds[0] or min(v[2]for v in tri)>bounds[3] or max(v[2]for v in tri)<bounds[1]:continue
  if min(v[1]for v in tri)<23.0 or max(v[1]for v in tri)>24.000001:continue
  p=[[v[0],v[2]]for v in tri];ar=geo.polygon_area(p)
  if ar<1e-10:continue
  ny=(tri[1][2]-tri[0][2])*(tri[2][0]-tri[0][0])-(tri[1][0]-tri[0][0])*(tri[2][2]-tri[0][2])
  if ny<=0:continue
  u=np.array(tri[1])-np.array(tri[0]);v=np.array(tri[2])-np.array(tri[0]);normal=np.cross(u,v)
  if math.hypot(normal[0],normal[2])/abs(normal[1])>.1200001:continue
  polys.append(p);toprows.append({'material':mat,'triangle_index':i//3,'polygon_xz_m':p})
body=[];bodies=[];natives=[];floorrows=[]
for p in scene['common_instances']:
 a=scene['common_assets'][p['asset_key']];bb=a.get('bounds');mesh=None
 if bb is None:mesh=load(ROOT/a['render_path']);bb=mesh['bounds']
 if bb['min'][1]+p['position_m'][1]>floor+2 or bb['max'][1]+p['position_m'][1]<floor-1e-7:continue
 if geo.intersection_area(b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p),win)<1e-8:continue
 if mesh is None:mesh=load(ROOT/a['render_path'])
 qs=[b.xform(q,p)for q in slab_rectangles(mesh,floor-p['position_m'][1]+.05,floor-p['position_m'][1]+1.8)]
 for q in qs:body.append(q);bodies.append({'native_id':p['id'],'polygon_xz_m':q})
 fs=[b.xform(q,p)for q in horizontal(mesh,floor-p['position_m'][1],True)]
 polys+=fs;floorrows +=[{'native_id':p['id'],'polygon_xz_m':q}for q in fs]
 natives.append({'placement':p,'asset':a})
step=.125;mask,xs,zs=raster(polys,bounds,step);obs,_,_=raster(body,bounds,step);clear=distance_transform_edt(mask&~obs)*step>=.425
road=load(CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_final_catalog_r01/route_catalog_481_r01.json');rp=next(r for r in road['routes']if r['id']=='ROAD:CASTLE_APPROACH')['points_xyz_m'];start=[rp[-1][0],rp[-1][2]];end=[-298.7712868288515,-238.16235134180585];gate=[-306.1463176962472,-234.8807481200617]
def cell(q):return round((q[1]-bounds[1])/step),round((q[0]-bounds[0])/step)
def astar(a,c):
 aa=cell(a);cc=cell(c);print('ends',a,clear[aa],c,clear[cc],flush=True);heap=[(math.dist(aa,cc),0,aa)];dist={aa:0};prev={aa:None};found=False
 while heap:
  _,cost,n=heapq.heappop(heap)
  if cost!=dist[n]:continue
  if n==cc:found=True;break
  z,x=n
  for dz,dx in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   zz,xx=z+dz,x+dx
   if not(0<=zz<len(zs)and 0<=xx<len(xs)and clear[zz,xx]):continue
   if dx and dz and(not clear[z,xx]or not clear[zz,x]):continue
   nd=cost+math.hypot(dx,dz)
   if nd<dist.get((zz,xx),1e99):dist[zz,xx]=nd;prev[zz,xx]=n;heapq.heappush(heap,(nd+math.dist((zz,xx),cc),nd,(zz,xx)))
 if not found:return []
 chain=[];n=cc
 while n is not None:chain.append([float(xs[n[1]]),float(zs[n[0]])]);n=prev[n]
 return [a]+list(reversed(chain))+[c]
curtain=next(n['placement']for n in natives if n['placement']['id']=='castle_registered:front_curtain');outside=b.xform([[0,2]],curtain)[0]
paths=[astar(start,outside),astar(gate,end)]
def safe(a,c):
 for t in np.linspace(0,1,max(2,math.ceil(math.dist(a,c)/.05))):
  q=[a[i]+float(t)*(c[i]-a[i])for i in range(2)]
  if not clear[cell(q)]:return False
 return True
simplified=[]
for path in paths:
 out=[];i=0
 while i<len(path)-1:
  out.append(path[i]);j=len(path)-1
  while j>i+1 and not safe(path[i],path[j]):j-=1
  i=j
 if path:out.append(path[-1])
 simplified.append(out)
result={'bounds':bounds,'start_xz_m':start,'gate_xz_m':gate,'end_xz_m':end,'floor_y_m':floor,'paths_xz_m':simplified,'screen_grid_step_m':step,'screen_clearance_m':.425,'exact_simplification_radius_m':.35,'native_bindings':natives,'actual_top_rows':toprows,'native_floor_rows':floorrows,'native_body_rows':bodies}
(OUT/'search_result.json').write_text(json.dumps(result,indent=2)+'\n');np.savez_compressed(OUT/'search_grid.npz',clear=clear,mask=mask,obs=obs,xs=xs,zs=zs)
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(10,10));ax.imshow(mask,origin='lower',extent=bounds[::2]+bounds[1::2] if False else [bounds[0],bounds[2],bounds[1],bounds[3]],cmap='Greys',alpha=.5);ax.contour(xs,zs,obs,levels=[.5],colors='red');
for path in simplified:
 if path:ax.plot(*zip(*path),'b.-')
for k,q in [('road',start),('gate',gate),('door',end)]:ax.plot(*q,'go');ax.text(*q,k)
ax.set_aspect('equal');fig.savefig(OUT/'plan.png');print('paths',simplified,flush=True)
