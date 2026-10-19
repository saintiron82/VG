"""Actual R6/native upward floor coverage for retained finite walking ribbons."""
import json,math
from . import author as a,frozen_r6 as f

def run():
 scene=f.load_scene();patch=json.loads((a.HERE/'footing_court_patch.json').read_bytes());fixed=f.apply_edits(scene,patch);pack=a.read('resolved_placements.json')
 rows=list(a.walk_reservations());holds=[r['polygon_xz_m'] for r in a.terminal_domains()]
 for route in a.read('terrain_handoff.json')['external_lanes']:
  for i,p in enumerate(a.subtract(a.disjoint_union(route['ribbon_and_join_polygons_xz_m']),holds)):
   rows.append(dict(id=route['id']+':RETAINED:'+str(i),route_id=route['id'],kind='retained_external_lane_before_terminal_hold',polygon_xz_m=p))
 idx=f.SurfaceIndex(fixed,windows=[f.bounds(r['polygon_xz_m']) for r in rows],margin=0)
 floors=[];ni=a.geo._SpatialIndex(8)
 for placement in pack['placements']:
  asset=pack['assets'][placement['asset_key']];path=a.ROOT/asset['render_path'];assert a.sha(path)==asset['render_sha256'];render=json.loads(path.read_bytes());c=math.cos(placement['yaw_rad']);s=math.sin(placement['yaw_rad']);pos=placement['position_m']
  for g in render['groups']:
   for q in g['quads']:
    if f.normal_y(q[:3])<=1e-10 or max(abs(v[1]-.5) for v in q)>1e-9:continue
    poly=[[pos[0]+c*v[0]+s*v[2],pos[2]-s*v[0]+c*v[2]] for v in q];ni.add(len(floors),poly);floors.append(poly)
 ledger=[];failures=[]
 for row in rows:
  p=row['polygon_xz_m'];covered=[];maxheight=0
  for rec in idx.intersecting(p):
   q=a.clean(a.geo.convex_intersection(p,rec['polygon_xz_m']))
   if not q:continue
   values=[a.height(rec['plane_y_xz_m'],v) for v in q];delta=max(abs(v-2.5) for v in values);maxheight=max(maxheight,delta)
   if delta<1e-7:covered.append(q)
  covered.extend(floors[i] for i in ni.candidates(p))
  remaining=a.subtract([p],covered);gap=sum(a.geo.polygon_area(q) for q in remaining)
  record=dict(id=row['id'],route_id=row['route_id'],kind=row['kind'],area_m2=a.geo.polygon_area(p),missing_level_floor_m2=gap,max_existing_height_delta_m=maxheight)
  ledger.append(record)
  if gap>1e-7:failures.append(dict(record,remaining_polygons_xz_m=remaining))
 report=dict(status='PASS' if not failures else 'FAIL',base_scene_sha256=f.SCENE_SHA256,partial_patch_sha256=a.sha(a.HERE/'footing_court_patch.json'),native_pack_sha256=a.EXPECTED['resolved_placements.json'],finite_walk_piece_count=len(rows),native_horizontal_floor_quad_count=len(floors),checks=ledger,failures=failures,public_terminal_fields_excluded=True,scope='Static upward floor coverage on all retained native/court/external walking ribbons. Public terminal profiles and obstacle/capsule tests are separate.')
 p=a.HERE/'retained_walk_coverage.json'
 if p.exists():raise ValueError('Evidence already exists')
 p.write_text(json.dumps(report,separators=(',',':'))+'\n');print(report['status'],len(rows),'pieces',len(failures),'failures',a.sha(p),flush=True)
if __name__=='__main__':run()
