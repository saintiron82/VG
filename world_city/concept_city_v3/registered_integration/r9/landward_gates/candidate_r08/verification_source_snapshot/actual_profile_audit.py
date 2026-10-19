"""Direct finite top support grades, including exact source replacement faces."""
import json,math,sys
from pathlib import Path
from .build_corridors import Ground,xz,ref
from world_city.runtime_city.checks import placement as geo
H=Path(__file__).parent;C=H/sys.argv[1];p=json.load(open(C/'surface_patch.json'));routes=json.load(open(C/'routes.json'))['routes'];base=json.load(open(H/'local_source_faces.json'));edits={(e['material'],e['triangle_index']):e for e in p['surface_edits']};rows=[]
for r in base:
 for t in edits.get((r['material'],r['triangle_index']),{}).get('replacement_triangles_xyz_m',[r['triangle']]):rows.append(dict(r,triangle=t))
rows.extend(dict(material=m,triangle_index=i//3,triangle=vs[i:i+3])for m,vs in p['appended_surfaces'].items()for i in range(0,len(vs),3));g=Ground(rows);bridge=next(o['polygon_xz_m']for o in p['ownership']if o['id']=='EAST_NATIVE_CANAL_BRIDGE');result=[]
def height(q):
 if geo.point_in_convex_polygon(q,bridge,1e-7):return 3.
 return g.at(q)
for r in routes:
 pts=[];distance=0
 for a,b in zip(r['points'],r['points'][1:]):
  ll=math.dist(xz(a),xz(b));n=max(1,math.ceil(ll/.25))
  for j in range(n):
   t=j/n;q=[a[k]+t*(b[k]-a[k])for k in range(3)];pts.append([distance+ll*t,q[0],height(xz(q)),q[2]])
  distance+=ll
 q=r['points'][-1];pts.append([distance,q[0],height(xz(q)),q[2]]);segs=[dict(index=i,from_arc_xyz_m=a,to_arc_xyz_m=b,grade=abs(b[2]-a[2])/(b[0]-a[0]))for i,(a,b)in enumerate(zip(pts,pts[1:]))];peak=max(segs,key=lambda v:v['grade']);result.append(dict(id=r['id'],support_sample_spacing_max_m=.25,peak=peak,samples_arc_xyz_m=pts,above_10_5_percent_length_m=sum(v['to_arc_xyz_m'][0]-v['from_arc_xyz_m'][0]for v in segs if v['grade']>.105)));print(r['id'],peak)
(C/'actual_support_arc_profiles.json').write_text(json.dumps(dict(sources=dict(patch=ref(C/'surface_patch.json'),routes=ref(C/'routes.json')),scope='Exact resolved ground plus native-bridge top sampled at <=0.25m; unchanged road/grass source faces participate, no sparse-waypoint height inference',routes=result),separators=(',',':'))+'\n')
