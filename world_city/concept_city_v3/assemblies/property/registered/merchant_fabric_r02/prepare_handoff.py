"""Finite materials, native holes, public profiles and below-floor edge supports."""
import json,math
from pathlib import Path
from .grammar import HERE,ROOT,CITY,PLAN,ref,write,g,estate,rect,xform,transform_polys
from .final_selection import additional_owners
from .author import terrain,context,native_masks,triangle_grade
from ..merchant_block011.prepare_handoff import union,subtract,area
GARDENS={'compact_old':[7,-15,11,-7],'compact_rebuilt':[7,-15,11,-7],'deep_workyard':[10,-11,14,-7],'deep_older_workyard':[10,-11,14,-7],'wide_early_court':[-14,-5,-10,3]}

def run():
 source=json.loads((HERE/'effective_eligibility.json').read_text());pack=json.loads((HERE/'resolved_placements.json').read_text());review=json.loads((HERE/'native_review.json').read_text());assert not review['issues'];assert review['pack']==ref(HERE/'resolved_placements.json');ctx=context();roads=ctx['plan']['roads'];records=[];checks=[];allplatforms=[p['polygon_xz_m'] for p in source['properties']];retired=set(pack['replaced_placement_ids'])|ctx['old_removed'];assigned_residuals=[]
 extra,extra_sources=additional_owners()
 for poly,identity in zip(extra.polys,extra.ids):ctx['hard'].add(poly,identity)
 for prop in source['properties']:
  pid=prop['id'];floor=prop['floor_y_m'];frame=prop['polygon_xz_m'];print('partitioning',pid,flush=True);found=union([q for m in pack['ownership_masks'] if m['property_id']==pid for q in m['terrain_exclusion_regions_xz_m']]);routes=[r for r in pack['access_proposals'] if r['property_id']==pid];stubs=[]
  for d in pack['actual_doors']:
   if d['owner_id'].startswith(pid+':'):
    width=min(x['native_leaf_width_m'] for x in d['actual_union_threshold_evidence']);a,b=d['cached_threshold_stub_xz_m']
    if math.dist(a,b)>1e-8:stubs.append(g.road_ribbon(a,b,width))
  paths=subtract(union([q for r in routes for q in r['ribbon_polygons_xz_m']+r['round_join_polygons_xz_m']]+stubs),found)
  garden=transform_polys([rect(*GARDENS[prop['family']])],prop['origin_xz_m'],prop['yaw_rad']);garden=subtract(garden,found+paths)
  assert area(garden)>=15.99,(pid,area(garden))
  roofs=[q for p in pack['placements'] if p['property_id']==pid for q in p['native_roof_polygons_xz_m']];assert area(subtract(garden,roofs))>=area(garden)-1e-5
  court=subtract(union([prop['court']['polygon_xz_m']]),found+paths+garden);rest=subtract([frame],found+paths+garden+court)
  layers=[dict(role='native_foundation',material='native_asset_owned',polygons_xz_m=found),dict(role='connected_pedestrian_and_goods_access',material='cobblestone',polygons_xz_m=paths),dict(role='productive_kitchen_garden',material='cultivated_soil',polygons_xz_m=garden),dict(role='shared_goods_handling_court',material='compacted_gravel',polygons_xz_m=court),dict(role='service_apron_and_yard',material='packed_earth',polygons_xz_m=rest)]
  for layer in layers:layer['area_m2']=area(layer['polygons_xz_m'])
  error=abs(sum(x['area_m2'] for x in layers)-g.polygon_area(frame));assert error<1e-4,(pid,error)
  link=prop['external_gate_link'];public=[]
  for road in roads:
   for si,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
    ribbon=g.road_ribbon(a,b,road['width_m'])
    if not estate.overlap(link['polygon_xz_m'],ribbon):continue
    for ti,tri in enumerate(link['triangles_xyz_m']):
     q=g.convex_intersection([[v[0],v[2]] for v in tri],ribbon)
     if g.polygon_area(q)>1e-7:public.append(dict(road_id=road['id'],segment_index=si,polygon_xz_m=q,source_triangle_index=ti,height_profile_xyz_m=tri,status='proposed shared finite surface; road-side collar acceptance pending'))
  poly=link['polygon_xz_m'];gate_edge=poly[:2];public_edge=[poly[3],poly[2]];approach=dict(id=pid+':FINITE_PUBLIC_HANDOFF',road_id=link['road_id'],source_target_segment=link['segment_index'],polygon_xz_m=poly,width_m=3.5,minimum_connector_width_m=min(math.dist(*gate_edge),math.dist(*public_edge)),gate_edge_xz_m=gate_edge,public_edge_xz_m=public_edge,endpoint_profile=link['public_edge_profile'],triangles_xyz_m=link['triangles_xyz_m'],height_evaluator=dict(kind='piecewise_affine_triangle_planes',triangles_xyz_m=link['triangles_xyz_m']),maximum_profile_grade=max(triangle_grade(t) for t in link['triangles_xyz_m']),public_coownership_proposals=public,surface_owner='merchant_r02_terrain_wrapper_candidate',status='source triangle profile; full-width public collar and sampled seam require terrain review',capsule_validated=False)
  W,D=prop['width_m'],prop['depth_m'];gx,gz=prop['gate_local_xz_m'];local=[[-W/2,-D/2],[W/2,-D/2],[W/2,D/2],[gx+1.75,D/2],[gx-1.75,D/2],[-W/2,D/2]];edges=[]
  for ei,(a,b) in enumerate(zip(local,local[1:]+local[:1])):
   if ei==3:continue
   n=math.ceil(math.dist(a,b)/6)
   for i in range(n):
    q=[xform([a[k]+(b[k]-a[k])*s/n for k in (0,1)],prop['origin_xz_m'],prop['yaw_rad']) for s in(i,i+1)];samples=[]
    for j in range(7):
     v=[q[0][k]+(q[1][k]-q[0][k])*j/6 for k in(0,1)];y=terrain.land_height_at(*v);samples.append(dict(point_xz_m=v,existing_y_m=y,cut_m=max(0,y-floor),fill_m=max(0,floor-y)))
    cut=max(s['cut_m'] for s in samples);fill=max(s['fill_m'] for s in samples)
    if max(cut,fill)>.25:edges.append(dict(id=pid+f':SUPPORT_EDGE:{ei}:{i}',edge_xz_m=q,finished_floor_y_m=floor,maximum_sampled_cut_m=cut,maximum_sampled_fill_m=fill,samples=samples,maximum_length_m=6,above_floor_wall_height_m=0,support_owner='merchant_r02_terrain_wrapper_candidate',ownership='Finite below-floor retaining / cut-edge interface; no walking-height wall.',status='source support requirement; no native ground or retaining compile'))
  # Retired plot portions outside the new holdings remain at the inherited grade.
  # They receive a finite yard designation, not an unproved flat slab or route.
  plotpolys=union([ctx['plots'][k]['polygon_xz_m'] for k in prop['source_plot_ids']]);cutpolys=allplatforms+assigned_residuals+ctx['hard'].polys+ctx['roads'].polys
  for q in plotpolys:
   for i in ctx['native_index'].candidates(q):
    p=ctx['old']['placements'][i]
    if p['id'] not in retired:cutpolys+=native_masks(p,ctx)['found']
  for route in ctx['path_polys']:
   if route['owner_id'] not in retired:cutpolys.append(route['polygon_xz_m'])
  residual=subtract(plotpolys,cutpolys);assigned_residuals+=residual
  remaining=dict(id=pid+':RETAINED_GRADE_YARD',source_plot_ids=prop['source_plot_ids'],polygons_xz_m=residual,area_m2=area(residual),land_use='private service yard with productive-ground potential',height_policy='retain exact inherited ground; no flattening',access_status='No new proven service connection to these lower fragments; unresolved',material_override=None)
  records.append(dict(property_id=pid,block_id=prop['block_id'],platform_polygon_xz_m=frame,finished_floor_y_m=floor,platform_area_m2=g.polygon_area(frame),materials=layers,ground_surface_regions_xz_m=paths+garden+court+rest,native_foundation_regions_xz_m=found,material_ownership_order=[q['role'] for q in layers],floor_ownership='Terrain wrapper owns exact surface materials; native foundations own their holes. No property floor mesh.',source_cut_fill_screen=prop['terrain_feasibility'],finite_gate_approach=approach,retaining_edge_candidates=edges,retained_lower_ground=remaining))
  checks.append(dict(property_id=pid,partition_error_m2=error,garden_area_m2=area(garden),net_unobstructed_gravel_court_area_m2=area(court),source_gate_grade=approach['maximum_profile_grade'],retaining_segments=len(edges),maximum_boundary_cut_m=max([e['maximum_sampled_cut_m'] for e in edges] or [0]),maximum_boundary_fill_m=max([e['maximum_sampled_fill_m'] for e in edges] or [0]),residual_yard_area_m2=area(residual)));print('pieces',len(found),len(paths),len(garden),len(court),len(rest),'residual',len(residual),flush=True)
 out=dict(schema='riverstone.merchant_fabric_r02_terrain_handoff.v1',status='finite_source_proposal_pending_terrain_ownership_and_native_support',pack=ref(HERE/'resolved_placements.json'),eligibility=ref(HERE/'effective_eligibility.json'),native_review=ref(HERE/'native_review.json'),screening_terrain=ref(Path(terrain.__file__)),r14_collar_reservation=ref(HERE/'collar_reservation.json'),author=ref(Path(__file__)),properties=records,checks=checks,summary=dict(platforms=len(records),platform_area_m2=sum(p['platform_area_m2'] for p in records),productive_garden_area_m2=sum(c['garden_area_m2'] for c in checks),retained_grade_yard_area_m2=sum(c['residual_yard_area_m2'] for c in checks),maximum_boundary_cut_m=max(c['maximum_boundary_cut_m'] for c in checks),maximum_boundary_fill_m=max(c['maximum_boundary_fill_m'] for c in checks)),limits=['No surface or retaining geometry compiled here. Cut/fill remains sampled source intent.','All full-width public overlaps are explicit proposals; terminal anchors do not prove adjacent-road continuity.','Private residual ground keeps inherited grade; unresolved access is not promoted.']);write(HERE/'terrain_handoff.json',out);print(json.dumps(out['summary'],indent=2));return out
if __name__=='__main__':run()
