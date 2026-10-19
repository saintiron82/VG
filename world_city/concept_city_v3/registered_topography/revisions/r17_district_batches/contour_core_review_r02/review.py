"""Separate exact design-screen excess on required cores from holding margins."""
import json,time
from .. import author as a,bulk_grade_budget as budget

def run():
 folder=a.HERE/'contour_core_review_r02';out=folder/'report.json'
 if out.exists():raise SystemExit('Preserve review')
 source=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/contour_revision_r01'
 targets={'BLOCK_001':[3],'BLOCK_003':[4],'BLOCK_004':[4,6],'BLOCK_006':[1,2],'BLOCK_016':[1]};items=[];refs=[]
 for bid,nums in targets.items():
  paths={n:source/bid/(n+'.json')for n in('selected_layout','access_handoff')};ds={n:json.loads(p.read_bytes())for n,p in paths.items()};refs.extend(dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))for p in paths.values());layout=ds['selected_layout']
  for n in nums:
   h=next(h for h in layout['holdings']if h['id'].endswith('C%03d'%n));feet=[p for r in layout['placements']if r.get('holding_id')==h['id']for p in r['native_foundation_polygons_xz_m']];walks=[p for r in ds['access_handoff']['routes']if r['holding_id']==h['id']for p in r['polygons_xz_m']];items.append((h,feet,walks,layout))
 t=time.monotonic();index=a.TriangleIndex(a.load_scene(),[h['holding_polygon_xz_m']for h,_,_,_ in items]);rows=[]
 for h,feet,walks,layout in items:
  y=h['floor_y_m'];parts=list(index.covering(h['holding_polygon_xz_m']));excess=[]
  for r in parts:
   for kind,kwargs in [('cut',dict(low=y+2.5000001)),('fill',dict(high=y-2.5000001))]:
    p=budget.height_part(r['intersection_polygon_xz_m'],r['plane_y_xz_m'],**kwargs)
    if p:excess.append(dict(kind=kind,polygon_xz_m=p,source_material=r['material'],source_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],plane_y_xz_m=r['plane_y_xz_m']))
  categories=[('native_foundation',feet),('core_court',h['core_court_polygons_xz_m']),('required_internal_walk',walks)];classified=[];ar={}
  for e in excess:
   rem=[e['polygon_xz_m']]
   for kind,masks in categories:
    for mask in masks:
     new=[]
     for p in rem:
      q=a.clip(p,mask)
      if q:classified.append(dict(e,classification=kind,polygon_xz_m=q));new.extend(a.common.subtract([p],[mask]))
      else:new.append(p)
     rem=new
   classified.extend(dict(e,classification='holding_margin',polygon_xz_m=p)for p in rem)
  for r in classified:ar[r['classification']]=ar.get(r['classification'],0)+a.geo.polygon_area(r['polygon_xz_m'])
  holes=[]
  for r in layout['retirement_records']:
   q=a.clip(h['holding_polygon_xz_m'],r['old_terrain_body_hole_polygon_xz_m'])
   if q:holes.append(dict(source_id=r['source_id'],polygon_xz_m=q,old_floor_y_m=r['existing_finished_floor_y_m'],note='Old native hole; this height is the retired threshold, not a measured ground plane.'))
  rows.append(dict(id=h['id'],floor_y_m=y,maximum_cut_m=max([a.common.height(r['plane_y_xz_m'],p)-y for r in parts for p in r['intersection_polygon_xz_m']]+[0]),maximum_fill_m=max([y-a.common.height(r['plane_y_xz_m'],p)for r in parts for p in r['intersection_polygon_xz_m']]+[0]),excess_area_by_disjoint_class_m2=ar,excess_regions=classified,retired_holes=holes,recommendation='REVISE_NATIVE_POSE_OR_REQUIRED_CORE'if sum(ar.get(k,0)for k in('native_foundation','core_court','required_internal_walk'))>1e-7 else'TRIM_NONESSENTIAL_HOLDING_MARGIN'))
 result=dict(schema='riverstone.r17.contour_core_excess.v1',base_scene_sha256=a.SCENE_SHA256,sources=refs,rows=rows,threshold_m=2.5,threshold_semantics='Design-screen threshold only; neither structural support nor access approval.',elapsed_s=time.monotonic()-t,activation=False);out.write_text(json.dumps(result,separators=(',',':'))+'\n');print([{k:r[k]for k in('id','floor_y_m','excess_area_by_disjoint_class_m2','recommendation')}for r in rows]);print(a.sha(out))
if __name__=='__main__':run()
