"""Coordinate-only source revision candidate; no master or collider is written."""
import copy
import csv
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
a, core, ROOT, F = d.a, d.core, d.ROOT, d.FACILITY
KEY = "registered_cathedral_nave_aisles_transept"


def bbox(points):
    return {"min": [min(p[j] for p in points) for j in range(3)],
            "max": [max(p[j] for p in points) for j in range(3)]}


def overlap(x, y, eps=1e-7):
    return all(min(x["max"][j], y["max"][j]) - max(x["min"][j], y["min"][j]) > eps for j in range(3))


def interval_overlap(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0))


def main():
    contract = a.load(F / "generated" / (KEY + ".replacement.json.gz"))
    master_path = ROOT / contract["source_master_path"]
    source = a.load(master_path)
    source_sha = a.sha(master_path)
    ops = {o["id"]: o for c in source["components"] for o in c["operations"]}
    centers = [ops[f"aisle_window_-1_{i}_pane"]["transform"]["translation"][2] for i in range(8)]
    step = (centers[-1] - centers[0]) / (len(centers) - 1)
    shift = step / 2
    table, proposals, panes = [], [], []
    for i, z in enumerate(centers):
        table.append({"axis": i, "window_center_z_m": z, "source_buttress_center_z_m": z,
                      "candidate_center_z_m": z + shift, "delta_z_m": shift,
                      "relation": f"between windows {i} and {i + 1}" if i < 7 else "end bay after window 7; no new buttress",
                      "source_pane_blocked_width_m": .9, "candidate_pane_blocked_width_m": 0})
        for side in (-1, 1):
            pane = ops[f"aisle_window_{side}_{i}_pane"]
            poly = pane["shape"]["polygon"]
            panes.append({"id": pane["id"], "side": side,
                          "center_z_m": pane["transform"]["translation"][2],
                          "half_width_m": (max(v[0] for v in poly) - min(v[0] for v in poly)) / 2})
            for level in ("lower", "upper"):
                op = ops[f"buttress_{side}_{i}_{level}"]
                old = {k: copy.deepcopy(op["shape"][k]) for k in ("min", "max")}
                new = copy.deepcopy(old)
                for bound in ("min", "max"):
                    new[bound][2] += shift
                assert all(new[k][j] == old[k][j] for k in ("min", "max") for j in (0, 1))
                proposals.append({"operation": op["id"], "side": side, "level": level,
                                  "source_operation_sha256": core.digest(op), "source_bbox_m": old,
                                  "candidate_bbox_m": new, "delta_translation_m": [0, 0, shift],
                                  "material_unchanged": op["material"], "dimensions_unchanged": True})
    overlaps = []
    for pane in panes:
        z, h = pane["center_z_m"], pane["half_width_m"]
        before, after = [], []
        for prop in proposals:
            if prop["side"] != pane["side"] or prop["level"] != "lower":
                continue
            for key, target in (("source_bbox_m", before), ("candidate_bbox_m", after)):
                b = prop[key]
                width = interval_overlap(z - h, z + h, b["min"][2], b["max"][2])
                if width > 1e-7:
                    target.append({"operation": prop["operation"], "blocked_pane_width_m": width})
        overlaps.append({"pane": pane["id"], "before": before, "candidate": after})
    assert all(len(x["before"]) == 1 and not x["candidate"] for x in overlaps)
    entry = ops["nave_door_opening"]["shape"]
    entry_bbox = {k: entry[k] for k in ("min", "max")}
    entry_hits = {key: [p["operation"] for p in proposals if overlap(p[key], entry_bbox)]
                  for key in ("source_bbox_m", "candidate_bbox_m")}
    assert all(not x for x in entry_hits.values())

    # Use the actual tile binary sources rather than interpreting screenshot
    # stairs as an unverified bbox. All terrain faces in this neighborhood are
    # checked conservatively, including step-like risers of any material.
    index_path = ROOT / "world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json"
    index = a.load(index_path)
    placement = None
    for cell in ("2_-4", "2_-5", "2_-3", "3_-4", "3_-5", "3_-3"):
        tile = a.load(ROOT / index["tiles"][cell]["instances_path"])
        for instance in tile["common_instances"]:
            if instance["asset_key"] == KEY:
                placement = instance
    assert placement
    pos, yaw = placement["position_m"], placement["yaw_rad"]
    c, s = math.cos(yaw), math.sin(yaw)
    def local(p):
        x, y, z = [p[j] - pos[j] for j in range(3)]
        return [c * x - s * z, y, s * x + c * z]
    terrain_inputs, risers, hits, native_steps, flying = [], [], [], [], []
    face_count = 0
    within_neighborhood = 0
    for cell in ("2_-4", "2_-5", "2_-3", "3_-4", "3_-5", "3_-3"):
        metadata = index["tiles"][cell]
        path = ROOT / metadata["terrain_path"]
        assert a.sha(path) == metadata["terrain_sha256"]
        terrain_inputs.append({"cell": cell, "path": d.relative(path), "sha256": a.sha(path)})
        tile = a.load(ROOT / metadata["instances_path"])
        for inst in tile["common_instances"]:
            lp = local(inst["position_m"])
            if abs(lp[0]) > 60 or abs(lp[2]) > 60:
                continue
            if any(word in inst["id"].lower() + inst["asset_key"].lower() for word in ("stair", "step")):
                native_steps.append({"id": inst["id"], "asset_key": inst["asset_key"], "position_local_m": lp})
            if "cathedral_registered:flying_" in inst["id"]:
                flying.append({"id": inst["id"], "asset_key": inst["asset_key"], "position_local_m": lp,
                               "source_entry_unchanged": True})
        with path.open("rb") as f:
            ordinal = 0
            while block := f.read(88 * 4096):
                for values in struct.iter_unpack("<9d4I", block):
                    face_count += 1
                    ordinal += 1
                    verts = [local(values[j:j + 3]) for j in (0, 3, 6)]
                    b = bbox(verts)
                    if b["max"][0] < -55 or b["min"][0] > 55 or b["max"][2] < -55 or b["min"][2] > 55:
                        continue
                    within_neighborhood += 1
                    # A strict potential penetration requires a face to span
                    # the candidate interval on all axes. Flat ground y=0 is
                    # a permitted contact; no collision edits are proposed.
                    if b["max"][1] > 1e-7:
                        for prop in proposals:
                            for key in ("source_bbox_m", "candidate_bbox_m"):
                                if all(b["max"][j] > prop[key]["min"][j] + 1e-7 and
                                       b["min"][j] < prop[key]["max"][j] - 1e-7 for j in range(3)):
                                    hits.append({"phase": key, "operation": prop["operation"], "tile": cell,
                                                 "triangle_ordinal": ordinal - 1, "terrain_bbox_local_m": b,
                                                 "material": index["material_ids"][values[10]]})
                    dy = b["max"][1] - b["min"][1]
                    if .10 <= dy <= .60 and b["max"][1] <= 2:
                        risers.append({"bbox": b, "material": index["material_ids"][values[10]],
                                       "tile": cell, "triangle_ordinal": ordinal - 1})
    riser_bbox = bbox([v for r in risers for v in (r["bbox"]["min"], r["bbox"]["max"])]) if risers else None
    # These are conservative terrain/step candidates, not a claim that every
    # short riser is an authored staircase or that native semantics are complete.
    result = {"schema": "riverstone.cathedral.buttress_axis_candidate.v1", "status": "coordinate_proposal_only",
              "source_master_path": d.relative(master_path), "source_master_sha256": source_sha,
              "source_collision_render_path": contract["source_render_path"], "source_collision_sha256": a.sha(ROOT / contract["source_render_path"]),
              "candidate_rule": "Translate each original lower+upper buttress pair by +half one window bay along local Z; preserve X/Y, dimensions, material, IDs, count and every window.",
              "bay_pitch_m": step, "delta_z_m": shift, "axis_count_per_side": 8,
              "source_operation_count": 32, "proposed_operation_count": 32,
              "axis_table": table, "bbox_proposals": proposals,
              "pane_projection_overlap": overlaps,
              "all_original_panes_keep_exact_polygons_and_transforms": True,
              "candidate_pane_overlap_count": sum(bool(x["candidate"]) for x in overlaps),
              "candidate_clearance_from_nearest_surround_edge_m": shift - .45 - 1.0,
              "candidate_last_axis_outer_z_m": centers[-1] + shift + .45,
              "existing_aisle_front_z_m": 16.8,
              "entry_bbox_local_m": entry_bbox, "entry_bbox_overlap": entry_hits,
              "entry_z_separation_from_candidate_m": entry_bbox["min"][2] - (centers[-1] + shift + .45),
              "source_master_stair_operations": [o["id"] for o in ops.values() if any(w in o["id"].lower() for w in ("stair", "step"))],
              "terrain_check": {"index_path": d.relative(index_path), "index_sha256": a.sha(index_path),
                                "placement": placement, "tile_inputs": terrain_inputs, "scanned_faces": face_count,
                                "neighborhood_faces": within_neighborhood, "possible_penetration_bbox_hits": hits,
                                "step_like_riser_face_count": len(risers), "step_like_riser_union_bbox_local_m": riser_bbox,
                                "native_stair_named_instances_within_60m": native_steps,
                                "proof_scope": "Conservative 3D AABB test of every terrain triangle in six relevant actual-city tiles; source master contains no stair operations. Flat ground contact at local Y=0 is retained. Step-like riser classification is only a superset diagnostic, not semantic staircase identification."},
              "independent_flying_buttresses": flying,
              "activation_blockers": ["Source-shadow comparison and later parent approval required before writing any source revision.",
                                      "Independent flying buttresses at local z=-18,2,22 need contact/alignment review; their source geometry is not moved by this proposal.",
                                      "Retaining old collision while moving visual buttresses may leave invisible old protrusions and noncolliding new protrusions. This plan changes no collider and grants no activation approval.",
                                      "The transept still obscures some low aisle windows. Moving these buttresses alone does not promise every pane becomes externally visible.",
                                      "Structural load-path, whole-assembly contacts, native-object clearances, camera visibility and runtime mesh/physics tests remain unperformed."],
              "source_master_modified": False, "collision_modified": False, "compile_calls": 0, "integration_edits": 0,
              "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    assert source_sha == a.sha(master_path)
    a.write(HERE / "buttress_axis_candidate.json", result)
    with (HERE / "buttress_axis_coordinates.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    print(json.dumps({"axis_rows": len(table), "source_operations_not_changed": len(proposals),
                      "pane_overlap_before": sum(bool(x["before"]) for x in overlaps), "pane_overlap_candidate": 0,
                      "entry_overlap": entry_hits, "terrain_faces_scanned": face_count,
                      "terrain_bbox_hits": len(hits), "step_like_riser_faces": len(risers), "step_like_bbox": riser_bbox,
                      "native_steps": native_steps, "max_rss_kib": result["max_rss_kib"], "compile_calls": 0}, indent=2))
    assert sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file()) < 512 * 1024


if __name__ == "__main__":
    main()
