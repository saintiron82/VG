"""Read-only source/fine/final cathedral window investigation. No compilation."""
import collections
import importlib.util
import json
import math
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import adapter as d

a, core, F, ROOT = d.a, d.core, d.FACILITY, d.ROOT
spec = importlib.util.spec_from_file_location("cathedral_readonly_stream", F / "composed_runtime/stream_render.py")
stream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stream)
KEY = "registered_cathedral_nave_aisles_transept"
Y = 8.025


def merged(intervals):
    out = []
    for lo, hi in sorted(intervals):
        if out and lo <= out[-1][1] + 1e-8:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def glass_intervals(quads, patch):
    intervals = []
    t = patch["local_to_master"]
    for material, q in quads:
        if material != "glass":
            continue
        local = [core.inverse(t, v) for v in q]
        lo = [min(v[j] for v in local) for j in range(3)]
        hi = [max(v[j] for v in local) for j in range(3)]
        if lo[1] <= Y < hi[1] and abs(lo[2] - hi[2]) < 1e-8 and -.24 < lo[2] < -.18:
            if hi[0] > -.8 and lo[0] < .8:
                intervals.append([max(-.8, lo[0]), min(.8, hi[0])])
    return merged(intervals)


def main():
    start = time.monotonic()
    contract = a.load(F / "generated" / (KEY + ".replacement.json.gz"))
    source = a.load(ROOT / contract["source_master_path"])
    generated_path = F / "generated" / (KEY + ".master.json.gz")
    generated = a.load(generated_path)
    manifest_path = F / "composed_runtime" / (KEY + ".r05.candidate.manifest.json")
    manifest = a.load(manifest_path)
    final_path = ROOT / manifest["render_path"]
    assert a.sha(final_path) == manifest["render_sha256"]
    source_ops = {op["id"]: op for c in source["components"] for op in c["operations"]}
    generated_ops = {op["id"]: op for c in generated["components"] for op in c["operations"]}
    aisles = [p for p in contract["patches"] if p["source_glass"]["operation"].startswith("aisle_window_")]
    near_path = ROOT / "world_city/concept_city_v3/playable_detail_r01/near_catalog.json"
    near = a.load(near_path)["assets"][KEY]
    assert near["render_path"] == manifest["render_path"] and near["sha256"] == manifest["render_sha256"]
    image_dir = F.parent / "evidence/cathedral_actual_r02"
    captures = []
    for view, mode in (("oblique", "after"), ("street", "after"), ("street", "before")):
        meta = a.load(image_dir / (view + "_" + mode + ".json"))
        captures.append({"view": view, "mode": mode, "image_path": d.relative(image_dir / (view + "_" + mode + ".png")),
                         "image_sha256": a.sha(image_dir / (view + "_" + mode + ".png")),
                         "direct_view_image_inspection": True, "capture_catalog_sha256": meta["near_catalog_sha256"],
                         "current_catalog_sha256": a.sha(near_path),
                         "current_catalog_hash_matches_capture": meta["near_catalog_sha256"] == a.sha(near_path),
                         "camera": meta["camera"], "active_asset_count": meta["world"].get("near_detail", {}).get("active_instances", 0)})
    # Bounded streaming pass: keep only X-normal faces intersecting one horizontal
    # line. No full render, occupancy reconstruction, mesh generation or images.
    section = []
    count = 0
    for material, q in stream.iter_quads(final_path):
        count += 1
        if all(abs(v[0] - q[0][0]) < 1e-8 for v in q):
            low_y, high_y = min(v[1] for v in q), max(v[1] for v in q)
            if low_y <= Y < high_y:
                section.append((material, q))
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < 192 * 1024
    rows = []
    for p in aisles:
        op = source_ops[p["source_glass"]["operation"]]
        name = op["id"].replace("_pane", "")
        surround = source_ops[name + "_surround"]
        old_mullion = source_ops[name + "_mullion"]
        new_glass = generated_ops[p["id"] + "_glass"]
        new_mullion = generated_ops[p["id"] + "_mullion"]
        assert op == generated_ops[op["id"]] and surround == generated_ops[surround["id"]]
        assert op["shape"]["polygon"] == new_glass["shape"]["polygon"]
        side, index = name.split("_")[-2:]
        buttress = source_ops["buttress_" + side + "_" + index + "_lower"]
        assert buttress == generated_ops[buttress["id"]]
        poly, outer = op["shape"]["polygon"], surround["shape"]["polygon"]
        width = max(v[0] for v in poly) - min(v[0] for v in poly)
        height = max(v[1] for v in poly) - min(v[1] for v in poly)
        fine_path = F / "compiled_active_r02" / KEY / (p["id"] + ".window.json.gz")
        fine = a.load(fine_path)
        fine_intervals = glass_intervals(((g["material"], q) for g in fine["groups"] for q in g["quads"]), p)
        final_intervals = glass_intervals(section, p)
        assert fine_intervals == final_intervals, "Final composition changed selected fine glass cross section"
        t = p["local_to_master"]
        world_z_center = t["translation"][2]
        # Frontmost normal rays reveal source buttress and transept occlusion.
        # Use global fine-grid Z centers that fall inside the source pane envelope.
        tangent_low, tangent_high = world_z_center - width / 2, world_z_center + width / 2
        rays = []
        for k in range(math.ceil(tangent_low / .05 - .5), math.ceil(tangent_high / .05 - .5)):
            z = (k + .5) * .05
            hits = [(q[0][0], material) for material, q in section
                    if min(v[2] for v in q) <= z < max(v[2] for v in q)]
            if hits:
                x, material = min(hits) if side == "-1" else max(hits)
                rays.append({"tangent_local_m": core.inverse(t, [t["translation"][0], Y, z])[0],
                             "frontmost_world_x_m": x, "material": material})
        lower_shape = buttress["shape"]
        overlap = min(tangent_high, lower_shape["max"][2]) - max(tangent_low, lower_shape["min"][2])
        rows.append({"patch_id": p["id"], "source_pane": op["id"],
                     "source_pane_width_m": width, "source_pane_height_m": height,
                     "source_pane_height_width_ratio": height / width,
                     "surround_outer_width_m": max(v[0] for v in outer) - min(v[0] for v in outer),
                     "surround_outer_height_m": max(v[1] for v in outer) - min(v[1] for v in outer),
                     "authored_polygon_exactly_preserved": True, "original_surround_exactly_preserved": True,
                     "original_mullion_width_m": old_mullion["shape"]["max"][0] - old_mullion["shape"]["min"][0],
                     "new_mullion_width_m": max(v[0] for v in new_mullion["shape"]["polygon"]) - min(v[0] for v in new_mullion["shape"]["polygon"]),
                     "buttress": {"id": buttress["id"], "source_shape": lower_shape,
                                  "source_operation_sha256": core.digest(buttress), "unchanged_in_generated_master": True,
                                  "pane_center_z_m": world_z_center,
                                  "buttress_center_z_m": (lower_shape["min"][2] + lower_shape["max"][2]) / 2,
                                  "pane_width_blocked_m": overlap, "analytic_side_lite_width_m": (width - overlap) / 2,
                                  "outward_projection_from_window_m": max(abs(v) for v in (lower_shape["min"][0], lower_shape["max"][0])) - abs(t["translation"][0])},
                     "section_y_m": Y, "compiled_fine_glass_intervals_local_m": fine_intervals,
                     "final_r05_glass_intervals_local_m": final_intervals,
                     "final_glass_front_total_width_m": sum(b - a for a, b in final_intervals),
                     "final_composition_preserves_fine_glass_section": True,
                     "normal_frontmost_rays": rays,
                     "normal_ray_material_counts": dict(collections.Counter(r["material"] for r in rays)),
                     "fine_window_path": d.relative(fine_path), "fine_window_sha256": a.sha(fine_path)})
    result = {
        "schema": "riverstone.cathedral.independent_window_profile_check.v1",
        "conclusion": "Source aisle panes are narrow lancets, but the slit appearance is primarily source lower buttresses centered on the same panes: 0.90 m of each 1.50 m pane is blocked. Fine authoring preserves the source polygon, reduces the mullion, and the final r05 section matches the fine windows; no pane-width loss from composition was found.",
        "visual_inspection": "Both requested after PNGs and street_before.png were opened with view_image. Both street views show narrow turquoise strips alongside deep stone piers. The after view has finer source profiles and recessed glass; the old coarse 0.5 m glass sampling can exaggerate individual strip widths. Oblique view shows tall buttresses and full-width upper lancets, consistent with lower buttress occlusion rather than a newly enlarged generic frame.",
        "captures": captures, "source_master_path": contract["source_master_path"], "source_master_sha256": a.sha(ROOT / contract["source_master_path"]),
        "generated_master_path": d.relative(generated_path), "generated_master_sha256": a.sha(generated_path),
        "final_render_path": d.relative(final_path), "final_render_sha256": a.sha(final_path),
        "runtime_catalog_matches_captured_catalog": all(x["current_catalog_hash_matches_capture"] for x in captures),
        "runtime_catalog_temporal_limit": "The current full catalog hash differs from the capture's hash. The current cathedral entry points to this exact r05 render; capture logs identify the cathedral and matching 94283568 geometry bytes, but no byte-identical captured catalog snapshot was found.",
        "current_runtime_render_matches_r05": True,
        "streamed_final_quads": count, "retained_section_quads": len(section), "aisle_windows": rows,
        "recommendation": "Treat wider-looking low windows as a separately approved source-layout/design correction. Review moving windows between buttresses or shifting buttress rhythm; do not silently widen frames, cut structural buttresses, or call this a render-only fix.",
        "limits": "One horizontal geometric cross-section and normal rays, plus direct screenshots. No exhaustive pixel-ray reconstruction or new rendering. Existing transept wall can additionally occlude some aisle windows.",
        "compile_calls": 0, "geometry_edits": 0, "runtime_edits": 0,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "elapsed_seconds": round(time.monotonic() - start, 3)}
    a.write(HERE / "report.json", result)
    assert sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file()) < 512 * 1024
    print(json.dumps({"aisle_windows_checked": len(rows), "final_section_matches_fine_windows": all(r["final_composition_preserves_fine_glass_section"] for r in rows),
                      "source_pane_width_m": rows[0]["source_pane_width_m"], "source_buttress_blocks_m": rows[0]["buttress"]["pane_width_blocked_m"],
                      "final_front_glass_width_m": sorted(set(round(r["final_glass_front_total_width_m"], 8) for r in rows)),
                      "streamed_quads": count, "section_quads": len(section), "max_rss_kib": result["max_rss_kib"],
                      "elapsed_seconds": result["elapsed_seconds"], "compile_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
