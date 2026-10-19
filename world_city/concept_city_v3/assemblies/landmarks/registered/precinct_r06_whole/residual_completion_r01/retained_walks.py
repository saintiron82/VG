"""Exact retained native service treads, selected by finite source ownership."""
from pathlib import Path
import sys,math
BASE=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(BASE))
from native_walks import *
class RetainedWalkIndex(CompositeSupportIndex):
 def __init__(self,scene,windows):
  super().__init__(scene,windows);vs=[];self.extra_sources=[]
  source=load(BASE/'actual_native_projection.json')
  for p in source['instances']:
   if p['asset_key']!='registered_training_r09_recovered_fine':continue
   ar=source['assets'][p['asset_key']];mesh=load(ROOT/ar['cache']['path']);self.extra_sources.append({'instance_id':p['id'],'cache':ar['cache'],'position_m':p['position_m'],'yaw_rad':p['yaw_rad']});cy,sy=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);x,y,z=p['position_m']
   for group in mesh['groups']:
    for q in group['quads']:
     if not all(abs(v[1]-q[0][1])<1e-8 for v in q)or q[0][1]<-1e-8 or q[0][1]>.5:continue
     if terrain.normal_y(q[:3])<=0:continue
     world=[[x+v[0]*cy-v[2]*sy,y+v[1],z+v[0]*sy+v[2]*cy]for v in q]
     for tri in terrain.fan_upward(world):vs.extend(tri)
  self.extra=terrain.TriangleIndex({'surfaces':{'retained_training_service_tread':vs}},windows)
 def covering(self,poly):
  rows=list(super().covering(poly));claimed=[r['intersection_polygon_xz_m']for r in rows]
  for r in rows:yield r
  for r in self.extra.covering(poly):
   for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
    if geo.polygon_area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
