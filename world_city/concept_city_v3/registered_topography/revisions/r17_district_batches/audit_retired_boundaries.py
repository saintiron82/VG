"""Finite original-R7 exterior seams of matching-floor ordinary body holes."""
import json,math,time
from . import author as a

def interval(p,q,poly):
 sign=1 if a.geo.signed_polygon_area(poly)>0 else-1;lo,hi=0.,1.
 for u,v in zip(poly,poly[1:]+poly[:1]):
  f=sign*a.geo._cross(u,v,p);g=sign*a.geo._cross(u,v,q);d=g-f
  if abs(d)<1e-14:
   if f< -1e-10:return None
  else:
   t=-f/d
   if d>0:lo=max(lo,t)
   else:hi=min(hi,t)
  if lo>hi+1e-12:return None
 return[max(0.,lo),min(1.,hi)]if hi-lo>1e-10 else None

def audit(index,row):
 poly=row['old_terrain_body_hole_polygon_xz_m'];floor=row['matching_level_band_y_m'];sign=1 if a.geo.signed_polygon_area(poly)>0 else-1
 edges=[]
 for k,(p,q)in enumerate(zip(poly,poly[1:]+poly[:1])):
  length=math.dist(p,q);normal=[sign*(q[1]-p[1])/length,sign*(p[0]-q[0])/length];pout=[p[i]+normal[i]*1e-5 for i in(0,1)];qout=[q[i]+normal[i]*1e-5 for i in(0,1)];hits=[]
  for i in index.index.candidates([pout,qout]):
   r=index.rows[i];span=interval(pout,qout,r['polygon_xz_m'])
   if span:
    points=[[p[j]+t*(q[j]-p[j])for j in(0,1)]for t in span];ys=[a.common.height(r['plane_y_xz_m'],x)for x in points]
    hits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],interval=span,exact_edge_points_xz_m=points,retained_edge_y_m=ys,max_height_delta_m=max(abs(y-floor)for y in ys)))
  spans=sorted(h['interval']for h in hits);covered=0.;end=0.
  for lo,hi in spans:
   if hi>end:covered+=hi-max(lo,end);end=hi
  gap=max(0.,1-covered)*length;delta=max((h['max_height_delta_m']for h in hits),default=None)
  edges.append(dict(edge_index=k,length_m=length,uncovered_length_m=gap,max_height_delta_m=delta,source_intervals=hits))
 missing=sum(e['uncovered_length_m']for e in edges);delta=max((e['max_height_delta_m']for e in edges if e['max_height_delta_m']is not None),default=0.)
 return dict(source_id=row['source_id'],block_id=row['block_id'],floor_y_m=floor,edges=edges,missing_exterior_length_m=missing,max_existing_seam_delta_m=delta,status='COMPLETE_LEVEL_BODY_BOUNDARY'if missing<1e-6 and delta<1e-7 else'KEEP_BODY_RESTORATION_PENDING_DISTRICT_UNION',scope='Body boundary only; old door/landing owners, protected reservations and actual new native support remain separate.')

if __name__=='__main__':
 out=a.HERE/'retired_body_boundary_audit.json'
 if out.exists():raise SystemExit('Refusing to overwrite boundary evidence')
 t=time.monotonic();data=json.loads((a.HERE/'retirement_candidates.json').read_text());rows=[r for r in data['rows']if r['matching_level_band_y_m']is not None];scene=a.load_scene();index=a.TriangleIndex(scene,[r['old_terrain_body_hole_polygon_xz_m']for r in rows]);result=[audit(index,r)for r in rows]
 d=dict(schema='riverstone.r17.retired_body_boundary_audit.v1',base_scene_sha256=a.SCENE_SHA256,retirement_candidates_sha256=a.sha(a.HERE/'retirement_candidates.json'),rows=result,summary=dict(checked=len(result),complete_level=sum(r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'for r in result),indexed_triangles=len(index.rows),seconds=time.monotonic()-t),activation=False)
 out.write_text(json.dumps(d,separators=(',',':'))+'\n');print(d['summary']);print(a.sha(out))
