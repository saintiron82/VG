"""Small independent 2D source-check geometry. No source author imports."""
import math
EPS=1e-8

def area(poly):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))/2) if len(poly)>2 else 0.
def signed_area(poly):return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))/2
def ccw(poly):return poly if signed_area(poly)>=0 else list(reversed(poly))
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return [a[0]-b[0],a[1]-b[1]]
def convex_intersection(subject,clip):
 out=[list(v) for v in subject]
 for a,b in zip(ccw(clip),ccw(clip)[1:]+ccw(clip)[:1]):
  inside=[]
  if not out:break
  prev=out[-1];pv=cross(sub(b,a),sub(prev,a))
  for cur in out:
   cv=cross(sub(b,a),sub(cur,a))
   if (pv>=-EPS)!=(cv>=-EPS):
    t=pv/(pv-cv);inside.append([prev[i]+(cur[i]-prev[i])*t for i in (0,1)])
   if cv>=-EPS:inside.append(cur)
   prev,pv=cur,cv
  out=inside
 return out

def ribbon(a,b,width):
 dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
 if length<EPS:return []
 nx,nz=-dz/length*width/2,dx/length*width/2
 return [[a[0]+nx,a[1]+nz],[a[0]-nx,a[1]-nz],[b[0]-nx,b[1]-nz],[b[0]+nx,b[1]+nz]]

def closest_point(point,a,b):
 v=sub(b,a);d=v[0]*v[0]+v[1]*v[1]
 t=max(0.,min(1.,sum((point[i]-a[i])*v[i] for i in (0,1))/d)) if d>EPS else 0.
 q=[a[i]+t*v[i] for i in (0,1)];return math.dist(point,q),q,t

def segment_hit(a,b,c,d):
 u,v=sub(b,a),sub(d,c);den=cross(u,v)
 if abs(den)<EPS:return None
 t=cross(sub(c,a),v)/den;s=cross(sub(c,a),u)/den
 if -EPS<=t<=1+EPS and -EPS<=s<=1+EPS:return [a[0]+t*u[0],a[1]+t*u[1]],t,s
 return None

def segment_distance(a,b,c,d):
 hit=segment_hit(a,b,c,d)
 if hit:return 0.,hit[0],hit[0]
 candidates=[]
 for p,x,y,rev in [(a,c,d,False),(b,c,d,False),(c,a,b,True),(d,a,b,True)]:
  dist,q,t=closest_point(p,x,y);candidates.append((dist,q,p) if rev else (dist,p,q))
 return min(candidates,key=lambda v:v[0])

def line_distance(p,q):
 return min((segment_distance(a,b,c,d) for a,b in zip(p,p[1:]) for c,d in zip(q,q[1:])),key=lambda v:v[0])
def point_line_distance(point,line):return min((closest_point(point,a,b) for a,b in zip(line,line[1:])),key=lambda v:v[0])
def point_inside(point,poly,tol=EPS):
 """Boundary-inclusive winding test for a simple, possibly concave polygon."""
 if len(poly)<3:return False
 winding=0
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if closest_point(point,a,b)[0]<=tol:return True
  side=cross(sub(b,a),sub(point,a))
  if a[1]<=point[1]<b[1] and side>0:winding+=1
  elif b[1]<=point[1]<a[1] and side<0:winding-=1
 return winding!=0

def triangulate(poly):
 """Ear-clip simple source polygons; reject degenerate/self-crossing inputs.

 This is audit geometry, never a render or voxel compiler. Collinear vertices
 are removed without moving the finite boundary.
 """
 points=[]
 for p in poly:
  if not points or math.dist(points[-1],p)>EPS:points.append(list(p))
 if len(points)>1 and math.dist(points[0],points[-1])<=EPS:points.pop()
 changed=True
 while changed and len(points)>3:
  changed=False
  for i,p in enumerate(points):
   if abs(cross(sub(p,points[i-1]),sub(points[(i+1)%len(points)],p)))<=EPS:
    points.pop(i);changed=True;break
 if len(points)<3 or area(points)<=EPS:raise ValueError('degenerate polygon')
 points=ccw(points);triangles=[]
 for i,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
  for j,(c,d) in enumerate(zip(points,points[1:]+points[:1])):
   if j<=i or (i-j)%len(points) in (1,len(points)-1):continue
   if segment_distance(a,b,c,d)[0]<=EPS:raise ValueError('self-intersecting polygon')
 while len(points)>3:
  for i,p in enumerate(points):
   a,b,c=points[i-1],p,points[(i+1)%len(points)]
   if cross(sub(b,a),sub(c,b))<=EPS:continue
   if any(point_inside(q,[a,b,c]) for j,q in enumerate(points) if j not in ((i-1)%len(points),i,(i+1)%len(points))):continue
   triangles.append([a,b,c]);points.pop(i);break
  else:raise ValueError('cannot triangulate simple polygon')
 triangles.append(points)
 return triangles

def intersection_area(a,b):
 """Area for any two simple polygons, including concave parcels."""
 return sum(area(convex_intersection(ta,tb)) for ta in triangulate(a) for tb in triangulate(b))
def bounds(poly):return [min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)]
def bbox_overlap(a,b):return a[0]<=b[2]+EPS and b[0]<=a[2]+EPS and a[1]<=b[3]+EPS and b[1]<=a[3]+EPS
