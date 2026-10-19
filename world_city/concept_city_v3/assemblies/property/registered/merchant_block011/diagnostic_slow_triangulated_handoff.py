"""Finite floor/material and access intents for a later reviewed terrain wrapper."""
import json,math
from pathlib import Path
from .grammar import HERE,ROOT,PLAN,ref,write,rect,worldpoly,xform,g,estate
from .author import terrain
from world_city.concept_city_v3.assemblies.property.registered.poor_block015_east.author_density import disjoint

def subtract(polys,cuts):
 index=g._SpatialIndex(24)
 for i,q in enumerate(cuts):index.add(i,q)
 out=[]
 for poly in polys:
  parts=[poly]
  for i in sorted(index.candidates(poly)):parts=[p for q in parts for p in g.convex_difference(q,cuts[i]) if g.polygon_area(p)>1e-7]
  out+=parts
 return out
def union(polys):return disjoint([tri for p in polys for tri in estate.triangulate(p)])
def area(polys):return sum(g.polygon_area(q) for q in polys)

def run():
 source=json.loads((HERE/'proposal.json').read_text());pack=json.loads((HERE/'resolved_placements.json').read_text());review=json.loads((HERE/'native_review.json').read_text());assert not review['issues'];assert review['pack']==ref(HERE/'resolved_placements.json');plan=json.loads(PLAN.read_text());roads={r['id']:r for r in plan['roads']};records=[];checks=[]
 for prop in source['properties']:
  pid=prop['id'];floor=prop['floor_y_m'];frame=prop['polygon_xz_m'];found=union([q for m in pack['ownership_masks'] if m['property_id']==pid for q in m['terrain_exclusion_regions_xz_m']]);routes=[r for r in pack['access_proposals'] if r['property_id']==pid]
  route_polys=[q for r in routes for q in r['ribbon_polygons_xz_m']+r['round_join_polygons_xz_m']]
  # The native closed threshold leaf is the start of the physical approach,
  # while the generous full-width reservation begins at its outer-envelope lip.
  stubs=[]
  for d in pack['actual_doors']:
   if d['owner_id'].startswith(pid+':'):
    width=min(x['native_leaf_width_m'] for x in d['actual_union_threshold_evidence']);a,b=d['cached_threshold_stub_xz_m']
    if math.dist(a,b)>1e-8:stubs.append(g.road_ribbon(a,b,width))
  paths=subtract(union(route_polys+stubs),found);court=subtract(union([prop['court']['polygon_xz_m']]),found+paths);rest=subtract([frame],found+paths+court)
  layers=[dict(role='native_foundation',material='native_asset_owned',polygons_xz_m=found),dict(role='connected_pedestrian_and_goods_access',material='cobblestone',polygons_xz_m=paths),dict(role='shared_goods_handling_court',material='compacted_gravel',polygons_xz_m=court),dict(role='service_apron_and_yard',material='packed_earth',polygons_xz_m=rest)]
  for layer in layers:layer['area_m2']=area(layer['polygons_xz_m'])
  error=abs(sum(x['area_m2'] for x in layers)-g.polygon_area(frame));assert error<1e-4,(pid,error)
  # The seven current road endpoints are locally level. Record complete native
  # seam anchors and retain explicit rejection if the terrain API changes.
  link=prop['external_gate_link'];gate,end=link['polyline_xz_m'];direction=[(end[k]-gate[k])/math.dist(gate,end) for k in (0,1)];cross=[-direction[1],direction[0]];left=xform([14.25,21],prop['origin_xz_m'],prop['yaw_rad']);right=xform([17.75,21],prop['origin_xz_m'],prop['yaw_rad']);ends=[[end[k]+s*1.75*cross[k] for k in (0,1)] for s in(-1,1)]
  if math.dist(left,ends[0])+math.dist(right,ends[1])>math.dist(left,ends[1])+math.dist(right,ends[0]):ends.reverse()
  endpoint_profile=[]
  for i in range(17):
   t=i/16;q=[ends[0][k]*(1-t)+ends[1][k]*t for k in (0,1)];endpoint_profile.append(dict(t=t,point_xz_m=q,y_m=terrain.land_height_at(*q)))
  deviation=max(abs(x['y_m']-floor) for x in endpoint_profile);assert deviation<1e-7,(pid,deviation)
  polygon=[left,right,ends[1],ends[0]];tris=estate.triangulate(polygon);public=[];road=roads[link['road_id']]
  for si,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   ribbon=g.road_ribbon(a,b,road['width_m'])
   for tri in tris:
    q=g.convex_intersection(tri,ribbon)
    if g.polygon_area(q)>1e-7:public.append(dict(road_id=road['id'],segment_index=si,polygon_xz_m=q,finished_floor_y_m=floor))
  sample=[]
  for t in (0,.25,.5,.75,1):
   for u in (0,.25,.5,.75,1):
    a=[left[k]*(1-u)+right[k]*u for k in (0,1)];b=[ends[0][k]*(1-u)+ends[1][k]*u for k in(0,1)];q=[a[k]*(1-t)+b[k]*t for k in(0,1)];y=terrain.land_height_at(*q);sample.append(dict(point_xz_m=q,existing_y_m=y,cut_m=max(0,y-floor),fill_m=max(0,floor-y)))
  approach=dict(id=pid+':FINITE_PUBLIC_HANDOFF',road_id=road['id'],source_target_segment=link['segment_index'],polygon_xz_m=polygon,width_m=3.5,minimum_connector_width_m=3.5,gate_edge_xz_m=[left,right],public_edge_xz_m=ends,endpoint_profile=endpoint_profile,triangles_xyz_m=[[[q[0],floor,q[1]] for q in tri] for tri in tris],height_evaluator=dict(kind='constant_plane',y_m=floor),maximum_profile_grade=0,maximum_sampled_cut_m=max(x['cut_m'] for x in sample),maximum_sampled_fill_m=max(x['fill_m'] for x in sample),samples=sample,public_coownership_proposals=public,surface_owner='merchant_terrain_wrapper_candidate',status='finite source proposal; public coownership and native sampled seam require terrain review',capsule_validated=False)
  edges=[];local=[[-18,-21],[18,-21],[18,21],[17.75,21],[14.25,21],[-18,21]]
  # Omit only the intentional 3.5 m gate. Retaining tops stop at floor and
  # cannot become a walking-height wall/rail without a new clearance review.
  for ei,(a,b) in enumerate(zip(local,local[1:]+local[:1])):
   if ei==3:continue
   n=math.ceil(math.dist(a,b)/6)
   for i in range(n):
    q=[xform([a[k]+(b[k]-a[k])*s/n for k in (0,1)],prop['origin_xz_m'],prop['yaw_rad']) for s in(i,i+1)];ys=[terrain.land_height_at(*x) for x in q];height=max(floor-y for y in ys)
    if height>.25:edges.append(dict(id=pid+f':RETAINING:{ei}:{i}',edge_xz_m=q,existing_ground_end_y_m=ys,top_y_m=floor,maximum_endpoint_fill_m=height,maximum_length_m=6,above_floor_wall_height_m=0,support_owner='merchant_terrain_wrapper_candidate',ownership='Finite edge-only below-floor retaining. No broad precinct hole.',status='source engineering/ownership intent, no native retaining cache yet'))
  records.append(dict(property_id=pid,block_id=prop['block_id'],platform_polygon_xz_m=frame,finished_floor_y_m=floor,platform_area_m2=g.polygon_area(frame),materials=layers,ground_surface_regions_xz_m=paths+court+rest,native_foundation_regions_xz_m=found,material_ownership_order=['native_foundation','connected_pedestrian_and_goods_access','shared_goods_handling_court','service_apron_and_yard'],floor_ownership='One terrain wrapper owns surface materials; native foundations own their exact regions. No duplicate property slab.',source_cut_fill_screen=prop['terrain_feasibility'],finite_gate_approach=approach,retaining_edge_candidates=edges,retained_lower_ground=[r for r in pack['retired_source_residuals'] if r['retired_placement_id'] in prop['source_retired_native_ids']]))
  checks.append(dict(property_id=pid,partition_error_m2=error,partition_area_m2=sum(x['area_m2'] for x in layers),gate_public_profile_error_m=deviation,source_gate_grade=0,retaining_segments=len(edges)))
 out=dict(schema='riverstone.merchant_finite_terrain_handoff.v1',status='source_domain_proposal_pending_terrain_ownership_and_native_support_review',pack=ref(HERE/'resolved_placements.json'),proposal=ref(HERE/'proposal.json'),native_review=ref(HERE/'native_review.json'),terrain_author=ref(Path(terrain.__file__)),author=ref(Path(__file__)),properties=records,checks=checks,source_floor_owner='next merchant terrain wrapper',limits=['No native ground/retaining compile is included.','Cut/fill is sampled eligibility, not continuous proof or soil engineering certification.','Exact public overlap polygons require explicit terrain acceptance.','Lower residual yards retain prior grade and unresolved service access.'])
 write(HERE/'terrain_handoff.json',out);print(json.dumps(dict(handoff=ref(HERE/'terrain_handoff.json'),checks=checks),indent=2));return out
if __name__=='__main__':run()
