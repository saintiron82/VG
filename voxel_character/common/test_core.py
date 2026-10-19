"""Bounded standard-library tests; no renderer or full asset generation."""
import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from core import (SCHEMA, BudgetExceeded, InvalidMaster, compile_master, contains,
                  prepare_shape, resolve_pitch)
from legacy_adapters import lower_prism_operation, lower_rotational_operation

ROOT = Path(__file__).resolve().parent


def box(low, high, **extra):
    return {"kind": "box", "min": low, "max": high, **extra}


def master(shape=None):
    return {"schema": SCHEMA, "id": "arbitrary-design", "revision": 1,
            "axes": {"up": "+Y", "front": "+Z", "right": "+X"},
            "materials": {"a": "#fff", "b": "#000"},
            "components": [{"id": "component", "parts": [{"id": "part", "pivot": [0, 0, 0]}],
                            "operations": [{"id": "solid", "part": "part", "material": "a", "action": "paint", "shape": shape or box([0, 0, 0], [1, 1, 1])}]}],
            "instances": [{"id": "first", "component": "component"}], "constraints": []}


def coords(result):
    return {tuple(row[:3]) for row in result["cells"]}


class CommonCoreTests(unittest.TestCase):
    def test_half_open_box_and_negative_world_coordinates(self):
        result = compile_master(master(box([-1, -.5, 0], [0, .5, 1])), {"pitch": .5})
        self.assertEqual(len(result["cells"]), 8)
        self.assertEqual({p[0] for p in coords(result)}, {-2, -1})

    def test_requested_resolution_is_not_hardcoded(self):
        for cells in (13, 27):
            result = compile_master(master(), {"reference_span": 1, "cells": cells})
            self.assertEqual(len(result["cells"]), cells**3)
            self.assertAlmostEqual(result["pitch"]*cells, 1)

    def test_determinism_and_immutable_input(self):
        m = master(); original = copy.deepcopy(m)
        self.assertEqual(compile_master(m, {"pitch": .2}), compile_master(m, {"pitch": .2}))
        self.assertEqual(m, original)

    def test_asset_name_does_not_change_geometry(self):
        m = master(); expected = compile_master(m, {"pitch": .2})["cells"]
        for name in ("fountain", "house", "unseen-object"):
            m["id"] = name
            self.assertEqual(compile_master(m, {"pitch": .2})["cells"], expected)

    def test_material_names_do_not_change_geometry(self):
        m = master(); expected = coords(compile_master(m, {"pitch": .2}))
        m["materials"]["arbitrary"] = m["materials"].pop("a")
        m["components"][0]["operations"][0]["material"] = "arbitrary"
        self.assertEqual(coords(compile_master(m, {"pitch": .2})), expected)

    def test_extension_metadata_and_pivots_are_preserved_but_not_executed(self):
        m = master(); original = compile_master(m, {"pitch": .2})
        m["extensions"] = {"physics_contract": {"status": "external_sidecar_only"}}
        m["components"][0]["parts"][0]["pivot"] = [.1, .2, .3]
        m["components"][0]["parts"][0]["metadata"] = {"attachment": "anchor"}
        result = compile_master(m, {"pitch": .2})
        self.assertEqual(result["extensions"], m["extensions"])
        self.assertEqual(result["components"][0]["parts"], m["components"][0]["parts"])
        self.assertEqual(result["cells"], original["cells"])
        self.assertNotEqual(result["master_hash"], original["master_hash"])

    def test_minimum_thickness_is_common_data_rule(self):
        thin = box([0, .005, 0], [1, .015, 1])
        m = master(thin)
        self.assertFalse(compile_master(m, {"pitch": .2})["cells"])
        thin["minimum_cells"] = [0, 1, 0]
        result = compile_master(m, {"pitch": .2})
        self.assertEqual(len(result["cells"]), 25)
        self.assertEqual({p[1] for p in coords(result)}, {0})

    def test_cut_is_real_empty_geometry(self):
        m = master()
        opening = box([.4, 0, 0], [.6, .8, 1])
        m["components"][0]["operations"].append({"id": "opening", "part": "part", "action": "cut", "shape": opening})
        m["constraints"] = [{"id": "clear", "kind": "empty_region", "selector": {}, "shape": opening}]
        result = compile_master(m, {"pitch": .2})
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["cells"]), 105)

    def test_empty_region_requires_sampled_extent(self):
        m = master()
        m["constraints"] = [{"id": "subcell_void", "kind": "empty_region", "selector": {}, "shape": box([2, 0, 0], [2.01, .01, .01])}]
        result = compile_master(m, {"pitch": .2})
        self.assertFalse(result["valid"])
        self.assertEqual(result["constraints"][0]["sampled_region_cells"], 0)

    def test_missing_required_feature_fails(self):
        m = master()
        m["constraints"] = [{"id": "required", "kind": "nonempty", "selector": {"feature": "missing"}}]
        self.assertFalse(compile_master(m, {"pitch": .2})["valid"])

    def test_transform_rotation_and_shared_grid_phase(self):
        m = master(box([0, 0, 0], [1, .5, .5]))
        m["instances"][0]["transform"] = {"translation": [.03, 0, -.07], "basis": [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]}
        result = compile_master(m, {"pitch": .1})
        self.assertEqual(len(result["cells"]), 250)
        self.assertEqual({p[2] for p in coords(result)}, set(range(-11, -1)))

    def test_parent_transform_and_cycle_rejection(self):
        m = master(box([0, 0, 0], [.2, .2, .2]))
        m["instances"][0]["transform"] = {"translation": [1, 0, 0]}
        m["instances"].append({"id": "second", "component": "component", "parent": "first", "transform": {"translation": [1, 0, 0]}})
        result = compile_master(m, {"pitch": .2})
        self.assertEqual({p[0] for p in coords(result)}, {5, 10})
        m["instances"][0]["parent"] = "second"
        with self.assertRaisesRegex(InvalidMaster, "cycle"):
            compile_master(m, {"pitch": .2})

    def test_explicit_world_cut_targets_only_selected_instance(self):
        m = master()
        m["instances"].append({"id": "second", "component": "component", "transform": {"translation": [2, 0, 0]}})
        m["assembly_cuts"] = [{"id": "penetration", "shape": box([0, 0, 0], [3, 1, 1]), "selector": {"instance": "first"}}]
        result = compile_master(m, {"pitch": .2})
        self.assertEqual(len(result["cells"]), 125)
        self.assertEqual({row[3] for row in result["cells"]}, {"second"})

    def test_local_cut_does_not_erase_overlapping_prior_instance(self):
        m = master()
        second = copy.deepcopy(m["components"][0]); second["id"] = "cut_component"
        second["operations"].append({"id": "hole", "part": "part", "action": "cut", "shape": box([.4, 0, 0], [.6, 1, 1])})
        m["components"].append(second)
        m["instances"].append({"id": "second", "component": "cut_component"})
        result = compile_master(m, {"pitch": .2})
        self.assertEqual(len(result["cells"]), 125)
        self.assertEqual(sum(row[3] == "first" for row in result["cells"]), 25)

    def test_targeted_assembly_cut_preserves_underlying_other_instance(self):
        m = master()
        m["instances"].append({"id": "second", "component": "component"})
        m["assembly_cuts"] = [{"id": "cut_second", "shape": box([.4, 0, 0], [.6, 1, 1]), "selector": {"instance": "second"}}]
        result = compile_master(m, {"pitch": .2})
        self.assertEqual(len(result["cells"]), 125)
        self.assertEqual(sum(row[3] == "first" for row in result["cells"]), 25)

    def test_scale_invariant_boundary_tolerance(self):
        for size in (1, 1e-8, 1e-9):
            result = compile_master(master(box([0, 0, 0], [size]*3)), {"pitch": size/10})
            self.assertEqual(len(result["cells"]), 1000, size)

    def test_compiled_origin_does_not_alias_source(self):
        m = master(); m["grid_origin"] = [0, 0, 0]
        result = compile_master(m, {"pitch": .2})
        result["grid_origin"][0] = 99
        self.assertEqual(m["grid_origin"], [0, 0, 0])
        m["grid_origin"][1] = 88
        self.assertEqual(result["grid_origin"][1], 0)

    def test_connected_and_touch_report_real_break(self):
        m = master()
        m["instances"].append({"id": "second", "component": "component", "transform": {"translation": [2, 0, 0]}})
        m["constraints"] = [{"id": "joined", "kind": "touch", "a": {"instance": "first"}, "b": {"instance": "second"}},
                            {"id": "single_component", "kind": "connected", "selector": {}}]
        self.assertFalse(compile_master(m, {"pitch": .2})["valid"])
        m["instances"][1]["transform"]["translation"] = [1, 0, 0]
        self.assertTrue(compile_master(m, {"pitch": .2})["valid"])

    def test_budget_is_execution_limit_not_master_dimension_cap(self):
        m = master(box([0, 0, 0], [100, 100, 100]))
        with self.assertRaises(BudgetExceeded):
            compile_master(m, {"pitch": .1}, max_candidate_cells=100)
        result = compile_master(m, {"pitch": 50}, max_candidate_cells=100)
        self.assertEqual(len(result["cells"]), 8)

    def test_output_budget(self):
        with self.assertRaises(BudgetExceeded):
            compile_master(master(), {"pitch": .2}, max_output_cells=10)

    def test_tube_minimum_radius_and_connectivity(self):
        m = master({"kind": "tube", "points": [[0, 0, 0], [0, 1, 0]], "radius": .01, "minimum_radius_cells": .75})
        m["constraints"] = [{"id": "connected", "kind": "connected", "selector": {}}]
        self.assertTrue(compile_master(m, {"pitch": .2})["valid"])

    def test_unknown_shape_never_silently_omitted(self):
        with self.assertRaisesRegex(InvalidMaster, "unsupported shape"):
            compile_master(master({"kind": "special_house"}), {"pitch": .2})
        with self.assertRaisesRegex(ValueError, "no silent fallback"):
            lower_rotational_operation({"id": "outlet", "kind": "radial_spillways", "part": "a", "role": "a"})

    def test_invalid_numeric_and_transform_inputs(self):
        for pitch in (0, -1, float("nan"), float("inf"), 10**500):
            with self.assertRaises(InvalidMaster):
                resolve_pitch({"pitch": pitch})
        m = master(); m["instances"][0]["transform"] = {"basis": [[2, 0, 0], [0, 1, 0], [0, 0, 1]]}
        with self.assertRaisesRegex(InvalidMaster, "orthonormal"):
            compile_master(m, {"pitch": .2})

    def test_prism_adapter_lowers_beam_and_slope_as_data(self):
        beam = lower_prism_operation({"kind": "beam_xy", "a": [0, 0, 0], "b": [1, 1, 0], "width": .2, "depth": .2, "material": "a"}, "beam", "part")
        self.assertTrue(contains(prepare_shape(beam["shape"], .1), [.5, .5, 0]))
        self.assertFalse(contains(prepare_shape(beam["shape"], .1), [.1, .9, 0]))
        slope = lower_prism_operation({"kind": "slope", "x0": 0, "x1": 1, "z0": 0, "z1": 1, "intercept": 1, "gradient": -1, "thickness": .2, "material": "a"}, "slope", "part")
        self.assertTrue(contains(prepare_shape(slope["shape"], .1), [.5, .4, .5]))

    def test_bezier_frontend_does_not_depend_on_output_resolution(self):
        source = {"id": "path", "kind": "radial_bezier_tubes", "part": "part", "role": "a", "count": 2, "phase_degrees": 45, "curve_radius_y": [[1, 1], [1, 2], [2, 1], [2, 0]], "radius": .03, "minimum_visible_cells": 1}
        result = lower_rotational_operation(source)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]["shape"]["points"]), 65)
        self.assertEqual(result, lower_rotational_operation(source))

    def test_actual_source_slices_use_same_core_at_two_pitches(self):
        for name in ("wall_window", "basin_support"):
            m = json.loads((ROOT/"examples"/f"{name}.json").read_text())
            for pitch in (.2, .1):
                with self.subTest(asset=name, pitch=pitch):
                    result = compile_master(m, {"pitch": pitch})
                    self.assertTrue(result["valid"], result["constraints"])
                    self.assertEqual(result["payload_hash"], compile_master(m, {"pitch": pitch})["payload_hash"])
                    self.assertEqual(len(result["constraints"]), 5)

    def test_cli_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/"master.json", Path(folder)/"out.json"
            source.write_text(json.dumps(master()))
            command = [sys.executable, str(ROOT/"core.py"), str(source), "--pitch", ".2", "--output", str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
            original = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 1)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
