#!/usr/bin/env python3
"""Audit fictional-history implementation using persisted continuous geometry.

No compiler, GUI, renderer, sampling or source mutation is performed. District
design ranges are observations, not hard validity gates: protected records and
source envelopes have higher precedence. Run from any directory, optionally
with --root REPO and --output FILE. --self-test runs only bounded math tests.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib
import itertools
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(values):
    return dict(sorted(Counter(values).items(), key=lambda item: str(item[0])))


def span(values):
    values = list(values)
    return [round(min(values), 6), round(max(values), 6)] if values else None


def transform(point, tr=None, vector=False):
    tr = tr or {}
    basis = tr.get("basis", IDENTITY)
    translation = [0, 0, 0] if vector else tr.get("translation", [0, 0, 0])
    return [sum(basis[i][j] * point[j] for j in range(3)) + translation[i]
            for i in range(3)]


def operations(master):
    components = {c["id"]: c for c in master["components"]}
    for instance in master["instances"]:
        component = components[instance["component"]]
        categories = {p.get("metadata", {}).get("source_category")
                      for p in component.get("parts", [])}
        for op in component["operations"]:
            yield component, categories, instance, op


def points(shape):
    if shape["kind"] == "box":
        return list(itertools.product(*zip(shape["min"], shape["max"])))
    if shape["kind"] == "extrusion":
        return [[x, y, z] for x, y in shape["polygon"]
                for z in (shape["z_min"], shape["z_max"])]
    return []  # Lathe envelopes are not needed for protected ordinary buildings.


def inspect_geometry(master):
    roof_parts = defaultdict(lambda: {"angles": set(), "axes": set(), "operations": []})
    floor_slabs, floor_heights, dados, bounds_points = [], [], [], []
    op_ids, wall_materials = set(), defaultdict(set)
    spires = []
    for component, categories, instance, op in operations(master):
        if op.get("action") != "paint":
            op_ids.add(op["id"])
            continue
        shape = op["shape"]
        op_ids.add(op["id"])
        for p in points(shape):
            bounds_points.append(transform(transform(p, op.get("transform")), instance.get("transform")))
        if "structural_floor" in categories and op["id"] == "floor_slab":
            floor_slabs.append(component["id"])
        if op["id"] == "wall_panel":
            floor_heights.append(shape["max"][1] - shape["min"][1])
            wall_materials[component["id"]].add(op.get("material"))
        if op["id"] == "era_stone_dado":
            dados.append(shape["max"][1] - shape["min"][1])
        if not categories.intersection({"roof", "roof_surface"}):
            continue
        if shape["kind"] == "extrusion":
            # Derive pitch from actual profile segments after operation and
            # component transforms. No roof_form/rise/eave metadata is used.
            poly = shape["polygon"]
            angles = set()
            for a, b in zip(poly, poly[1:] + poly[:1]):
                if abs(b[0] - a[0]) < 1e-9:
                    continue  # Vertical shell-thickness end, not roof slope.
                v = transform([b[0]-a[0], b[1]-a[1], 0], op.get("transform"), True)
                v = transform(v, instance.get("transform"), True)
                angles.add(round(math.degrees(math.atan2(abs(v[1]), math.hypot(v[0], v[2]))), 6))
            ridge = transform([0, 0, 1], op.get("transform"), True)
            ridge = transform(ridge, instance.get("transform"), True)
            # Landmark roof components hold multiple named roof masses.
            name = component["id"] if "roof_surface" in categories else op["id"].rsplit("_", 2)[0]
            item = roof_parts[name]
            item["angles"].update(angles)
            item["axes"].add("x" if abs(ridge[0]) > abs(ridge[2]) else "z")
            item["operations"].append(op["id"])
        elif shape["kind"] == "lathe":
            a, b = shape["profile"][:2]
            spires.append({"operation": op["id"], "outer_profile_slope_degrees":
                           round(math.degrees(math.atan2(abs(b[1]-a[1]), abs(b[0]-a[0]))), 6)})
    roofs = [{"part": name, "slope_degrees": sorted(item["angles"]),
              "ridge_axes_local": sorted(item["axes"]), "source_operations": item["operations"]}
             for name, item in sorted(roof_parts.items())]
    cues = {
        "shop_aperture": "shop_opening_aperture" in op_ids,
        "work_bay_aperture": "work_bay_aperture" in op_ids,
        "workshop_flue": "workshop_flue" in op_ids,
        "shop_canopy": "sloping_canopy" in op_ids,
        "diagonal_timber_braces": any("diagonal_brace" in i for i in op_ids),
        "window_shutters": any(i.endswith("_shutter") for i in op_ids),
        "double_loading_leaves": {"closed_left_leaf", "closed_right_leaf"} <= op_ids,
        "light_plaster_panels": any("plaster_light" in v for v in wall_materials.values()),
        "stone_ground_floor_panels": any(k.startswith("wall_0_") and "stone" in v for k, v in wall_materials.items()),
        "dark_stone_ground_floor_panels": any(k.startswith("wall_0_") and "stone_dark" in v for k, v in wall_materials.items()),
        "stone_dado": bool(dados),
    }
    return {
        "roof_parts": roofs, "main_roof_pitch_range_degrees": span(a for r in roofs for a in r["slope_degrees"]),
        "spire_profiles": spires, "authored_floor_slab_count": len(floor_slabs),
        "wall_storey_height_range_m": span(floor_heights), "observed_stone_dado_heights_m": sorted(set(round(d, 6) for d in dados)),
        "operation_level_style_cues": cues,
        "painted_box_extrusion_envelope_m": {"min": [min(p[i] for p in bounds_points) for i in range(3)],
                                              "max": [max(p[i] for p in bounds_points) for i in range(3)]} if bounds_points else None,
        "envelope_limit": "Painted box/extrusion union only; not CSG occupancy or sampled silhouette. Lathe spires excluded from this envelope.",
    }


def audit(root):
    rels = {
        "history": "world_city/runtime_city/source/city_history_recovered_r1.json",
        "layout": "world_city/data/city_brief.v2.json",
        "plan": "world_city/runtime_city/generated/r1/authoring_plan.json",
        "scene": "world_city/runtime_city/generated/r1/scene.json",
        "ordinary_author": "world_city/runtime_city/archetypes/ordinary.py",
        "landmark_author": "world_city/runtime_city/landmarks/author.py",
        "orchestration": "world_city/runtime_city/assemble_city.py",
        "recovery": "world_city/runtime_city/source/recovery_record.json",
    }
    fingerprints = {k: {"path": v, "sha256": sha(root / v)} for k, v in rels.items()}
    history, layout, plan, scene = [json.loads((root / rels[k]).read_text()) for k in ("history", "layout", "plan", "scene")]
    sys.path.insert(0, str(root))
    ordinary = importlib.import_module("world_city.runtime_city.archetypes.ordinary")
    landmark = importlib.import_module("world_city.runtime_city.landmarks.author")
    inspections, resource_errors, author_drift, spec_geometry_errors = {}, [], [], []
    for key, spec in sorted(scene["asset_specs"].items()):
        entry = scene["assets"].get(key, {}).get("coarse")
        if not entry or not (root / entry["master_path"]).is_file():
            resource_errors.append({"asset_key": key, "error": "missing_persisted_master"})
            continue
        path = root / entry["master_path"]
        master = json.loads(path.read_text())
        actual_hash = sha(path)
        if actual_hash != entry["master_sha256"]:
            resource_errors.append({"asset_key": key, "error": "master_hash_mismatch"})
        generator = ordinary.make_master if spec["family"] == "ordinary" else landmark.make_master
        fresh = generator({k: v for k, v in spec.items() if k != "family"})
        equal = master == fresh
        if not equal:
            author_drift.append(key)
        result = inspect_geometry(master)
        if spec["family"] == "ordinary" and result["authored_floor_slab_count"] != spec["floors"]:
            spec_geometry_errors.append({"asset_key": key, "error": "floor_count_differs_from_geometry"})
        inspections[key] = {"spec": spec, "master_path": entry["master_path"], "master_sha256": actual_hash,
                            "matches_current_author_without_compilation": equal, **result}
    source_ids = {b["id"] for b in layout["building_plans"]}
    scene_ids = [i["id"] for i in scene["instances"]]
    protected = history["preservation"]["authored_D03_buildings"]["records"]
    districts, below_ids, unmeasured_ids = {}, [], []
    by_district = defaultdict(list)
    by_asset_eras = defaultdict(set)
    for inst in scene["instances"]:
        by_district[inst["district_id"]].append(inst)
        by_asset_eras[inst["asset_key"]].add(inst["era_id"])
    for did, rule in history["district_rules"].items():
        all_instances = by_district[did]
        ordinary_instances = [i for i in all_instances if scene["asset_specs"][i["asset_key"]]["family"] == "ordinary"]
        specs = [scene["asset_specs"][i["asset_key"]] for i in ordinary_instances]
        pairs = [(i, inspections[i["asset_key"]]) for i in ordinary_instances if i["asset_key"] in inspections]
        measured = [a for _, g in pairs for a in (g["main_roof_pitch_range_degrees"] or [])]
        eligible = [(i, g) for i, g in pairs if i["id"] not in protected]
        below = [i["id"] for i, g in eligible if g["main_roof_pitch_range_degrees"] and g["main_roof_pitch_range_degrees"][1] < rule["roof"]["pitch_degrees"][0] - 1e-5]
        unmeasured = [i["id"] for i, g in eligible if not g["main_roof_pitch_range_degrees"]]
        below_ids.extend(below)
        unmeasured_ids.extend(unmeasured)
        outside_floors = [i["id"] for i, g in pairs if not rule["floors"][0] <= g["authored_floor_slab_count"] <= rule["floors"][1]]
        districts[did] = {
            "name": rule["name"], "total_instances": len(all_instances), "ordinary_instances": len(ordinary_instances),
            "landmark_instances": len(all_instances)-len(ordinary_instances),
            "ordinary_style_counts": counts(s["style"] for s in specs),
            "ordinary_chronology_label_counts": counts(i["era_id"] for i in ordinary_instances),
            "ordinary_geometry_era_counts": counts(s["construction_era"] for s in specs),
            "chronology_to_geometry_era_counts": counts(i["era_id"] + " -> " + g["spec"]["construction_era"] for i, g in pairs),
            "canonical_era_design_priors": rule["era_mix"],
            "actual_floor_slab_counts": counts(g["authored_floor_slab_count"] for _, g in pairs),
            "canonical_floor_design_range": rule["floors"],
            "outside_floor_design_range_ids": outside_floors,
            "floor_range_exceptions": {i["id"]: "protected_record" if i["id"] in protected else "explicit_rear_annex" if i["functional_role"] == "rear_workshop_or_store" else "review_source_height_precedence" for i in ordinary_instances if i["id"] in outside_floors},
            "roof_form_spec_counts": counts(s["roof_form"] for s in specs),
            "actual_primary_roof_pitch_range_degrees": span(measured),
            "canonical_new_ordinary_pitch_design_range": rule["roof"]["pitch_degrees"],
            "nonprotected_ordinary_measured": len(eligible)-len(unmeasured),
            "below_proposed_pitch_range_count": len(below),
            "actual_style_cue_building_counts": counts(c for _, g in pairs for c, present in g["operation_level_style_cues"].items() if present),
            "height_adjusted_ids": [i["id"] for i in all_instances if i["height_delta_m"]],
        }
    protected_checks = []
    inst_by_id = {i["id"]: i for i in scene["instances"]}
    topology = {"single_z": (1, "z"), "twin_z": (2, "z"), "twin_x": (2, "x")}
    for bid, record in protected.items():
        if bid not in inst_by_id or inst_by_id[bid]["asset_key"] not in inspections:
            protected_checks.append({"id": bid, "pass": False, "error": "missing_instance_or_geometry"})
            continue
        inst = inst_by_id[bid]
        g = inspections[inst["asset_key"]]
        envelope = g["painted_box_extrusion_envelope_m"]
        measured_w = envelope["max"][0] - envelope["min"][0]
        measured_d = envelope["max"][2] - envelope["min"][2]
        roofs = g["roof_parts"]
        n, axis = topology[record["roof_topology"]]
        checks = {"width_matches_painted_envelope": abs(measured_w-record["width_m"]) < 1e-6,
                  "depth_matches_painted_envelope": abs(measured_d-record["depth_m"]) < 1e-6,
                  "floor_slabs_match": g["authored_floor_slab_count"] == record["floors"],
                  "roof_topology_matches": len(roofs) == n and all(r["ridge_axes_local"] == [axis] for r in roofs),
                  "palette_alias_assignment_matches": inst["palette_id"] == record["roof_palette"] + "__" + record["masonry_palette"],
                  "explicit_reconstruction_label": inst["reconstruction_status"] == "protected_design_reconstructed_not_original_mesh"}
        protected_checks.append({"id": bid, "pass": all(checks.values()), "checks": checks,
                                 "measured_width_depth_m": [round(measured_w, 6), round(measured_d, 6)],
                                 "actual_floor_slabs": g["authored_floor_slab_count"],
                                 "roof_part_count": len(roofs), "roof_axes": [r["ridge_axes_local"] for r in roofs],
                                 "palette_id": inst["palette_id"],
                                 "limit": "Alias assignment and reconstructed geometry verified; missing original r4 mesh/material bytes cannot be compared."})
    ord_ins = [i for i in scene["instances"] if scene["asset_specs"][i["asset_key"]]["family"] == "ordinary"]
    landmarks = [{"id": i["id"], "kind": scene["asset_specs"][i["asset_key"]]["kind"],
                  "asset_key": i["asset_key"], "roof_parts": inspections[i["asset_key"]]["roof_parts"],
                  "spire_profiles": inspections[i["asset_key"]]["spire_profiles"]}
                 for i in scene["instances"] if scene["asset_specs"][i["asset_key"]]["family"] == "landmark" and i["asset_key"] in inspections]
    changed_inputs = [k for k, v in fingerprints.items() if sha(root / v["path"]) != v["sha256"]]
    findings = [
        {"id": "era_labels_not_driving_geometry", "priority": "high", "status": "partial_implementation",
         "finding": "Weighted six-phase chronology labels are separate from geometry. All ordinary buildings in a district use one construction_era; the geometry cache does not depend on era_id. Era-sensitive dado/post/window authoring exists but is not bound to the sampled history.",
         "action": "Define an explicit chronology-to-construction-cue mapping and spatially place a limited rebuilding frontage, retaining surviving neighbors and protected records; do not force exact percentages."},
        {"id": "ordinary_roof_pitch_not_bound", "priority": "high", "status": "design_reconciliation_needed",
         "finding": f"All {len(below_ids)} measured nonprotected ordinary roofs lie below their district design range. Slopes are measured from persisted polygon geometry, not roof labels. Low total height, floor allocation and capped roof rise constrain the silhouette.",
         "action": "Review storey/roof/envelope allocation and target silhouettes together. District pitch ranges apply only to new ordinary roofs; do not silently raise protected buildings or landmarks to meet them."},
        {"id": "historical_features_unbound", "priority": "high", "status": "proposed_not_implemented",
         "finding": "All six canonical historical-feature records remain proposed with empty geometry_ids. An inherited lane bend is not evidence of a verified rebuilding seam, reused foundation or drain.",
         "action": "Bind a small number of reviewed physical features to actual asset/placement IDs and verify them before claiming visibly layered city history."},
        {"id": "terrain_hierarchy_deferred", "priority": "high", "status": "explicitly_unimplemented",
         "finding": "All building bases are Y=0. Castle 52 m and cathedral 28 m ground candidates, grade-dependent drainage and elevated wall-access routes are not realized.",
         "action": "Keep this labeled a flat exterior milestone. Future terrain requires connected road/threshold/bridge profiles and fresh traversal tests; candidate elevations are not fixed acceptance values."},
        {"id": "roof_and_frontage_grammar_narrower_than_rules", "priority": "medium", "status": "partial_implementation",
         "finding": "Only gable/twin-gable roofs are instantiated. Hipped, steep and shed roofs exist in the author but are unused; half_hip is unsupported. Hoist gables, stacked loading doors, masonry party walls, mixed-era repair seams and drainage are not implemented by the current ordinary author.",
         "action": "Select a few functionally motivated additions, such as a quay loading/hoist front or market party-wall seam, rather than randomly using every available form."},
        {"id": "palette_provenance_open", "priority": "medium", "status": "alias_match_only",
         "finding": "Protected palette aliases match the seven records and original common materials are available. Additional roof/stone hex tables are hardcoded in orchestration while canonical integration_status still lists r4 alias resolution as incomplete. Original r4 material identity cannot be established from missing meshes.",
         "action": "Document which color bindings are recovered evidence versus reconstructed art direction, resolve the remaining alias provenance, then update integration status truthfully."},
        {"id": "seed_and_clustering_contract_partial", "priority": "medium", "status": "not_implemented_as_declared",
         "finding": "Selection hashes stable building IDs, but does not combine city_brief.seed. Era/palette choices are independent ID hashes rather than spatially clustered fabric, age/exposure weathering or district-edge blending.",
         "action": "Use explicit bounded spatial/history selections where visual continuity matters; preserve already protected palettes and geometry."},
        {"id": "landmark_adjectives_need_geometric_review", "priority": "medium", "status": "measured_not_visually_reviewed",
         "finding": "Warehouse and town-hall sources call roofs steep, but their actual angles depend on broad source envelopes. See landmark_measurements; ordinary district pitch rules do not apply to these landmarks.",
         "action": "Review these silhouettes at city scale and amend geometry or descriptive claims, without substituting arbitrary pitch thresholds."},
    ]
    integrity_ok = not (resource_errors or spec_geometry_errors or changed_inputs) and set(scene_ids) == source_ids and len(scene_ids) == len(set(scene_ids)) and all(p["pass"] for p in protected_checks)
    return {
        "schema": "riverstone.history_geometry_audit.v1", "scope": "persisted_continuous_source_geometry_and_scene_bindings",
        "baseline_policy": "This audit binds the recovered r1 historical snapshot, not the evolving canonical city_history.json. R1 palettes, district pitch proposals and 1308-instance coverage are baseline observations, not permanent constraints on later authorized era/material changes or documented footprint consolidation.",
        "status": "source_integrity_pass_with_history_implementation_gaps" if integrity_ok else "source_integrity_requires_review",
        "source_integrity_pass": integrity_ok, "input_fingerprints": fingerprints, "inputs_changed_during_audit": changed_inputs,
        "method": {"roof_angles": "atan2(abs(dy), horizontal run) over nonvertical edges of actual roof extrusion polygons after rigid authoring transforms; shell top/bottom parallel segments deduplicated. Spire outer profile measured separately. No metadata-derived roof rise formula.",
                   "floors_and_style": "Count persisted structural_floor slabs and actual wall/door/window/flue/canopy operations. Geometric cues are evidence of source authoring, not visual approval or structural certification.",
                   "source_regeneration": "Reauthor each small continuous master in memory and compare full JSON; do not call any voxel compiler or renderer.",
                   "range_policy": "Report design differences; honor protected records, landmark scope and source-envelope precedence. Never demand exact random era proportions.",
                   "limits": ["No GUI or rendered visual-quality review", "No new compilation or sampled roof-fit measurement", "No structural, weatherproofing or historical authenticity certification", "Road/void collision and traversal correctness belong to existing dedicated evidence", "No claim that absent original r4 meshes are restored"]},
        "coverage": {"source_footprints": len(source_ids), "scene_instances": len(scene_ids), "unique_asset_specs": len(scene["asset_specs"]),
                     "persisted_masters_inspected": len(inspections), "ordinary_instances": len(ord_ins), "landmark_instances": len(landmarks),
                     "missing_source_ids": sorted(source_ids-set(scene_ids)), "extra_scene_ids": sorted(set(scene_ids)-source_ids),
                     "duplicate_scene_ids": sorted(k for k, n in Counter(scene_ids).items() if n > 1),
                     "plan_and_scene_asset_specs_equal": plan["asset_specs"] == scene["asset_specs"],
                     "history_source_hash_matches_scene": fingerprints["history"]["sha256"] == scene["sources"]["history_sha256"]},
        "integrity": {"resource_errors": resource_errors, "spec_geometry_errors": spec_geometry_errors,
                      "persisted_masters_differing_from_current_author": author_drift,
                      "note": "Author drift is reported separately from persisted-source integrity; do not assume regenerated output would be identical when this list is nonempty."},
        "summary": {"all_ordinary_pitch_range_degrees": span(a for i in ord_ins for a in (inspections.get(i["asset_key"], {}).get("main_roof_pitch_range_degrees") or [])),
                    "nonprotected_ordinary_below_proposed_pitch_range": len(below_ids), "ordinary_unmeasured_roof_ids": unmeasured_ids,
                    "protected_records_verified": sum(p["pass"] for p in protected_checks),
                    "ordinary_assets_shared_across_multiple_chronology_labels": sum(len(v) > 1 for k, v in by_asset_eras.items() if scene["asset_specs"][k]["family"] == "ordinary"),
                    "historical_features_with_geometry_binding": sum(bool(f.get("geometry_ids")) for f in history["historical_features"]),
                    "height_adjusted_instances": sum(bool(i["height_delta_m"]) for i in scene["instances"]),
                    "rear_annex_instances": sum(i["functional_role"] == "rear_workshop_or_store" for i in scene["instances"])},
        "findings": findings, "districts": districts, "protected_record_checks": protected_checks,
        "historical_features": history["historical_features"],
        "terrain": {"actual_building_base_y_m": sorted(set(i["position_m"][1] for i in scene["instances"])),
                    "source_district_ground_candidates_m": {d["id"]: d.get("ground_y_candidate_m") for d in layout["districts"]},
                    "infrastructure_terrain_record": scene.get("infrastructure", {}).get("terrain"),
                    "deferred_wall_access_segments": scene.get("infrastructure", {}).get("checks", {}).get("deferred_wall_access_segments")},
        "roof_grammar": {"supported_ordinary_forms": list(ordinary.ROOF_FORMS), "instantiated_form_counts": counts(scene["asset_specs"][i["asset_key"]]["roof_form"] for i in ord_ins)},
        "below_proposed_pitch_range_ids": below_ids, "landmark_measurements": landmarks, "asset_geometry": inspections,
    }


def self_test():
    base = {"components": [{"id": "roof", "parts": [{"metadata": {"source_category": "roof_surface"}}],
                            "operations": [{"id": "slope", "action": "paint", "shape": {"kind": "extrusion", "polygon": [[0, 0], [3, 3], [3, 2.5], [0, -.5]], "z_min": -2, "z_max": 2}}]}],
            "instances": [{"component": "roof", "id": "roof"}]}
    result = inspect_geometry(base)
    assert result["main_roof_pitch_range_degrees"] == [45.0, 45.0]
    base["instances"][0]["transform"] = {"basis": [[0, 0, 1], [0, 1, 0], [-1, 0, 0]], "translation": [10, 4, 3]}
    result = inspect_geometry(base)
    assert result["roof_parts"][0]["ridge_axes_local"] == ["x"]
    assert result["main_roof_pitch_range_degrees"] == [45.0, 45.0]
    assert transform([1, 2, 3], {"translation": [4, 5, 6]}, True) == [1, 2, 3]
    print("history_geometry_audit self-test: PASS (polygon pitch, rotated ridge, translation independence)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    report = audit(args.root.resolve())
    output = args.output or args.root / "world_city/runtime_city/evidence/history_geometry_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "status": report["status"], "coverage": report["coverage"], "summary": report["summary"], "integrity": report["integrity"]}, ensure_ascii=False))
    if not report["source_integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
