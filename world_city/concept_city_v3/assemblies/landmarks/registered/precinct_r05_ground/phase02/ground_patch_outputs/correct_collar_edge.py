"""One-time parent-authorized exact road-edge correction; no native/scene changes."""
import importlib.util,json,math,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('ground',HERE/'ground_patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.load(HERE/'collar_design.json');poly=c['polygon_xz_m'];scene=m.f.load_scene();idx=m.f.SurfaceIndex(scene,windows=[m.f.bounds(poly)],margin=.1)
a,b=poly[:2];d=[b[k]-a[k]for k in(0,1)];rows=[r for r in idx.records if r['material']=='road'];parts=[];cuts=[0.,1.]
for row in rows:
 hit=m.segment_interval(a,b,row['polygon_xz_m'])
 if hit:parts.append((row,hit));cuts+=list(hit)
cuts.sort();breaks=[]
for t in cuts:
 if not breaks or t-breaks[-1]>1e-10:breaks.append(t)
edge=[];ledger=[]
for lo,hi in zip(breaks,breaks[1:]):
 mid=[a[k]+d[k]*(lo+hi)/2 for k in(0,1)];rr=[r for r,iv in parts if iv[0]-1e-10<(lo+hi)/2<iv[1]+1e-10]
 assert rr,(lo,hi)
 r=rr[0];p0=[a[k]+d[k]*lo for k in(0,1)];p1=[a[k]+d[k]*hi for k in(0,1)];v0=[p0[0],m.a.height(r['plane_y_xz_m'],p0),p0[1]];v1=[p1[0],m.a.height(r['plane_y_xz_m'],p1),p1[1]]
 if not edge:edge.append(v0)
 else:assert math.dist(edge[-1],v0)<1e-8
 edge.append(v1);ledger.append({'parameter_interval':[lo,hi],'source_road_triangle':{'material':r['material'],'triangle_index':r['triangle_index'],'sha256':r['source_triangle_sha256']},'plane_y_xz_m':r['plane_y_xz_m'],'endpoints_xyz_m':[v0,v1]})
upper=[poly[2][0],8.1,poly[2][1]];other=[poly[3][0],8.1,poly[3][1]]
tris=[m.f.upward([u,v,upper])for u,v in zip(edge,edge[1:])]+[m.f.upward([edge[0],upper,other])]
grades=[math.hypot(*m.a.plane(t)[:2])for t in tris];assert max(grades)<.12
reject=m.OUT/'rejected_collar_mixed_edge.json'
if reject.exists():raise ValueError('Mixed-edge rejection is already preserved; do not repeat correction blindly')
shutil.copyfile(HERE/'collar_design.json',reject)
c.update(triangles=[{'triangle_xyz_m':t,'grade':g}for t,g in zip(tris,grades)],actual_road_edge_segments=ledger,maximum_grade=max(grades),all_gradients_below_12percent=True,source_mixed_edge_rejection=m.reference(reject),status='Exact actual-road seam correction; same finite domain and native stair datum; terrain application pending.')
(HERE/'collar_design.json').write_text(json.dumps(c,indent=2,allow_nan=False)+'\n')
print(json.dumps({'collar':m.reference(HERE/'collar_design.json'),'road_edge_segments':ledger,'maximum_grade':max(grades),'domain_area_m2':m.geo.polygon_area(poly)},indent=2))
