"""Data-driven exact-source rectangular-aperture authoring; never compiles.

Only this directory is writable. The frozen author helpers provide source
transforms, primitive bounds and finite cache-quad subtraction. Source component
operations are immutable; this revision adds target-specific assembly cuts only.
"""
from __future__ import annotations

import copy
from collections import Counter, defaultdict
import gzip
import importlib.util
import json
import math
from pathlib import Path
import resource
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FACILITY = HERE.parents[1]
ROOT = FACILITY.parents[4]
spec = importlib.util.spec_from_file_location("frozen_facility_author", FACILITY / "author.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
core = a.core


def relative(path):
    return str(Path(path).relative_to(ROOT))


def signed_permutation(t):
    b = core.transform(t)["basis"]
    return all(sum(abs(x) > 1e-8 for x in row) == 1 and
               all(abs(x) < 1e-8 or abs(abs(x) - 1) < 1e-8 for x in row) for row in b)


def read_inputs():
    rules = a.load(HERE / "rules.v1.json")
    audit = a.load(ROOT / rules["source_audit"])
    windows = defaultdict(list)
    with gzip.open(ROOT / rules["source_windows"], "rt") as stream:
        for line in stream:
            w = json.loads(line)
            windows[w["asset_key"]].append(w)
    return rules, {x["asset_key"]: x for x in audit["assets"]}, windows


def source_context(source):
    inv = a.source_inventory(source)
    return inv, {(c, i, o["id"]): (o, t, b) for c, i, o, t, b in inv}


def resolve_window(w, lookup, rules):
    """Bind raw source objects; never reconstruct from rounded audit bounds."""
    assert w["source_profile"] == rules["supported_profile"], "unsupported aperture profile"
    assert w["local_outward_sign"] == 1 and w["source_surface_coordinate_m"] == 0, "unsupported local surface orientation"
    assert not w["source_frame_is_filled_panel"], "filled panels require a different rule"
    glass, t, _ = lookup[(w["component"], w["instance"], w["glass"]["id"])]
    assert core.digest(glass) == w["glass"]["operation_sha256"], "glass source hash mismatch"
    aperture, at, _ = lookup[(w["component"], w["instance"], w["associated_aperture"]["id"])]
    assert core.digest(aperture) == w["associated_aperture"]["operation_sha256"], "aperture source hash mismatch"
    assert glass["action"] == "paint" and aperture["action"] == "cut"
    assert glass["shape"]["kind"] == aperture["shape"]["kind"] == "box"
    assert not glass["shape"].get("minimum_cells") and not aperture["shape"].get("minimum_cells")
    assert t == at and signed_permutation(t), "source frames must share a signed-permutation frame"
    assert all(abs(t["translation"][j] - w["local_to_master"]["translation"][j]) < 1e-7 for j in range(3)), "audit translation disagreement"
    assert all(abs(t["basis"][j][k] - w["local_to_master"]["basis"][j][k]) < 1e-7 for j in range(3) for k in range(3)), "audit basis disagreement"
    g, opening = glass["shape"], aperture["shape"]
    assert all(abs(g[k][j] - opening[k][j]) < 1e-8 for k in ("min", "max") for j in (0, 1)), "pane/aperture mismatch"
    back, front = -rules["glass_recess_m"] - rules["glass_thickness_m"], -rules["glass_recess_m"]
    assert g["min"][2] < back < front < g["max"][2]
    assert opening["min"][2] <= g["min"][2] and opening["max"][2] >= g["max"][2]
    features = []
    for f in w["associated_features"]:
        op, ft, _ = lookup[(w["component"], w["instance"], f["id"])]
        assert core.digest(op) == f["operation_sha256"]
        assert op["action"] == "paint" and op["shape"]["kind"] == "box" and ft == t
        assert f["role"] in ("window_frame_sill", "mullion", "shutter")
        features.append((f, op))
    assert sum(f["role"] == "window_frame_sill" for f, op in features) == 4
    return glass, aperture, features, t, back, front


def make_cuts(w, glass, t, back, front, stem):
    selector = {"component": w["component"], "instance": w["instance"],
                "part": glass["part"], "material": glass["material"], "feature": glass["id"]}
    rear, forward = copy.deepcopy(glass["shape"]), copy.deepcopy(glass["shape"])
    rear["max"][2], forward["min"][2] = back, front
    return [{"id": stem + "_glass_" + side, "selector": copy.deepcopy(selector),
             "shape": shape, "transform": copy.deepcopy(t)}
            for side, shape in (("rear_trim", rear), ("front_recess", forward))]


def patch_for(glass, aperture, features, t, render, rules):
    # Include the whole existing feature envelope and aperture. Fine compilation
    # must evaluate the complete authored master in this ROI, not window-only paint.
    shapes = [glass["shape"], aperture["shape"]] + [op["shape"] for f, op in features]
    lo = [min(s["min"][j] for s in shapes) - rules["patch_margin_m"] for j in range(3)]
    hi = [max(s["max"][j] for s in shapes) + rules["patch_margin_m"] for j in range(3)]
    low, high = a.bounds({"kind": "box", "min": lo, "max": hi}, t)
    pitch, origin, fine = render["pitch"], render["grid_origin"], rules["fine_pitch_m"]
    assert abs(pitch / fine - round(pitch / fine)) < 1e-8, "coarse/fine grids must nest"
    volume = {
        "min": [origin[j] + math.floor((low[j] - origin[j]) / pitch + 1e-8) * pitch for j in range(3)],
        "max": [origin[j] + math.ceil((high[j] - origin[j]) / pitch - 1e-8) * pitch for j in range(3)]}
    cells = {key: [round((v[j] - origin[j]) / fine) for j in range(3)] for key, v in volume.items()}
    return volume, cells


def normalized_signature(glass, aperture, features):
    center = [(glass["shape"]["min"][j] + glass["shape"]["max"][j]) / 2 for j in (0, 1)]
    def shifted(s):
        return {key: [round(v - (center[j] if j < 2 else 0), 8) for j, v in enumerate(s[key])]
                for key in ("min", "max")}
    shape = {"glass": shifted(glass["shape"]), "aperture": shifted(aperture["shape"]),
             "features": [{"role": f["role"], "material": op["material"], "box": shifted(op["shape"])}
                          for f, op in features]}
    return core.digest(shape), shape


def guard(rules):
    size = sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    assert size < rules["output_cap_bytes"], "owned directory output cap exceeded"
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < rules["memory_cap_mib"] * 1024
    return size


def author_asset(asset, rows, rules):
    key = asset["asset_key"]
    assert a.sha(ROOT / asset["source_master_path"]) == asset["source_sha256"]
    assert a.sha(ROOT / asset["render_path"]) == asset["render_sha256"]
    source, render = a.load(ROOT / asset["source_master_path"]), a.load(ROOT / asset["render_path"])
    assert source.get("grid_origin", [0, 0, 0]) == render["grid_origin"]
    inv, lookup = source_context(source)
    master, cuts, patches, signatures = copy.deepcopy(source), [], [], Counter()
    for n, w in enumerate(rows):
        glass, aperture, features, t, back, front = resolve_window(w, lookup, rules)
        stem = f"aperture_{n:03d}"
        new_cuts = make_cuts(w, glass, t, back, front, stem)
        cuts.extend(new_cuts)
        volume, cells = patch_for(glass, aperture, features, t, render, rules)
        sig, profile = normalized_signature(glass, aperture, features)
        signatures[sig] += 1
        patches.append({
            "id": stem, "source_glass": a.op_binding(w["component"], w["instance"], glass),
            "source_aperture": a.op_binding(w["component"], w["instance"], aperture),
            "source_features": [dict(a.op_binding(w["component"], w["instance"], op), role=f["role"])
                                for f, op in features],
            "local_to_master": copy.deepcopy(t), "source_profile": w["source_profile"],
            "normalized_profile_sha256": sig, "normalized_profile": profile,
            "source_glass_shape_local": copy.deepcopy(glass["shape"]),
            "source_aperture_shape_local": copy.deepcopy(aperture["shape"]),
            "source_glass_recess_m": w["source_glass_recess_m"],
            "new_glass_recess_m": rules["glass_recess_m"], "glass_thickness_m": rules["glass_thickness_m"],
            "retained_glass_local_z_interval_m": [back, front],
            "authored_cut_ids": [c["id"] for c in new_cuts],
            "replacement_volume_master_m": volume, "fine_cell_bounds": cells,
            "source_render_observation": w["glass"]["cache"]["status"],
            "source_protrusion_m": max(op["shape"]["max"][2] for f, op in features),
            "new_outward_protrusion_m": 0, "new_paint_operations": 0,
            "runtime_ready": False})
    assert len(cuts) == 2 * len(rows) and len(rows) > 0
    master["assembly_cuts"] = copy.deepcopy(source.get("assembly_cuts", [])) + cuts
    master["id"] = key + "__existing_aperture_recess_r01"
    master["revision"] = source["revision"] + 1
    master.setdefault("provenance", {})["existing_aperture_revision"] = {
        "source_master_path": asset["source_master_path"], "source_sha256": asset["source_sha256"],
        "rules_sha256": a.sha(HERE / "rules.v1.json"), "adapter_sha256": a.sha(__file__),
        "source_components_instances_operations_preserved": True,
        "unchanged_source_occupancy_claim": False,
        "geometry_revision": "Subtractive source-pane front/rear trim only; existing detail recovered at finer pitch.",
        "new_empty_space_fill": False, "source_envelope_growth_m": 0, "generated_with_ai": True}
    core.validate_master(master, rules["fine_pitch_m"])
    out = HERE / "generated" / (key + ".master.json.gz")
    a.write(out, master)
    edits = a.cache_contract(render, patches)
    protected = [{"source": a.op_binding(c, i, op), "shape": copy.deepcopy(op["shape"]),
                  "transform": copy.deepcopy(t), "selector": copy.deepcopy(op.get("selector", {}))}
                 for c, i, op, t, b in inv if op["action"] == "cut" and
                 any(word in op["id"].lower() for word in ("door", "entry", "portal", "passage", "loading_bay"))]
    contract = {
        "schema": "riverstone.facility_openings.replacement.v1", "adapter_schema": "riverstone.existing_aperture.adapter.v1",
        "asset_key": key, "source_master_path": asset["source_master_path"], "source_sha256": asset["source_sha256"],
        "source_render_path": asset["render_path"], "source_render_sha256": asset["render_sha256"],
        "authored_master_path": relative(out), "authored_master_sha256": a.sha(out),
        "source_pitch_m": render["pitch"], "fine_pitch_m": rules["fine_pitch_m"], "grid_origin": render["grid_origin"],
        "patches": patches, "cache_quad_edits": edits,
        "original_assembly_cuts": copy.deepcopy(source.get("assembly_cuts", [])),
        "protected_component_entry_cuts": [], "preserved_source_entry_cuts": protected,
        "protected_component_entry_cuts_note": "No new paint layer exists to mirror cuts into; all original entry cuts remain exact.",
        "entrances": copy.deepcopy(asset["entrance_metadata"]), "city_placement_ids": asset["placement_ids"],
        "activation": {
            "runtime_ready": False, "atomic": True, "whole_group_removal": False,
            "untouched_quads_byte_preserved": True, "collision_reference_changed": False,
            "source_envelope_growth_m": 0, "source_components_unchanged": True,
            "source_occupancy_unchanged": False, "new_empty_space_fill": False,
            "overlapping_patches": "Partition union into disjoint owned integer-cell regions or deduplicate exact final cells before meshing. Independent window shells are insufficient.",
            "fine_selection": "Compile the complete unmodified authored common master with bounded cell_bounds. Do not clip source shapes or discard intersecting components.",
            "coarse_grid_transition_seams": "Required before activation, against actual composed outside geometry including roof replacements.",
            "scope": "Finite window union only; preserve unrelated source quads and all entrances.",
            "pending": ["coordinated bounded fine compilation", "coarse/fine seam closure", "overlap ownership", "visible recessed glass", "whole composed boundary QA", "visual review", "global constraints"]}}
    cp = HERE / "generated" / (key + ".replacement.json.gz")
    a.write(cp, contract)
    return {"asset_key": key, "source_master_path": asset["source_master_path"], "source_sha256": asset["source_sha256"],
            "emitted_master_path": relative(out), "emitted_master_sha256": a.sha(out),
            "replacement_contract_path": relative(cp), "replacement_contract_sha256": a.sha(cp),
            "window_count": len(rows), "new_operations": 0, "bounded_source_cuts": len(cuts),
            "impacted_original_quads": len(edits), "city_placements": len(asset["placement_ids"]),
            "normalized_profile_repetition": dict(signatures), "runtime_ready": False}


def assess_extension(assets, windows, rules):
    result, unsupported = [], Counter()
    for key, rows in windows.items():
        selected = [w for w in rows if w["source_profile"] == rules["supported_profile"]]
        unsupported.update(w["source_profile"] for w in rows if w["source_profile"] != rules["supported_profile"])
        if not selected:
            continue
        asset = assets[key]
        assert a.sha(ROOT / asset["source_master_path"]) == asset["source_sha256"]
        source = a.load(ROOT / asset["source_master_path"])
        inv, lookup = source_context(source)
        shapes, failures = Counter(), []
        for w in selected:
            try:
                glass, aperture, features, t, back, front = resolve_window(w, lookup, rules)
                sig, profile = normalized_signature(glass, aperture, features)
                shapes[sig] += 1
            except (AssertionError, KeyError, ValueError) as exc:
                failures.append({"instance": w["instance"], "glass": w["glass"]["id"], "reason": str(exc) or type(exc).__name__})
        result.append({"asset_key": key, "family": asset["family"], "source_kind": asset["source_master_metadata_kind"],
                       "window_count": len(selected), "source_contract_eligible_windows": len(selected) - len(failures),
                       "normalized_profile_count": len(shapes), "profile_repetition": dict(shapes),
                       "source_hash_verified": True, "failures": failures,
                       "authored_in_this_batch": key in rules["asset_keys"],
                       "next_gate": "Per-asset source/render hash bindings, source entry overlap and patch ownership/roof composition QA; no automatic activation."})
    return {"schema": "riverstone.existing_aperture.extension_assessment.v1", "assets": result,
            "rectangular_assets": len(result), "rectangular_windows": sum(x["window_count"] for x in result),
            "source_contract_eligible_windows": sum(x["source_contract_eligible_windows"] for x in result),
            "remaining_unwritten_windows": sum(x["window_count"] for x in result if not x["authored_in_this_batch"]),
            "excluded_profiles": dict(unsupported), "compile_calls": 0,
            "unsupported_policy": "Polygon-painted and recovered-flat panels need their own exact-source cavity adapter; never assume a cut bay.",
            "source_style_policy": "Retain source-defined frame, sill, mullion and shutter geometry exactly. Absence is not permission to add them."}


def main():
    rules, assets, windows = read_inputs()
    assert rules["compile_authorized"] is False and rules["new_paint_allowed"] is False
    (HERE / "generated").mkdir(exist_ok=True)
    a.write(HERE / "generated/structural_qa.json", {"status": "pending", "reason": "Authoring inputs regenerated; rerun structural QA.", "compile_calls": 0})
    frozen = {relative(p): a.sha(p) for p in (FACILITY / "author.py", Path(core.__file__))}
    catalog = [author_asset(assets[key], windows[key], rules) for key in rules["asset_keys"]]
    a.write(HERE / "generated" / "catalog.json", {
        "schema": "riverstone.facility_openings.catalog.v1", "assets": catalog,
        "full_compile": False, "runtime_activation": False, "compile_calls": 0,
        "compile_priority_asset_keys": rules["compile_priority_asset_keys"],
        "rules_sha256": a.sha(HERE / "rules.v1.json"), "frozen_helpers": frozen})
    a.write(HERE / "generated" / "extension_assessment.json", assess_extension(assets, windows, rules))
    assert all(a.sha(ROOT / p) == digest for p, digest in frozen.items())
    print(json.dumps({"assets": catalog, "owned_directory_bytes": guard(rules),
                      "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "compile_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
