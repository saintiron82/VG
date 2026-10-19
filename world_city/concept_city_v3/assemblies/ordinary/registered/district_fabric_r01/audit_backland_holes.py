"""Name every missing backland top and preserve partial old-ground supersessions."""
from . import geometry as g
from .design import HERE as SOURCE
from .allocate_backlands import OUT,setup
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc

def run():
 p=OUT/'native_ground_program_final.json'
 if not p.exists():p=OUT/'native_ground_program_r02.json'
 program=g.load(p);manifest=g.load(SOURCE/'effective_city_manifest_r01.json');retired=set(manifest['replaced_placement_ids']);r17=g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01';records=g.load(r17/'retirement_candidates.json')['rows'];proofs={r['source_id']:r for r in g.load(r17/'body_boundary_audit.json')['rows']};sp=g.geo._SpatialIndex(16)
 for i,r in enumerate(records):sp.add(i,r['old_terrain_body_hole_polygon_xz_m'])
 regions=[];unclassified=[]
 for own in program['ground_owners']:
  for mi,poly in enumerate(own['missing_original_top_polygons_xz_m']):
   covered=[]
   for j in sp.candidates(poly):
    r=records[j];part=tc.clean(g.geo.convex_intersection(poly,r['old_terrain_body_hole_polygon_xz_m']))
    if not part:continue
    covered.append(part);regions.append(dict(id=own['id']+f':MISSING:{mi}:{r["source_id"]}',ground_owner_id=own['id'],source_id=r['source_id'],polygon_xz_m=part,area_m2=g.geo.polygon_area(part),old_finished_floor_y_m=r['existing_finished_floor_y_m'],source_body_boundary_status=proofs[r['source_id']].get('status'),retired_in_effective_city_manifest=r['source_id']in retired,proposed_new_material=next((q['target_material']for q in own['material_source_pieces']),'ground_earth'),restoration_authority='Finite exposed old body-hole ownership; R17 must compose the true transition from surviving source edges. No new independent full pad is authorized.'))
   for q in tc.subtract([poly],covered):
    if g.geo.polygon_area(q)>1e-7:unclassified.append(dict(ground_owner_id=own['id'],polygon_xz_m=q,area_m2=g.geo.polygon_area(q),status='HELD_UNCLASSIFIED_MISSING_R7_TOP'))
 ledger=dict(schema='riverstone.district_fabric.backland_missing_tops.v1',source_program=g.ref(p),effective_city_manifest=g.ref(SOURCE/'effective_city_manifest_r01.json'),retirement_candidates=g.ref(r17/'retirement_candidates.json'),body_boundary_audit=g.ref(r17/'body_boundary_audit.json'),regions=regions,unclassified=unclassified,summary=dict(named_old_body_hole_area_m2=sum(r['area_m2']for r in regions),effective_retired_body_area_m2=sum(r['area_m2']for r in regions if r['retired_in_effective_city_manifest']),held_nonretired_body_area_m2=sum(r['area_m2']for r in regions if not r['retired_in_effective_city_manifest']),unclassified_missing_area_m2=sum(r['area_m2']for r in unclassified)));g.write(OUT/'missing_top_ownership.json',ledger);print(ledger['summary'])
 base=g.np.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_masks.npz');setup(base);labels=g.np.load(g.CITY/'registered_integration/r8/coverage_plan/ground_unit_labels.npz')['unit_labels'];alloc=g.load(OUT/'ground_owner_allocation.json');am=g.np.load(OUT/'allocation_masks.npz')['allocation'];old=g.load(g.CITY/'registered_integration/r8/coverage_plan/ground_program_units.json');effective={o['id']for o in program['ground_owners']if o['block_id']!='BLOCK_007'};lookup={i:o['id']for i,o in enumerate(alloc['owners'],1)if o['id']in effective};units=[]
 for i,u in enumerate(old['units'],1):
  m=labels==i;replacements=[];used=g.np.zeros(g.SHAPE,bool)
  for ai in g.np.unique(am[m]):
   if ai not in lookup:continue
   take=m&(am==ai);used|=take;replacements.append(dict(new_ground_owner_id=lookup[int(ai)],source_grid_area_m2=int(take.sum()),finite_superseded_polygon_parts_xz_m=g.parts(take)))
  if not replacements:continue
  remaining=m&~used;units.append(dict(old_unit_id=u['id'],old_unit_function=u['source_function'],replacements=replacements,remaining_source_grid_m2=int(remaining.sum()),preserved_remainder_polygon_parts_xz_m=g.parts(remaining),atomic_rule='Supersede only listed finite intersections. Keep the explicit remainder unless another accepted native/route/protected-owner job replaces it.'))
 out=dict(schema='riverstone.district_fabric.backland_fragment_supersession.v1',old_ground_program=g.ref(g.CITY/'registered_integration/r8/coverage_plan/ground_program_units.json'),new_native_program=g.ref(p),effective_city_manifest=g.ref(SOURCE/'effective_city_manifest_r01.json'),units=units,summary=dict(touched_old_units=len(units),fully_replaced_old_units=sum(u['remaining_source_grid_m2']==0 for u in units),partially_replaced_old_units=sum(u['remaining_source_grid_m2']>0 for u in units)),held_blocks=['BLOCK_007'],partial_old_units_are_not_wholly_retired=True);g.write(OUT/'fragment_supersession.json',out);print(out['summary'])
if __name__=='__main__':run()
