"""Independent finite partition/no-road-floor checks for the r02 handoff."""
import json,math
from pathlib import Path
from .grammar import HERE,ref,write,g,estate
from .final_selection import additional_owners
from .author import context,native_masks
from ..merchant_block011.prepare_handoff import subtract,area
from world_city.concept_city_v3.registered_source.author import Domain

def run():
 h=json.loads((HERE/'terrain_handoff.json').read_text());p=json.loads((HERE/'resolved_placements.json').read_text());ctx=context();assert h['pack']==ref(HERE/'resolved_placements.json');issues=[];counts=dict(material_polygons=0,public_ownership_pieces=0,retaining_edges=0,residual_regions=0);native=Domain([q['polygon_xz_m'] for q in p['native_walking_slabs']]);retired=set(p['replaced_placement_ids'])|ctx['old_removed'];allresidual=[]
 extra,extra_sources=additional_owners()
 for poly,identity in zip(extra.polys,extra.ids):ctx['hard'].add(poly,identity)
 for prop in h['properties']:
  pid=prop['property_id'];allpolys=[];index=g._SpatialIndex(12)
  for layer in prop['materials']:
   for poly in layer['polygons_xz_m']:
    counts['material_polygons']+=1;assert g.is_convex_polygon(poly)
    if not estate.contained(poly,prop['platform_polygon_xz_m']):issues.append(dict(kind='material_outside_platform',property_id=pid))
    for i in index.candidates(poly):
     overlap=g.polygon_area(g.convex_intersection(poly,allpolys[i])) if g.positive_area_overlap(poly,allpolys[i],1e-7) else 0
     if overlap>1e-6:issues.append(dict(kind='double_owned_material_floor',property_id=pid,area_m2=overlap))
    index.add(len(allpolys),poly);allpolys.append(poly)
  if abs(sum(g.polygon_area(q) for q in allpolys)-prop['platform_area_m2'])>1e-4:issues.append(dict(kind='partition_area_mismatch',property_id=pid))
  if ctx['roads'].hits(prop['platform_polygon_xz_m']) or ctx['hard'].hits(prop['platform_polygon_xz_m']):issues.append(dict(kind='platform_reserved_owner_overlap',property_id=pid))
  gate=prop['finite_gate_approach'];public=[q['polygon_xz_m'] for q in gate['public_coownership_proposals']];counts['public_ownership_pieces']+=len(public)
  for tri in estate.triangulate(gate['polygon_xz_m']):
   if native.hits(tri) or ctx['hard'].hits(tri):issues.append(dict(kind='gate_native_or_protected_overlap',property_id=pid))
   for i in ctx['native_index'].candidates(tri):
    old=ctx['old']['placements'][i]
    if old['id'] not in retired and any(estate.overlap(tri,q) for q in native_masks(old,ctx)['walk']):issues.append(dict(kind='gate_retained_native_overlap',property_id=pid,other_id=old['id']))
   for i in ctx['roads'].index.candidates(tri):
    q=g.convex_intersection(tri,ctx['roads'].polys[i])
    if g.polygon_area(q)<1e-7:continue
    if area(subtract([q],public))>1e-6:issues.append(dict(kind='undeclared_gate_public_overlap',property_id=pid,road_id=ctx['roads'].ids[i]))
  assert gate['minimum_connector_width_m']>=3.49;assert gate['maximum_profile_grade']<=.12+1e-7
  for edge in prop['retaining_edge_candidates']:
   counts['retaining_edges']+=1;assert math.dist(*edge['edge_xz_m'])<=6+1e-7;assert edge['above_floor_wall_height_m']==0
  for q in prop['retained_lower_ground']['polygons_xz_m']:
   counts['residual_regions']+=1
   if ctx['roads'].hits(q) or ctx['hard'].hits(q):issues.append(dict(kind='residual_yard_protected_overlap',property_id=pid))
   if any(estate.overlap(q,r) for r in allresidual):issues.append(dict(kind='residual_double_ownership',property_id=pid))
   allresidual.append(q)
 result=dict(schema='riverstone.merchant_fabric_r02_handoff_review.v1',handoff=ref(HERE/'terrain_handoff.json'),pack=ref(HERE/'resolved_placements.json'),checker=ref(Path(__file__)),status='pass_finite_material_partition_and_gate_domains' if not issues else 'failed',counts=counts,issues=issues,limits=['Finite source ownership only. Actual terrain support, retaining and public collars require a separately accepted terrain revision.','Residual yard fragments retain prior grade and unresolved service access.']);write(HERE/'handoff_review.json',result);print(json.dumps(result,indent=2));return result
if __name__=='__main__':raise SystemExit(bool(run()['issues']))
