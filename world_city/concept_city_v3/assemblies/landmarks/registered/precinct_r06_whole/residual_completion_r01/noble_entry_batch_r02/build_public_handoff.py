"""Exact source endpoints, actual native holes and physical exterior seam edges."""
from build_ground_patch import *
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.coherent_b15_r01.compose_cluster import interfaces
OUT=Path(__file__).resolve().parent

def main():
 pack=load(OUT/'resolved_native_candidate.json');routes=load(OUT/'runtime_routes.json');caps=load(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json');ground=load(OUT/'native_ground_candidate_audit.json');collars=load(OUT/'private_collars.json')['owners'];rows=[]
 for owner in pack['owners']:
  eid=owner['owner_id'];route=next(r for r in routes['routes']if r['owner_id']==eid);top=load(ROOT/route['physical_top']['path']);end=np.array(route['polyline_xz_m'][-2]);start=np.array(route['polyline_xz_m'][-3]);direction=(end-start)/np.linalg.norm(end-start);window=b.ribbon([(end+direction*min(-8.,route['public_transition_start_offset_m'])).tolist(),(end+direction*.85).tolist()],3.6)[0];logical=[]
  for i,r in enumerate(top['top_pieces']+[r for r in collars if r['owner_id']==eid]):
   q=geo.convex_intersection(r['polygon_xz_m'],window)
   if geo.polygon_area(q)>1e-8:logical.append(dict(id=eid+':physical:'+str(i),polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],action='field',kind='exact_physical_native_walk'))
  # Empty outside source intentionally returns only the actual finite top
  # exterior, including public cap-column cut notches, with no inferred road.
  empty={'surfaces':{}};index=terrain.TriangleIndex(empty,[window]);boundary=interfaces(empty,index,logical)['unknown_exterior_segments'];lookup={r['id']:r for r in logical};seams=[]
  for e in boundary:
   mid=np.mean(e['edge_xz_m'],axis=0);longitudinal=float((mid-end)@direction)
   # Keep complete public-end envelope. Longitudinal near-seam side edges are
   # explicit finite ownership edges, not all promised walking cross-sections.
   if longitudinal<min(-8.,route['public_transition_start_offset_m'])+.1:continue
   pl=lookup[e['owner_id']]['plane_y_xz_m'];seams.append(dict(edge_xz_m=e['edge_xz_m'],edge_xyz_m=lift(e['edge_xz_m'],pl),plane_y_xz_m=pl,profile_owner=route['native_fine_id'],public_transition_required=True))
  cap=next((r for r in caps['records']if r['property_id']==eid),None);native=[r for r in ground['new_native_upward_faces']if r['native_id']==route['native_fine_id']];rows.append(dict(owner_id=eid,source_public_endpoint=owner['original_public_endpoint'],named_public_road_id=route['named_public_road_id'],native_fine_id=route['native_fine_id'],exact_physical_public_edge_segments=seams,physical_public_top_pieces=logical,actual_native_hole_polygons_xz_m=[r['polygon_xz_m']for r in ground['new_native_undersides']if r['native_id']==route['native_fine_id']],actual_visible_native_upper_faces=native,retired_public_cap_columns_xz_m=[r['polygon_xz_m']for r in cap['candidate_columns']]if cap else[],finite_public_transition_window_xz_m=window,source_profile_preserved=eid=='E3',finite_private_sampling_collar_pieces=[r for r in collars if r['owner_id']==eid],status='FIXED_NATIVE_AND_PHYSICAL_INTERFACE_ONWARD_PUBLIC_FIELD_PENDING'))
 out=dict(schema='riverstone.noble_seven_public_interfaces.v1',id='R8_NOBLE_SEVEN_ENTRY_FIXED_R18_R02',native_pack=ref(OUT/'resolved_native_candidate.json'),collision_contracts=ref(OUT/'collision_contracts.json'),ground_patch=ref(OUT/'native_ground_candidate_patch.json'),original_cap_columns=ref(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json'),owners=rows,public_continuation_owner='R18',policy='Original named road endpoints remain route references. Canonical public planes and full widths take priority. Six bounded visible private tails are regraded to their actual public edge; E3 is unchanged. Actual native columns do not overlap canonical public records. Explicit private collars close native sampling gaps without public overlay. Physical boundary profiles, visible source cells, finite soil and collision activate atomically.')
 write('fixed_public_interfaces_r18.json',out);print('public interfaces',len(rows),sum(len(r['exact_physical_public_edge_segments'])for r in rows),flush=True)
if __name__=='__main__':main()
