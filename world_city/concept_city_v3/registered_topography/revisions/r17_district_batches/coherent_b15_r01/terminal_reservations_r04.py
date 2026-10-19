"""Move only four failed public contacts to exact nearby level cross-sections."""
import json,math,time
from .. import author as a,public_tails,native_clearance
from .source_preflight import HERE,FABRIC,read,write
from ..audit_retired_boundaries import interval
from .effective_routes import trim_before

def at_distance(line,d):
 for p,q in zip(line,line[1:]):
  L=math.dist(p,q)
  if L>=d:return[p[k]+d/L*(q[k]-p[k])for k in(0,1)]
  d-=L
 return line[-1]
def run():
 scene=a.load_scene();layout=read('selected_layout.json');hand=read('terrain_handoff.json');plan=json.loads(a.PLAN_PATH.read_bytes());screen=json.loads((HERE/'public_root_screen.json').read_bytes());roots=[r for r in screen['roots']if r['node_id']in ('B15:R8:LANE:2_5:03','B15:R8:LANE:2_5:05')];windows=[]
 for r in roots:
  x,z=r['source_node']['polyline_xz_m'][-1];windows.append([[x-30,z-30],[x+30,z-30],[x+30,z+30],[x-30,z+30]])
 index=a.TriangleIndex(scene,windows);protected=[];pi=a.geo._SpatialIndex(16)
 def add(id,p,kind):pi.add(len(protected),p);protected.append(dict(id=id,polygon_xz_m=p,kind=kind))
 projection=json.loads(native_clearance.PROJECTION.read_bytes())
 for inst in projection['instances']:
  if inst['id']in layout['retired_source_ids']:continue
  for j,p in enumerate(inst['native_owner_parts_xz_m']):add(inst['id']+':'+str(j),p,'retained_native')
 for r in scene['terrain_contract']['water_domain_polygons']:add(r['surface_id'],r['polygon_xz_m'],'water')
 for r in hand['protected_regions']:add(r['id'],r.get('polygon_xz_m',r.get('polygon')),r['kind'])
 for r in layout['placements']:
  for j,p in enumerate(r['native_walking_obstacles_xz_m']):add(r['id']+':'+str(j),p,'new_native')
 results=[]
 for root in roots:
  rd=next(r for r in plan['roads']if r['id']==root['public_road_id']);node=root['source_node'];line=node['polyline_xz_m'];floor=node['floor_y_m'];width=node['width_m'];oldend=line[-1];candidates=[];attempts=[]
  for j,(u,v)in enumerate(zip(rd['polyline_xz_m'],rd['polyline_xz_m'][1:])):
   L=math.dist(u,v);tg=[(v[k]-u[k])/L for k in(0,1)];normal=[-tg[1],tg[0]]
   nearest=sum((oldend[k]-u[k])*tg[k]for k in(0,1))/L
   for frac in sorted({max(0.,min(1.,nearest+i*.25/L))for i in range(-48,49)}):
    center=[u[k]+frac*(v[k]-u[k])for k in(0,1)]
    if math.dist(center,oldend)>18:continue
    side=1 if sum((oldend[k]-center[k])*normal[k]for k in(0,1))>0 else-1
    end=[[center[k]+side*normal[k]*(rd['width_m']/2-.5)+sgn*tg[k]*width/2 for k in(0,1)]for sgn in(-1,1)]
    for setback in [1.,2.,3.,4.,6.,8.]:
     startcenter=at_distance(line[::-1],setback);dist=math.dist(startcenter,center)
     if dist<1:continue
     direction=[(center[k]-startcenter[k])/dist for k in(0,1)];nn=[-direction[1],direction[0]];start=[[startcenter[k]+sgn*nn[k]*width/2 for k in(0,1)]for sgn in(-1,1)];ee=end if math.dist(start[0],end[0])+math.dist(start[1],end[1])<=math.dist(start[0],end[1])+math.dist(start[1],end[0])else end[::-1];poly=a.common.clean([start[0],start[1],ee[1],ee[0]])
     if not poly or not a.geo.is_convex_polygon(poly):continue
     candidates.append((math.dist(center,oldend)+setback*.15,j,frac,setback,poly,start,end,center))
  chosen=None
  for score,j,frac,setback,poly,start,end,center in sorted(candidates,key=lambda v:v[0]):
   # Only the last half-metre is public; its complete profile must be level.
   checkstrip=a.geo.road_ribbon(end[0],end[1],.02);coverage=[r for r in index.covering(checkstrip)if r['material']in('road','alley')];gap=sum(a.geo.polygon_area(p)for p in a.common.subtract([checkstrip],[r['intersection_polygon_xz_m']for r in coverage]));delta=max([abs(a.common.height(r['plane_y_xz_m'],p)-floor)for r in coverage for p in r['intersection_polygon_xz_m']]+[0])
   if gap>1e-7 or delta>1e-7:continue
   kept=[q for p in node['polygons_xz_m']if(q:=trim_before(p,start,line[0]))]
   public_parts=[r for p in kept+[poly]for r in index.covering(p)if r['material']in ('road','alley')]
   if any(abs(a.common.height(r['plane_y_xz_m'],v)-floor)>1e-7 for r in public_parts for v in r['intersection_polygon_xz_m']):continue
   contacts=[]
   for k in pi.candidates(poly):
    r=protected[k];q=a.clip(poly,r['polygon_xz_m'])
    if q and a.geo.polygon_area(q)>1e-7:contacts.append(dict(id=r['id'],kind=r['kind'],polygon_xz_m=q))
   attempts.append(dict(road_segment_index=j,setback_m=setback,score=score,protected_contacts=len(contacts)))
   if contacts:continue
   chosen=dict(id=node['id']+':PUBLIC_REJOIN',source_node_id=node['id'],floor_y_m=floor,road_id=rd['id'],road_segment_index=j,source_terminal_polyline_xz_m=line,private_start_edge_xz_m=start,public_seam_xyz_m=[[x,floor,z]for x,z in end],polygon_xz_m=poly,polyline_xyz_m=[[(start[0][0]+start[1][0])/2,floor,(start[0][1]+start[1][1])/2],[(end[0][0]+end[1][0])/2,floor,(end[0][1]+end[1][1])/2]],public_source_triangles=[dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'])for r in coverage],superseded_terminal_setback_m=setback,new_plane_y_xz_m=[0,0,floor],maximum_new_grade=0.,status='EXACT_LEVEL_SEAM_CANDIDATE_REQUIRES_OWNER_COMPOSITION');break
  results.append(dict(source_node_id=node['id'],chosen=chosen,attempts=attempts));print(node['id'],{k:chosen[k]for k in('road_segment_index','superseded_terminal_setback_m','polygon_xz_m')}if chosen else'HELD',flush=True)
 write('terminal_reservations_r04.json',dict(schema='riverstone.r17.coherent_terminal_reservations.v1',base_scene_sha256=a.SCENE_SHA256,roots=results,activation=False))
if __name__=='__main__':run()
