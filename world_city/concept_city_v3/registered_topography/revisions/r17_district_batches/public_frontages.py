"""Full-width existing public frontage screen for initial district batches."""
import json,time,math
from . import author as a

def build(scene,plan):
 started=time.monotonic();blocks=[b for b in plan['blocks']if b['id']in a.PRIORITY_BLOCKS];boxes=[a.bounds(b['polygon_xz_m'])for b in blocks];windows=[[[x0-8,z0-8],[x1+8,z0-8],[x1+8,z1+8],[x0-8,z1+8]]for x0,z0,x1,z1 in boxes];index=a.TriangleIndex(scene,windows)
 parts=[(b['id'],p)for b in blocks for p in a.triangulate(b['polygon_xz_m'])];bi=a.geo._SpatialIndex(32)
 for i,(bid,p)in enumerate(parts):bi.add(i,p)
 ids=set(k for b in blocks for k in b['boundary_road_ids']+b['interior_path_ids']);rows=[]
 for r in plan['roads']:
  if r['id']not in ids:continue
  station=0.
  for j,(p,q)in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   length=math.dist(p,q)
   if length<1e-8:continue
   poly=a.geo.road_ribbon(p,q,r['width_m']);touch=sorted({parts[i][0]for i in bi.candidates(poly)if a.clip(poly,parts[i][1])})
   if touch:
    covered=list(index.covering(poly));polys=[x['intersection_polygon_xz_m']for x in covered];gap=sum(a.geo.polygon_area(p)for p in a.common.subtract([poly],polys));area=sum(a.geo.polygon_area(p)for p in polys);expected=a.geo.polygon_area(poly)
    ys=[a.common.height(v['plane_y_xz_m'],p)for v in covered for p in v['intersection_polygon_xz_m']];floor=round(sum(ys)/len(ys),7)if ys else None
    flat=bool(ys)and max(ys)-min(ys)<=a.BAND_TOLERANCE_M;maxgrade=max((math.hypot(*v['plane_y_xz_m'][:2])for v in covered),default=0)
    status='COMPLETE_EXISTING_LEVEL_FRONTAGE'if flat and gap<1e-7 and abs(area-expected)<1e-7 else'NONLEVEL_OR_NATIVE_HOLE_FULL_PROFILE_REQUIRED'
    rows.append(dict(road_id=r['id'],segment_index=j,block_ids=touch,width_m=r['width_m'],station_m=[station,station+length],centerline_xz_m=[p,q],polygon_xz_m=poly,floor_y_m=floor if flat else None,min_y_m=min(ys)if ys else None,max_y_m=max(ys)if ys else None,max_actual_triangle_grade=maxgrade,missing_area_m2=gap,overlap_excess_area_m2=max(0,area-expected+gap),status=status,source_indices=[dict(material=v['material'],triangle_index=v['triangle_index'])for v in covered]))
   station+=length
 return dict(schema='riverstone.r17.public_frontage_screen.v1',base_scene_sha256=a.SCENE_SHA256,index_window_margin_m=8,prior_narrow_window_report_sha256=a.sha(a.HERE/'public_frontage_screen.json'),rows=rows,summary=dict(segments=len(rows),complete_level=sum(r['status']=='COMPLETE_EXISTING_LEVEL_FRONTAGE'for r in rows),indexed_triangles=len(index.rows),seconds=time.monotonic()-started),limits=['Rectangular full-width segments only; turning joins/caps and new private ribbons require final batch checks.','No native bridge or portal floor inferred through missing rendered terrain.','Old road identity supplies the reservation; actual R7 triangle planes supply height.'],activation=False)
if __name__=='__main__':
 p=a.HERE/'public_frontage_screen_r2.json'
 if p.exists():raise SystemExit('Refusing to overwrite frontage evidence')
 d=build(a.load_scene(),json.loads(a.PLAN_PATH.read_bytes()));p.write_text(json.dumps(d,separators=(',',':'))+'\n');print(d['summary']);print(a.sha(p))
