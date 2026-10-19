"""Independent bounded parity QA for layered house cells and render surfaces.

The common reference cells are streamed, coarse occupancy is expanded only one
owned chunk at a time, and render occupancy is retained only one face plane at a
time. This module deliberately does not import the compiler or its fingerprint
helpers: parity must not rely on the implementation being checked.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

SCHEMA = "riverstone.house_detail.layered_qa.v1"
FINE_PITCH = 0.05
MODULUS = 1 << 256
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


class QAError(ValueError):
    """Malformed or incompatible QA input."""


class Fingerprint:
    """Order-independent row multiset fingerprint, preserving all metadata."""

    def __init__(self):
        self.count = 0
        self.xor256 = 0
        self.sum256 = 0

    def add(self, row):
        encoded = json.dumps(row, separators=(",", ":"), ensure_ascii=False).encode()
        digest = int.from_bytes(hashlib.blake2b(encoded, digest_size=32).digest(), "big")
        self.count += 1
        self.xor256 ^= digest
        self.sum256 = (self.sum256 + digest) % MODULUS

    def merge(self, other):
        self.count += other.count
        self.xor256 ^= other.xor256
        self.sum256 = (self.sum256 + other.sum256) % MODULUS

    def as_dict(self):
        return {"count": self.count, "xor256": f"{self.xor256:064x}",
                "sum256": f"{self.sum256:064x}"}


def fingerprint(rows):
    result = Fingerprint()
    for row in rows:
        result.add(row)
    return result.as_dict()


def _fingerprint(value):
    if (not isinstance(value, dict) or set(value) != {"count", "xor256", "sum256"}
            or type(value["count"]) is not int or value["count"] < 0
            or any(not isinstance(value[key], str)
                   or not re.fullmatch(r"[0-9a-fA-F]{64}", value[key])
                   for key in ("xor256", "sum256"))):
        raise QAError("fingerprint must contain count, xor256 and sum256 (64 hex digits)")
    return {"count": value["count"], "xor256": value["xor256"].lower(),
            "sum256": value["sum256"].lower()}


@contextmanager
def _text_file(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        yield stream


class _JSONStream:
    """Incremental JSON values; never read an unbounded reference cells array."""

    def __init__(self, stream, read_size=65536):
        if read_size < 1:
            raise ValueError("read_size must be positive")
        self.stream, self.read_size = stream, read_size
        self.buffer, self.position, self.eof = "", 0, False
        self.decoder = json.JSONDecoder()

    def fill(self):
        self.buffer = self.buffer[self.position:]
        self.position = 0
        data = self.stream.read(self.read_size)
        if not data:
            self.eof = True
        self.buffer += data
        return bool(data)

    def peek(self):
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position].isspace():
                self.position += 1
            if self.position < len(self.buffer):
                return self.buffer[self.position]
            if self.eof:
                return ""
            self.fill()

    def expect(self, token):
        actual = self.peek()
        if actual != token:
            raise QAError(f"expected JSON {token!r}, got {actual!r}")
        self.position += 1

    def value(self):
        if not self.peek():
            raise QAError("truncated JSON value")
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
            except json.JSONDecodeError as error:
                if self.eof:
                    raise QAError(f"invalid or truncated JSON: {error.msg}") from error
                self.fill()
                continue
            # A scalar number can end at a read boundary before its fraction.
            if (end == len(self.buffer) or self.buffer[end] not in ",]}: \t\r\n") and not self.eof:
                self.fill()
                continue
            self.position = end
            return value


def iter_reference_cells(path, metadata=None, read_size=65536):
    """Yield rows from a common compiled JSON object using fixed-size reads.

    metadata is populated as encountered; exhaust the iterator before using it.
    Fields before and after cells are supported. Only one cell row is decoded at
    a time; no json.load or whole-file read is used for this artifact.
    """
    if metadata is None:
        metadata = {}
    with _text_file(path) as stream:
        reader = _JSONStream(stream, read_size)
        reader.expect("{")
        keys = set()
        first = True
        while reader.peek() != "}":
            if not first:
                reader.expect(",")
            key = reader.value()
            if not isinstance(key, str) or key in keys:
                raise QAError("reference contains a non-string or duplicate top-level key")
            keys.add(key)
            reader.expect(":")
            if key == "cells":
                reader.expect("[")
                first_row = True
                while reader.peek() != "]":
                    if not first_row:
                        reader.expect(",")
                    yield reader.value()
                    first_row = False
                reader.expect("]")
            else:
                metadata[key] = reader.value()
            first = False
        reader.expect("}")
        if reader.peek():
            raise QAError("trailing content after reference JSON")
        if "cells" not in keys:
            raise QAError("reference has no cells array")


def _row(row):
    if (not isinstance(row, list) or len(row) != 7
            or any(type(value) is not int for value in row[:3])):
        raise QAError("cell row must be [ix,iy,iz,instance,part,material,feature] with integer coordinates")
    return row


def _origin(origin):
    if (not isinstance(origin, list) or len(origin) != 3
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) for value in origin)):
        raise QAError("grid_origin must contain three finite numbers")
    return origin


def _bounds(bounds):
    if (not isinstance(bounds, list) or len(bounds) != 2
            or any(not isinstance(corner, list) or len(corner) != 3
                   or any(type(value) is not int for value in corner) for corner in bounds)
            or any(bounds[0][axis] >= bounds[1][axis] for axis in range(3))):
        raise QAError("owned_bounds_fine must be nonempty integer [lo,hi) bounds")
    return bounds


def expand_coarse(row):
    """Expand a shared-origin 0.1m row to its eight 0.05m addresses."""
    _row(row)
    for offset in itertools.product((0, 1), repeat=3):
        yield [*(2 * row[axis] + offset[axis] for axis in range(3)), *row[3:]]


def boxes_overlap(a, b):
    return all(max(a[0][axis], b[0][axis]) < min(a[1][axis], b[1][axis])
               for axis in range(3))


def analyze_layered(path):
    combined = Fingerprint()
    chunks, boxes, box_overlap_examples = [], [], []
    box_overlap_count = 0
    with _text_file(path) as stream:
        try:
            header = json.loads(next(stream))
        except StopIteration as error:
            raise QAError("empty layered cells artifact") from error
        if not isinstance(header, dict) or header.get("kind") != "header":
            raise QAError("first layered JSONL record must be a header")
        if header.get("fine_pitch_m") != FINE_PITCH or header.get("coarse_pitch_m") != 0.1:
            raise QAError("layered pitches must be 0.05m fine and 0.1m coarse")
        _origin(header.get("grid_origin"))
        for line_number, line in enumerate(stream, 2):
            if not line.strip():
                raise QAError(f"blank layered JSONL record on line {line_number}")
            chunk = json.loads(line)
            if not isinstance(chunk, dict) or chunk.get("kind") != "chunk":
                raise QAError(f"expected chunk record on line {line_number}")
            bounds = _bounds(chunk.get("owned_bounds_fine"))
            for previous_index, previous in enumerate(boxes):
                if boxes_overlap(previous, bounds):
                    box_overlap_count += 1
                    if len(box_overlap_examples) < 8:
                        box_overlap_examples.append([previous_index, len(boxes)])
            boxes.append(bounds)
            local = Fingerprint()
            seen = set()
            duplicate_count = outside_count = unknown_material_count = 0
            duplicate_examples, outside_examples = [], []
            fine_rows, coarse_rows = chunk.get("fine_cells"), chunk.get("coarse_cells")
            if not isinstance(fine_rows, list) or not isinstance(coarse_rows, list):
                raise QAError("each chunk must contain fine_cells and coarse_cells arrays")
            rows = itertools.chain((_row(row) for row in fine_rows),
                                   (fine for row in coarse_rows for fine in expand_coarse(row)))
            for row in rows:
                key = tuple(row[:3])
                if "materials" in header and row[5] not in header["materials"]:
                    unknown_material_count += 1
                if key in seen:
                    duplicate_count += 1
                    if len(duplicate_examples) < 8:
                        duplicate_examples.append(list(key))
                seen.add(key)
                if not all(bounds[0][axis] <= key[axis] < bounds[1][axis] for axis in range(3)):
                    outside_count += 1
                    if len(outside_examples) < 8:
                        outside_examples.append(list(key))
                local.add(row)
            expected = _fingerprint(chunk.get("full_fine_fingerprint"))
            matched = local.as_dict() == expected
            chunks.append({"index": len(chunks), "id": chunk.get("id", chunk.get("chunk_id", chunk.get("chunk"))),
                           "owned_bounds_fine": bounds, "fine_cell_count": len(fine_rows),
                           "coarse_cell_count": len(coarse_rows),
                           "expanded_fingerprint": local.as_dict(),
                           "full_fine_fingerprint": expected, "fingerprint_match": matched,
                           "duplicate_coordinate_count": duplicate_count,
                           "duplicate_examples": duplicate_examples,
                           "outside_owned_bounds_count": outside_count,
                           "outside_owned_bounds_examples": outside_examples,
                           "unknown_material_count": unknown_material_count,
                           "pass": matched and duplicate_count == outside_count == unknown_material_count == 0})
            combined.merge(local)
            # Do not retain expanded chunk coordinates into the next iteration.
            del seen, chunk, fine_rows, coarse_rows
    header_fingerprint_match = ("full_fine_fingerprint" not in header
                                or _fingerprint(header["full_fine_fingerprint"]) == combined.as_dict())
    return {"header": header, "chunk_count": len(chunks), "chunks": chunks,
            "expanded_fingerprint": combined.as_dict(),
            "header_fingerprint_match": header_fingerprint_match,
            "chunk_box_overlap_count": box_overlap_count,
            "chunk_box_overlap_examples": box_overlap_examples,
            "max_expanded_chunk_cells": max((c["expanded_fingerprint"]["count"] for c in chunks), default=0),
            "pass": bool(chunks) and all(c["pass"] for c in chunks)
                    and box_overlap_count == 0 and header_fingerprint_match}


def _quad_rectangle(quad, origin, pitch):
    if (not isinstance(quad, list) or len(quad) != 4
            or any(not isinstance(point, list) or len(point) != 3 for point in quad)):
        raise QAError("render quad must contain four 3D vertices")
    points = []
    for point in quad:
        snapped = []
        for axis, coordinate in enumerate(point):
            if (isinstance(coordinate, bool) or not isinstance(coordinate, (int, float))
                    or not math.isfinite(coordinate)):
                raise QAError("render vertices must contain finite numbers")
            grid = (coordinate - origin[axis]) / pitch
            address = round(grid)
            if abs(grid - address) > 1e-6:
                raise QAError("render quad vertex is not aligned to the shared 0.05m grid")
            snapped.append(address)
        points.append(tuple(snapped))
    constant = [axis for axis in range(3) if len({p[axis] for p in points}) == 1]
    if len(constant) != 1 or len(set(points)) != 4:
        raise QAError("render quad is degenerate or not axis-aligned")
    axis = constant[0]
    # Cyclic tangential axes define the public face fingerprint convention.
    u, v = (axis + 1) % 3, (axis + 2) % 3
    u0, u1 = min(p[u] for p in points), max(p[u] for p in points)
    v0, v1 = min(p[v] for p in points), max(p[v] for p in points)
    if {(p[u], p[v]) for p in points} != set(itertools.product((u0, u1), (v0, v1))):
        raise QAError("render quad must be a rectangular face")
    edges = [tuple(points[(i + 1) % 4][a] - points[i][a] for a in range(3)) for i in range(4)]
    if any(sum(value != 0 for value in edge) != 1 for edge in edges):
        raise QAError("render quad has crossed or non-axis-aligned edges")
    e, f = edges[:2]
    normal = (e[1] * f[2] - e[2] * f[1], e[2] * f[0] - e[0] * f[2],
              e[0] * f[1] - e[1] * f[0])
    sign = 1 if normal[axis] > 0 else -1
    return axis, sign, points[0][axis], u0, u1, v0, v1


def analyze_render(path, expected_origin=None, pitch=FINE_PITCH):
    with _text_file(path) as stream:
        render = json.load(stream)
    if not isinstance(render, dict):
        raise QAError("render root must be a JSON object")
    origin = _origin(render.get("grid_origin"))
    if expected_origin is not None and origin != expected_origin:
        raise QAError("render grid_origin differs from the cell grid_origin")
    groups = render.get("groups")
    if not isinstance(groups, list):
        raise QAError("render must contain groups[{material,quads}]")
    planes = defaultdict(list)
    quad_count = unknown_material_groups = 0
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("quads"), list) or "material" not in group:
            raise QAError("malformed render group")
        material = group["material"]
        if "materials" in render and material not in render["materials"]:
            unknown_material_groups += 1
        for quad in group["quads"]:
            axis, sign, plane, u0, u1, v0, v1 = _quad_rectangle(quad, origin, pitch)
            planes[(axis, plane)].append((sign, u0, u1, v0, v1, material))
            quad_count += 1
    declared_quads = render.get("quad_count")
    metadata = {key: render[key] for key in ("schema", "pitch", "grid_origin", "source_id", "source_revision",
                "master_hash", "materials", "payload_hash", "cell_count", "provenance") if key in render}
    del groups, render
    result = Fingerprint()
    overlap_count, overlap_examples, max_plane_faces = 0, [], 0
    for (axis, plane), rectangles in planes.items():
        seen = set()
        for sign, u0, u1, v0, v1, material in rectangles:
            for u in range(u0, u1):
                for v in range(v0, v1):
                    key = (u, v)
                    if key in seen:
                        overlap_count += 1
                        if len(overlap_examples) < 8:
                            overlap_examples.append([axis, plane, u, v])
                    seen.add(key)
                    result.add([axis, sign, plane, u, v, material])
        max_plane_faces = max(max_plane_faces, len(seen))
        del seen
    return {"metadata": metadata, "quad_count": quad_count,
            "unknown_material_groups": unknown_material_groups,
            "declared_quad_count_match": declared_quads is None or declared_quads == quad_count,
            "face_fingerprint": result.as_dict(), "overlap_count": overlap_count,
            "overlap_examples": overlap_examples, "plane_count": len(planes),
            "max_unique_faces_on_one_plane": max_plane_faces,
            "pass": overlap_count == unknown_material_groups == 0 and (declared_quads is None or declared_quads == quad_count)}


def _file_info(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def _sha256(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _source_checks(header, stats, catalog_path):
    """Verify real immutable source files through the explicit asset catalog."""
    catalog_path = Path(catalog_path or HERE / "generated" / "active_catalog.json")
    with _text_file(catalog_path) as stream:
        catalog = json.load(stream)
    matches = [record for record in catalog.get("assets", []) if record.get("asset_key") == header.get("asset_key")]
    if len(matches) != 1:
        raise QAError("source catalog must identify exactly one matching asset")
    record = matches[0]
    paths = {"source_master": record.get("source_master_path"), "authored_master": record.get("emitted_master_path")}
    if any(not isinstance(path, str) or not path for path in paths.values()):
        raise QAError("source catalog lacks source/authored master paths")
    files = {key: _file_info(ROOT / path) for key, path in paths.items()}
    checks = {}
    for key, catalog_key in (("source_master", "source_sha256"), ("authored_master", "emitted_master_sha256")):
        actual = files[key]["sha256"]
        checks[key + "_file_sha256_match"] = actual == header.get(key + "_sha256") == stats.get(key + "_sha256") == record.get(catalog_key)
    with _text_file(ROOT / paths["authored_master"]) as stream:
        master = json.load(stream)
    canonical = json.dumps(master, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    checks["authored_master_canonical_hash_match"] = hashlib.sha256(canonical).hexdigest() == header.get("master_hash")
    checks["authored_source_id_match"] = master.get("id") == header.get("source_id")
    checks["authored_source_revision_match"] = master.get("revision") == header.get("source_revision")
    checks["authored_grid_origin_match"] = master.get("grid_origin", [0, 0, 0]) == header.get("grid_origin")
    checks["authored_material_palette_match"] = master.get("materials") == header.get("materials")
    return {"checks": checks, "files": files, "catalog": _file_info(catalog_path), "pass": all(checks.values())}


def validate_stats(stats_path, layered, surface, file_info, source_catalog=None):
    with _text_file(stats_path) as stream:
        stats = json.load(stream)
    if not isinstance(stats, dict):
        raise QAError("layered stats root must be a JSON object")
    header, metadata = layered["header"], surface["metadata"]
    checks = {"stats_schema": stats.get("schema") == "riverstone.house_detail.layered_stats.v1",
              "header_schema": header.get("schema") == "riverstone.house_detail.layered_cells.v1",
              "asset_key_match": isinstance(header.get("asset_key"), str) and bool(header["asset_key"])
                                 and stats.get("asset_key") == header["asset_key"],
              "header_chunk_count_match": header.get("chunks") == layered["chunk_count"],
              "full_fine_fingerprint_match": _fingerprint(stats.get("full_fine_fingerprint")) == layered["expanded_fingerprint"],
              "rasterized_face_fingerprint_match": _fingerprint(stats.get("fine_face_fingerprint")) == surface["face_fingerprint"]}
    for key in ("source_master_sha256", "authored_master_sha256"):
        checks[key + "_match"] = _sha256(header.get(key)) and header[key] == stats.get(key)
    for key in ("source_id", "source_revision", "master_hash", "grid_origin", "materials"):
        checks["render_" + key + "_match"] = key in header and key in metadata and header[key] == metadata[key]
    checks["master_hash_format"] = _sha256(header.get("master_hash"))
    checks["render_fine_pitch"] = metadata.get("pitch") == FINE_PITCH
    checks["material_palette_present"] = isinstance(header.get("materials"), dict) and bool(header["materials"])
    checks["render_cell_count_match"] = metadata.get("cell_count") == layered["expanded_fingerprint"]["count"]
    provenance = metadata.get("provenance", {})
    if not isinstance(provenance, dict):
        raise QAError("render provenance must be an object")
    for header_key, provenance_key in (("compiler_source_sha256", "compiler_source_hash"),
                                        ("layer_engine_sha256", "layer_engine_sha256"),
                                        ("layer_rules_sha256", "layer_rules_sha256")):
        checks[header_key + "_match"] = _sha256(header.get(header_key)) and header[header_key] == provenance.get(provenance_key)
    checks["render_provenance_face_fingerprint_match"] = _fingerprint(provenance.get("fine_face_fingerprint")) == surface["face_fingerprint"]
    checks["render_payload_file_sha256_match"] = metadata.get("payload_hash") == file_info["layered_cells"]["sha256"]
    for suffix, key in ((".cells.jsonl.gz", "layered_cells"), (".render.json", "layered_render")):
        declared = stats.get("files", {}).get(suffix, {})
        actual = file_info[key]
        checks[key + "_file_sha256_match"] = _sha256(declared.get("sha256")) and declared["sha256"] == actual["sha256"]
        checks[key + "_file_size_match"] = declared.get("bytes") == actual["bytes"]
        checks[key + "_file_path_match"] = isinstance(declared.get("path"), str) and (ROOT / declared["path"]).resolve() == Path(actual["path"]).resolve()
    total_fine = sum(chunk["fine_cell_count"] for chunk in layered["chunks"])
    total_coarse = sum(chunk["coarse_cell_count"] for chunk in layered["chunks"])
    for key, expected in (("reference_full_fine_cells", layered["expanded_fingerprint"]["count"]),
                          ("lossless_fine_expanded_cell_count", total_fine + 8 * total_coarse),
                          ("stored_fine_cells", total_fine), ("stored_core_cells", total_coarse),
                          ("stored_total_cells", total_fine + total_coarse),
                          ("quads", surface["quad_count"]), ("visible_unit_faces", surface["face_fingerprint"]["count"])):
        checks[key + "_match"] = stats.get(key) == expected
    summaries = stats.get("chunks")
    if not isinstance(summaries, list):
        raise QAError("stats chunks must be an array")
    checks["stats_chunk_count_match"] = len(summaries) == layered["chunk_count"]
    per_chunk = []
    for index, (chunk, summary) in enumerate(zip(layered["chunks"], summaries)):
        current = {"id_match": summary.get("chunk") == chunk["id"],
                   "expanded_count_match": summary.get("reference_owned_fine_cells") == chunk["expanded_fingerprint"]["count"],
                   "fine_count_match": summary.get("stored_fine_cells") == chunk["fine_cell_count"],
                   "coarse_count_match": summary.get("stored_core_cells") == chunk["coarse_cell_count"]}
        per_chunk.append({"index": index, "checks": current, "pass": all(current.values())})
    checks["per_chunk_stats_match"] = all(chunk["pass"] for chunk in per_chunk)
    checks["summed_chunk_faces_match"] = sum(chunk.get("visible_unit_faces", -1) for chunk in summaries) == surface["face_fingerprint"]["count"]
    checks["summed_chunk_quads_match"] = sum(chunk.get("quads", -1) for chunk in summaries) == surface["quad_count"]
    source = _source_checks(header, stats, source_catalog)
    checks["source_artifacts_match"] = source["pass"]
    return {"checks": checks, "per_chunk_checks": per_chunk, "source_artifacts": source,
            "stats_file": _file_info(stats_path), "pass": all(checks.values()),
            "evidence_limit": "Stats and per-chunk reference fingerprints originate in the layered compiler; these checks validate artifact consistency, not an independent whole-house baseline."}


def verify(reference_cells=None, reference_render=None, layered_cells=None, layered_render=None,
           layered_stats=None, source_catalog=None):
    if bool(reference_cells) != bool(reference_render):
        raise QAError("reference-cells and reference-render must be supplied together")
    if reference_cells is None and layered_stats is None:
        raise QAError("supply both reference artifacts or --layered-stats for structural-only validation")
    layered = analyze_layered(layered_cells)
    origin = layered["header"]["grid_origin"]
    layered_surface = analyze_render(layered_render, origin)
    layered_metadata_checks = {key: layered["header"][key] == layered_surface["metadata"].get(key)
                               for key in ("source_id", "source_revision", "master_hash", "materials")
                               if key in layered["header"]}
    file_info = {"layered_cells": _file_info(layered_cells), "layered_render": _file_info(layered_render)}
    full_baseline = reference_cells is not None
    report = {"schema": SCHEMA,
              "validation_scope": "independent full-house reference parity" if full_baseline else "chunk-reference structural validation, full-house baseline unavailable",
              "full_house_baseline_available": full_baseline, "full_house_parity_pass": None,
              "method": {"cells": ("streamed independent reference and per-owned-chunk expansion" if full_baseline
                                    else "per-owned-chunk expansion compared with compiler-reported chunk/stats fingerprints")
                                   + "; count/xor256/sum256 BLAKE2b-256 multisets",
                         "render": "independent CCW quad rasterization to directed 0.05m unit faces; per-plane overlap checks",
                         "face_coordinates": "[axis,sign,plane,u,v,material], u=(axis+1)%3, v=(axis+2)%3",
                         "whole_building_merged_cell_dataset_created": False},
              "layered_cells": layered, "layered_render": layered_surface, "input_files": file_info,
              "layered_metadata_checks": layered_metadata_checks,
              "pass": layered["pass"] and layered_surface["pass"] and all(layered_metadata_checks.values())}
    if full_baseline:
        reference_metadata = {}
        reference_fp = Fingerprint()
        for row in iter_reference_cells(reference_cells, reference_metadata):
            reference_fp.add(_row(row))
        if reference_metadata.get("pitch") != FINE_PITCH:
            raise QAError("reference cells must use 0.05m pitch")
        reference_origin = _origin(reference_metadata.get("grid_origin"))
        origin_match = origin == reference_origin
        cells_match = reference_fp.as_dict() == layered["expanded_fingerprint"]
        metadata_checks = {key: reference_metadata[key] == layered["header"][key]
                           for key in ("source_id", "source_revision", "master_hash", "materials")
                           if key in reference_metadata and key in layered["header"]}
        reference_surface = analyze_render(reference_render, reference_origin)
        reference_metadata_checks = {key: reference_metadata[key] == reference_surface["metadata"].get(key)
                                     for key in ("source_id", "source_revision", "master_hash", "materials", "payload_hash")
                                     if key in reference_metadata}
        render_match = reference_surface["face_fingerprint"] == layered_surface["face_fingerprint"]
        palette_match = reference_surface["metadata"].get("materials") == layered_surface["metadata"].get("materials")
        report.update(reference_cells={"fingerprint": reference_fp.as_dict(), "pitch": FINE_PITCH, "grid_origin": reference_origin},
                      cell_fingerprint_match=cells_match, grid_origin_match=origin_match, metadata_checks=metadata_checks,
                      reference_render=reference_surface, reference_metadata_checks=reference_metadata_checks,
                      render_face_fingerprint_match=render_match,
                      render_material_palette_match=palette_match)
        report["pass"] = (report["pass"] and cells_match and origin_match and all(metadata_checks.values())
                          and all(reference_metadata_checks.values()) and reference_surface["pass"] and render_match and palette_match)
        report["full_house_parity_pass"] = report["pass"]
        file_info.update(reference_cells=_file_info(reference_cells), reference_render=_file_info(reference_render))
    if layered_stats is not None:
        report["stats_validation"] = validate_stats(layered_stats, layered, layered_surface, file_info, source_catalog)
        report["pass"] = report["pass"] and report["stats_validation"]["pass"]
        file_info["layered_stats"] = report["stats_validation"]["stats_file"]
    if not full_baseline:
        report["limitations"] = ["No independent whole-house 0.05m baseline was supplied.",
                                  "Original source sampling, crop completeness, and visual/runtime correctness are not independently established by this structural consistency check."]
    report["status"] = ("PASS_FULL_REFERENCE_PARITY" if full_baseline else "PASS_CHUNK_REFERENCE_STRUCTURAL_ONLY") if report["pass"] else "FAIL"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layered-cells", "layered-render", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("reference-cells", "reference-render", "layered-stats", "source-catalog"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args(argv)
    # Resolve the declared logical render artifact from stats, including compressed JSON.
    if args.layered_stats is not None and not args.layered_render.exists():
        with _text_file(args.layered_stats) as stream: declared_stats=json.load(stream)
        declared_path=declared_stats.get('files',{}).get('.render.json',{}).get('path')
        if declared_path is not None:args.layered_render=ROOT/declared_path
    try:
        report = verify(args.reference_cells, args.reference_render, args.layered_cells, args.layered_render,
                        args.layered_stats, args.source_catalog)
    except (QAError, OSError, ValueError, TypeError, KeyError) as error:
        report = {"schema": SCHEMA, "pass": False, "error": str(error), "error_type": type(error).__name__}
    report["inputs"] = {key: str(getattr(args, key)) for key in
                        ("reference_cells", "reference_render", "layered_cells", "layered_render", "layered_stats", "source_catalog")
                        if getattr(args, key) is not None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "status": report.get("status", "FAIL"), "report": str(args.output),
                      **({"error": report["error"]} if "error" in report else {})}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
