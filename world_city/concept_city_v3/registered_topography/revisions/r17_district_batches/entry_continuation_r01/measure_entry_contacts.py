"""Exact first full-width source-strip/public contact for held-entry design."""
import json,math
from pathlib import Path
from .. import author as a
from ..audit_retired_boundaries import interval
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'contour_bulk_r01'
def run():
 summary=json.loads((SOURCE/'private_profiles_summary_r02.json').read_bytes());g={r['id']:r for r in json.loads((SOURCE/'shared_private_groups_r03.json').read_bytes())['groups']};rows=[]
 for row in summary['groups']:
  if row['status']!='INFEASIBLE_FIXED_FINITE_PROFILE':continue
  data=json.loads((a.ROOT/row['path']).read_bytes());public=data['public_fixed_regions'];idx=a.geo._SpatialIndex(8)
  for j,r in enumerate(public):idx.add(j,r['polygon_xz_m'])
  for h in g[row['id']]['source_holding_records']:
   points=h['external_route'];station=0.;first=[];center=[];court_intervals=[]
   for segment,(u,v)in enumerate(zip(points,points[1:])):
    length=math.dist(u,v)
    if length<1e-10:continue
    strip=a.geo.road_ribbon(u,v,h['external_width_m']);direction=[(v[k]-u[k])/length for k in(0,1)]
    for j in idx.candidates(strip):
     r=public[j];q=a.clip(strip,r['polygon_xz_m'])
     if not q or a.geo.polygon_area(q)<1e-10:continue
     values=[station+sum((p[k]-u[k])*direction[k]for k in(0,1))for p in q];lo,hi=min(values),max(values);first.append(dict(segment_index=segment,station_range_m=[lo,hi],polygon_xz_m=q,public_profile_id=r['id'],plane_y_xz_m=r['plane_y_xz_m'],height_range_m=[min(a.common.height(r['plane_y_xz_m'],p)for p in q),max(a.common.height(r['plane_y_xz_m'],p)for p in q)]))
     span=interval(u,v,r['polygon_xz_m'])
     if span:
      t=span[0];p=[u[k]+t*(v[k]-u[k])for k in(0,1)];center.append(dict(station_m=station+t*length,point_xyz_m=[p[0],a.common.height(r['plane_y_xz_m'],p),p[1]],source_public_profile_id=r['id']))
    q=a.clip(strip,h['holding_polygon_xz_m'])
    if q:
     values=[station+sum((p[k]-u[k])*direction[k]for k in(0,1))for p in q];court_intervals.append(dict(segment_index=segment,station_range_m=[min(values),max(values)],polygon_xz_m=q))
    station+=length
   first.sort(key=lambda r:r['station_range_m'][0]);center.sort(key=lambda r:r['station_m']);earliest=first[0]['station_range_m'][0]if first else None;c=center[0]if center else None
   rows.append(dict(holding_id=h['id'],group_id=row['id'],floor_y_m=h['floor_y_m'],public_road_id=h['public_road_id'],source_centerline_xz_m=points,full_width_m=h['external_width_m'],source_route_length_m=station,earliest_full_width_public_station_m=earliest,earliest_centerline_public_contact=c,centerline_rise_m=c['point_xyz_m'][1]-h['floor_y_m']if c else None,centerline_gate_to_first_public_average_grade=abs(c['point_xyz_m'][1]-h['floor_y_m'])/c['station_m']if c and c['station_m']>1e-8 else None,early_public_contact_regions=[r for r in first if r['station_range_m'][0]<(earliest+2 if earliest is not None else -1)],all_fixed_public_regions=public,exact_court_intersection_intervals=court_intervals,holding_polygon_xz_m=h['holding_polygon_xz_m'],source_route_polygons_xz_m=h['external_route_polygons_xz_m'],source_profile=dict(path=row['path'],sha256=a.sha(a.ROOT/row['path'])),policy='First public contact is measured against every finite released public plane, not distance to the source road center. Strip-projected station bounds are exact per straight route segment; they are design evidence, not a full-width grade pass or a bent-domain geodesic proof. The court remains fixed wherever its exact holding intersects the entry.',activation=False))
 p=HERE/'held_entry_contact_budget_r01.json';assert not p.exists();p.write_text(json.dumps(dict(rows=rows,activation=False),separators=(',',':'))+'\n');print('rows',len(rows),'sha',a.sha(p));print([(r['holding_id'],round(r['earliest_full_width_public_station_m'] or 0,2),round(r['centerline_rise_m']or 0,3))for r in rows])
if __name__=='__main__':run()
