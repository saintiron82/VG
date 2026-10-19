import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from author_lane import author, compile_master, covered_rect, digest, make_render_data, polygon


def spec_small(pitch=0.0125):
    spec = json.loads((HERE/"inputs/lane_rules.json").read_text())
    spec["bounds"] = {"rect": [-2, 7, 2, 9]}
    spec["walking_corridor"] = {"rect": [-1, 7, 1, 9]}
    spec["pitch"] = pitch
    spec["bevel_inset"] = pitch
    return spec


def compiled(spec):
    bundle = author(spec)
    result = compile_master(bundle["surface"], {"pitch": spec["pitch"]})
    return bundle, result


class LaneRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = spec_small()
        cls.bundle, cls.output = compiled(cls.spec)

    def test_author_deterministic_and_source_immutable(self):
        spec = copy.deepcopy(self.spec)
        before = copy.deepcopy(spec)
        one, two = author(spec), author(spec)
        self.assertEqual(spec, before)
        self.assertEqual(one, two)
        changed = copy.deepcopy(spec)
        changed["seed"] += 1
        self.assertNotEqual(digest(author(changed)["surface"]), digest(one["surface"]))

    def test_common_compile_deterministic_and_master_immutable(self):
        master = self.bundle["surface"]
        before = copy.deepcopy(master)
        again = compile_master(master, {"pitch": self.spec["pitch"]})
        self.assertEqual(master, before)
        self.assertEqual(again, self.output)
        self.assertTrue(again["valid"])
        self.assertEqual(make_render_data(again), make_render_data(self.output))

    def test_true_voxel_bounds_joints_and_bevel(self):
        pitch, origin = self.output["pitch"], self.output["grid_origin"]
        heights = set()
        columns = {}
        for cell in self.output["cells"]:
            x, y, z = [origin[i]+cell[i]*pitch for i in range(3)]
            self.assertGreaterEqual(x, -2-1e-8)
            self.assertLessEqual(x+pitch, 2+1e-8)
            self.assertGreaterEqual(z, 7-1e-8)
            self.assertLessEqual(z+pitch, 9+1e-8)
            self.assertLessEqual(y+pitch, 1e-8)
            if cell[5] == "joint":
                self.assertLessEqual(y+pitch, -0.025+1e-8)
            key = (cell[0], cell[2])
            columns[key] = max(columns.get(key, -1), round(y+pitch, 6))
        heights = set(columns.values())
        self.assertEqual(heights, {-0.025, -0.0125, 0.0})
        self.assertGreater(sum(v == -0.025 for v in columns.values()), 100)
        self.assertGreater(sum(v == -0.0125 for v in columns.values()), 100)
        self.assertGreater(sum(v == 0 for v in columns.values()), 100)

    def test_varied_dimensions_four_coherent_stone_tones(self):
        stones = self.bundle["stones"]
        self.assertGreaterEqual(len({s["length"] for s in stones}), 4)
        self.assertGreaterEqual(len({s["width"] for s in stones}), 3)
        self.assertEqual(len({s["material"] for s in stones}), 4)
        by_stone = {}
        for c in self.output["cells"]:
            if c[4] == "stone":
                by_stone.setdefault(c[6].rsplit("_", 1)[0], set()).add(c[5])
        self.assertTrue(all(len(tones) == 1 for tones in by_stone.values()))

    def test_flat_continuous_collision_independent_support(self):
        collision = self.bundle["collision"]
        self.assertFalse(collision["surface_collision"])
        self.assertEqual(collision["boxes"], [{"id": "flat_support_0000", "min": [-2.0, -1, 7.0], "max": [2.0, 0, 9.0]}])
        support = compile_master(self.bundle["support"], {"pitch": 1.0})
        render = make_render_data(support)
        self.assertEqual(support["pitch"], 1.0)
        self.assertEqual(render["cell_count"], 8)
        self.assertAlmostEqual(render["bounds"]["max"][1], -0.0375)
        self.assertEqual(collision["walking_corridor"]["rect"], [-1, 7, 1, 9])

    def test_polygon_boundary_and_hole_exclusions(self):
        spec = spec_small(0.025)
        spec["bounds"] = {"polygon": [[-2,7],[2,7],[2,8],[1.5,8],[1.5,9],[-2,9]]}
        spec["holes"] = [{"rect": [-1.9,7.2,-1.3,7.8]}]
        bundle, output = compiled(spec)
        outline = polygon(spec["bounds"])
        holes = [polygon(h) for h in spec["holes"]]
        origin, pitch = output["grid_origin"], output["pitch"]
        footprints = set((c[0], c[2]) for c in output["cells"])
        for x, z in footprints:
            rect = [origin[0]+x*pitch, origin[2]+z*pitch, origin[0]+(x+1)*pitch, origin[2]+(z+1)*pitch]
            self.assertTrue(covered_rect(rect, outline, holes), rect)
        for box in bundle["collision"]["boxes"]:
            rect = [box["min"][0],box["min"][2],box["max"][0],box["max"][2]]
            self.assertTrue(covered_rect(rect, outline, holes), box)
        support = compile_master(bundle["support"], {"pitch": 1.0})
        origin = support["grid_origin"]
        for cell in support["cells"]:
            rect = [origin[0]+cell[0], origin[2]+cell[2], origin[0]+cell[0]+1, origin[2]+cell[2]+1]
            self.assertTrue(covered_rect(rect, outline, holes), rect)

    def test_both_supported_surface_pitches(self):
        spec = spec_small(0.025)
        bundle, output = compiled(spec)
        self.assertTrue(output["valid"])
        self.assertEqual(output["pitch"], 0.025)
        render = make_render_data(output)
        self.assertAlmostEqual(render["bounds"]["max"][1], 0)
        self.assertEqual(bundle["surface"]["extensions"]["lane"]["joint_y"], -0.025)

    def test_reject_corridor_holes_and_unbounded_budget(self):
        spec = spec_small()
        spec["holes"] = [{"rect": [-0.1, 7.5, 0.1, 7.7]}]
        with self.assertRaisesRegex(ValueError, "corridor"):
            author(spec)
        spec = spec_small()
        spec["bounds"] = {"rect": [-20,0,20,40]}
        with self.assertRaisesRegex(ValueError, "bounded patch"):
            author(spec)

    def test_reject_self_crossing_polygon(self):
        with self.assertRaisesRegex(ValueError, "simple"):
            polygon({"polygon": [[0,0],[3,3],[0,2],[2,0]]})
        with self.assertRaisesRegex(ValueError, "distinct"):
            polygon({"polygon": [[0,0],[1,0],[1,1],[0,0]]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
