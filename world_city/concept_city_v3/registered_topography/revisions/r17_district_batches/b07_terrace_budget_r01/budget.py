"""Measured feasible court datum intervals from actual required cores."""
import json,math
from .. import author as a,bulk_grade_budget as bg

def run():
 f=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/coherent_regrade_r01/BLOCK_007';l=json.loads((f/'selected_layout.json').read_bytes());access=json.loads((f/'access_handoff.json').read_bytes());chosen=[h for h in l['holdings']if h['id'].endswith(('C001','C005','C006','C007'))];idx=a.TriangleIndex(a.load_scene(),[h['holding_polygon_xz_m']for h in chosen]);rows=[]
 for h in chosen:
  sets={'native_foundations':[p for r in l['placements']if r['holding_id']==h['id']for p in r['native_foundation_polygons_xz_m']],'core_courts':h['core_court_polygons_xz_m']};record={};all_ys=[]
  for kind,polys in sets.items():
   pieces=[];ys=[]
   for p in polys:
    for r in idx.covering(p):
     vals=[a.common.height(r['plane_y_xz_m'],q)for q in r['intersection_polygon_xz_m']];ys.extend(vals);pieces.append(dict(polygon_xz_m=r['intersection_polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],source_material=r['material'],source_triangle_index=r['triangle_index'],min_y_m=min(vals),max_y_m=max(vals)))
   all_ys.extend(ys);record[kind]=dict(min_y_m=min(ys),max_y_m=max(ys),pieces=pieces)
  low=max(all_ys)-2.5;high=min(all_ys)+2.5;floor=(min(all_ys)+max(all_ys))/2;proposal=round(floor*4)/4;allowed=[]
  for r in idx.covering(h['holding_polygon_xz_m']):
   p=bg.height_part(r['intersection_polygon_xz_m'],r['plane_y_xz_m'],low=proposal-2.5,high=proposal+2.5)
   if p:allowed.append(p)
  rows.append(dict(id=h['id'],required_core=record,whole_core_floor_interval_for_2_5m_screen_m=[low,high],one_level_core_feasible=low<=high,minimax_core_floor_y_m=floor,rounded_candidate_floor_y_m=proposal,rounded_maximum_core_cut_fill_m=max(abs(y-proposal)for y in all_ys),eligible_measured_holding_parts_xz_m=allowed,retired_body_holes=[dict(source_id=r['source_id'],polygon_xz_m=q,old_native_threshold_y_m=r['existing_finished_floor_y_m'])for r in l['retirement_records']if(q:=a.clip(h['holding_polygon_xz_m'],r['old_terrain_body_hole_polygon_xz_m']))],policy='Measured core interval only; retired native holes are separate support obligations, never guessed source terrain. Profile/route reservation and exact native relocation remain pending.'))
 out=a.HERE/'b07_terrace_budget_r01/core_intervals.json';out.write_text(json.dumps(dict(base_scene_sha256=a.SCENE_SHA256,source_layout=dict(path=str((f/'selected_layout.json').relative_to(a.ROOT)),sha256=a.sha(f/'selected_layout.json')),rows=rows,activation=False),separators=(',',':'))+'\n');print([{k:r[k]for k in('id','whole_core_floor_interval_for_2_5m_screen_m','minimax_core_floor_y_m','rounded_candidate_floor_y_m','rounded_maximum_core_cut_fill_m')}for r in rows]);print(a.sha(out))
if __name__=='__main__':run()
