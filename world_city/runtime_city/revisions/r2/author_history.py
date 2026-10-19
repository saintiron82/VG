"""Author the user-directed second urban revision without altering the sealed r1."""
from pathlib import Path
import copy, json
ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'world_city/runtime_city/source/city_history_recovered_r1.json'
OUTPUT = Path(__file__).parent / 'city_history.r2.candidate.json'
MATERIALS = {'clay_red': {'slate': 'a16b51', 'slate_light': 'ac775c', 'slate_dark': '80523f', 'slate_worn': 'b18a6c'}, 'wood_brown': {'slate': '80664a', 'slate_light': '8c7355', 'slate_dark': '624f3d', 'slate_worn': '9c8568'}, 'slate_gray': {'slate': '646f73', 'slate_light': '748085', 'slate_dark': '4a565c', 'slate_worn': '879096'}, 'approved_teal': {'slate': '45676a', 'slate_light': '658284', 'slate_dark': '355157', 'slate_worn': '7b8f8a'}}
WEIGHTS = {'D01': {'slate_gray': 0.75, 'clay_red': 0.2, 'wood_brown': 0.05}, 'D02': {'slate_gray': 0.8, 'clay_red': 0.18, 'approved_teal': 0.02}, 'D03': {'clay_red': 0.62, 'slate_gray': 0.28, 'wood_brown': 0.05, 'approved_teal': 0.05}, 'D04': {'clay_red': 0.58, 'slate_gray': 0.28, 'wood_brown': 0.1, 'approved_teal': 0.04}, 'D05': {'clay_red': 0.55, 'wood_brown': 0.3, 'slate_gray': 0.15}, 'D06': {'clay_red': 0.68, 'wood_brown': 0.24, 'slate_gray': 0.08}, 'D07': {'wood_brown': 0.55, 'clay_red': 0.35, 'slate_gray': 0.08, 'approved_teal': 0.02}, 'D08': {'wood_brown': 0.48, 'clay_red': 0.4, 'slate_gray': 0.12}, 'D09': {'slate_gray': 0.78, 'clay_red': 0.18, 'wood_brown': 0.04}, 'D10': {'clay_red': 0.52, 'slate_gray': 0.42, 'wood_brown': 0.06}, 'S01': {'wood_brown': 0.66, 'clay_red': 0.3, 'slate_gray': 0.04}}
PROPERTY = {'D01': ['fortified_stone_hall', 'military_service_yard'], 'D02': ['ecclesiastical_close', 'cemetery', 'formal_precinct_garden'], 'D03': ['market_shop_house', 'civic_square_edge_stalls', 'inn_service_court'], 'D04': ['merchant_shop_warehouse_court', 'merchant_palazzo', 'stone_manor'], 'D05': ['loading_warehouse', 'cart_turning_quay', 'timber_storage_yard'], 'D06': ['workshop_workyard', 'kiln_free_safety_space', 'worker_house'], 'D07': ['poor_row', 'patched_timber_house', 'shared_service_court'], 'D08': ['timber_courtyard_house', 'orchard_holding', 'garden_house'], 'D09': ['gatehouse', 'wall_tower', 'patrol_strip'], 'D10': ['monastery_garden', 'charitable_hospital', 'cloister_service_court'], 'S01': ['small_farmstead', 'orchard', 'roadside_workshop']}
PITCH = {'clay_red': [38, 42, 46], 'wood_brown': [40, 45, 50], 'slate_gray': [42, 48, 54], 'approved_teal': [38, 44, 48]}

def build():
    h = copy.deepcopy(json.loads(BASE.read_text()))
    h['schema_version'] = 'riverstone.city.history.v2'
    h['integration_status'] = 'r2_candidate_source_not_yet_geometry_or_visual_pass'
    h['revision_direction'] = {'source': 'Publication note: project design decision; conversational attribution omitted.', 'priorities': ['social_class_and_property_type_change_actual_land_use', 'red_clay_brown_wood_gray_slate_roofs_dominant_teal_minority', 'forest_outside_walls_orchards_and_gardens_inside', 'defensible_hills_and_lower_floodplain_constrain_settlement', 'consolidation_allowed_with_source_ids_and_access_provenance'], 'fictional_design_not_historical_reconstruction': True}
    h['roof_material_families'] = MATERIALS
    h['era_geometry_mapping'] = {'crossing_fort': 'early', 'religious_precinct': 'early', 'chartered_market': 'early', 'river_trade': 'rebuilt', 'market_rebuilding': 'rebuilt', 'outer_infill': 'late'}
    h['era_selection_policy'] = {'unit': 'spatially_coherent_property_cluster', 'cluster_span_m': 96, 'require_geometry_choice_before_cache_key': True, 'fire_rule': 'market_rebuilding restricted to the market and adjacent merchant cluster, not random whole-city fire marks', 'geometry_fields': ['construction_era', 'facade_class', 'roof_form', 'roof_pitch_degrees', 'floor_height_m', 'roof_material_family']}
    h['roof_pitch_design_values_degrees'] = PITCH
    h['functional_pitch_cache_values_degrees'] = {'merchant': 46, 'old_timber': 48, 'port': 38, 'artisan': 42, 'garden': 45, 'institutional': 50, 'poor_row': 44, 'servant_lodge': 44, 'shed': 26}
    h['functional_pitch_scope'] = 'implemented source selector uses finite functional values; material-specific arrays are broader design bounds, not randomized per-building targets'
    for did, r in h['district_rules'].items():
        r['roof']['palette_family'] = 'function_era_material_families_r2'
        r['roof']['material_weights'] = WEIGHTS[did]
        r['roof']['pitch_degrees_policy'] = 'choose by material/function then reconcile height; earlier district ranges are superseded unimplemented design targets'
        r['roof']['superseded_pitch_target_degrees'] = r['roof'].pop('pitch_degrees')
        r['roof']['forms'] = ['gable', 'hip', 'twin_gable_z', 'shed'] if did not in ['D01', 'D02', 'D09'] else ['gable', 'hip', 'steep_gable']
        r['property_types'] = PROPERTY[did]
        r['courtyard_policy'] = 'explicit functional land use plus reserved pedestrian/service paths; no random clutter or automatic empty-court preservation'
        r['existing_footprint_count_scope'] = 'provenance count only, not immutable building count target'
    h['preservation']['existing_footprints'] = 'source retained as provenance; documented property consolidations may replace runtime footprints'
    h['preservation']['existing_ids'] = 'stable source IDs retained with retained/superseded/replacement status'
    h['city_defaults'].update({'roof_palette_family': 'function_era_clay_wood_slate_with_teal_minority_r2', 'palette_reference_policy': 'Publication note: project design decision; conversational attribution omitted.', 'era_assignment': 'choose deterministic96m property cluster era before geometry/cache selection, with explicit estate exceptions', 'floor_policy': 'derive height from authored floor height/count and true roof pitch; record delta from superseded planning height', 'roof_material_note': 'Clay-red, wood-brown and slate-gray are fictional game material families, not a survey or claim of historical uniformity', 'palette_binding_note': 'Protected seven are local exceptions. All other roof maps resolve to the explicit new material map.', 'procedural_variation_contract': {'seed_source': 'stable district/property cluster', 'era_mix_scope': 'fictional design priors', 'floor_counts_exclude': 'attic_and_roof', 'discrete_cache_key': ['assembly_class', 'dimensions', 'floors', 'construction_era', 'roof_form', 'roof_pitch', 'facade_style'], 'palette_cache': 'separate runtime material override, not unique geometry', 'orientation': 'explicit property frontage/access', 'no_unique_mesh_per_building': True}})
    for check in h['consistency_checks']:
        if check['id'] == 'palette_aliases':
            check['rule'] = 'Every per-property roof alias resolves to either explicit r2 material values or protected r4 values; no random per-cell color.'
        if check['id'] == 'protected_voids':
            check['rule'] = 'Keep route, river and active public/court/service access clear. Document any repurposed source court with functional ownership and replacement access.'
        if check['id'] == 'known_layout_count':
            check['rule'] = 'Account for every original1308 ID as retained or explicitly superseded. Resulting building count is not a forced target.'
        if check['id'] == 'nonuniform_identity':
            check['rule'] = 'Districts express physical era, function, tenure and land-use differences; documented property consolidation is allowed.'
    h['landuse_contract'] = {'source_ids': 'all retained, superseded or consolidated IDs recorded', 'roads': 'preserve primary network and justify any local access amendment', 'active_walkspaces': 'reserve explicit widths before placing buildings or facilities', 'woodland': 'outside wall, exclude roads, river floodway, bridge and gate sight/access corridors', 'orchards': 'productive inner holdings, not random city forest', 'manors': 'three distinct coherent holdings: older stone manor, merchant palazzo, timber courtyard house', 'floodplain': 'keep banks/loading accesses clear; not flood simulation', 'roof_palette': 'stable by property/era/material; never random per cell', 'protected_seven': 'retain recorded palette and geometry until separately superseded by explicit design, as local exceptions'}
    h['precedence'].insert(0, 'Publication note: project design decision; conversational attribution omitted.') if isinstance(h['precedence'], list) else None
    return h
if __name__ == '__main__':
    h = build()
    OUTPUT.write_text(json.dumps(h, ensure_ascii=False, indent=2) + '\n')
    print(OUTPUT)
