"""Compact sequential checks. No GUI and no whole-city/fine landmark compile."""
from __future__ import annotations

import copy
import itertools
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from voxel_character.common import coordinate_planes, core, render_data
from world_city.runtime_city.landmarks.author import PALETTE, SUPPORTED_KINDS, make_master


COMPACT = {
    "castle_keep": (16,12,12), "cathedral": (8,16,16),
    "town_hall": (12,8,10), "gatehouse": (18,14,18),
    "wall_tower": (5,5,8), "monastery": (12,12,8),
    "church": (8,14,12), "warehouse": (8,10,8),
}
PLANNING = {
    "castle_keep": (70,38,32), "cathedral": (32,80,70),
    "town_hall": (46,24,24), "gatehouse": (18,14,22),
    "wall_tower": (11,11,18), "monastery": (36,30,14),
    "church": (14,30,24), "warehouse": (16,20,12),
}


def spec(kind, dimensions):
    return dict(asset_id="test_"+kind, kind=kind,
                **dict(zip(("width_m","depth_m","height_m"),dimensions)))


def paint_bounds(master):
    lows, highs = [], []
    for comp in master["components"]:
        for op in comp["operations"]:
            if op["action"] != "paint":
                continue
            lo,hi = core.shape_bounds(op["shape"])
            points = [core.apply(core.transform(op.get("transform")), p)
                      for p in itertools.product(*zip(lo,hi))]
            lows.append([min(p[i] for p in points) for i in range(3)])
            highs.append([max(p[i] for p in points) for i in range(3)])
    return [min(p[i] for p in lows) for i in range(3)], [max(p[i] for p in highs) for i in range(3)]


class LandmarkTests(unittest.TestCase):
    def test_all_planning_masters_validate_without_large_compile(self):
        for kind, dimensions in PLANNING.items():
            with self.subTest(kind=kind):
                master=make_master(spec(kind,dimensions))
                core.validate_master(master,.5)
                core.validate_master(master,.25)
                self.assertEqual(master["axes"],{"up":"+Y","front":"+Z","right":"+X"})
                self.assertEqual(master["extensions"]["landmark_kind"],kind)
                self.assertGreaterEqual(len(master["extensions"]["exterior_features"]),3)

    def test_total_continuous_envelopes(self):
        for source in (COMPACT, PLANNING):
            for kind, dimensions in source.items():
                with self.subTest(kind=kind,dimensions=dimensions):
                    master=make_master(spec(kind,dimensions))
                    lo,hi=paint_bounds(master)
                    env=master["extensions"]["total_envelope_m"]
                    for axis in range(3):
                        self.assertAlmostEqual(lo[axis],env["min"][axis],places=7)
                        self.assertAlmostEqual(hi[axis],env["max"][axis],places=7)

    def test_compact_common_compile_and_export(self):
        for kind, dimensions in COMPACT.items():
            with self.subTest(kind=kind):
                master=make_master(spec(kind,dimensions))
                compiled=coordinate_planes.compile_master(master,{"pitch":.5},
                    max_candidate_cells=250_000,max_output_cells=100_000)
                self.assertTrue(compiled["valid"],compiled["constraints"])
                render=render_data.make_render_data(compiled)
                self.assertGreater(render["quad_count"],0)
                self.assertLess(compiled["candidate_cells"],250_000)
                self.assertLess(len(compiled["cells"]),100_000)

    def test_gate_passage_clear_at_both_requested_pitches(self):
        master=make_master(spec("gatehouse",COMPACT["gatehouse"]))
        for pitch in (.5,.25):
            with self.subTest(pitch=pitch):
                compiled=coordinate_planes.compile_master(master,{"pitch":pitch},
                    max_candidate_cells=500_000,max_output_cells=200_000)
                self.assertTrue(compiled["valid"])
                clear=[c for c in compiled["constraints"] if c["kind"]=="empty_region"][0]
                self.assertEqual(clear["blocked_cells"],0)
                self.assertGreater(clear["sampled_region_cells"],0)
                for row in compiled["cells"]:
                    x,y,z=[(v+.5)*pitch for v in row[:3]]
                    self.assertFalse(-5 <= x < 5 and 0 <= y < 5 and -7 <= z < 7)

    def test_gate_enforces_minimum_functional_envelope(self):
        for dims in ((12,14,18),(18,14,8)):
            with self.assertRaisesRegex(ValueError,"10 m x 5 m passage"):
                make_master(spec("gatehouse",dims))

    def test_west_gate_secondary_opening_cuts_every_layer(self):
        source=spec("gatehouse",(18,14,22))
        baseline=make_master(source)
        source["secondary_openings"]=[{"min":[-9,0,0],"max":[-5,5,7]}]
        master=make_master(source)
        self.assertEqual(baseline["assembly_cuts"],[])
        self.assertEqual(len(master["assembly_cuts"]),1)
        self.assertEqual(master["extensions"]["secondary_openings"],source["secondary_openings"])
        for pitch in (.5,.25):
            with self.subTest(pitch=pitch):
                result=coordinate_planes.compile_master(master,{"pitch":pitch})
                self.assertTrue(result["valid"],result["constraints"])
                check=next(c for c in result["constraints"] if c["id"]=="secondary_opening_0_clearance")
                self.assertEqual(check["blocked_cells"],0)
                self.assertGreater(check["sampled_region_cells"],0)

    def test_invalid_secondary_openings_rejected(self):
        cases=[None,{},[{"min":[-10,0,0],"max":[-5,5,7]}],
               [{"min":[-9,0,0],"max":[-5,float("nan"),7]}],
               [{"min":[-9,0,0],"max":[-9,5,7]}]]
        for opening in cases:
            source=spec("gatehouse",(18,14,22));source["secondary_openings"]=opening
            with self.subTest(opening=opening),self.assertRaises(ValueError):
                make_master(source)
        source=spec("cathedral",(11,11,18))
        source["secondary_openings"]=[{"min":[-5,0,0],"max":[0,5,5]}]
        with self.assertRaisesRegex(ValueError,"gatehouse or wall_tower only"):
            make_master(source)

    def test_lane_tower_opening_preserves_rear_ground_support(self):
        source=spec("wall_tower",(10,10,18))
        source["secondary_openings"]=[{"min":[-5,0,2.5],"max":[5,3,5]}]
        master=make_master(source)
        support=master["extensions"]["secondary_opening_support"]
        self.assertTrue(support["rear_half_ground_shell_retained"])
        self.assertTrue(support["clearance_is_game_design_inference"])
        portal=master["extensions"]["entrances"][0]
        self.assertEqual(portal["threshold_local_m"],[0,0,5])
        self.assertEqual((portal["clear_width_m"],portal["clear_height_m"]),(10,3))
        self.assertEqual(portal["door_state"],"no_leaf")
        self.assertFalse(portal["through_passage"])
        self.assertFalse(portal["interior_transition_available"])
        self.assertNotIn("doors",[c["id"] for c in master["components"]])
        for pitch in (.5,.25):
            with self.subTest(pitch=pitch):
                result=coordinate_planes.compile_master(master,{"pitch":pitch})
                self.assertTrue(result["valid"],result["constraints"])
                check=next(c for c in result["constraints"] if c["id"]=="secondary_opening_0_clearance")
                self.assertEqual(check["blocked_cells"],0)
                positions=[[(n+.5)*pitch for n in row[:3]] for row in result["cells"]]
                self.assertEqual(sum(-5 <= x < 5 and 0 <= y < 3 and 2.5 <= z < 5
                                     for x,y,z in positions),0)
                self.assertTrue(any(abs(x)<.5 and y<.5 and z<-4.5 for x,y,z in positions))
                self.assertTrue(any(x<-4.5 and y<.5 and z<0 for x,y,z in positions))
                self.assertTrue(any(x>4.5 and y<.5 and z<0 for x,y,z in positions))

    def test_standard_tower_has_visible_closed_exterior_door(self):
        master=make_master(spec("wall_tower",(10,10,18)))
        portal=master["extensions"]["entrances"][0]
        self.assertEqual(portal["threshold_local_m"],[0,0,5])
        self.assertEqual(portal["door_state"],"closed")
        self.assertFalse(portal["through_passage"])
        self.assertFalse(portal["interior_transition_available"])
        self.assertEqual(portal["wallwalk_access"],"pending_vertical_connection")
        self.assertFalse(any(c["kind"]=="empty_region" for c in master["constraints"]))
        compiled=coordinate_planes.compile_master(master,{"pitch":.5})
        self.assertTrue(compiled["valid"])
        door=[row for row in compiled["cells"] if row[5]=="door"]
        self.assertTrue(door)
        self.assertTrue(any(row[1]==0 for row in door))

    def test_actual_low_church_entries_have_capsule_headroom(self):
        brief=json.loads((ROOT/"world_city/data/city_brief.v2.json").read_text())
        plans={b["id"]:b for b in brief["building_plans"]}
        for asset_id in ("D01-B006","D07-B135"):
            plan=plans[asset_id];polygon=plan["footprint_xz_m"]
            dimensions=(math.dist(polygon[0],polygon[1]),math.dist(polygon[1],polygon[2]),
                        plan["height_candidate_m"])
            source=spec("church",dimensions);source["asset_id"]=asset_id
            master=make_master(source);portal=master["extensions"]["entrances"][0]
            self.assertGreaterEqual(portal["clear_height_m"],2.2)
            self.assertGreaterEqual(portal["clear_width_m"],1.4)
            for pitch in (.5,.25):
                with self.subTest(asset_id=asset_id,pitch=pitch):
                    compiled=coordinate_planes.compile_master(master,{"pitch":pitch})
                    self.assertTrue(compiled["valid"],compiled["constraints"])
                    check=next(c for c in compiled["constraints"] if c["id"]=="church_entry_clearance")
                    self.assertEqual(check["blocked_cells"],0)
                    door_w=portal["clear_width_m"];door_h=portal["clear_height_m"];z=dimensions[1]/2
                    positions=[[(n+.5)*pitch for n in row[:3]] for row in compiled["cells"]]
                    self.assertEqual(sum(-door_w/2 <= x < door_w/2 and 0 <= y < door_h and z-.9 <= zz < z
                                         for x,y,zz in positions),0)

    def test_actual_warehouse_posts_survive_both_requested_pitches(self):
        from world_city.runtime_city.assemble_city import frame
        brief=json.loads((ROOT/"world_city/data/city_brief.v2.json").read_text())
        plans={b["id"]:b for b in brief["building_plans"]}
        for asset_id in ("D05-B009","D05-B013","D04-B171"):
            plan=plans[asset_id];_,_,width,depth,_=frame(plan)
            dimensions=(round(width,3),round(depth,3),plan["height_candidate_m"])
            source=spec("warehouse",dimensions);source["asset_id"]=asset_id
            master=make_master(source)
            for pitch in (.5,.25):
                with self.subTest(asset_id=asset_id,dimensions=dimensions,pitch=pitch):
                    compiled=coordinate_planes.compile_master(master,{"pitch":pitch})
                    self.assertTrue(compiled["valid"],compiled["constraints"])
                    timber=next(c for c in compiled["constraints"] if c["id"]=="timber_present")
                    self.assertGreater(timber["occupied_cells"],0)
                    for side in (-1,1):
                        self.assertTrue(any(row[5]=="timber" and side*(row[0]+.5)>0
                                            for row in compiled["cells"]))

    def test_shared_stone_palette(self):
        house=json.loads((ROOT/"voxel_character/common/assets/house/master.json").read_text())
        self.assertTrue(all(house["materials"][k]==v for k,v in PALETTE.items()))

    def test_source_is_deterministic_and_unmutated_by_compile(self):
        source=spec("wall_tower",COMPACT["wall_tower"])
        master=make_master(source)
        before=copy.deepcopy(master)
        self.assertEqual(master,make_master(source))
        a=coordinate_planes.compile_master(master,{"pitch":.5})
        b=coordinate_planes.compile_master(master,{"pitch":.5})
        self.assertEqual(a["payload_hash"],b["payload_hash"])
        self.assertEqual(a["master_hash"],b["master_hash"])
        self.assertEqual(master,before)

    def test_bad_spec_rejected(self):
        for invalid in (None,{},spec("unknown",(8,8,8)),spec("wall_tower",(float("nan"),8,8))):
            with self.assertRaises(ValueError):
                make_master(invalid)


if __name__ == "__main__":
    unittest.main()
