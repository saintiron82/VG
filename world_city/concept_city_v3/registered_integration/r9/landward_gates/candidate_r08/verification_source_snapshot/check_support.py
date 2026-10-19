import json,math,sys
from pathlib import Path
import numpy as np
from .build_corridors import Ground,xz,plane,ph,sha,ref
from .check_candidates import transform
from world_city.runtime_city.checks import placement as geo
H=Path(__file__).parent
C=H/(sys.argv[1]if len(sys.argv)>1 else 'candidate_r01')
p=json.load(open(C/'surface_patch.json'));r=json.load(open(C/'routes.json'));rows=json.load(open(H/'local_source_faces.json'));edits={(e['material'],e['triangle_index']):e for e in p['surface_edits']};resolved=[];bad=[]
for row in rows:
 for t in edits.get((row['material'],row['triangle_index']),{}).get('replacement_triangles_xyz_m',[row['triangle']]):resolved.append(dict(row,triangle=t))
for m,vs in p['appended_surfaces'].items():
 for i in range(0,len(vs),3):
  t=vs[i:i+3];resolved.append(dict(material=m,triangle_index=i//3,triangle=t))
  a=np.asarray(t,dtype=np.float32);n=np.cross(a[1]-a[0],a[2]-a[0])
  if not np.any(n):bad.append([m,i//3,t])
g=Ground(resolved);bridge=p['ownership'][-1]['polygon_xz_m']
def at(q):
 if geo.point_in_convex_polygon(q,bridge,1e-7):return 3.
 return g.at(q)
results=[]
for route in r['routes']:
 fails=[];maxdelta=0;maxresid=0
 for k,(a,b)in enumerate(zip(route['points'],route['points'][1:])):
  ll=math.dist(xz(a),xz(b));u=[(b[i]-a[i])/ll for i in [0,2]];v=[-u[1],u[0]]
  for j in range(max(1,math.ceil(ll/.5))):
   f=j/max(1,math.ceil(ll/.5));c=[a[i]+f*(b[i]-a[i])for i in range(3)];support=[]
   try:
    cy=at(xz(c));delta=cy-c[1];maxdelta=max(maxdelta,abs(delta))
    for s,t in [(-1,-1),(-1,1),(1,1),(1,-1)]:
     q=[c[i]+u[k0]*s*1.25+v[k0]*t*.75 for k0,i in enumerate([0,2])];support.append([q[0],at(q),q[1]])
    vals=np.asarray(support);X=np.c_[vals[:,0]-c[0],vals[:,2]-c[2],np.ones(4)];Y=vals[:,1];fit=np.linalg.lstsq(X,Y,rcond=None)[0];resid=float(max(abs(X@fit-Y)));maxresid=max(resid,maxresid)
    if abs(delta)>.2 or resid>.05:fails.append(dict(segment=k,t=f,center=c,support=support,center_delta=delta,plane_residual=resid))
   except ValueError as e:fails.append(dict(segment=k,t=f,center=c,error=str(e)))
 results.append(dict(id=route['id'],max_center_height_delta_m=maxdelta,max_support_plane_residual_m=maxresid,failures=fails))
out=dict(scope='diagnostic terrain and bridge top sample; native side collisions require runtime',candidate=ref(C/'routes.json'),float32_degenerate_appended_triangles=bad,routes=results)
(C/'support_diagnostic.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps({'float32_degenerate':len(bad),'routes':[{k:v for k,v in r.items()if k!='failures'}|{'failures':len(r['failures'])}for r in results]},indent=2))
