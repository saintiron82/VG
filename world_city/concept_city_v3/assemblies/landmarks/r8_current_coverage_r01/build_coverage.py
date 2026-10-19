"""Read-only exact R04 facility audit. No inventory, source, cache or scene mutation."""
import collections,fnmatch,hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir()); D=ROOT/'world_city/concept_city_v3'
SCENE=D/'evidence/r8_district_r04/scene.json'; INVENTORY=D/'assemblies/landmarks/implementation_coverage.json'
EXPECTED='3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def read(p):return json.loads(p.read_bytes())
def write(name,d):
 with (H/name).open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def digest(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def paths(rows):
 out=[]
 for row in rows:
  if not row.get('path'):continue
  p=ROOT/row['path'];out.append(dict(path=row['path'],historical_sha256=row.get('sha256'),exists=p.is_file(),current_sha256=sha(p)if p.is_file()else None,historical_hash_matches=(sha(p)==row.get('sha256'))if p.is_file()and row.get('sha256')else None))
 return out
# Each explicit rule records its bounded implementation and omissions. Related rows overlap.
RULES={}
def rule(ids,patterns=(),note='',omissions=(),status='partial_exterior',surfaces=(),water=(),components=(),movable=()):
 for rid in ids.split('|'):RULES[rid]=dict(patterns=list(patterns),implemented=note,omissions=list(omissions),status=status,surfaces=list(surfaces),water=list(water),components=list(components),movable=list(movable))
rule('timber_dock|loading_platform|timber_dock_piles_bents',['PORT_PIER_*','PORT_BENT_*'],'Three native loading piers with 21 dock bents.', ['All-tide access, structural loads and working cargo animation are unproved.'],status='exterior_present')
rule('bridge_deck|waterworks/complete_bridge_assembly',['BRIDGE_MAIN_RIVER:*','REGISTERED_WATER_CROSSING:*'],'Actual fixed main bridge/causeway, explicit moving leaf poses and four native canal crossings.', ['Final joint public network replay is pending; moving traffic simulation is outside this audit.'],movable=['timber_lift_leaf_7x14','sliding_hinge_cover'])
rule('bridge_pier',['BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED','REGISTERED_WATER_CROSSING:*'],'Compiled fixed bridge masonry and canal-crossing abutments/bearings.', ['Scour, load capacity and flood engineering are unproved.'])
rule('city_curtain_wall|city_battlements',['FORT_CURTAIN_*'],'Actual perimeter curtain modules, closures and sampled battlement tops.', ['Wall-walk connectivity and detailed guard access are unproved.'],status='exterior_present')
rule('street_paving',note='Actual road and alley triangle surfaces are present.',surfaces=['road','alley'],omissions=['R04 predates canonical R18 activation; presence does not certify whole-road traversal.'])
rule('plaza_surface',patterns=['MARKET_FOUNTAIN'],note='Actual civic/market surface and native fountain anchor.',surfaces=['space_civic'],omissions=['Fountain circulation and all loading routes are unproved.'])
rule('cathedral_nave_transept',['cathedral_registered:nave_aisles_transept'],'Actual native nave, aisles and transept.', ['Interiors, detailed tracery and full precinct traversal are unproved.'],status='exterior_present')
rule('cathedral_twin_steeples',['cathedral_registered:single_bell_tower','cathedral_registered:single_bell_tower_footing'],'Registered cathedral uses its approved single bell tower variant.', ['The old twin-steeple inventory label is superseded by the actual registered single-tower source; no twin towers are claimed.'],status='superseded_requirement')
rule('cathedral_existing_buttresses',['cathedral_registered:nave_aisles_transept'],'Native cathedral master includes explicit buttresses component.', ['Fine connection and decorative details are unfinished.'],components=['buttresses'])
rule('castle_keep_courtyard',['castle_registered:*residence','castle_registered:*wing','castle_registered:court'],'Castle residence wings and court are actually placed.', ['Occupied interiors and every door route are unproved.'],status='exterior_present')
rule('castle_curtain_towers',['castle_registered:*tower','castle_registered:*curtain'],'Castle curtain and four named tower bodies are placed.', ['Guard circulation, gates and interior rooms remain outside this audit.'],status='exterior_present')
rule('perimeter_wall_towers',['FORT_TOWER:*'],'Six perimeter tower bodies and their native footing instances.', ['Interior stairs, combat and wall-walk access are unproved.'],status='exterior_present')
rule('gatehouses|perimeter_gate_assemblies',['FORT_GATE:*','FORT_TOWER:main_gate*'],'Main and reservoir-service gate headers with native flanking structures.', ['Moving defensive door/portcullis and full guard circulation are unfinished.'])
rule('warehouse_buildings',['PORT_SHED_*'],'Six actual long loading sheds at the harbor.', ['Warehouse interiors, stock system and hoists are not established.'],status='exterior_present')
rule('civic_hall',['civic_registered:*'],'Actual civic market hall, tower and tower footing.', ['Interior civic program and grain-specific operation are unproved.'],status='exterior_present')
rule('monastery_hospital',['monastery_registered:*','ABBEY_NORTH_WORK'],'Monastic church/ranges/refectory and explicit infirmary components within ABBEY_NORTH_WORK.', ['This supports an abbey infirmary exterior, not a separately certified hospital or usable medical interior.'])
rule('market_stall_family',['MARKET_stall_*'],'104 actual cloth/timber stall instances.', ['Goods microdetail and trading behavior remain unfinished.'],status='exterior_present')
rule('workyard_bench',['B13_YARD_*','BANK_DRY_WORK_COURT:SHARED_WORKBENCH','BLOCK_015:*COURT*'],'Actual workbench/craft-yard components; exact selected bench assets are filtered below.', ['Craft operation and props inside buildings are unbuilt.'])
rule('timber_cargo_stack',['B13_YARD_*','BANK_DRY_WORK_COURT:TIMBER_RACK_AND_STORE','*:fuel_stack:*'],'Actual timber stacks, dry rack/store and precinct fuel stacks.', ['Working cargo handling is unbuilt.'])
rule('garden_beds_orchards|park_and_garden_recipe_families',['E*:registered:garden_bed_*','E*:registered:orchard_tree_*','*:compact_bed:*','CLERGY_*ORCHARD','CLERGY_SOUTH_ALLOTMENT','ABBEY_*HERBS','ABBEY_*NURSERY','ABBEY_*ORCHARD','B13_YARD_*'],'Actual estate gardens/orchards, native productive precinct beds and bounded extensions.', ['Some retained abbey garden thresholds and final public continuation remain unresolved; no automatic all-owner completion.'])
rule('park_grove_trees',['WOOD_REGISTERED_*','CLERGY_CLOISTER_GARDEN:*','E*:registered:orchard_tree_*'],'Actual grove trees, understory, cypresses and orchard trees.', ['Species/detail art pass and all path interfaces remain unfinished.'],status='exterior_present')
rule('grave_markers',['CLERGY_CEMETERY:burial_row_*'],'Nine native four-grave row assets are placed.', ['Cemetery obsolete-cap repair is upcoming source; R04 presence does not prove final cemetery access.'],status='exterior_present')
rule('property_walls',['E*:registered_r1:infrastructure','SITE_*:LOW_BOUNDARY_BELT','*:native_boundary','*:boundary_*','BLOCK_015:*BOUNDARY*','MARKET_SHARED_WORK_COURT:DOMESTIC_BOUNDARY','BANK_DRY_WORK_COURT:WORK_BOUNDARY'],'Actual estate/precinct/ordinary boundary assemblies.', ['Seven noble entry replacements are sealed sources for the next scene and are not activated here.'])
rule('market_fountain',['MARKET_FOUNTAIN'],'Actual masonry fountain and retained static water-colored native cells.', ['Supply graph head is an inlet association; upper-bowl pumping/manual filling and fluid circulation are unbuilt.'],status='exterior_present')
rule('varied_roof_forms',note='Actual native masters include dimension-authored roof variants.',omissions=['Dormer family and roof microdetail are not established.'],components=['roof'])
rule('chimneys',note='Actual masters include explicit chimney components and compiled cells.',omissions=['Smoke/fire simulation and interior hearth connections are unbuilt.'],components=['chimney'])
rule('shopfronts',note='Actual ordinary/merchant masters include explicit shop or canopy components.',omissions=['Signs, display variants, interiors and shop operation are unfinished.'],components=['shop','canopy'])
rule('attached_housing_manors',['DENS_*','M_BATCH_*','M11_SHOP_COURT:*','MF02_*','BLOCK_015:*ATTACHED_FABRIC*','E*:registered:main'],'Actual attached native rows, merchant courts, B15 fabric and seven estate houses.', ['Other upcoming regraded holding batches and usable interiors are not part of R04.'],status='exterior_present')
rule('quay_retaining_segment|port_land_apron_quay_foundations',['PORT_QUAY_RUN_*','PORT_PIER_*','PORT_BENT_*'],'Four actual quay runs and adjoining native piers/bents; port terrain retained.', ['Basin loading ground stays open; flood capacity and all access routes are unproved.'],surfaces=['land_D_PORT'])
rule('timber_harbor_crane',['PORT_MAIN_CRANE'],'Actual braced timber harbor crane.', ['Hoisting animation, load limits and cargo interaction are unbuilt.'],status='exterior_present')
rule('river_cargo_barge|sailing_river_boat_family',['PORT_BARGE_*','PORT_RIGGED_BARGE'],'Three moored cargo barges and one static rigged barge.', ['Buoyancy, sailing, boarding and moving navigation are unbuilt.'],status='exterior_present')
rule('cathedral_flying_buttress',['cathedral_registered:flying_*'],'Six actual native flying buttresses.', ['Decorative connection refinement remains.'],status='exterior_present')
rule('pointed_arch_cloister_bay|cathedral_partial_cloister',['cathedral_registered:*cloister*','monastery_registered:*arcade*'],'Actual cathedral cloister ranges/walk bays and monastery arcade bays.', ['Corner/portal traversal and complete interior-cloister circulation are unproved.'])
rule('park_terrace_stair',['PHASE02:real_neighborhood_stair:0'],'A native two-flight neighborhood stair is placed as a related terrace-access assembly.', ['The standalone park_terrace_stair catalog master has no exact R04 placement; park-specific endpoint/runtime review remains.'])
rule('retaining_wall_corner|terrace_retaining_structure_assemblies',['PHASE02:terrain_aligned_boundary_retaining:*','ABBEY_FINITE_BEARING_SUPPORT','MERCHANT_FINITE_BEARING_SUPPORT','*:RETAINED_EDGE_GUARD'],'Finite native retaining/bearing and boundary assemblies are present.', ['No citywide structural certification or automatic slope acceptance.'],surfaces=['bank'])
rule('park_bench',['PUBLIC_TERRACE_PARK:*bench*','*:park_bench:*'],'Thirteen actual park/precinct bench instances.', ['Microdetail remains.'],status='exterior_present')
rule('cargo_crate',['*:cargo_crate:*'],'Six actual precinct cargo-crate instances.', ['Cargo behavior and harbor-specific unloading details are unfinished.'],status='exterior_present')
rule('cargo_barrel',['MARKET_SHARED_WORK_COURT:DOMESTIC_WASH_BARREL'],'A domestic wash-barrel instance is actual related geometry.', ['It is not evidence of the separate cargo-barrel family; that catalog source remains unplaced.'])
rule('harbor_floodwall_and_water_stairs',['PORT_QUAY_RUN_*'],'Actual quay retaining edges provide partial physical waterfront boundary.', ['Dedicated water stairs, flood datum and flood-engineered retaining system are missing.'])
rule('full_cloister_corners_and_court',['cathedral_registered:*cloister*','monastery_registered:*arcade*','ABBEY_CLOISTER_HERBS','CLERGY_CLOISTER_GARDEN:*'],'Actual ranges/arcades and planted cloister components provide partial court geometry.', ['Complete corner detail, drainage and verified oriented portal continuation are unresolved.'])
rule('cathedral_tracery_and_roof_detail',['cathedral_registered:nave_aisles_transept','cathedral_registered:single_bell_tower'],'Cathedral has roof/window silhouette components.', ['Fine tracery, gargoyles, drainage and roof microdetail remain incomplete.'])
rule('grain_hall',['civic_registered:north_market_hall'],'Actual north market hall is related civic/hall geometry.', ['A distinct grain-hall program and unloading/storage interior are not established; civic_grain remains a catalog adaptation.'])
rule('shop_awning_sign_and_display',note='Some actual native masters contain shop canopy components.',omissions=['Dedicated sign and display variants remain missing.'],components=['shop_canopy'])
rule('park_paths_edges_vegetation_variants',['WOOD_REGISTERED_*','PUBLIC_TERRACE_PARK:*','*:field_edge_*'],'Actual vegetation, park benches and bounded field edges.', ['No final landscape species, path-edge detail or whole-park traversal approval.'],surfaces=['ground_grass'])
rule('neighborhood_terrace_assemblies',['PHASE02:real_neighborhood_stair:0','PHASE02:terrain_aligned_boundary_retaining:*','R06_COMMON_R02:*','TRAIN:r09:*'],'Actual finite neighborhood stair/retaining and common/training access assemblies.', ['The remaining common reverse case needs canonical public field; cart alternatives and other terraces remain bounded source work.'])
rule('defensive_doors_portcullis_access',['FORT_GATE:*'],'Gate apertures/headers exist; bridge road barriers have explicit scene poses.', ['Defensive city-gate doors, portcullis motion and guard-wall access are not established.'],movable=['timber_road_barrier_half'])
rule('craft_equipment_and_mills',['REGISTERED_MILL:EAST_CANAL','B13_YARD_*','BANK_DRY_WORK_COURT:*'],'Actual small canal mill and bounded craft benches/drying/timber storage.', ['Gearing, process power, furnaces, effects and craft operation remain unbuilt.'])
rule('water_source_intake_headworks|waterworks/spring_intake',['RESERVOIR_SPRING_INTAKE'],'Actual graded spring intake at the registered spring mouth.', ['Spring yield, water quality and discharge simulation are unbuilt.'],status='exterior_present')
rule('water_reservoir_settling_pond|waterworks/reservoir_complete_shell',['RESERVOIR_BED','RESERVOIR_BANKS','RESERVOIR_OVERFLOW_SLUICE','RESERVOIR_SPRING_INTAKE'],'Native six-sided reservoir bed/perimeter with declared intake, overflow and supply openings.', ['Settling baffles, sediment operation and hydraulic capacity are not implemented.'],water=['NORTHERN_RESERVOIR'])
rule('water_clean_cistern|water_well_drawpoint|waterworks/covered_wellhouse|waterworks/covered_cistern',['RESERVOIR_DRAWPOINT','REGISTERED_SERVICES:*'],'Actual reservoir draw structure and three closed-bottom manual-draw storage fixtures.', ['Buried supply branches, manual filling/lift operation and water-quality simulation are unbuilt. Castle floor Y24 / stored head Y22 is independent manually raised/local storage, not gravity-fed from reservoir Y15.5.'])
rule('water_covered_clean_conduit|waterworks/covered_clean_conduit',['RESERVOIR_PROTECTED_CONDUIT'],'A native protected bank conduit exists at the reservoir.', ['Long cathedral, market and monastery distribution branches remain graph-only, not rendered buried pipes.'])
rule('water_millrace|waterworks/service_channel_segment|waterworks/channel_bends_transitions',['REGISTERED_MILL:EAST_CANAL'],'Actual process-canal water, bed/banks and local mill bank interface.', ['No separately controlled headrace/tailrace, discharge or torque simulation. A retained craft/east join has a 15.137 mm source water-head step.'],water=['CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE','NORTHERN_CHANNEL_VISIBLE'])
rule('water_sluice|waterworks/sluice_bay|waterworks/reservoir_overflow_spillway',['RESERVOIR_OVERFLOW_SLUICE'],'Actual reservoir overflow sluice fixture and visible downstream channel.', ['Gate operation, spill capacity, bypass and flood routing are unbuilt.'],water=['NORTHERN_CHANNEL_VISIBLE'])
rule('water_outfall|waterworks/drain_outfall',note='Registered industrial canal water reaches the receiving river through retained actual outfall triangles.',water=['EAST_CHANNEL_VISIBLE','MAIN_RIVER'],omissions=['This is the process outfall, not a complete storm-drain collection network.'])
rule('water_canal_footbridge|waterworks/canal_footbridge',['RESERVOIR_SERVICE_CIRCUIT_RECOVERY','REGISTERED_WATER_CROSSING:*'],'Native reservoir maintenance crossings and four full-width canal road decks.', ['Final canonical public approach field is upcoming; local R04 deck replay passed.'])
rule('water_protective_edge|waterworks/reservoir_lining_segment',['RESERVOIR_BANKS','RESERVOIR_BED','RESERVOIR_SERVICE_CIRCUIT_RECOVERY','REGISTERED_WATER_CROSSING:*'],'Native reservoir lining, maintenance edges and canal deck guards.', ['No universal waterside guard coverage or flood engineering claim.'])
rule('military_training_ground',['TRAIN:*','FIELD_SITE_TRAIN_*'],'Actual barrack structures, targets, racks, troughs, training surface and fine access.', ['Training behavior, armory interiors and full public continuation are unproved.'],surfaces=['land_D_TRAIN'])
rule('logistics_market_container',['MARKET_stall_*','MARKET_FOUNTAIN','civic_registered:north_market_hall'],'Actual coordinated market stall/civic hall/fountain group.', ['Carts, unloading scheduling, grain storage interior and complete logistics simulation are unfinished.'],surfaces=['space_civic'])
rule('large_noble_compound_container|property_compound_and_service_families',['E*:registered:*','E*:registered_r1:infrastructure'],'Seven actual estate houses with stables, servants, garden/orchard and infrastructure families.', ['Seven replacement noble entry envelopes are source-ready for the next scene; R04 all-estate public traversal is not certified.'])
rule('service_housing_container',['CLERGY_CANONS_CLOSE','CLERGY_SCHOOL_SERVICE','CLERGY_GUEST_ALMS','ABBEY_*SERVICE','ABBEY_NORTH_WORK','E*:registered:servants'],'Actual clergy/abbey and estate service ranges.', ['Interior occupancy and all individual entry routes remain unproved.'])
rule('poorer_row_quarter_container',['DENS_B13_*','DENS_B15E_*','BLOCK_015:*ATTACHED_FABRIC*'],'Actual dense attached-row groups and sealed B15 exterior fabric.', ['Other regraded holding batches are upcoming; public continuity outside the tested B15 subset is not assumed.'])
rule('waterworks/undershot_mill_wheel|waterworks/mill_bank_interface|waterworks/millhouse_gearing_race_control',['REGISTERED_MILL:EAST_CANAL'],'Actual static wheel, bank support, drive wall, bearings and millhouse shell.', ['Internal gearing, flow control, wheel rotation, hydraulic power and usable interior are not implemented.'])
rule('waterworks/stair_endpoint_assemblies|waterworks/retaining_stair_landing',['RESERVOIR_SERVICE_CIRCUIT_RECOVERY','R06_COMMON_R02:fine_access','TRAIN:r09:fine'],'Actual native finite service/common/training access assemblies provide related endpoints.', ['The generic waterworks stair module has no direct R04 placement. These are not certified water stairs or all-city grade solutions.'])
rule('castle_stables',['castle_registered:stable','castle_registered:stable_floor'],'Actual castle stable and floor.', ['Stable interior operation and animal behavior remain unbuilt.'],status='exterior_present')
rule('monastery_cloister_garden_enclosure',['monastery_registered:*arcade*','ABBEY_CLOISTER_HERBS','ABBEY_WEST_NURSERY','ABBEY_EAST_ORCHARD','SITE_MONASTERY:LOW_BOUNDARY_BELT'],'Actual monastery arcade/garden and low-boundary assemblies.', ['Two retained abbey garden thresholds and complete cloister portal continuation remain unresolved.'])
rule('castle_actual_primary_access',note='Retained actual castle approach road geometry exists.',surfaces=['road','land_D_CASTLE'],omissions=['Generic surface presence alone is not proof of the named castle primary route. Final exact-scene route catalog/replay remains pending.'])
rule('cathedral_service_lodge_addon',['CLERGY_GUEST_ALMS','CLERGY_CANONS_CLOSE','CLERGY_SCHOOL_SERVICE'],'Actual registered service/guest/school compounds fulfill related exterior uses.', ['The older exact cathedral_service_lodge addon source is not an R04 asset; no automatic source equivalence or interior access claim.'])
# Strict missing/source-only rows are intentionally not mapped to nearby generic objects.

def main():
 assert sha(SCENE)==EXPECTED
 original=ref(INVENTORY);scene=read(SCENE);inventory=read(INVENTORY);inst=scene['common_instances'];assets=scene['common_assets'];byid={r['id']:r for r in inst};assert len(byid)==len(inst)
 dependencies={str(SCENE.relative_to(ROOT)):EXPECTED,str(INVENTORY.relative_to(ROOT)):original['sha256']};errors=[];assetrows={};masters={}
 for key,a in assets.items():
  src=ROOT/a['master_path'];cache=ROOT/a['render_path'];sr=ref(src);cr=ref(cache)
  if sr['sha256']!=a['master_sha256']or cr['sha256']!=a['render_sha256']:errors.append(key)
  dependencies[sr['path']]=sr['sha256'];dependencies[cr['path']]=cr['sha256'];m=read(src);c=read(cache);masters[key]=m
  assetrows[key]=dict(source=sr,cache=cr,source_master_id=m.get('id'),cache_source_id=c.get('source_id'),cache_master_hash=c.get('master_hash'),compiled_quad_count=sum(len(g['quads'])for g in c['groups']),compiled_cell_count=c.get('cell_count'),component_ids=[r['id']for r in m.get('components',[])],operation_features=sorted({str(o['feature'])for co in m.get('components',[])for o in co.get('operations',[])if'feature'in o}),actual_instance_ids=[r['id']for r in inst if r['asset_key']==key],scene_asset_record=a)
 assert not errors,errors
 surf={k:dict(scene_json_pointer='/surfaces/'+k,vertices=len(v),triangles=len(v)//3,value_sha256=digest(v))for k,v in scene['surfaces'].items()}
 bridge=scene['bridge_mechanism'];state_rows={state:[dict(r,scene_json_pointer='/bridge_mechanism/states/'+state+'/movable_placements/'+str(i))for i,r in enumerate(v['movable_placements'])]for state,v in bridge['states'].items()}
 registry=dict(schema='riverstone.r8.actual_facility_registry.v1',scene=ref(SCENE),instances=inst,assets=assetrows,surfaces=surf,bridge_to_world=bridge['bridge_to_world'],bridge_state_placements=state_rows,bridge_chain_assets=sorted({r['native_link_key']for v in bridge['states'].values()for r in v.get('chains',[])}),limits=['Bridge state records describe alternative poses of the same mechanism, not additional simultaneous physical structures.'])
 write('actual_registry.json',registry)
 # Rebind inherited water triangles/bed evidence by exact values, not obsolete indices.
 wp=D/'assemblies/waterworks/registered_water_completion_r01';audit=read(wp/'actual_geometry_audit.json');old=read(D/'evidence/visual_registered_common_r7_palette_r01/scene.json');wmap=collections.defaultdict(list);bmap=collections.defaultdict(list)
 for i in range(0,len(scene['surfaces']['water']),3):wmap[tuple(tuple(v)for v in scene['surfaces']['water'][i:i+3])].append(i//3)
 for i in range(0,len(scene['surfaces']['bank']),3):bmap[tuple(tuple(v)for v in scene['surfaces']['bank'][i:i+3])].append(i//3)
 water=[]
 for row in audit['water_triangles']:
  i=row['water_triangle_index'];tri=old['surfaces']['water'][i*3:i*3+3];actual=wmap[tuple(tuple(v)for v in tri)];beds=[]
  for bed in row['bed_owners']:
   if bed.get('material')=='bank'and'triangle_index'in bed:
    j=bed['triangle_index'];bt=old['surfaces']['bank'][j*3:j*3+3];beds.append(dict(previous_index=j,actual_indices=bmap[tuple(tuple(v)for v in bt)]))
   elif 'instance_id'in bed:beds.append(dict(instance_id=bed['instance_id'],present=bed['instance_id']in byid,asset_key=bed.get('asset_key')))
  water.append(dict(previous_triangle_index=i,actual_triangle_indices=actual,domains=row['domains'],bed_bindings=beds,all_exact_bed_sources_present=all(bool(r.get('actual_indices',r.get('present',False)))for r in beds)))
 wb=dict(schema='riverstone.r8.retained_water_source_binding.v1',scene=ref(SCENE),previous_audit=ref(wp/'actual_geometry_audit.json'),rows=water,all_previous_water_triangles_present=all(r['actual_triangle_indices']for r in water),all_previous_bed_sources_present=all(r['all_exact_bed_sources_present']for r in water),limits=['Exact retained triangle/native membership transports the bounded R7 audit only; it is not a fresh fluid, flood, load or citywide containment calculation.'])
 write('retained_water_binding.json',wb)
 docs=['head_graph_and_asset_associations.json','reservoir_native_audit.json','bank_continuity.json','harbor_interfaces.json','main_bridge_interfaces.json','crossing_interfaces.json']
 source_audits=[ref(wp/x)for x in docs]
 for r in source_audits+[ref(wp/'actual_geometry_audit.json')]:dependencies[r['path']]=r['sha256']
 rows=[]
 for originalrow in inventory['entries']:
  rid=originalrow['id'];rule=RULES.get(rid);selected=[];component_matches={};mov=[];material=[];waterids=[]
  if rule:
   selected=[r['id']for r in inst if any(fnmatch.fnmatchcase(r['id'],p)for p in rule['patterns'])]
   if rid=='workyard_bench':selected=[x for x in selected if any(s in byid[x]['asset_key']for s in ['bench'])]
   if rid=='timber_cargo_stack':selected=[x for x in selected if any(s in byid[x]['asset_key']for s in ['stack','rack_store'])]
   if rid in ['garden_beds_orchards','park_and_garden_recipe_families']:selected=[x for x in selected if not x.startswith('B13_YARD')or byid[x]['asset_key']=='productive_bed']
   if rule['components']:
    for key,a in assetrows.items():
     matches=[c for c in a['component_ids']if any(token in c.lower()for token in rule['components'])]
     if matches and a['actual_instance_ids']:component_matches[key]=matches
    if not rule['patterns']:selected=sorted({x for key in component_matches for x in assetrows[key]['actual_instance_ids']})
    else:component_matches={k:v for k,v in component_matches.items()if k in{byid[x]['asset_key']for x in selected}}
   mov=[dict(state=state,id=r['id'],asset_key=r['asset_key'],json_pointer=r['scene_json_pointer'])for state,rr in state_rows.items()for r in rr if r['asset_key']in rule['movable']]
   material=rule['surfaces'];waterids=rule['water'];status=rule['status'];implemented=rule['implemented'];omissions=rule['omissions']
   assert selected or material or waterids or mov,(rid,'No actual evidence')
  else:
   status='source_only'if originalrow.get('source_present')else'missing'
   implemented='No exact active R04 placement or separately identified implemented component was established for this family.'
   omissions=originalrow.get('remaining_work',[])
  keys=sorted({byid[x]['asset_key']for x in selected}|{r['asset_key']for r in mov})
  rr=dict(id=rid,family=originalrow['family'],status=status,actual_common_asset_placed_in_r04=bool(selected or mov),native_instance_count=len(selected),native_instance_ids=selected,asset_keys=keys,geometry_cache_refs=[dict(asset_key=k,source=assetrows[k]['source'],cache=assetrows[k]['cache'])for k in keys],component_evidence=component_matches,surface_evidence=[surf[k]for k in material],water_domain_evidence=dict(binding='retained_water_binding.json',domain_ids=waterids,actual_water_triangle_indices=sorted({i for r in water if any(x['surface_id']in waterids for x in r['domains'])for i in r['actual_triangle_indices']}))if waterids else None,bridge_pose_evidence=mov,implemented_exterior=implemented,omissions=omissions,microdetail='Deferred detail/material pass; this report does not certify final art quality.',interiors='No usable interior or interactive door coverage inferred from exterior geometry.',runtime='Only separately named exact-scene replay evidence can support a runtime claim.',actual_viewed_in_this_audit=False,complete_facility_claim=False,historical_inventory_stage=originalrow['stage'],historical_source_refs=paths(originalrow.get('source_refs',[])),historical_cache_refs=paths(originalrow.get('cache_refs',[])or[]))
  rows.append(rr)
 assert len(rows)==109 and len({r['id']for r in rows})==109
 currentproof=D/'traversal_r5/revisions/r06_r8_precinct/district_services_r03/evidence/summary.json'
 upcoming=[D/'registered_topography/revisions/r17_district_batches'/x/'ready_subset_contract_r01.json'for x in ['contour_bulk_r01','coherent_batch18_r01','coherent_batch20_r01']]
 upcoming+=[D/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r01/integration_handoff.json']
 ledger=dict(schema='riverstone.r8.current_facility_coverage.v1',status='EXACT_R04_GEOMETRY_COVERAGE_NOT_WHOLE_CITY_COMPLETION',scene=ref(SCENE),frozen_original_inventory=original,actual_registry=ref(H/'actual_registry.json'),retained_water_binding=ref(H/'retained_water_binding.json'),counts=dict(required_family_rows=len(rows),common_instances=len(inst),scene_asset_records=len(assets),assets_with_common_instances=sum(bool(a['actual_instance_ids'])for a in assetrows.values()),family_status=dict(collections.Counter(r['status']for r in rows)),families_with_native_placements=sum(r['actual_common_asset_placed_in_r04']for r in rows)),entries=rows,water_source_audits=source_audits,exact_scene_runtime_evidence=ref(currentproof),runtime_scope='R04 services replay 45/46: all 24 canal-deck lanes, six connected local networks, five of six common lanes and ten negative controls pass. COMMON_FINE_ENTRY_LANE_2_REVERSE fails at old public-road lip and remains failed until joint R18 replay.',upcoming_source_only=[ref(p)for p in upcoming],upcoming_note='First61 holding batches, corrected835 yard fixtures, seven noble entry replacements and cemetery obsolete-cap repair belong to the next immutable scene. This ledger does not activate them or count them as R04.',limits=['Required family rows intentionally overlap. Counts are not additive numbers of complete facilities.','No scene, master, cache, controller or original inventory was changed.','The Y15.5 reservoir-associated protected distribution and manually raised castle storage are distinct. Castle floor Y24 and stored water Y22 cannot be gravity-fed from Y15.5.','Separate household draw and process-canal branches are fictional design choices, not universal historical facts.','Fluid flow, water quality, hydraulic power, flood/structural capacity and working interiors remain unimplemented or unproved.','No fresh GUI visual inspection was performed for this source report.'],whole_city_completion_claim=False)
 write('facility_coverage.json',ledger)
 dependencies[str(currentproof.relative_to(ROOT))]=sha(currentproof)
 for p in upcoming:dependencies[str(p.relative_to(ROOT))]=sha(p)
 write('source_closure.json',dict(schema='riverstone.r8.facility_coverage_source_closure.v1',dependencies=dependencies,scope='Exact scene and all 263 master/cache pairs plus declared source audits; original legacy reference validity is separately reported per family.'))
 report=['# R8 current facility coverage: exact R04 snapshot','',f'Scene SHA256: `{EXPECTED}`','',f"The scene contains **{len(inst):,} common native instances** and **{len(assets)} asset records**. The old inventory’s zero-placement statement is obsolete. This report preserves that inventory and accounts for each of its 109 overlapping required family rows.",'', '## Scope','',ledger['runtime_scope'],'','No whole-city completion, working interiors, fluid simulation or final microdetail pass is claimed. Upcoming first61/noble/cemetery/835-fixture sources are not counted as R04 placements.','', '## Family ledger','', '| Required family | R04 status | Native instances | Exterior evidence and remaining scope |','|---|---|---:|---|']
 for r in rows:report.append('| '+r['id']+' | '+r['status']+' | '+str(r['native_instance_count'])+' | '+r['implemented_exterior'].replace('|','/')+' Remaining: '+' '.join(r['omissions']).replace('|','/')+' |')
 report+=['','Exact IDs, rigid poses, source/cache hashes, component references, triangle membership and all omissions are in `facility_coverage.json` and `actual_registry.json`. Source-only means a catalog source exists without proven exact active placement. Missing means no actual family geometry or implemented source was established. Partial exterior means related or incomplete physical work is present; it never closes the entire requirement.','', 'The single registered cathedral bell tower supersedes the older twin-steeple inventory label. Static rigged harbor geometry is present, while sailing remains unimplemented. Castle storage stays independently supplied/manually raised.']
 with(H/'CURRENT_COVERAGE.md').open('x')as f:f.write('\n'.join(report)+'\n')
 assert ref(INVENTORY)==original and sha(SCENE)==EXPECTED
 print(json.dumps(ledger['counts'],indent=2));print('retained water',wb['all_previous_water_triangles_present'],wb['all_previous_bed_sources_present'])
if __name__=='__main__':main()
