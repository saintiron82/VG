"""Low-memory source/contract and finite analytic witness tests. No compilation."""
from __future__ import annotations

import copy
import itertools
import json
import math
import resource
import sys

sys.dont_write_bytecode = True
import adapter as d

a, core = d.a, d.core


def evaluator(master, pitch):
    """Evaluate only requested continuous points using common source predicates.

    This is deliberately not a cell enumeration, mesh, or compile substitute.
    It mirrors source instance layering and cut selectors to supply witnesses.
    """
    inv = a.source_inventory(master)
    grouped = {}
    for c, i, op, t, b in inv:
        grouped.setdefault(i, []).append((c, op, t, core.prepare_shape(op["shape"], pitch)))
    cuts = [(cut, core.transform(cut.get("transform")), core.prepare_shape(cut["shape"], pitch))
            for cut in master.get("assembly_cuts", [])]

    def point(world, instance=None):
        layers = {}
        for i, rows in grouped.items():
            label = None
            for c, op, t, shape in rows:
                if not core.contains(shape, core.inverse(t, world)):
                    continue
                if op["action"] == "paint":
                    label = {"instance": i, "component": c, "part": op["part"],
                             "material": op["material"], "feature": op["id"]}
                elif label and core.selector_matches(op.get("selector", {}), label):
                    label = None
            if label:
                layers[i] = label
        for cut, t, shape in cuts:
            if core.contains(shape, core.inverse(t, world)):
                layers = {i: label for i, label in layers.items()
                          if not core.selector_matches(cut.get("selector", {}), label)}
        if instance is not None:
            return layers.get(instance)
        return list(layers.values())[-1] if layers else None
    return point


def assert_raises(call):
    try:
        call()
    except (AssertionError, ValueError, KeyError):
        return
    raise AssertionError("unsupported input was accepted")


def overlaps(a_box, b_box):
    return all(min(a_box["max"][j], b_box["max"][j]) >
               max(a_box["min"][j], b_box["min"][j]) + 1e-8 for j in range(3))


def main():
    rules, assets, all_windows = d.read_inputs()
    catalog = a.load(d.HERE / "generated/catalog.json")
    a.write(d.HERE / "generated/structural_qa.json", {"status": "pending", "reason": "Structural QA in progress.", "catalog_sha256": a.sha(d.HERE / "generated/catalog.json"), "compile_calls": 0})
    reports = []
    original_compile = core.compile_master
    def forbidden(*args, **kwargs):
        raise AssertionError("Compilation is not authorized in structural QA")
    core.compile_master = forbidden
    for item in catalog["assets"]:
        asset = assets[item["asset_key"]]
        source = a.load(d.ROOT / item["source_master_path"])
        master = a.load(d.ROOT / item["emitted_master_path"])
        contract = a.load(d.ROOT / item["replacement_contract_path"])
        render = a.load(d.ROOT / contract["source_render_path"])
        assert a.sha(d.ROOT / item["source_master_path"]) == item["source_sha256"]
        assert a.sha(d.ROOT / item["emitted_master_path"]) == item["emitted_master_sha256"]
        assert a.sha(d.ROOT / item["replacement_contract_path"]) == item["replacement_contract_sha256"]
        assert a.sha(d.ROOT / contract["source_render_path"]) == contract["source_render_sha256"]
        for key in source:
            if key not in ("id", "revision", "assembly_cuts", "provenance"):
                assert source[key] == master[key], "Changed preserved source field: " + key
        assert all(master["provenance"][k] == v for k, v in source["provenance"].items())
        prefix = len(source.get("assembly_cuts", []))
        assert master["assembly_cuts"][:prefix] == source.get("assembly_cuts", [])
        assert len(master["assembly_cuts"]) - prefix == 2 * item["window_count"]
        assert contract["entrances"] == asset["entrance_metadata"]
        assert contract["city_placement_ids"] == asset["placement_ids"]
        assert contract["activation"]["source_occupancy_unchanged"] is False
        assert contract["activation"]["new_empty_space_fill"] is False
        core.validate_master(master, rules["fine_pitch_m"])
        inv, lookup = d.source_context(source)
        before, after = evaluator(source, rules["fine_pitch_m"]), evaluator(master, rules["fine_pitch_m"])
        pane_witnesses, preserved_details, rejected = [], [], 0
        for w, patch in zip(all_windows[item["asset_key"]], contract["patches"]):
            glass, aperture, features, t, back, front = d.resolve_window(w, lookup, rules)
            cuts = [x for x in master["assembly_cuts"][prefix:] if x["id"] in patch["authored_cut_ids"]]
            assert cuts == d.make_cuts(w, glass, t, back, front, patch["id"])
            assert all(set(c["selector"]) == {"component", "instance", "part", "material", "feature"} for c in cuts)
            assert all(c["shape"]["kind"] == "box" for c in cuts)
            assert all(all(c["shape"]["min"][j] >= glass["shape"]["min"][j] and
                           c["shape"]["max"][j] <= glass["shape"]["max"][j] for j in range(3)) for c in cuts)
            assert math.isclose(front - back, rules["glass_thickness_m"], abs_tol=1e-12)
            found = None
            for fx, fy in itertools.product((.2, .35, .65, .8), (.4, .6)):
                p = [glass["shape"]["min"][j] + f * (glass["shape"]["max"][j] - glass["shape"]["min"][j])
                     for j, f in enumerate((fx, fy))]
                old_front = before(core.apply(t, p + [.01]), instance=w["instance"])
                if not old_front or old_front["instance"] != w["instance"] or old_front["feature"] != glass["id"]:
                    continue
                samples = {"retained_glass": (back + front) / 2,
                           "new_front_air": (front + min(0, glass["shape"]["max"][2])) / 2,
                           "rear_removed": (glass["shape"]["min"][2] + back) / 2}
                labels = {name: after(core.apply(t, p + [z]), instance=w["instance"]) for name, z in samples.items()}
                if labels["retained_glass"] == old_front and labels["new_front_air"] is None and labels["rear_removed"] is None:
                    global_labels = {name: after(core.apply(t, p + [z])) for name, z in samples.items()}
                    old_global = before(core.apply(t, p + [.01]))
                    visible = (old_global == old_front and global_labels["retained_glass"] == old_front and global_labels["new_front_air"] is None)
                    found = {"patch_id": patch["id"], "local_xy_m": p, "depth_witnesses_m": samples,
                             "source_glass_front_local_z_m": glass["shape"]["max"][2], "source_instance_labels": labels,
                             "global_labels": global_labels, "original_global_front_label": old_global,
                             "whole_master_recess_exposed_witness": visible,
                             "exposure_status": "exposed_witness_pass" if visible else "source_occlusion_retained_no_new_wall_cut"}
                    if visible:
                        break
            assert found, "No actual source glass/air analytic witness for " + patch["id"]
            pane_witnesses.append(found)
            for feature, op in features:
                s = op["shape"]
                p = [(s["min"][j] + s["max"][j]) / 2 for j in range(3)]
                p[2] = (max(0, s["min"][2]) + s["max"][2]) / 2
                world = core.apply(t, p)
                old, new = before(world, instance=w["instance"]), after(world, instance=w["instance"])
                assert old == new, "Changed existing frame/sill/mullion/shutter witness"
                assert old is not None, "Source detail witness unexpectedly absent"
                preserved_details.append({"patch_id": patch["id"], "operation": op["id"],
                                          "role": feature["role"], "world_m": world,
                                          "source_instance_label": old, "preserved": True,
                                          "global_before": before(world), "global_after": after(world),
                                          "global_label_changed_by_other_glass_trim": before(world) != after(world)})
            # Shapes, orientations, hashes and aperture eligibility fail closed.
            for mutate in (
                lambda q: q.update(source_profile="landmark_polygon_painted_panel"),
                lambda q: q.update(local_outward_sign=-1),
                lambda q: q.update(source_frame_is_filled_panel=True),
                lambda q: q["glass"].update(operation_sha256="0" * 64),
            ):
                bad = copy.deepcopy(w)
                mutate(bad)
                assert_raises(lambda: d.resolve_window(bad, lookup, rules))
                rejected += 1
        # Every proposed finite quad edit is tied to exact source bytes and
        # conserves source area. No material-wide suppression can enter the plan.
        assert contract["cache_quad_edits"] == a.cache_contract(render, contract["patches"])
        removed_area = 0
        for edit in contract["cache_quad_edits"]:
            q = render["groups"][edit["group_index"]]["quads"][edit["quad_index"]]
            assert q == edit["original_quad"] and core.digest(q) == edit["original_quad_sha256"]
            retained = sum(a.rect_area(a.quad_info(q)[4]) for q in edit["retained_quads"])
            assert abs(retained + edit["removed_area_m2"] - edit["original_area_m2"]) < 1e-7
            removed_area += edit["removed_area_m2"]
        pairs = [[p["id"], q["id"]] for p, q in itertools.combinations(contract["patches"], 2)
                 if overlaps(p["replacement_volume_master_m"], q["replacement_volume_master_m"])]
        roof_edits = [e for e in contract["cache_quad_edits"] if "slate" in e["material"] or "roof" in e["material"]]
        reports.append({"asset_key": item["asset_key"], "source_preservation": "pass",
                        "exact_common_master_validation": "pass", "source_component_count": len(source["components"]),
                        "source_instance_count": len(source["instances"]), "authored_targeted_cuts": 2 * item["window_count"],
                        "source_operation_count": sum(len(c["operations"]) for c in source["components"]),
                        "source_entry_cut_count": len(contract["preserved_source_entry_cuts"]),
                        "continuous_pane_witnesses": pane_witnesses, "preserved_detail_witnesses": preserved_details,
                        "whole_master_exposed_witnesses": sum(w["whole_master_recess_exposed_witness"] for w in pane_witnesses),
                        "source_occluded_patches": [w["patch_id"] for w in pane_witnesses if not w["whole_master_recess_exposed_witness"]],
                        "unsupported_input_rejections": rejected, "finite_quad_edit_count": len(contract["cache_quad_edits"]),
                        "removed_cache_area_m2": removed_area, "patch_overlap_pairs": pairs,
                        "roof_material_quad_edits": len(roof_edits), "compiled": False, "visual_review": "pending"})
    core.compile_master = original_compile
    assert all(a.sha(d.ROOT / p) == sha for p, sha in catalog["frozen_helpers"].items())
    assessment = a.load(d.HERE / "generated/extension_assessment.json")
    result = {"schema": "riverstone.existing_aperture.structural_qa.v1", "status": "pass_with_exposure_limits", "assets": reports,
              "catalog_sha256": a.sha(d.HERE / "generated/catalog.json"),
              "compile_calls": 0, "runtime_edits": 0, "source_shapes_cropped": False,
              "source_data_unchanged": True, "authored_occupancy_is_subtractive_revision": True,
              "remaining_source_contract_eligible_windows": assessment["source_contract_eligible_windows"] - sum(x["window_count"] for x in catalog["assets"]),
              "limits": "Continuous witnesses and structural/cache algebra only; fine occupied-cell, seam closure, visible mesh and global constraint QA remain pending.",
              "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    a.write(d.HERE / "generated/structural_qa.json", result)
    print(json.dumps({"status": result["status"], "assets": len(reports), "window_witnesses": sum(len(x["continuous_pane_witnesses"]) for x in reports),
                      "preserved_detail_witnesses": sum(len(x["preserved_detail_witnesses"]) for x in reports),
                      "whole_master_exposed_witnesses": sum(x["whole_master_exposed_witnesses"] for x in reports),
                      "source_occluded_patches": {x["asset_key"]: x["source_occluded_patches"] for x in reports if x["source_occluded_patches"]},
                      "negative_cases": sum(x["unsupported_input_rejections"] for x in reports),
                      "compile_calls": 0, "output_bytes": d.guard(rules), "max_rss_kib": result["max_rss_kib"]}, indent=2))


if __name__ == "__main__":
    main()
