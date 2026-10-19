"""Deterministic placement regressions. Run with python -m unittest discover.

These tests deliberately corrupt otherwise valid fixtures. They do not use the
production scene generator, so a generator/validator shared implementation bug
cannot automatically make the fixtures pass.
"""

import copy
import importlib.util
import math
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("placement_under_test", Path(__file__).with_name("placement.py"))
placement = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(placement)


def fixture(gate=False):
    bounds = {"min": [-8.9, 0, -6.9], "max": [8.9, 10, 6.9]} if gate else {"min": [-1, 0, -1], "max": [1, 3, 1]}
    footprint = [[-9, -7], [9, -7], [9, 7], [-9, 7]] if gate else [[-2, -2], [2, -2], [2, 2], [-2, 2]]
    connection = [0, 0] if gate else [0, 4]
    source = {"id": "B1", "district_id": "D09" if gate else "D01", "footprint_xz_m": footprint,
              "functional_role": "gatehouse" if gate else "house", "implementation_tier": "exterior_only",
              "road_access": {"road_id": "R1", "connection_xz_m": connection}}
    if gate:
        source["opening_required_m"] = {"width": 10, "height": 5}
    plan = {"building_plans": [source], "road_nodes": [
        {"id": "N1", "position_m": [0, None, -20] if gate else [-10, None, 4]},
        {"id": "N2", "position_m": [0, None, 20] if gate else [10, None, 4]}],
        "roads": [{"id": "R1", "from_node": "N1", "to_node": "N2", "width_m": 7 if gate else 2, "kind": "cart_street"}],
        "plots": [{"id": "P1", "courtyard_xz_m": [[10, 0], [12, 0], [12, 2], [10, 2]]}]}
    instance = {"id": "I1", "source_footprint_id": "B1", "district_id": source["district_id"],
                "asset_key": "house", "position_m": [0, 0, 0], "yaw_rad": 0,
                "source_footprint_xz_m": copy.deepcopy(footprint), "local_bounds": copy.deepcopy(bounds),
                "entrance": {"position_m": [0, 0, bounds["max"][2]],
                             "local_position_m": [0, 0, bounds["max"][2]], "facade_inset_m": 0, "road_id": "R1",
                             "road_connection_m": [connection[0], 0, connection[1]]},
                "implementation_tier": "exterior_only", "preserved_record": False}
    if gate:
        instance["gate_opening"] = {"local_bounds": {"min": [-5, 0, -6.9], "max": [5, 5, 6.9]}, "road_ids": ["R1"]}
    scene = {"instances": [instance], "assets": {"house": {"render_path": "assets/house.obj", "local_bounds": bounds}}}
    return scene, plan


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.square = [[0, 0], [2, 0], [2, 2], [0, 2]]

    def test_polygon_area_both_orientations_and_large_origin(self):
        self.assertEqual(placement.polygon_area(self.square), 4)
        self.assertEqual(placement.polygon_area(list(reversed(self.square))), 4)
        self.assertEqual(placement.polygon_area([[p[0] + 1000000, p[1] + 1000000] for p in self.square]), 4)

    def test_concavity_and_self_crossing_rejected(self):
        self.assertFalse(placement.is_convex_polygon([[0, 0], [2, 0], [1, 1], [2, 2], [0, 2]]))
        self.assertFalse(placement.is_convex_polygon([[0, 0], [2, 2], [2, 0], [0, 2]]))
        self.assertFalse(placement.is_convex_polygon(None))

    def test_touching_is_not_positive_area_overlap(self):
        edge = [[2, 0], [4, 0], [4, 2], [2, 2]]
        point = [[2, 2], [4, 2], [4, 4], [2, 4]]
        self.assertFalse(placement.positive_area_overlap(self.square, edge))
        self.assertFalse(placement.positive_area_overlap(self.square, point))
        self.assertEqual(placement.intersection_area(self.square, edge), 0)

    def test_positive_overlap_area_and_winding(self):
        other = [[1, 1], [3, 1], [3, 3], [1, 3]]
        self.assertTrue(placement.positive_area_overlap(self.square, other))
        self.assertAlmostEqual(placement.intersection_area(self.square, other), 1)
        self.assertAlmostEqual(placement.intersection_area(list(reversed(other)), self.square), 1)

    def test_tolerance_is_metres_not_axis_length(self):
        a = [[0, 0], [100, 0], [100, 2], [0, 2]]
        b = [[0, 1.999], [100, 1.999], [100, 4], [0, 4]]
        self.assertAlmostEqual(placement.convex_penetration_m(a, b), 0.001)
        self.assertTrue(placement.positive_area_overlap(a, b))
        self.assertFalse(placement.positive_area_overlap(a, b, 0.002))
        self.assertAlmostEqual(placement.intersection_area(a, b), 0.1)

    def test_small_polygon_contained_deeply_is_not_rounding_sliver(self):
        skinny = [[0.5, 0.5], [0.501, 0.5], [0.501, 1.5], [0.5, 1.5]]
        self.assertTrue(placement.positive_area_overlap(self.square, skinny, 0.002))

    def test_containment_tolerance_is_normalized(self):
        self.assertTrue(placement.point_in_convex_polygon([2.001, 1], self.square))
        self.assertFalse(placement.point_in_convex_polygon([2.003, 1], self.square))
        self.assertTrue(placement.point_in_convex_polygon([1, 1], list(reversed(self.square))))

    def test_right_handed_yaw_and_inverse(self):
        point = placement.transform_point_m([0, 2, 1], [10, 20, 30], math.pi / 2)
        for measured, expected in zip(point, [11, 22, 30]):
            self.assertAlmostEqual(measured, expected)
        recovered = placement.inverse_transform_point_m(point, [10, 20, 30], math.pi / 2)
        for measured, expected in zip(recovered, [0, 2, 1]):
            self.assertAlmostEqual(measured, expected)

    def test_transformed_aabb_uses_rotated_corners(self):
        bounds = {"min": [-2, 0, -1], "max": [2, 3, 1]}
        polygon = placement.transformed_aabb_xz_m(bounds, [0, 0, 0], math.pi / 4)
        self.assertAlmostEqual(placement.polygon_area(polygon), 8)
        self.assertTrue(placement.convex_polygon_contains(polygon, polygon))
        self.assertFalse(placement.point_in_convex_polygon([2, 2], polygon))

    def test_ribbon_area_and_zero_length(self):
        self.assertAlmostEqual(placement.polygon_area(placement.road_ribbon([0, 0], [3, 4], 2)), 10)
        with self.assertRaises(ValueError):
            placement.road_ribbon([1, 1], [1, 1], 3)

    def test_union_coverage_preserves_gap(self):
        left = [[0, 0], [1, 0], [1, 2], [0, 2]]
        right = [[1, 0], [2, 0], [2, 2], [1, 2]]
        self.assertTrue(placement.polygon_covered_by_union(self.square, [left, right], 0))
        right = [[1.1, 0], [2, 0], [2, 2], [1.1, 2]]
        self.assertFalse(placement.polygon_covered_by_union(self.square, [left, right]))
        self.assertAlmostEqual(placement.uncovered_area_by_union(self.square, [left, right]), 0.2)

    def test_union_overlapping_covers_do_not_double_count(self):
        a = [[0, 0], [1.5, 0], [1.5, 2], [0, 2]]
        b = [[0.5, 0], [2, 0], [2, 1], [0.5, 1]]
        self.assertAlmostEqual(placement.uncovered_area_by_union(self.square, [a, b]), 0.5)
        self.assertFalse(placement.polygon_covered_by_union(self.square, [a, b]))

    def test_union_tolerance_is_explicit(self):
        left = [[0, 0], [0.9995, 0], [0.9995, 2], [0, 2]]
        right = [[1.0005, 0], [2, 0], [2, 2], [1.0005, 2]]
        self.assertFalse(placement.polygon_covered_by_union(self.square, [left, right], 0))
        self.assertTrue(placement.polygon_covered_by_union(self.square, [left, right], 0.002))

    def test_union_tolerance_is_not_doubled_at_shared_gap(self):
        left = [[0, 0], [0.9985, 0], [0.9985, 2], [0, 2]]
        right = [[1.0015, 0], [2, 0], [2, 2], [1.0015, 2]]
        self.assertFalse(placement.polygon_covered_by_union(self.square, [left, right], 0.002))


class PlacementTests(unittest.TestCase):
    def validate(self, scene, plan):
        return placement.validate_placements(scene, plan)

    def failed_names(self, result):
        return {x["check"] for x in result["failures"]}

    def test_valid_scene(self):
        result = self.validate(*fixture())
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["counts"]["transformed_aabbs"], 1)

    def test_no_empty_unconditional_pass(self):
        result = self.validate({}, {})
        self.assertFalse(result["passed"])
        self.assertGreaterEqual(result["failure_count"], 3)

    def test_missing_source_coverage_fails(self):
        scene, plan = fixture()
        scene["instances"] = []
        self.assertIn("all_source_buildings_represented", self.failed_names(self.validate(scene, plan)))

    def test_duplicate_instance_id_fails(self):
        scene, plan = fixture()
        scene["instances"].append(copy.deepcopy(scene["instances"][0]))
        self.assertIn("unique_instance_ids", self.failed_names(self.validate(scene, plan)))

    def test_source_footprint_cannot_be_moved_to_hide_overflow(self):
        scene, plan = fixture()
        scene["instances"][0]["position_m"][0] = 10
        scene["instances"][0]["source_footprint_xz_m"] = [[x + 10, z] for x, z in plan["building_plans"][0]["footprint_xz_m"]]
        names = self.failed_names(self.validate(scene, plan))
        self.assertIn("source_footprint_unchanged", names)
        self.assertIn("transformed_aabb_inside_source_footprint", names)

    def test_bounds_overflow_over_two_mm_fails(self):
        scene, plan = fixture()
        scene["instances"][0]["position_m"][0] = 1.003
        self.assertIn("transformed_aabb_inside_source_footprint", self.failed_names(self.validate(scene, plan)))

    def test_nan_transform_fails(self):
        scene, plan = fixture()
        scene["instances"][0]["yaw_rad"] = float("nan")
        self.assertIn("finite_positive_instance_bounds_and_transform", self.failed_names(self.validate(scene, plan)))

    def test_false_bounds_cannot_override_asset_declaration(self):
        scene, plan = fixture()
        scene["instances"][0]["local_bounds"]["max"][0] = 0.5
        self.assertIn("instance_matches_asset_bounds", self.failed_names(self.validate(scene, plan)))

    def test_nested_lod_render_resources_are_validated(self):
        scene, plan = fixture()
        resource = scene["assets"]["house"]
        scene["assets"]["house"] = {"coarse": resource, "fine": copy.deepcopy(resource)}
        self.assertTrue(self.validate(scene, plan)["passed"])
        scene["assets"]["house"]["fine"]["render_path"] = "/absolute/fine.json"
        self.assertIn("asset_render_paths_relative", self.failed_names(self.validate(scene, plan)))

    def test_fine_lod_cannot_escape_declared_placement_bounds(self):
        scene, plan = fixture()
        resource = scene["assets"]["house"]
        fine = copy.deepcopy(resource)
        fine["local_bounds"]["max"][0] = 2.5
        scene["assets"]["house"] = {"coarse": resource, "fine": fine}
        names = self.failed_names(self.validate(scene, plan))
        self.assertIn("instance_matches_asset_bounds", names)
        self.assertIn("transformed_aabb_inside_source_footprint", names)

    def test_malformed_asset_reference_fails_without_crashing(self):
        scene, plan = fixture()
        scene["instances"][0]["asset_key"] = []
        self.assertIn("asset_references", self.failed_names(self.validate(scene, plan)))

    def test_relative_render_path_required(self):
        for path in ("/tmp/building.obj", "C:\\secret\\building.obj", "https://example.com/a.obj", ""):
            scene, plan = fixture()
            scene["assets"]["house"]["render_path"] = path
            self.assertIn("asset_render_paths_relative", self.failed_names(self.validate(scene, plan)))

    def test_wrong_front_and_road_connection_fail(self):
        scene, plan = fixture()
        scene["instances"][0]["entrance"]["position_m"] = [0, 0, -1]
        scene["instances"][0]["entrance"]["road_connection_m"] = [0, 0, 4.1]
        names = self.failed_names(self.validate(scene, plan))
        self.assertIn("entrance_authored_world_transform_consistent", names)
        self.assertIn("connection_on_named_road", names)

    def test_canopy_inset_uses_authored_door(self):
        scene, plan = fixture()
        entrance = scene["instances"][0]["entrance"]
        entrance.update(local_position_m=[0, 0, 0.5], position_m=[0, 0, 0.5], facade_inset_m=0.5)
        result = self.validate(scene, plan)
        self.assertTrue(result["passed"], result["failures"])
        self.assertTrue(result["verification_complete"])

    def test_missing_door_metadata_is_unverified_not_guessed(self):
        scene, plan = fixture()
        entrance = scene["instances"][0]["entrance"]
        del entrance["local_position_m"]
        del entrance["facade_inset_m"]
        entrance["position_m"] = [0, 0, 0.5]
        result = self.validate(scene, plan)
        self.assertTrue(result["passed"], result["failures"])
        self.assertFalse(result["verification_complete"])
        self.assertEqual(result["counts"]["unverified_entrance_local_geometry"], 1)

    def test_false_authored_facade_inset_fails(self):
        scene, plan = fixture()
        scene["instances"][0]["entrance"]["facade_inset_m"] = 0.5
        self.assertIn("entrance_inside_bounds_on_declared_positive_z_facade", self.failed_names(self.validate(scene, plan)))

    def test_ordinary_building_road_collision_fails(self):
        scene, plan = fixture()
        for node in plan["road_nodes"]:
            node["position_m"][2] = 0
        result = self.validate(scene, plan)
        self.assertEqual(result["counts"]["road_overlaps"], 1)

    def test_courtyard_reserved_space_collision_fails(self):
        scene, plan = fixture()
        plan["plots"][0]["courtyard_xz_m"] = [[0, 0], [3, 0], [3, 3], [0, 3]]
        self.assertEqual(self.validate(scene, plan)["counts"]["courtyard_overlaps"], 1)

    def test_cad_overlap_explicitly_reported(self):
        scene, plan = fixture()
        plan["plots"][0]["courtyard_xz_m"] = [[0.999, 0], [3, 0], [3, 1], [0.999, 1]]
        result = self.validate(scene, plan)
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["counts"]["tolerated_positive_area_overlaps"], 1)
        self.assertAlmostEqual(result["tolerated_positive_area_overlaps"][0]["penetration_m"], 0.001)

    def test_meaningful_overlap_not_silenced(self):
        scene, plan = fixture()
        plan["plots"][0]["courtyard_xz_m"] = [[0.997, 0], [3, 0], [3, 1], [0.997, 1]]
        self.assertEqual(self.validate(scene, plan)["counts"]["courtyard_overlaps"], 1)

    def test_cannot_expand_tolerance_to_silence_collision(self):
        with self.assertRaises(ValueError):
            placement.validate_placements(*fixture(), tolerance_m=1)

    def test_distinct_buildings_cannot_overlap(self):
        scene, plan = fixture()
        source = copy.deepcopy(plan["building_plans"][0])
        source["id"] = "B2"
        plan["building_plans"].append(source)
        instance = copy.deepcopy(scene["instances"][0])
        instance.update(id="I2", source_footprint_id="B2")
        scene["instances"].append(instance)
        self.assertEqual(self.validate(scene, plan)["counts"]["building_overlaps"], 1)

    def test_same_source_assembly_may_overlap(self):
        scene, plan = fixture()
        instance = copy.deepcopy(scene["instances"][0])
        instance["id"] = "I2"
        scene["instances"].append(instance)
        self.assertTrue(self.validate(scene, plan)["passed"])

    def test_explicit_gate_opening_passes(self):
        result = self.validate(*fixture(gate=True))
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["counts"]["accepted_gate_road_intersections"], 1)

    def test_gate_without_opening_fails(self):
        scene, plan = fixture(gate=True)
        del scene["instances"][0]["gate_opening"]
        result = self.validate(scene, plan)
        self.assertIn("explicit_gate_opening_contract", self.failed_names(result))
        self.assertEqual(result["counts"]["road_overlaps"], 1)

    def test_gate_does_not_exempt_whole_footprint(self):
        scene, plan = fixture(gate=True)
        for node in plan["road_nodes"]:
            node["position_m"][0] = 7
        self.assertEqual(self.validate(scene, plan)["counts"]["road_overlaps"], 1)

    def test_gate_does_not_exempt_undesigned_road(self):
        scene, plan = fixture(gate=True)
        other = copy.deepcopy(plan["roads"][0])
        other["id"] = "R2"
        plan["roads"].append(other)
        result = self.validate(scene, plan)
        self.assertEqual(result["counts"]["accepted_gate_road_intersections"], 1)
        self.assertEqual(result["counts"]["road_overlaps"], 1)

    def test_gate_does_not_exempt_courtyard(self):
        scene, plan = fixture(gate=True)
        plan["plots"][0]["courtyard_xz_m"] = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
        self.assertEqual(self.validate(scene, plan)["counts"]["courtyard_overlaps"], 1)

    def gate_with_secondary_arch(self, gap=0):
        scene, plan = fixture(gate=True)
        primary = scene["instances"][0].pop("gate_opening")
        primary["road_ids"].append("R2")
        secondary = {"local_bounds": {"min": [5 + gap, 0, -6.9], "max": [8.9, 5, 6.9]}, "road_ids": ["R2"]}
        scene["instances"][0]["gate_openings"] = [primary, secondary]
        plan["road_nodes"].extend([{"id": "N3", "position_m": [6, None, -20]}, {"id": "N4", "position_m": [6, None, 20]}])
        plan["roads"].append({"id": "R2", "from_node": "N3", "to_node": "N4", "width_m": 7, "kind": "cart_street"})
        return scene, plan

    def test_gate_secondary_arch_union_covers_road(self):
        result = self.validate(*self.gate_with_secondary_arch())
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["counts"]["accepted_gate_road_intersections"], 2)

    def test_gate_secondary_arch_union_cannot_bridge_solid_gap(self):
        result = self.validate(*self.gate_with_secondary_arch(gap=0.1))
        self.assertEqual(result["counts"]["road_overlaps"], 1)
        conflict = next(f for f in result["failures"] if f["check"] == "no_road_overlaps")
        self.assertGreater(conflict["detail"]["uncovered_area_m2"], 1)

    def test_gate_secondary_arch_three_mm_gap_is_meaningful(self):
        result = self.validate(*self.gate_with_secondary_arch(gap=0.003))
        self.assertEqual(result["counts"]["road_overlaps"], 1)

    def test_gate_secondary_arch_requires_source_clearance_height(self):
        scene, plan = self.gate_with_secondary_arch()
        scene["instances"][0]["gate_openings"][1]["local_bounds"]["max"][1] = 4.9
        self.assertIn("explicit_gate_opening_contract", self.failed_names(self.validate(scene, plan)))

    def test_gate_cannot_supply_ambiguous_singular_and_plural_openings(self):
        scene, plan = fixture(gate=True)
        scene["instances"][0]["gate_openings"] = [copy.deepcopy(scene["instances"][0]["gate_opening"])]
        self.assertIn("explicit_gate_opening_contract", self.failed_names(self.validate(scene, plan)))

    def test_gate_requires_full_depth_width_height(self):
        for side, coordinate, value in (("min", 0, -4.9), ("max", 1, 4.9), ("max", 2, 6.8)):
            scene, plan = fixture(gate=True)
            scene["instances"][0]["gate_opening"]["local_bounds"][side][coordinate] = value
            self.assertIn("explicit_gate_opening_contract", self.failed_names(self.validate(scene, plan)))

    def test_d09_wall_tower_cannot_claim_gate_exception(self):
        scene, plan = fixture(gate=True)
        plan["building_plans"][0]["functional_role"] = "wall_tower"
        result = self.validate(scene, plan)
        self.assertEqual(result["counts"]["road_overlaps"], 1)
        self.assertIn("explicit_gate_opening_contract", self.failed_names(result))

    def fixture_tower_arch(self):
        scene, plan = fixture()
        plan["building_plans"][0]["functional_role"] = "wall_tower"
        for node in plan["road_nodes"]:
            node["position_m"][2] = 0
        plan["building_plans"][0]["road_access"]["connection_xz_m"] = [0, 0]
        scene["instances"][0]["entrance"]["road_connection_m"] = [0, 0, 0]
        scene["instances"][0]["road_openings"] = [{
            "local_bounds": {"min": [-1, 0, -1], "max": [1, 3, 1]},
            "road_ids": ["R1"], "clearance_height_m": 3}]
        return scene, plan

    def test_explicit_tower_arch_clearance(self):
        result = self.validate(*self.fixture_tower_arch())
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["counts"]["accepted_wall_tower_arch_intersections"], 1)
        self.assertEqual(result["counts"]["accepted_gate_road_intersections"], 0)
        self.assertEqual(result["declared_wall_tower_clearances"][0]["clearance_height_m"], 3)

    def test_tower_arch_does_not_guess_clearance(self):
        scene, plan = self.fixture_tower_arch()
        del scene["instances"][0]["road_openings"][0]["clearance_height_m"]
        self.assertIn("explicit_wall_tower_road_opening_contract", self.failed_names(self.validate(scene, plan)))

    def test_tower_arch_requires_declared_clear_height(self):
        scene, plan = self.fixture_tower_arch()
        scene["instances"][0]["road_openings"][0]["local_bounds"]["max"][1] = 2.9
        self.assertIn("explicit_wall_tower_road_opening_contract", self.failed_names(self.validate(scene, plan)))

    def test_ordinary_building_cannot_claim_tower_arch_exception(self):
        scene, plan = self.fixture_tower_arch()
        plan["building_plans"][0]["functional_role"] = "house"
        result = self.validate(scene, plan)
        self.assertIn("explicit_wall_tower_road_opening_contract", self.failed_names(result))
        self.assertEqual(result["counts"]["road_overlaps"], 1)

    def test_tower_arch_does_not_exempt_unlisted_road(self):
        scene, plan = self.fixture_tower_arch()
        other = copy.deepcopy(plan["roads"][0])
        other["id"] = "R2"
        plan["roads"].append(other)
        result = self.validate(scene, plan)
        self.assertEqual(result["counts"]["accepted_wall_tower_arch_intersections"], 1)
        self.assertEqual(result["counts"]["road_overlaps"], 1)

    def test_wall_walk_exclusion_is_explicit_and_narrow(self):
        scene, plan = fixture()
        for node in plan["road_nodes"]:
            node["position_m"][2] = 0
        plan["roads"][0]["kind"] = "wall_walk"
        result = self.validate(scene, plan)
        self.assertEqual(result["excluded_wall_walk_road_ids"], ["R1"])
        self.assertEqual(result["counts"]["ground_road_segments"], 0)
        self.assertEqual(result["counts"]["road_overlaps"], 0)

    def test_source_wall_access_stair_reservation_is_explicitly_unimplemented(self):
        scene, plan = fixture()
        for node in plan["road_nodes"]:
            node["position_m"][2] = 0
        plan["roads"][0].update(id="WALL_ACCESS_north", route_id="WALL_ACCESS", kind="pedestrian")
        result = self.validate(scene, plan)
        self.assertEqual(result["excluded_stair_to_wall_road_ids"], ["WALL_ACCESS_north"])
        self.assertEqual(result["counts"]["road_overlaps"], 0)
        self.assertTrue(result["vertical_access_unimplemented"])

    def test_other_pedestrian_roads_are_not_exempt(self):
        scene, plan = fixture()
        for node in plan["road_nodes"]:
            node["position_m"][2] = 0
        plan["roads"][0].update(kind="pedestrian", route_id="WALL_ACCESS")
        result = self.validate(scene, plan)
        self.assertEqual(result["counts"]["road_overlaps"], 1)
        self.assertEqual(result["excluded_stair_to_wall_road_ids"], [])


if __name__ == "__main__":
    unittest.main()
