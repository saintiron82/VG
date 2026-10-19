"""Reference actual existing sources and the bounded staged set, without compiling."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from world_city.runtime_city.parts.author import HERE, KINDS, file_ref, make_master, write_sources

CONCEPT = 'world_city/reference/revision_02/city_terrain_concept.png'
PROMPT = 'world_city/reference/revision_02/prompt.txt'
INFRA = 'world_city/runtime_city/infrastructure/generated/infrastructure.json'
FABRIC = 'world_city/runtime_city/urban_fabric/generated/urban_fabric.json'
R2 = 'world_city/runtime_city/revisions/r2/authoring_plan.base.json'
LANDMARK = 'world_city/runtime_city/landmarks/author.py'
INFRA_AUTHOR = 'world_city/runtime_city/infrastructure/author.py'
FABRIC_AUTHOR = 'world_city/runtime_city/urban_fabric/author.py'


def build_inventory():
    entries = []
    infra = json.loads((ROOT / INFRA).read_text())
    fabric = json.loads((ROOT / FABRIC).read_text())
    plan = json.loads((ROOT / R2).read_text())

    def existing(name, family, observed, refs, gaps, contract, evidence='observed_family'):
        entries.append({'id': name, 'facility_family': family, 'status': 'existing_implemented',
                        'geometry_state': 'source_exists_not_rebuilt_in_this_task',
                        'observation': {'status': evidence, 'note': observed, 'source': CONCEPT},
                        'source_refs': refs, 'remaining_work': gaps, 'interface_contract': contract,
                        'art_review': 'required_against_revision_02_concept',
                        'city_placement_changed': False})

    def infrastructure_refs(kind):
        items = [(k, v) for k, v in infra['master_specs'].items() if v['kind'] == kind]
        return [{**file_ref(INFRA), 'json_pointer': '/master_specs/' + key, 'spec': value,
                 'author': INFRA_AUTHOR} for key, value in items[:1]] or [{**file_ref(INFRA_AUTHOR), 'callable':'make_master', 'source_kind':kind, 'status':'implemented_source_branch_no_current_generated_spec'}]

    def fabric_refs(kind):
        items = [(k, v) for k, v in fabric['master_specs'].items() if v['kind'] == kind]
        return [{**file_ref(FABRIC), 'json_pointer': '/master_specs/' + key, 'spec': value,
                 'author': FABRIC_AUTHOR} for key, value in items[:1]]

    def landmark_refs(kind):
        result = []
        for key, value in plan['asset_specs'].items():
            if value.get('family') == 'landmark' and value['kind'] == kind:
                p = 'world_city/runtime_city/generated/r1/masters/' + key + '.json'
                result.append({**file_ref(p), 'author': LANDMARK, 'asset_id': key, 'dimensions_source': value})
        return result

    for name, family, kind, note, gaps in [
        ('timber_dock', 'harbor', 'dock', 'Timber loading piers visible along the south city bank.', ['Piles, bents, edge detail and changing water-level placement remain assembly work.']),
        ('bridge_deck', 'bridge', 'bridge_deck', 'Single main stone bridge connects south gate and south bank.', ['Existing deck is not a complete multi-arch stone bridge.']),
        ('bridge_pier', 'bridge', 'bridge_pier', 'Bridge support/pier family visible; underside count is not safely measurable.', ['Cutwaters, foundation depth, arch springing and hydraulic clearance need design.']),
        ('city_curtain_wall', 'fortification', 'wall_panel', 'Continuous perimeter stone walls connect towers.', ['Terrain-following revised wall grade and retaining interactions remain open.']),
        ('city_battlements', 'fortification', 'battlement', 'Wall parapets/crowns are visible.', ['Detailed wall-walk access, guards and collision remain assembly checks.']),
        ('street_paving', 'circulation', 'road_paver', 'Connected main streets and narrower lanes visible.', ['Revision 02 intermediate terrace grades and switchbacks remain design work.']),
        ('plaza_surface', 'market_and_parks', 'surface_patch', 'Central civic square and terrace courts are paved.', ['New park/path/market reservations are not committed by this catalog.']),
    ]:
        existing(name, family, note, infrastructure_refs(kind), gaps,
                 {'datum': 'Local source walking top Y=0; never interpret as final world elevation.',
                  'support': 'Use source spec envelope and external bearing surface.',
                  'lod': 'Use unchanged common compiler and existing route seam contract.',
                  'animation': 'static', 'sockets': 'Endpoint/grade interfaces in infrastructure source; not new geometry.'})

    for name, family, kind, note, gaps in [
        ('cathedral_nave_transept', 'cathedral', 'cathedral', 'Northeast cathedral has nave, transept, lower aisles and projecting buttress rhythm.', ['Existing cathedral master has stepped buttresses; flying system and final concept silhouette need review.']),
        ('cathedral_twin_steeples', 'cathedral', 'cathedral', 'Two tall front steeple forms visible in northeast cathedral.', ['Reuse tower/spire components from existing cathedral, not duplicate a tower engine.']),
        ('cathedral_existing_buttresses', 'cathedral', 'cathedral', 'Buttress rhythm is visible; exact rib/arch geometry is inferred.', ['Existing stepped buttresses and new flying prototype require compatibility review.']),
        ('castle_keep_courtyard', 'castle', 'castle_keep', 'Northwest castle has open court, keep, curtain walls and projecting towers.', ['Hill, court grade and detailed castle traversal remain separate terrain/assembly work.']),
        ('castle_curtain_towers', 'castle', 'castle_keep', 'Castle enclosure towers and walls visible on upper-left terrace.', ['Source components are within existing castle master; extract/reference only if a later approved assembly needs them.']),
        ('perimeter_wall_towers', 'fortification', 'wall_tower', 'Repeated wall towers ring city.', ['Existing towers have unresolved vertical wall-walk access; no claim of playable interiors.']),
        ('gatehouses', 'fortification', 'gatehouse', 'South bridge gate and side gatehouses visible.', ['Retain existing passage/secondary-opening source; reassess every changed approach grade.']),
        ('warehouse_buildings', 'harbor', 'warehouse', 'Quayside warehouses and inland loading yards visible.', ['Reuse existing three warehouse specifications; hoist attachment/facade openings need review.']),
        ('civic_hall', 'market', 'town_hall', 'Central civic hall with arcade/tower faces market.', ['A grain hall is a distinct program; existing town hall must not silently substitute for it.']),
        ('monastery_hospital', 'religious_service', 'monastery', 'Large southwest religious court/cloister complex visible.', ['Exact hospital rooms and cloister circulation are not implemented.']),
        ('neighborhood_church', 'religious_service', 'church', 'Smaller religious building forms appear across districts.', ['Interiors and new-concept placement remain unverified.']),
    ]:
        existing(name, family, note, landmark_refs(kind), gaps,
                 {'dimensions': 'Read source dimensions_source and master total_envelope_m; do not measure image pixels.',
                  'sockets': 'Existing master extensions.entrances and component pivots.',
                  'clearances': 'Existing constraints plus new assembly-side setbacks; no automatic facade cutting.',
                  'support': 'Original master base requires verified terrain foundation.',
                  'lod': 'Single common master per existing source; retain approved r2 palette overrides.',
                  'animation': 'No new behavior. Closed-door/interior limitations remain.'})

    for name, family, kind, note, gaps in [
        ('market_stall_family', 'market', 'market_stall', 'Organized canopy stall clusters visible in central square.', ['Existing timber/cloth options are primitive sources; facade/pole/display variety needs art review.']),
        ('loading_platform', 'harbor', 'loading_platform', 'Quay and warehouse loading platforms/yards visible.', ['Match crate, hoist and cart heights at actual assembly time.']),
        ('workyard_bench', 'craft', 'workbench', 'Southeast craft yards are visible; exact benches are inferred.', ['Tool racks, work-specific equipment and interior workflows not built.']),
        ('timber_cargo_stack', 'harbor', 'timber_stack', 'Timber/cargo storage in working yards is a program inference.', ['Cargo arrangement and lift clearances need review.']),
        ('garden_beds_orchards', 'park_and_garden', 'garden_bed', 'North-central gardens and productive south-bank plots visible.', ['Beds alone do not implement an orchard or botanical variety.']),
        ('park_grove_trees', 'park_and_garden', 'tree', 'Small interior groves and irregular exterior north/west woodland visible.', ['Existing tree source is a simple prototype; varied crowns, species and non-grid ecology remain art work.']),
        ('grave_markers', 'cathedral_close', 'grave_marker', 'Cemetery is required by prompt; individual graves are not reliably resolved.', ['Cemetery layout, memorial variation and paths require source/concept review.']),
        ('property_walls', 'neighborhood', 'boundary_wall', 'Enclosed manor/garden and workshop holdings visible.', ['Use existing source lengths; gates and cross-grade seams require assembly work.']),
    ]:
        existing(name, family, note, fabric_refs(kind), gaps,
                 {'sockets': 'Use source module dimensions and external assembly anchors.',
                  'support': 'Ground/foundation interface at local source base.',
                  'clearances': 'Existing property access reservations; no city placement change.',
                  'lod': 'Existing common master authoring only.', 'animation': 'static'},
                 'inferred_detail_in_observed_family' if kind in ('workbench','timber_stack','grave_marker') else 'observed_family')

    existing('market_fountain', 'market', 'Central market fountain is clearly visible.',
             [file_ref('voxel_character/common/assets/fountain/master.json')],
             ['Existing fountain is protected source; scale/placement and separate runtime flow integration require assembly validation.'],
             {'sockets': 'Existing ground/plume sockets and water/outlet connections.',
              'support': 'Level plaza; keep basin and outlets coherent.', 'lod': 'Existing common plane/functional-opening constraints.',
              'animation': 'Existing cell-animation subsystem is separate; no new flow runtime integrated here.'})

    ordinary_author = 'world_city/runtime_city/archetypes/ordinary_r2.py'
    ordinary = next((k,v) for k,v in plan['asset_specs'].items() if v.get('family') == 'ordinary_r2')
    ordinary_refs = [file_ref(ordinary_author), {**file_ref(R2), 'json_pointer':'/asset_specs/' + ordinary[0], 'spec':ordinary[1]}]
    for name, note, gap in [
        ('varied_roof_forms', 'Gables, hips, shed roofs and varied roof orientation are visible.', 'Ordinary r2 gable/hip/twin-gable/shed source forms exist; exact concept matching still needs art review.'),
        ('chimneys', 'Small chimney-like roof projections visible; individual counts inferred.', 'Existing ordinary source authors masonry shaft/cap; final silhouette and smoke/effects remain unreviewed.'),
        ('shopfronts', 'Merchant/craft street frontages visible; individual shop fittings inferred.', 'Existing shopfront openings/doors provide source detail; awnings, signs and displays need art review.'),
        ('attached_housing_manors', 'Dense attached blocks and several large enclosed garden estates visible.', 'Reuse ordinary r2 classes/urban fabric compounds; do not repeat one house type or invent final placements.'),
    ]:
        existing(name, 'urban_buildings', note, ordinary_refs, [gap],
                 {'dimensions':'Read actual source spec and derived envelope.', 'sockets':'Existing entrance metadata.',
                  'support':'Per-property graded foundation required.', 'clearances':'Preserve street/property access.',
                  'lod':'Single common master; roof role mapping uses canonical r2 palette.', 'animation':'No new runtime behavior.'})

    labels = {
        'quay_retaining_segment': ('harbor', 'Stone riverbank/quay edge visible; exact cross-section inferred.'),
        'timber_harbor_crane': ('harbor', 'Timber loading cranes visible on south quay; mechanism detail inferred.'),
        'river_cargo_barge': ('harbor', 'Several low river cargo boats visible; prototype is one open flat-bottom family.'),
        'warehouse_hoist': ('harbor', 'Hoist function required by quay/warehouse program; exact facade mount inferred.'),
        'cathedral_flying_buttress': ('cathedral', 'Cathedral buttress family visible; free-standing flying profile inferred.'),
        'pointed_arch_cloister_bay': ('cathedral', 'Cloister/arcade family visible near religious courts; bay dimensions inferred.'),
        'park_terrace_stair': ('park_and_terrace', 'Terrace stairs required and shown at neighborhood/precinct transitions; exact risers inferred.'),
        'retaining_wall_corner': ('park_and_terrace', 'Retaining walls turn around castle/cathedral/neighborhood terraces.'),
        'park_bench': ('park_and_terrace', 'Bench is a functional park inference, not confidently resolved in the image.'),
        'stone_planter': ('park_and_terrace', 'Planter is a functional park inference; planted garden/court family visible.'),
        'cargo_crate': ('harbor_and_market', 'Cargo piles/working yards visible; individual crate proportions inferred.'),
        'cargo_barrel': ('harbor_and_market', 'Cargo handling program implies barrels; exact individual barrel form inferred.'),
    }
    for kind in KINDS:
        master = make_master(kind); ext = master['extensions']; family, note = labels[kind]
        entries.append({'id':kind, 'facility_family':family, 'status':'staged_prototype',
                        'geometry_state':'new_continuous_master_authored',
                        'observation':{'status':'inferred_geometry_in_observed_or_required_family','note':note,'source':CONCEPT},
                        'source_refs':[file_ref('world_city/runtime_city/parts/masters/' + kind + '.json')],
                        'interface_contract':{key:copy for key,copy in ext.items() if key in ('local_bounds_m','footprint_xz_m','sockets','supports','clearances','animation_hooks','lod','design_notes')},
                        'remaining_work':['Matched-view art review.', 'Final material/scale and host assembly review.',
                                          'Placement, terrain, physical/traversal and animation integration where relevant.'],
                        'art_review':'not_run', 'city_placement_changed':False})

    for name, family, note, dependency, next_step in [
        ('multi_arch_bridge_vaults', 'bridge', 'Multi-arch stone bridge is required; image underside obscures precise vault geometry.', ['bridge_deck','bridge_pier'], 'Author real arch barrel/spandrel/cutwater modules after span, waterway, deck grade and boat clearance are fixed.'),
        ('harbor_floodwall_and_water_stairs', 'harbor', 'Floodwall and stairs down to water required in prompt; shoreline family visible.', ['quay_retaining_segment','park_terrace_stair'], 'Define flood datum, wet stair/tide access, quay edge guards and retaining loads; park stair is not automatically a flood-safe water stair.'),
        ('timber_dock_piles_bents', 'harbor', 'Pile-supported timber piers visible.', ['timber_dock'], 'Author piles/cross-bents for approved bed depth and deck interface; existing deck alone is insufficient.'),
        ('sailing_river_boat_family', 'harbor', 'Small sailboats with masts/rigging visible in foreground river.', ['river_cargo_barge'], 'Create rigged cargo and sailboat variants; no mast/rigging/sail or sailing runtime in staged barge.'),
        ('full_cloister_corners_and_court', 'cathedral', 'Enclosed cloister/court families visible at cathedral and monastery.', ['pointed_arch_cloister_bay','monastery_hospital'], 'Resolve corner bay, courtyard, drainage, path links and exterior/interior relationship.'),
        ('cathedral_tracery_and_roof_detail', 'cathedral', 'Large windows/spires and roof articulation visible.', ['cathedral_nave_transept','cathedral_twin_steeples'], 'Refine tracery, gargoyles/drainage and flying-buttress connection against approved concept.'),
        ('grain_hall', 'market', 'Grain hall explicitly required by prompt; identity of individual square-side building is inferred.', ['civic_hall','warehouse_buildings'], 'Create distinct grain-hall program/master or approve a source adaptation, keeping hall circulation and unloading separate.'),
        ('market_carts_and_handcarts', 'market_and_harbor', 'Cart unloading required by prompt and suggested by working-square/yard details.', ['cargo_crate','cargo_barrel'], 'Author wheels, axle, bed, shafts, loading sockets and collision; carts are missing, not silently substituted by crates.'),
        ('dormer_family', 'urban_buildings', 'Roof/dormer-like projections visible; exact per-house form is not measurable.', ['varied_roof_forms'], 'Dedicated dormer cut/roof/sill modules not confirmed in existing ordinary master; inspect/refine with art review.'),
        ('shop_awning_sign_and_display', 'urban_buildings', 'Street commerce visible; individual signs and display design inferred.', ['shopfronts','market_stall_family'], 'Existing ordinary source already includes a shop_canopy; add/refine canopy variants, signs and displays without narrowing access.'),
        ('park_paths_edges_vegetation_variants', 'park_and_garden', 'Smaller urban parks and varied woodland crowns visible.', ['park_grove_trees','garden_beds_orchards','park_bench','stone_planter'], 'Review species/canopies, path edging, slopes and non-grid woodland placement; no final landscape claimed.'),
        ('neighborhood_terrace_assemblies', 'park_and_terrace', 'Intermediate 2–6 m terraces are an explicit design target.', ['park_terrace_stair','retaining_wall_corner','street_paving'], 'Approve terrain scheme and cart switchbacks, then assemble steps/landings, guards, retaining drainage and accessible alternatives.'),
        ('defensive_doors_portcullis_access', 'fortification', 'Gatehouse doors and wall-walk access are required functional inferences.', ['gatehouses','perimeter_wall_towers'], 'Author compatible door/portcullis motions, guard stairs and walk access without closing approved passage clearances.'),
        ('craft_equipment_and_mills', 'craft', 'Craft yards visible; watermill/industrial mechanics not confidently identified.', ['workyard_bench','warehouse_buildings'], 'Review craft program before adding furnace, forge, mill wheel, machinery or effects.'),
    ]:
        entries.append({'id':name,'facility_family':family,'status':'needs_art_review',
                        'geometry_state':'missing_or_incomplete_assembly','observation':{'status':'observed_family_or_explicit_prompt_with_inferred_details','note':note,'source':CONCEPT},
                        'source_refs':[file_ref(PROMPT)],'depends_on_inventory_ids':dependency,
                        'remaining_work':[next_step],'art_review':'required_before_geometry_commit',
                        'city_placement_changed':False})

    water_requirements = 'world_city/runtime_city/parts/requirements_addendum.json'
    water_rows = [
        ('water_source_intake_headworks','clean_supply','Higher-head source, intake screen and headworks require catchment/source validation.'),
        ('water_reservoir_settling_pond','clean_supply','Reservoir or settling pond requires approved capacity, water surface head, embankment, spillway and sediment access.'),
        ('water_clean_cistern','clean_supply','Covered storage cistern needs floor/roof/access, usable level and drawpoint links.'),
        ('water_covered_clean_conduit','clean_supply','Covered clean-water conduit needs invert/crown, maintained positive head or supported pumping proposal, and contamination separation.'),
        ('water_millrace','industrial_water','Industrial millrace needs independent intake/return path and a validated head drop; no connection to potable storage is assumed.'),
        ('water_sluice','industrial_water','Sluice gate/guide/pivot and operating clearance are missing; dynamics are not implemented.'),
        ('water_weir','industrial_water','Weir crest, overflow and fish/debris passage are candidate design questions, not measured historical facts.'),
        ('water_storm_drain','drainage','Street drain/inlet and collection conduit must follow local falling invert and remain distinct from clean supply.'),
        ('water_outfall','drainage','Outfall needs receiving level, backflow protection and erosion apron after the candidate node/head graph is approved.'),
        ('water_floodgate','flood_control','Floodgate needs certified closure envelope, flood head and operating access; no current flood-control simulation.'),
        ('water_well_drawpoint','clean_supply','Well/drawpoint needs source/water-quality and access review; existing well reservations are not built wells.'),
        ('water_canal_footbridge','crossing','Small canal footbridge can reference existing deck grammar but needs its own span, clearance, pier/abutment and handrail master.'),
        ('water_protective_edge','safety_edge','Canal/reservoir protective coping, parapet or rails must preserve inspection and emergency access.'),
    ]
    for name, system, requirement in water_rows:
        entries.append({'id':name,'facility_family':'water_system','water_system':system,
                        'status':'needs_art_review','geometry_state':'missing_candidate_design_only',
                        'observation':{'status':'latest_explicit_requirement_not_confirmed_in_revision_02_image','note':requirement,'source':water_requirements},
                        'source_refs':[file_ref(water_requirements)],
                        'depends_on_inventory_ids':[],
                        'interface_contract':{'hydrology':'Await candidate node/head graph. Do not assume low river can feed uphill by gravity.',
                                              'local_geometry':'No exact dimensions, source head or final footprint committed.',
                                              'separation':'Clean supply, industrial water and drainage are separate systems.',
                                              'runtime':'No water simulation, pollution, pump or gate animation implemented.'},
                        'remaining_work':[requirement,'Review full hydraulic/source/level/access design before authoring or placement.'],
                        'art_review':'required','city_placement_changed':False})
    for name, note, dependencies in [
        ('military_training_ground','Training surface, assembly space, armory/store, guards, access and separation from public streets form a functional container; not implemented.', ['castle_keep_courtyard','gatehouses']),
        ('logistics_market_container','Cart arrival, unloading, grain/cargo storage, stalls and clear circulation need one coordinated functional container.', ['grain_hall','market_carts_and_handcarts','market_stall_family','warehouse_buildings']),
        ('large_noble_compound_container','Existing three estate/urban-fabric sources are reusable, but gates, servants, stable/service yards and garden circulation require one reviewed social-use assembly.', ['attached_housing_manors','property_walls','garden_beds_orchards']),
        ('service_housing_container','Ordinary r2 servant_lodge class exists; service quarters need explicit household/workplace/access relationships, not only a roof palette.', ['attached_housing_manors']),
        ('poorer_row_quarter_container','Ordinary r2 poor_row class exists; poorer quarter needs dense plot rhythm, shared water/access and work/yard relationships.', ['attached_housing_manors','water_well_drawpoint']),
    ]:
        entries.append({'id':name,'facility_family':'social_functional_container','status':'needs_art_review',
                        'geometry_state':'assembly_missing_reusable_component_sources_exist',
                        'observation':{'status':'latest_explicit_requirement_with_existing_source_references','note':note,'source':water_requirements},
                        'source_refs':[file_ref(water_requirements),file_ref(ordinary_author),file_ref(FABRIC_AUTHOR)],
                        'depends_on_inventory_ids':dependencies,'remaining_work':[note,'Coordinate with revised district/terrain plan before committing placements.'],
                        'art_review':'required','city_placement_changed':False})

    return {
        'schema':'riverstone.city.parts_inventory.v1', 'revision':1,
        'status':'staged_catalog_not_final_city',
        'inputs':[file_ref(CONCEPT),file_ref(PROMPT),file_ref('voxel_character/common/assets/house/master.json'),file_ref('voxel_character/common/assets/fountain/master.json'),file_ref(R2)],
        'observation_policy':'Concept inspected for visible/required facility families. Hidden geometry and every new module dimension are design inferences; exact metres are never guessed from pixels.',
        'concept_scope':'Revision 02 production design reference, not an actual game render or verified implementation. New water/social requirements are inventoried separately; next concept not yet inspected.',
        'water_system_policy':{'clean_supply_separate':True,'industrial_separate':True,'drainage_separate':True,'head_graph_status':'separate_candidate_pending','low_river_gravity_uphill_claim':False},
        'terrain_reference_only':{'castle_terrace_m':24,'cathedral_terrace_m':14,'intermediate_terraces_m':[2,6],'source':PROMPT,'status':'concept targets; not implemented by parts catalog'},
        'implementation_boundary':{'new_engine':False,'new_mesher':False,'city_placements':False,'terrain_changes':False,'existing_master_edits':False,'gui_run':False},
        'process':{
            'input':'Revision 02 concept/prompt, recovered plan, existing common masters and canonical r2 palettes.',
            'conditions':'One continuous common master per staged part. Reuse existing sources. Preserve local metre axes, real openings, support zones and unknowns. No final terrain or city placement.',
            'deliverables':'Complete facility-family inventory, 12 bounded prototype masters, source author, contract tests, small common compile evidence and Korean/English handoff.',
            'completion_criteria':'Every required facility family classified; refs resolve; source contracts validate; bounded smoke/repeat tests reported honestly. City/art/physics integration remains pending.'},
        'compile_budget':{'candidate_cells_per_compile':120000,'output_cells_per_compile':40000,'sequential_only':True,
                          'default_smoke_pitch_m':.2,'stair_smoke_pitch_m':.15,'extra_repeat':'Bench at .15 and .2 m, independent direct source compiles.',
                          'no_whole_city_compile':True,'no_gui':True},
        'counts':{status:sum(e['status']==status for e in entries) for status in ('existing_implemented','staged_prototype','needs_art_review')},
        'entries':entries,
    }


def readable_inventory(inventory):
    lines = ['# 시설별 구현 상태 / Facility inventory', '',
             'This is a source handoff, not an art-approved city. Source dimensions are not measurements of image pixels.',
             '관찰한 시설군과 설계 추정을 구분하고, 빠진 시설은 검토 필요 상태로 남깁니다.', '',
             'Input: revision 02 concept and source data; added water/social requirements are recorded separately.',
             'Conditions: reuse existing sources, author one common continuous master per new part, preserve functional clearances, and leave terrain/placement uncommitted.',
             'Deliverables: this inventory, machine-readable inventory.json, 12 masters, source code and bounded smoke evidence.',
             'Completion criteria: references and required families covered; declared small tests pass. Visual/physics/traversal/animation and complete-city integration remain pending.', '']
    labels = {'existing_implemented':'기존 구현 소스 / Existing implemented source',
              'staged_prototype':'새 시제품 / Staged prototype',
              'needs_art_review':'미구현·조립 검토 / Missing or incomplete assembly'}
    for status, label in labels.items():
        lines += ['## ' + label + ' (' + str(inventory['counts'][status]) + ')', '']
        for entry in inventory['entries']:
            if entry['status'] != status: continue
            lines += ['### ' + entry['id'].replace('_',' '),
                      '- ID: `' + entry['id'] + '`',
                      '- Family: ' + entry['facility_family'].replace('_',' '),
                      '- Evidence: ' + entry['observation']['status'].replace('_',' ') + '. ' + entry['observation']['note'],
                      '- Source: ' + '; '.join('[' + Path(r['path']).name + '](' + '../../../' + r['path'] + ')' + (' at ' + r['json_pointer'] if 'json_pointer' in r else '') for r in entry['source_refs']),
                      '- Remaining: ' + ' '.join(entry['remaining_work'])]
            contract=entry.get('interface_contract',{})
            if 'local_bounds_m' in contract:
                b=contract['local_bounds_m']
                lines += ['- Local bounds, metres: ' + str(b['min']) + ' to ' + str(b['max']) + '.',
                          '- Sockets: ' + ', '.join(s['id'] for s in contract['sockets']) + '.',
                          '- Supports: ' + ' '.join(s['requires'] for s in contract['supports']),
                          '- Reserve: ' + '; '.join(c['id'] + ': ' + c['purpose'] for c in contract['clearances']),
                          '- Animation: ' + (', '.join(h['id'] for h in contract['animation_hooks']) + ' (metadata only).' if contract['animation_hooks'] else 'Static; no new runtime motion.')]
            if entry.get('depends_on_inventory_ids'):
                lines += ['- Reuses: ' + ', '.join(entry['depends_on_inventory_ids']) + '.']
            lines += ['']
    lines += ['## Status boundaries', '',
              '- Existing implemented means a source branch or master exists. It does not approve its match to the new concept.',
              '- Staged prototype means new source geometry exists and small common checks were run. It does not establish final art, gameplay or placement.',
              '- Missing/incomplete means the facility family is explicitly tracked; no implementation is invented.',
              '- New water systems require a source/head graph. No uphill gravity supply from the low river is claimed.',
              '- For measured smoke results and limitations, see [README_KO.md](README_KO.md) and [smoke report](evidence/smoke_report.json).', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    write_sources()
    value=build_inventory()
    (HERE/'inventory.json').write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    (HERE/'INVENTORY.md').write_text(readable_inventory(value))
    print(json.dumps(value['counts']))
