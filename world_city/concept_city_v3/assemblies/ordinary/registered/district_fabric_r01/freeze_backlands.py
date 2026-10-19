"""Freeze finite backland materials and complete native use systems.

Analytic fragment perimeter traces are diagnostic only. Incomplete enclosures are
withheld atomically rather than emitting scattered rail fragments.
"""
from . import geometry as g
from .design import HERE as SOURCE
from .allocate_backlands import OUT
from collections import defaultdict

def run():
 pp=OUT/'native_ground_program_final.json';bp=OUT/'native_boundary_addendum_r01.json';prog=g.load(pp);bound=g.load(bp);access=g.load(OUT/'access_handoff_final.json');manifest=g.load(SOURCE/'effective_city_manifest_r01.json');owners={r['id']:r for r in prog['ground_owners']};retired=set(manifest['replaced_placement_ids']);projection=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];retained=[q for r in projection if r['id']not in retired for q in r['native_owner_parts_xz_m']];newnative=[];currentroutes=[]
 for d in manifest['districts']:
  pack=g.load(g.ROOT/d['pack']['path']);l=g.load(g.ROOT/pack['layout']['path']);newnative += [q for p in l['placements']for q in p['native_walking_obstacles_xz_m']];cp=(g.ROOT/pack['layout']['path']).parent/'court_equipment.json'
  if cp.exists():newnative += [q for p in g.load(cp)['placements']for q in p['native_walking_obstacles_xz_m']]
  t=g.load(g.ROOT/d['terrain']['path']);currentroutes += [q for p in t['parcels']for q in p['walk_polygons_xz_m']]
 b15=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/coherent_b15_r02/route_handoff.json');sealedroutes=[q for r in b15['nodes']+b15['door_routes']for q in r['polygons_xz_m']];b05=g.load(SOURCE/'contour_revision_r01/b05_dryside_addendum_r01.json');currentroutes+=b05['replacement_route']['polygons_xz_m'];oldrows=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01/retirement_candidates.json')['rows'];retained_access=[q for r in oldrows if r['source_id']not in retired for a in r['actual_old_access_records']for q in a['reserved_connection_polygons_xz_m']];routes=[q for r in access['routes']for q in r['polygons_xz_m']]+bound['preserved_access_polygons_xz_m']+retained_access+sealedroutes+currentroutes;sets={'retained_native':retained,'selected_city_native':newnative,'reserved_access':routes};indexes={}
 for k,polys in sets.items():
  si=g.geo._SpatialIndex(16)
  for i,p in enumerate(polys):si.add(i,p)
  indexes[k]=si
 def hit(k,ps):return sum(g.geo.intersection_area(p,sets[k][j])for p in ps for j in indexes[k].candidates(p))
 kept=[];rejected=[];held=[]
 # The 15,419 analytic outer rails never enter this active candidate list.
 for p in prog['placements']:
  if owners[p['ground_owner_id']]['block_id']=='BLOCK_007':held.append(dict(id=p['id'],reason='B07 native/contour source remains held'));continue
  checks={k:hit(k,p['native_walking_obstacles_xz_m'])for k in sets}
  if any(v>1e-7 for v in checks.values()):rejected.append(dict(id=p['id'],ground_owner_id=p['ground_owner_id'],reason='Exact projected retained/new-native or preserved-access clearance gate',overlap_m2=checks));continue
  p=dict(p,source_pack='ordinary_backland_completion_r01');p['native_bottom_y_m']=p['position_m'][1]+prog['assets'][p['asset_key']]['bounds']['min'][1];kept.append(p)
 # Each deliberately rectangular enclosed court is an indivisible native system.
 keptids={p['id']for p in kept};complete=[];incomplete=[];remove=set()
 for e in prog['enclosures']:
  missing=[pid for pid in e['boundary_ids']if pid not in keptids];gate_checks={k:hit(k,e['full_width_gate_access']['polygons_xz_m'])for k in ('retained_native','selected_city_native')}
  if missing or any(v>1e-7 for v in gate_checks.values()):
   incomplete.append(dict(id=e['id'],ground_owner_id=e['ground_owner_id'],missing_boundary_ids=missing,gate_native_overlap_m2=gate_checks,status='HELD_COMPLETE_ENCLOSURE_SYSTEM'));remove.update(e['boundary_ids'])
  else:complete.append(dict(e,status='COMPLETE_GATED_SUBYARD_SOURCE_PENDING_TERRAIN_ROUTE_SIDE_PROOF'))
 for p in kept:
  if p['id']in remove:held.append(dict(id=p['id'],reason='Whole enclosure withheld because at least one necessary boundary panel failed final clearance'))
 kept=[p for p in kept if p['id']not in remove];keptids={p['id']for p in kept}
 # Explicit internal native pair gate, allowing only intended rail corner joints.
 ni=g.geo._SpatialIndex(8);polys=[];polyowners=[];contacts=[]
 for p in kept:
  for q in p['native_walking_obstacles_xz_m']:
   for j in ni.candidates(q):
    other=polyowners[j]
    if other['id']==p['id']or(p['asset_key']==other['asset_key']=='district_r01_boundary_2m'and p['ground_owner_id']==other['ground_owner_id']):continue
    a=g.geo.intersection_area(q,polys[j])
    if a>1e-7:contacts.append(dict(a=p['id'],b=other['id'],area_m2=a))
   ni.add(len(polys),q);polys.append(q);polyowners.append(p)
 if contacts:raise RuntimeError('Unresolved native internal contacts: '+str(contacts[:8]))
 byowner=defaultdict(list)
 for p in kept:byowner[p['ground_owner_id']].append(p)
 completebyowner={e['ground_owner_id']:e for e in complete};grounds=[];functional=defaultdict(list)
 for oid,o in owners.items():
  if o['block_id']=='BLOCK_007':continue
  o=g.copy.deepcopy(o);o['native_placement_ids']=[p['id']for p in byowner[oid]];o['native_hole_polygons_xz_m']=[q for p in byowner[oid]for q in p['native_foundation_polygons_xz_m']];o['enclosure_id']=completebyowner.get(oid,{}).get('id');o['retained_native_hole_policy']='Original missing tops under retained native owners remain occupied holes; no duplicate fill.';o['source_material_piece_policy']='Compose by original R7 triangle identity. Subtract sealed B15/current district profile owners, every actual route owner and all new native holes before emitting private material surfaces.';o['required_public_and_private_route_exclusions']=True;o['boundary_status']='COMPLETE_GATED_SUBYARD_WITH_OPEN_REMAINDER'if oid in completebyowner else'OPEN_FUNCTIONAL_GROUND_OUTER_ENCLOSURE_HELD';o['completion_status']='FROZEN_NATIVE_SOURCE_REQUIRING_R17_COMPOSED_PLANE_SIDE_AND_RUNTIME_ACCEPTANCE';grounds.append(o);functional[o['named_owner']].append(o)
 ledger=[]
 for name,os in sorted(functional.items()):
  es=[completebyowner[o['id']]for o in os if o['id']in completebyowner];ledger.append(dict(named_owner=name,block_id=os[0]['block_id'],ground_component_ids=[o['id']for o in os],source_ground_area_m2=sum(o['source_ground_area_m2']for o in os),planned_functions=sorted({o['planned_function']for o in os}),complete_gated_subyard_ids=[e['id']for e in es],outer_boundary_status='HELD_AS_A_COMPLETE_FUNCTIONAL_HOLDING_SYSTEM',analytic_fragment_fences_active=False,status='HAS_COMPLETE_GATED_SUBYARD'if es else'OPEN_SHARED_OR_WORKING_GROUND'))
 boundary_report=dict(schema='riverstone.district_fabric.functional_boundary_continuity.v1',source_trace=g.ref(bp),native_program=g.ref(pp),functional_owners=ledger,complete_gated_subyards=complete,held_subyard_systems=incomplete,withheld_analytic_perimeter_panels=len(bound['placements']),fully_enclosed_functional_holdings=0,complete_gated_subyards_count=len(complete),functional_owners_with_complete_gated_subyards=sum(bool(r['complete_gated_subyard_ids'])for r in ledger),open_functional_owners=sum(not r['complete_gated_subyard_ids']for r in ledger),partial_enclosure_rails_emitted=0,policy='All same-name ground fragments form one functional holding. Analytic raster fragment perimeter rails are withheld, including individually supported fragments. Only complete deliberately shaped native courtyard systems with connected gate reservations are selected. Outer-boundary redesign remains explicit; these grounds are not claimed enclosed.');g.write(OUT/'boundary_continuity.json',boundary_report)
 activeids={o['id']for o in grounds};summary=dict(native_ground_owners=len(grounds),named_functional_holdings=len(ledger),actual_R7_source_top_area_m2=sum(o['source_ground_area_m2']for o in grounds),source_nonwalking_slope_verge_area_m2=sum(o['nonwalking_slope_verge_area_m2']for o in grounds),proposed_native_instances=len(kept),native_boundary_panels=sum(p['asset_key']=='district_r01_boundary_2m'for p in kept),productive_beds=sum(p['asset_key']=='productive_bed'for p in kept),other_native_function_equipment=sum(p['asset_key']not in['district_r01_boundary_2m','productive_bed']for p in kept),complete_gated_subyards=len(complete),fully_enclosed_functional_holdings=0,withheld_analytic_perimeter_panels=len(bound['placements']),partial_enclosure_rails_emitted=0,rejected_source_native_instances=len(rejected),held_native_instances=len(held),unresolved_access_owners=len(access['held_owner_routes']),unresolved_access_ground_m2=access['summary']['held_ground_m2'],new_compilations=0)
 proof=dict(schema='riverstone.district_fabric.backland_native_source_audit.v1',base_scene=g.ref(g.R7),effective_city_manifest=g.ref(SOURCE/'effective_city_manifest_r01.json'),source_program=g.ref(pp),source_boundaries=g.ref(bp),source_access=g.ref(OUT/'access_handoff_final.json'),rejected_native_candidates=rejected,held_candidates=held,checks=dict(unique_ids=len(keptids)==len(kept),unit_scales=all(p['scale']==[1,1,1]for p in kept),retained_new_native_access_projected_clearance=True,new_native_internal_contacts=len(contacts)==0,exact_source_plane_support=all(p['support_proof'].get('missing_top_area_m2',0)<=1e-7 for p in kept),same_approved_native_asset_bytes=all(g.ref(g.ROOT/a['render_path'])['sha256']==a['render_sha256']for a in prog['assets'].values()),complete_enclosure_systems=all(all(pid in keptids for pid in e['boundary_ids'])for e in complete)),limits=['Intentional rail corner/end joints may overlap within the same native courtyard system.','Terrain side faces, route grades, restoration-plane material transfer and integrated runtime acceptance remain R17/R18 gates.']);proof['passed']=all(proof['checks'].values());g.write(OUT/'source_native_audit.json',proof)
 terrain=dict(schema='riverstone.district_fabric.backland_terrain_batch.v1',base_scene=g.ref(g.R7),effective_city_manifest=g.ref(SOURCE/'effective_city_manifest_r01.json'),ground_mode='preserve_actual_source_planes_with_finite_original_triangle_ownership',material_owners=grounds,full_width_routes=[r for r in access['routes']if r['ground_owner_id']in activeids],enclosure_gate_routes=[dict(ground_owner_id=e['ground_owner_id'],**e['full_width_gate_access'])for e in complete],native_placements=kept,existing_access_reservations=bound['preserved_access_polygons_xz_m']+retained_access,sealed_B15_routes=sealedroutes,current_city_route_reservations=currentroutes,missing_top_ownership=g.ref(OUT/'missing_top_ownership_final.json'),partial_old_fragment_supersession=g.ref(OUT/'fragment_supersession.json'),boundary_continuity=g.ref(OUT/'boundary_continuity.json'),retirement_activation='No independent new ordinary retirements. The selected effective city manifest and accepted R17 extensions exclusively authorize old native/pad/bank retirement.',composition_rules=['Do not append a second plane in an old body hole. Reclassify the exact residual-body restoration plane already emitted by the relevant district patch.','Retained native bottom holes remain holes. Unclassified missing tops stay held.','Group all source cuts by original R7 triangle identity; emit one remainder and one material owner per finite piece.','Public traffic/water/special-owner geometry and sealed public/private route profiles have precedence over private ground paint.'],summary=summary,status='FROZEN_SOURCE_BULK_REQUIRING_R17_GROUND_ROUTE_SIDE_ACCEPTANCE');g.write(OUT/'terrain_handoff.json',terrain)
 pack=dict(schema='riverstone.district_fabric.backland_native_pack.v1',base_scene=g.ref(g.R7),effective_city_manifest=g.ref(SOURCE/'effective_city_manifest_r01.json'),assets=prog['assets'],placements=kept,terrain_handoff=g.ref(OUT/'terrain_handoff.json'),source_audit=g.ref(OUT/'source_native_audit.json'),boundary_continuity=g.ref(OUT/'boundary_continuity.json'),summary=summary,implementation_tier='exterior_only',new_compilations=0,status=terrain['status'],source_references=[g.ref(pp),g.ref(bp),g.ref(OUT/'access_handoff_final.json')],limits=['This source pack does not certify whole-city physical completion. Explicit access, outer-enclosure and missing-top holds remain.','No simulated cultivation, commerce, water supply or open interiors.']);g.write(OUT/'resolved_placements.json',pack);g.write(OUT/'freeze_manifest.json',dict(pack=g.ref(OUT/'resolved_placements.json'),terrain=g.ref(OUT/'terrain_handoff.json'),audit=g.ref(OUT/'source_native_audit.json'),boundary_continuity=g.ref(OUT/'boundary_continuity.json'),missing_tops=g.ref(OUT/'missing_top_ownership_final.json'),fragment_supersession=g.ref(OUT/'fragment_supersession.json'),summary=summary));print(summary);print(g.ref(OUT/'resolved_placements.json'))
if __name__=='__main__':run()
