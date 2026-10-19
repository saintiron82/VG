"""Read-only multiview evidence gates. Never an automatic art/coverage judge.

This validator checks supplied evidence and existing common occupancy. It does
not infer unseen anatomy, execute generators, remesh, or certify truthful human
annotations. See docs/voxel_asset_multiview/README_KO.md for the trust boundary.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

SCHEMA = "riverstone.asset.multiview_contract.v1"
VIEWS = {"front": 0.0, "side": 90.0, "back": 180.0}
COMPLEX = {"complex_character", "complex_hair", "complex_clothing"}
DIMENSIONAL = {"standard_component", "parametric_building"}
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_CELLS = 200_000
MAX_ARTIFACTS = 128
MAX_TOTAL_BYTES = 256 * 1024 * 1024


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def vec(value, n=3):
    return isinstance(value, list) and len(value) == n and all(finite(x) for x in value)


class ContractError(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(detail)


def require(ok, code, detail):
    if not ok:
        raise ContractError(code, detail)


def close(a, b, tolerance=1e-6):
    return finite(a) and finite(b) and abs(a-b) <= tolerance


def read_json(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        data = stream.read(MAX_JSON_BYTES + 1)
    require(len(data) <= MAX_JSON_BYTES, "json_budget", f"JSON exceeds {MAX_JSON_BYTES} decoded bytes")
    return json.loads(data, parse_constant=lambda text: (_ for _ in ()).throw(
        ContractError("nonfinite_json", f"Forbidden JSON number {text}")))


def png_size(path):
    # Render evidence is deliberately PNG-only in v1. Reference images may use
    # other formats; their pixel dimensions remain declared in calibration.
    require(path.stat().st_size <= 32*1024*1024, "render_image_budget", "PNG exceeds 32 MiB")
    data = path.read_bytes()
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "render_image_format", "Model render evidence must be PNG")
    offset, dimensions, compressed, ended = 8, None, bytearray(), False
    while offset+12 <= len(data):
        size = struct.unpack(">I", data[offset:offset+4])[0]
        kind = data[offset+4:offset+8]
        require(offset+12+size <= len(data), "render_image_format", "Truncated PNG chunk")
        payload = data[offset+8:offset+8+size]
        crc = struct.unpack(">I", data[offset+8+size:offset+12+size])[0]
        require(zlib.crc32(kind+payload)&0xffffffff == crc, "render_image_format", "PNG checksum mismatch")
        if kind == b"IHDR":
            require(dimensions is None and offset == 8 and size == 13, "render_image_format", "Invalid PNG header")
            w,h,bits,color,compression,filters,interlace = struct.unpack(">IIBBBBB", payload)
            require(0 < w <= 4096 and 0 < h <= 4096 and bits == 8 and color in (2,6) and
                    compression == filters == interlace == 0, "render_image_format", "v1 requires bounded noninterlaced 8-bit RGB/RGBA PNG")
            dimensions, row_bytes = [w,h], w*(3 if color == 2 else 4)+1
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            require(size == 0 and offset+12 == len(data), "render_image_format", "Invalid PNG ending")
            ended = True
            break
        offset += 12+size
    require(dimensions and compressed and ended, "render_image_format", "Incomplete render PNG")
    decoder = zlib.decompressobj()
    decoded = decoder.decompress(compressed, dimensions[1]*row_bytes+1)
    require(decoder.eof and len(decoded) == dimensions[1]*row_bytes and not decoder.unused_data and
            all(decoded[i*row_bytes] <= 4 for i in range(dimensions[1])),
            "render_image_format", "PNG pixel stream is incomplete or has invalid filters")
    return dimensions


class Artifacts:
    def __init__(self, rows, root):
        require(isinstance(rows, dict) and 0 < len(rows) <= MAX_ARTIFACTS,
                "artifacts", "A nonempty bounded artifact map is required")
        self.rows, self.root, self.paths = rows, Path(root).resolve(), {}
        total = 0
        for key, row in rows.items():
            require(isinstance(key, str) and isinstance(row, dict), "artifact_record", "Invalid artifact record")
            raw = row.get("path")
            require(isinstance(raw, str) and not Path(raw).is_absolute(), "artifact_path", f"{key}: repo-relative path required")
            path = (self.root / raw).resolve()
            require(path.is_relative_to(self.root) and ".." not in Path(raw).parts,
                    "artifact_path", f"{key}: escaping artifact path")
            require(path.is_file(), "artifact_missing", f"{key}: {raw}")
            total += path.stat().st_size
            require(total <= MAX_TOTAL_BYTES, "artifact_budget", "Artifact read budget exceeded; split validation explicitly")
            expected = row.get("sha256")
            require(isinstance(expected, str) and len(expected) == 64 and
                    all(c in "0123456789abcdef" for c in expected), "artifact_sha256", f"{key}: lowercase SHA-256 required")
            require(sha256_file(path) == expected, "artifact_hash_mismatch", f"{key}: {raw}")
            require(isinstance(row.get("kind"), str), "artifact_kind", f"{key}: kind required")
            self.paths[key] = path
        self.total_bytes = total

    def get(self, key, kind=None):
        require(key in self.paths, "artifact_reference", f"Unknown artifact id {key!r}")
        if kind:
            require(self.rows[key]["kind"] == kind, "artifact_kind", f"{key}: expected {kind}")
        return self.paths[key]

    def sha(self, key):
        self.get(key)
        return self.rows[key]["sha256"]

    def json(self, key, kind=None):
        value = read_json(self.get(key, kind))
        require(isinstance(value, dict), "json_object", f"{key}: object required")
        return value


def references(contract, artifacts):
    rows = contract.get("references")
    require(isinstance(rows, list) and len(rows) == 3, "reference_views", "Exactly front, side, back reference records required")
    seen, crops, observed, inferred = set(), set(), [], []
    alignments = []
    for row in rows:
        view, origin, ref = row.get("view"), row.get("origin"), row.get("artifact")
        require(view in VIEWS and view not in seen, "reference_views", "Duplicate/unknown reference view")
        seen.add(view)
        require(origin in {"observed", "generated_inference", "manual_inference"}, "reference_origin", "Explicit observation/inference label required")
        kind = {"observed": "observed_reference", "generated_inference": "generated_reference", "manual_inference": "manual_reference"}[origin]
        artifacts.get(ref, kind)
        crop = row.get("crop_px")
        require(isinstance(crop, list) and len(crop) == 4 and all(type(x) is int for x in crop)
                and min(crop[:2]) >= 0 and min(crop[2:]) > 0, "reference_crop", "Positive integer crop rectangle required")
        crop_key = (artifacts.sha(ref), tuple(crop))
        require(crop_key not in crops, "reference_duplicate_crop", "Same image/crop cannot stand for multiple views")
        crops.add(crop_key)
        if origin == "observed":
            observed.append(view)
            require(row.get("observation_record"), "observation_record", "Observed source needs acquisition/authorization provenance")
            proof = artifacts.json(row["observation_record"], "observation_record")
            require(proof.get("source_sha256") == artifacts.sha(ref) and proof.get("source_type") in
                    {"user_illustration", "photograph", "measured_drawing", "scan"}, "observation_record", "Invalid observed provenance binding")
        else:
            inferred.append(view)
            sources = row.get("source_refs", [])
            require(isinstance(sources, list) and sources, "inference_sources", "Inferred views need original observed source refs")
            for source in sources:
                artifacts.get(source, "observed_reference")
            proof = artifacts.json(row.get("generation_record"), "generation_record")
            require(proof.get("output_sha256") == artifacts.sha(ref) and
                    proof.get("source_sha256") == [artifacts.sha(s) for s in sources] and
                    proof.get("method") == origin and bool(proof.get("unobserved_surfaces")),
                    "inference_provenance", "Inference provenance must bind originals/output and disclose unseen surfaces")
        aligned = artifacts.json(row.get("alignment_record"), "calibration")
        require(aligned.get("schema") == "riverstone.multiview.calibration.v1" and
                aligned.get("reference_sha256") == artifacts.sha(ref) and aligned.get("view") == view and
                aligned.get("crop_px") == crop, "alignment_binding", "Calibration must bind exact reference crop and view")
        require(aligned.get("projection") == "orthographic_aligned" and aligned.get("unresolved_conflicts") == [],
                "alignment_unresolved", "Unmeasured/perspective/conflicting reference alignment is not ready")
        require(close(aligned.get("yaw_deg"), VIEWS[view]) and close(aligned.get("pitch_deg"), 0) and
                close(aligned.get("roll_deg"), 0), "reference_orientation", "Reference orientation must be front/right-side/back")
        ppm, foot, crown = aligned.get("pixels_per_m"), aligned.get("footline_px"), aligned.get("crown_px")
        height = contract["frame"]["asset_height_m"]
        require(finite(ppm) and ppm > 0 and finite(foot) and finite(crown) and 0 <= crown < foot <= crop[3]
                and close((foot-crown)/ppm, height, 1.0/ppm), "reference_scale", "Calibrated height/baseline must match declared physical scale within one pixel")
        alignments.append((ppm, foot, crop[2], crop[3]))
    require(seen == set(VIEWS), "reference_views", "All three reference views required")
    require(all(all(close(a, b) for a, b in zip(alignments[0], v)) for v in alignments),
            "reference_alignment", "Aligned crops must share scale, footline and canvas dimensions")
    return {"observed_views": sorted(observed), "inferred_views": sorted(inferred),
            "observed_three_view_coverage": len(observed) == 3,
            "note": "Artifact metadata labels are checked, not externally authenticated."}


def volume_profile(contract, artifacts):
    volume = contract.get("volume", {})
    require(volume.get("authoring_method") in {"section_loft", "curve_sweep", "mixed_section_curve"},
            "volume_method", "Complex shapes require authored section/curve volumes")
    source = volume.get("source_artifact")
    authoring = artifacts.json(source, "source_volume")
    profile = artifacts.json(volume.get("profile_artifact"), "volume_profile")
    require(profile.get("schema") == "riverstone.volume.profile.v1" and profile.get("source_sha256") == artifacts.sha(source),
            "volume_profile_binding", "Profile must bind source authoring artifact")
    parts = profile.get("parts")
    require(isinstance(parts, list) and 0 < len(parts) <= 256, "volume_parts", "Bounded nonempty part profiles required")
    diagnostics, ids = [], set()
    for part in parts:
        pid = part.get("id")
        require(isinstance(pid, str) and pid not in ids and part.get("source_pointer"), "volume_part", "Unique part id and authoring source pointer required")
        ids.add(pid)
        pointer = part["source_pointer"]
        require(isinstance(pointer, str) and pointer.startswith("/"), "volume_source_pointer", "An RFC6901 authoring pointer is required")
        target = authoring
        try:
            for token in pointer[1:].split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                target = target[int(token)] if isinstance(target, list) else target[token]
        except (KeyError, IndexError, TypeError, ValueError):
            raise ContractError("volume_source_pointer", f"Missing authoring source location {pointer}")
        require(isinstance(target, (dict, list)), "volume_source_pointer", "Source pointer must identify geometry data")
        mode = part.get("representation")
        if mode in {"section_loft", "surface_with_thickness"}:
            sections, step = part.get("sections"), part.get("max_station_step_m")
            require(isinstance(sections, list) and 3 <= len(sections) <= 4096 and finite(step) and step > 0,
                    "section_sampling", "At least three explicit ordered section samples and positive sampling step required")
            previous, depths = None, []
            for section in sections:
                station, width, depth = section.get("station_m"), section.get("width_m"), section.get("depth_m")
                require(finite(station) and finite(width) and finite(depth) and width > 0 and depth > 0 and
                        vec(section.get("center_xz_m"), 2), "section_volume", "Every section needs finite positive width/depth and finite centre")
                require(previous is None or 0 < station-previous <= step+1e-9,
                        "section_continuity", "Section stations out of order or exceed declared sampling gap")
                previous = station
                depths.append(depth)
            if mode == "surface_with_thickness":
                require(finite(part.get("thickness_m")) and part["thickness_m"] > 0,
                        "cloth_thickness", "Cloth must declare nonzero physical thickness")
            diagnostics.append({"part": pid, "representation": mode, "samples": len(sections),
                                "depth_min_m": min(depths), "depth_max_m": max(depths),
                                "max_adjacent_depth_change_m": max(abs(a-b) for a,b in zip(depths, depths[1:]))})
        elif mode == "curve_sweep":
            points, radii = part.get("points_m"), part.get("radii_m")
            require(isinstance(points, list) and 3 <= len(points) <= 4096 and all(vec(p) for p in points)
                    and isinstance(radii, list) and len(radii) == len(points) and all(finite(r) and r > 0 for r in radii),
                    "curve_volume", "Curves require finite 3D samples and positive radii")
            lengths = [math.dist(a,b) for a,b in zip(points, points[1:])]
            limit = part.get("max_sample_step_m")
            require(finite(limit) and limit > 0 and all(0 < x <= limit+1e-9 for x in lengths),
                    "curve_continuity", "Repeated/discontinuous curve samples")
            diagnostics.append({"part": pid, "representation": mode, "samples": len(points),
                                "radius_min_m": min(radii), "radius_max_m": max(radii)})
        else:
            raise ContractError("volume_representation", f"Unsupported evidence representation {mode!r}")
    return {"parts": diagnostics, "note": "Derived authoring profiles are evidence, not a replacement geometry engine or an anatomy score."}


def component_sizes(cells):
    remaining = set(cells)
    sizes = []
    while remaining:
        seed = remaining.pop()
        queue, count = deque([seed]), 1
        while queue:
            x,y,z = queue.popleft()
            for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                if q in remaining:
                    remaining.remove(q)
                    queue.append(q)
                    count += 1
        sizes.append(count)
    return sorted(sizes, reverse=True)


def check_mesh_boundary(mesh, points, material_at, pitch, origin):
    """Verify supplied greedy quads against occupied-cell boundaries, no remesh.

    A six-bit mask per occupied boundary cell prevents duplicated/missing faces
    without constructing a large global unit-face set. Work is <=6*cell_count.
    """
    masks = {}
    for p in points:
        mask = 0
        for axis in range(3):
            for positive in (0, 1):
                neighbour = list(p)
                neighbour[axis] += 1 if positive else -1
                if tuple(neighbour) not in points:
                    mask |= 1 << (2*axis+positive)
        if mask:
            masks[p] = mask
    count = 0
    for group in mesh["groups"]:
        for quad in group["quads"]:
            grid = [[(p[i]-origin[i])/pitch for i in range(3)] for p in quad]
            require(all(close(x, round(x)) for p in grid for x in p), "mesh_grid", "Quad vertex is not on the compiled grid")
            q = [[round(x) for x in p] for p in grid]
            a,b = [q[1][i]-q[0][i] for i in range(3)], [q[3][i]-q[0][i] for i in range(3)]
            aa,bb = [i for i in range(3) if a[i]], [i for i in range(3) if b[i]]
            require(len(aa)==len(bb)==1 and aa != bb and
                    q[2] == [q[0][i]+a[i]+b[i] for i in range(3)],
                    "mesh_rectangle", "Common greedy surfaces require nondegenerate axis-aligned rectangles")
            u,v = aa[0],bb[0]
            axis = next(i for i in range(3) if i not in (u,v))
            cross = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
            positive = int(cross[axis]>0)
            bit = 1 << (2*axis+positive)
            u0,u1 = min(p[u] for p in q),max(p[u] for p in q)
            v0,v1 = min(p[v] for p in q),max(p[v] for p in q)
            count += (u1-u0)*(v1-v0)
            require(count <= 6*len(points), "mesh_surface_budget", "Quad unit-face area exceeds occupancy boundary budget")
            for iu in range(u0,u1):
                for iv in range(v0,v1):
                    p = list(q[0]);p[u]=iu;p[v]=iv;p[axis]-=positive
                    key=tuple(p)
                    require(masks.get(key,0)&bit, "mesh_boundary", "Quad is duplicate, inward, internal or outside actual occupied boundary")
                    require(material_at[key] == group["material"], "mesh_material", "Quad material differs from occupied boundary cell")
                    masks[key] ^= bit
    require(not any(masks.values()), "mesh_missing_faces", "Common mesh omits occupied boundary faces")
    return count


def common_geometry(contract, artifacts, complex_asset):
    common = contract.get("common", {})
    master = artifacts.json(common.get("master"), "master")
    compiled = artifacts.json(common.get("compiled"), "compiled")
    mesh = artifacts.json(common.get("render_mesh"), "render_mesh")
    require(master.get("schema") == "riverstone.voxel.master.v1", "master_schema", "Native common master required")
    require(master.get("axes") == {"up":"+Y","front":"+Z","right":"+X"}, "master_frame", "Master axes must match the declared normalized frame")
    require(compiled.get("schema") == "riverstone.voxel.compiled.v1" and compiled.get("valid") is True,
            "compiled_schema", "Valid native common compiled occupancy required")
    require(compiled.get("master_hash") == digest(master), "master_binding", "Compiled master semantic hash mismatch")
    require(compiled.get("source_id") == master.get("id") and compiled.get("source_revision") == master.get("revision") and
            all(check.get("pass") is True for check in compiled.get("constraints", [])),
            "compiled_identity", "Source identity/revision or constraint results mismatch")
    compiler_sha = artifacts.sha(common.get("compiler_source"))
    artifacts.get(common["compiler_source"], "compiler_source")
    require(compiled.get("compiler_source_hash") == compiler_sha, "compiler_binding", "Compiler snapshot hash mismatch")
    require(compiled.get("global_constraints_evaluated", True) is not False and
            compiled.get("valid_scope", "full_asset") != "cell_bounds_only" and
            compiled.get("evaluation_scope", {}).get("kind") != "cell_bounds",
            "scoped_compile", "Partial cell_bounds result cannot satisfy the full-asset evidence gate")
    cells, pitch, origin = compiled.get("cells"), compiled.get("pitch"), compiled.get("grid_origin")
    require(isinstance(cells, list) and 0 < len(cells) <= MAX_CELLS and finite(pitch) and pitch > 0 and vec(origin),
            "compiled_budget", "Nonempty bounded cells, positive pitch and finite origin required")
    require(compiled.get("payload_hash") == digest(cells), "payload_binding", "Compiled occupancy hash mismatch")
    points, parts, levels, material_at = set(), defaultdict(set), defaultdict(list), {}
    materials = compiled.get("materials", {})
    for row in cells:
        require(isinstance(row, list) and len(row) == 7 and all(type(i) is int for i in row[:3]) and
                all(isinstance(i, str) for i in row[3:]) and row[5] in materials, "cell_row", "Malformed native cell row")
        xyz = tuple(row[:3])
        require(xyz not in points, "duplicate_cell", "Duplicate final occupancy coordinate")
        points.add(xyz)
        material_at[xyz] = row[5]
        parts[row[3]+":"+row[4]].add(xyz)
        levels[xyz[1]].append(xyz[2])
    require(mesh.get("schema") == "riverstone.voxel.render.v1" and mesh.get("master_hash") == compiled["master_hash"] and
            mesh.get("payload_hash") == compiled["payload_hash"] and mesh.get("cell_count") == len(cells),
            "mesh_binding", "Common render does not bind same master/occupancy")
    require(mesh.get("pitch") == pitch and mesh.get("grid_origin") == origin and
            mesh.get("materials") == materials, "mesh_frame", "Render pitch/origin/material table mismatch")
    provenance = mesh.get("provenance", {})
    require(provenance.get("compiler_source_hash") == compiler_sha and
            provenance.get("exporter_sha256") == artifacts.sha(common.get("exporter_source")) and
            provenance.get("mesher_sha256") == artifacts.sha(common.get("mesher_source")),
            "mesh_provenance", "Render exporter/mesher/compiler hashes mismatch")
    artifacts.get(common["exporter_source"], "exporter_source")
    artifacts.get(common["mesher_source"], "mesher_source")
    require(isinstance(mesh.get("groups"), list) and mesh["groups"] and mesh.get("quad_count", 0) > 0,
            "mesh_empty", "Actual common render quads required")
    actual_quads = 0
    for group in mesh["groups"]:
        require(group.get("material") in materials and isinstance(group.get("quads"), list), "mesh_group", "Unknown material or missing quads")
        for quad in group["quads"]:
            require(isinstance(quad, list) and len(quad) == 4 and all(vec(p) for p in quad), "mesh_quad", "Finite 3D quads required")
            actual_quads += 1
    require(actual_quads == mesh["quad_count"], "mesh_quad_count", "Quad count mismatch")
    unit_faces = check_mesh_boundary(mesh, points, material_at, pitch, origin)
    lo = [origin[i]+min(p[i] for p in points)*pitch for i in range(3)]
    hi = [origin[i]+(max(p[i] for p in points)+1)*pitch for i in range(3)]
    require(all(close(a,b) for a,b in zip(mesh.get("bounds", {}).get("min", []), lo)) and
            len(mesh.get("bounds", {}).get("min", [])) == 3 and
            all(close(a,b) for a,b in zip(mesh.get("bounds", {}).get("max", []), hi)) and
            len(mesh.get("bounds", {}).get("max", [])) == 3, "mesh_bounds", "Render bounds do not match actual occupancy")
    if complex_asset:
        require(len({p[2] for p in points}) > 1, "single_depth_layer", "A single Z layer cannot establish a complex volume")
    sizes = component_sizes(points)
    per_part = {key: component_sizes(value) for key,value in sorted(parts.items())}
    disposition = contract.get("volume", {}).get("continuity_disposition", {})
    if complex_asset:
        unresolved = [key for key, value in per_part.items() if len(value) > 1 and
                      not isinstance(disposition.get(key), str)]
        require(not unresolved and all(len(disposition.get(k, "").strip()) >= 12 for k,v in per_part.items() if len(v)>1),
                "continuity_unreviewed", "Disconnected parts require explicit reasons/review disposition: " + ", ".join(unresolved))
        require(len(sizes) == 1 or (isinstance(disposition.get("$assembly"), str) and
                len(disposition["$assembly"].strip()) >= 12), "assembly_continuity_unreviewed",
                "Disconnected assembly requires a separate $assembly explanation; separate accessories may be intentional")
    depth_profile = [{"y_index": y, "z_min_m": origin[2]+min(z)*pitch,
                      "z_max_m": origin[2]+(max(z)+1)*pitch,
                      "occupied_z_layers": len(set(z))} for y,z in sorted(levels.items())]
    return {"cell_count": len(cells), "pitch_m": pitch, "bounds_m": {"min": lo, "max": hi},
            "verified_mesh_boundary_unit_faces": unit_faces,
            "global_component_sizes": sizes, "part_component_sizes": per_part,
            "depth_profile": depth_profile,
            "note": "Six-neighbour continuity and depth are diagnostics, never an art/likeness/completeness score."}


def render_evidence(contract, artifacts, complex_asset):
    renders = contract.get("model_renders", [])
    require(isinstance(renders, list), "model_renders", "Render records must be an array")
    stages = ("authored_volume", "compiled_mesh") if complex_asset else ("compiled_mesh",)
    seen, cameras, reference_hashes = set(), [], {artifacts.sha(r["artifact"]) for r in contract.get("references", [])}
    for render in renders:
        stage, view = render.get("stage"), render.get("view")
        require(stage in stages and view in VIEWS and (stage, view) not in seen,
                "render_views", "Unknown/duplicate model render stage or orientation")
        seen.add((stage, view))
        image_id = render.get("image")
        image_path = artifacts.get(image_id, "model_render")
        require(artifacts.sha(image_id) not in reference_hashes, "reference_as_render", "Reference image bytes cannot count as a model render")
        record = artifacts.json(render.get("record"), "render_record")
        expected_input = contract["volume"]["source_artifact"] if stage == "authored_volume" else contract["common"]["render_mesh"]
        require(record.get("schema") == "riverstone.multiview.render_record.v1" and
                record.get("subject") == stage and record.get("view") == view and
                record.get("input_sha256") == artifacts.sha(expected_input) and
                record.get("image_sha256") == artifacts.sha(image_id), "render_binding", "Render record must bind stage, view, model and image")
        require(record.get("renderer_source_sha256") == artifacts.sha(render.get("renderer_source")) and
                bool(record.get("command")) and record.get("actual_geometry_render") is True,
                "render_execution_record", "Renderer source, command and actual geometry declaration required")
        artifacts.get(render["renderer_source"], "renderer_source")
        camera = record.get("camera", {})
        require(camera.get("projection") == "orthographic" and camera.get("frame_id") == contract["frame"]["id"] and
                close(camera.get("yaw_deg"), VIEWS[view]) and close(camera.get("pitch_deg"), 0) and close(camera.get("roll_deg"), 0),
                "render_orientation", "Locked orthographic front/right-side/back camera required")
        span, resolution = camera.get("vertical_span_m"), camera.get("resolution_px")
        require(finite(span) and span >= contract["frame"]["asset_height_m"] and
                isinstance(resolution, list) and len(resolution) == 2 and all(type(x) is int and x > 0 for x in resolution) and
                png_size(image_path) == resolution and vec(camera.get("target_m")), "render_scale", "PNG dimensions and camera physical scale must agree")
        require(camera.get("scale_source") == "locked_reference_frame" and
                close(camera["target_m"][1], contract["frame"]["asset_height_m"]/2) and
                close(camera["target_m"][0], 0) and close(camera["target_m"][2], 0),
                "render_auto_fit", "Model-bounds auto-fit cannot replace the reference camera frame")
        cameras.append((span, resolution, camera["target_m"]))
    require(seen == {(stage,view) for stage in stages for view in VIEWS},
            "render_views", "Actual front/side/back evidence is required at each applicable stage")
    require(all(value == cameras[0] for value in cameras), "render_alignment", "Every model view/stage must share camera scale, target and resolution")
    return {"required_records": len(stages)*3, "bound_records": len(seen),
            "scope": "Hash-bound execution records; not proof that images are artistically correct or records are honest."}


def lowering_chain(contract, artifacts):
    """Bind inspected continuous source to the common master; never approve art."""
    volume, common = contract["volume"], contract["common"]
    review_id = volume.get("precompile_review")
    review = artifacts.json(review_id, "precompile_review")
    expected_images = {artifacts.sha(r["image"]) for r in contract.get("model_renders", [])
                       if r.get("stage") == "authored_volume"}
    require(review.get("schema") == "riverstone.multiview.precompile_review.v1" and
            review.get("source_sha256") == artifacts.sha(volume["source_artifact"]) and
            review.get("profile_sha256") == artifacts.sha(volume["profile_artifact"]) and expected_images and
            set(review.get("reviewed_image_sha256", [])) == expected_images,
            "precompile_review_binding", "Precompile review must bind exact source, profile and authored three-view images")
    require(review.get("decision") == "ready_for_voxelization" and review.get("basis") == "direct_multiview_image_review" and
            isinstance(review.get("reviewer"), str) and review["reviewer"].strip() and
            isinstance(review.get("findings"), list) and review["findings"],
            "precompile_review_pending", "Source-volume image review must be recorded before delivery compilation")
    record = artifacts.json(common.get("lowering_record"), "lowering_record")
    artifacts.get(common.get("adapter_source"), "adapter_source")
    require(record.get("schema") == "riverstone.multiview.common_lowering.v1" and
            record.get("source_sha256") == artifacts.sha(volume["source_artifact"]) and
            record.get("master_sha256") == artifacts.sha(common["master"]) and
            record.get("precompile_review_sha256") == artifacts.sha(review_id) and
            record.get("adapter_source_sha256") == artifacts.sha(common["adapter_source"]) and
            bool(record.get("command")), "lowering_binding", "Lowering record must bind reviewed continuous source, adapter and common master")
    return {"source_review_decision": review["decision"], "binding_verified": True,
            "scope": "Recorded process dependency; runtime chronology and reviewer identity are not independently authenticated."}


def visual_review(contract, artifacts):
    review = contract.get("visual_review")
    require(isinstance(review, dict), "visual_review_status", "Explicit separate visual review record/status required")
    status = review.get("status")
    require(status in {"pending", "rejected", "recorded_accepted"}, "visual_review_status", "Explicit separate visual review status required")
    if status != "pending":
        data = artifacts.json(review.get("record"), "visual_review")
        require(data.get("status") == status and isinstance(data.get("reviewer"), str) and data["reviewer"].strip() and
                isinstance(data.get("findings"), list) and data["findings"] and
                data.get("basis") == "direct_multiview_image_review", "visual_review_record", "Named visual reviewer and actual image findings required")
        hashes = {artifacts.sha(r["image"]) for r in contract.get("model_renders", [])}
        require(hashes and set(data.get("reviewed_image_sha256", [])) == hashes,
                "visual_review_stale", "Review must bind all current model render images")
        require(data.get("asset_complete") is not True and data.get("coverage_pass") is not True,
                "review_overclaim", "Image review alone cannot certify pipeline completeness or city coverage")
    return {"status": status, "authority": "Recorded reviewer statement, not authenticated by this validator",
            "automatic_art_acceptance": False}


def validate_contract(contract, repo_root):
    """Return explicit gates/diagnostics without running any generation code."""
    result = {"schema": "riverstone.asset.multiview_validation.v1", "technical_contract_pass": False,
              "automatic_art_acceptance": False, "asset_complete": False, "coverage_claim_allowed": False,
              "gates": {}, "errors": [], "diagnostics": {}}
    def run(name, function):
        try:
            result["diagnostics"][name] = function()
            result["gates"][name] = True
            return True
        except (ContractError, KeyError, TypeError, ValueError, OSError, AttributeError, OverflowError, RecursionError, zlib.error, struct.error) as error:
            result["gates"][name] = False
            result["errors"].append({"gate": name, "code": getattr(error, "code", "malformed_contract"), "detail": str(error)})
            return False
    def header():
        require(isinstance(contract, dict) and contract.get("schema") == SCHEMA, "contract_schema", "Unsupported contract schema")
        require(contract.get("asset_class") in COMPLEX | DIMENSIONAL, "asset_class", "Unsupported asset class")
        require(isinstance(contract.get("asset_id"), str) and contract["asset_id"], "asset_id", "Asset id required")
        frame = contract.get("frame", {})
        require(frame.get("unit") == "m" and frame.get("up") == "+Y" and frame.get("front") == "+Z" and
                frame.get("right") == "+X" and frame.get("handedness") == "right" and isinstance(frame.get("id"), str) and frame["id"] and
                finite(frame.get("asset_height_m")) and frame["asset_height_m"] > 0 and frame.get("foot_y_m") == 0,
                "coordinate_frame", "Metre, right-handed +Y up/+Z front/+X right, foot Y=0 required")
        claims = contract.get("claims", {})
        require(not any(claims.get(k) or contract.get(k) for k in ("asset_complete", "coverage_pass", "art_quality_pass", "numeric_quality_pass")),
                "automatic_quality_claim", "Contract validation cannot declare asset/coverage/art completion")
        return {"asset_id": contract["asset_id"], "asset_class": contract["asset_class"]}
    if not run("header", header):
        return result
    holder = {}
    def provenance():
        holder["artifacts"] = Artifacts(contract.get("artifacts"), repo_root)
        return {"verified_artifacts": len(holder["artifacts"].rows), "total_bytes": holder["artifacts"].total_bytes}
    if not run("provenance", provenance):
        return result
    artifacts = holder["artifacts"]
    complex_asset = contract["asset_class"] in COMPLEX
    if complex_asset:
        run("reference_alignment", lambda: references(contract, artifacts))
        run("source_volume_profile", lambda: volume_profile(contract, artifacts))
    else:
        result["diagnostics"]["dimensional_exception"] = "Dimension-driven standardized/parametric geometry does not require invented three-view references."
    run("common_geometry", lambda: common_geometry(contract, artifacts, complex_asset))
    run("model_render_evidence", lambda: render_evidence(contract, artifacts, complex_asset))
    if complex_asset:
        run("source_review_to_common", lambda: lowering_chain(contract, artifacts))
    run("visual_review_record", lambda: visual_review(contract, artifacts))
    result["technical_contract_pass"] = all(result["gates"].values())
    result["visual_review_status"] = result["diagnostics"].get("visual_review_record", {}).get("status", "invalid_or_missing")
    result["next_decision"] = "Human multiview shape/identity/clothing review remains separate from technical gates."
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate_contract(read_json(args.contract), args.repo_root)
    except (ValueError, OSError) as error:
        result = {"technical_contract_pass": False, "automatic_art_acceptance": False,
                  "asset_complete": False, "coverage_claim_allowed": False, "errors": [str(error)]}
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(text)
    else:
        sys.stdout.write(text)
    return 0 if result["technical_contract_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
