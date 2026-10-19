"""Cheap source-level guardrails; numerical/renderer checks live in Godot.

This intentionally does not claim to profile Godot's internal allocations. It
checks explicit allocations on the runtime tick call graph and frozen ownership.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def functions(source: str) -> dict[str, str]:
    matches = list(re.finditer(r"^(?:static )?func (\w+)\([^\n]*", source, re.M))
    return {
        match.group(1): source[match.start(): matches[i + 1].start() if i + 1 < len(matches) else len(source)]
        for i, match in enumerate(matches)
    }


class RuntimeContractTests(unittest.TestCase):
    def test_canonical_static_renderer_is_byte_identical(self):
        local = (ROOT / "RenderData.gd").read_bytes()
        canonical = (ROOT.parent / "preview/RenderData.gd").read_bytes()
        self.assertEqual(local, canonical)
        self.assertEqual(hashlib.sha256(local).hexdigest(), hashlib.sha256(canonical).hexdigest())

    def test_tick_call_graph_has_no_explicit_heap_container_or_object_allocation(self):
        source = (ROOT / "CellPools.gd").read_text()
        funcs = functions(source)
        tick = ("seek", "advance", "pause", "play", "stop", "_threshold_value", "_apply")
        forbidden = (
            r"\.new\s*\(", r"\b(?:Array|Dictionary|Packed\w+Array)\s*\(",
            r"=\s*\[", r"=\s*\{", r"\brange\s*\(",
            r"\.(?:resize|append|append_array|duplicate|get_children)\s*\(",
            r"\b(?:state|configure|clear)\s*\(",
        )
        for name in tick:
            body = funcs[name]
            for expression in forbidden:
                self.assertIsNone(re.search(expression, body), (name, expression))

    def test_fixed_capacity_is_allocated_only_during_configuration(self):
        funcs = functions((ROOT / "CellPools.gd").read_text())
        self.assertIn("pool.multimesh.instance_count = pool.capacity", funcs["configure"])
        self.assertNotIn("instance_count =", funcs["seek"])
        self.assertNotRegex(funcs["_apply"], r"(?<!visible_)instance_count\s*=")
        self.assertIn("pool.multimesh.visible_instance_count = visible", funcs["_apply"])

    def test_runtime_is_asset_agnostic_and_has_no_physics(self):
        source = (ROOT / "CellPools.gd").read_text()
        self.assertNotRegex(source.lower(), r"fountain|droplet|plume|splash|house|rigidbody|physicsserver|intersect_ray")
        self.assertNotRegex(functions(source)["_apply"], r"(?:pool\.id|source_id)\s*(?:==|!=|in\b)")
        self.assertNotRegex(source, r"\b(?:randf|randi|randomize|load)\s*\(")

    def test_preview_uses_explicit_fixed_fps_movie_clock(self):
        source = (ROOT / "Preview.gd").read_text()
        self.assertIn('"--write-movie"', source)
        self.assertIn('"--fixed-fps"', source)
        self.assertIn("movie_time = movie_start_time + float(movie_frame_count) / movie_fps", source)
        self.assertNotIn("movie_time +=", source)
        self.assertIn("player.seek(movie_time)", source)
        self.assertIn('if options.has("capture-fps"):', source)
        self.assertIn('movie_fps = float(options["capture-fps"])', source)
        self.assertIn('--capture-fps must be positive', source)
        self.assertIn("Headless preview is only for --validate-only", source)
        self.assertIn("PNG evidence requires a graphical renderer", source)


if __name__ == "__main__":
    unittest.main()
