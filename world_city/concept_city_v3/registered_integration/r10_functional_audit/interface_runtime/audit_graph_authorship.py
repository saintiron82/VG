"""Independent exact-source provenance check for the bounded public T probe."""
import math
from pathlib import Path
import prepare as prep

def verify(request):
 g=prep.read(prep.resolve(request['producer_sources']['graph']))
 rows=prep.read(prep.resolve(request['producer_sources']['registration']))
 j=next(x for x in rows if x['source_node']==10836)
 assert j['horizontal_gap_m'] <= 0.00005 if 'horizontal_gap_m' in j else True
 nodes=g['nodes_xyz_m']; source=nodes[j['source_node']]
 routes={r['id']:i for i,r in enumerate(g['routes'])}
 allowed=['ROAD:BLOCK_011:ALLEY','ROAD:CIVIC_WEST_APPROACH']
 segments={rid:[(nodes[e['u']],nodes[e['v']]) for e in g['edges'] if routes[rid] in e['route_indices']] for rid in allowed}
 def close(p,rid):
  best=None
  for a,b in segments[rid]:
   vx,vz=b[0]-a[0],b[2]-a[2];d=vx*vx+vz*vz
   t=max(0.,min(1.,((p[0]-a[0])*vx+(p[2]-a[2])*vz)/d)) if d else 0.
   q=[a[k]+t*(b[k]-a[k]) for k in range(3)]
   item=(math.hypot(p[0]-q[0],p[2]-q[2]),abs(p[1]-q[1]))
   if best is None or item[0]<best[0]:best=item
  assert best[0] <= 0.00005 and best[1] <= 0.020,(p,rid,best)
 for r in request['routes']:
  assert r['source_road_ids']==allowed and not r['cart_test'] and r['both_directions']
  pts=r['points'];turn=pts.index(source);assert 0<turn<len(pts)-1
  for side,(lo,hi) in enumerate(((0,turn),(turn,len(pts)-1))):
   length=sum(math.hypot(pts[i+1][0]-pts[i][0],pts[i+1][2]-pts[i][2])for i in range(lo,hi))
   assert abs(length-3.) < 0.000001,(side,length)
   for i in range(lo,hi):
    a,b=pts[i:i+2];n=max(1,math.ceil(math.dist(a,b)/.25))
    for k in range(n+1):close([a[c]+(b[c]-a[c])*k/n for c in range(3)],allowed[side])
 return {r['id']:r for r in request['routes']}
