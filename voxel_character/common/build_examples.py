"""Freeze two small real-source slices into common master DATA, without sampling.

These deliberately partial fixtures are not full house/fountain migrations.
Run only to review a new source revision; normal regeneration reads saved JSON.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

from legacy_adapters import lower_prism_operation, lower_rotational_operation

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent


def evidence(path):
    return {"path": str(path.relative_to(PROJECT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def header(asset_id, materials, source_files, scope):
    return {"schema": "riverstone.voxel.master.v1", "id": asset_id, "revision": 1,
            "axes": {"up": "+Y", "front": "+Z", "right": "+X"}, "grid_origin": [0, 0, 0],
            "materials": materials, "components": [], "instances": [], "assembly_cuts": [], "constraints": [],
            "provenance": {"source_files": [evidence(p) for p in source_files], "scope": scope,
                           "status": "partial_structural_fixture_not_visual_approval"}}


def make_prism_example():
    path = ROOT.parent / "house" / "generate_house.py"
    source_path = path.with_name("house_master.json")
    spec = importlib.util.spec_from_file_location("legacy_prism_authoring", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    source = json.loads(source_path.read_text())
    definitions, _ = module.make_design(source)  # Only source recipes, never sample/build.
    result = header("wall_window_slice", source["materials"], [source_path, path], "One original wall bay and its separate window; no house, roof, interior or door certification.")
    for key, name, at in (("panel", "wall_lower_window", [0, 0, 0]), ("insert", "window_front_lower", [1.2, .72, 0])):
        definition = definitions[name]
        result["components"].append({"id": key, "parts": [{"id": key, "pivot": [0, 0, 0]}], "operations": [lower_prism_operation(op, f"op_{i}", key) for i, op in enumerate(definition["operations"])]})
        result["instances"].append({"id": key, "component": key, "transform": {"translation": at}})
        result["constraints"].append({"id": f"{key}_present", "kind": "nonempty", "selector": {"instance": key}})
    result["constraints"].extend([
        {"id": "frame_contacts_panel", "kind": "touch", "a": {"instance": "panel"}, "b": {"instance": "insert", "material": "timber_light"}},
        {"id": "glass_present", "kind": "nonempty", "selector": {"material": "glass"}},
        {"id": "window_hole_clear_of_plaster", "kind": "empty_region", "selector": {"material": "plaster"}, "shape": {"kind": "box", "min": [.87, .73, -.13], "max": [1.53, 1.59, .13]}}
    ])
    return result


def make_rotational_example():
    source_path = ROOT.parent / "master" / "fountain_master.json"
    source = json.loads(source_path.read_text())
    result = header("basin_support_slice", source["palette"], [source_path], "Original base, basin, pedestal and basin water only. Spillways, tier jets, splashes and full fountain migration are deliberately absent.")
    selected = [op for op in source["operations"] if op["id"] in ("base", "basin", "basin_rim", "pedestal", "basin_water")]
    operations = [lowered for op in selected for lowered in lower_rotational_operation(op)]
    result["components"] = [{"id": "rotational_structure", "parts": source["parts"], "operations": operations}]
    result["instances"] = [{"id": "assembly", "component": "rotational_structure"}]
    result["constraints"] = [
        {"id": "water_present", "kind": "nonempty", "selector": {"part": "water"}},
        {"id": "structure_connected", "kind": "connected", "selector": {"part": "masonry"}},
        {"id": "bowl_supported", "kind": "touch", "a": {"feature": "base"}, "b": {"feature": "basin"}},
        {"id": "water_contacts_basin", "kind": "touch", "a": {"part": "water"}, "b": {"feature": "basin"}},
        {"id": "basin_space_open", "kind": "empty_region", "selector": {}, "shape": {"kind": "box", "min": [.8, .65, -.2], "max": [1.2, .8, .2]}}
    ]
    return result


if __name__ == "__main__":
    target = ROOT / "examples"
    target.mkdir(exist_ok=True)
    for name, data in (("wall_window.json", make_prism_example()), ("basin_support.json", make_rotational_example())):
        path = target/name
        with path.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(path.relative_to(PROJECT))
