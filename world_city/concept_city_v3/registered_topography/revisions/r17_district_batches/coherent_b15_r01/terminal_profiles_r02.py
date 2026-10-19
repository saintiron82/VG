"""Shared finite triangle fields for nonflat public terminals."""
import json,math
from .. import author as a,regeneration,public_tails,native_clearance
from ..audit_retired_boundaries import interval
from .source_preflight import HERE,FABRIC,read,write
from .terminal_reservations import at_distance

def run():
 scene=a.load_scene();layout=read('selected_layout.json');hand=read('terrain_handoff.json');plan=json.loads(a.PLAN_PATH.read_bytes());screen=json.loads((HERE/'public_root_screen.json').read_bytes());reservations=json.loads((HERE/'terminal_reservations_r02.json').read_bytes());held={r['source_node_id']for r in reservations['roots']if r['chosen'] is None};roots=[r for r in screen['roots']if r['node_id']in held];windows=[]
 for r in roots:
  x,z=r['source_node']['polyline_xz_m'][-1];windows.append([[x-25,z-25],[x+25,z-25],[x+25,z+25],[x-25,z+25]])
 index=a.TriangleIndex(scene,windows);protected=[];pi=a.geo._SpatialIndex(16)
 def add(p):pi.add(len(protected),p);protected.append(p)
 projection=json.loads(native_clearance.PROJECTION.read_bytes())
 for inst in projection['instances']:
  if inst['id']not in layout['retired_source_ids']:
   for p in inst['native_owner_parts_xz_m']:add(p)
 for r in scene['terrain_contract']['water_domain_polygons']:add(r['polygon_xz_m'])
 for r in hand['protected_regions']:add(r.get('polygon_xz_m',r.get('polygon')))
 for r in layout['placements']:
  for p in r['native_walking_obstacles_xz_m']:add(p)
 results=[]
 for root in roots:
  node=root['source_node'];line=node['polyline_xz_m'];floor=node['floor_y_m'];width=node['width_m'];oldend=line[-1];rd=next(r for r in plan['roads']if r['id']==root['public_road_id']);choices=[];diagnostics=[];chosen=None
  for j,(u,v)in enumerate(zip(rd['polyline_xz_m'],rd['polyline_xz_m'][1:])):
   L=math.dist(u,v);tg=[(v[k]-u[k])/L for k in(0,1)];normal=[-tg[1],tg[0]];nearest=sum((oldend[k]-u[k])*tg[k]for k in(0,1))/L
   for shift in range(-32,33):
    frac=max(0.,min(1.,nearest+shift*.25/L));center=[u[k]+frac*(v[k]-u[k])for k in(0,1)]
    if math.dist(center,oldend)>12:continue
    side=1 if sum((oldend[k]-center[k])*normal[k]for k in(0,1))>0 else-1
    end=[[center[k]+side*normal[k]*(rd['width_m']/2-.25)+sgn*tg[k]*width/2 for k in(0,1)]for sgn in(-1,1)]
    for setback in [0.,.5,1.,2.,4.,6.,8.,10.]:
     startcenter=at_distance(line[::-1],setback);distance=math.dist(startcenter,center)
     if distance<1:continue
     direction=[(center[k]-startcenter[k])/distance for k in(0,1)];nn=[-direction[1],direction[0]];start=[[startcenter[k]+sgn*nn[k]*width/2 for k in(0,1)]for sgn in(-1,1)];ee=end if math.dist(start[0],end[0])+math.dist(start[1],end[1])<=math.dist(start[0],end[1])+math.dist(start[1],end[0])else end[::-1];poly=a.common.clean([start[0],start[1],ee[1],ee[0]])
     if poly and a.geo.is_convex_polygon(poly):choices.append((math.dist(center,oldend)+setback*.1,j,setback,poly,start,ee))
  for score,j,setback,poly,start,end in sorted(choices,key=lambda x:x[0]):
   if any((q:=a.clip(poly,protected[k]))and a.geo.polygon_area(q)>1e-7 for k in pi.candidates(poly)):continue
   spans=[]
   for k in index.index.candidates(end):
    r=index.rows[k]
    if r['material']not in('road','alley'):continue
    span=interval(*end,r['polygon_xz_m'])
    if span:spans.append((span,r))
   knots=sorted({0.,1.}|{v for span,_ in spans for v in span});knots=[v for k,v in enumerate(knots)if k==0 or v-knots[k-1]>1e-7];ys=[];bad=False
   for t in knots:
    p=[end[0][k]+t*(end[1][k]-end[0][k])for k in(0,1)];votes=[a.common.height(r['plane_y_xz_m'],p)for span,r in spans if span[0]-1e-8<=t<=span[1]+1e-8]
    if not votes or max(votes)-min(votes)>1e-6:bad=True;break
    ys.append(votes[0])
   if bad:continue
   seamgrad=max([abs(ys[k+1]-ys[k])/((knots[k+1]-knots[k])*math.dist(*end))for k in range(len(knots)-1)]+[0])
   if seamgrad>.119:continue
   pts=[];targets=[];fixed={};steps=10
   for row in range(steps+1):
    t=row/steps
    for k,s in enumerate(knots):
     p=[(1-t)*(start[0][c]+s*(start[1][c]-start[0][c]))+t*(end[0][c]+s*(end[1][c]-end[0][c]))for c in(0,1)];pts.append(p);targets.append(floor+t*(ys[k]-floor))
     if row==0:fixed[len(pts)-1]=floor
     if row==steps:fixed[len(pts)-1]=ys[k]
   n=len(knots);tris=[]
   for row in range(steps):
    for k in range(n-1):
     i=row*n+k;tris.extend([[i,i+1,i+n+1],[i,i+n+1,i+n]])
   try:sol=regeneration.solve_field(pts,tris,fixed,targets)
   except Exception as exc:diagnostics.append(dict(score=score,segment=j,setback=setback,error=str(exc)));continue
   if sol.get('status') not in('PASS','OPTIMAL') and sol.get('maximum_gradient',99)>.120000001:continue
   chosen=dict(sol,id=node['id']+':PUBLIC_PROFILE',source_node_id=node['id'],road_id=rd['id'],road_segment_index=j,floor_y_m=floor,polygon_xz_m=poly,private_start_edge_xz_m=start,public_edge_xz_m=end,public_seam_knots_xyz_m=[[end[0][0]+t*(end[1][0]-end[0][0]),y,end[0][1]+t*(end[1][1]-end[0][1])]for t,y in zip(knots,ys)],superseded_terminal_setback_m=setback,source_terminal_polyline_xz_m=line,public_source_triangles=[dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'])for _,r in spans]);break
  results.append(dict(source_node_id=node['id'],profile=chosen,failed_attempts=diagnostics));print(node['id'],'PASS'if chosen else'HELD',None if chosen is None else(chosen['maximum_gradient'],chosen['road_segment_index'],chosen['superseded_terminal_setback_m']),flush=True)
 write('terminal_profiles_r02.json',dict(base_scene_sha256=a.SCENE_SHA256,results=results,activation=False))
if __name__=='__main__':run()
