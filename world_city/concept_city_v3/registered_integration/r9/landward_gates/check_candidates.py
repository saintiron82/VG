import json,math
from pathlib import Path
from world_city.runtime_city.checks import placement as g
H=Path(__file__).parent;ROOT=H.parents[4];s=json.load(open(H/'base_context.json'));bs=json.load(open(H/'asset_bounds.json'))
def transform(v,i):
 x,y,z=i['position_m'];c,si=math.cos(i['yaw_rad']),math.sin(i['yaw_rad']);return [x+c*v[0]+si*v[2],y+v[1],z-si*v[0]+c*v[2]]
def strip(a,b,w=4):
 dx,dz=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dz);nx,nz=-dz/l*w,dx/l*w;return [[a[0]+nx,a[1]+nz],[b[0]+nx,b[1]+nz],[b[0]-nx,b[1]-nz],[a[0]-nx,a[1]-nz]]
def crosses(a,b,c,d):
 u=[b[0]-a[0],b[1]-a[1]];v=[d[0]-c[0],d[1]-c[1]];den=u[0]*v[1]-u[1]*v[0]
 if abs(den)<1e-12:return min(g.point_segment_distance(a,c,d),g.point_segment_distance(b,c,d),g.point_segment_distance(c,a,b),g.point_segment_distance(d,a,b))<1e-7
 t=((c[0]-a[0])*v[1]-(c[1]-a[1])*v[0])/den;s=((c[0]-a[0])*u[1]-(c[1]-a[1])*u[0])/den
 return -1e-8<=t<=1+1e-8 and -1e-8<=s<=1+1e-8

def intersects(a,b):
 if g.polygon_area(a)>1e-8:return g.positive_area_overlap(a,b,0)
 if any(g.point_in_convex_polygon(p,b,1e-7)for p in a):return True
 return any(crosses(p,q,r,t) for p,q in zip(a,a[1:]+a[:1])for r,t in zip(b,b[1:]+b[:1]))
if __name__=='__main__':
 for name,pts in [('W_GAP',[[-400.106,-232.022],[-389,-228],[-361,-237],[-330,-225],[-300,-215],[-273.02884,-197.71714]])]:
  strips=[strip(a,b,3.0)for a,b in zip(pts,pts[1:])];print(name,flush=True)
  for i in s['common_instances']:
   b=bs[i['asset_key']];poly=[transform([xx,0,zz],i)for xx,zz in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]]
   if not any(g.positive_area_overlap([[p[0],p[2]]for p in poly],st,0)for st in strips):continue
   r=json.load(open(ROOT/s['common_assets'][i['asset_key']]['render_path']));hits=[]
   for group in r['groups']:
    for q in group['quads']:
     q=[transform(v,i)for v in q];xz=[[v[0],v[2]]for v in q]
     if any(intersects(xz,st)for st in strips):hits.append((min(v[1]for v in q),max(v[1]for v in q),xz))
   print(i['id'],'quad_hits',len(hits),'y_range',[round(min(q[0]for q in hits),3),round(max(q[1]for q in hits),3)]if hits else None,flush=True)
