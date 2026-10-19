"""Finite partition, native boundary, public-ownership and gate-domain checks."""
import json,math
from pathlib import Path
from .grammar import HERE,ROOT,PLAN,ORDINARY,ref,write,g,estate
from .prepare_handoff import difference
from world_city.concept_city_v3.registered_source.author import Domain

def run():
 h=json.loads((HERE/'terrain_handoff.json').read_text());p=json.loads((HERE/'resolved_placements.json').read_text());plan=json.loads(PLAN.read_text());old=json.loads(ORDINARY.read_text());assert h['pack']==ref(HERE/'resolved_placements.json');issues=[];counts=dict(material_polygons=0,public_ownership_pieces=0,retaining_edges=0)
 native=Domain([q['polygon_xz_m'] for q in p['native_walking_slabs']]);water=Domain([q['polygon_xz_m'] for q in plan['water_reservations']['finite_water_polygons']]);fixed=Domain([q['actual_outer_footprint_xz_m'] for q in old['placements'] if q['id'] not in p['replaced_placement_ids']]);roads=Domain()
 for road in plan['roads']:
  for si,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):roads.add(g.road_ribbon(a,b,road['width_m']),road['id']+':'+str(si))
 for prop in h['properties']:
  pid=prop['property_id'];allpolys=[];index=g._SpatialIndex(12)
  for layer in prop['materials']:
   for poly in layer['polygons_xz_m']:
    counts['material_polygons']+=1;assert g.is_convex_polygon(poly)
    if not estate.contained(poly,prop['platform_polygon_xz_m']):issues.append(dict(kind='material_outside_platform',property_id=pid))
    for i in index.candidates(poly):
     if g.positive_area_overlap(poly,allpolys[i],1e-7):
      area=g.polygon_area(g.convex_intersection(poly,allpolys[i]))
      if area>1e-6:issues.append(dict(kind='double_owned_material_floor',property_id=pid,area_m2=area))
    index.add(len(allpolys),poly);allpolys.append(poly)
  if abs(sum(g.polygon_area(q) for q in allpolys)-prop['platform_area_m2'])>1e-4:issues.append(dict(kind='partition_area_mismatch',property_id=pid))
  if roads.hits(prop['platform_polygon_xz_m']) or water.hits(prop['platform_polygon_xz_m']):issues.append(dict(kind='platform_public_or_water_overlap',property_id=pid))
  gate=prop['finite_gate_approach'];public=[q['polygon_xz_m'] for q in gate['public_coownership_proposals']];counts['public_ownership_pieces']+=len(public)
  for tri in estate.triangulate(gate['polygon_xz_m']):
   for label,domain in [('native',native),('water',water),('retained_building',fixed)]:
    if domain.hits(tri):issues.append(dict(kind='gate_'+label+'_overlap',property_id=pid))
   for i in roads.index.candidates(tri):
    q=g.convex_intersection(tri,roads.polys[i])
    if g.polygon_area(q)<1e-7:continue
    rest=[q]
    for cover in public:rest=[s for r in rest for s in difference(r,cover)]
    if sum(g.polygon_area(r) for r in rest)>1e-6:issues.append(dict(kind='undeclared_gate_public_overlap',property_id=pid,road_id=roads.ids[i]))
  assert gate['minimum_connector_width_m']>=3.49
  for edge in prop['retaining_edge_candidates']:
   counts['retaining_edges']+=1;assert math.dist(*edge['edge_xz_m'])<=6+1e-7;assert edge['above_floor_wall_height_m']==0;assert edge['maximum_endpoint_fill_m']<=3+1e-7
 result=dict(schema='riverstone.merchant_finite_handoff_review.v1',handoff=ref(HERE/'terrain_handoff.json'),pack=ref(HERE/'resolved_placements.json'),checker=ref(Path(__file__)),status='pass_finite_material_partition_and_gate_domains' if not issues else 'failed',counts=counts,issues=issues,limits=['Finite source domains and sampled public-profile agreement only; no native support or continuous seam promotion.','Public co-ownership and retaining interfaces require acceptance in a separate terrain revision.']);write(HERE/'handoff_review.json',result);print(json.dumps(result,indent=2));return result
if __name__=='__main__':raise SystemExit(bool(run()['issues']))
