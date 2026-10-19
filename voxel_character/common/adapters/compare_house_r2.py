"""Read-only numerical comparison of legacy RLE and common final occupancy.

Both sides are composited in the same instance order and normalized to +Z.
This does not establish visual equivalence or compare mesh topology/performance.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_legacy(folder):
    folder = Path(folder)
    manifest = json.loads((folder/"manifest.json").read_text())
    assembly = json.loads((folder/manifest["assembly"]).read_text())
    if manifest["source_hash"] != assembly["source_hash"]:
        raise ValueError("legacy assembly and manifest source revisions differ")
    if manifest["pitch_metres"] != .1 or manifest["world_scale"] != 1:
        raise ValueError("comparison is scoped to pitch 0.1 and world scale 1")
    if assembly["coordinate_system"]["source_to_project"]["rotation_y_degrees"] != 180:
        raise ValueError("legacy normalization changed")
    modules = {key: json.loads((folder/name).read_text()) for key, name in manifest["module_files"].items()}
    cells = {}
    for instance in assembly["instances"]:
        module = modules[instance["mesh_key"]]
        anchor = instance["grid_anchor"]
        for x, y, z, count, material in module["voxel_rle"]:
            role = module["material_order"][material]
            for zz in range(z, z+count):
                ix, iy, iz = x+anchor[0], y+anchor[1], zz+anchor[2]
                # A 180-degree rotation of a CELL maps i to -i-1, not -i.
                point = (-ix-1, iy, -iz-1)
                cells[point] = {"instance": instance["id"], "component": instance["module"], "material": role}
    files = [folder/"manifest.json", folder/manifest["assembly"], *[folder/name for name in manifest["module_files"].values()]]
    return manifest, assembly, cells, {str(p): sha(p) for p in files}


def bounds(cells, pitch):
    return [[min(p[i] for p in cells)*pitch, (max(p[i] for p in cells)+1)*pitch] for i in range(3)]


def metrics(old, new):
    a, b = set(old), set(new)
    common = a & b
    changed = [p for p in common if old[p]["material"] != new[p]["material"]]
    owner_changed = [p for p in common if old[p]["instance"] != new[p]["instance"]]
    return {"legacy_cells": len(a), "common_cells": len(b), "intersection": len(common),
            "removed_cells": len(a-b), "added_cells": len(b-a), "occupancy_iou": len(common)/len(a | b) if a | b else 1,
            "material_changes_on_shared_cells": len(changed),
            "instance_owner_changes_on_shared_cells": len(owner_changed),
            "same_occupancy_and_material": a == b and not changed,
            "material_change_pairs": [{"from": old_role, "to": new_role, "cells": count}
                                      for (old_role, new_role), count in Counter((old[p]["material"], new[p]["material"]) for p in changed).most_common()]}


def difference_groups(old, new, field):
    a, b = defaultdict(dict), defaultdict(dict)
    for point, cell in old.items():
        a[cell[field]][point] = cell
    for point, cell in new.items():
        b[cell[field]][point] = cell
    return {key: metrics(a[key], b[key]) for key in sorted(set(a) | set(b))}


def compare(legacy_folder, compiled_path, master_path):
    old_manifest, old_assembly, old, preserved = load_legacy(legacy_folder)
    compiled = json.loads(Path(compiled_path).read_text())
    master = json.loads(Path(master_path).read_text())
    canonical_master_hash = hashlib.sha256(json.dumps(master, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    if compiled["master_hash"] != canonical_master_hash:
        raise ValueError("compiled output does not belong to this common master")
    canonical_payload_hash = hashlib.sha256(json.dumps(compiled["cells"], sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    if compiled["payload_hash"] != canonical_payload_hash:
        raise ValueError("compiled payload hash does not match its cells")
    if old_manifest["source_hash"] != master["provenance"]["source_design_hash"]:
        raise ValueError("legacy and common output do not share the same source design revision")
    recipes = [item["sha256"] for item in master["provenance"]["source_files"] if Path(item["path"]).name == "generate_house.py"]
    if recipes != [old_manifest["generator_sha256"]]:
        raise ValueError("legacy and common authoring recipe hashes differ")
    if compiled["pitch"] != .1 or compiled["grid_origin"] != [0, 0, 0]:
        raise ValueError("common comparison expects pitch 0.1 and shared zero origin")
    instance_component = {i["id"]: i["component"] for i in compiled["instances"]}
    new = {tuple(row[:3]): {"instance": row[3], "component": instance_component[row[3]], "material": row[5]} for row in compiled["cells"]}
    if len(new) != len(compiled["cells"]):
        raise ValueError("compiled output contains duplicate occupied coordinates")
    component_category = {c["id"]: c["parts"][0]["metadata"]["source_category"] for c in master["components"]}
    old_categories, new_categories = defaultdict(dict), defaultdict(dict)
    for p, cell in old.items():
        old_categories[component_category[cell["component"]]][p] = cell
    for p, cell in new.items():
        new_categories[component_category[cell["component"]]][p] = cell
    old_ids = {i["id"] for i in old_assembly["instances"]}
    new_ids = set(instance_component)
    old_materials, new_materials = Counter(c["material"] for c in old.values()), Counter(c["material"] for c in new.values())
    core_file = Path(__file__).resolve().parents[1]/"core.py"
    all_files_unchanged = all(sha(Path(path)) == digest for path, digest in preserved.items())
    source_files_unchanged = all(sha(Path(__file__).resolve().parents[3]/item["path"]) == item["sha256"] for item in master["provenance"]["source_files"])
    def normalize(point):
        return [-point[0], point[1], -point[2]]
    joint_fields = ("id", "child", "pivot_world", "axis_world", "closed_degrees", "open_degrees")
    expected_joints = [{"id": j["id"], "child": j["child"], "pivot_world": normalize(j["pivot_world"]),
                        "axis_world": normalize(j["axis"]), "closed_degrees": j["closed_degrees"], "open_degrees": j["open_degrees"]}
                       for j in old_assembly["hinges"]]
    actual_joints = [{key: j.get(key) for key in joint_fields} for j in compiled["extensions"]["rigid_joint_contracts"]]
    entrance_fields = ("exterior_id", "interior_id", "portal_id", "interior_status", "threshold_world", "exterior_approach_world", "interior_arrival_anchor", "forward_into_house")
    expected_entrance = {key: old_assembly["entrance_contract"][key] for key in entrance_fields}
    for key in ("threshold_world", "exterior_approach_world", "interior_arrival_anchor", "forward_into_house"):
        expected_entrance[key] = normalize(expected_entrance[key])
    actual_entrance = {key: compiled["extensions"]["entrance_contract"].get(key) for key in entrance_fields}
    expected_attachments = {i["id"]: {"parent": i.get("parent"), "dynamic": bool(i.get("dynamic"))} for i in old_assembly["instances"]}
    actual_attachments = {i["id"]: {"parent": i.get("metadata", {}).get("parent"), "dynamic": bool(i.get("metadata", {}).get("dynamic"))} for i in compiled["instances"]}
    return {
        "scope": "complete authored exterior r2; pitch 0.1 only; numerical shadow comparison",
        "comparison_space": "+Y up, +Z front; legacy cells normalized exactly once",
        "source_design_hash": old_manifest["source_hash"],
        "common_master_hash": compiled["master_hash"], "common_payload_hash": compiled["payload_hash"],
        "compiled_file_sha256": sha(Path(compiled_path)), "master_file_sha256": sha(Path(master_path)),
        "common_compiler_hash_current": sha(core_file) == compiled["compiler_source_hash"],
        "legacy_files_unchanged_during_comparison": all_files_unchanged,
        "source_files_match_adapter_provenance": source_files_unchanged,
        "legacy_reference_hashes": preserved,
        "aggregate": metrics(old, new),
        "bounds_metres": {"legacy": bounds(old, .1), "common": bounds(new, .1)},
        "material_counts": {role: {"legacy": old_materials[role], "common": new_materials[role], "delta": new_materials[role]-old_materials[role]} for role in sorted(set(old_materials) | set(new_materials))},
        "by_category": {category: metrics(old_categories[category], new_categories[category]) for category in sorted(set(old_categories) | set(new_categories))},
        "by_component": difference_groups(old, new, "component"),
        "by_instance": difference_groups(old, new, "instance"),
        "by_material": difference_groups(old, new, "material"),
        "part_contract": {
            "legacy_instances": len(old_ids), "common_instances": len(new_ids),
            "missing_instances": sorted(old_ids-new_ids), "added_instances": sorted(new_ids-old_ids),
            "components": len(master["components"]), "source_operations": master["extensions"]["legacy_shape_count"],
            "material_table_equal": compiled["materials"] == old_assembly["materials"],
            "instance_component_mapping_equal": all(instance_component.get(i["id"]) == i["module"] for i in old_assembly["instances"]),
            "unbound_interior_preserved": compiled["extensions"]["entrance_contract"]["interior_status"] == "NOT_BUILT",
            "joint_contracts_equal_after_normalization": expected_joints == actual_joints,
            "entrance_contract_equal_after_normalization": expected_entrance == actual_entrance,
            "external_parent_and_dynamic_metadata_equal": expected_attachments == actual_attachments,
            "joint_contracts": compiled["extensions"]["rigid_joint_contracts"],
            "entrance_contract": compiled["extensions"]["entrance_contract"],
        },
        "common_structural_checks": compiled["constraints"], "common_structural_pass": compiled["valid"],
        "known_differences": master["provenance"]["sampling_differences"],
        "cause_assessment": [
            {"categories": ["floor_belt", "window"], "assessment": "likely minimum-thickness / exact-boundary cell selection differences", "evidence": "legacy thin-axis floor(centroid/pitch+eps) differs from symmetric local-axis expansion and common half-open boundaries", "status": "inference_from_algorithms_and_localized_diff_not_every_cell_traced"},
            {"categories": ["roof", "gable"], "assessment": "likely beam-to-polygon boundary and thin-feature retention differences", "evidence": "legacy beam predicate includes boundary and applies world-AABB thin-axis retention; common uses polygon extrusion and explicit shape minimums", "status": "inference_from_algorithms_and_localized_diff_not_every_cell_traced"},
            {"assessment": "overlap ownership can change when nearby boundary cells move", "evidence": "report includes instance_owner_changes_on_shared_cells and per-instance/category diffs", "status": "measured_ownership_difference_with_cause_not_individually_proven"}
        ],
        "interpretation_limits": [
            "Legacy voxel RLE is a prior sampled output, not independent exact high-detail 3D ground truth.",
            "The source images do not establish hidden surfaces or a unique exact 3D reconstruction; procedural source geometry remains the authored interpretation.",
            "IoU measures cell-set overlap at one pitch after normalization; it is not percentage visual fidelity or a visual acceptance result.",
            "Final occupancy composition hides overwritten instance cells; this report does not establish moving-part hidden geometry preservation.",
            "No triangulation, mesh sharing, rendering, animation playback, physical behavior or other pitch was compared."
        ],
        "visual_equivalence": "NOT_ASSESSED", "mesh_equivalence": "NOT_ASSESSED",
        "runtime_performance": "NOT_MEASURED", "physics_integration": "NOT_PERFORMED",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy_folder", type=Path)
    parser.add_argument("compiled", type=Path)
    parser.add_argument("master", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.legacy_folder, args.compiled, args.master)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"aggregate": result["aggregate"], "bounds_metres": result["bounds_metres"],
                      "common_structural_pass": result["common_structural_pass"]}, indent=2))
