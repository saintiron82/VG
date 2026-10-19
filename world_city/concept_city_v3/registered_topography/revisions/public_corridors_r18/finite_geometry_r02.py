"""Bounded finite convex overlay with distance-independent sign classification.
Unlike the legacy cross-product epsilon, short edges retain their true side.
No mask expansion, coordinate snapping, or physical tolerance is applied.
"""
import math
from decimal import Decimal,localcontext
MIN_AREA=1e-14

def cross(a,b,p):
 x=(b[0]-a[0])*(p[1]-a[1]);y=(b[1]-a[1])*(p[0]-a[0]);v=x-y
 if abs(v)>1e-14*(abs(x)+abs(y)+1e-30):return v
 with localcontext()as c:
  c.prec=60;A=list(map(Decimal.from_float,map(float,a)));B=list(map(Decimal.from_float,map(float,b)));P=list(map(Decimal.from_float,map(float,p)))
  return float((B[0]-A[0])*(P[1]-A[1])-(B[1]-A[1])*(P[0]-A[0]))
def signed_area(p):
 if len(p)<3:return 0.
 o=p[0];return math.fsum((u[0]-o[0])*(v[1]-o[1])-(u[1]-o[1])*(v[0]-o[0])for u,v in zip(p,p[1:]+p[:1]))/2
def area(p):return abs(signed_area(p))
def clean(p):
 q=[]
 for v in p:
  if not q or v!=q[-1]:q.append(list(v))
 if len(q)>1 and q[0]==q[-1]:q.pop()
 return q if len(q)>=3 and area(q)>MIN_AREA else[]
def half(p,a,b,sign,inside):
 out=[]
 if not p:return out
 u=p[-1];du=sign*cross(a,b,u);iu=du>=0 if inside else du<=0
 for v in p:
  dv=sign*cross(a,b,v);iv=dv>=0 if inside else dv<=0
  if iu!=iv:
   t=du/(du-dv);out.append([u[k]+t*(v[k]-u[k])for k in(0,1)])
  if iv:out.append(v)
  u,du,iu=v,dv,iv
 return clean(out)
def normalize_mask(p):
 out=[]
 for v in p:
  if not out or math.dist(out[-1],v)>1e-12:out.append(v)
 while len(out)>1 and math.dist(out[0],out[-1])<=1e-12:out.pop()
 return out

def clip(p,q):
 q=normalize_mask(q)
 if len(q)<3 or area(q)<=MIN_AREA:return[]
 sign=1 if signed_area(q)>0 else -1;out=p
 for a,b in zip(q,q[1:]+q[:1]):
  if a==b:continue
  out=half(out,a,b,sign,True)
  if not out:break
 return out
def difference(p,q):
 q=normalize_mask(q)
 if len(q)<3 or area(q)<=MIN_AREA:return[p]
 sign=1 if signed_area(q)>0 else -1;inside=p;out=[]
 for a,b in zip(q,q[1:]+q[:1]):
  if a==b:continue
  part=half(inside,a,b,sign,False)
  if part:out.append(part)
  inside=half(inside,a,b,sign,True)
  if not inside:break
 return out
def subtract(ps,masks):
 out=ps
 for mask in masks:
  new=[]
  for p in out:
   if clip(p,mask):new.extend(difference(p,mask))
   else:new.append(p)
  out=new
  if not out:break
 return out
def union(ps):
 out=[]
 for p in ps:out.extend(subtract([p],out))
 return out
