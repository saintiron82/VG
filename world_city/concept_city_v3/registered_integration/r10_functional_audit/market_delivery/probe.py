import json,math
from pathlib import Path
import numpy as np
from world_city.concept_city_v3.registered_integration.r9.market_clusters.author import Context,corridor
from world_city.runtime_city.checks import placement as g
H=Path(__file__).resolve().parent;R=H.parents[4];M=H.parents[1]/'r9/market_clusters'
def load(p):return json.loads(p.read_bytes())
def bez(a,b,c,d,n=40):return [[(1-t)**3*a[k]+3*(1-t)**2*t*b[k]+3*(1-t)*t*t*c[k]+t**3*d[k]for k in (0,1)]for t in np.linspace(0,1,n+1)]
def route():
 p0=[91.41505784216918+(10.75638652919374-5)*11.09509136742555/19.71863098455343,5]
 t=[7/math.sqrt(58),3/math.sqrt(58)];n=[t[1],-t[0]];B=[110,3];O=[102.51014920959473,-8.96224445535969];d=[4.5136560353815,2.06543353739945];cross=lambda a,b:a[0]*b[1]-a[1]*b[0];radius=-cross([B[k]-O[k]for k in(0,1)],d)/(2*cross(n,d));C=[B[k]+radius*n[k]for k in(0,1)];theta=math.atan2(B[1]-C[1],B[0]-C[0]);arc=[[C[0]+radius*math.cos(theta-a),C[1]+radius*math.sin(theta-a)]for a in np.linspace(0,math.pi,64)]
 exitp=arc[-1];J=[105.5,O[1]+(105.5-O[0])*d[1]/d[0]];Q=[99.75,10.75638652919374-(99.75-91.41505784216918)*19.71863098455343/11.09509136742555]
 return bez(p0,[97.1,.65],[100.2,-1.2],[103,0])+[[103+7*t,3*t]for t in np.linspace(0,1,32)[1:]]+arc[1:]+[[exitp[k]+tt*(J[k]-exitp[k])for k in (0,1)]for tt in np.linspace(0,1,40)[1:]]+bez(J,[103.2,J[1]-2.3*d[1]/d[0]],[101.2,Q[1]-1.45*19.71863098455343/11.09509136742555],Q)[1:]+[[Q[k]+tt*(p0[k]-Q[k])for k in (0,1)]for tt in np.linspace(0,1,50)[1:]]

def run():
 ctx=Context();l=load(M/'layout.json');p=load(M/'pack.json');pts=route();polys=corridor(pts,3.5)
 solids=ctx.solids+[dict(id=s['id'],polygon=s['footprint_xz_m'],y_min=s['native_bottom_y_m'],y_max=s['native_top_y_m'])for s in p['add_instances']]
 near=lambda poly:min(v[0]for v in poly)<125 and max(v[0]for v in poly)>90 and min(v[1]for v in poly)<12 and max(v[1]for v in poly)>-8
 solids=[s for s in solids if near(s['polygon'])];res=[s for s in ctx.res if near(s['polygon'])]
 links=[(s,corridor(s['path_xz_m'],s['width_m']))for s in l['routes']if near(s['path_xz_m'])]
 print('entry',pts[0],'exit',pts[-1],'length',sum(math.dist(a,b)for a,b in zip(pts,pts[1:])))
 print('solid', sorted(set(s['id']for s in solids if any(g.positive_area_overlap(q,s['polygon'],0)for q in polys))))
 print('res',sorted(set(s['id']for s in res if any(g.positive_area_overlap(q,s['polygon'],0)for q in polys))))
 print('links',sorted(set(s['id']for s,pp in links if any(g.positive_area_overlap(q,p,0)for q in polys for p in pp))))
 support=[]
 for i,(a,b)in enumerate(zip(pts,pts[1:])):
  dx,dz=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dz);dx/=L;dz/=L
  for o in [-1.75,-.9,0,.9,1.75]:
   x,z=a[0]-dz*o,a[1]+dx*o
   if ctx.height(x,z) is None:support.append([i,x,z])
 print('unsupported',len(support),support[:20])
 if __name__=='__main__':
  import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
  from matplotlib.patches import Polygon
  fig,ax=plt.subplots(figsize=(10,8))
  for s in res:ax.add_patch(Polygon(s['polygon'],fc='#ddd8bf',alpha=.4))
  for s in solids:ax.add_patch(Polygon(s['polygon'],fc='#786f61'))
  for s,pp in links:
   for poly in pp:ax.add_patch(Polygon(poly,fc='#d1c4d9',alpha=.3))
  for poly in polys:ax.add_patch(Polygon(poly,fc='#78b9c9',alpha=.2))
  ax.plot(*zip(*pts),color='#174b58');ax.set_xlim(90,130);ax.set_ylim(18,-12);ax.set_aspect('equal');ax.grid();fig.savefig(H/'probe.png',dpi=140)
run()
