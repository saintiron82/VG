"""Find full-width cistern approaches to actual frozen public tops, not plan centerlines."""
import json,math,time
from .select_drawhouses import HERE,CITY,rect,ribbon
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
from world_city.runtime_city.checks import placement as g
NODES=[('CATHEDRAL_DRAW',[230.2118,-199.3513],14.,14.5),('MONASTERY_DRAW',[-282.1378,111.7377],8.,8.5),('CASTLE_DRAW',[-288.7108,-245.5437],24.,24.6)]
def run():
 scene=a.load_scene();np=json.loads((CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text());nrows=[];ni=g._SpatialIndex(8)
 for row in np['instances']:
  for p in row['native_owner_parts_xz_m']:ni.add(len(nrows),p);nrows.append((row['id'],p))
 def conflicts(p):return sorted(set(nrows[i][0] for i in ni.candidates(p) if g.polygon_area(g.convex_intersection(p,nrows[i][1]))>1e-7))
 contract=json.loads((CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json').read_text());roads=[];ri=g._SpatialIndex(16)
 for road in contract['roads']:
  for j,(u,v) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   if math.dist(u,v)<1e-7:continue
   p=ribbon(u,v,road['width_m']);ri.add(len(roads),p);roads.append(dict(id=road['id'],segment=j,polygon=p,start=u,end=v,levels=road['levels_m'][j:j+2]))
 out=[]
 for name,node,y,head in NODES:
  begin=time.monotonic();win=[rect(*node,105)];ix=a.TriangleIndex(scene,win);side=SideIndex(scene,win);pub=[];pi=g._SpatialIndex(12)
  for r in ix.rows:
   if r['material'] in ('road','alley') and min(abs(v[1]-y) for v in r['vertices_xyz_m'])<6:
    # Only actual public tops at the service datum can anchor an ungraded route.
    p=r['polygon_xz_m']
    for rid in ri.candidates(p):
     road=roads[rid];qpoly=g.convex_intersection(p,road['polygon'])
     if g.polygon_area(qpoly)<.005:continue
     q=[sum(v[0]for v in qpoly)/len(qpoly),sum(v[1]for v in qpoly)/len(qpoly)];u,v=road['start'],road['end'];dx,dz=v[0]-u[0],v[1]-u[1];t=((q[0]-u[0])*dx+(q[1]-u[1])*dz)/(dx*dx+dz*dz);hy=road['levels'][0]+t*(road['levels'][1]-road['levels'][0])
     if abs(hy-a.common.height(r['plane_y_xz_m'],q))>.1:continue
     rr=dict(r,public_road_id=road['id'],public_road_segment=road['segment'],public_owner_polygon_xz_m=qpoly);pub.append((q,rr));pi.add(len(pub)-1,qpoly)
  accepted=[];count=dict(public=len(pub),ground=0,access=0,banks=0)
  candidates=[]
  for dx in range(-96,97,4):
   for dz in range(-96,97,4):
    candidates.append((math.hypot(dx,dz),node[0]+dx,node[1]+dz))
  for _,x,z in sorted(candidates):
   if accepted and math.dist(node,[x,z])>accepted[0]['score']+3:break
   body=rect(x,z,2);clear=rect(x,z,2.6)
   if conflicts(clear):continue
   pids=pi.candidates(rect(x,z,18))
   if not pids:continue
   ground=a.audit_polygon(ix,body,y)
   if not ground['passes_existing_surface'] or any(p['material']in('road','alley','water')for p in ground['source_pieces']):continue
   count['ground']+=1
   targets=sorted(((math.dist([x,z],pub[i][0]),*pub[i])for i in pids),key=lambda t:t[0])
   target_seen=set()
   for dist,q,rr in targets:
    if dist<4 or dist>18:continue
    key=tuple(round(v,1)for v in q)
    if key in target_seen:continue
    target_seen.add(key)
    ux,uz=(q[0]-x)/dist,(q[1]-z)/dist
    axis=[(1 if ux>0 else -1),0] if abs(ux)>abs(uz) else [0,(1 if uz>0 else -1)]
    start=[x+axis[0]*2,z+axis[1]*2];bend=[x+axis[0]*3.6,z+axis[1]*3.6]
    walks=[ribbon(start,bend,2.),ribbon(bend,q,2.),rect(*bend,1.)]
    if any(g.polygon_area(g.convex_intersection(w,body))>1e-7 for w in walks):continue
    walk=walks[0]
    if any(conflicts(w)for w in walks):continue
    audits=[a.audit_polygon(ix,w)for w in walks]
    if not all(v['passes_existing_surface']for v in audits):continue
    access=dict(source_pieces=[p for aa in audits for p in aa['source_pieces']],passes_existing_surface=True)
    count['access']+=1
    owners=[dict(id=name+':'+str(i),polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for i,r in enumerate(ground['source_pieces']+access['source_pieces'])]
    contacts=side.audit(owners)['contacts']
    if contacts:count['banks']+=1;continue
    # Positive-area public overlap at the seam proves this is not point-only contact.
    public=sum(p['area_m2']for p in access['source_pieces']if p['material']in('road','alley'))
    if public<.1:continue
    row=dict(id=name,position_m=[x,y,z],upstream_source_head_m=head,local_stored_head_m=y-2,manual_bucket_lift_m=3.1,network='protected_local_storage',supply='Covered branch from named head node; castle cistern is explicit manual raised supply.',offset_from_head_node_m=[x-node[0],z-node[1]],footprint_xz_m=body,public_road_id=rr['public_road_id'],public_road_segment=rr['public_road_segment'],public_anchor_material=rr['material'],public_anchor_triangle_index=rr['triangle_index'],public_owner_polygon_xz_m=rr['public_owner_polygon_xz_m'],public_anchor_triangle_sha256=rr['source_triangle_sha256'],public_seam_area_m2=public,walk_polygon_xz_m=walk,walk_polygons_xz_m=walks,walk_centerline_xz_m=[start,bend,q],walk_width_m=2.,access_side_local_xz=axis,ground=ground,access=access,score=math.dist(node,[x,z])+dist)
    accepted.append(row);accepted.sort(key=lambda r:r['score']);print(name,'candidate',row['position_m'],row['score'],flush=True);break
  out.append(accepted[0]if accepted else dict(id=name,status='NO_VALID_LOCATION_FOUND'))
  print(name,'SELECT',out[-1].get('position_m'),count,'seconds',time.monotonic()-begin,flush=True)
 report=dict(schema='riverstone.r8.drawhouse_location.v2',base_scene_sha256=a.SCENE_SHA256,native_projection_sha256=a.sha(CITY/'registered_integration/r8/coverage_plan/native_projection.json'),status='source_location_candidate_not_activated',drawhouses=out,limits=['Public anchor is exact existing R7 road/alley surface intersecting a named R14 public road segment, with matching source profile head.','Covered source links are authored subsurface network semantics, not fluid simulation.','Nominal head values do not certify potable quality.'])
 (HERE/'actual_public_locations.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
if __name__=='__main__':run()
