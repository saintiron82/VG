"""Finite draw-cistern locations using frozen actual ground and native projections."""
import json,math
from pathlib import Path
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[2]
def rect(x,z,h):return [[x-h,z-h],[x+h,z-h],[x+h,z+h],[x-h,z+h]]
def ribbon(p,q,w):
 dx,dz=q[0]-p[0],q[1]-p[1];n=math.hypot(dx,dz);nx,nz=-dz/n*w/2,dx/n*w/2
 return [[p[0]+nx,p[1]+nz],[q[0]+nx,q[1]+nz],[q[0]-nx,q[1]-nz],[p[0]-nx,p[1]-nz]]
def nearest(p,road):
 best=None
 for i,(u,v) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
  dx,dz=v[0]-u[0],v[1]-u[1];n=dx*dx+dz*dz
  t=max(0,min(1,((p[0]-u[0])*dx+(p[1]-u[1])*dz)/n)) if n else 0
  q=[u[0]+dx*t,u[1]+dz*t];d=math.dist(p,q)
  if best is None or d<best[0]:best=(d,q,i)
 return best

def run():
 scene=a.load_scene();plan=json.loads(a.PLAN_PATH.read_text());np=json.loads((CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text());nrows=[];ni=g._SpatialIndex(8)
 for row in np['instances']:
  for p in row['native_owner_parts_xz_m']:ni.add(len(nrows),p);nrows.append((row['id'],p))
 def conflicts(p):return sorted(set(nrows[i][0] for i in ni.candidates(p) if g.polygon_area(g.convex_intersection(p,nrows[i][1]))>1e-7))
 nodes=[('CATHEDRAL_DRAW',[230.2118,-199.3513],14.,14.5),('MONASTERY_DRAW',[-282.1378,111.7377],8.,8.5),('CASTLE_DRAW',[-288.7108,-245.5437],24.,24.6)]
 ix=a.TriangleIndex(scene,[rect(*q,110) for _,q,_,_ in nodes]);side=SideIndex(scene,[rect(*q,110) for _,q,_,_ in nodes]);out=[]
 for name,node,y,head in nodes:
  accepted=[]
  for dx in range(-90,91,6):
   for dz in range(-90,91,6):
    x,z=node[0]+dx,node[1]+dz;body=rect(x,z,2);clear=rect(x,z,3)
    if conflicts(clear):continue
    near=sorted(((*nearest([x,z],r),r)for r in plan['roads']),key=lambda x:x[0])[0];dist,q,segment,road=near
    if dist<road['width_m']/2+4 or dist>36:continue
    ground=a.audit_polygon(ix,body,y)
    if not ground['passes_existing_surface']:continue
    if any(v['material']in('road','alley','water')for v in ground['source_pieces']):continue
    # Outside 2m square, full-width 2.4m connection terminates on public lane center.
    ux,uz=(q[0]-x)/dist,(q[1]-z)/dist;start=[x+ux*2.1,z+uz*2.1];walk=ribbon(start,q,2.4)
    if conflicts(walk):continue
    access=a.audit_polygon(ix,walk)
    if not access['passes_existing_surface']:continue
    # All source side faces are screened against the actual finite floor planes.
    owners=[dict(id=name+':'+str(i),polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for i,r in enumerate(ground['source_pieces']+access['source_pieces'])]
    if side.audit(owners)['contacts']:continue
    accepted.append(dict(id=name,position_m=[x,y,z],upstream_source_head_m=head,local_stored_head_m=y-2,manual_bucket_lift_m=3.1,network='protected_local_storage',supply='Covered branch from named head node; castle cistern is explicit manual raised supply.',offset_from_head_node_m=[dx,dz],footprint_xz_m=body,public_road_id=road['id'],road_segment=segment,walk_polygon_xz_m=walk,walk_centerline_xz_m=[start,q],walk_width_m=2.4,ground=ground,access=access,score=math.hypot(dx,dz)+dist))
  accepted.sort(key=lambda r:r['score']);out.append(accepted[0]if accepted else dict(id=name,status='NO_VALID_LOCATION_FOUND'))
  print(name,[(r.get('position_m'),r.get('public_road_id'),round(r.get('score',0),3))for r in out[-1:]],flush=True)
 report=dict(schema='riverstone.r8.drawhouse_location.v1',base_scene_sha256=a.SCENE_SHA256,native_projection_sha256=a.sha(CITY/'registered_integration/r8/coverage_plan/native_projection.json'),status='source_location_candidate_not_activated',drawhouses=out,limits=['Exact native volume and bank-side tests pending.','Covered source links are authored subsurface network semantics, not fluid simulation.','Nominal head values do not certify potable quality.'])
 (HERE/'locations.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':run()
