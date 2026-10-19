"""Bounded explicit repair of the source bank court's repeated-point link."""
import json,math
from . import author as a,frozen_r6 as f

def ribbon(start,end,width):
 dx,dz=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dz);nx,nz=-dz/length*width/2,dx/length*width/2
 return [[start[0]+nx,start[1]+nz],[end[0]+nx,end[1]+nz],[end[0]-nx,end[1]-nz],[start[0]-nx,start[1]-nz]]
def circle(p,width):
 radius=width/2/math.cos(math.pi/16)
 return [[p[0]+radius*math.cos(i*math.tau/16),p[1]+radius*math.sin(i*math.tau/16)] for i in range(16)]
def build():
 hand=a.read('terrain_handoff.json');court=next(c for c in hand['source_courts'] if c['id']=='BANK_DRY_WORK_COURT');route=next(r for r in hand['external_lanes'] if r['holding_id']==court['holding_id'])
 start=route['polyline_xz_m'][0];end=court['access_link']['polyline_xz_m'][0];width=2.;polys=a.disjoint_union([ribbon(start,end,width),circle(start,width),circle(end,width)])
 scene=f.load_scene();idx=f.SurfaceIndex(scene,windows=[f.bounds(p) for p in polys],margin=0);checks=[];conflicts=[]
 for i,p in enumerate(polys):
  recs=idx.cover(p);missing=sum(a.geo.polygon_area(q) for q in a.subtract([p],[r['intersection_polygon_xz_m'] for r in recs]));values=[a.height(r['plane_y_xz_m'],q) for r in recs for q in r['intersection_polygon_xz_m']]
  checks.append(dict(piece=i,area_m2=a.geo.polygon_area(p),uncovered_m2=missing,min_y_m=min(values),max_y_m=max(values)))
  for native in a.read('native_geometry.json')['placements']:
   for j,obstacle in enumerate(native['native_walking_obstacles_xz_m']):
    hit=a.clean(a.geo.convex_intersection(p,obstacle))
    if hit and a.geo.polygon_area(hit)>1e-8:conflicts.append(dict(placement_id=native['id'],obstacle=j,polygon_xz_m=hit,area_m2=a.geo.polygon_area(hit)))
 assert not conflicts,conflicts
 assert all(r['uncovered_m2']<1e-7 and abs(r['min_y_m']-2.5)<1e-7 and abs(r['max_y_m']-2.5)<1e-7 for r in checks),checks
 return dict(schema='riverstone.r16.bank_court_connection.v1',status='SOURCE_GEOMETRY_PASS_PENDING_COMBINED_PATCH',base_scene_sha256=f.SCENE_SHA256,id='BANK_DRY_WORK_COURT:EXPLICIT_ROUTE_ORIGIN_CONNECTOR',court_id=court['id'],connects_route_id=route['id'],width_m=width,polyline_xz_m=[start,end],polyline_xyz_m=[[x,2.5,z] for x,z in [start,end]],length_m=math.dist(start,end),polygon_regions_xz_m=polys,source_supersession=dict(original_polyline_xz_m=court['access_link']['polyline_xz_m'],reason='Source link contained only repeated court points and did not explicitly reach the external route origin.'),ground_checks=checks,native_walking_conflicts=conflicts,policy='Retain actual +2.5 R6 planes. This connects the route origin, not the separate unbuilt boundary gate.')
if __name__=='__main__':
 p=a.HERE/'court_connector.json'
 if p.exists():raise ValueError('Evidence exists')
 d=build();p.write_text(json.dumps(d,indent=2)+'\n');print(d['status'],d['length_m'],a.sha(p))
