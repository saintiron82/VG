"""Small exact upper-envelope regression tests; no filesystem writes."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[8];sys.path.insert(0,str(ROOT))
from upper_surface_support import Support,terrain,geo

def surface(poly,fn):return[v for tri in terrain.fan_upward([[x,fn(x,z),z]for x,z in poly])for v in tri]
def test():
 square=[[-1,-1],[1,-1],[1,1],[-1,1]]
 scene={'surfaces':{'ascending':surface(square,lambda x,z:x),'descending':surface(square,lambda x,z:-x)}}
 index=Support(scene,[square],{});rows=list(index.covering(square));assert abs(sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in rows)-4)<1e-10
 for r in rows:
  for x,z in r['intersection_polygon_xz_m']:assert abs(terrain.common.height(r['plane_y_xz_m'],[x,z])-abs(x))<1e-10
 scene={'surfaces':{'a':surface(square,lambda x,z:1),'b':surface(square,lambda x,z:1)}}
 rows=list(Support(scene,[square],{}).covering(square));assert abs(sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in rows)-4)<1e-10
 small=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]];scene={'surfaces':{'ground':surface(square,lambda x,z:0)}};native={'native:raised':surface(small,lambda x,z:2)};rows=list(Support(scene,[square],native).covering(square));assert abs(sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in rows)-4)<1e-10;assert abs(sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in rows if r['material']=='native:raised')-1)<1e-10
 print('PASS: crossing slope dominance, duplicate coplanar ownership, raised native ownership')
if __name__=='__main__':test()
