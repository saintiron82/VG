from pathlib import Path
import sys,json,math
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks.placement import *
from world_city.runtime_city.urban_fabric.author import rect,center,unit,add,mix

def offset(poly,inset):
 if signed_polygon_area(poly)<0:poly=list(reversed(poly))
 lines=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  u=unit(a,b);n=[-u[1],u[0]];lines.append((add(a,n,inset),u))
 out=[]
 for i,(p,u) in enumerate(lines):
  q,v=lines[i-1];den=u[0]*v[1]-u[1]*v[0];qp=[q[0]-p[0],q[1]-p[1]];t=(qp[0]*v[1]-qp[1]*v[0])/den;out.append(add(p,u,t))
 return out
if __name__=='__main__':
 scene=json.load(open(ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json'));fabric=json.load(open(ROOT/'world_city/runtime_city/urban_fabric/generated/urban_fabric.json'))
 nodes={p['id']:[p['position_m'][0],p['position_m'][2]] for p in scene['road_nodes']}
 obs={b['id']:transformed_aabb_xz_m(b['local_bounds'],b['position_m'],b['yaw_rad']) for b in scene['instances']}
 obs.update({r['id']:road_ribbon(nodes[r['from_node']],nodes[r['to_node']],r['width_m']) for r in scene['roads']})
 for p in fabric['properties'][:3]:
  print(p['id'])
  for inset in [-.25,0,.25,.5]:
   poly=offset(p['footprint_xz_m'],inset);hit={}
   for n,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
    ribbon=road_ribbon(a,b,1.25)
    for k,q in obs.items():
     if positive_area_overlap(ribbon,q,.01):hit.setdefault(n,[]).append(k)
   print(inset,hit)
