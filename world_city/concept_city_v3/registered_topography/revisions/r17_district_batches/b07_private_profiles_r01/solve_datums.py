"""Exact visible-core budget and three bounded B07 datum proposals."""
import json,time,types,math
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01.finite import inside
from ..entry_continuation_r01 import solve_coherent_datums as coherent
from .solve import HERE,LAYOUT,write

def run():
 layout=json.loads(LAYOUT.read_bytes());index=a.TriangleIndex(a.load_scene(),[h['holding_polygon_xz_m']for h in layout['holdings']]);budgets=[]
 for h in layout['holdings']:
  core=a.common.disjoint_union(h['core_court_polygons_xz_m']+[p for r in layout['placements']if r['holding_id']==h['id']for p in r['native_foundation_polygons_xz_m']]);pieces=[];ys=[]
  for p in core:
   for r in index.covering(p):
    vals=[a.common.height(r['plane_y_xz_m'],v)for v in r['intersection_polygon_xz_m']];ys+=vals;pieces.append(dict(polygon_xz_m=r['intersection_polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],source_material=r['material'],source_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256']))
  missing=a.common.subtract(core,[r['polygon_xz_m']for r in pieces]);old=[]
  for r in layout['retirement_records']:
   for p in missing:
    q=a.clip(p,r['old_terrain_body_hole_polygon_xz_m'])
    if q:old.append(dict(source_id=r['source_id'],polygon_xz_m=q,old_native_floor_y_m=r['existing_finished_floor_y_m']))
  row=dict(id=h['id'],floor_y_m=h['floor_y_m'],maximum_required_core_cut_m=max(0,max(ys)-h['floor_y_m']),maximum_required_core_fill_m=max(0,h['floor_y_m']-min(ys)),actual_visible_source_min_y_m=min(ys),actual_visible_source_max_y_m=max(ys),visible_core_parts=pieces,retired_native_core_holes=old,unclassified_core_holes_xz_m=a.common.subtract(missing,[r['polygon_xz_m']for r in old]),policy='Actual visible core defines the hill-preservation interval. Obsolete ordinary floors are retirement provenance, not preserved source terrain. Their outer interfaces still need exact closure.');budgets.append(row)
 write(HERE/'required_core_budget.json',dict(rows=budgets,layout=dict(path=str(LAYOUT.relative_to(a.ROOT)),sha256=a.sha(LAYOUT)),base_scene_sha256=a.SCENE_SHA256,activation=False));lookup={r['id']:r for r in budgets};rows=[]
 geo=types.SimpleNamespace(**vars(a.geo));geo.point_in_convex_polygon=inside;proxy=types.SimpleNamespace(**vars(a));proxy.geo=geo;solver=types.FunctionType(coherent.solve.__code__,dict(coherent.solve.__globals__,a=proxy))
 for hid in ['BLOCK_007:R8_C001','BLOCK_007:R8_C003','BLOCK_007:R8_C005']:
  p=HERE/(hid.replace(':','_')+'.json');source=json.loads(p.read_bytes());h=source['source_holding'];court=[dict(r,id=r['id'].split(':COURT:')[0]+':COURT_DATUM')for r in source['court_fixed_regions']];group=dict(holding_ids=[hid],source_holding_records=[h],gate_fixed_regions=court,gate_targets=[dict(point_xz_m=h['gate_position_xz_m'],floor_y_m=h['floor_y_m'])]);start=time.monotonic();result=solver(group,source,lookup);out=HERE/(hid.replace(':','_')+'_datum.json');write(out,dict(id='PRIVATE_GROUP:'+hid,holding_ids=[hid],private_domain_polygons_xz_m=source['private_domain_polygons_xz_m'],public_fixed_regions=source['public_fixed_regions'],result=result,source=dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),elapsed_s=time.monotonic()-start,activation=False));brief=dict(holding_id=hid,status=result['status'],datum_changes=result.get('datum_changes'),maximum_gradient=result.get('maximum_gradient'),path=str(out.relative_to(a.ROOT)),sha256=a.sha(out));rows.append(brief);print(brief,flush=True)
 write(HERE/'datum_summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
