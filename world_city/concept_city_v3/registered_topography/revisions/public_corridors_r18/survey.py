"""Read actual public surfaces against the canonical traced road network."""
import json,math,time
from pathlib import Path
from ..r17_district_batches import author as a
from ... import author as topo
HERE=Path(__file__).resolve().parent
ROAD_IDS='UPPER_CONTOUR MARKET_CONTOUR LOWER_CONTOUR SOUTH_MARKET_AXIS MARKET_NORTH CATHEDRAL_APPROACH NOBLE_RISE WEST_MONASTERY_EDGE NORTH_BACK_LANE CENTRAL_WEST_RADIAL MARKET_WEST_EDGE MARKET_EAST_EDGE EAST_RADIAL EAST_WALL_SERVICE SOUTH_WALL_SERVICE CLERGY_EAST_GATE'.split()
def run():
 start=time.monotonic();scene=a.load_scene();plan=json.loads(a.PLAN_PATH.read_bytes());roads=[r for r in plan['roads']if r['id']in ROAD_IDS]
 windows=[a.geo.road_ribbon(p,q,r['width_m'])for r in roads for p,q in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]
 index=a.TriangleIndex(scene,windows);report=[]
 for r in roads:
  rows=[]
  for j,(p,q)in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   length=math.dist(p,q);n=[-(q[1]-p[1])/length,(q[0]-p[0])/length]
   for t in (0.,.5):
    for side in(-.3,0,.3):
     xz=[p[k]+t*(q[k]-p[k])+side*r['width_m']*n[k]for k in(0,1)]
     hits=[row for k in index.index.candidates([xz])if (row:=index.rows[k])['material']in('road','alley') and a.geo.point_in_convex_polygon(xz,row['polygon_xz_m'],1e-8)]
     values=[a.common.height(v['plane_y_xz_m'],xz)for v in hits]
     actual=max(values)if values else None;theory=topo.dry_height_at(*xz)
     rows.append(dict(segment=j,t=t,side=side,xz_m=xz,actual_y_m=actual,canonical_y_m=theory,delta_m=actual-theory if actual is not None else None,spread_m=max(values)-min(values)if values else None,source_faces=[v['triangle_index']for v in hits]))
  diffs=sorted([abs(v['delta_m'])for v in rows if v['delta_m']is not None]);report.append(dict(id=r['id'],samples=len(rows),missing=sum(v['actual_y_m']is None for v in rows),max_delta_m=max(diffs,default=0),p95_delta_m=diffs[int(len(diffs)*.95)]if diffs else 0,major_changes=[v for v in rows if v['delta_m']is None or abs(v['delta_m'])>.25],samples_detail=rows));print(r['id'],{k:report[-1][k]for k in('missing','max_delta_m','p95_delta_m')},flush=True)
 out=dict(schema='riverstone.r18.public_source_survey.v1',base_scene_sha256=a.SCENE_SHA256,plan_sha256=a.sha(a.PLAN_PATH),roads=report,elapsed_s=time.monotonic()-start,activation=False);(HERE/'source_survey.json').write_text(json.dumps(out,separators=(',',':'))+'\n')
if __name__=='__main__':run()
