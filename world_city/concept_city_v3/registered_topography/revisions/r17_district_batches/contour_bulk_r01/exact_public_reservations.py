"""Exact source-ribbon/public-corridor intersections supersede screening edges."""
import json,time,collections
from .screen import HERE,write
from .. import author as a
from ...r01_ownership import author as ownership

def run():
 start=time.monotonic();layout=json.loads((HERE/'effective_source_layout.json').read_bytes());roads=json.loads(a.PLAN_PATH.read_bytes())['roads'];rows=[];idx=a.geo._SpatialIndex(16)
 for road in roads:
  for p in ownership.corridor(road['polyline_xz_m'],road['width_m']):idx.add(len(rows),p);rows.append(dict(road_id=road['id'],polygon_xz_m=p))
 result=[]
 for h in layout['holdings']:
  parts=collections.defaultdict(list)
  for p in h['external_route_polygons_xz_m']:
   for j in idx.candidates(p):
    r=rows[j];q=a.clip(p,r['polygon_xz_m'])
    if q and a.geo.polygon_area(q)>1e-9:parts[r['road_id']].append(q)
  byroad=[]
  for rid,ps in sorted(parts.items()):
   union=a.common.disjoint_union(ps);byroad.append(dict(road_id=rid,polygon_parts_xz_m=union,area_m2=sum(a.geo.polygon_area(p)for p in union)))
  allparts=a.common.disjoint_union([p for r in byroad for p in r['polygon_parts_xz_m']]);private=a.common.subtract(a.common.disjoint_union(h['external_route_polygons_xz_m']),allparts)
  result.append(dict(id=h['id']+':EXACT_PUBLIC_RESERVATION',holding_id=h['id'],named_public_road_id=h['public_road_id'],source_public_target_xz_m=h['public_target_xz_m'],source_reserved_centerline_xz_m=h['external_route'],source_reserved_route_polygons_xz_m=h['external_route_polygons_xz_m'],public_intersections_by_road=byroad,public_union_parts_xz_m=allparts,private_union_parts_xz_m=private,current_court_floor_y_m=h['floor_y_m'],named_public_overlap_area_m2=sum(r['area_m2']for r in byroad if r['road_id']==h['public_road_id']),activation=False))
 out=dict(schema='riverstone.r17.exact_public_frontage_reservations.v1',base_scene_sha256=a.SCENE_SHA256,source_layout=dict(path=str((HERE/'effective_source_layout.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'effective_source_layout.json')),canonical_plan=dict(path=str(a.PLAN_PATH.relative_to(a.ROOT)),sha256=a.sha(a.PLAN_PATH)),corridor_helper=dict(path=str(__import__('pathlib').Path(ownership.__file__).relative_to(a.ROOT)),sha256=a.sha(ownership.__file__)),entries=result,summary=dict(entries=len(result),named_public_overlap_missing=[r['holding_id']for r in result if r['named_public_overlap_area_m2']<1e-7],elapsed_s=time.monotonic()-start),policy='These exact routed-ribbon overlaps supersede the illustrative straight requested_public_edge and quad in earlier screening requests. R18 keeps its public field. Private profile ownership subtracts its final finite road/junction union and shares every resulting boundary knot. No court datum or existing accepted seam changes are authorized by this request.',activation=False)
 write('exact_public_reservations.json',out);print(out['summary'],flush=True);print(a.sha(HERE/'exact_public_reservations.json'))
if __name__=='__main__':run()
