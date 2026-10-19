"""Lower the frozen complete house r2 authoring recipe to common master data.

Reads house sources; never calls its sampler/build/validators or writes house/.
Normalization includes geometry, hinge and connector anchors exactly once.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
COMMON = HERE.parent
PROJECT = COMMON.parent.parent
sys.path.insert(0, str(COMMON))
from core import SCHEMA, apply, compose, digest, transform
from legacy_adapters import lower_prism_operation

PROJECT_ROTATION = [[-1, 0, 0], [0, 1, 0], [0, 0, -1]]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def yaw_basis(degrees):
    if degrees % 90:
        raise ValueError("legacy house adapter currently expects quarter-turn source instances")
    return [
        [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
        [[-1, 0, 0], [0, 1, 0], [0, 0, -1]],
        [[0, 0, -1], [0, 1, 0], [1, 0, 0]],
    ][(degrees//90) % 4]


def load_authoring(source_dir):
    source_dir = Path(source_dir).resolve()
    master_path, recipe_path = source_dir/"house_master.json", source_dir/"generate_house.py"
    source = json.loads(master_path.read_text())
    if source.get("schema") != "riverstone.modular-house.master.v1" or source.get("revision") != 2:
        raise ValueError("adapter requires reviewed modular-house source revision 2")
    spec = importlib.util.spec_from_file_location("house_r2_authoring_recipe", recipe_path)
    recipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recipe)
    definitions, instances = recipe.make_design(source)
    return source, definitions, instances


def adapt(source, definitions, instances, source_files):
    coordinate = source["coordinate_system"]
    normalization = coordinate["source_to_project"]
    if (coordinate["source_front"] != "-Z" or coordinate["project_front"] != "+Z"
            or normalization["rotation_y_degrees"] != 180 or normalization["scale"] != 1
            or normalization["translation"] != [0, 0, 0]):
        raise ValueError("source coordinate contract changed; explicit adapter review required")
    root = transform({"basis": PROJECT_ROTATION})
    result = {
        "schema": SCHEMA, "id": source["id"], "revision": source["revision"],
        "axes": {"up": "+Y", "front": "+Z", "right": "+X"},
        "grid_origin": [0, 0, 0], "materials": copy.deepcopy(source["materials"]),
        "components": [], "instances": [], "assembly_cuts": [], "constraints": [],
        "provenance": {
            "source_design_hash": digest(source),
            "source_files": source_files,
            "adapter": "common/adapters/house_r2.py",
            "reference_provenance": copy.deepcopy(source["provenance"]),
            "source_of_geometry": "source JSON plus pinned make_design authoring recipe; no legacy sampling",
            "sampling_differences": [
                "Common boxes declare per-local-axis minimum one-cell thickness; legacy sampler retained any thin WORLD AABB axis for every non-cut primitive.",
                "Common beam/slope lower to polygon extrusion; legacy center boundary inclusion and epsilon differ.",
                "Source -Z assembly is normalized by a 180-degree root rotation to project +Z, including pivots and connector anchors.",
                "Common output composites final occupancy; legacy artifacts preserve independently meshed overlapping module layers."
            ],
        },
    }
    for name, definition in definitions.items():
        result["components"].append({
            "id": name,
            "parts": [{"id": "solid", "pivot": [0, 0, 0],
                       "metadata": {"source_category": definition["category"], "dynamic": bool(definition.get("dynamic"))}}],
            "operations": [lower_prism_operation(operation, f"operation_{index:04d}", "solid")
                           for index, operation in enumerate(definition["operations"])],
        })
    for instance in instances:
        original = transform({"translation": instance["origin"], "basis": yaw_basis(instance["yaw_degrees"])})
        item = {"id": instance["id"], "component": instance["module"],
                "transform": compose(root, original),
                "metadata": {key: copy.deepcopy(value) for key, value in instance.items()
                             if key not in ("id", "module", "origin", "yaw_degrees")}}
        # The source parent is a hinge declaration, not a geometry instance.
        # Preserve it as an external attachment, never fabricate a hierarchy node.
        result["instances"].append(item)

    roof_instances = [instance["id"] for instance in instances if definitions[instance["module"]]["category"] == "roof"]
    ch = source["chimney"]
    result["assembly_cuts"] = [{
        "id": "authored_cover_penetration", "selector": {"instance": roof_instances},
        "transform": root,
        "shape": {"kind": "box", "min": [ch["x"]-.015, 0, ch["z"]-.015],
                  "max": [ch["x"]+ch["width"]+.015, ch["cap_top"]+1, ch["z"]+ch["depth"]+.015]},
    }]
    categories = sorted({definition["category"] for definition in definitions.values()})
    for category in categories:
        result["constraints"].append({"id": f"category_{category}_present", "kind": "nonempty",
                                      "selector": {"component": [name for name, definition in definitions.items()
                                                                    if definition["category"] == category]}})
    static_ids = [instance["id"] for instance in instances if not instance.get("dynamic")]
    base = source["dimensions"]["foundation_height"]
    front = -source["dimensions"]["depth"]/2
    door = source["door"]
    result["constraints"].append({
        "id": "authored_entry_clearance", "kind": "empty_region", "selector": {"instance": static_ids},
        "transform": root,
        "shape": {"kind": "box", "min": [-door["minimum_clear_width"]/2, base, front-.35],
                  "max": [door["minimum_clear_width"]/2, base+door["minimum_clear_height"], front+.35]},
    })
    flue_center = [ch["x"]+ch["width"]/2, ch["z"]+ch["depth"]/2]
    flue_half = ch["flue_width"]/2
    result["constraints"].append({
        "id": "authored_flue_clearance", "kind": "empty_region", "selector": {}, "transform": root,
        "shape": {"kind": "box", "min": [flue_center[0]-flue_half, ch["bottom"]+.2, flue_center[1]-flue_half],
                  "max": [flue_center[0]+flue_half, ch["shaft_top"]-.01, flue_center[1]+flue_half]},
    })
    entrance = copy.deepcopy(source["exterior_interior_contract"])
    for field in ("threshold_world", "exterior_approach_world", "interior_arrival_anchor", "forward_into_house"):
        entrance[field] = apply(root, entrance[field])
    entrance["coordinate_space"] = "project_metres_after_single_root_normalization"
    result["extensions"] = {
        "source_coordinate_system": copy.deepcopy(coordinate),
        "canonical_dimensions": copy.deepcopy(source["dimensions"]),
        "entrance_contract": entrance,
        "rigid_joint_contracts": [{"id": "front_door_hinge", "child": "front_door_leaf", "part": "solid",
                                   "pivot_world": apply(root, [door["hinge_x"], base, door["hinge_z"]]),
                                   "axis_world": [0, 1, 0], "closed_degrees": 0, "open_degrees": door["open_degrees"],
                                   "execution": "metadata_only_no_physics_or_animation_created"}],
        "legacy_shape_count": sum(len(d["operations"]) for d in definitions.values()),
        "scope": {"interior": "NOT_BUILT", "physics": "NOT_INTEGRATED", "visual_review": "NOT_RUN"},
    }
    return result


def build(source_dir):
    source_dir = Path(source_dir).resolve()
    source, definitions, instances = load_authoring(source_dir)
    paths = [source_dir/"house_master.json", source_dir/"generate_house.py",
             COMMON/"legacy_adapters.py", Path(__file__)]
    source_files = [{"path": str(p.relative_to(PROJECT)), "sha256": sha(p)} for p in paths]
    return adapt(source, definitions, instances, source_files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=COMMON.parent/"house")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.source)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"components": len(result["components"]), "instances": len(result["instances"]),
                      "master_hash": digest(result)}, indent=2))
