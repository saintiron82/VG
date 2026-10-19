"""Exact accepted entry seams and retained common repair datum for R18."""
from pathlib import Path
import sys,json
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def main():
 pack=load(BASE/'resolved_connected_placements.json');proof=load(BASE/'connected_public_continuation.json');graphs={g:load(BASE/f'entry_graph_{g}.json')for g in ('monastery','cathedral','castle')};rows=[]
 for r in proof['route_continuations']:
  route=next(q for q in pack['external_routes']if q['id']==r['route_id']);graph=graphs[r['group_id']];ids=set(r['terminal_actual_triangle_ids']);terminal=[]
  for tri in graph['rows']:
   if tri['triangle_index']not in ids:continue
   for p in route['ribbon_polygons_xz_m']:
    q=geo.convex_intersection(p,tri['polygon_xz_m'])
    if geo.polygon_area(q)>1e-8:terminal.append({'polygon_xz_m':q,'plane_y_xz_m':tri['plane_y_xz_m'],'actual_road_triangle_index':tri['triangle_index'],'recovered_owner_ids':tri['recovered_owner_ids']})
  last=r['continuation_triangle_ids'][-1];end=next(t for t in graph['rows']if t['triangle_index']==last);seams=[s for s in graph['road_seams']if s['owner_id']in r['named_landing_mask_ids']and geo.intersection_area(end['polygon_xz_m'],s['polygon_xz_m'])>1e-9];rows.append({'id':r['route_id'],'status':'ACCEPTED_STATIC_ENTRY','owner_id':r['holding_id'],'width_m':2,'terminal_actual_regions':terminal,'continuation_last_actual_triangle':end,'named_public_road_ids':r['named_public_road_ids'],'named_landing_seam_masks':seams,'route_source':ref(BASE/'resolved_connected_placements.json'),'graph_proof':ref(BASE/'connected_public_continuation.json')})
 training=load(OUT/'training_entry_audit.json');tt=load(OUT/'training_walk_tests.json');rows.append({'id':'RETAINED_TRAINING_ENTRY_R01','status':'ACCEPTED_STATIC_ENTRY_CONTROLLER_PENDING','native_stair_id':'TRAIN:r09:fine','width_m':2,'terminal_polygon_xz_m':training['actual_public_terminal_polygon_xz_m'],'floor_y_m':18,'named_public_road_ids':[tt['source_public_road_id']],'source_proof':ref(OUT/'training_walk_tests.json')})
 common=load(OUT/'common_entry_surface_audit.json');ext=common['row']['external_surface'];rows.append({'id':'PUBLIC_TERRACE_PARK:public_approach','status':'FAILED_R7_REQUIRES_BOUNDED_LOCAL_FIELD','width_m':3,'fixed_source_public_lane_endpoint':ext['public_lane_endpoint'],'public_surface_override_regions':ext['public_surface_override_regions'],'native_gate_floor_y_m':9,'failed_actual_audit':ref(OUT/'common_entry_surface_audit.json')})
 result={'base_scene':ref(terrain.SCENE_PATH),'interfaces':rows,'policy':'Preserve accepted native entry floors and exact finite seam polygons. Public ownership must continue through the named source road. Common terminal is a repair contract, not existing R7 support. Controller replay remains pending.'};(OUT/'public_entry_interfaces_r18.json').write_text(json.dumps(result,indent=2)+'\n');print(len(rows),'interfaces')
if __name__=='__main__':main()
