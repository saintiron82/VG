"""Tiny synthetic input tests. No house/fountain generation or graphical renders."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
GODOT = shutil.which(os.environ.get("GODOT", "godot"))


def fixture(pitch=0.1):
    low, high = [2.0, 3.0, 4.0], [3.0, 5.0, 6.0]
    quads = []
    for axis in range(3):
        u, v = (axis + 1) % 3, (axis + 2) % 3
        for sign in (-1, 1):
            corners = []
            for a, b in [(low[u], low[v]), (high[u], low[v]),
                         (high[u], high[v]), (low[u], high[v])]:
                point = [0.0] * 3
                point[axis] = high[axis] if sign > 0 else low[axis]
                point[u], point[v] = a, b
                corners.append(point)
            quads.append(corners if sign > 0 else corners[::-1])
    return {"schema": "riverstone.voxel.render.v1", "source_id": "synthetic_box",
            "source_revision": 1, "master_hash": "fixture_only_not_a_real_master",
            "payload_hash": "fixture_only", "pitch": pitch, "unit": "m",
            "grid_origin": [11, 12, 13], "cell_count": 4000,
            "bounds": {"min": low, "max": high}, "materials": {"clay": "a37253"},
            "groups": [{"material": "clay", "quads": quads}]}


@unittest.skipUnless(GODOT, "Installed Godot binary required")
class ViewerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="common-viewer-")
        self.folder = Path(self.temp.name)
        self.env = dict(os.environ)
        self.env["HOME"] = str(self.folder)
        for key, subdir in [("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                            ("XDG_CACHE_HOME", "cache")]:
            directory = self.folder / subdir
            directory.mkdir()
            self.env[key] = str(directory)
        self.left = self.write("left.json", fixture())
        self.right = self.write("right.json", fixture(0.05))

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        path = self.folder / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def run_godot(self, *args, script=None):
        command = [GODOT, "--headless", "--path", str(PROJECT), "--audio-driver", "Dummy"]
        if script:
            command.extend(["--script", script])
        result = subprocess.run(command + ["--", *map(str, args)], env=self.env,
                                text=True, capture_output=True, timeout=20)
        output = result.stdout + result.stderr
        self.assertNotIn("SCRIPT ERROR", output, output)
        self.assertNotIn("ERROR:", output.replace("COMMON_VIEWER_ERROR:", "EXPECTED_REJECTION:"), output)
        return result, output

    def validate(self, *extra, left=None):
        return self.run_godot("--left", left or self.left, "--right", self.right,
                              "--validate-only", *extra)

    def report(self, output):
        line = next(line for line in output.splitlines() if line.startswith("COMMON_VIEWER_REPORT="))
        return json.loads(line.split("=", 1)[1])

    def test_all_views_share_scale_and_transform(self):
        for view in ("orbit", "front", "detail"):
            with self.subTest(view=view):
                result, output = self.validate("--view=" + view)
                self.assertEqual(result.returncode, 0, output)
                report = self.report(output)
                self.assertTrue(report["same_camera_transform"])
                self.assertTrue(report["same_camera_scale"])
                self.assertTrue(report["same_viewport_dimensions"])
                self.assertTrue(report["same_master_hash"])
                self.assertFalse(report["screenshot_saved"])
                self.assertEqual([m["pitch"] for m in report["models"]], [0.1, 0.05])
                self.assertEqual(report["models"][0]["render_file_sha256"], hashlib.sha256(self.left.read_bytes()).hexdigest())

    def test_mesh_world_coordinates_normals_and_winding(self):
        result, output = self.run_godot(self.left, script="res://tests/CheckMesh.gd")
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("COMMON_VIEWER_MESH_OK", output)

    def test_detail_target_and_report_file(self):
        destination = self.folder / "nested" / "report.json"
        result, output = self.validate("--view=detail", "--detail-target=2.5,4,6", "--detail-size=0.75", "--report", destination)
        self.assertEqual(result.returncode, 0, output)
        report = json.loads(destination.read_text())
        self.assertAlmostEqual(report["cameras"][0]["orthographic_size"], 0.75)
        self.assertEqual(report["visual_review"], "NOT_PERFORMED_BY_THIS_REPORT")

    def test_rejects_headless_capture_and_existing_report(self):
        result, output = self.validate("--output", self.folder / "capture.png")
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires a graphical renderer", output)
        target = self.folder / "existing.json"
        target.write_text("original evidence")
        result, output = self.validate("--report", target)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Refusing to replace", output)
        self.assertEqual(target.read_text(), "original evidence")

    def test_rejects_invalid_geometry_and_wrong_schema(self):
        changes = [
            (lambda data: data.update(schema="riverstone.voxel.compiled.v1"), "Expected riverstone.voxel.render.v1"),
            (lambda data: data.update(pitch=0), "pitch must be finite and positive"),
            (lambda data: data["groups"][0].update(material="missing"), "known material"),
            (lambda data: data["groups"][0]["quads"][0][0].__setitem__(0, -100), "beyond declared"),
        ]
        for change, message in changes:
            with self.subTest(message=message):
                data = copy.deepcopy(fixture())
                change(data)
                left = self.write("bad.json", data)
                result, output = self.validate(left=left)
                self.assertEqual(result.returncode, 1, output)
                self.assertIn(message, output)

    def test_rgba_and_different_source_are_generic(self):
        data = fixture(0.037)
        data["source_id"] = "arbitrary_source_309"
        data["master_hash"] = "another_master"
        data["materials"]["clay"] = {"rgba": [0.4, 0.6, 0.8, 1.0]}
        left = self.write("generic.json", data)
        result, output = self.validate(left=left)
        self.assertEqual(result.returncode, 0, output)
        self.assertFalse(self.report(output)["same_master_hash"])
        self.assertEqual(self.report(output)["models"][0]["pitch"], 0.037)


if __name__ == "__main__":
    unittest.main()
