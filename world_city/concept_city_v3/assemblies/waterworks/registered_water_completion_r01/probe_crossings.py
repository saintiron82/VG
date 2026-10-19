import json,math
from .audit import *
from world_city.concept_city_v3.assemblies.waterworks.registered_services_r01.select_drawhouses import rect

def run():
 s=a.load_scene();c=json.loads(CONTRACT.read_text());out=[]
 for road in c['roads']:
  if road['id']not in ['MARKET_NORTH','NORTH_BACK_LANE','EAST_RADIAL','EAST_WALL_SERVICE']:continue
  for j,(u,v)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   for canal in c['water_surfaces']:
    if canal['id']not in ['NORTHERN_CHANNEL_VISIBLE','CRAFT_CANAL_VISIBLE']:continue
    for k,(b,d)in enumerate(zip(canal['polyline_xz_m'],canal['polyline_xz_m'][1:])):
     dx,dz=v[0]-u[0],v[1]-u[1];ex,ez=d[0]-b[0],d[1]-b[1];det=dx*(-ez)-(-ex)*dz
     if abs(det)<1e-8:continue
     rx,rz=b[0]-u[0],b[1]-u[1];t=(rx*(-ez)-(-ex)*rz)/det;tt=(dx*rz-rx*dz)/det
     if not(0<=t<=1 and 0<=tt<=1):continue
     o=[u[0]+t*dx,u[1]+t*dz];yaw=math.atan2(-dz,dx);out.append(dict(id=road['id'],road_segment=j,canal_id=canal['id'],canal_segment=k,position_xz_m=o,yaw_rad=yaw,road_width_m=road['width_m'],water_y_m=canal['levels_m'][k]+tt*(canal['levels_m'][k+1]-canal['levels_m'][k])))
 ix=a.TriangleIndex(s,[rect(*r['position_xz_m'],35)for r in out])
 from world_city.concept_city_v3.assemblies.waterworks.registered_mill_r01.select_site import pose as xzpose
 for r in out:
  samples=[]
  for d in [-25,-20,-15,-12,-10,-8,-6,-5,-4,-3,-2,0,2,3,4,5,6,8,10,12,15,20,25]:
   q=xzpose([d,0],r['position_xz_m'],r['yaw_rad']);vals=[]
   for k in ix.index.candidates(rect(*q,.001)):
    z=ix.rows[k]
    if g.point_in_convex_polygon(q,z['polygon_xz_m']):vals.append([z['material'],round(a.common.height(z['plane_y_xz_m'],q),6),z['triangle_index']])
   samples.append(dict(station_m=d,xz_m=q,actual_tops=vals))
  r['samples']=samples;print(r['id'],r['position_xz_m'],'water',r['water_y_m']);print([(x['station_m'],x['actual_tops'])for x in samples],flush=True)
 write('crossing_probes.json',dict(base_scene=ref(a.SCENE_PATH),candidates=out))
if __name__=='__main__':run()
