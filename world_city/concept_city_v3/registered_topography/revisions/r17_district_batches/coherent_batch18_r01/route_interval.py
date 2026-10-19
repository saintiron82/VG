"""Finite segment clipping with a distance-scaled coincident-edge predicate.

Only points within 1e-10 m of the same edge are treated as incident. All true
crossing parameters use the original line equation, without expanding masks.
"""
import math
from .. import author as a

def interval(p,q,poly):
 sign=1 if a.geo.signed_polygon_area(poly)>0 else -1;lo,hi=0.,1.;eps=1e-10
 for u,v in zip(poly,poly[1:]+poly[:1]):
  length=math.dist(u,v)
  if length<1e-12:continue
  f=sign*a.geo._cross(u,v,p)/length;g=sign*a.geo._cross(u,v,q)/length;d=g-f
  if max(abs(f),abs(g))<=eps:continue
  if abs(d)<1e-14:
   if f< -eps:return None
  else:
   t=-f/d
   if d>0:lo=max(lo,t)
   else:hi=min(hi,t)
  if lo>hi+1e-12:return None
 return [max(0.,lo),min(1.,hi)]if hi-lo>1e-10 else None
