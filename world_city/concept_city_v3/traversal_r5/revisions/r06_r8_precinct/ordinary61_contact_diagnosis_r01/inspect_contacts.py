import json,math,hashlib,collections,itertools
from pathlib import Path
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as g
H=Path(__file__).resolve().parent;B=H.parent/'ordinary61_diagnostic_r01';ROOT=next(x for x in H.parents if(x/'voxel_character').exists())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def norm(t):
 a=[t[1][i]-t[0][i]for i in range(3)];b=[t[2][i]-t[0][i]for i in range(3)];n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];L=math.hypot(*n);return [v/L for v in n]if L else [0,0,0]
def plane(t):
 n=norm(t)
 if not n[1]:return None
 return[-n[0]/n[1],-n[2]/n[1],sum(n[i]*t[0][i]for i in range(3))/n[1]]
def height(p,v):return p[0]*v[0]+p[1]*v[1]+p[2]
def distance(p,u,v):
 d=[v[k]-u[k]for k in(0,1)];s=sum(x*x for x in d);f=max(0,min(1,sum((p[k]-u[k])*d[k]for k in(0,1))/s))if s else 0;return math.dist(p,[u[k]+f*d[k]for k in(0,1)])
def contains(p,poly):
 bb=[min(v[0]for v in poly),min(v[1]for v in poly),max(v[0]for v in poly),max(v[1]for v in poly)]
 if not bb[0]-1e-9<=p[0]<=bb[2]+1e-9 or not bb[1]-1e-9<=p[1]<=bb[3]+1e-9:return False
 return all(g.cross(u,v,p)>=-1e-9*math.dist(u,v)for u,v in zip(poly,poly[1:]+poly[:1]))if g.signed_area(poly)>0 else all(g.cross(u,v,p)<=1e-9*math.dist(u,v)for u,v in zip(poly,poly[1:]+poly[:1]))
def main():
 fp=B/'evidence/first5_failure_handoff.json';d=json.loads(fp.read_bytes());rows=[]
 for case in d['cases']:
  r=case['result']
  if r['status']!='blocked':continue
  route=case['prepared_route'];gp=B/'geometry'/((r['id'].removesuffix('_REVERSE'))+'.json');geo=json.loads(gp.read_bytes());center=r['end_position'];p=[center[0],center[2]];square=[[p[0]-.6,p[1]-.6],[p[0]+.6,p[1]-.6],[p[0]+.6,p[1]+.6],[p[0]-.6,p[1]+.6]];faces=[];tops=[]
  for i,t in enumerate(geo['triangles']):
   poly=[[v[0],v[2]]for v in t];dist=min(distance(p,u,v)for u,v in zip(poly,poly[1:]+poly[:1]));inside=contains(p,poly)if g.area(poly)>1e-14 else False
   if not inside and dist>.65:continue
   n=norm(t);pl=plane(t);face=dict(extracted_index=i,scene_source_face=geo['source_face_indices'][i],triangle_godot_xyz_m=t,normal_standard=n,projected_area_m2=g.area(poly),center_inside_projection=inside,center_edge_distance_m=dist,plane_y_xz_m=pl,plane_y_at_center_m=height(pl,p)if pl else None,gradient=math.hypot(pl[0],pl[1])if pl else None)
   faces.append(face)
   if pl and abs(n[1])>.1:
    q=g.clip(poly,square)
    if q:tops.append((face,q))
  overlaps=[]
  for (x,p1),(y,p2)in itertools.combinations(tops,2):
   q=g.clip(p1,p2);ar=g.area(q)
   if ar>1e-8:overlaps.append(dict(source_faces=[x['scene_source_face'],y['scene_source_face']],area_m2=ar,polygon_xz_m=q,height_difference_range_m=[min(height(x['plane_y_xz_m'],v)-height(y['plane_y_xz_m'],v)for v in q),max(height(x['plane_y_xz_m'],v)-height(y['plane_y_xz_m'],v)for v in q)]))
  rows.append(dict(case_id=r['id'],capsule_center=center,feet_y_m=center[1]-.9,target=r['failed_target'],waypoint_index=r['failed_target_index'],route_local_points=route['points'][max(0,r['failed_target_index']-2):r['failed_target_index']+2],geometry_source=ref(gp),nearby_faces=faces,positive_area_top_overlaps=overlaps))
 out=dict(schema='riverstone.r18.actual_blocked_contact_diagnostic.v1',scene=d['scene'],trace=ref(fp),rows=rows,scope='Exact unchanged extracted actual scene triangles only; no collision replay or modification.')
 op=H/'blocked_actual_triangle_report.json';op.write_text(json.dumps(out,separators=(',',':'))+'\n');print(ref(op))
 for r in rows:
  print(r['case_id'],'feet',r['feet_y_m'],'faces',len(r['nearby_faces']),'overlaps',len(r['positive_area_top_overlaps']));print('inside',[(x['scene_source_face'],x['plane_y_at_center_m'],x['gradient'],x['normal_standard'])for x in r['nearby_faces']if x['center_inside_projection']]);print('near steep',[(x['scene_source_face'],x['center_edge_distance_m'],x['gradient'])for x in r['nearby_faces']if x['gradient']is None or x['gradient']>.2]);print('overlap',r['positive_area_top_overlaps'][:5]);print('points',r['route_local_points'])
if __name__=='__main__':main()
