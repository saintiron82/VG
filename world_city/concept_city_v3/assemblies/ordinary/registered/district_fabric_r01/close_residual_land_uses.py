"""Assign all sixteen substantive source remainders without changing terrain."""
from . import geometry as g
from .activate_backlands_subset import MaskIndex,ActualNative,SCENE
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import Counter
import math,time

OUT=g.HERE/'backland_completion_r01/residual_land_use_r01'
INTENT={
 ('BLOCK_003','0003'):('SITE_CASTLE','castle_fuel_and_service_edge','ground_earth','Keep the narrow castle service margin open beside the existing fuel yard. Preserve the separate 12 m and 24 m terraces and their retaining edge.'),
 ('BLOCK_003','0004'):('SITE_CASTLE:TRAIN','training_ground_outer_clearance','ground_grass','Attach the level pockets to the existing training ground as unobstructed practice and maintenance clearance. Retain the steep castle hill and curtain-wall edge as nonwalking defensive slope.'),
 ('BLOCK_003','0008'):('E4','stable_service_and_turnout_margin','ground_earth','Use the existing terrace margin beside the stable for turnout and service clearance, preserving the castle approach and every existing retaining edge.'),
 ('BLOCK_003','0010'):('E7','estate_kitchen_fuel_garden_margin','ground_grass','Assign the separated existing terrace pockets to the adjacent E7 kitchen and fuel garden. Preserve their current levels and all stable/native occupied holes.'),
 ('BLOCK_003','0021'):('SITE_MONASTERY','monastery_productive_and_service_edge','ground_grass','Continue the monastery productive grounds on their existing terraces. Keep its western service frontage, drains and nonwalking slope edges open; do not treat the long irregular strip as a public park.'),
 ('BLOCK_004','0016'):('BLOCK_004:R8_C002','craft_service_margin','ground_earth','Attach usable remnants to the adjacent craft holding; existing retired-body and future private-ground reservations retain priority.'),
 ('BLOCK_005','0025'):('UPPER_CONTOUR:BLOCK_005:ALLEY','junction_service_shoulder','ground_earth','Keep the alley/upper-contour junction margin unobstructed for visibility and road maintenance.'),
 ('BLOCK_005','0068'):('EAST_WALL_SERVICE','wall_and_mill_approach_service_margin','ground_earth','Preserve the narrow eastern service margin and the mill approach. No storage or boundary panels are proposed here.'),
 ('BLOCK_005','0071'):('EAST_WALL_SERVICE:POOR_NORTH_CROSS','mill_and_canal_service_margin','ground_earth','Keep the dry wall-service and north-crossing margin clear beside the existing mill and dense poor district.'),
 ('BLOCK_005','0093'):('FORT_CURTAIN_15','curtain_wall_inspection_margin','ground_grass','Reserve the narrow wall-side ground for inspection and drainage while retaining the adjacent productive garden boundaries.'),
 ('BLOCK_005','0148'):('B_REG_0474','household_fuel_and_work_margin','ground_earth','Attach the small existing-level remnant to the retained household work and fuel yard, keeping the south service road clear.'),
 ('BLOCK_010','0003'):('BLOCK_010:R8_C002','craft_frontage_service_margin','ground_earth','Attach the usable edge to the adjoining craft frontage; preserve the old native support holes and pending replacements.'),
 ('BLOCK_011','0042'):('CENTRAL_WEST_RADIAL','junction_drainage_and_service_shoulder','ground_earth','Keep the radial/contour corner open for drainage, visibility and maintenance beside the retained household gardens.'),
 ('BLOCK_015','0009'):('DENS_B13_GROUP_003','shared_domestic_service_margin','ground_earth','Complete the small shared domestic service edge beside the retained dense B13 roofs and south crossing, with no additional buildings.'),
 ('BLOCK_015','0012'):('BLOCK_015:R8_D019','shared_domestic_workyard_margin','ground_earth','Attach the remnant outside the existing boundary to the named domestic holding as a shared open work margin; retain its public contour frontage.'),
 ('BLOCK_015','0153'):('BLOCK_015:R8_D015','shared_alley_work_and_drainage_margin','ground_earth','Keep the alley-side domestic work/drainage strip open and subordinate to the sealed B15 access and boundary geometry.'),
}

def area(ps):return sum(g.geo.polygon_area(p)for p in ps)
def run():
 start=time.monotonic();OUT.mkdir(exist_ok=True);ledger=g.HERE/'city_completion_ledger_r02/completion_ledger.json';rows=g.load(ledger)['meaningful_unallocated_regions'];assert len(rows)==16 and sum(r['area_m2']for r in rows)==3859
 scene=g.load(SCENE);index=a.TriangleIndex(scene,[p for r in rows for p in r['polygon_parts_xz_m']]);native=ActualNative(scene)
 rp=g.HERE/'backland_completion_r01/phase02_ownership_correction_r01/reservation_snapshot.json';masks=list(g.load(rp)['reservations']);refs=[g.ref(rp)];plan=g.load(g.CITY/'registered_source/plan.json')
 for r in plan['spaces']+plan['plots']:
  for p in g.triangulate(r['polygon_xz_m']):masks.append(dict(id=r['id'],kind='RETAINED_SPECIAL_OWNER',polygon_xz_m=p))
 for sub in ['contour_bulk_r01','coherent_batch18_r01','coherent_batch20_r01']:
  path=g.CITY/'registered_topography/revisions/r17_district_batches'/sub/'physical_owner_handoff_r02.json';q=g.load(path);refs.append(g.ref(path));masks +=[dict(id=r['id'],kind='PRIVATE_PHYSICAL_EARTH',polygon_xz_m=r['polygon_xz_m'])for r in q['physical_earth_owners']]
 nextpath=g.HERE/'next20_source_addendum_r01/atomic_source_addendum.json';refs.append(g.ref(nextpath))
 for r in g.load(nextpath)['records']:
  h=r['replacement_holding'];masks +=[dict(id=h['id'],kind='NEXT20_PRIVATE_RESERVATION',polygon_xz_m=p)for p in [h['holding_polygon_xz_m']]+h['external_route_polygons_xz_m']]
 for path in [g.HERE/'b07_terrace_refit_r02/BLOCK_007/selected_layout.json',g.HERE/'coherent_regrade_r01/BLOCK_015/selected_layout.json']:
  refs.append(g.ref(path))
  for h in g.load(path)['holdings']:masks +=[dict(id=h['id'],kind='B07_OR_B15_HOLDING_AND_ENTRY',polygon_xz_m=p)for p in [h['holding_polygon_xz_m']]+h['external_route_polygons_xz_m']]
 np=g.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r01/resolved_placements.json';refs.append(g.ref(np));noble=g.load(np)
 masks +=[dict(id=r['native_id'],kind='NEW_NOBLE_NATIVE_BEARING',polygon_xz_m=r['polygon_xz_m'])for r in noble['actual_bearing_footprints']]
 precinct=g.CITY/'assemblies/landmarks/registered/precinct_r06_whole'
 for pp in [precinct/'resolved_connected_placements.json',precinct/'residual_completion_r01/resolved_residual_placements.json',precinct/'residual_completion_r01/residual_extensions_r02/resolved_extension_placements.json']:
  refs.append(g.ref(pp));pk=g.load(pp)
  for h in pk['holdings']:
   polys=h.get('polygon_parts_xz_m',h.get('polygons_xz_m',[h['polygon_xz_m']]if 'polygon_xz_m'in h else[]))
   masks +=[dict(id=h['id'],kind='RETAINED_PRECIINCT_FUNCTIONAL_GROUND',polygon_xz_m=p)for p in polys]
  masks +=[dict(id=r.get('native_id',r['id']),kind='RETAINED_PRECINCT_NATIVE_BEARING',polygon_xz_m=r['polygon_xz_m'])for r in pk['actual_bearing_footprints']]
  for r in pk['internal_routes']+pk['external_routes']:
   masks +=[dict(id=r.get('id',r.get('holding_id','precinct_access')),kind='RETAINED_PRECINCT_ACCESS',polygon_xz_m=p)for p in r.get('polygon_parts_xz_m',r.get('polygons_xz_m',r.get('ribbon_polygons_xz_m',[])))]
 # Existing source ownership and route reservations are semantic priority,
 # irrespective of whether an overlapping source proposal is activated yet.
 # One cached full-solid projection is a deliberately conservative native
 # clearance reservation. Avoid re-extracting thousands of differently sliced
 # copies of a precinct master merely to classify same-plane open ground.
 native_rows=[];native_candidates={j for r in rows for p in r['polygon_parts_xz_m']for j in native.index.candidates(p)};projections={}
 for j in sorted(native_candidates):
  nr=native.rows[j]
  if nr.get('box'):polys=[nr['polygon_xz_m']]
  else:
   ass=nr['asset'];key=ass['render_sha256']
   if key not in native.cache:native.cache[key]=g.load(g.ROOT/ass['render_path'])
   if key not in projections:projections[key]=slab_rectangles(native.cache[key],ass['bounds']['min'][1],ass['bounds']['max'][1])
   polys=[transform(q,nr['placement'])for q in projections[key]]
  native_rows +=[dict(id=nr['id'],kind='RETAINED_NATIVE_CLEARANCE',polygon_xz_m=p)for p in polys]
 nmi=MaskIndex(native_rows);mi=MaskIndex(masks);result=[];functions=Counter();statusarea=Counter()
 for r in rows:
  owner,use,material,reason=INTENT[(r['block_id'],r['id'].split(':')[-1])];reserved=[];free=[]
  for p in r['polygon_parts_xz_m']:
   remaining=[p]
   for j in sorted(mi.index.candidates(p)):
    if not remaining:break
    m=masks[j];left=[]
    for t in remaining:
     q=a.clip(t,m['polygon_xz_m'])
     if not q or g.geo.polygon_area(q)<=1e-8:left.append(t);continue
     reserved.append(dict(owner_id=m['id'],kind=m['kind'],polygon_xz_m=q));left+=a.common.subtract([t],[m['polygon_xz_m']])
    remaining=left
   free+=remaining
  pieces=[];gaps=[];occupied=[];steep=[]
  for p in free:
   query=a.audit_polygon(index,p,None,grade_limit=math.inf);covered=[]
   for s in query['source_pieces']:
    q=s['polygon_xz_m'];covered.append(q);hits=nmi.hit([q]);cuts=[]
    for hit in hits:
     unique=a.common.subtract([hit['polygon_xz_m']],cuts);occupied +=[dict(native_id=hit['id'],polygon_xz_m=t)for t in unique];cuts+=unique
    for t in a.common.subtract([q],cuts):
     grad=math.hypot(*s['plane_y_xz_m'][:2]);entry=dict(s,polygon_xz_m=t,area_m2=g.geo.polygon_area(t),named_function_owner=owner,planned_function=use,proposed_material=material,height_action='PRESERVE_EXISTING_ACTUAL_SOURCE_PLANE',new_walkability_claim=False)
     if grad>.12+1e-7:entry.update(planned_function='nonwalking_slope_and_drainage_edge',proposed_material='PRESERVE_EXISTING_MATERIAL');steep.append(entry)
     else:pieces.append(entry)
   gaps+=a.common.subtract([p],covered)
  declared=area(r['polygon_parts_xz_m']);parts=area([q['polygon_xz_m']for q in reserved])+area([q['polygon_xz_m']for q in occupied])+area([q['polygon_xz_m']for q in pieces+steep])+area(gaps);error=abs(declared-parts)
  row=dict(id=r['id'].replace('UNALLOCATED_REVIEW','RESIDUAL_LAND_USE'),supersedes_unassigned_id=r['id'],block_id=r['block_id'],named_function_owner=owner,planned_function=use,design_reason=reason,source_domain_polygons_xz_m=r['polygon_parts_xz_m'],source_area_m2=declared,retained_reservation_regions=reserved,retained_native_clearance_regions=occupied,same_plane_functional_ground=pieces,nonwalking_slope_regions=steep,existing_missing_top_regions_xz_m=gaps,existing_missing_top_policy='Preserve native/support holes and current source gaps. No fill, new walkability or ground activation is claimed; joint terrain ownership review remains required for any restoration.',access_policy='Use the adjacent existing named holding or service frontage only. This designation does not add a new through-route or claim continuous access across different existing terraces.',boundary_policy='Intentionally open functional margin. No analytic fragment fencing; existing complete owner enclosures and gates remain authoritative.',implementation_tier='exterior_only',new_native_instances=0,new_terrain_geometry=0,area_partition_error_m2=error,design_assignment_complete=True,physical_activation_status='FINITE_SAME_PLANE_SOURCE_PLAN_PENDING_PARENT_COMPOSITION',summary=dict(reserved_existing_owner_area_m2=area([q['polygon_xz_m']for q in reserved]),retained_native_clearance_area_m2=area([q['polygon_xz_m']for q in occupied]),functional_ground_area_m2=area([q['polygon_xz_m']for q in pieces]),nonwalking_slope_area_m2=area([q['polygon_xz_m']for q in steep]),existing_missing_top_area_m2=area(gaps)))
  assert error<1e-5,(r['id'],error);result.append(row);functions[use]+=row['summary']['functional_ground_area_m2'];statusarea.update(row['summary']);print(r['id'],row['summary'],flush=True)
 report=dict(schema='riverstone.ordinary_residual.finite_land_use_plan.v1',status='ALL_SIXTEEN_MEANINGFUL_SOURCE_REMAINDERS_ASSIGNED_NO_SCENE_ACTIVATION',source_ledger=g.ref(ledger),actual_source_scene=g.ref(SCENE),source_plan=g.ref(g.CITY/'registered_source/plan.json'),reservation_sources=refs,author=g.ref(__file__),regions=result,summary=dict(assigned_connected_components=16,assigned_source_area_m2=3859,remaining_unlabelled_components_at_least_25_m2=0,disposition_area_m2=dict(statusarea),functional_use_area_m2=dict(functions),new_native_instances=0,new_compilations=0,new_terrain_geometry=0,maximum_area_partition_error_m2=max(r['area_partition_error_m2']for r in result),seconds=time.monotonic()-start),limits=['This closes the finite source design assignment, not pending building, access, support or runtime gates.','All current exact reservations retain priority; no native, public, special-owner or future court domain is reassigned.','Existing source gaps are finite and explicit. No blanket pad, additional roof, clutter or disconnected fence is introduced.']);g.write(OUT/'source_plan.json',report)
 lines=['# Final sixteen residual land-use assignments','',f"All 16 source patches (3,859 m²) now have a named adjacent function. Existing reservations, native clearance, slopes and support holes remain explicitly partitioned. This is a source design plan; terrain composition and access acceptance remain separate.",'']
 for r in result:
  s=r['summary'];lines +=[f"## {r['id']}",f"Owner: {r['named_function_owner']}. Use: {r['planned_function'].replace('_',' ')}.",r['design_reason'],f"Source area {r['source_area_m2']:.1f} m²: {s['functional_ground_area_m2']:.2f} m² existing-plane functional ground; {s['reserved_existing_owner_area_m2']:.2f} m² prior reservations; {s['retained_native_clearance_area_m2']:.2f} m² native clearance; {s['nonwalking_slope_area_m2']:.2f} m² nonwalking slope; {s['existing_missing_top_area_m2']:.2f} m² existing source holes/gaps. Intentionally open margin; no new enclosure or objects.",'']
 (OUT/'assignments.md').write_text('\n'.join(lines)+'\n');g.write(OUT/'manifest.json',dict(plan=g.ref(OUT/'source_plan.json'),readable=g.ref(OUT/'assignments.md'),summary=report['summary']));print(report['summary']);print(g.ref(OUT/'source_plan.json'))
if __name__=='__main__':run()
