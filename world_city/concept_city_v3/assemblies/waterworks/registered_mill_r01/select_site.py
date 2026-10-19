"""Select an industrial mill against actual canal, dry bank, and public street geometry."""
import json,math
from pathlib import Path
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
from world_city.concept_city_v3.assemblies.waterworks.registered_services_r01.select_drawhouses import rect,ribbon,nearest
from world_city.runtime_city.checks import placement as g
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[2]
def pose(p,o,yaw):
 c,s=math.cos(yaw),math.sin(yaw);return[o[0]+c*p[0]+s*p[1],o[1]-s*p[0]+c*p[1]]
def run():
 scene=a.load_scene();contract=json.loads((CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json').read_text());channels=[r for r in contract['water_surfaces']if r['id']in('CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE')];np=json.loads((CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text());native=[];ni=g._SpatialIndex(8)
 for r in np['instances']:
  for p in r['native_owner_parts_xz_m']:ni.add(len(native),p);native.append((r['id'],p))
 def hits(p):return sorted(set(native[i][0]for i in ni.candidates(p)if g.polygon_area(g.convex_intersection(p,native[i][1]))>1e-7))
 windows=[rect(*p,35)for canal in channels for p in canal['polyline_xz_m']];ix=a.TriangleIndex(scene,windows);si=SideIndex(scene,windows);roadparts=[];ri=g._SpatialIndex(16)
 for road in contract['roads']:
  for j,(u,v)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   if math.dist(u,v)<1e-6:continue
   p=ribbon(u,v,road['width_m']);ri.add(len(roadparts),p);roadparts.append((road['id'],j,p))
 public=[];pi=g._SpatialIndex(12)
 for r in ix.rows:
  if r['material']!='road':continue
  for k in ri.candidates(r['polygon_xz_m']):
   rid,j,p=roadparts[k];q=g.convex_intersection(r['polygon_xz_m'],p)
   if g.polygon_area(q)<.005:continue
   target=[sum(v[0]for v in q)/len(q),sum(v[1]for v in q)/len(q)];pi.add(len(public),q);public.append((target,r,rid,j))
 found=[];count=dict(positions=0,dry=0,access=0)
 for canal in channels:
  for j,(u,v)in enumerate(zip(canal['polyline_xz_m'],canal['polyline_xz_m'][1:])):
   length=math.dist(u,v);tx,tz=(v[0]-u[0])/length,(v[1]-u[1])/length;nx,nz=-tz,tx
   for t in [.15,.3,.45,.6,.75,.85]:
    center=[u[0]+(v[0]-u[0])*t,u[1]+(v[1]-u[1])*t];head=canal['levels_m'][j]+t*(canal['levels_m'][j+1]-canal['levels_m'][j])
    for side in [-1,1]:
     count['positions']+=1;o=[center[0]+nx*side*1.8,center[1]+nz*side*1.8];axis=[-nx*side,-nz*side];yaw=math.atan2(-axis[1],axis[0]);body=[pose(p,o,yaw)for p in [[-7,-3],[-1.8,-3],[-1.8,3],[-7,3]]];reserve=[pose(p,o,yaw)for p in [[-7.6,-3.6],[-1.6,-3.6],[-1.6,3.6],[-7.6,3.6]]]
     if hits(reserve):continue
     ground=a.audit_polygon(ix,body)
     if not ground['passes_existing_surface']or not ground['source_pieces']or any(r['material']in('water','road','alley')for r in ground['source_pieces']):continue
     ymin=min(r['min_y_m']for r in ground['source_pieces']);ymax=max(r['max_y_m']for r in ground['source_pieces'])
     if ymax-ymin>1e-6 or ymin-head<.5 or ymin-head>3.2:continue
     count['dry']+=1;door=pose([-7,0],o,yaw);bend=pose([-9,0],o,yaw);targets=sorted(((math.dist(door,public[k][0]),*public[k])for k in pi.candidates(rect(*door,32))),key=lambda p:p[0])
     for dist,q,rr,rid,rseg in targets[:80]:
      if dist<3 or dist>32:continue
      walks=[ribbon(door,bend,2),ribbon(bend,q,2),rect(*bend,1)]
      if any(hits(w)or g.polygon_area(g.convex_intersection(w,body))>1e-7 for w in walks):continue
      audits=[a.audit_polygon(ix,w)for w in walks]
      if not all(r['passes_existing_surface']for r in audits):continue
      owners=[dict(id='mill',polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for r in ground['source_pieces']+[p for aa in audits for p in aa['source_pieces']]]
      if si.audit(owners)['contacts']:continue
      count['access']+=1;row=dict(canal_id=canal['id'],segment=j,t=t,side=side,position_xz_m=o,yaw_rad=yaw,water_head_y_m=head,ground_y_m=ymin,body_polygon_xz_m=body,reservation_polygon_xz_m=reserve,ground=ground,walk_polygons_xz_m=walks,walk_centerline_xz_m=[door,bend,q],access_source_pieces=[p for aa in audits for p in aa['source_pieces']],public_road_id=rid,public_road_segment=rseg,public_anchor_triangle_index=rr['triangle_index'],public_anchor_triangle_sha256=rr['source_triangle_sha256'],score=dist+abs(ymin-head-1.4)*10)
      found.append(row);print('candidate',canal['id'],j,t,side,o,ymin,head,rid,dist,flush=True);break
  print('done canal',canal['id'],count,flush=True)
 found.sort(key=lambda r:r['score']);report=dict(schema='riverstone.registered_mill.site_candidates.v1',base_scene_sha256=a.SCENE_SHA256,counts=count,candidates=found[:8],selected=found[0]if found else None,limits=['Source selection only; wet shaft, source-derived native assembly, finite ownership and swept-wheel/native clearance still required.'])
 (HERE/'site_candidates.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print('SELECT',str(found[0])[:600]if found else'NONE',flush=True)
if __name__=='__main__':run()
