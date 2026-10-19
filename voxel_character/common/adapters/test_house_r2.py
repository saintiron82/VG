"""Read-only house adapter checks and tiny source-contract mutation cases."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from house_r2 import COMMON, PROJECT, adapt, build, digest, load_authoring
from compare_house_r2 import compare, load_legacy, metrics
from check_house_clearance import static_only_master
from core import compile_master

RESULTS = Path(__file__).resolve().parent/"results"/"house_r2_pitch_0.1"


class HouseR2AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.definitions, cls.instances = load_authoring(COMMON.parent/"house")
        cls.master = json.loads((RESULTS/"master.json").read_text())
        cls.compiled = json.loads((RESULTS/"compiled.json").read_text())

    def test_complete_authoring_recipe_lowered(self):
        self.assertEqual(len(self.master["components"]), len(self.definitions))
        self.assertEqual(len(self.master["instances"]), len(self.instances))
        self.assertEqual(len(self.master["instances"]), 134)
        self.assertEqual(sum(len(c["operations"]) for c in self.master["components"]), 505)
        self.assertEqual({c["id"] for c in self.master["components"]}, set(self.definitions))

    def test_adapter_is_deterministic_and_source_is_unchanged(self):
        self.assertEqual(digest(build(COMMON.parent/"house")), digest(self.master))
        original = copy.deepcopy(self.source)
        a = adapt(self.source, self.definitions, self.instances, [])
        b = adapt(self.source, self.definitions, self.instances, [])
        self.assertEqual(a, b)
        self.assertEqual(self.source, original)

    def test_single_source_to_project_normalization(self):
        mapped = {i["id"]: i for i in self.master["instances"]}
        for instance in self.instances:
            x, y, z = instance["origin"]
            self.assertEqual(mapped[instance["id"]]["transform"]["translation"], [-x, y, -z])
        door = self.master["extensions"]["rigid_joint_contracts"][0]
        self.assertEqual(door["pivot_world"], [.65, .6, 2.72])
        self.assertEqual(door["open_degrees"], 105)
        entrance = self.master["extensions"]["entrance_contract"]
        self.assertEqual(entrance["threshold_world"], [0, .6, 2.6])
        self.assertEqual(entrance["forward_into_house"], [0, 0, -1])
        self.assertIsNone(entrance["interior_id"])
        self.assertEqual(entrance["interior_status"], "NOT_BUILT")

    def test_changed_coordinate_contract_rejected(self):
        source = copy.deepcopy(self.source)
        source["coordinate_system"]["source_to_project"]["rotation_y_degrees"] = 90
        with self.assertRaisesRegex(ValueError, "coordinate contract"):
            adapt(source, self.definitions, self.instances, [])

    def test_external_hinge_not_fabricated_as_geometry_parent(self):
        door = next(i for i in self.master["instances"] if i["id"] == "front_door_leaf")
        self.assertNotIn("parent", door)
        self.assertEqual(door["metadata"]["parent"], "front_door_hinge")
        self.assertTrue(door["metadata"]["dynamic"])

    def test_world_cut_targets_exactly_authored_cover_instances(self):
        expected = {i["id"] for i in self.instances if self.definitions[i["module"]]["category"] == "roof"}
        self.assertEqual(set(self.master["assembly_cuts"][0]["selector"]["instance"]), expected)
        self.assertNotIn("chimney", expected)

    def test_all_current_constraints_pass_but_do_not_imply_visual_approval(self):
        self.assertTrue(self.compiled["valid"])
        self.assertEqual(len(self.compiled["constraints"]), 15)
        self.assertTrue(all(c["pass"] for c in self.compiled["constraints"]))
        self.assertEqual(self.compiled["extensions"]["scope"]["visual_review"], "NOT_RUN")
        self.assertEqual(self.compiled["pitch"], .1)

    def test_numerical_shadow_report_and_part_contract(self):
        report = compare(COMMON.parent/"house/generated/pitch_0.1", RESULTS/"compiled.json", RESULTS/"master.json")
        self.assertEqual(report["aggregate"]["legacy_cells"], 71454)
        self.assertEqual(report["aggregate"]["common_cells"], 71173)
        self.assertEqual(report["aggregate"]["removed_cells"], 1159)
        self.assertEqual(report["aggregate"]["added_cells"], 878)
        self.assertEqual(report["aggregate"]["material_changes_on_shared_cells"], 257)
        self.assertFalse(report["aggregate"]["same_occupancy_and_material"])
        self.assertTrue(report["part_contract"]["material_table_equal"])
        self.assertTrue(report["part_contract"]["instance_component_mapping_equal"])
        self.assertTrue(report["part_contract"]["joint_contracts_equal_after_normalization"])
        self.assertTrue(report["part_contract"]["entrance_contract_equal_after_normalization"])
        self.assertTrue(report["part_contract"]["external_parent_and_dynamic_metadata_equal"])
        self.assertTrue(report["source_files_match_adapter_provenance"])
        self.assertEqual(report["bounds_metres"]["legacy"], report["bounds_metres"]["common"])

    def test_tampered_master_or_payload_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            master, compiled = Path(folder)/"master.json", Path(folder)/"compiled.json"
            master.write_text(json.dumps(self.master))
            data = copy.deepcopy(self.compiled)
            data["cells"][0][5] = "tampered-material"
            compiled.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "payload hash"):
                compare(COMMON.parent/"house/generated/pitch_0.1", compiled, master)
            compiled.write_text(json.dumps(self.compiled))
            changed = copy.deepcopy(self.master); changed["revision"] = 3
            master.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "does not belong"):
                compare(COMMON.parent/"house/generated/pitch_0.1", compiled, master)

    def test_different_legacy_source_revision_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            master, compiled = Path(folder)/"master.json", Path(folder)/"compiled.json"
            changed = copy.deepcopy(self.master); changed["provenance"]["source_design_hash"] = "wrong-revision"
            data = copy.deepcopy(self.compiled); data["master_hash"] = digest(changed)
            master.write_text(json.dumps(changed)); compiled.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "same source design"):
                compare(COMMON.parent/"house/generated/pitch_0.1", compiled, master)

    def test_physics_consumed_core_source_unchanged(self):
        baseline = json.loads((COMMON/"verification.json").read_text())
        self.assertEqual(self.compiled["compiler_source_hash"], baseline["runs"][0]["compiler_source_hash"])

    def test_different_authoring_recipe_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            master, compiled = Path(folder)/"master.json", Path(folder)/"compiled.json"
            changed = copy.deepcopy(self.master)
            next(item for item in changed["provenance"]["source_files"] if item["path"].endswith("generate_house.py"))["sha256"] = "wrong-recipe"
            data = copy.deepcopy(self.compiled); data["master_hash"] = digest(changed)
            master.write_text(json.dumps(changed)); compiled.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "recipe hashes differ"):
                compare(COMMON.parent/"house/generated/pitch_0.1", compiled, master)

    def test_joint_metadata_change_is_reported_as_contract_difference(self):
        with tempfile.TemporaryDirectory() as folder:
            compiled = Path(folder)/"compiled.json"
            data = copy.deepcopy(self.compiled)
            data["extensions"]["rigid_joint_contracts"][0]["open_degrees"] = 90
            compiled.write_text(json.dumps(data))
            report = compare(COMMON.parent/"house/generated/pitch_0.1", compiled, RESULTS/"master.json")
            self.assertFalse(report["part_contract"]["joint_contracts_equal_after_normalization"])

    def test_static_only_check_catches_blocker_hidden_by_dynamic_child(self):
        m = copy.deepcopy(self.master)
        shape = {"kind": "box", "min": [-.4, 1.0, 2.7], "max": [-.3, 1.1, 2.8]}
        m["components"] = [{"id": "box", "parts": [{"id": "solid", "pivot": [0, 0, 0]}], "operations": [{"id": "box", "part": "solid", "material": "plaster", "action": "paint", "shape": shape}]}]
        m["instances"] = [{"id": "front_door_bay", "component": "box"}, {"id": "front_door_leaf", "component": "box", "metadata": {"dynamic": True}}]
        m["assembly_cuts"] = []
        m["constraints"] = [c for c in m["constraints"] if c["id"] == "authored_entry_clearance"]
        self.assertTrue(compile_master(m, {"pitch": .1})["valid"])
        self.assertFalse(compile_master(static_only_master(m), {"pitch": .1})["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
