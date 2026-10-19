"""Audit actual resolved surface heights along route center and cart wheel tracks."""
import json,math,sys
from pathlib import Path
from .build_corridors import Ground,xz,ref,ph
from world_city.runtime_city.checks import placement as geo
H=Path(__file__).parent;C=H/sys.argv[1];p=json.load(open(C/'surface_patch.json'));routes=json.load(open(C/'routes.json'))['routes'];base=json.load(open(H/'local_source_faces.json'));edits={(e['material'],e['triangle_index']):e for e in p['surface_edits']};rows=[]
for r in base:
 for t in edits.get((r['material'],r['triangle_index']),{}).get('replacement_triangles_xyz_m',[r['triangle']]):rows.append(dict(r,triangle=t))
rows.extend(dict(material=m,triangle_index=i//3,triangle=vs[i:i+3])for m,vs in p['appended_surfaces'].items()for i in range(0,len(vs),3));g=Ground(rows);bridge=next(o['polygon_xz_m']for o in p['ownership']if o['id']=='EAST_NATIVE_CANAL_BRIDGE');result=[]
def height(q):
 found=[r for i in g.idx.candidates([q])if geo.point_in_convex_polygon(q,(r:=g.rows[i])['polygon'],1e-8)];heights=[ph(r['plane'],q)for r in found]
 if geo.point_in_convex_polygon(q,bridge,1e-7):heights.append(3.)
 if not heights:raise ValueError(q)
 return max(heights)
for r in routes:
 pts=[];distance=0
 for a,b in zip(r['points'],r['points'][1:]):
  ll=math.dist(xz(a),xz(b));n=max(1,math.ceil(ll/.1));normal=[-(b[2]-a[2])/ll,(b[0]-a[0])/ll]
  for j in range(n):
   t=j/n;q=[a[k]+t*(b[k]-a[k])for k in range(3)];pts.append([distance+ll*t,q[0],q[2],normal])
  distance+=ll
 q=r['points'][-1];pts.append([distance,q[0],q[2],normal]);tracks=[]
 for offset in [0.,-.75,.75]:
  samples=[[s,x+offset*n[0],height([x+offset*n[0],z+offset*n[1]]),z+offset*n[1]]for s,x,z,n in pts];pairs=[dict(from_arc_xyz_m=a,to_arc_xyz_m=b,grade=abs(b[2]-a[2])/math.dist([a[1],a[3]],[b[1],b[3]]))for a,b in zip(samples,samples[1:])if math.dist([a[1],a[3]],[b[1],b[3]])>1e-6];peak=max(pairs,key=lambda a:a['grade']);tracks.append(dict(offset_m=offset,peak=peak));print(r['id'],offset,peak)
 result.append(dict(id=r['id'],tracks=tracks))
(C/'actual_lane_surface_audit.json').write_text(json.dumps(dict(sources=dict(patch=ref(C/'surface_patch.json'),routes=ref(C/'routes.json')),scope='Highest resolved triangle or native bridge top, <=0.1m samples, 0 and +/-0.75m wheel-track offsets; geometric audit only',routes=result),separators=(',',':'))+'\n')
