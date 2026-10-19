"""Compare coordinate proposals only; never writes/compiles an actual master."""
import copy
import itertools
import json
import math
from pathlib import Path
import resource
import struct
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import adapter as d
from propose_axes import bbox, overlap, interval_overlap
a, core, ROOT, F = d.a, d.core, d.ROOT, d.FACILITY
KEY = "registered_cathedral_nave_aisles_transept"


def shifted(box, dz):
    box = copy.deepcopy(box)
    for k in ("min", "max"):
        box[k][2] += dz
    return box


def padded_snapped(box, pad=.1):
    return {"min": [math.floor((v - pad) / .5 + 1e-8) * .5 for v in box["min"]],
            "max": [math.ceil((v + pad) / .5 - 1e-8) * .5 for v in box["max"]]}


def roi_cost(boxes):
    cells = set()
    for b in boxes:
        cells.update(itertools.product(*(range(round(b["min"][j] / .5), round(b["max"][j] / .5)) for j in range(3))))
    return {"region_count_before_union": len(boxes), "coarse_half_meter_union_cells": len(cells),
            "union_volume_m3": len(cells) * .125,
            "fine_005m_union_cell_domain": len(cells) * 1000,
            "kind": "Exact union of declared coarse-aligned processing boxes, not occupied cells/candidate visits or runtime prediction."}


def main():
    contract = a.load(F / "generated" / (KEY + ".replacement.json.gz"))
    source_path = ROOT / contract["source_master_path"]
    source = a.load(source_path)
    source_sha = a.sha(source_path)
    window_rules = a.load(F / "rules.v1.json")
    ops = {o["id"]: o for c in source["components"] for o in c["operations"]}
    axes = a.load(HERE / "buttress_axis_candidate.json")
    centers = [r["window_center_z_m"] for r in axes["axis_table"]]
    half = axes["delta_z_m"]
    simple = [z + half for z in centers]
    simple[4] += .10  # Explicit local adjustment: clear the transept front corner.
    exposed = [-24.6, (centers[0] + centers[1]) / 2, (centers[1] + centers[2]) / 2,
               -.10, (centers[5] + centers[6]) / 2, (centers[6] + centers[7]) / 2,
               13.55, 15.65]
    entry = {k: ops["nave_door_opening"]["shape"][k] for k in ("min", "max")}
    patches = [p for p in contract["patches"] if p["source_glass"]["operation"].startswith("aisle_window_")]
    source_windows = []
    for p in patches:
        name = p["source_glass"]["operation"].replace("_pane", "")
        side, number = map(int, name.split("_")[-2:])
        pane, frame = ops[name + "_pane"], ops[name + "_surround"]
        lo, hi = a.bounds(frame["shape"], core.transform(frame["transform"]))
        source_windows.append({"name": name, "side": side, "index": number,
                               "pane": pane, "frame": frame, "source_frame_bbox": {"min": lo, "max": hi},
                               "source_roi": p["replacement_volume_master_m"]})
    fly = []
    for x in axes["independent_flying_buttresses"]:
        p = x["position_local_m"]
        fly.append({"id": x["id"], "bbox": {"min": [p[0] - 6, -.5, p[2] - .5],
                                             "max": [p[0] + 6, 26, p[2] + .5]}})
    # This is an intentionally conservative common-render flying envelope.
    # It proves separation, but an intersection is only a contact-risk flag.
    old_structural = [p["source_bbox_m"] for p in axes["bbox_proposals"]]
    moved_structural = [p["candidate_bbox_m"] for p in axes["bbox_proposals"]]
    fly_aabb_contacts = {"original": sum(overlap(b, f["bbox"]) for b in old_structural for f in fly),
                         "buttress_move": sum(overlap(b, f["bbox"]) for b in moved_structural for f in fly)}
    # Pair lower and upper source supports into one processing ROI per axis,
    # for each old/new position, matching the moved-window ROI cost convention.
    a_boxes = []
    for side in (-1, 1):
        for i in range(8):
            matching = [p for p in axes["bbox_proposals"] if p["side"] == side and p["operation"].split("_")[-2] == str(i)]
            for k in ("source_bbox_m", "candidate_bbox_m"):
                b = bbox([v for p in matching for v in (p[k]["min"], p[k]["max"])])
                a_boxes.append(padded_snapped(b))
    results = []
    for name, target in (("B1_minimal_half_bay_corner_clearance", simple), ("B2_all_exposed_bay_layout", exposed)):
        rows, boxes = [], []
        for w in source_windows:
            z0, z1 = centers[w["index"]], target[w["index"]]
            dz = z1 - z0
            newframe = shifted(w["source_frame_bbox"], dz)
            original_pane = w["pane"]
            poly = original_pane["shape"]["polygon"]
            width = max(p[0] for p in poly) - min(p[0] for p in poly)
            pane_interval = [z1 - width / 2, z1 + width / 2]
            buttress_overlap = sum(interval_overlap(*pane_interval, b["source_bbox_m"]["min"][2], b["source_bbox_m"]["max"][2])
                                   for b in axes["bbox_proposals"] if b["side"] == w["side"] and b["level"] == "lower")
            transept_overlap = interval_overlap(*pane_interval, -12, -1.2)
            structural_side = "west" if w["side"] == -1 else "east"
            crossing = [key for key in ("transept_rear", "transept_front", "transept_" + structural_side)
                        if overlap(newframe, {b: ops[key]["shape"][b] for b in ("min", "max")})]
            flyhits = [f["id"] for f in fly if overlap(newframe, f["bbox"])]
            candidate_t = copy.deepcopy(w["frame"]["transform"])
            candidate_t["translation"][2] += dz
            candidate_roi, _ = a.patch_for({"local_to_master": candidate_t}, w["frame"]["shape"],
                                           window_rules, contract["source_pitch_m"], contract["grid_origin"])
            boxes += [w["source_roi"], candidate_roi]
            rows.append({"window": w["name"], "source_center_z_m": z0, "candidate_center_z_m": z1,
                         "delta_z_m": dz, "candidate_frame_bbox_m": newframe,
                         "new_authored_window_roi_m": candidate_roi,
                         "source_operations_to_relocate": [w["name"] + suffix for suffix in ("_surround", "_pane", "_mullion")],
                         "pane_polygon_and_dimensions_unchanged": True,
                         "projected_buttress_blocked_pane_width_m": buttress_overlap,
                         "projected_transept_blocked_pane_width_m": transept_overlap,
                         "transept_source_bbox_intersections": crossing,
                         "independent_flying_bbox_intersections": flyhits,
                         "entry_bbox_intersection": overlap(newframe, entry),
                         "aisle_end_clearance_rear_m": newframe["min"][2] - (-25.8),
                         "aisle_end_clearance_front_m": 16.8 - newframe["max"][2]})
        own_overlaps = []
        for p, q in itertools.combinations(rows, 2):
            if overlap(p["candidate_frame_bbox_m"], q["candidate_frame_bbox_m"]):
                own_overlaps.append([p["window"], q["window"]])
        result = {"candidate": name, "window_count": len(rows), "source_operation_transform_changes": 48,
                  "support_operations_changed": 0, "upper_clerestory_or_great_window_changes": 0,
                  "windows": rows, "own_frame_overlap_pairs": own_overlaps,
                  "buttress_occluded_panes": sum(r["projected_buttress_blocked_pane_width_m"] > 1e-7 for r in rows),
                  "transept_occluded_panes": sum(r["projected_transept_blocked_pane_width_m"] > 1e-7 for r in rows),
                  "transept_frame_bbox_hits": sum(bool(r["transept_source_bbox_intersections"]) for r in rows),
                  "independent_flying_frame_bbox_hits": sum(bool(r["independent_flying_bbox_intersections"]) for r in rows),
                  "entry_bbox_hits": sum(r["entry_bbox_intersection"] for r in rows), "roi_cost": roi_cost(boxes),
                  "walking_collision_impact": "No source support/collider relocation; changed window geometry is >=4.4776 m above local ground. Existing high window paint and wall are already solid in the collision reference."}
        # Recheck all neighborhood actual terrain faces against the prospective
        # frame boxes. Unlike volume/volume tests, flat faces inside a volume
        # count, while flat ground exactly on its base is merely contact.
        pos, yaw = axes["terrain_check"]["placement"]["position_m"], axes["terrain_check"]["placement"]["yaw_rad"]
        c, s = math.cos(yaw), math.sin(yaw)
        def local(v):
            x, y, z = [v[j] - pos[j] for j in range(3)]
            return [c * x - s * z, y, s * x + c * z]
        terrain_hits = []
        for source_tile in axes["terrain_check"]["tile_inputs"]:
            with (ROOT / source_tile["path"]).open("rb") as f:
                number = 0
                while block := f.read(88 * 4096):
                    for values in struct.iter_unpack("<9d4I", block):
                        b = bbox([local(values[j:j + 3]) for j in (0, 3, 6)])
                        if b["max"][1] > 4.4776:
                            for r in rows:
                                box = r["candidate_frame_bbox_m"]
                                if all(b["max"][j] > box["min"][j] + 1e-7 and b["min"][j] < box["max"][j] - 1e-7 for j in range(3)):
                                    terrain_hits.append({"window": r["window"], "tile": source_tile["cell"], "face": number})
                        number += 1
        result["all_terrain_face_bbox_hits"] = terrain_hits
        results.append(result)
    source_rebuild = [
        "Start a separately versioned source candidate from the original full cathedral master, whose masonry walls are solid and whose window surrounds/panes are painted source geometry.",
        "Relocate only the 16 lower-window source triples (surround, pane, mullion) by their proposed transform delta. Keep source shapes, glass dimensions, materials, upper windows, all buttresses, flying buttresses, entry cuts and placements exact.",
        "Re-run the existing exact-polygon window authoring against this relocated source data. Author the actual masonry/surround cavity only at each new window position, and create recessed pane, sill and mullion there.",
        "Do not reuse old lower-window cavity cuts or merely move an overlay. Old positions recover by re-evaluating the original full masonry with the relocated paint operations absent there; no arbitrary fill boxes are permitted.",
        "Compile only the finite union of old and new lower-window regions and replace old fine/coarse patches atomically. Reuse unchanged roof/support inputs only after boundary/hash checks. This is an explicit occupancy-changing source revision.",
        "Retain the existing source collider for this candidate review; no collision write is authorized. Since windows are high and supports remain fixed, this avoids the buttress option's ground-level invisible old projections. Later actual physics and visual review are still required."]
    out = {"schema": "riverstone.cathedral.source_relocation_comparison.v1", "status": "candidate_data_only_not_authorized_for_activation",
           "source_master_path": d.relative(source_path), "source_master_sha256": source_sha,
           "A_buttress_half_bay": {"source_operations_to_translate": 32, "lower_window_source_operations_to_translate": 0,
                                    "pane_buttress_overlap_after": 0, "unchanged_transept_pane_occlusion": "Four panes remain fully and two partially behind the transept in their original positions.",
                                    "independent_flying_envelope_contacts": fly_aabb_contacts, "roi_cost": roi_cost(a_boxes),
                                    "ground_collision_risk": "Existing protruding buttress colliders stay at old axes while new visual supports move. Not an internally consistent activation with collision unchanged."},
           "window_options": results, "rebuild_contract": source_rebuild,
           "recommendation": "Prefer B2 for a complete coherent low-window correction: keep the entire structural/collision rhythm and relocate only the 16 lower windows into actually exposed bays. It is a 16-window source-layout revision, with 48 transform-only source operation changes and no pane resizing. B1 is smaller layout motion but leaves four windows hidden by the transept, so it cannot be accepted as a complete correction.",
           "B2_layout_tradeoff": "Eight windows per side are retained. Three use the rear exposed bays; five use the front exposed section, including two existing-size windows in the long last-buttress-to-end-wall bay with 0.10 m frame separation. This rhythm change needs visual/source-shadow review.",
           "ROI_comparison_limits": "Window ROI union includes both abandoned and new positions. Fine-cell domain is a geometric work-size comparison; source candidate visits, seams, output quads, time and global constraints require a later coordinated estimate/compile.",
           "step_evidence": axes["terrain_check"]["step_like_riser_union_bbox_local_m"],
           "original_master_unchanged": a.sha(source_path) == source_sha, "original_collision_unchanged": True,
           "master_written": False, "compile_calls": 0, "runtime_edits": 0,
           "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    a.write(HERE / "window_vs_buttress_candidates.json", out)
    print(json.dumps({"A_roi": out["A_buttress_half_bay"]["roi_cost"], "A_flying_envelope_contacts": fly_aabb_contacts,
                      "B_options": [{k: v for k, v in r.items() if k != "windows"} for r in results],
                      "max_rss_kib": out["max_rss_kib"], "compile_calls": 0}, indent=2))
    assert sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file()) < 512 * 1024


if __name__ == "__main__":
    main()
