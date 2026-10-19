"""Application-only current-plane polygons; future private owners win."""
from . import geometry as g
from .activate_backlands_subset import MaskIndex
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import Counter
import copy
OUT=g.HERE/'backland_completion_r01/residual_material_application_r01'
def area(ps):return sum(g.geo.polygon_area(p)for p in ps)
def run():
 OUT.mkdir(exist_ok=True);sp=g.HERE/'backland_completion_r01/residual_land_use_r01/source_plan.json';source=g.load(sp);scene=g.load(g.ROOT/source['actual_source_scene']['path']);r17=g.CITY/'registered_topography/revisions/r17_district_batches';ledgerp=r17/'public_dependency_review_r01/remaining17_and_b07_ledger_r01.json';held={r['holding_id']for r in g.load(ledgerp)['held_holdings']};lp=r17/'contour_bulk_r01/effective_source_layout_r03.json';bp=g.HERE/'b07_terrace_refit_r02/BLOCK_007/selected_layout.json';holdings=[h for h in g.load(lp)['holdings']if h['id']in held]+g.load(bp)['holdings'];masks=[];refs=[g.ref(lp),g.ref(bp)]
 for h in holdings:masks +=[dict(id=h['id'],kind='PENDING_FINAL24_SOURCE_OWNER_OR_ENTRY',polygon_xz_m=p)for p in [h['holding_polygon_xz_m']]+h['external_route_polygons_xz_m']]
 for folder in ['hard_core_native_refit_r02','hard_core_native_refit_r03','hard_core_native_refit_r05','hard_core_native_refit_r08','paired_contour_entry_refit_r02','paired_contour_entry_refit_r03']:
  p=g.HERE/folder/'source_candidates.json';refs.append(g.ref(p))
  for r in g.load(p)['records']:
   masks +=[dict(id=r['holding_id'],kind='PENDING_FINAL24_REVISED_PROFILE_OR_FLAT_CORE',polygon_xz_m=q)for q in r['flat_owner_polygons_xz_m']+r['profile_domain_polygons_xz_m']]
 mi=MaskIndex(masks);rows=[];ceded=[];preserved=[];counts=Counter()
 for owner in source['regions']:
  for p in owner['same_plane_functional_ground']:
   cuts=mi.hit([p['polygon_xz_m']]);unique=a.common.disjoint_union([q['polygon_xz_m']for q in cuts]);ceded +=[dict(source_owner_id=owner['id'],private_owner_ids=sorted({q['id']for q in cuts}),polygon_xz_m=q,area_m2=g.geo.polygon_area(q))for q in unique]
   for q in a.common.subtract([p['polygon_xz_m']],unique):
    r=dict(source_owner_id=owner['id'],named_function_owner=p['named_function_owner'],planned_function=p['planned_function'],source_material=p['material'],source_triangle_index=p['triangle_index'],source_triangle_sha256=p['source_triangle_sha256'],polygon_xz_m=q,plane_y_xz_m=p['plane_y_xz_m'],target_material=p['proposed_material'],area_m2=g.geo.polygon_area(q),height_action='PRESERVE_EXACT_R04_SOURCE_PLANE',new_walkability_claim=False,new_native_facility_claim=False)
    if scene['materials'].get(p['material'])==scene['materials'].get(p['proposed_material']):preserved.append(r);counts['already_target_material_m2']+=r['area_m2']
    else:rows.append(r);counts['material_application_area_m2']+=r['area_m2'];counts['target_'+r['target_material']+'_m2']+=r['area_m2']
 report=dict(schema='riverstone.residual_ground.material_application_only.v1',source_plan=g.ref(sp),actual_R04_source_scene=source['actual_source_scene'],exact_original_reservation_sources=source['reservation_sources'],pending_final24_reservation_sources=refs,remaining_holding_ledger=g.ref(ledgerp),author=g.ref(__file__),material_application_regions=rows,already_matching_material_regions=preserved,ceded_to_future_private_owners=ceded,unchanged_slope_reservation_and_hole_regions_source=g.ref(sp),summary=dict(counts,source_functional_area_m2=source['summary']['disposition_area_m2']['functional_ground_area_m2'],ceded_pending_private_area_m2=area([q['polygon_xz_m']for q in ceded]),new_native_instances=0,new_height_or_bank_edits=0),composition_rules=['Use exact R04 source triangle/hash and original plane. Preserve all source-plan reservations, measured nonwalking slopes and existing holes.','Cede to the final24 actual physical ownership if its final domains change after this snapshot; these material regions never override a private regrade.','Already-matching material regions need only ownership metadata, not duplicate surface geometry.','New labels do not count as new facilities. This handoff creates only the listed visible material changes on existing ground.']);g.write(OUT/'application_handoff.json',report);print(report['summary']);print(g.ref(OUT/'application_handoff.json'))
if __name__=='__main__':run()
