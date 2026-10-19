"""Bounded lane rules -> ordinary common master data. No alternate sampler/mesher.

The only grid-aware authoring is a conservative boundary mask. It becomes plain
box cuts in the common master, so polygon edges and holes never leak full cells.
Regenerate the master when changing the requested pitch; do not resample its mask.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "voxel_character" / "common"))
from core import compile_master, digest, validate_master
from render_data import make_render_data

EPS = 1e-9
TONES = ("stone_warm", "stone_cool", "stone_light", "stone_dark")
AXES = {"up": "+Y", "front": "+Z", "right": "+X"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def rounded(n):
    return round(n, 9)


def polygon(region):
    if "rect" in region:
        require(len(region["rect"]) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in region["rect"]), "rectangle requires four finite XZ bounds")
        x0, z0, x1, z1 = region["rect"]
        require(x0 < x1 and z0 < z1, "rectangle bounds must increase")
        return [[x0, z0], [x1, z0], [x1, z1], [x0, z1]]
    points = region.get("polygon", [])
    require(len(points) >= 3 and all(len(p) == 2 for p in points), "polygon needs three XZ points")
    require(all(type(v) in (int, float) and math.isfinite(v) for p in points for v in p), "finite polygon points required")
    require(len({tuple(p) for p in points}) == len(points), "simple polygon vertices must be distinct; do not repeat the closing vertex")
    require(area(points) > EPS, "polygon area must be positive")
    def orient(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on_segment(a, b, p):
        return abs(orient(a,b,p)) < EPS and all(min(a[k],b[k])-EPS <= p[k] <= max(a[k],b[k])+EPS for k in range(2))
    edges = list(zip(points, points[1:]+points[:1]))
    for i, (a,b) in enumerate(edges):
        for j, (c,d) in enumerate(edges):
            if j <= i+1 or (i == 0 and j == len(edges)-1):
                continue
            crosses = orient(a,b,c)*orient(a,b,d) < 0 and orient(c,d,a)*orient(c,d,b) < 0
            touches = any((on_segment(a,b,c), on_segment(a,b,d), on_segment(c,d,a), on_segment(c,d,b)))
            require(not (crosses or touches), "polygon must be simple and non-self-intersecting")
    return copy.deepcopy(points)


def area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))) / 2 if len(points) >= 3 else 0


def clip_rect(points, rect):
    """Sutherland-Hodgman area clipping against a convex axis-aligned box."""
    result = list(points)
    for axis, edge, sign in ((0, rect[0], 1), (0, rect[2], -1), (1, rect[1], 1), (1, rect[3], -1)):
        previous = result
        result = []
        if not previous:
            break
        for a, b in zip(previous[-1:]+previous[:-1], previous):
            ai, bi = sign*(a[axis]-edge) >= -EPS, sign*(b[axis]-edge) >= -EPS
            if ai != bi:
                t = (edge-a[axis])/(b[axis]-a[axis])
                p = [a[k]+t*(b[k]-a[k]) for k in range(2)]
                p[axis] = edge
                result.append(p)
            if bi:
                result.append(b)
    return result


def bbox(points):
    return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]


def covered_rect(rect, outline, holes):
    size = (rect[2]-rect[0])*(rect[3]-rect[1])
    tolerance = max(1e-11, size*1e-7)
    return abs(area(clip_rect(outline, rect))-size) <= tolerance and all(area(clip_rect(h, rect)) <= tolerance for h in holes)


def rectangle_runs(cells):
    """Merge authoring-mask cell coordinates into bounded rectangular cuts."""
    by_row = {}
    for x, z in cells:
        by_row.setdefault(z, []).append(x)
    active, result = {}, []
    for z in sorted(by_row):
        xs = sorted(by_row[z])
        runs = []
        if xs:
            start = end = xs[0]
            for x in xs[1:]:
                if x == end+1:
                    end = x
                else:
                    runs.append((start, end+1)); start = end = x
            runs.append((start, end+1))
        fresh = {}
        for run in runs:
            prior = active.pop(run, None)
            if prior is not None and prior[3] == z:
                prior[3] = z+1
                fresh[run] = prior
            else:
                if prior is not None:
                    result.append(prior)
                fresh[run] = [run[0], z, run[1], z+1]
        result.extend(active.values())
        active = fresh
    result.extend(active.values())
    return sorted(result, key=lambda r: (r[1], r[0], r[3], r[2]))


def mask_rectangles(outline, holes, pitch):
    bounds = bbox(outline)
    nx = math.ceil((bounds[2]-bounds[0])/pitch-EPS)
    nz = math.ceil((bounds[3]-bounds[1])/pitch-EPS)
    require(nx*nz <= 400000, "bounded patch exceeds 400,000 planar cells; split the patch")
    # The common case is exact and does not scan individual fine cells.
    if not holes and outline == polygon({"rect": bounds}) and all(abs(n-round(n)) < EPS for n in ((bounds[2]-bounds[0])/pitch, (bounds[3]-bounds[1])/pitch)):
        return bounds, [], [[0, 0, nx, nz]]
    allowed, denied = [], []
    for iz in range(nz):
        for ix in range(nx):
            rect = [bounds[0]+ix*pitch, bounds[1]+iz*pitch, bounds[0]+(ix+1)*pitch, bounds[1]+(iz+1)*pitch]
            (allowed if covered_rect(rect, outline, holes) else denied).append((ix, iz))
    require(allowed, "bounds and exclusions leave no full cells")
    return bounds, rectangle_runs(denied), rectangle_runs(allowed)


def world_rect(rect, origin, pitch):
    return [rounded(origin[0]+rect[0]*pitch), rounded(origin[1]+rect[1]*pitch), rounded(origin[0]+rect[2]*pitch), rounded(origin[1]+rect[3]*pitch)]


def shape_box(rect, y0, y1):
    return {"kind": "box", "min": [rect[0], rounded(y0), rect[1]], "max": [rect[2], rounded(y1), rect[3]]}


def xz_shape(points, y0, y1):
    # Local XY maps to world XZ; extrusion +Z maps to world -Y.
    return {"shape": {"kind": "extrusion", "polygon": points, "z_min": rounded(-y1), "z_max": rounded(-y0)},
            "transform": {"basis": [[1, 0, 0], [0, 0, -1], [0, 1, 0]]}}


def octagon(rect, inset, corner):
    a, b, c, d = rect
    a += inset; b += inset; c -= inset; d -= inset
    if c-a <= EPS or d-b <= EPS:
        return []
    t = min(corner, (c-a)/4, (d-b)/4)
    return [[rounded(x), rounded(z)] for x, z in ((a+t,b),(c-t,b),(c,b+t),(c,d-t),(c-t,d),(a+t,d),(a,d-t),(a,b+t))]


def header(spec, suffix, origin, operations, parts):
    return {"schema": "riverstone.voxel.master.v1", "id": spec["id"]+"_"+suffix, "revision": spec["revision"],
            "axes": AXES, "grid_origin": origin, "materials": copy.deepcopy(spec["materials"]),
            "components": [{"id": "lane", "parts": [{"id": p, "pivot": [0,0,0]} for p in parts], "operations": operations}],
            "instances": [{"id": "lane", "component": "lane"}], "assembly_cuts": [],
            "constraints": [{"id": "nonempty", "kind": "nonempty", "selector": {}}],
            "extensions": {"lane": {"rules_hash": digest(spec), "bounded_sample_only": True}},
            "provenance": {"author": "author_lane.py", "input": "inputs/lane_rules.json", "geometry": "Ordinary common paint/cut operations; no alternate compiler or mesher."}}


def author(spec):
    """Pure source authoring; does not alter the input or existing city files."""
    spec = copy.deepcopy(spec)
    require(spec.get("schema") == "riverstone.lane.rules.v1", "unsupported lane rules")
    pitch = spec["pitch"]
    require(pitch in (0.0125, 0.025), "surface pitch must be 0.0125 or 0.025 m")
    require(spec["support_pitch"] == 1 and spec["support_thickness"] == 1, "support is an independent 1 m slab")
    require(spec["joint_depth"] == 0.025 and spec["top_y"] == 0, "sample top must be zero with 0.025 m recessed joints")
    require(spec["joint_width"] >= pitch, "joint width must resolve at the chosen pitch")
    require(spec["bevel_inset"] >= pitch and spec["corner_clip"] >= 0, "bevel inset must resolve at chosen pitch")
    require(all(type(v) in (int, float) and math.isfinite(v) and v > 2*spec["joint_width"]+2*spec["bevel_inset"] for key in ("stone_lengths", "stone_widths") for v in spec[key]), "stone dimensions must fit joints and bevel")
    outline = polygon(spec["bounds"])
    holes = [polygon(h) for h in spec.get("holes", [])]
    corridor = spec["walking_corridor"]["rect"]
    require(corridor[2]-corridor[0] >= 2-EPS, "reserve a continuous walking corridor at least 2 m wide")
    require(covered_rect(corridor, outline, holes), "walking corridor must be fully within bounds and clear of holes")
    bounds, denied, allowed = mask_rectangles(outline, holes, pitch)
    bed_top, bed_bottom = -spec["joint_depth"], -spec["joint_depth"]-pitch
    ops = [{"id": "joint_bed", "action": "paint", "part": "joint", "material": "joint", "shape": shape_box(bounds, bed_bottom, bed_top)}]
    rng = random.Random(spec["seed"])
    stones = []
    z, row, index = bounds[1], 0, 0
    half_joint = spec["joint_width"]/2
    while z < bounds[3]-EPS:
        width = rng.choice(spec["stone_widths"])
        z1 = min(z+width, bounds[3])
        # Shift the first bond in every other course, while keeping edge cuts bounded.
        x = bounds[0]
        first = True
        while x < bounds[2]-EPS:
            length = rng.choice(spec["stone_lengths"])
            if first and row % 2:
                length *= 0.65
            x1 = min(x+length, bounds[2])
            rect = [rounded(x+half_joint), rounded(z+half_joint), rounded(x1-half_joint), rounded(z1-half_joint)]
            base = octagon(rect, 0, spec["corner_clip"])
            cap = octagon(rect, spec["bevel_inset"], spec["corner_clip"])
            if base and cap and rect[2]-rect[0] > 2*spec["bevel_inset"]+pitch and rect[3]-rect[1] > 2*spec["bevel_inset"]+pitch:
                tone = TONES[(rng.randrange(12)+row//3) % 4]
                stone_id = f"stone_{index:04d}"
                ops.append({"id": stone_id+"_shoulder", "action": "paint", "part": "stone", "material": tone, **xz_shape(base, bed_bottom, -pitch)})
                ops.append({"id": stone_id+"_cap", "action": "paint", "part": "stone", "material": tone, **xz_shape(cap, -pitch, 0)})
                stones.append({"id": stone_id, "row": row, "rect": rect, "material": tone, "length": rounded(x1-x), "width": rounded(z1-z)})
                index += 1
            x = x1; first = False
        z = z1; row += 1
    for i, rect in enumerate(denied):
        ops.append({"id": f"boundary_mask_{i:04d}", "action": "cut", "part": "joint", "shape": shape_box(world_rect(rect, bounds[:2], pitch), bed_bottom, 0)})
    surface = header(spec, "surface", [bounds[0], 0, bounds[1]], ops, ["joint", "stone"])
    surface["extensions"]["lane"].update({"required_pitch": pitch, "top_y": 0, "joint_y": bed_top, "bed_bottom_y": bed_bottom, "boundary_rule": "Every occupied fine cell's XZ footprint is fully inside the outline and outside holes.", "stone_count": len(stones)})
    _, _, coarse_allowed = mask_rectangles(outline, holes, 1.0)
    support_ops = [{"id": f"support_{i:04d}", "action": "paint", "part": "support", "material": "support", "shape": shape_box(world_rect(rect, bounds[:2], 1.0), bed_bottom-1, bed_bottom)} for i, rect in enumerate(coarse_allowed)]
    support = header(spec, "support", [bounds[0], bed_bottom, bounds[1]], support_ops, ["support"])
    support["extensions"]["lane"].update({"required_pitch": 1.0, "top_y": bed_bottom, "role": "Coarse visual supporting slab, not fine collision."})
    collision = {"schema": "riverstone.lane.collision.v1", "unit": "m", "top_y": 0, "source_rules_hash": digest(spec),
                 "walking_corridor": copy.deepcopy(spec["walking_corridor"]), "outline": outline, "holes": holes,
                 "surface_collision": False, "boxes": [{"id": f"flat_support_{i:04d}", "min": [r[0], -1, r[1]], "max": [r[2], 0, r[3]]} for i, grid in enumerate(allowed) for r in [world_rect(grid, bounds[:2], pitch)]],
                 "note": "Use these flat continuous supports for walking; do not generate collision from fine stone quads. All boxes share Y=0, so joints and bevels cannot snag feet. Holes are excluded conservatively. Default rectangular patch has exactly one box."}
    validate_master(surface, pitch); validate_master(support, 1.0)
    return {"surface": surface, "support": support, "collision": collision, "stones": stones, "bounds": bounds, "rules_hash": digest(spec)}


def json_bytes(data):
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)+"\n").encode()


def save_new_or_identical(path, data):
    if path.exists():
        require(path.read_bytes() == data, f"refusing to overwrite changed file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def build(rules_path, destination):
    spec = json.loads(rules_path.read_text())
    require(spec["budgets"]["max_artifact_bytes"] <= 20000000, "hard artifact cap is 20 MB")
    before = rules_path.read_bytes()
    bundle = author(spec)
    artifacts = {"source/lane_surface.master.json": json_bytes(bundle["surface"]),
                 "source/lane_support.master.json": json_bytes(bundle["support"]),
                 "source/stone_layout.json": json_bytes(bundle["stones"]),
                 "generated/lane_collision.json": json_bytes(bundle["collision"])}
    stats = {}
    for name, pitch in (("surface", spec["pitch"]), ("support", 1.0)):
        master = bundle[name]
        original_hash = digest(master)
        compiled = compile_master(master, {"pitch": pitch}, max_candidate_cells=spec["budgets"]["max_candidate_cells"], max_output_cells=spec["budgets"]["max_output_cells"])
        require(compiled["valid"], "common compiler constraints failed")
        require(digest(master) == original_hash, "common compile changed master")
        render = make_render_data(compiled)
        artifacts[f"generated/lane_{name}.compiled.json.gz"] = gzip.compress(json_bytes(compiled), compresslevel=9, mtime=0)
        artifacts[f"generated/lane_{name}.render.json"] = json_bytes(render)
        stats[name] = {"pitch": pitch, "cells": len(compiled["cells"]), "candidate_cells": compiled["candidate_cells"], "quads": render["quad_count"], "bounds": render["bounds"], "master_hash": compiled["master_hash"], "payload_hash": compiled["payload_hash"], "valid": compiled["valid"]}
        del compiled, render
    require(rules_path.read_bytes() == before, "input rules changed during build")
    report = {"schema": "riverstone.lane.build.v1", "rules_hash": bundle["rules_hash"], "stone_count": len(bundle["stones"]), "walking_corridor": spec["walking_corridor"], "collision_boxes": len(bundle["collision"]["boxes"]), "input_unchanged": True, "common_compile_source_immutable": True, "stats": stats,
              "files": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in artifacts.items()},
              "scope": "Bounded house-front near-detail sample only, X[-5,5] Z[7,12] by default. No full-city terrain or runtime integration. Fine render is not collision."}
    artifacts["generated/build_report.json"] = json_bytes(report)
    total = sum(len(data) for data in artifacts.values())
    require(total <= spec["budgets"]["max_artifact_bytes"], f"artifact budget exceeded: {total}")
    for name, data in artifacts.items():
        save_new_or_identical(destination/name, data)
    print(json.dumps({"artifact_bytes": total, "stone_count": len(bundle["stones"]), "stats": stats}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, default=HERE/"inputs/lane_rules.json")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    build(args.rules, args.output)
