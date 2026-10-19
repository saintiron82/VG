"""Finite B015 half-metre planning raster; exact vectors retained for handoff."""
from .design import *
import numpy as np
from scipy import ndimage
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_source.geometry import triangulate
GRID=.5;BOUNDS=[60.,100.,400.,400.];NX=round((BOUNDS[2]-BOUNDS[0])/GRID);NZ=round((BOUNDS[3]-BOUNDS[1])/GRID);SHAPE=(NZ,NX)
XS=BOUNDS[0]+(np.arange(NX)+.5)*GRID;ZS=BOUNDS[1]+(np.arange(NZ)+.5)*GRID

def raster(ps,touch=False,concave=False):
 out=np.zeros(SHAPE,bool)
 for raw in ps:
  for p in(triangulate(raw)if concave else[raw]):
   x0=max(0,int(math.floor((min(q[0]for q in p)-BOUNDS[0])/GRID)));x1=min(NX,int(math.ceil((max(q[0]for q in p)-BOUNDS[0])/GRID)))
   z0=max(0,int(math.floor((min(q[1]for q in p)-BOUNDS[1])/GRID)));z1=min(NZ,int(math.ceil((max(q[1]for q in p)-BOUNDS[1])/GRID)))
   if x0>=x1 or z0>=z1:continue
   hit=np.ones((z1-z0,x1-x0),bool);sgn=1 if geo.signed_polygon_area(p)>0 else -1
   for a,b in zip(p,p[1:]+p[:1]):
    dx,dz=b[0]-a[0],b[1]-a[1];val=sgn*(dx*(ZS[z0:z1,None]-a[1])-dz*(XS[None,x0:x1]-a[0]));margin=-GRID*.5*(abs(dx)+abs(dz))if touch else 0;hit&=val>=margin-1e-8
   out[z0:z1,x0:x1]|=hit
 return out

def parts(m):
 out=[];active={};zz,xx=np.where(m)
 if not len(xx):return[]
 for z in range(int(zz.min()),int(zz.max())+2):
  row=m[z]if z<NZ else np.zeros(NX,bool);edges=np.flatnonzero(np.diff(np.r_[False,row,False]));runs=list(zip(edges[::2],edges[1::2]));new={}
  for run in runs:new[run]=active.pop(run,z)
  for(x0,x1),z0 in active.items():out.append(rect(BOUNDS[0]+int(x0)*GRID,BOUNDS[1]+z0*GRID,BOUNDS[0]+int(x1)*GRID,BOUNDS[1]+z*GRID))
  active=new
 return out

def ribbons(line,width,caps=True):
 out=[geo.road_ribbon(a,b,width)for a,b in zip(line,line[1:])if math.dist(a,b)>1e-8]
 for p in(line if caps else line[1:-1]):
  r=width/2/math.cos(math.pi/16);out.append([[p[0]+r*math.cos(i*math.pi/8),p[1]+r*math.sin(i*math.pi/8)]for i in range(16)])
 return out

def transform(ps,c,yaw):return[[xform(q,c,yaw)for q in p]for p in ps]
def area(m):return int(m.sum())*GRID*GRID
def cell(q):return(int((q[1]-BOUNDS[1])/GRID),int((q[0]-BOUNDS[0])/GRID))
def point(q):return[float(XS[q[1]]),float(ZS[q[0]])]
def local_box(a,margin=0):
 b=a['bounds'];return rect(b['min'][0]-margin,b['min'][2]-margin,b['max'][0]+margin,b['max'][2]+margin)
def nearest(free,q,maxdist=10):
 z,x=cell(q);r=int(math.ceil(maxdist/GRID));z0=max(0,z-r);z1=min(NZ,z+r+1);x0=max(0,x-r);x1=min(NX,x+r+1);zz,xx=np.where(free[z0:z1,x0:x1]);zz+=z0;xx+=x0
 if not len(xx):return None
 dd=(XS[xx]-q[0])**2+(ZS[zz]-q[1])**2;i=int(np.argmin(dd));return(int(zz[i]),int(xx[i]))if dd[i]<=maxdist**2 else None

def astar(free,start,goals):
 import heapq
 if start is None:return None
 dist=ndimage.distance_transform_edt(~goals)*GRID;queue=[(dist[start],0,start)];cost={start:0};prev={};end=None
 while queue:
  _,g,q=heapq.heappop(queue)
  if g!=cost[q]:continue
  if goals[q]:end=q;break
  z,x=q
  for dz,dx in[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   nz,nx=z+dz,x+dx
   if not(0<=nz<NZ and 0<=nx<NX)or not free[nz,nx]:continue
   if dz and dx and(not free[z,nx]or not free[nz,x]):continue
   t=(nz,nx);ng=g+(math.sqrt(2)if dz and dx else 1)*GRID
   if ng<cost.get(t,math.inf):cost[t]=ng;prev[t]=q;heapq.heappush(queue,(ng+dist[t],ng,t))
 if end is None:return None
 path=[end]
 while end in prev:end=prev[end];path.append(end)
 path=path[::-1];out=[path[0]]
 for i in range(1,len(path)-1):
  a,b,c=path[i-1:i+2]
  if(b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):out.append(b)
 return[point(p)for p in out+[path[-1]]]
