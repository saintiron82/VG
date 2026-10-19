"""Small independent tests; no house compilation or full-building cell union."""
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import layered_qa as qa


def quad(x0, x1, y0, y1, z=0):
    return [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]]


class LayeredQATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.meta = ["house/translated", "solid", "stone", "굴곡"]
        self.coarse = [-1, 2, 0, *self.meta]
        self.fine = list(qa.expand_coarse(self.coarse))
        self.header = {"kind": "header", "fine_pitch_m": .05, "coarse_pitch_m": .1, "grid_origin": [0, 0, 0]}

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, value):
        path = self.root / name
        if name.endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        else:
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def write_layered(self, chunks, header=None):
        path = self.root / "layered.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            for record in [header or self.header, *chunks]:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def chunk(self, coarse=None, fine=None, bounds=None):
        coarse = [self.coarse] if coarse is None else coarse
        fine = [] if fine is None else fine
        expanded = [*fine, *(row for item in coarse for row in qa.expand_coarse(item))]
        return {"kind": "chunk", "id": "bounded-probe", "owned_bounds_fine": bounds or [[-2, 4, 0], [0, 6, 2]],
                "fine_cells": fine, "coarse_cells": coarse, "full_fine_fingerprint": qa.fingerprint(expanded)}

    def render(self, name, quads, origin=None):
        return self.write_json(name, {"grid_origin": origin or [0, 0, 0], "pitch": .05,
                                     "materials": {"stone": "999999"},
                                     "groups": [{"material": "stone", "quads": quads}], "quad_count": len(quads)})

    def structural_fixture(self, compressed=False):
        master = {"id": "fixture-house", "revision": 3, "grid_origin": [0, 0, 0], "materials": {"stone": "999999"}}
        authored = self.write_json("authored.master.json.gz" if compressed else "authored.master.json", master)
        source = self.write_json("original.master.json", {"id": "original-house"})
        header = dict(self.header, schema="riverstone.house_detail.layered_cells.v1", asset_key="fixture", chunks=1,
                      source_id=master["id"], source_revision=3, materials=master["materials"],
                      master_hash=hashlib.sha256(json.dumps(master, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
                      authored_master_sha256=qa._file_info(authored)["sha256"], source_master_sha256=qa._file_info(source)["sha256"],
                      compiler_source_sha256="a" * 64, layer_engine_sha256="b" * 64, layer_rules_sha256="c" * 64)
        cells = self.write_layered([self.chunk()], header)
        render = self.render("structural.render.json", [quad(0, .1, 0, .1)])
        face_fp = qa.analyze_render(render)["face_fingerprint"]
        value = json.loads(render.read_text())
        value.update({key: header[key] for key in ("source_id", "source_revision", "master_hash")})
        value.update(cell_count=8, payload_hash=qa._file_info(cells)["sha256"],
                     provenance={"compiler_source_hash": "a" * 64, "layer_engine_sha256": "b" * 64,
                                 "layer_rules_sha256": "c" * 64, "fine_face_fingerprint": face_fp})
        render.write_text(json.dumps(value))
        stats = self.write_json("structural.stats.json", {
            "schema": "riverstone.house_detail.layered_stats.v1", "asset_key": "fixture",
            "source_master_sha256": header["source_master_sha256"], "authored_master_sha256": header["authored_master_sha256"],
            "full_fine_fingerprint": qa.fingerprint(self.fine), "fine_face_fingerprint": face_fp,
            "reference_full_fine_cells": 8, "lossless_fine_expanded_cell_count": 8, "stored_fine_cells": 0,
            "stored_core_cells": 1, "stored_total_cells": 1, "quads": 1, "visible_unit_faces": 4,
            "chunks": [{"chunk": "bounded-probe", "reference_owned_fine_cells": 8, "stored_fine_cells": 0,
                        "stored_core_cells": 1, "visible_unit_faces": 4, "quads": 1}],
            "files": {".cells.jsonl.gz": qa._file_info(cells), ".render.json": qa._file_info(render)}})
        catalog = self.write_json("catalog.json", {"assets": [{"asset_key": "fixture", "source_master_path": str(source),
                    "emitted_master_path": str(authored), "source_sha256": header["source_master_sha256"],
                    "emitted_master_sha256": header["authored_master_sha256"]}]})
        return cells, render, stats, catalog

    def verify_structural(self, paths):
        cells, render, stats, catalog = paths
        return qa.verify(layered_cells=cells, layered_render=render, layered_stats=stats, source_catalog=catalog)

    def test_structural_only_is_explicitly_not_full_reference_parity(self):
        report = self.verify_structural(self.structural_fixture())
        self.assertTrue(report["pass"])
        self.assertEqual(report["status"], "PASS_CHUNK_REFERENCE_STRUCTURAL_ONLY")
        self.assertEqual(report["validation_scope"], "chunk-reference structural validation, full-house baseline unavailable")
        self.assertFalse(report["full_house_baseline_available"])
        self.assertIsNone(report["full_house_parity_pass"])
        self.assertNotIn("cell_fingerprint_match", report)
        self.assertTrue(report["stats_validation"]["source_artifacts"]["pass"])

    def test_gzip_authored_source_uses_compressed_file_sha_and_decoded_canonical_hash(self):
        paths = self.structural_fixture(compressed=True)
        report = self.verify_structural(paths)
        self.assertTrue(report["pass"])
        self.assertTrue(report["stats_validation"]["source_artifacts"]["checks"]["authored_master_canonical_hash_match"])
        self.assertFalse((self.root / "authored.master.json").exists())

    def test_full_reference_and_stats_can_be_verified_together(self):
        cells, render, stats, catalog = self.structural_fixture()
        reference = self.write_json("reference.json.gz", {"pitch": .05, "grid_origin": [0, 0, 0], "cells": self.fine})
        report = qa.verify(reference, render, cells, render, stats, catalog)
        self.assertTrue(report["pass"])
        self.assertTrue(report["full_house_parity_pass"])
        self.assertTrue(report["stats_validation"]["pass"])

    def test_structural_stats_detects_fingerprint_and_file_hash_tampering(self):
        for kind in ("fingerprint", "file_hash", "chunk_count"):
            with self.subTest(kind=kind):
                paths = self.structural_fixture()
                stats = json.loads(paths[2].read_text())
                if kind == "fingerprint":
                    stats["full_fine_fingerprint"] = qa.fingerprint([])
                elif kind == "file_hash":
                    stats["files"][".render.json"]["sha256"] = "0" * 64
                else:
                    stats["chunks"][0]["stored_core_cells"] = 2
                paths[2].write_text(json.dumps(stats))
                self.assertFalse(self.verify_structural(paths)["pass"])

    def test_structural_stats_detects_changed_original_source_file(self):
        paths = self.structural_fixture()
        source = self.root / "original.master.json"
        source.write_text(source.read_text() + " ")
        report = self.verify_structural(paths)
        self.assertFalse(report["pass"])
        self.assertFalse(report["stats_validation"]["source_artifacts"]["checks"]["source_master_file_sha256_match"])

    def test_structural_stats_detects_render_metadata_tampering(self):
        for key, bad_value in (("source_revision", 99), ("materials", {"stone": "000000"}), ("master_hash", "0" * 64)):
            with self.subTest(key=key):
                paths = self.structural_fixture()
                render = json.loads(paths[1].read_text())
                render[key] = bad_value
                paths[1].write_text(json.dumps(render))
                stats = json.loads(paths[2].read_text())
                stats["files"][".render.json"] = qa._file_info(paths[1])
                paths[2].write_text(json.dumps(stats))
                report = self.verify_structural(paths)
                self.assertFalse(report["pass"])
                self.assertFalse(report["stats_validation"]["checks"]["render_" + key + "_match"])

    def test_face_fingerprint_uses_cyclic_axes_for_y_normal(self):
        points = [[0, 0, 0], [0, 0, .1], [.05, 0, .1], [.05, 0, 0]]
        report = qa.analyze_render(self.render("yface.json", [points]))
        self.assertEqual(report["face_fingerprint"], qa.fingerprint([[1, 1, 0, 0, 0, "stone"], [1, 1, 0, 1, 0, "stone"]]))

    def test_missing_reference_requires_stats_and_reference_pair_is_atomic(self):
        with self.assertRaises(qa.QAError):
            qa.verify(layered_cells="missing", layered_render="missing")
        with self.assertRaises(qa.QAError):
            qa.verify(reference_cells="missing", layered_cells="missing", layered_render="missing")

    def test_structural_only_cli(self):
        cells, render, stats, catalog = self.structural_fixture()
        output = self.root / "structural.report.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = qa.main(["--layered-cells", str(cells), "--layered-render", str(render), "--layered-stats", str(stats),
                            "--source-catalog", str(catalog), "--output", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.read_text())["status"], "PASS_CHUNK_REFERENCE_STRUCTURAL_ONLY")

    def test_reference_gzip_streams_with_tiny_reads_and_trailing_metadata(self):
        path = self.write_json("reference.cells.json.gz", {"pitch": .05, "cells": self.fine, "grid_origin": [0, 0, 0], "valid": True})
        metadata = {}
        with mock.patch.object(qa.json, "load", side_effect=AssertionError("must not load whole reference")):
            self.assertEqual(list(qa.iter_reference_cells(path, metadata, read_size=1)), self.fine)
        self.assertEqual(metadata, {"pitch": .05, "grid_origin": [0, 0, 0], "valid": True})

    def test_reference_fixed_size_reads_do_not_materialize_array(self):
        class BoundedRead(io.StringIO):
            def read(self, size=-1):
                if size < 0 or size > 17:
                    raise AssertionError("unbounded read")
                return super().read(size)
        stream = BoundedRead(json.dumps({"cells": self.fine}))
        with mock.patch.object(qa, "_text_file", return_value=contextlib.nullcontext(stream)):
            rows = qa.iter_reference_cells("unused", read_size=17)
            self.assertEqual(next(rows), self.fine[0])
            self.assertLess(stream.tell(), len(stream.getvalue()))
            self.assertEqual(list(rows), self.fine[1:])

    def test_reference_truncated_array_is_rejected(self):
        path = self.root / "broken.json"
        path.write_text('{"cells":[[1,2,3,"a","b","c","d"]')
        with self.assertRaises(qa.QAError):
            list(qa.iter_reference_cells(path, read_size=7))

    def test_fingerprint_matches_prescribed_hash(self):
        row = self.fine[0]
        digest = hashlib.blake2b(json.dumps(row, separators=(",", ":"), ensure_ascii=False).encode(), digest_size=32).hexdigest()
        self.assertEqual(qa.fingerprint([row]), {"count": 1, "xor256": digest, "sum256": digest})
        self.assertEqual(qa.fingerprint(self.fine), qa.fingerprint(reversed(self.fine)))
        self.assertNotEqual(qa.fingerprint([row]), qa.fingerprint([[*row[:6], "changed"]]))

    def test_one_coarse_cell_expands_to_eight_signed_addresses(self):
        self.assertEqual(len(self.fine), 8)
        self.assertEqual({tuple(row[:3]) for row in self.fine}, {(x, y, z) for x in (-2, -1) for y in (4, 5) for z in (0, 1)})
        self.assertTrue(all(row[3:] == self.meta for row in self.fine))
        result = qa.analyze_layered(self.write_layered([self.chunk()]))
        self.assertTrue(result["pass"])
        self.assertEqual(result["expanded_fingerprint"], qa.fingerprint(self.fine))
        self.assertEqual(result["max_expanded_chunk_cells"], 8)

    def test_fine_coarse_overlap_fails_even_when_fingerprint_agrees(self):
        result = qa.analyze_layered(self.write_layered([self.chunk(fine=[self.fine[0]])]))
        self.assertFalse(result["pass"])
        self.assertEqual(result["chunks"][0]["duplicate_coordinate_count"], 1)
        self.assertTrue(result["chunks"][0]["fingerprint_match"])

    def test_duplicate_coarse_cell_reports_eight_overlaps(self):
        result = qa.analyze_layered(self.write_layered([self.chunk(coarse=[self.coarse, self.coarse])]))
        self.assertFalse(result["pass"])
        self.assertEqual(result["chunks"][0]["duplicate_coordinate_count"], 8)

    def test_chunk_ownership_is_half_open_and_coarse_must_fit(self):
        result = qa.analyze_layered(self.write_layered([self.chunk(bounds=[[-2, 4, 0], [-1, 6, 2]])]))
        self.assertFalse(result["pass"])
        self.assertEqual(result["chunks"][0]["outside_owned_bounds_count"], 4)

    def test_adjacent_chunk_boxes_pass_and_intersecting_boxes_fail(self):
        first = self.chunk()
        adjacent = self.chunk(coarse=[[0, 2, 0, *self.meta]], bounds=[[0, 4, 0], [2, 6, 2]])
        self.assertTrue(qa.analyze_layered(self.write_layered([first, adjacent]))["pass"])
        adjacent["owned_bounds_fine"][0][0] = -1
        result = qa.analyze_layered(self.write_layered([first, adjacent]))
        self.assertFalse(result["pass"])
        self.assertEqual(result["chunk_box_overlap_count"], 1)
        repeated = qa.analyze_layered(self.write_layered([first, first]))
        self.assertFalse(repeated["pass"])
        self.assertEqual(repeated["chunk_box_overlap_count"], 1)

    def test_chunk_fingerprint_and_header_origin_are_validated(self):
        chunk = self.chunk()
        chunk["full_fine_fingerprint"] = qa.fingerprint([])
        self.assertFalse(qa.analyze_layered(self.write_layered([chunk]))["pass"])
        with self.assertRaises(qa.QAError):
            qa.analyze_layered(self.write_layered([chunk], dict(self.header, grid_origin=[0, 0])))

    def test_split_quads_are_equivalent_to_one_large_surface(self):
        full = qa.analyze_render(self.render("full.json", [quad(0, .1, 0, .1)]))
        split = qa.analyze_render(self.render("split.json", [quad(0, .05, 0, .1), quad(.05, .1, 0, .1)]))
        self.assertTrue(full["pass"] and split["pass"])
        self.assertEqual(full["face_fingerprint"], split["face_fingerprint"])
        self.assertEqual(full["face_fingerprint"]["count"], 4)
        self.assertEqual(full["max_unique_faces_on_one_plane"], 4)

    def test_render_orientation_material_and_overlap_are_checked(self):
        corners = quad(0, .1, 0, .1)
        forward = qa.analyze_render(self.render("forward.json", [corners]))
        reverse = qa.analyze_render(self.render("reverse.json", [list(reversed(corners))]))
        self.assertNotEqual(forward["face_fingerprint"], reverse["face_fingerprint"])
        duplicated = qa.analyze_render(self.render("duplicate.json", [corners, list(reversed(corners))]))
        self.assertFalse(duplicated["pass"])
        self.assertEqual(duplicated["overlap_count"], 4)
        path = self.render("material.json", [corners])
        value = json.loads(path.read_text())
        value["groups"][0]["material"] = "timber"
        path.write_text(json.dumps(value))
        self.assertNotEqual(forward["face_fingerprint"], qa.analyze_render(path)["face_fingerprint"])

    def test_quad_axes_and_nonzero_origin(self):
        origin = [.03, -.02, .07]
        points = [[origin[i] + p[i] * .05 for i in range(3)] for p in [[-1, 0, 0], [-1, 1, 0], [-1, 1, 2], [-1, 0, 2]]]
        result = qa.analyze_render(self.render("xface.json", [points], origin), origin)
        self.assertEqual(result["face_fingerprint"], qa.fingerprint([[0, 1, -1, 0, 0, "stone"], [0, 1, -1, 0, 1, "stone"]]))
        with self.assertRaises(qa.QAError):
            qa.analyze_render(self.root / "xface.json", [0, 0, 0])

    def test_render_rejects_skew_grid_misalignment_and_crossed_quads(self):
        invalid = [quad(0, .071, 0, .1), [[0, 0, 0], [.1, 0, 0], [.1, .1, .05], [0, .1, 0]],
                   [[0, 0, 0], [.1, .1, 0], [.1, 0, 0], [0, .1, 0]]]
        for index, corners in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(qa.QAError):
                qa.analyze_render(self.render(f"invalid{index}.json", [corners]))

    def test_end_to_end_cli_small_artifacts(self):
        reference = self.write_json("reference.cells.json.gz", {"pitch": .05, "grid_origin": [0, 0, 0], "cells": self.fine})
        layered = self.write_layered([self.chunk()])
        ref_render = self.render("reference.render.json", [quad(0, .1, 0, .1)])
        new_render = self.render("layered.render.json", [quad(0, .05, 0, .1), quad(.05, .1, 0, .1)])
        output = self.root / "report.json"
        args = ["--reference-cells", str(reference), "--reference-render", str(ref_render), "--layered-cells", str(layered),
                "--layered-render", str(new_render), "--output", str(output)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(qa.main(args), 0)
        report = json.loads(output.read_text())
        self.assertTrue(report["pass"])
        self.assertTrue(report["render_face_fingerprint_match"])
        self.assertFalse(report["method"]["whole_building_merged_cell_dataset_created"])
        changed = self.chunk()
        changed["coarse_cells"][0] = [*self.coarse[:6], "different-feature"]
        self.write_layered([changed])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(qa.main(args), 1)
        self.assertFalse(json.loads(output.read_text())["pass"])

    def test_cli_writes_failure_report_on_malformed_input(self):
        output = self.root / "error.json"
        with contextlib.redirect_stdout(io.StringIO()):
            result = qa.main(["--reference-cells", "missing.gz", "--reference-render", "missing.json",
                              "--layered-cells", "missing.jsonl.gz", "--layered-render", "missing2.json", "--output", str(output)])
        self.assertEqual(result, 1)
        self.assertFalse(json.loads(output.read_text())["pass"])


if __name__ == "__main__":
    unittest.main()
